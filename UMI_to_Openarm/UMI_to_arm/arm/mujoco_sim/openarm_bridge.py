#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""OpenArm 真机 ZMQ 桥（Process A 侧）——镜像 ``piper_umi_core.PiperArm`` 接口。

Piper 版 ``PiperArm`` 用 piper_sdk 经 CAN 直驱真机；OpenArm 没有可从 conda 环境
直接调用的 SDK，低层走 ROS2 ros2_control。且 rclpy（/opt/ros/humble）与 conda 的
pinocchio 4.1.0 存在 PYTHONPATH 冲突，无法同进程。因此拆成两进程：

  * 本文件（Process A，conda ``piper_pinocchio`` env，非 ROS）：遥操主循环调用
    ``OpenArmBridge``，把解算出的 7 关节角/夹爪开度经 ZMQ 发给 ROS2 侧，并订阅
    ROS2 侧回发的 ``/joint_states`` 反馈。
  * ROS2 侧 ``openarm_umi_bridge`` 节点（Process B，rclpy）：收 ZMQ 命令，做关节
    空间速度限幅后发布到 ``right_forward_position_controller/commands``，并把
    ``/joint_states`` 回发到 ZMQ 反馈通道。

接口刻意与 ``PiperArm`` 对齐（send/read_joints/read_end_pose/send_gripper/
emergency_stop/freeze/close/gripper_max_m），使 ``openarm_vio_teleop.py`` 只需把
``PiperArm`` 换成 ``OpenArmBridge`` 即可，控制策略零改动。

消息协议（JSON 行，双方约定）：
  * 命令（本侧 PUSH -> 对端 PULL）：``{"type":"joints","q":[...7]}`` /
    ``{"type":"gripper","width":w}`` / ``{"type":"estop"}`` / ``{"type":"freeze"}`` /
    ``{"type":"config","max_joint_speed_deg_s":x}``。
  * 反馈（对端 PUB -> 本侧 SUB）：``{"type":"state","q":[...7]}``。

注意：**每拍关节速度上限不在本侧做**（Piper 版在 ``PiperArm.send`` 里做）。OpenArm
的前向控制器本身无插值/限速，速度限幅放在 ROS2 侧（离硬件最近的安全阀），本侧只
发目标。``max_joint_speed_deg_s`` 通过 ``config`` 消息下发给 ROS2 侧生效。
"""
from __future__ import annotations

import json
import math
import threading
import time

import numpy as np

from openarm_umi_core import _rot_to_rpy_deg  # noqa: E402  (同目录)

# 夹爪开度上限 (m)：openarm 指爪 prismatic 行程 0..0.044（URDF finger_joint1 上限）。
GRIPPER_MAX_M = 0.044

# 默认端点（与 ROS2 侧 openarm_umi_bridge 的默认参数一致）。
DEFAULT_CMD_ENDPOINT = "tcp://127.0.0.1:5556"
DEFAULT_FB_ENDPOINT = "tcp://127.0.0.1:5557"


class OpenArmBridge:
    """ZMQ 客户端：下发 7 关节角 + 夹爪开度，读回真机关节角/末端位姿，急停/冻结。

    ``kine``（可选，``OpenArmDecoupledIk``）用于 ``read_end_pose`` 把反馈关节角
    转成末端位姿（状态显示用）；不传则 read_end_pose 返回零。
    """

    def __init__(self, cmd_endpoint: str = DEFAULT_CMD_ENDPOINT,
                 fb_endpoint: str = DEFAULT_FB_ENDPOINT,
                 max_joint_speed_deg_s: float = 30.0,
                 kine=None) -> None:
        import zmq  # local import: conda piper_pinocchio env 需有 pyzmq

        self._ctx = zmq.Context()

        # 命令通道：PUSH（connect，非 bind，对 ROS2 侧后启动鲁棒）。
        self._cmd = self._ctx.socket(zmq.PUSH)
        self._cmd.setsockopt(zmq.LINGER, 0)
        self._cmd.setsockopt(zmq.SNDHWM, 10)
        self._cmd.connect(cmd_endpoint)

        # 反馈通道：SUB（订阅 ROS2 侧回发的 joint_states）。
        self._sub = self._ctx.socket(zmq.SUB)
        self._sub.setsockopt(zmq.SUBSCRIBE, b"")
        self._sub.setsockopt(zmq.LINGER, 0)
        self._sub.setsockopt(zmq.RCVTIMEO, 200)
        self._sub.connect(fb_endpoint)

        self._lock = threading.Lock()
        self._q_fb = None          # 最新真机 7 关节角（rad，来自 /joint_states），None=尚无反馈
        self._last_recv = 0.0
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._fb_loop, name="openarm_zmq_fb",
                                        daemon=True)
        self._thread.start()

        # 关节速度上限不下发本侧限幅，而是经 config 消息传给 ROS2 侧。
        self._max_joint_speed_deg_s = float(max_joint_speed_deg_s)
        self._config_sent = False

        self._kine = kine
        self.gripper_max_m = GRIPPER_MAX_M
        self._last_q = None        # 最近一次下发的目标 q（反馈未到时的 read_joints 兜底）

    # ------------------------------------------------------------------ #
    # 反馈线程
    # ------------------------------------------------------------------ #
    def _fb_loop(self) -> None:
        import zmq
        while not self._stop.is_set():
            try:
                raw = self._sub.recv()
            except zmq.Again:
                continue
            except Exception:
                break
            try:
                msg = json.loads(raw.decode("utf-8", "replace"))
            except (ValueError, UnicodeDecodeError):
                continue
            if msg.get("type") != "state":
                continue
            q = msg.get("q")
            if isinstance(q, (list, tuple)) and len(q) == 7:
                try:
                    q_array = np.asarray(q, dtype=float)
                except (TypeError, ValueError):
                    continue
                if not np.all(np.isfinite(q_array)):
                    continue
                with self._lock:
                    self._q_fb = q_array
                    self._last_recv = time.monotonic()

    # ------------------------------------------------------------------ #
    # 命令下发
    # ------------------------------------------------------------------ #
    def _send_json(self, obj: dict) -> None:
        self._cmd.send(json.dumps(obj).encode("utf-8"))

    def _send_config(self) -> None:
        self._send_json({"type": "config",
                         "max_joint_speed_deg_s": self._max_joint_speed_deg_s})
        self._config_sent = True

    def send(self, q: np.ndarray) -> np.ndarray:
        """下发 7 关节角 (rad)。速度限幅由 ROS2 侧做，本侧只发目标，返回目标 q。"""
        if not self._config_sent:
            self._send_config()
        q = np.asarray(q, dtype=float).reshape(7)
        self._send_json({"type": "joints", "q": [float(v) for v in q]})
        self._last_q = q.copy()
        return q

    def send_gripper(self, width_m: float, effort_nm: float = 1.0) -> None:
        """下发夹爪开度 (m)，clamp 到 [0, 0.044]。effort 参数保留接口兼容（OpenArm
        指爪为位置控制，无力矩档）。"""
        w = max(0.0, min(float(width_m), self.gripper_max_m))
        self._send_json({"type": "gripper", "width": w})

    def emergency_stop(self) -> None:
        """急停：ROS2 侧停止发布（前向控制器保持最后命令，臂原地保持，不下坠）。"""
        self._send_json({"type": "estop"})

    def resume(self) -> None:
        """显式解除 ROS 桥的保持状态（用户按 h 后调用）。"""
        self._send_json({"type": "resume"})

    def freeze(self) -> None:
        """冻结在位：停止发布、保持最后位置（退出前回准备姿态后调用）。"""
        self._send_json({"type": "freeze"})

    # ------------------------------------------------------------------ #
    # 读回
    # ------------------------------------------------------------------ #
    def joint_feedback(self):
        """返回实测状态和年龄；尚无反馈时返回 None，不使用目标兜底。"""
        with self._lock:
            q = None if self._q_fb is None else self._q_fb.copy()
            age = time.monotonic() - self._last_recv if q is not None else float("inf")
        return q, age

    def read_joints(self) -> np.ndarray:
        """读真机 7 关节角 (rad)。反馈未到则退回最近下发目标，再退回 0。"""
        with self._lock:
            q = None if self._q_fb is None else self._q_fb.copy()
        if q is not None:
            return q
        if self._last_q is not None:
            return self._last_q.copy()
        return np.zeros(7)

    def wait_for_joints(self, timeout: float = 5.0, interval: float = 0.05) -> np.ndarray:
        """等首帧 /joint_states 反馈（连接后真机关节角可能在几百 ms 后才到）。

        与 Piper 的 ``_read_joints_with_retry`` 同义：避免把「尚未收到反馈」当成
        「关节角全 0」而把 home 锚到限位。返回读到的 7 关节角。
        """
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            with self._lock:
                if self._q_fb is not None and time.monotonic() - self._last_recv <= 0.5:
                    return self._q_fb.copy()
            time.sleep(interval)
        raise TimeoutError("未收到新鲜的 OpenArm 关节反馈，拒绝用目标或零值初始化")

    def read_end_pose(self) -> tuple[np.ndarray, np.ndarray]:
        """读末端位姿 -> (p_xyz_m (3,), rpy_deg (3,))。

        由反馈关节角经 ``kine`` FK 得到（body 系）；无 kine 或无反馈时返回零。
        """
        q = self.read_joints()
        if self._kine is not None:
            T = self._kine.fk(q)
            return T.translation.copy(), _rot_to_rpy_deg(T.rotation)
        return np.zeros(3), np.zeros(3)

    # ------------------------------------------------------------------ #
    def close(self) -> None:
        # 先置 stop 并 join 反馈线程（RCVTIMEO=200ms，线程最多 ~200ms 内退出），
        # 再关 socket / term 上下文。若反序（先关 socket / term 再 join），recv 中的
        # 线程会让 ctx.term() 阻塞，导致进程挂住。
        self._stop.set()
        if self._thread.is_alive():
            self._thread.join(timeout=1.0)
        for sock in ("_sub", "_cmd"):
            try:
                getattr(self, sock).close(linger=0)
            except Exception:
                pass
        try:
            self._ctx.term()
        except Exception:
            pass
