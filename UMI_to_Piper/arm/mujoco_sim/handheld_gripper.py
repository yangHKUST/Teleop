#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""手持夹爪（DM3507 电机）非 ROS 读取：CANable2(SLCAN) -> 物理两指间距 (m)。

复用 ``gripper/gripper_teleop/dm_canable2`` 纯 Python CAN 驱动 +
``gripper/config/gripper_calibration.json`` 线性标定（encoder 38079 全闭 ~ 34247 全开，
开度随编码器递减），把原始编码器读数映射成物理两指间距 width_m 与开合百分比 pct，
供遥操层 1:1 驱动仿真 qpos[6:8] 与真机 ``GripperCtrl``。

设备不插（/dev/ttyACM0 不存在）或打开失败时构造函数抛异常，调用方应降级为
「无夹爪跟随」而不是崩溃。后台线程非阻塞读，``width()`` 返回 None 表示尚无有效读数。
"""
from __future__ import annotations

import json
import sys
import threading
import time
from collections import deque
from pathlib import Path
from typing import Optional, Tuple

REPO_ROOT = Path(__file__).resolve().parents[2]
GRIPPER_DIR = REPO_ROOT / "gripper"
CALIB_FILE = GRIPPER_DIR / "config" / "gripper_calibration.json"
DEFAULT_CALIB = {
    "encoder_min": 38079,
    "encoder_max": 34247,
    "width_min_m": 0.00013,
    "width_max_m": 0.07039,
}


def encoder_to_width_pct(raw_encoder: float, calib: dict) -> Tuple[float, float]:
    """原始编码器计数 -> (物理两指间距 m, 开合百分比 %)。规范 §4.6 线性映射。"""
    c_min = float(calib["encoder_min"])
    c_max = float(calib["encoder_max"])
    w_min = float(calib["width_min_m"])
    w_max = float(calib["width_max_m"])
    frac = (float(raw_encoder) - c_min) / (c_max - c_min)
    frac = max(0.0, min(1.0, frac))
    return w_min + frac * (w_max - w_min), frac * 100.0


class HandheldGripper:
    """后台线程读取手持夹爪开度，非阻塞地提供 latest width_m / pct。"""

    def __init__(self, channel: str = "/dev/ttyACM0", motor_id: int = 7,
                 master_id: int = 17, rate_hz: float = 20.0,
                 calib_file: Optional[Path] = None) -> None:
        if str(GRIPPER_DIR) not in sys.path:
            sys.path.insert(0, str(GRIPPER_DIR))
        from gripper_teleop.dm_canable2 import (  # noqa: E402
            DM_Motor_Type, Motor, MotorControl)

        calib_path = Path(calib_file) if calib_file is not None else CALIB_FILE
        try:
            calib = json.loads(calib_path.read_text(encoding="utf-8"))
        except (OSError, ValueError, json.JSONDecodeError):
            calib = {}
        for key in ("encoder_min", "encoder_max", "width_min_m", "width_max_m"):
            calib.setdefault(key, DEFAULT_CALIB[key])
        self._calib = calib

        self._motor = Motor(DM_Motor_Type.DM3507, int(motor_id), int(master_id))
        self._control = MotorControl(channel=channel, can_bitrate=1000000,
                                     tty_baudrate=115200)
        self._control.addMotor(self._motor)

        self._lock = threading.Lock()
        self._width: Optional[float] = None
        self._pct: Optional[float] = None
        self._raw: Optional[float] = None
        self._rate_hz = float(rate_hz)
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._loop, name="handheld_gripper",
                                        daemon=True)
        self._thread.start()

    def _loop(self) -> None:
        period = 1.0 / max(self._rate_hz, 1.0)
        hist: deque = deque(maxlen=10)
        while not self._stop.is_set():
            t0 = time.monotonic()
            try:
                self._control.refresh_motor_status(self._motor)
                raw = self._motor.getRawEncoder()
                if raw == 0:
                    # 尚未收到有效反馈（Motor.state_q_raw 默认 0），不当作开度。
                    time.sleep(0.05)
                    continue
                hist.append(raw)
                avg = sum(hist) / len(hist)
                width, pct = encoder_to_width_pct(avg, self._calib)
                with self._lock:
                    self._raw = float(avg)
                    self._width = width
                    self._pct = pct
            except Exception:
                time.sleep(0.05)
                continue
            sleep = period - (time.monotonic() - t0)
            if sleep > 0:
                time.sleep(sleep)

    def width(self) -> Optional[float]:
        with self._lock:
            return None if self._width is None else self._width

    def pct(self) -> Optional[float]:
        with self._lock:
            return None if self._pct is None else self._pct

    def close(self) -> None:
        self._stop.set()
        if self._thread.is_alive():
            self._thread.join(timeout=1.0)
        try:
            self._control.close()
        except Exception:
            pass
