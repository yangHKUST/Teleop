#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""VIO（ORB_SLAM3-Cyperstereo，左目光心世界）→ OpenArm v1.0 机械臂 增量式遥操（非 ROS）。

**无 ROS**：直接订阅 ORB_SLAM3 ``cyperstereo_online`` 经 ZMQ PUB 发布的 6DoF 位姿
（``tcp://127.0.0.1:5555``，每帧一行 ``"<ts> <tx> <ty> <tz> <qx> <qy> <qz> <qw>"``，
q 为 R_wc（相机→世界，xyzw），t 为相机在 VIO 世界中的位置）。

控制策略与 ``piper_vio_teleop.py`` **逐行一致**（增量式遥操：平移在 base 系、姿态在
末端夹爪局部系；1€ 滤波、死区、增益、平滑、逆解）。差异只在硬件适配：

  * IK：``OpenArmDecoupledIk``（URDF 建模，全 6D 位姿 + 7 关节全动的 DLS IK，
    冗余自由度零空间投影到可配置参考姿态）。
  * 真机下发：``OpenArmBridge``（ZMQ 客户端）替代 ``PiperArm``（CAN 直驱）。每拍
    关节变化在本侧求解时限制，ROS2 侧保留原速度限幅。
  * 可视化：RViz（ROS2 侧 bringup 自动拉起，显示真实/仿真硬件位姿）；本脚本不带
    MuJoCo 孪生。

运行（piper_pinocchio conda env、unset PYTHONPATH，先启动 ROS2 侧再运行本脚本）：
    ./arm/mujoco_sim/openarm_vio_teleop.py                          # VIO + RViz（先标定 R_BW）
    ./arm/mujoco_sim/openarm_vio_teleop.py --bridge                 # + 真机（经 ZMQ 桥）
    ./arm/mujoco_sim/openarm_vio_teleop.py --no-calibrate           # 跳过标定，R_BW=单位阵
    ./arm/mujoco_sim/openarm_vio_teleop.py --synthetic --steps 300  # 离线冒烟（仅计算，无可视化）
"""

from __future__ import annotations

import argparse
import atexit
import json
import math
import os
import signal
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Optional, Tuple

import numpy as np

# Repo root + 本目录（openarm_umi_core / openarm_urdf_ik / openarm_bridge）。
REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import pinocchio as pin  # noqa: E402
from openarm_umi_core import (  # noqa: E402
    so3_log, _exp_so3, _rot_to_rpy_deg,
    default_home_q, home_file, ready_file,
    save_home_q, anchor_home_from_arm, load_ready_q, save_ready_q,
    default_ready_q, restore_default_ready_q, ready_source,
)
from openarm_urdf_ik import OpenArmDecoupledIk  # noqa: E402
from openarm_bridge import OpenArmBridge  # noqa: E402
from teleop_output import TeleopOutput
from teleop_keys import KeyRelay
from vio_launch import vio_environment
output = TeleopOutput()


def print(*args, **kwargs):
    """本模块旧提示通过统一输出层，未改变控制行为。"""
    output.legacy(*args, **kwargs)

from keyboard.keyboard_input import KeyboardReader  # noqa: E402
from handheld_gripper import HandheldGripper  # noqa: E402


def _quat_xyzw_to_rot(qx, qy, qz, qw) -> np.ndarray:
    """四元数 (x, y, z, w) -> 3x3 旋转矩阵（R_wc：相机→世界）。"""
    x, y, z, w = qx, qy, qz, qw
    return np.array([
        [1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
        [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
        [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)],
    ], dtype=np.float64)


# ============================================================================
# VIO 位姿源
# ============================================================================

class VioZMQSource:
    """ZMQ SUB 订阅 ORB_SLAM3-Cyperstereo 位姿，后台线程持续更新 latest T_W←C。

    与 ``vio_odom_bridge`` 相同：静默 = VIO 未就绪或跟踪丢失；``age()`` 给出距上一帧
    的秒数，供遥操层判跟踪丢失并重锁参考。
    """

    def __init__(self, endpoint: str) -> None:
        import zmq  # local import: conda piper_pinocchio env 需有 pyzmq
        self._ctx = zmq.Context()
        self._sock = self._ctx.socket(zmq.SUB)
        self._sock.setsockopt(zmq.SUBSCRIBE, b"")
        self._sock.setsockopt(zmq.LINGER, 0)
        self._sock.connect(endpoint)
        self._poller = zmq.Poller()
        self._poller.register(self._sock, zmq.POLLIN)

        self._lock = threading.Lock()
        self._T: Optional[np.ndarray] = None   # latest 4x4 T_W←C
        self._seq = 0                          # 收到帧计数（main 据此识别新帧）
        self._last_recv = time.monotonic()
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._recv_loop, name="zmq_recv", daemon=True)
        self._thread.start()

    def _recv_loop(self) -> None:
        while not self._stop.is_set():
            try:
                events = dict(self._poller.poll(timeout=200))
            except Exception:
                break
            if self._sock not in events:
                continue
            try:
                raw = self._sock.recv()
            except Exception:
                break
            T = self._parse(raw)
            if T is not None:
                with self._lock:
                    self._T = T
                    self._seq += 1
                    self._last_recv = time.monotonic()

    @staticmethod
    def _parse(raw: bytes) -> Optional[np.ndarray]:
        parts = raw.decode("ascii", "replace").split()
        if len(parts) != 8:
            return None
        try:
            _ts, tx, ty, tz, qx, qy, qz, qw = (float(p) for p in parts)
        except ValueError:
            return None
        T = np.eye(4, dtype=np.float64)
        T[:3, :3] = _quat_xyzw_to_rot(qx, qy, qz, qw)
        T[:3, 3] = [tx, ty, tz]
        return T

    def latest_with_seq(self) -> Tuple[Optional[np.ndarray], int]:
        """返回 (最新 T_W←C 4x4 或 None, 帧计数)。"""
        with self._lock:
            return (None if self._T is None else self._T.copy()), self._seq

    def latest(self) -> Optional[np.ndarray]:
        return self.latest_with_seq()[0]

    def age(self) -> float:
        with self._lock:
            return time.monotonic() - self._last_recv

    def close(self) -> None:
        self._stop.set()
        try:
            self._sock.close(linger=0)
        except Exception:
            pass
        try:
            self._ctx.term()
        except Exception:
            pass
        if self._thread.is_alive():
            self._thread.join(timeout=1.0)


class SyntheticVioSource:
    """脚本化 VIO 位姿（无相机冒烟测试）：小幅正弦平动 + 绕 x/y/z 三轴摆动（覆盖 6D）。"""

    def __init__(self) -> None:
        self._t0 = time.monotonic()
        self._seq = 0
        self._T = np.eye(4)

    def latest_with_seq(self) -> Tuple[Optional[np.ndarray], int]:
        t = time.monotonic() - self._t0
        self._seq += 1
        T = np.eye(4)
        T[:3, 3] = [
            0.25 * math.sin(2 * math.pi * 0.2 * t),
            0.25 * math.sin(2 * math.pi * 0.13 * t),
            0.18 * math.sin(2 * math.pi * 0.17 * t),
        ]
        # 绕局部 x/y/z（yaw/pitch/roll）三轴摆动，覆盖全 6D 姿态增量。
        T[:3, :3] = _exp_so3(np.array([
            0.12 * math.sin(2 * math.pi * 0.09 * t),   # yaw（绕 +x 掌法向）
            0.12 * math.sin(2 * math.pi * 0.11 * t),   # pitch（绕 +y 开合轴）
            0.15 * math.sin(2 * math.pi * 0.1 * t),    # roll（绕 +z approach）
        ]))
        self._T = T
        return self._T.copy(), self._seq

    def latest(self) -> Optional[np.ndarray]:
        return self.latest_with_seq()[0]

    def age(self) -> float:
        return 0.0

    def close(self) -> None:
        pass


# ============================================================================
# 启动标定：R_BW（world→base）
# ============================================================================

def record_direction(src, axis: str, desc: str) -> Optional[np.ndarray]:
    """手持夹爪沿 base +axis（desc）平移，返回该方向在 VIO 世界中的单位向量。"""
    _tty_input(f"[{axis}] 手持夹爪放到起点（{desc}），回车记录起点位置 ... ")
    T0 = src.latest()
    if T0 is None:
        print("  没有收到 VIO 位姿，请确认 cyperstereo_online 已 tracking")
        return None
    p0 = T0[:3, 3].copy()
    _tty_input(f"[{axis}] 沿 base +{axis}（{desc}）平移一段距离，回车记录终点 ... ")
    T1 = src.latest()
    if T1 is None:
        print("  没有收到 VIO 位姿")
        return None
    p1 = T1[:3, 3].copy()
    d = p1 - p0
    n = float(np.linalg.norm(d))
    if n < 1e-3:
        print(f"  位移太小 ({n * 1000:.1f} mm)，请重试")
        return None
    d = d / n
    print(f"  base +{axis} 在 VIO world 中的方向: [{d[0]:+.5f}, {d[1]:+.5f}, {d[2]:+.5f}]")
    return d


def gram_schmidt(vectors: list[np.ndarray]) -> Optional[np.ndarray]:
    basis: list[np.ndarray] = []
    for v in vectors:
        w = v.copy()
        for b in basis:
            w = w - float(np.dot(w, b)) * b
        n = float(np.linalg.norm(w))
        if n < 1e-9:
            return None
        basis.append(w / n)
    return np.array(basis)


def handeye_camera_to_flange(pitch_deg: float) -> np.ndarray:
    """相机光心系 → 法兰系的手眼旋转 ``R_CF``（3x3）。

    与 piper 版完全一致（手眼描述的是手持相机 ↔ 夹爪的关系，与臂无关）：
    相机在夹爪上方、俯视夹爪、倒装，光轴比夹爪指向(approach)低 ``pitch_deg`` 度。
    ``R_CF = Rz(+90°) · Rx(+pitch_deg)``。
    """
    a = math.radians(pitch_deg)
    ca, sa = math.cos(a), math.sin(a)
    return np.array(
        [
            [0.0, -ca, sa],
            [1.0, 0.0, 0.0],
            [0.0, sa, ca],
        ],
        dtype=np.float64,
    )


def calibrate_rbw_base(src, R_cf: np.ndarray, *, confirm=True, max_age=None) -> Optional[np.ndarray]:
    """测 R_BW（VIO world→base）——Z/X 标定（摆朝向法，不再推）。

    用户把手持夹爪摆成与机械臂末端夹爪「同向」（手指指向工作区），回车后读相机朝向
    R_WC，结合手眼 R_CF 得到法兰朝向 R_WF = R_WC·R_CFᵀ：
      * +Z（上）：VIO 世界重力对齐（Z 沿重力），相机俯视夹爪 → 光轴(相机 +z)朝下，
        据此定世界 +z 的正负，无需再推上。
      * +X（前）：人站在机械臂对面相向遥操，摆「同向」时手指（approach，法兰 +z）
        指向工作区 = 指向机械臂，与 base +X（机械臂伸向工作区 = 指向人）相反，故
        base +X = −approach。取 −approach 投影到水平面。
      * 左 = 上×前 自动导出。
    """
    print("\n" + "=" * 72)
    print("启动 Z/X 标定 R_BW（VIO world → robot base）")
    print("  机械臂保持在准备位姿不动；手持夹爪摆成与机械臂末端夹爪「同向」：")
    print("    手指（approach）水平指向工作区（人机相向，与 base +X 相反，代码自动取反）")
    print("  （+Z 上由 VIO 重力自动定，+X 前由夹爪指向定，左 = 上×前 自动导出，无需再推。）")
    print("=" * 72)

    if confirm:
        _tty_input("[step] 摆好朝向（手指水平指前后），回车确定 ... ")
    if max_age is not None and src.age() > max_age:
        output.event("标定位姿已过期，请恢复视觉追踪后重新启动标定。", "ERROR", "calibration")
        return None

    T = src.latest()
    if T is None:
        print("  没有收到 VIO 位姿，请确认 cyperstereo_online 已 tracking")
        return None

    R_wc = np.asarray(T[:3, :3], dtype=float)   # camera → world
    # R_CF 是「相机→法兰」（v_f = R_CF·v_c），故法兰→世界 = R_WC·R_CFᵀ（不是 R_WC·R_CF）。
    R_wf = R_wc @ R_cf.T                         # flange → world

    # +Z（上）：相机俯视夹爪 → 光轴(相机 +z)朝下。R_wc[2,2] 是光轴在世界 +z 上的分量：
    # 为负说明世界 +z 朝上，为正说明世界 +z 朝下（ORB-SLAM3/IMU 常见）。据此定 base +Z。
    if abs(float(R_wc[2, 2])) < 0.3:
        print(f"[warn] 光轴世界 z 分量 {R_wc[2, 2]:+.2f} 接近 0，可能没摆正（相机应俯视"
              f"夹爪），上下判定或不准。")
    u = np.array([0.0, 0.0, 1.0]) if R_wc[2, 2] < 0.0 else np.array([0.0, 0.0, -1.0])
    print(f"[info] 世界 +z {'朝上' if u[2] > 0 else '朝下'} → base +Z = {u.tolist()}。")

    # +X（前）：人机相向 → base 前向 = −approach（法兰 +z 的反向），投影到水平面。
    f = -R_wf[:, 2].copy()
    f = f - float(np.dot(f, u)) * u
    nf = float(np.linalg.norm(f))
    if nf < 1e-3:
        print("[fail] approach 方向几乎竖直，请把手持夹爪摆成水平指前后重试")
        return None
    f = f / nf

    l = np.cross(u, f)

    R_wb = np.column_stack([f, l, u])  # 列 = base 三轴在世界系（R_WB：base→world）
    R_bw = R_wb.T                       # world→base

    print("\n=== R_BW (VIO world -> robot base), 9 值行主序 ===")
    flat = R_bw.flatten()
    print("rotation: [" + ", ".join(f"{v:.6f}" for v in flat) + "]")
    fwd = R_bw[0, :]   # base +X（前）在 VIO world 中的方向（= R_wb 第 1 列 = f）
    up = R_bw[2, :]    # base +Z（上）在 VIO world 中的方向（= R_wb 第 3 列 = u）
    print(f"[info] base +X（前）在 VIO world 中 = [{fwd[0]:+.3f}, {fwd[1]:+.3f}, {fwd[2]:+.3f}]")
    print(f"[info] base +Z（上）在 VIO world 中 = [{up[0]:+.3f}, {up[1]:+.3f}, {up[2]:+.3f}]")
    print("验证：手持夹爪沿机械臂 +X（前）平移，机械臂末端应沿自身 +X 平移。")
    print("      若前后/左右又反了（180° yaw）→ 手指指向摆反了，重摆一次（或加 --flip-yaw）。")
    return R_bw


def _terminate_process_group(proc) -> None:
    """终止 VIO 子进程组（shell=True 启动的进程须 killpg 才能连带杀掉其子进程）。"""
    if proc is None or proc.poll() is not None:
        return
    try:
        os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
        proc.wait(timeout=5)
    except Exception:
        try:
            os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
        except Exception:
            pass


def _print_banner() -> None:
    print("=" * 72)
    print("VIO → OpenArm 机械臂 增量式遥操（非 ROS · 左目光心世界为本体）")
    print("  平移 <- base 系逐帧增量 Δ_t（scale·R_BW·Δ_t，累加到目标）")
    print("  姿态 <- 夹爪局部旋转向量（6D：yaw/pitch/roll 全跟，全 6D IK）")
    print("  真机 + RViz 同步；空格=离合(冻结/跟随)  s=记录当前位姿为准备姿态  h=回准备姿态  esc=急停")
    print("=" * 72)


# ============================================================================
# 手持生理性抖动滤波：1€ 滤波器（Casiez et al. 2012）
# ============================================================================

class _OneEuro:
    """单通道 1€ 自适应低通：静止时用低截止狠压抖动，运动越快截止越高（低延迟）。"""

    def __init__(self, min_cutoff: float, beta: float, d_cutoff: float) -> None:
        self.min_cutoff = float(min_cutoff)
        self.beta = float(beta)
        self.d_cutoff = float(d_cutoff)
        self._x = None
        self._dx = 0.0
        self._t = None

    def reset(self) -> None:
        self._x = None
        self._dx = 0.0
        self._t = None

    @staticmethod
    def _alpha(cutoff: float, dt: float) -> float:
        tau = 1.0 / (2.0 * math.pi * max(cutoff, 1e-6))
        return 1.0 / (1.0 + tau / dt)

    def __call__(self, t: float, x: float) -> float:
        if self._x is None:
            self._x = float(x)
            self._t = float(t)
            return float(x)
        dt = t - self._t
        self._t = float(t)
        if dt <= 1e-6:
            return self._x
        dx = (x - self._x) / dt
        a_d = self._alpha(self.d_cutoff, dt)
        self._dx = a_d * dx + (1.0 - a_d) * self._dx
        cutoff = self.min_cutoff + self.beta * abs(self._dx)
        a = self._alpha(cutoff, dt)
        self._x = a * x + (1.0 - a) * self._x
        return self._x


def _build_pose(R: np.ndarray, p: np.ndarray) -> np.ndarray:
    """旋转 + 平移 -> 4x4 齐次位姿。"""
    T = np.eye(4, dtype=np.float64)
    T[:3, :3] = R
    T[:3, 3] = p
    return T


class PoseFilter:
    """VIO 位姿/增量滤波（与 piper 版一致）。"""

    def __init__(self, args) -> None:
        self.mode = args.filter
        if self.mode == "one_euro":
            self._p = [_OneEuro(args.one_euro_min_cutoff, args.one_euro_beta,
                                args.one_euro_d_cutoff) for _ in range(3)]
            self._r = [_OneEuro(args.one_euro_min_cutoff, args.one_euro_beta,
                                args.one_euro_d_cutoff) for _ in range(3)]
            self._R_ref = None
        else:
            self.ema_dp = np.zeros(3)
            self.ema_rot = np.zeros(3)
            self.alpha = args.vio_alpha

    def reset(self) -> None:
        if self.mode == "one_euro":
            for f in self._p + self._r:
                f.reset()
            self._R_ref = None
        else:
            self.ema_dp[:] = 0.0
            self.ema_rot[:] = 0.0

    def filter_pose(self, t: float, T: np.ndarray) -> np.ndarray:
        R_raw = T[:3, :3]
        p_raw = T[:3, 3]
        if self._R_ref is None:
            self._R_ref = R_raw.copy()
            return _build_pose(R_raw, np.array([f(t, v) for f, v in zip(self._p, p_raw)]))
        rv = so3_log(self._R_ref.T @ R_raw)
        rv_filt = np.array([f(t, v) for f, v in zip(self._r, rv)])
        R_filt = self._R_ref @ _exp_so3(rv_filt)
        p_filt = np.array([f(t, v) for f, v in zip(self._p, p_raw)])
        return _build_pose(R_filt, p_filt)

    def filter_inc(self, delta_p, rot_inc):
        a = self.alpha
        self.ema_dp = a * delta_p + (1.0 - a) * self.ema_dp
        self.ema_rot = a * rot_inc + (1.0 - a) * self.ema_rot
        return self.ema_dp, self.ema_rot


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="VIO → OpenArm 机械臂 6D 增量遥操（非 ROS）")
    p.add_argument("--arm", choices=["left", "right"], default="right",
                   help="遥操哪条臂：right=右臂（默认），left=左臂（镜像 home/限位/默认端口）")
    p.add_argument("--endpoint", default=None,
                   help="ORB_SLAM3 ZMQ 位姿端点（默认按 --arm 选 5555/5565）")
    p.add_argument("--synthetic", action="store_true", help="脚本化 VIO 位姿（无相机冒烟）")
    p.add_argument("--bridge", action="store_true",
                   help="真机经 ZMQ 桥下发（需 ROS2 侧 openarm_umi_bridge 已运行）")
    p.add_argument("--bridge-cmd", default=None,
                   help="ZMQ 命令端点（默认按 --arm 选 5556/5566）")
    p.add_argument("--bridge-fb", default=None,
                   help="ZMQ 反馈端点（默认按 --arm 选 5557/5567）")
    p.add_argument("--steps", type=int, default=0, help="headless：跑 N tick 后退出（0=直到退出）")
    # 启动标定
    p.add_argument("--calibrate", action=argparse.BooleanOptionalAction, default=True,
                   help="启动 Z/X 标定测 R_BW（+Z 上由重力自动定、+X 前由夹爪指向定）；--no-calibrate 用单位阵")
    p.add_argument("--rbw-output", default="", help="可选：把 R_BW 9 值写到文件")
    # 增量映射 / 死区 / 跟踪丢失
    p.add_argument("--scale", type=float, default=0.51, help="位移缩放（world m → base m）")
    p.add_argument("--pitch-gain", type=float, default=1.0,
                   help="俯仰(pitch)增益，>1 放大俯仰（夹爪点头/仰头更跟手）")
    p.add_argument("--y-gain", type=float, default=1.0, help="左右平移增益")
    p.add_argument("--x-gain", type=float, default=1.5, help="前后平移增益")
    p.add_argument("--z-gain", type=float, default=1.5, help="上下平移增益")
    p.add_argument("--trans-deadzone", type=float, default=0.005, help="平移死区 (m)")
    p.add_argument("--rot-deadzone", type=float, default=0.001,
                   help="滚转(roll)死区 (rad，~0.057°)")
    p.add_argument("--pitch-deadzone", type=float, default=0.0029,
                   help="俯仰(pitch)死区 (rad，~0.17°)")
    p.add_argument("--filter", choices=["one_euro", "ema"], default="one_euro",
                   help="抖动滤波：one_euro=1€ 自适应低通（默认）；ema=对增量一阶低通")
    p.add_argument("--one-euro-min-cutoff", type=float, default=1.2, help="1€ 最小截止频率 (Hz)")
    p.add_argument("--one-euro-beta", type=float, default=0.5, help="1€ 速度系数")
    p.add_argument("--one-euro-d-cutoff", type=float, default=1.0, help="1€ 速度低通截止 (Hz)")
    p.add_argument("--vio-alpha", type=float, default=0.3, help="EMA 一阶低通系数（--filter ema）")
    p.add_argument("--silence-s", type=float, default=0.5, help="ZMQ 静默判丢失阈值 (s)")
    p.add_argument("--reloc-jump", type=float, default=1.0, help="世界跳变判重锁阈值 (m)")
    p.add_argument("--reloc-rot", type=float, default=0.35,
                   help="世界旋转跳变判重锁阈值 (rad)")
    p.add_argument("--swap-xz", action=argparse.BooleanOptionalAction, default=True,
                   help="交换平移映射的前后/上下轴（默认开启，--no-swap-xz 恢复原映射）")
    p.add_argument("--flip-x", action=argparse.BooleanOptionalAction, default=True,
                   help="反转前后平移方向（默认开启，--no-flip-x 关闭）")
    p.add_argument("--flip-z", action="store_true",
                   help="把 base 系 z（上下）翻反（标定后上下仍反时的临时修复）")
    p.add_argument("--flip-yaw", action="store_true", help="把 base 系 x/y 一起翻反（180° yaw）")
    p.add_argument("--flip-y", action=argparse.BooleanOptionalAction, default=True,
                   help="把 base 系 y（左右）翻反（默认开：镜向遥操）；--no-flip-y 关闭")
    p.add_argument("--flip-roll", action="store_true", help="把夹爪 roll 方向翻反")
    p.add_argument("--flip-pitch", action=argparse.BooleanOptionalAction, default=True,
                   help="把夹爪 pitch（俯仰，绕 +y 开合轴）翻反（默认开）；--no-flip-pitch 关闭")
    p.add_argument("--flip-rot-yaw", action=argparse.BooleanOptionalAction, default=True,
                   help="把夹爪 yaw（摆头，绕 +x 掌法向）翻反（默认开）；--no-flip-rot-yaw 关闭。"
                        "注意与平移的 --flip-yaw 不同")
    p.add_argument("--handeye-pitch-deg", type=float, default=20.0,
                   help="手眼：相机光轴比夹爪指向低的俯角（度），默认 20")
    # 平滑 / IK / 下发
    p.add_argument("--max-linear", type=float, default=0.15, help="最大平滑平动速度 (m/s)")
    p.add_argument("--max-angular", type=float, default=0.6,
                   help="夹爪滚转(roll)最大平滑转动速度 (rad/s)")
    p.add_argument("--pitch-slew", type=float, default=0.45,
                   help="已废弃：姿态统一用 max-angular 限速")
    p.add_argument("--ik-damping", type=float, default=1e-3, help="已废弃：阻尼在 IK 构造时设定")
    p.add_argument("--lock-joints", type=str, default="", help="已废弃：解耦 IK 恒锁")
    p.add_argument("--cmd-hz", type=float, default=30.0, help="真机启动去准备姿态的下发频率")
    p.add_argument("--control-hz", type=float, default=50.0,
                   help="主循环 + 控制下发频率（默认 50）")
    p.add_argument("--vio-hz", type=float, default=15.0,
                   help="VIO 位姿标称频率，仅首帧估算增量均分份数")
    p.add_argument("--joint-speed", type=float, default=30.0,
                   help="真机每拍单关节最大速度 (deg/s)，经 ZMQ config 下发给 ROS2 侧限幅")
    p.add_argument("--posture-mode", choices=["ready", "home", "off"], default="ready",
                   help="零空间参考姿态；off 用于对照")
    p.add_argument("--posture-q", type=float, nargs=7, default=None,
                   help="显式指定单臂参考关节角(rad)，覆盖 ready/home")
    p.add_argument("--posture-weights", type=float, nargs=7,
                   default=[1.0, 1.0, 1.0, 0.5, 0.3, 0.3, 0.3])
    p.add_argument("--posture-speed", type=float, default=0.15, help="零空间速度预算(rad/s)")
    p.add_argument("--ik-position-tol", type=float, default=0.01, help="最终位置误差上限(m)")
    p.add_argument("--ik-orientation-tol", type=float, default=0.03, help="最终朝向误差上限(rad)")
    p.add_argument("--feedback-timeout", type=float, default=0.5, help="反馈最大年龄(s)")
    p.add_argument("--tracking-error", type=float, default=0.2,
                   help="反馈相对有效指令偏差提示阈值(rad)")
    p.add_argument("--pause-on-tracking-error", action="store_true",
                   help="可选：超过跟随偏差阈值时暂停；默认仅提示")
    p.add_argument("--output-mode", choices=["teaching", "developer"], default="teaching",
                   help="终端输出方案，默认 teaching")
    p.add_argument("--vio-viewer", action="store_true",
                   help="显示 VIO 点云、双目彩色和跟踪图像窗口；默认不显示（仅控制本脚本启动的 VIO）")
    p.add_argument("--log-file", default="",
                   help="详细 JSON 行日志(.log)，默认自动创建；支持 {arm}，双臂自动区分文件")
    # 手持夹爪跟随（仿真 qpos[7] + 真机 gripper）
    p.add_argument("--gripper-channel", default=None,
                   help="手持夹爪 CANable2 SLCAN 设备（默认按 --arm 选 /dev/ttyACM0//dev/ttyACM1）")
    p.add_argument("--gripper-motor-id", type=int, default=None,
                   help="手持 DM3507 电机 CAN id（默认按 --arm 选 7/1）")
    p.add_argument("--gripper-calib", default="", help="手持夹爪标定文件 JSON 路径")
    p.add_argument("--gripper-effort", type=float, default=1.0,
                   help="真机夹爪夹持力矩（OpenArm 指爪为位置控制，此参数仅兼容保留）")
    p.add_argument("--gripper-deadband", type=float, default=0.0005, help="夹爪开度死区 (m)")
    p.add_argument("--no-gripper", action="store_true", help="禁用手持夹爪跟随")
    # 真机启动准备姿态
    p.add_argument("--ready-q", type=float, nargs=7, default=None,
                   metavar=("J1", "J2", "J3", "J4", "J5", "J6", "J7"),
                   help="真机启动后自动去的准备姿态（7 关节角 rad），默认读当前 --arm 的 ready 文件"
                        "（无则内置 [0,0,0,π/2,0,0,0]，大臂向下、小臂向前）")
    p.add_argument("--ready-tol", type=float, default=math.radians(2.0), help="准备姿态到位判定：各关节最大误差 (rad)，默认 2°")
    p.add_argument("--ready-timeout", type=float, default=15.0, help="准备姿态超时 (s)")
    p.add_argument("--no-ready-move", action="store_true", help="跳过自动去准备姿态")
    p.add_argument("--staged", action="store_true",
                   help="分阶段流程：回准备姿态 → VIO 初始化 → Z/X 标定 → 回车开启遥操")
    p.add_argument("--vio-cmd", default="", help="VIO(ORB-SLAM3) 启动命令（--staged 时用）")
    p.add_argument("--vio-log", default="/tmp/cyperstereo_vio.log", help="VIO 进程日志文件")
    p.add_argument("--stop-file", default="", help="共享停止标记文件（双臂同退，单臂留空）")
    p.add_argument("--dual-state", default="",
                   help="双臂协调目录：写 ready/calib 旗标、等 go 旗标，左臂广播共享键")
    return p.parse_args()


def move_arm_to_ready(arm, ready_q: np.ndarray, tol: float, timeout: float,
                      cmd_hz: float) -> np.ndarray:
    """让真机缓慢走到准备姿态（速度受限，限幅在 ROS2 侧），到位返回实际关节角。

    与 piper 版一致：反复 send 同一目标，ROS2 侧平滑逼近；读回关节角判断到位。
    超时则按当前位姿继续，不阻塞遥操启动。
    """
    print("\n" + "=" * 72)
    print(f"[ready] 真机自动前往准备姿态 q=[{', '.join(f'{v:+.3f}' for v in ready_q)}]")
    print("        （每拍受 --joint-speed 速度上限约束（ROS2 侧限幅），到位后以此为 home）")
    print("=" * 72)
    output.last_ready_reached = False
    period = 1.0 / max(cmd_hz, 1.0)
    deadline = time.monotonic() + timeout
    last_print = 0.0
    while time.monotonic() < deadline:
        arm.send(ready_q)
        time.sleep(period)
        try:
            measured, feedback_age = arm.joint_feedback()
        except Exception:
            measured, feedback_age = None, float("inf")
        valid_feedback = (measured is not None and feedback_age <= 0.5
                          and np.asarray(measured).shape == ready_q.shape
                          and np.all(np.isfinite(measured)))
        q = np.asarray(measured, dtype=float) if valid_feedback else None
        err = float(np.max(np.abs(q - ready_q))) if valid_feedback else float("inf")
        now = time.monotonic()
        if now - last_print >= 1.0:
            last_print = now
            if valid_feedback:
                print(f"[ready] 前往准备姿态中… 最大关节误差 {math.degrees(err):.1f}°")
            else:
                print("[warn] 未收到新鲜关节反馈，无法确认准备姿态到位。")
        if err <= tol:
            output.last_ready_reached = True
            print(f"[ready] 已到位（误差 ≤ {math.degrees(tol):.1f}°）")
            return q
    print(f"[warn] 准备姿态超时（{timeout:.0f}s），按当前位姿继续")
    return arm.read_joints()


def _dual_mark(dual_state: Path, name: str, side: str) -> None:
    """双臂协调：写 <dir>/<name>.<side> 旗标（幂等）。"""
    try:
        (dual_state / f"{name}.{side}").write_text("done", encoding="utf-8")
    except OSError:
        pass


def _dual_wait(dual_state: Path, relname: str, stop_file, label: str) -> bool:
    """双臂协调：等 <dir>/<relname> 出现；期间收到停止信号返回 False。"""
    print(f"[dual] 等待 {label} ...")
    while not (dual_state / relname).exists():
        if stop_file and Path(stop_file).exists():
            return False
        time.sleep(0.2)
    return True


def _dual_prepare_gate(dual_state: Path, side: str, stop_file) -> bool:
    """Both cores join before either starts its ready motion; no completion dependency."""
    _dual_mark(dual_state, "prepare", side)
    other = "right" if side == "left" else "left"
    return _dual_wait(dual_state, f"prepare.{other}", stop_file, "两侧控制核心就绪后并行准备")


def _tty_input(prompt: str = "") -> str:
    """从控制终端读一行（阻塞）。

    分阶段标定里的提示（VIO 初始化确认 / Z/X 起终点）必须读终端；但双臂编排脚本
    把遥操核心用 ``&`` 后台拉起，此时 stdin 是 /dev/null（``input()`` 会立刻 EOFError）。
    所以改走 /dev/tty（与 KeyboardReader 同一思路），后台也能正常等待用户回车。
    """
    print(prompt, end="", flush=True)
    try:
        with open("/dev/tty", "r", encoding="utf-8") as tty:
            return tty.readline().rstrip("\n")
    except (OSError, ValueError):
        return input()


def main() -> int:
    global output
    args = parse_args()
    from datetime import datetime
    from uuid import uuid4
    if args.log_file:
        log_path = args.log_file.replace("{arm}", args.arm)
        if (args.dual_state or os.environ.get("OPENARM_DUAL_RUN") == "1") and "{arm}" not in args.log_file:
            original = Path(log_path)
            log_path = str(original.with_name(original.stem + "_" + args.arm + original.suffix))
    else:
        log_path = str(REPO_ROOT / "logs" / (datetime.now().strftime("%Y%m%d_%H%M%S")
                       + "_" + args.arm + "_" + uuid4().hex[:6] + ".log"))
    output = TeleopOutput(args.arm, args.output_mode, log_path)
    output.event("OpenArm 手持夹爪遥操作教学系统", category="startup")
    output.event("双臂遥操作" if args.dual_state else
                 ("左臂遥操作；右臂硬件同时连接并保持" if args.arm == "left" else
                  "右臂遥操作；左臂硬件同时连接并保持") if args.bridge else "离线计算模式", category="startup")
    output.event("准备姿态来源：" + ("命令行指定" if args.ready_q is not None else
                 "默认姿态（大臂向下，小臂与夹爪向前）" if ready_source(args.arm)=="builtin_default" else
                 "自定义准备姿态"), category="ready")
    output.event("详细日志已启用，不生成 CSV。", category="logging",data={"path":log_path})
    output.stage(1, "正在连接机械臂与位姿通道……")
    positive = [args.control_hz, args.joint_speed, args.ik_position_tol,
                args.ik_orientation_tol, args.feedback_timeout, args.tracking_error]
    if not all(np.isfinite(v) and v > 0 for v in positive):
        raise ValueError("控制频率、速度、误差阈值和反馈超时必须有限且为正")
    if (not np.isfinite(args.posture_speed) or args.posture_speed < 0
            or not np.all(np.isfinite(args.posture_weights))
            or np.any(np.asarray(args.posture_weights) < 0)
            or (args.posture_q is not None and not np.all(np.isfinite(args.posture_q)))):
        raise ValueError("姿态参数必须有限，速度和权重必须非负")

    # ---- 左/右臂默认端点/夹爪参数：命令行未显式指定时按 --arm 回填 ----
    _side_defaults = {
        "right": {"endpoint": "tcp://127.0.0.1:5555",
                  "bridge_cmd": "tcp://127.0.0.1:5556",
                  "bridge_fb": "tcp://127.0.0.1:5557",
                  "gripper_channel": "/dev/ttyACM0",
                  "gripper_motor_id": 7},
        "left": {"endpoint": "tcp://127.0.0.1:5565",
                 "bridge_cmd": "tcp://127.0.0.1:5566",
                 "bridge_fb": "tcp://127.0.0.1:5567",
                 "gripper_channel": "/dev/ttyACM1",
                 "gripper_motor_id": 1},
    }
    _sd = _side_defaults[args.arm]
    if args.endpoint is None:
        args.endpoint = _sd["endpoint"]
    if args.bridge_cmd is None:
        args.bridge_cmd = _sd["bridge_cmd"]
    if args.bridge_fb is None:
        args.bridge_fb = _sd["bridge_fb"]
    if args.gripper_channel is None:
        args.gripper_channel = _sd["gripper_channel"]
    if args.gripper_motor_id is None:
        args.gripper_motor_id = _sd["gripper_motor_id"]
    print(f"[arm] 遥操目标：{args.arm} 臂（endpoint={args.endpoint}, "
          f"cmd={args.bridge_cmd}, fb={args.bridge_fb}）")

    # ---- 双臂同退：共享停止标记 + 统一信号处理 ----
    stop_file = args.stop_file or None
    dual_state = Path(args.dual_state) if args.dual_state else None

    def _request_stop() -> None:
        if stop_file:
            try:
                Path(stop_file).write_text("stop", encoding="utf-8")
            except OSError:
                pass

    def _signal_abort(_signum, _frame) -> None:
        _request_stop()
        raise KeyboardInterrupt

    signal.signal(signal.SIGINT, _signal_abort)
    signal.signal(signal.SIGTERM, _signal_abort)
    try:
        signal.signal(signal.SIGHUP, _signal_abort)
    except (ValueError, OSError):
        pass

    # 原调试横幅保留为函数，新版使用统一输出层。

    # ---- VIO 源 ----
    if args.synthetic:
        src = SyntheticVioSource()
        print("[info] --synthetic：脚本化 VIO 位姿（跳过标定，R_BW=单位阵）")
    else:
        src = VioZMQSource(args.endpoint)
        print(f"[vio] 订阅 {args.endpoint}（左目光心位姿，世界 z 上）")

    # ---- Pinocchio IK + 关节限位（URDF 权威）+ home ----
    kine = OpenArmDecoupledIk(side=args.arm, reach_tol=args.ik_position_tol,
                              orientation_tol=args.ik_orientation_tol)
    qmin = kine.qmin
    qmax = kine.qmax
    R_cf = handeye_camera_to_flange(args.handeye_pitch_deg)
    print(f"[handeye] R_CF = Rz(+90°)·Rx(+{args.handeye_pitch_deg:g}°)"
          f"（相机倒装 + 俯视夹爪 {args.handeye_pitch_deg:g}°）")

    # ---- 真机（可选）：真机为主，识别绝对 home 点 ----
    arm = None
    if args.bridge:
        arm = OpenArmBridge(cmd_endpoint=args.bridge_cmd, fb_endpoint=args.bridge_fb,
                            max_joint_speed_deg_s=args.joint_speed, kine=kine)
        # 两侧控制核心均初始化后，一起放行准备动作。
        if dual_state is not None:
            if not _dual_prepare_gate(dual_state, args.arm, stop_file):
                src.close()
                arm.close()
                return 1
        # 自动去准备姿态（大臂向下、小臂及夹爪向前），到位后以此为 home。
        if not args.no_ready_move:
            output.stage(2, "正在移动到准备姿态……")
            ready_q = (np.array(args.ready_q, dtype=float)
                       if args.ready_q is not None else load_ready_q(args.arm))
            ready_q = np.clip(ready_q, qmin, qmax)
            move_arm_to_ready(arm, ready_q, args.ready_tol, args.ready_timeout, args.cmd_hz)
        home_q, T_home = anchor_home_from_arm(arm, kine, args.arm)
        output.event("已取得机械臂关节反馈，并建立遥操作起始位置。", "DONE", "feedback")
        p_fk = T_home.translation
        print(f"[home] 真机绝对 home = FK pos({p_fk[0]:+.3f},{p_fk[1]:+.3f},{p_fk[2]:+.3f}) m")
        try:
            save_home_q(home_q, args.arm)
            print(f"[home] 真机绝对 home 已写入 {home_file(args.arm)}")
        except OSError as exc:
            print(f"[warn] 写 home 失败: {exc}")
        # 双臂：通知对侧本臂准备姿态完成。
        if dual_state is not None:
            _dual_mark(dual_state, "ready", args.arm)
    else:
        # 仅仿真（无真机）：用中性 home（腕部角 0 → 夹爪水平指前）。
        output.stage(2, "离线初始化准备姿态（不连接机械臂）")
        home_q = (np.array(args.ready_q, dtype=float) if args.ready_q is not None
                  else load_ready_q(args.arm))
        home_q = kine.clamp(home_q)
        T_home = kine.fk(home_q)
        print("[home] 离线准备姿态（大臂向下、小臂及夹爪向前）")

    p_home = T_home.translation.copy()

    # 准备姿态（h 键复位目标）：读 cartesian_ready_q_openarm.json（或 --ready-q 显式指定）。
    ready_q = (np.array(args.ready_q, dtype=float)
               if args.ready_q is not None else load_ready_q(args.arm))
    ready_q = np.clip(ready_q, qmin, qmax)
    T_ready = kine.fk(ready_q)
    p_ready = T_ready.translation.copy()
    R_ready = T_ready.rotation.copy()

    output.event("准备配置", category="ready",data={"source":"command_line" if args.ready_q is not None else ready_source(args.arm),
                 "q_rad":ready_q.tolist(), "q_deg":np.degrees(ready_q).tolist()})
    output.stage(3, "正在准备视觉位姿输入……")
    # ---- 分阶段流程（--staged）：回准备姿态 → VIO 启动/初始化 → Z/X 标定 ----
    vio_proc = None
    if args.staged:
        print("\n" + "=" * 72)
        print("[step] 准备动作已结束，将按实际当前位置继续启动。")
        # 两臂准备阶段结束后，各自同时启动 VIO，不再等待对侧标定。
        if dual_state is not None:
            other = "right" if args.arm == "left" else "left"
            if not _dual_wait(dual_state, f"ready.{other}", stop_file, "两臂准备阶段完成"):
                return 1
        if args.vio_cmd:
            output.event("VIO 窗口：" + ("开启。" if args.vio_viewer else "关闭（默认），视觉追踪继续运行。"),
                         category="vio_viewer", data={"enabled": args.vio_viewer})
            print(f"[vio] 启动 VIO 系统: {args.vio_cmd}")
            try:
                _logf = open(args.vio_log, "wb")
            except OSError as exc:
                print(f"[vio] WARN: 无法打开日志 {args.vio_log}: {exc}")
                _logf = None
            vio_proc = subprocess.Popen(
                args.vio_cmd, shell=True, env=vio_environment(args.vio_viewer),
                stdout=_logf, stderr=subprocess.STDOUT,
                start_new_session=True,
            )
            atexit.register(_terminate_process_group, vio_proc)
            print(f"[vio] VIO 进程已启动 (PID {vio_proc.pid})，日志: {args.vio_log}")
            waited = 0.0
            while (vio_proc.poll() is None) and src.latest() is None and waited < 60.0:
                time.sleep(0.5)
                waited += 0.5
            if src.latest() is not None:
                print("[vio] 已收到视觉位姿（仅确认数据接收，不独立判断追踪质量）。")
            elif vio_proc.poll() is not None:
                print(f"[vio] WARN: VIO 进程已退出 (code {vio_proc.poll()})，"
                      f"请查看 {args.vio_log}")
            else:
                print("[vio] WARN: 60s 内未收到位姿，请检查 VIO 日志和相机输入是否完成初始化。")
        else:
            print("[vio] 未提供 --vio-cmd，假设 VIO 已在外部运行。")
        print("=" * 72)

    if dual_state is not None and args.staged:
        # 只有收到新鲜位姿才放行统一确认；失败不留下就绪旗标。
        if src.latest() is None or src.age() > args.silence_s:
            output.event("VIO 未提供有效的新鲜位姿，双臂标定无法开始。", "ERROR", "calibration")
            _terminate_process_group(vio_proc)
            src.close()
            if arm is not None:
                arm.close()
            return 1
        _dual_mark(dual_state, "vio", args.arm)
        if not _dual_wait(dual_state, "calibrate_go", stop_file, "双臂统一标定确认"):
            _terminate_process_group(vio_proc)
            src.close()
            if arm is not None:
                arm.close()
            return 1

    output.stage(4, "方向标定")
    # ---- 启动标定 R_BW ----
    if args.synthetic:
        R_bw = np.eye(3)
    elif args.calibrate:
        R_bw = calibrate_rbw_base(src, R_cf,
                                  confirm=dual_state is None,
                                  max_age=args.silence_s if dual_state is not None else None)
        if R_bw is None:
            src.close()
            if arm is not None:
                arm.close()
            return 1
        if args.rbw_output:
            try:
                Path(args.rbw_output).write_text(
                    "# R_BW (VIO world -> robot base), row-major 3x3\n"
                    "rotation: [" + ", ".join(f"{v:.6f}" for v in R_bw.flatten()) + "]\n",
                    encoding="utf-8",
                )
                print(f"R_BW 已写入 {args.rbw_output}")
            except OSError as exc:
                print(f"[warn] 写 R_BW 失败: {exc}")
    else:
        R_bw = np.eye(3)
        print("[info] --no-calibrate：R_BW=单位阵")

    # 双臂：两侧分别计算标定，通知编排脚本本侧完成。
    if dual_state is not None:
        _dual_mark(dual_state, "calib", args.arm)

    output.event("有效配置", category="configuration", data={
        "control_hz":args.control_hz,"command_hz":args.cmd_hz,"arm":args.arm,
        "endpoints":{"vio":args.endpoint,"command":args.bridge_cmd,"feedback":args.bridge_fb},
        "mapping":{"R_BW":R_bw.tolist(),"R_CF":R_cf.tolist(),"swap_xz":args.swap_xz,
                   "flip_x":args.flip_x,"flip_y":args.flip_y,"flip_z":args.flip_z,
                   "flip_yaw":args.flip_yaw,"scale":args.scale,
                   "xyz_gain":[args.x_gain,args.y_gain,args.z_gain],
                   "flip_roll":args.flip_roll,"flip_pitch":args.flip_pitch,
                   "flip_rot_yaw":args.flip_rot_yaw},
        "ik":{"backend":"pinocchio_dls","seed":"previous_accepted_command",
              "position_tol_m":args.ik_position_tol,"orientation_tol_rad":args.ik_orientation_tol,
              "joint_speed_deg_s":args.joint_speed,"posture_mode":args.posture_mode,
              "posture_weights":args.posture_weights,"posture_speed_rad_s":args.posture_speed},
        "feedback":{"timeout_s":args.feedback_timeout,"tracking_warn_rad":args.tracking_error,
                    "pause_on_tracking_error":args.pause_on_tracking_error}})
    output.stage(5, "准备开始遥操作")
    # ---- 分阶段流程（--staged）：Z/X 标定完成 → 回车开启遥操 ----
    if args.staged:
        if dual_state is not None:
            # 双臂：等编排脚本确认回车后统一开遥操。
            print("\n[dual] 本臂标定完成，等待编排脚本回车后双臂同步开遥操 ...")
            if not _dual_wait(dual_state, "go", stop_file, "编排脚本回车（go）"):
                _terminate_process_group(vio_proc)
                src.close()
                if arm is not None:
                    arm.close()
                print("\n[exit] 已退出（等待 go 阶段）。")
                return 1
        else:
            try:
                _tty_input("\n[step] Z/X 标定完成。按回车开启遥操 "
                           "（空格=离合冻结  h=回准备姿态  s=记录准备姿态  esc=急停）...")
            except (KeyboardInterrupt, EOFError):
                _terminate_process_group(vio_proc)
                src.close()
                if arm is not None:
                    arm.close()
                print("\n[exit] 已退出（标定完成阶段）。")
                return 1

    # ---- 手持夹爪（可选）：非 ROS 读开度 -> 仿真 qpos[7] + 真机 gripper ----
    handheld = None
    gripper_max_m = arm.gripper_max_m if arm is not None else 0.044
    if args.no_gripper:
        output.event("已按参数跳过夹爪开合跟随，机械臂位姿遥操作继续。",category="gripper")
    else:
        output.event("正在连接手持夹爪……", category="gripper")
        try:
            handheld = HandheldGripper(channel=args.gripper_channel,
                                       motor_id=args.gripper_motor_id,
                                       calib_file=args.gripper_calib or None)
            deadline = time.monotonic() + 1.0
            while handheld.pct() is None and time.monotonic() < deadline:
                time.sleep(0.02)
            if handheld.pct() is None:
                handheld.close()
                handheld = None
                raise TimeoutError("串口已打开，但未收到手持夹爪有效开度反馈")
            output.event("手持夹爪已连接，开合跟随已启用。", "DONE", "gripper",
                         {"device":args.gripper_channel,"motor_id":args.gripper_motor_id})
        except Exception as exc:
            handheld = None
            output.event("未连接手持夹爪，已自动跳过开合跟随，机械臂位姿遥操作继续启动。",
                         "WARN", "gripper", {"device":args.gripper_channel,"error":str(exc)})

    # ---- 目标 / 当前状态 ----
    # 位置用 p 向量、姿态用完整旋转矩阵 R 跟踪（6D），初始 = home 位姿。
    p_target = p_home.copy()
    R_target = T_home.rotation.copy()
    p_cur = p_home.copy()
    R_cur = T_home.rotation.copy()
    q_prev = home_q.copy()
    kine.reset(q_prev)
    posture_ref = (np.array(args.posture_q) if args.posture_q is not None
                   else (home_q if args.posture_mode == "home" else ready_q))
    kine.set_posture(posture_ref, args.posture_weights,
                     speed=0.0 if args.posture_mode == "off" else args.posture_speed)
    # ---- 键盘（交互式才启用；--steps 的 headless 模式不读键）----
    # 双臂：左臂是「键主」，独占 /dev/tty 并广播到共享键文件；右臂只读该文件，
    # 避免两个进程同时 raw /dev/tty 抢同一按键。
    kb = None
    if args.steps == 0 and not (dual_state is not None and args.arm == "right"):
        try:
            kb = KeyboardReader()
            kb.start()
        except Exception:
            kb = None

    relay = KeyRelay(dual_state / "keys.json") if dual_state is not None else None
    tick_period = 1.0 / args.control_hz
    last_status = 0.0
    estop = False
    tick = 0

    T_prev: Optional[np.ndarray] = None
    last_T: Optional[np.ndarray] = None
    last_seq = -1

    vio_period_est = 1.0 / args.vio_hz
    last_frame_arrival = time.monotonic()
    inc_buf = np.zeros(6)
    inc_remaining = 0
    disp_dp = np.zeros(3)
    last_gripper_w: Optional[float] = None
    run_counts = {"accepted_steps":0, "rejected_steps":0, "max_tracking_error_rad":0.0}

    pose_filter = PoseFilter(args)
    T_filt_prev: Optional[np.ndarray] = None
    if args.filter == "one_euro":
        print(f"[filter] 1€ 自适应低通（抖动滤波）：min_cutoff={args.one_euro_min_cutoff:g}Hz "
              f"beta={args.one_euro_beta:g} d_cutoff={args.one_euro_d_cutoff:g}Hz")
    else:
        print(f"[filter] EMA 一阶低通：alpha={args.vio_alpha:g}")
    output.event("操作按键：Space 暂停/恢复；H 返回准备末端位姿；S 保存自定义姿态；"
                 "R 恢复默认配置（不移动）；Esc 软件急停；Ctrl+C 退出并尝试返回准备姿态。",
                 category="keyboard")

    clutch = False
    space_prev = False
    last_clutch_toggle = 0.0

    def reanchor(T: np.ndarray) -> None:
        nonlocal T_prev, last_T
        T_prev = T.copy()
        last_T = T.copy()

    def step_toward() -> None:
        nonlocal p_cur, R_cur
        dp = p_target - p_cur
        step_p = dp * 0.1
        sp = float(np.linalg.norm(step_p))
        lim = args.max_linear * tick_period
        if sp > lim:
            step_p = step_p / sp * lim
        p_cur = p_cur + step_p

        # 姿态平滑：R_cur -> R_target，旋转向量指数趋近 + 角速度限幅。
        rv_err = so3_log(R_cur.T @ R_target)
        rv_step = rv_err * 0.1
        n = float(np.linalg.norm(rv_step))
        lim_ang = args.max_angular * tick_period
        if n > lim_ang:
            rv_step = rv_step / n * lim_ang
        R_cur = R_cur @ _exp_so3(rv_step)

    try:
        next_tick = time.monotonic()
        while True:
            now = time.monotonic()

            # --- 双臂同退 ---
            if stop_file and Path(stop_file).exists():
                print("\n[exit] 检测到另一臂退出信号，回准备姿态并退出…")
                break

            # --- 键盘：离合 / 复位 / 急停（双臂：左臂键主广播，右臂读共享键文件）---
            keys: list = []
            if kb is not None:
                keys = kb.read_keys()
                if relay is not None and args.arm == "left":
                    try:
                        relay.publish(keys)
                    except OSError as exc:
                        output.event("双臂按键广播失败。", "ERROR", "keyboard", {"error":str(exc)})
            elif relay is not None and args.arm == "right":
                keys = relay.consume()

            space_now = " " in keys
            if space_now and not space_prev and \
                    (time.monotonic() - last_clutch_toggle) > 0.4:
                clutch = not clutch
                last_clutch_toggle = time.monotonic()
                print(f"[clutch] {'冻结：不跟随、不累积增量（再按空格恢复）' if clutch else '恢复跟随'}")
                T_prev = None
                last_T = None
                T_filt_prev = None
                pose_filter.reset()
                inc_buf = np.zeros(6)
                inc_remaining = 0
                if arm is not None and not clutch:
                    feedback, age = arm.joint_feedback()
                    if feedback is not None and age <= args.feedback_timeout:
                        q_prev = kine.clamp(feedback)
                        kine.reset(q_prev)
                        anchor = kine.fk(q_prev)
                        p_cur = anchor.translation.copy()
                        R_cur = anchor.rotation.copy()
                        p_target = p_cur.copy()
                        R_target = R_cur.copy()
            space_prev = space_now
            for key in keys:
                if key == "h":
                    p_target = p_ready.copy()
                    R_target = R_ready.copy()
                    # 保持当前构型与平滑状态，逐步返回准备位姿。
                    kine.reset(q_prev)
                    inc_buf = np.zeros(6)
                    inc_remaining = 0
                    if estop and arm is not None:
                        arm.resume()
                    estop = False
                    cur = src.latest()
                    if cur is not None:
                        reanchor(cur)
                    print("[reset] 回到准备姿态，重锁参考")
                elif key in ("s", "r"):
                    try:
                        if key == "s":
                            if arm is None:
                                output.event("无真机反馈，跳过保存自定义姿态。", "WARN", "ready")
                                continue
                            measured, measured_age = arm.joint_feedback()
                            if measured is None or measured_age > args.feedback_timeout:
                                output.event("关节反馈不新鲜，未保存准备姿态。", "WARN", "ready")
                                continue
                            new_ready = kine.clamp(measured)
                            save_ready_q(new_ready, args.arm)
                        else:
                            new_ready = restore_default_ready_q(args.arm)
                        ready_q = new_ready.copy()
                        T_ready = kine.fk(ready_q)
                        p_ready, R_ready = T_ready.translation.copy(), T_ready.rotation.copy()
                        if args.posture_mode == "ready" and args.posture_q is None:
                            kine.set_posture(ready_q, args.posture_weights, args.posture_speed)
                        output.event("当前姿态已保存，H 返回目标和下次启动准备姿态已更新。" if key == "s" else
                                     "自定义姿态已清除，恢复默认：大臂向下、小臂和夹爪向前。当前位置不变，按 H 返回。",
                                     "DONE", "ready", {"q_rad":ready_q.tolist(),"immediate_motion":False,
                                     "source":"custom" if key=="s" else "builtin_default"})
                    except (OSError, ValueError) as exc:
                        output.event("准备姿态保存/恢复失败，保留原配置。", "ERROR", "ready", {"error":str(exc)})
                elif key == "esc":
                    estop = True
                    if arm is not None:
                        arm.emergency_stop()
                    print("[estop] 急停")

            # --- VIO -> 位姿增量（新帧：算增量并压入均分缓冲）---
            T_cur, seq = src.latest_with_seq()
            new_frame = (seq != last_seq) and (T_cur is not None)
            if new_frame:
                if last_seq >= 0:
                    period = now - last_frame_arrival
                    if period > 0.001:
                        vio_period_est = 0.9 * vio_period_est + 0.1 * period
                last_frame_arrival = now
                last_seq = seq
            else:
                if src.age() > args.silence_s and T_prev is not None:
                    output.record("vision_silence", age_s=float(src.age()))
                    T_prev = None
                    last_T = None

            # --- 逐帧增量（仅新帧；姿态增量为局部旋转向量，重锁帧为 0）---
            if new_frame:
                rot_inc = np.zeros(3)
                t_frame = now

                if clutch:
                    delta_p = np.zeros(3)
                else:
                    reanchored = False
                    if T_prev is None:
                        reanchor(T_cur)
                        reanchored = True
                    elif last_T is not None:
                        dtrans = float(np.linalg.norm(T_cur[:3, 3] - last_T[:3, 3]))
                        drot = float(np.linalg.norm(
                            so3_log(last_T[:3, :3].T @ T_cur[:3, :3])))
                        if dtrans > args.reloc_jump or drot > args.reloc_rot:
                            print(f"[warn] VIO 世界跳变（平移 {dtrans:.3f}m / "
                                  f"旋转 {math.degrees(drot):.1f}°），重锁参考")
                            reanchor(T_cur)
                            reanchored = True
                    if reanchored:
                        pose_filter.reset()

                    T_filt = (pose_filter.filter_pose(t_frame, T_cur)
                              if args.filter == "one_euro" else T_cur)

                    if T_filt_prev is None:
                        T_filt_prev = T_filt.copy()
                        delta_p = np.zeros(3)
                    else:
                        dt = T_filt[:3, 3] - T_filt_prev[:3, 3]
                        dR_local = T_filt_prev[:3, :3].T @ T_filt[:3, :3]
                        rv = so3_log(dR_local)
                        if float(np.linalg.norm(dt)) < args.trans_deadzone:
                            dt = np.zeros(3)
                        delta_p = args.scale * (R_bw @ dt)
                        # 实测前后/上下对应互换：在符号与轴增益之前修正平移通道。
                        if args.swap_xz:
                            delta_p = delta_p[[2, 1, 0]]
                        rv_f = R_cf @ rv
                        # 法兰局部旋转向量分量序 [yaw, pitch, roll]：
                        #   rv_f[0] 绕 +x(掌法向) yaw，rv_f[1] 绕 +y(开合) pitch，rv_f[2] 绕 +z(approach) roll。
                        rot_inc = rv_f.copy()
                        if abs(rot_inc[2]) < args.rot_deadzone:      # roll
                            rot_inc[2] = 0.0
                        if abs(rot_inc[1]) < args.pitch_deadzone:    # pitch
                            rot_inc[1] = 0.0
                        if abs(rot_inc[0]) < args.rot_deadzone:      # yaw
                            rot_inc[0] = 0.0
                        if args.flip_roll:
                            rot_inc[2] = -rot_inc[2]
                        if args.flip_pitch:
                            rot_inc[1] = -rot_inc[1]
                        if args.flip_rot_yaw:
                            rot_inc[0] = -rot_inc[0]
                        rot_inc[1] = args.pitch_gain * rot_inc[1]
                        if args.flip_x:
                            delta_p[0] = -delta_p[0]
                        if args.flip_z:
                            delta_p[2] = -delta_p[2]
                        if args.flip_yaw:
                            delta_p[0] = -delta_p[0]
                            delta_p[1] = -delta_p[1]
                        if args.flip_y:
                            delta_p[1] = -delta_p[1]
                        delta_p[0] = args.x_gain * delta_p[0]
                        delta_p[1] = args.y_gain * delta_p[1]
                        delta_p[2] = args.z_gain * delta_p[2]
                        T_filt_prev = T_filt.copy()

                    T_prev = T_cur.copy()
                    last_T = T_cur.copy()

                if args.filter == "ema":
                    delta_p, rot_inc = pose_filter.filter_inc(delta_p, rot_inc)

                inc_buf = np.array([delta_p[0], delta_p[1], delta_p[2],
                                    rot_inc[0], rot_inc[1], rot_inc[2]],
                                   dtype=np.float64)
                inc_remaining = max(1, int(round(vio_period_est * args.control_hz)))

            # 反馈只用于跟随监控，避免把陈旧值或目标兜底当实测。
            tracking_error = 0.0
            tracking_lag = False
            feedback_ok = True
            feedback, age = None, float("nan")
            if arm is not None:
                feedback, age = arm.joint_feedback()
                feedback_ok = (feedback is not None and np.all(np.isfinite(feedback))
                               and age <= args.feedback_timeout)
                if feedback_ok:
                    tracking_error = float(np.max(np.abs(feedback - q_prev)))
                    tracking_lag = tracking_error > args.tracking_error
                    if args.pause_on_tracking_error and tracking_lag:
                        feedback_ok = False
            # --- 每 tick 泄放一份增量到目标 ---
            if clutch or estop or not feedback_ok:
                inc_buf = np.zeros(6)
                inc_remaining = 0
                disp_dp = np.zeros(3)
            elif inc_remaining > 0:
                step = inc_buf / inc_remaining
                p_new = p_target + step[:3]
                R_new = R_target @ _exp_so3(step[3:6])
                _, ok_target, _ = kine.ik6d(pin.SE3(R_new, p_new), q_seed=q_prev, commit=False, dt=tick_period)
                if ok_target:
                    p_target = p_new
                    R_target = R_new
                inc_buf -= step
                inc_remaining -= 1
                disp_dp = step[:3].copy()
            else:
                disp_dp = np.zeros(3)

            # --- 平滑轨迹 ---
            previous_p, previous_R = p_cur.copy(), R_cur.copy()
            if not estop and feedback_ok:
                step_toward()

            # 关节变化限制放入求解，失败保持上一条有效指令。
            attempted_p, attempted_R = p_cur.copy(), R_cur.copy()
            q, ok, res = kine.track_step(pin.SE3(R_cur, p_cur), q_seed=q_prev,
                                        dt=tick_period,
                                        max_delta=math.radians(args.joint_speed) * tick_period)
            reason = "accepted"
            if ok and not estop and feedback_ok:
                q_prev = q.copy()
                kine.reset(q_prev)
                achieved = kine.fk(q_prev)
                p_cur, R_cur = achieved.translation.copy(), achieved.rotation.copy()
            else:
                p_cur, R_cur = previous_p, previous_R
                p_target, R_target = p_cur.copy(), R_cur.copy()
                inc_buf = np.zeros(6)
                inc_remaining = 0
                reason = "estop" if estop else ("feedback" if not feedback_ok else "ik_rejected")
            # 夹爪跟随（手持开合百分比 -> 臂夹爪行程：行程不同，按百分比映射）。
            if handheld is not None:
                pct = handheld.pct()
                if pct is not None:
                    w = (pct / 100.0) * gripper_max_m
                    if arm is not None and not estop:
                        if (last_gripper_w is None or
                                abs(w - last_gripper_w) >= args.gripper_deadband):
                            arm.send_gripper(w, args.gripper_effort)
                            last_gripper_w = w

            # --- 真机下发（每 tick = control_hz）---
            if arm is not None and not estop:
                arm.send(q_prev)

            state = ("ESTOP" if estop else "CLUTCH" if clutch else
                     "PAUSED_FEEDBACK" if not feedback_ok else "PAUSED_IK" if not ok else "RUNNING")
            run_counts["accepted_steps" if reason == "accepted" else "rejected_steps"] += 1
            run_counts["max_tracking_error_rad"] = max(run_counts["max_tracking_error_rad"],tracking_error)
            output.transition("control", state, {
                "RUNNING":"遥操作运行中。", "CLUTCH":"手持跟随已暂停，不累积新运动增量。",
                "ESTOP":"软件急停保持；H 解除并返回准备末端位姿。",
                "PAUSED_FEEDBACK":"关节反馈异常，保持上一条位置指令；反馈恢复后自动继续。",
                "PAUSED_IK":"当前目标暂无有效运动步骤，保持指令；请小幅向回移动手持夹爪。"})
            vio_fresh = src.age() <= args.silence_s
            output.transition("vision", "normal" if vio_fresh else "interrupted", {
                "normal":"视觉位姿更新正常。", "interrupted":"视觉位姿更新中断，等待新位姿重新建立参考。"})
            output.transition("tracking", "lag" if tracking_lag else "normal", {
                "normal":"跟随偏差在提示阈值内。", "lag":"跟随偏差超过阈值。"})
            if now - last_status >= 1.0:
                last_status = now
                diag = kine.last_diagnostics
                pct = handheld.pct() if handheld is not None else None
                def pose_dict(T):
                    return {"position_m":T.translation.tolist(),
                            "quaternion_xyzw":pin.Quaternion(T.rotation).coeffs().tolist()}
                q_measured = feedback if feedback is not None and np.all(np.isfinite(feedback)) else None
                metrics = dict(state=state, ik=reason, vio_fresh=vio_fresh,
                               vio_age_s=float(src.age()) if np.isfinite(src.age()) else None,
                               feedback_ok=feedback_ok, hardware_connected=arm is not None,
                               feedback_age_s=float(age) if np.isfinite(age) else None,
                               position_error_m=res, orientation_error_rad=diag["orientation_error_rad"],
                               max_joint_delta_rad=diag["max_joint_delta_rad"], tracking_error_rad=tracking_error,
                               step_fraction=diag.get("step_fraction",0),
                               gripper="disabled" if handheld is None else "unavailable" if pct is None else f"{pct:.0f}%")
                telemetry = dict(q_measured=None if q_measured is None else q_measured.tolist(),
                                 q_command=q_prev.tolist(),
                                 ee_measured=None if q_measured is None else pose_dict(kine.fk(q_measured)),
                                 ee_command=pose_dict(kine.fk(q_prev)),
                                 ee_target=pose_dict(pin.SE3(R_target,p_target)),
                                 ee_attempted=pose_dict(pin.SE3(attempted_R,attempted_p)), tick=tick)
                output.status(metrics, telemetry)

            tick += 1
            if args.steps and tick >= args.steps:
                break

            next_tick += tick_period
            sleep = next_tick - time.monotonic()
            if sleep > 0:
                time.sleep(sleep)
            else:
                next_tick = time.monotonic()
    except KeyboardInterrupt:
        print("\n[exit] Ctrl+C：退出中…")
    finally:
        output.summary.update(ticks=tick, estop=estop, **run_counts)
        output.record("control_summary", ticks=tick, estop=estop, **run_counts)
        _request_stop()
        _terminate_process_group(vio_proc)
        if kb is not None:
            kb.stop()
        src.close()
        if handheld is not None:
            handheld.close()
        if arm is not None:
            if estop:
                try:
                    arm.freeze()
                except Exception:
                    arm.close()
                output.summary["shutdown_result"] = "estop_held"
                print("[real arm] 急停保持（未解除急停，已冻结）")
            else:
                try:
                    move_arm_to_ready(arm, ready_q, args.ready_tol,
                                      args.ready_timeout, args.cmd_hz)
                    arm.freeze()
                    if output.last_ready_reached:
                        output.summary["shutdown_result"] = "returned_and_held"
                        output.event("已返回准备姿态并保持位置。", "DONE", "shutdown")
                    else:
                        output.summary["shutdown_result"] = "ready_timeout_held"
                        output.event("返回准备姿态超时，已保持最后位置指令。", "WARN", "shutdown")
                except Exception as exc:
                    output.summary["shutdown_result"] = "return_failed"
                    print(f"[exit] 回准备姿态失败（{exc}），断开")
                    try:
                        arm.close()
                    except Exception:
                        pass

    q_final = np.asarray(q_prev)
    print(f"\n[tick {tick}] final q=[{', '.join(f'{v:+.3f}' for v in q_final)}] "
          f"{'IN-LIMITS' if np.all(q_final >= qmin - 1e-6) and np.all(q_final <= qmax + 1e-6) else 'OUT-OF-LIMITS'}")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:
        import traceback
        output.record("exception", traceback=traceback.format_exc())
        output.event("启动或运行失败，请检查详细日志。", "ERROR", "system",
                     {"type":type(exc).__name__,"error":str(exc)})
        output.summary["shutdown_result"] = "error"
        sys.exit(1)
    finally:
        output.close()
