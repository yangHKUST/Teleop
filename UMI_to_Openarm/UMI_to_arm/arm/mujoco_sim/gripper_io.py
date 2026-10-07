#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""夹爪 I/O（独立遥操内嵌）：手持 DM3507 读开度 + AGX 夹爪裸 CAN 驱动。

把仓库 ``gripper/`` ROS 包的夹爪遥操能力，抽成**无 ROS** 的可复用模块，供
``piper_umi_attitude.py`` 等独立遥操脚本直接调用：

  * ``HandGripper``  —— 读手持夹爪 DM3507 编码器（SLCAN ``/dev/ttyACM3``），
    后台线程持续刷新，线性映射成物理两指间距 ``width_m``。
  * ``AgxGripper``   —— 向 ``can0`` 发一条 8 字节 CAN 帧（ID ``0x159``），
    驱动 AGX 机械臂夹爪到目标宽度 + 夹持力。
  * ``map_width``    —— 手持宽度 → AGX 宽度的 1:1 线性映射（scale/offset/clamp），
    与 ``gripper/gripper_teleop/gripper_agx_bridge.py`` 一致。

三条物理通道互不冲突：DM3507 走 SLCAN 串口、AGX 夹爪与 Piper 臂共用 ``can0``
（不同 CAN ID、SocketCAN 多 socket 可并存）、IMU 走 ``/dev/video*``。

单位约定（与 pyAgxArm ``AgxGripperDriverDefault.move_gripper_m`` 一致）：
  * ``value``  = 夹爪行程，int32，单位 **µm**（= width_m × 1e6）。
  * ``force``  = 夹持力，uint16，单位 **mN**（= force_n × 1e3）。
  * ``status_code`` = 0x01（使能 / 宽度模式）；``set_zero`` = 0x00（不设零点）。
"""

from __future__ import annotations

import json
import struct
import sys
import threading
import time
from collections import deque
from pathlib import Path

# 复用 gripper/ 包里的 dm_canable2（纯 python-can，无 ROS）。
_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT / "gripper") not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT / "gripper"))

from gripper_teleop.dm_canable2 import (  # noqa: E402
    Control_Type,
    DM_Motor_Type,
    Motor,
    MotorControl,
)

# AGX 夹爪控制帧
GRIPPER_CTRL_ID = 0x159
GRIPPER_STATUS_ENABLE_WIDTH = 0x01
GRIPPER_SET_ZERO_NONE = 0x00

# 手持夹爪标定文件（与 gripper/gripper_publisher.py 共用同一份）
_CALIB_PATH = _REPO_ROOT / "gripper" / "config" / "gripper_calibration.json"

# 手持电机模式：read-only=仅读编码器；disabled=失能后读；zero-torque=MIT 零目标力矩（可自由开合）。
HAND_GRIPPER_MODES = ("read-only", "disabled", "zero-torque")


def load_calibration(path: Path | None = None) -> dict:
    p = Path(path) if path is not None else _CALIB_PATH
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def encoder_to_width(raw_encoder: int, calib: dict) -> tuple[float, float]:
    """原始编码器计数 → (物理宽度 m, 开合百分比 %)。线性映射，随开度递减方向已处理。"""
    c_min = float(calib["encoder_min"])
    c_max = float(calib["encoder_max"])
    w_min = float(calib["width_min_m"])
    w_max = float(calib["width_max_m"])
    if c_min == c_max:
        raise ValueError("gripper_calibration.json encoder_min == encoder_max")
    frac = (float(raw_encoder) - c_min) / (c_max - c_min)
    frac = max(0.0, min(1.0, frac))
    return w_min + frac * (w_max - w_min), frac * 100.0


def map_width(width_m: float, scale: float = 1.0, offset: float = 0.0,
              min_w: float = 0.0, max_w: float = 0.1) -> float:
    """手持宽度 → AGX 宽度：agx = clamp(scale * width + offset, min_w, max_w)。"""
    return max(min_w, min(max_w, scale * width_m + offset))


class HandGripper:
    """DM3507 编码器读取；可选失能或 MIT 零目标力矩，串口访问由内部串行化。

    ``mode``：
      * ``read-only``   —— 仅查询编码器（默认，与旧行为一致）。
      * ``disabled``    —— 先失能电机，再读编码器。
      * ``zero-torque`` —— 切 MIT 控制模式、发零目标力矩后使能，夹爪可自由开合
        （人直接捏开/捏合），编码器读回位置映射到 AGX 夹爪。
    """

    def __init__(self, device: str = "/dev/ttyACM0",
                 calib_path: Path | None = None,
                 motor_id: int = 7, master_id: int = 17,
                 read_hz: float = 50.0, mode: str = "read-only") -> None:
        if mode not in HAND_GRIPPER_MODES:
            raise ValueError(f"未知手持夹爪模式: {mode}")
        self.mode = mode
        self.enabled = False
        self._width_m = 0.0
        self._lock = threading.Lock()
        self._io_lock = threading.Lock()
        self._stop = threading.Event()
        self._raw_history = deque(maxlen=10)
        self._control = None
        self._thread = None
        self._zero_torque_active = False

        try:
            self._motor = Motor(DM_Motor_Type.DM3507, motor_id, master_id)
            self._control = MotorControl(
                channel=device, can_bitrate=1000000, tty_baudrate=115200,
                auto_open=False)
            self._control.addMotor(self._motor)
            self._calib = load_calibration(calib_path)
            self._control.open()  # 提前打开，设备不存在时此处抛错 → 降级
            if mode != "read-only":
                self._control.disable(self._motor)
            if mode == "zero-torque":
                if not self._control.switchControlMode(self._motor, Control_Type.MIT):
                    raise RuntimeError("MIT 模式切换未确认，未发送使能指令")
                # 先覆盖旧控制目标，再使能；不保存到 Flash，也不设置编码器零点。
                self._send_zero_torque()
                self._control.enable(self._motor)
                self._send_zero_torque()
                self._zero_torque_active = True
        except (Exception, KeyboardInterrupt) as exc:
            self.close()
            if isinstance(exc, KeyboardInterrupt):
                raise
            if mode != "read-only":
                raise RuntimeError(f"手持夹爪 {mode} 启动失败: {exc}") from exc
            print(f"[gripper] 手持夹爪不可用（{exc}），本会话跳过夹爪读取")
            return

        try:
            self.enabled = True
            self._period = 1.0 / max(1.0, read_hz)
            self._thread = threading.Thread(target=self._run, daemon=True)
            self._thread.start()
            c = self._calib
            print(f"[gripper] 手持夹爪 {device} 已连接：encoder "
                  f"{c['encoder_min']}~{c['encoder_max']} / width "
                  f"{c['width_min_m']:.5f}~{c['width_max_m']:.5f} m")
            print(f"[gripper] 手持电机模式={mode}")
        except (Exception, KeyboardInterrupt):
            self.close()
            raise

    def _send_zero_torque(self) -> None:
        """MIT 零目标力矩：位置刚度、速度阻尼和前馈力矩均为 0。"""
        self._control.controlMIT(self._motor, kp=0.0, kd=0.0, q=0.0, dq=0.0, tau=0.0)

    def _run(self) -> None:
        while not self._stop.is_set():
            try:
                with self._io_lock:
                    if self._zero_torque_active:
                        self._send_zero_torque()  # 控制帧返回的反馈同时更新编码器。
                    else:
                        self._control.refresh_motor_status(self._motor)
                raw = self._motor.getRawEncoder()
                self._raw_history.append(raw)
                avg = sum(self._raw_history) / len(self._raw_history)
                width, _ = encoder_to_width(avg, self._calib)
                with self._lock:
                    self._width_m = width
            except Exception as exc:  # noqa: BLE001
                if not self._stop.is_set():
                    print(f"[gripper] 读取失败: {exc}")
                    if self.mode != "read-only":
                        self.stop_motor()
                        self.enabled = False
                        self._stop.set()
            self._stop.wait(self._period)

    def stop_motor(self) -> None:
        """停止主动力矩输出，后续仅查询编码器；本会话不自动重新使能。"""
        with self._io_lock:
            self._zero_torque_active = False
            if self.mode != "read-only" and self._control is not None and self._control.bus is not None:
                try:
                    self._control.disable(self._motor)
                except Exception as exc:
                    print(f"[gripper] 失能指令发送失败: {exc}")

    @property
    def width_m(self) -> float:
        with self._lock:
            return self._width_m

    def close(self) -> None:
        self._stop.set()
        if self._thread is not None and self._thread.is_alive():
            self._thread.join()
        self.stop_motor()
        if self._control is not None:
            try:
                self._control.close()
            except Exception:  # noqa: BLE001
                pass
            self._control = None
        self.enabled = False


class AgxGripper:
    """AGX 机械臂夹爪裸 CAN 驱动（socketcan，与 piper_sdk 共用 can0）。"""

    def __init__(self, channel: str = "can0") -> None:
        import can  # noqa: E402  (python-can，piper_sdk 已依赖)
        self._can = can
        self._bus = can.interface.Bus(
            interface="socketcan", channel=channel, bitrate=1000000,
            receive_own_messages=False)
        print(f"[gripper] AGX 夹爪 CAN 通道 {channel} 已打开")

    def move(self, width_m: float, force_n: float = 1.0) -> None:
        """下发目标宽度 (m) + 夹持力 (N)。宽度越界由调用方 clamp。"""
        value_i = int(round(width_m * 1e6))      # m -> µm，int32
        force_i = int(round(max(0.0, force_n) * 1e3))  # N -> mN，uint16
        data = struct.pack(">iHBB", value_i, force_i,
                           GRIPPER_STATUS_ENABLE_WIDTH, GRIPPER_SET_ZERO_NONE)
        self._bus.send(self._can.Message(
            arbitration_id=GRIPPER_CTRL_ID, is_extended_id=False, data=data))

    def close(self) -> None:
        try:
            self._bus.shutdown()
        except Exception:  # noqa: BLE001
            pass
