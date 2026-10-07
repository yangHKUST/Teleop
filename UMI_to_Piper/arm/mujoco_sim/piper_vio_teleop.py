#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""VIO（ORB_SLAM3-Cyperstereo，左目光心世界）→ 松灵(Piper) 机械臂 增量式遥操（非 ROS）。

**无 ROS**：直接订阅 ORB_SLAM3 ``cyperstereo_online`` 经 ZMQ PUB 发布的 6DoF 位姿
（``tcp://127.0.0.1:5555``，每帧一行 ``"<ts> <tx> <ty> <tz> <qx> <qy> <qz> <qw>"``，
q 为 R_wc（相机→世界，xyzw），t 为相机在 VIO 世界中的位置）。不再经过
``vio_odom_bridge`` / ``flange_odom_republisher`` / ``agx_arm_teleop``。

本体坐标系 = **左目光心系 C_L 扶正到 VIO 世界**（VIO 世界本就重力对齐、z 上，yaw 为
任意规范自由度）。需要三个变换：

  * ``T_W←C_L``：VIO 直接给出（leveling 已由 ORB-SLAM3 IMU 初始化完成）。
  * ``R_CF``（camera→flange 手眼）：相机在夹爪上方、俯视夹爪，光轴比夹爪指向(approach)
    低 ``--handeye-pitch-deg`` 度（默认 20°）。相机光心系 = OpenCV（x 右/y 下/z 前），
    法兰系 = 中性位形下 +z=approach、+y=左(俯仰轴)、+x=下；二者相差一个绕光轴的 -90°
    滚转 + 一个 -20° 俯仰：``R_CF = Rz(-90°)·Rx(-handeye_pitch_deg)``。
  * ``R_BW``（world→base）：**启动标定**。VIO 初始化后，手持夹爪沿机械臂 base 系三轴
    （+X 前 / +Y 左 / +Z 上）分别推动，测出 base 三轴在 VIO 世界中的方向 →
    Gram-Schmidt → ``R_WB``（列 = base 轴在世界系），``R_BW = R_WBᵀ``。

增量遥操（对漂移一阶免疫；位置在 base 系、姿态在末端夹爪局部系）：
  * 逐帧差：``Δ_t = p_W(t) - p_W(t-1)``，``Δ_R_local = R_WC(t-1)ᵀ · R_WC(t)``
  * 位置（base 系，左乘 R_BW）：``delta_p = scale · R_BW · Δ_t``，``p_target ← p_target + delta_p``
  * 姿态：``rv_f = R_CF · so3_log(Δ_R_local)`` 映射到法兰系，取法兰 +z(approach)=roll→
    joint6、+y(俯仰轴)=pitch→joint5，yaw 丢弃（跟随摆臂），``roll_target/pitch_target``
    逐帧累加。
  * 跟踪丢失（ZMQ 静默）或世界跳变时重新锁参考帧，不产生跳变。

真机 + MuJoCo 数字孪生同步；末端位置走有界平滑 + **解耦逆解**（``piper_urdf_ik.py``，
URDF 建模：joint1/2/3 位置数值 IK + joint5/6 腕部直接映射，规避 home 位形腕部奇异），
真机端下发 ``JointCtrl``。运动控制用 ``piper_umi_core.PiperArm``（piper_sdk python-can
直驱），替换原松灵自带运动学库。

运行（piper_pinocchio conda env、unset PYTHONPATH，用 run_vio_teleop.sh）：
    ./arm/mujoco_sim/run_vio_teleop.sh                        # VIO + MuJoCo（先标定 R_BW）
    ./arm/mujoco_sim/run_vio_teleop.sh --can can0             # + 真机
    ./arm/mujoco_sim/run_vio_teleop.sh --no-calibrate         # 跳过标定，R_BW=单位阵
    ./arm/mujoco_sim/run_vio_teleop.sh --synthetic --no-viewer --steps 300  # 离线冒烟
"""

from __future__ import annotations

import argparse
import atexit
import importlib
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

# Repo root + 本目录（piper_pinocchio / piper_umi_core）。
REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import mujoco  # noqa: E402
from piper_pinocchio import so3_log  # noqa: E402
from piper_urdf_ik import PiperDecoupledIk  # noqa: E402
from keyboard.keyboard_input import KeyboardReader  # noqa: E402
from piper_umi_core import (  # noqa: E402
    PiperArm, _exp_so3, _mat_to_quat_wxyz,
    load_home_q, save_home_q, anchor_home_from_arm, HOME_FILE, HOME_Q,
    load_ready_q, save_ready_q, READY_FILE,
)
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
    """脚本化 VIO 位姿（无相机冒烟测试）：小幅正弦平动 + 绕 z 摆动。"""

    def __init__(self) -> None:
        self._t0 = time.monotonic()
        self._seq = 0
        self._T = np.eye(4)

    def latest_with_seq(self) -> Tuple[Optional[np.ndarray], int]:
        t = time.monotonic() - self._t0
        self._seq += 1
        T = np.eye(4)
        T[:3, 3] = [
            0.05 * math.sin(2 * math.pi * 0.2 * t),
            0.05 * math.sin(2 * math.pi * 0.13 * t),
            0.03 * math.sin(2 * math.pi * 0.17 * t),
        ]
        T[:3, :3] = _exp_so3(np.array([0.0, 0.0, 0.15 * math.sin(2 * math.pi * 0.1 * t)]))
        self._T = T
        return self._T.copy(), self._seq

    def latest(self) -> Optional[np.ndarray]:
        return self.latest_with_seq()[0]

    def age(self) -> float:
        return 0.0

    def close(self) -> None:
        pass


# ============================================================================
# 启动标定：R_FW（world→flange）与 R_BW（world→base）
# ============================================================================

def record_direction(src, axis: str, desc: str) -> Optional[np.ndarray]:
    """手持夹爪沿 base +axis（desc）平移，返回该方向在 VIO 世界中的单位向量。"""
    input(f"[{axis}] 手持夹爪放到起点（{desc}），回车记录起点位置 ... ")
    T0 = src.latest()
    if T0 is None:
        print("  没有收到 VIO 位姿，请确认 cyperstereo_online 已 tracking")
        return None
    p0 = T0[:3, 3].copy()
    input(f"[{axis}] 沿 base +{axis}（{desc}）平移一段距离，回车记录终点 ... ")
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

    物理安装：相机在夹爪**上方**、**俯视**夹爪，且**倒装**（绕光轴转了 180°，即相机
    "图像右"=物理左、"图像下"=物理上），光轴比夹爪指向(approach)低 ``pitch_deg`` 度
    （默认 20°）。相机光心系 = OpenCV（x 右 / y 下 / z 前）；法兰系在中性位形（夹爪
    水平指前）下 = +z=approach、+y=左(俯仰轴，joint5 轴)、+x=下。二者相差：
      * 一个绕光轴的 +90° 滚转（倒装：相机"图像右"↔法兰"左"、相机"图像下"↔法兰"上"）；
      * 一个 +pitch_deg 俯仰（相机俯视夹爪，光轴低于 approach）。
    故 ``R_CF = Rz(+90°) · Rx(+pitch_deg)``。实测 det=+1、正交。

    （此前误用正装 ``Rz(-90°)·Rx(-20°)``，把俯仰轴与滚转轴各差了 180°，导致
    仰头/低头反向、且绕 approach 的滚转被拆出一半到 yaw 后丢弃。）
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


def calibrate_rbw_base(src) -> Optional[np.ndarray]:
    """测 R_BW（VIO world→base），只用两个无歧义方向：+Z（上）+ +X（前）。

    base 系是右手系（x=前 / y=左 / z=上）。三个轴里「上」由重力唯一确定，「前/左」
    里「左」最容易推反——之前用三轴 Gram-Schmidt + 盲翻轴，一旦推反一个水平轴就会
    把上下/左右翻乱。改成只推 上+前 两个方向，再由 x×y=z ⇒ 前×左=上 ⇒ 左=上×前
    直接导出，右手性恒成立，从根上杜绝「推反一个轴导致别的轴被翻」。
    """
    print("\n" + "=" * 72)
    print("启动标定 R_BW（VIO world → robot base）")
    print("  机械臂保持在 home 位姿不动；手持夹爪沿 base 系两个方向推动：")
    print("    +Z = 上（竖直向上，重力反方向）")
    print("    +X = 前（水平，机械臂末端伸出的方向）")
    print("  （左 = 上×前 自动导出，无需再推左。）")
    print("  每个轴：起点回车 -> 平移 -> 终点回车。")
    print("=" * 72)

    def push(axis: str, desc: str) -> Optional[np.ndarray]:
        while True:
            try:
                d = record_direction(src, axis, desc)
            except (KeyboardInterrupt, EOFError):
                return None
            if d is not None:
                return d

    u = push("Z", "上(up)")
    if u is None:
        return None
    f = push("X", "前(forward)")
    if f is None:
        return None

    # 世界 z 已确认向上（ORB-SLAM3 重力沿 -z），故「上」应指向世界 +z；若指向 -z
    # 说明推反了（向下），自动翻转，保证上下恒正确。
    if float(u[2]) < 0.0:
        print("[fix] 实测 +Z 指向世界 -z（推成了向下？），已自动翻转 +Z。")
        u = -u

    # 把「前」正交化到与「上」垂直（去除手部倾斜），再归一。
    f = f - float(np.dot(f, u)) * u
    nf = float(np.linalg.norm(f))
    if nf < 1e-3:
        print("[fail] +X 方向与 +Z 几乎平行，标定失败，请重试")
        return None
    f = f / nf

    # 左 = 上 × 前（右手系：前×左=上 ⇒ 左=上×前）。
    l = np.cross(u, f)

    R_wb = np.column_stack([f, l, u])  # 列 = base 三轴在世界系（R_WB：base→world）
    R_bw = R_wb.T                       # world→base

    print("\n=== R_BW (VIO world -> robot base), 9 值行主序 ===")
    flat = R_bw.flatten()
    print("rotation: [" + ", ".join(f"{v:.6f}" for v in flat) + "]")
    # 自检：world +z（向上）应映射到 base +z（向上）；「前」推反只会造成 180° yaw，
    # 不会影响上下。
    z_map = R_bw[:, 2]
    x_map = R_bw[:, 0]
    if float(z_map[2]) < 0.0:
        print(f"[warn] world +z → base -z（z {z_map[2]:+.3f}）→ 上下会反向！")
    else:
        print(f"[ok] world +z → base z 分量 {z_map[2]:+.3f}（向上）。")
    print(f"[info] world +x → base 前向 x 分量 {x_map[0]:+.3f}（应 ≈ +1）。")
    print("验证：手持夹爪沿机械臂 +X（前）平移，机械臂末端应沿自身 +X 平移。")
    print("      若前后/左右都反了（180° yaw）→ 前推反了，加 --flip-yaw 或重标定。")
    return R_bw


def _terminate_process_group(proc) -> None:
    """终止 VIO 子进程组。

    ``--vio-cmd`` 用 ``shell=True`` 启动，``proc`` 是 shell，须 ``killpg`` 才能连带
    杀掉它 exec/fork 出来的 ``cyperstereo_online``（否则只剩孤儿进程占着相机/ZMQ）。
    """
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
    print("VIO → Piper 机械臂 增量式遥操（非 ROS · 左目光心世界为本体）")
    print("  平移 <- base 系逐帧增量 Δ_t（scale·R_BW·Δ_t，累加到目标）")
    print("  姿态 <- 夹爪局部 roll/pitch（解耦：roll→joint6, pitch→joint5, yaw 丢弃）")
    print("  真机 + MuJoCo 同步；空格=离合(冻结/跟随)  s=记录当前位姿为准备姿态  h=回准备姿态  esc=急停")
    print("=" * 72)


# ============================================================================
# 手持生理性抖动滤波：1€ 滤波器（Casiez et al. 2012）
# ============================================================================

class _OneEuro:
    """单通道 1€ 自适应低通：静止时用低截止狠压抖动，运动越快截止越高（低延迟）。"""

    def __init__(self, min_cutoff: float, beta: float, d_cutoff: float) -> None:
        self.min_cutoff = float(min_cutoff)   # 最小截止频率 (Hz)
        self.beta = float(beta)               # 速度系数（越大运动时越跟手）
        self.d_cutoff = float(d_cutoff)       # 速度低通截止 (Hz)
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
        # 速度低通（d_cutoff）
        dx = (x - self._x) / dt
        a_d = self._alpha(self.d_cutoff, dt)
        self._dx = a_d * dx + (1.0 - a_d) * self._dx
        # 自适应截止频率
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
    """VIO 位姿/增量滤波。

    one_euro：对**原始位姿**滤波（位置 3 通道 + 相对参考系的旋转向量 3 通道），
      增量从滤波后的位姿差分得到——把抖动挡在差分之前，且运动越快越跟手。
    ema：保持旧行为，对**增量**做一阶低通（--vio-alpha）。
    """

    def __init__(self, args) -> None:
        self.mode = args.filter
        if self.mode == "one_euro":
            self._p = [_OneEuro(args.one_euro_min_cutoff, args.one_euro_beta,
                                args.one_euro_d_cutoff) for _ in range(3)]
            self._r = [_OneEuro(args.one_euro_min_cutoff, args.one_euro_beta,
                                args.one_euro_d_cutoff) for _ in range(3)]
            self._R_ref = None  # 旋转向量滤波的参考系（重锁时刷新）
        else:
            self.ema_dp = np.zeros(3)
            self.ema_roll = 0.0
            self.ema_pitch = 0.0
            self.alpha = args.vio_alpha

    def reset(self) -> None:
        if self.mode == "one_euro":
            for f in self._p + self._r:
                f.reset()
            self._R_ref = None
        else:
            self.ema_dp[:] = 0.0
            self.ema_roll = 0.0
            self.ema_pitch = 0.0

    def filter_pose(self, t: float, T: np.ndarray) -> np.ndarray:
        """one_euro：滤波原始位姿，返回滤波位姿。"""
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

    def filter_inc(self, delta_p, roll_inc, pitch_inc):
        """ema：对增量做一阶低通。"""
        a = self.alpha
        self.ema_dp = a * delta_p + (1.0 - a) * self.ema_dp
        self.ema_roll = a * roll_inc + (1.0 - a) * self.ema_roll
        self.ema_pitch = a * pitch_inc + (1.0 - a) * self.ema_pitch
        return self.ema_dp, self.ema_roll, self.ema_pitch


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="VIO → Piper 机械臂 6D 增量遥操（非 ROS）")
    p.add_argument("--model-file", default=str(Path(__file__).resolve().parent / "piper_h.xml"))
    p.add_argument("--endpoint", default="tcp://127.0.0.1:5555", help="ORB_SLAM3 ZMQ 位姿端点")
    p.add_argument("--synthetic", action="store_true", help="脚本化 VIO 位姿（无相机冒烟）")
    p.add_argument("--can", default="", help="真机 CAN 端口，如 can0（空 = 仅 MuJoCo）")
    p.add_argument("--no-viewer", action="store_true", help="无窗口（headless）")
    p.add_argument("--steps", type=int, default=0, help="headless：跑 N tick 后退出（0=直到退出）")
    # 启动标定
    p.add_argument("--calibrate", action=argparse.BooleanOptionalAction, default=True,
                   help="启动测 R_BW（沿 base +X/+Y/+Z 推手持夹爪）；--no-calibrate 用单位阵")
    p.add_argument("--rbw-output", default="", help="可选：把 R_BW 9 值写到文件")
    # 增量映射 / 死区 / 跟踪丢失
    p.add_argument("--scale", type=float, default=0.51, help="位移缩放（world m → base m）")
    p.add_argument("--pitch-gain", type=float, default=3.0,
                   help="俯仰(pitch)增益，>1 更灵敏（夹爪点头/仰头更跟手）")
    p.add_argument("--y-gain", type=float, default=1.0,
                   help="左右平移增益（base y 分量缩放），>1 左右更灵敏，<1 更钝")
    p.add_argument("--x-gain", type=float, default=1.5,
                   help="前后平移增益（base x 分量缩放），>1 前后更灵敏")
    p.add_argument("--z-gain", type=float, default=1.5,
                   help="上下平移增益（base z 分量缩放），>1 上下更灵敏")
    p.add_argument("--trans-deadzone", type=float, default=0.005, help="平移死区 (m)")
    p.add_argument("--rot-deadzone", type=float, default=0.001,
                   help="滚转(roll)死区 (rad，~0.057°)；VIO 30Hz 下允许 ≥1.7°/s 的慢速滚转")
    p.add_argument("--pitch-deadzone", type=float, default=0.0029,
                   help="俯仰(pitch)死区 (rad，~0.17°)；VIO 30Hz 下允许 ≥5°/s 的慢速俯仰")
    p.add_argument("--filter", choices=["one_euro", "ema"], default="one_euro",
                   help="抖动滤波：one_euro=1€ 自适应低通（默认，对原始位姿滤波）；ema=对增量做一阶低通")
    p.add_argument("--one-euro-min-cutoff", type=float, default=1.2,
                   help="1€ 最小截止频率 (Hz)，静止时越狠压抖动；越小越平滑但越滞后")
    p.add_argument("--one-euro-beta", type=float, default=0.5,
                   help="1€ 速度系数，运动越快截止越高；越大跟手越灵但抖动残留越多")
    p.add_argument("--one-euro-d-cutoff", type=float, default=1.0,
                   help="1€ 速度低通截止频率 (Hz)")
    p.add_argument("--vio-alpha", type=float, default=0.3,
                   help="EMA 一阶低通系数 (0~1)，仅 --filter ema 时生效；越小越平滑但越滞后")
    p.add_argument("--silence-s", type=float, default=0.5, help="ZMQ 静默判丢失阈值 (s)")
    p.add_argument("--reloc-jump", type=float, default=1.0, help="世界跳变判重锁阈值 (m)")
    p.add_argument("--reloc-rot", type=float, default=0.35,
                   help="世界旋转跳变判重锁阈值 (rad)。VIO 地图重置会带来任意朝向跳变（平移可能很小），"
                        "超过即重锁，避免手腕（roll/pitch）被误驱动失控")
    p.add_argument("--flip-z", action="store_true",
                   help="把 base 系 z 方向翻反（标定 z 反导致上下不跟时的临时修复）")
    p.add_argument("--flip-yaw", action="store_true",
                   help="把 base 系 x/y 一起翻反（180° yaw：标定「前」推反导致前后左右都反时的修复）")
    p.add_argument("--flip-y", action=argparse.BooleanOptionalAction, default=True,
                   help="把 base 系 y（左右）翻反（默认开：镜向遥操，手持向左→仿真向右；--no-flip-y 关闭）")
    p.add_argument("--flip-roll", action="store_true",
                   help="把夹爪 roll（绕指向轴）方向翻反")
    p.add_argument("--flip-pitch", action="store_true",
                   help="把夹爪 pitch（绕横轴）方向翻反")
    p.add_argument("--handeye-pitch-deg", type=float, default=20.0,
                   help="手眼：相机光轴比夹爪指向(approach)低的俯角（度），默认 20（相机俯视夹爪）")
    # 平滑 / IK / 下发
    p.add_argument("--max-linear", type=float, default=0.15,
                   help="最大平滑平动速度 (m/s)，内部按 tick 周期换算步长")
    p.add_argument("--max-angular", type=float, default=0.6,
                   help="夹爪滚转(roll)最大平滑转动速度 (rad/s)，内部按 tick 周期换算步长（默认 0.6≈34°/s，对齐真机关节速度）")
    p.add_argument("--pitch-slew", type=float, default=0.45,
                   help="俯仰最大转动速度 (rad/s)，单独放宽使夹爪抬头/低头更快（默认 0.45≈26°/s）")
    p.add_argument("--ik-damping", type=float, default=1e-3, help="解耦 IK 位置雅可比阻尼")
    p.add_argument("--lock-joints", type=str, default="", help="已废弃：解耦 IK 恒锁 joint4")
    p.add_argument("--cmd-hz", type=float, default=30.0, help="真机启动去准备姿态的下发频率")
    p.add_argument("--control-hz", type=float, default=50.0,
                   help="主循环 + 控制下发频率；VIO 帧间增量均分到该节奏（默认 50）")
    p.add_argument("--vio-hz", type=float, default=15.0,
                   help="VIO 位姿标称频率，仅用于首帧估算增量均分份数，之后按实际帧间隔在线修正")
    p.add_argument("--joint-speed", type=float, default=30.0,
                   help="真机每拍单关节最大速度 (deg/s)")
    # 手持夹爪跟随（仿真 qpos[6:8] + 真机 GripperCtrl）
    p.add_argument("--gripper-channel", default="/dev/ttyACM0",
                   help="手持夹爪 CANable2 SLCAN 设备")
    p.add_argument("--gripper-motor-id", type=int, default=7,
                   help="手持 DM3507 电机 CAN id（默认 7，勿与 master id 17 混淆）")
    p.add_argument("--gripper-calib", default="",
                   help="手持夹爪标定文件 JSON 路径（空=用默认共享标定，供零点不同的第二套夹爪使用）")
    p.add_argument("--gripper-effort", type=float, default=1.0,
                   help="真机夹爪夹持力矩 (N·m，0~5)")
    p.add_argument("--gripper-deadband", type=float, default=0.0005,
                   help="夹爪开度死区 (m)，变化小于此值不下发（抑制抖动）")
    p.add_argument("--no-gripper", action="store_true",
                   help="禁用手持夹爪跟随（仿真/真机夹爪都保持不动）")
    # 真机启动准备姿态
    p.add_argument("--ready-q", type=float, nargs=6, default=None,
                   metavar=("J1", "J2", "J3", "J4", "J5", "J6"),
                   help="真机启动后自动去的准备姿态（6 关节角 rad），默认读 cartesian_ready_q.json"
                        "（无则内置 [0,0.7,-0.62,0,0,0]，夹爪水平指前）")
    p.add_argument("--ready-tol", type=float, default=0.02,
                   help="准备姿态到位判定：各关节最大误差 (rad)")
    p.add_argument("--ready-timeout", type=float, default=15.0,
                   help="准备姿态超时 (s)，超时按当前位姿继续（不阻塞遥操）")
    p.add_argument("--no-ready-move", action="store_true",
                   help="跳过自动去准备姿态（以真机当前位姿为 home）")
    p.add_argument("--staged", action="store_true",
                   help="分阶段流程：回准备姿态 → VIO 初始化(提示) → Z/X 标定 → 回车开启遥操")
    p.add_argument("--vio-cmd", default="",
                   help="VIO(ORB-SLAM3) 启动命令；--staged 时在回准备姿态后启动（空=假设 VIO 已在外部运行）")
    p.add_argument("--vio-log", default="/tmp/cyperstereo_vio.log",
                   help="VIO 进程 stdout/stderr 日志文件")
    p.add_argument("--stop-file", default="",
                   help="共享停止标记文件（双臂同退）：本进程退出时写入它通知另一臂；"
                        "主循环检测到该文件也立即回准备姿态并退出。单臂留空则行为不变")
    return p.parse_args()


def move_arm_to_ready(arm, ready_q: np.ndarray, tol: float, timeout: float,
                      cmd_hz: float) -> np.ndarray:
    """让真机缓慢走到准备姿态（速度受限），到位返回实际关节角。

    ``arm.send`` 内部有每拍单关节速度上限，所以反复 send 同一目标即可平滑逼近；
    读回关节角判断是否到位。超时则按当前位姿继续，不阻塞遥操启动。
    """
    print("\n" + "=" * 72)
    print(f"[ready] 真机自动前往准备姿态 q=[{', '.join(f'{v:+.3f}' for v in ready_q)}]")
    print("        （每拍受 --joint-speed 速度上限约束，到位后以此为 home）")
    print("=" * 72)
    period = 1.0 / max(cmd_hz, 1.0)
    deadline = time.monotonic() + timeout
    last_print = 0.0
    while time.monotonic() < deadline:
        arm.send(ready_q)
        time.sleep(period)
        try:
            q = arm.read_joints()
        except Exception:
            q = ready_q.copy()
        err = float(np.max(np.abs(q - ready_q)))
        now = time.monotonic()
        if now - last_print >= 1.0:
            last_print = now
            print(f"[ready] 前往准备姿态中… 最大关节误差 {math.degrees(err):.1f}°")
        if err < tol:
            print(f"[ready] 已到位（误差 < {math.degrees(tol):.1f}°）")
            return q
    print(f"[warn] 准备姿态超时（{timeout:.0f}s），按当前位姿继续")
    return arm.read_joints()


def main() -> int:
    args = parse_args()

    # ---- 双臂同退：共享停止标记 + 统一信号处理 ----
    # Ctrl+C 在遥操主循环里是 KeyboardReader 原始模式读到的 0x03 字节（不是 OS 信号），
    # 在分阶段 input() 里才是真正的 SIGINT。这里统一：
    #   * stop_file：任何退出路径（finally / 信号处理）写入，另一臂主循环检测到即同退。
    #   * SIGINT/SIGTERM/SIGHUP → 写停止标记 + 抛 KeyboardInterrupt，走同一清理路径。
    # 单臂（--stop-file 空）时 stop_file 为 None，逻辑全部退化为「仅本进程清理」。
    stop_file = args.stop_file or None

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

    _print_banner()

    # ---- VIO 源 ----
    if args.synthetic:
        src = SyntheticVioSource()
        print("[info] --synthetic：脚本化 VIO 位姿（跳过标定，R_BW=单位阵）")
    else:
        src = VioZMQSource(args.endpoint)
        print(f"[vio] 订阅 {args.endpoint}（左目光心位姿，世界 z 上）")

    # ---- MuJoCo + Pinocchio + home ----
    model = mujoco.MjModel.from_xml_path(args.model_file)
    data = mujoco.MjData(model)
    qmin = model.jnt_range[:6, 0].copy()
    qmax = model.jnt_range[:6, 1].copy()
    mujoco.mj_resetDataKeyframe(model, data, mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_KEY, "home"))

    kine = PiperDecoupledIk()
    R_cf = handeye_camera_to_flange(args.handeye_pitch_deg)  # 相机光心系→法兰系手眼
    print(f"[handeye] R_CF = Rz(+90°)·Rx(+{args.handeye_pitch_deg:g}°)"
          f"（相机倒装 + 俯视夹爪 {args.handeye_pitch_deg:g}°）")

    # ---- 真机（可选）：真机为主，识别绝对 home 点 ----
    arm = None
    if args.can:
        arm = PiperArm(args.can, max_joint_speed_deg_s=args.joint_speed)
        # 自动去准备姿态（默认 [0,0.7,-0.62,0,0,0]，夹爪水平指前），到位后以此为 home。
        if not args.no_ready_move:
            ready_q = (np.array(args.ready_q, dtype=float)
                       if args.ready_q is not None else load_ready_q())
            ready_q = np.clip(ready_q, qmin, qmax)
            move_arm_to_ready(arm, ready_q, args.ready_tol, args.ready_timeout, args.cmd_hz)
        home_q, T_home = anchor_home_from_arm(arm, kine)
        data.qpos[:6] = np.clip(home_q, qmin, qmax)
        mujoco.mj_forward(model, data)
        p_fk = T_home.translation
        print(f"[home] 真机绝对 home = FK pos({p_fk[0]:+.3f},{p_fk[1]:+.3f},{p_fk[2]:+.3f}) m")
        try:
            save_home_q(home_q)
            print(f"[home] 真机绝对 home 已写入 {HOME_FILE}")
        except OSError as exc:
            print(f"[warn] 写 home 失败: {exc}")
    else:
        # 仅仿真（无真机）：用中性 home（腕部角 0 → 夹爪水平指前）。不读
        # cartesian_home_q.json —— 那是真机绝对 home，可能带腕部下俯（本机曾存过
        # joint5=+0.40 → 夹爪下倾 ~23°），导致仿真夹爪「向下倾斜」。
        home_q = HOME_Q.copy()
        T_home = kine.fk(home_q)
        print("[home] 仿真中性 home（腕部角 0，夹爪水平指前）")

    p_home = T_home.translation.copy()

    # 准备姿态（h 键复位目标）：读 cartesian_ready_q.json（或 --ready-q 显式指定），无则 fallback HOME_Q。
    ready_q = (np.array(args.ready_q, dtype=float)
               if args.ready_q is not None else load_ready_q())
    ready_q = np.clip(ready_q, qmin, qmax)
    T_ready = kine.fk(ready_q)
    p_ready = T_ready.translation.copy()
    roll_ready = ready_q[5]
    pitch_ready = ready_q[4]

    # ---- 分阶段流程（--staged）：回准备姿态 → VIO 启动/初始化 → Z/X 标定 ----
    vio_proc = None
    if args.staged:
        print("\n" + "=" * 72)
        print("[step] 机械臂已到达准备位姿。")
        if args.vio_cmd:
            print(f"[vio] 启动 VIO 系统: {args.vio_cmd}")
            try:
                _logf = open(args.vio_log, "wb")
            except OSError as exc:
                print(f"[vio] WARN: 无法打开日志 {args.vio_log}: {exc}")
                _logf = None
            vio_proc = subprocess.Popen(
                args.vio_cmd, shell=True,
                stdout=_logf, stderr=subprocess.STDOUT,
                start_new_session=True,
            )
            # 任意退出路径都回收 VIO（含标定失败 return 1、Ctrl-C、异常）。
            atexit.register(_terminate_process_group, vio_proc)
            print(f"[vio] VIO 进程已启动 (PID {vio_proc.pid})，日志: {args.vio_log}")
            # 非阻塞等待首帧位姿（VIO tracking 的信号），最多 60s。
            waited = 0.0
            while (vio_proc.poll() is None) and src.latest() is None and waited < 60.0:
                time.sleep(0.5)
                waited += 0.5
            if src.latest() is not None:
                print("[vio] 已收到 VIO 位姿，VIO 已 tracking。")
            elif vio_proc.poll() is not None:
                print(f"[vio] WARN: VIO 进程已退出 (code {vio_proc.poll()})，"
                      f"请查看 {args.vio_log}")
            else:
                print("[vio] WARN: 60s 内未收到位姿，请确认 ORB-SLAM3 窗口是否完成初始化。")
        else:
            print("[vio] 未提供 --vio-cmd，假设 VIO 已在外部运行。")
        print("=" * 72)
        try:
            input("\n[step] 请缓慢移动手持相机完成 VIO 初始化（观察 ORB-SLAM3 窗口 tracking），\n"
                  "       完成后按回车进入 Z/X 标定 ...")
        except (KeyboardInterrupt, EOFError):
            _terminate_process_group(vio_proc)
            src.close()
            if arm is not None:
                arm.close()
            print("\n[exit] 已退出（VIO 初始化阶段）。")
            return 1

    # ---- 启动标定 R_BW ----
    if args.synthetic:
        R_bw = np.eye(3)
    elif args.calibrate:
        R_bw = calibrate_rbw_base(src)
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

    # ---- 分阶段流程（--staged）：Z/X 标定完成 → 回车开启遥操 ----
    if args.staged:
        try:
            input("\n[step] Z/X 标定完成。按回车开启遥操 "
                  "（空格=离合冻结  h=回准备姿态  s=记录准备姿态  esc=急停）...")
        except (KeyboardInterrupt, EOFError):
            _terminate_process_group(vio_proc)
            src.close()
            if arm is not None:
                arm.close()
            print("\n[exit] 已退出（标定完成阶段）。")
            return 1

    # ---- 手持夹爪（可选）：非 ROS 读开度 -> 仿真 qpos[6:8] + 真机 GripperCtrl ----
    handheld = None
    gripper_max_m = arm.gripper_max_m if arm is not None else 0.07
    if args.no_gripper:
        print("[gripper] --no-gripper：禁用夹爪跟随")
    else:
        try:
            handheld = HandheldGripper(channel=args.gripper_channel,
                                       motor_id=args.gripper_motor_id,
                                       calib_file=args.gripper_calib or None)
            print(f"[gripper] 手持夹爪已连接 {args.gripper_channel}，开合百分比映射到臂夹爪行程"
                  f"（0~{gripper_max_m * 1000:.0f} mm）")
        except Exception as exc:
            handheld = None
            print(f"[warn] 手持夹爪不可用（{exc}），跳过夹爪跟随")

    # ---- 目标 / 当前状态 ----
    # 姿态用夹爪局部 roll(joint6)/pitch(joint5) 两个标量跟踪，初始 = home 腕部角。
    p_target = p_home.copy()
    roll_target = home_q[5]
    pitch_target = home_q[4]
    p_cur = p_home.copy()
    roll_cur = home_q[5]
    pitch_cur = home_q[4]
    q_prev = home_q.copy()

    # ---- viewer ----
    viewer = None
    if not args.no_viewer:
        try:
            importlib.import_module("mujoco.viewer")
        except ImportError as exc:
            src.close()
            raise SystemExit(
                f"cannot open viewer: {exc}\n"
                "hint: pip install glfw, 或加 --no-viewer") from exc
        viewer = mujoco.viewer.launch_passive(model, data)

    kb = None
    if not args.no_viewer or args.steps == 0:
        try:
            kb = KeyboardReader()
            kb.start()  # 关键：不进 raw 模式的话空格会被终端行缓冲，只有回车才读得到
        except Exception:
            kb = None

    tick_period = 1.0 / args.control_hz
    last_status = 0.0
    estop = False
    tick = 0

    T_prev: Optional[np.ndarray] = None     # 上一帧相机位姿（逐帧增量的参考）
    last_T: Optional[np.ndarray] = None
    last_seq = -1

    # 增量均分（把每 VIO 帧增量拆到 control_hz 节奏泄放，实现 50Hz 平滑下发）
    vio_period_est = 1.0 / args.vio_hz       # 帧间隔估计 (s)，按实际帧间隔在线修正
    last_frame_arrival = time.monotonic()     # 上一帧到达时刻（monotonic）
    inc_buf = np.zeros(5)                     # [dx,dy,dz, roll_inc, pitch_inc] 待泄放增量
    inc_remaining = 0                         # 剩余泄放 tick 数
    disp_dp = np.zeros(3)                     # 最近一次泄放的平移步长（状态显示用）
    last_gripper_w: Optional[float] = None    # 上次下发真机夹爪开度（死区比较）

    # VIO 抖动滤波（1€ 或 EMA；重锁时复位，避免残留尾迹）
    pose_filter = PoseFilter(args)
    T_filt_prev: Optional[np.ndarray] = None  # 滤波后上一帧（增量用）
    if args.filter == "one_euro":
        print(f"[filter] 1€ 自适应低通（抖动滤波）：min_cutoff={args.one_euro_min_cutoff:g}Hz "
              f"beta={args.one_euro_beta:g} d_cutoff={args.one_euro_d_cutoff:g}Hz")
    else:
        print(f"[filter] EMA 一阶低通：alpha={args.vio_alpha:g}")
    print(f"[control] 主循环/下发 {args.control_hz:g}Hz，VIO 帧间增量均分泄放")

    # 离合（空格切换）：冻结时臂不跟随、不累积增量，保持原位
    clutch = False
    space_prev = False
    last_clutch_toggle = 0.0

    def reanchor(T: np.ndarray) -> None:
        """重锁参考帧（无跳变）：只重置上一帧参考，不清 roll/pitch 目标。"""
        nonlocal T_prev, last_T
        T_prev = T.copy()
        last_T = T.copy()

    def step_toward() -> None:
        """有界平滑逼近 (p_target, roll_target, pitch_target)，速率按 tick 周期换算。"""
        nonlocal p_cur, roll_cur, pitch_cur
        dp = p_target - p_cur
        step_p = dp * 0.1
        sp = float(np.linalg.norm(step_p))
        lim = args.max_linear * tick_period
        if sp > lim:
            step_p = step_p / sp * lim
        p_cur = p_cur + step_p

        droll = roll_target - roll_cur
        roll_cur = roll_cur + float(np.clip(droll * 0.1, -args.max_angular * tick_period,
                                            args.max_angular * tick_period))
        dpitch = pitch_target - pitch_cur
        pitch_cur = pitch_cur + float(np.clip(dpitch * 0.1, -args.pitch_slew * tick_period,
                                              args.pitch_slew * tick_period))

    try:
        next_tick = time.monotonic()
        while (viewer is None) or viewer.is_running():
            now = time.monotonic()

            # --- 双臂同退：另一臂退出（Ctrl+C）时写入共享标记，立即回准备姿态并退出 ---
            if stop_file and Path(stop_file).exists():
                print("\n[exit] 检测到另一臂退出信号，回准备姿态并退出…")
                break

            # --- 键盘：离合 / 复位 / 急停 ---
            if kb is not None:
                keys = kb.read_keys()
                # 离合：空格切换（边沿检测 + 去抖 0.4s，避免按住自动重复反复翻转）
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
                    inc_buf = np.zeros(5)
                    inc_remaining = 0
                space_prev = space_now
                for key in keys:
                    if key == "h":
                        p_target = p_ready.copy()
                        roll_target = roll_ready
                        pitch_target = pitch_ready
                        p_cur = p_ready.copy()
                        roll_cur = roll_ready
                        pitch_cur = pitch_ready
                        q_prev = ready_q.copy()
                        estop = False
                        cur = src.latest()
                        if cur is not None:
                            reanchor(cur)
                        print("[reset] 回到准备姿态，重锁参考")
                    elif key == "s":
                        if arm is not None:
                            q_now = arm.read_joints()
                            try:
                                save_ready_q(q_now)
                                print(f"[save] 准备姿态已写入 {READY_FILE}: "
                                      f"[{', '.join(f'{v:+.4f}' for v in q_now)}] rad")
                            except OSError as exc:
                                print(f"[warn] 写准备姿态失败: {exc}")
                        else:
                            print("[save] 无真机（未加 --can），跳过")
                    elif key == "esc":
                        estop = True
                        if arm is not None:
                            arm.emergency_stop()
                        print("[estop] 急停")

            # --- VIO -> 位姿增量（新帧：算增量并压入均分缓冲）---
            T_cur, seq = src.latest_with_seq()
            new_frame = (seq != last_seq) and (T_cur is not None)
            if new_frame:
                # 在线修正帧间隔估计（首帧跳过）
                if last_seq >= 0:
                    period = now - last_frame_arrival
                    if period > 0.001:
                        vio_period_est = 0.9 * vio_period_est + 0.1 * period
                last_frame_arrival = now
                last_seq = seq
            else:
                # 无新帧：判跟踪丢失（静默）
                if src.age() > args.silence_s and T_prev is not None:
                    print(f"[warn] VIO 静默 {src.age():.2f}s > {args.silence_s}s，跟踪丢失")
                    T_prev = None  # 下一帧到达时 reanchor，避免误动
                    last_T = None

            # --- 逐帧增量（仅新帧；roll/pitch 为局部量，重锁帧为 0）---
            if new_frame:
                roll_inc = 0.0
                pitch_inc = 0.0
                t_frame = now

                if clutch:
                    # 离合冻结：不跟随、不累积，臂保持当前目标；T_prev/T_filt_prev 保持
                    # None（切换时已清），恢复时首帧自动重锁，避免把冻结期间位移甩给臂。
                    delta_p = np.zeros(3)
                else:
                    # 重锁判定用**原始**位姿（不被滤波拖慢）：首帧 / 丢失恢复 / 世界跳变。
                    reanchored = False
                    if T_prev is None:
                        reanchor(T_cur)
                        reanchored = True
                    elif last_T is not None:
                        dtrans = float(np.linalg.norm(T_cur[:3, 3] - last_T[:3, 3]))
                        drot = float(np.linalg.norm(
                            so3_log(last_T[:3, :3].T @ T_cur[:3, :3])))
                        # 地图重置/重定位常表现为「平移很小 + 朝向任意跳变」，只查平移会漏判，
                        # 导致手腕 roll/pitch 被甩出。平移与旋转任一超阈值即重锁。
                        if dtrans > args.reloc_jump or drot > args.reloc_rot:
                            print(f"[warn] VIO 世界跳变（平移 {dtrans:.3f}m / "
                                  f"旋转 {math.degrees(drot):.1f}°），重锁参考")
                            reanchor(T_cur)
                            reanchored = True
                    if reanchored:
                        pose_filter.reset()

                    # 滤波当前帧（1€ 对位姿滤波；EMA 模式不滤位姿，直接透传）
                    T_filt = (pose_filter.filter_pose(t_frame, T_cur)
                              if args.filter == "one_euro" else T_cur)

                    if T_filt_prev is None:
                        T_filt_prev = T_filt.copy()
                        delta_p = np.zeros(3)
                    else:
                        # 位置：世界系差分后映射到 base 系（左乘 R_BW）。
                        dt = T_filt[:3, 3] - T_filt_prev[:3, 3]
                        # 姿态：相机/夹爪局部系增量，分解为 roll/pitch（yaw 丢弃）。
                        dR_local = T_filt_prev[:3, :3].T @ T_filt[:3, :3]
                        rv = so3_log(dR_local)
                        # 平移死区
                        if float(np.linalg.norm(dt)) < args.trans_deadzone:
                            dt = np.zeros(3)
                        delta_p = args.scale * (R_bw @ dt)
                        # 姿态增量：相机光心系 → 法兰系（手眼 R_CF，含俯视 20°），再取法兰
                        # +z(approach)=roll→joint6、+y(俯仰轴)=pitch→joint5；yaw 丢弃（跟随摆臂）。
                        rv_f = R_cf @ rv
                        roll_inc = rv_f[2]   # 法兰 +z（approach）→ joint6（滚转）
                        pitch_inc = rv_f[1]  # 法兰 +y（俯仰轴）→ joint5（俯仰）
                        # 滚转/俯仰各自独立死区（分别映射到法兰系后再判，互不牵连）
                        if abs(roll_inc) < args.rot_deadzone:
                            roll_inc = 0.0
                        if abs(pitch_inc) < args.pitch_deadzone:
                            pitch_inc = 0.0
                        if args.flip_roll:
                            roll_inc = -roll_inc
                        if args.flip_pitch:
                            pitch_inc = -pitch_inc
                        pitch_inc = args.pitch_gain * pitch_inc  # 俯仰更灵敏
                        if args.flip_z:
                            delta_p[2] = -delta_p[2]
                        if args.flip_yaw:
                            delta_p[0] = -delta_p[0]
                            delta_p[1] = -delta_p[1]
                        if args.flip_y:
                            delta_p[1] = -delta_p[1]
                        delta_p[0] = args.x_gain * delta_p[0]  # 前后更灵敏
                        delta_p[1] = args.y_gain * delta_p[1]  # 左右缓解
                        delta_p[2] = args.z_gain * delta_p[2]  # 上下更灵敏
                        T_filt_prev = T_filt.copy()

                    # 原始上一帧推进（供下次跳变判定）
                    T_prev = T_cur.copy()
                    last_T = T_cur.copy()

                # EMA 增量低通（仅 --filter ema；1€ 模式已在位姿级滤过，不再叠加）
                if args.filter == "ema":
                    delta_p, roll_inc, pitch_inc = pose_filter.filter_inc(
                        delta_p, roll_inc, pitch_inc)

                # 压入均分缓冲（不再直接累加 target）
                inc_buf = np.array([delta_p[0], delta_p[1], delta_p[2],
                                    roll_inc, pitch_inc], dtype=np.float64)
                inc_remaining = max(1, int(round(vio_period_est * args.control_hz)))

            # --- 每 tick 泄放一份增量到目标 ---
            if clutch:
                inc_buf = np.zeros(5)
                inc_remaining = 0
                disp_dp = np.zeros(3)
            elif inc_remaining > 0:
                step = inc_buf / inc_remaining
                p_new = p_target + step[:3]
                roll_new = roll_target + step[3]
                pitch_new = pitch_target + step[4]
                # 目标可达性守卫（不可达则本份丢弃，继续泄放剩余）
                _, ok_target, _ = kine.ik(p_new, roll_new, pitch_new)
                if ok_target:
                    p_target = p_new
                    roll_target = roll_new
                    pitch_target = pitch_new
                inc_buf -= step
                inc_remaining -= 1
                disp_dp = step[:3].copy()
            else:
                disp_dp = np.zeros(3)

            # --- 平滑轨迹 ---
            if not estop:
                step_toward()

            # --- 解耦 IK（尽力跟随）---
            q, ok, res = kine.ik(p_cur, roll_cur, pitch_cur)
            q_prev = kine.clamp(q)

            # --- MuJoCo（数字孪生）---
            data.qpos[:6] = np.clip(q_prev, qmin, qmax)
            # 夹爪跟随（手持开合百分比 -> 臂夹爪行程：行程不同，按百分比映射）。
            if handheld is not None:
                pct = handheld.pct()          # 0~100，与各自行程无关的归一化开度
                if pct is not None:
                    w = (pct / 100.0) * gripper_max_m
                    data.qpos[6] = w / 2.0
                    data.qpos[7] = -w / 2.0
                    if arm is not None and not estop:
                        if (last_gripper_w is None or
                                abs(w - last_gripper_w) >= args.gripper_deadband):
                            arm.send_gripper(w, args.gripper_effort)
                            last_gripper_w = w
            if model.nmocap > 0:
                data.mocap_pos[0] = p_target
                data.mocap_quat[0] = _mat_to_quat_wxyz(kine.fk(q_prev).rotation)
            mujoco.mj_forward(model, data)

            # --- 真机下发（每 tick = control_hz）---
            if arm is not None and not estop:
                arm.send(q_prev)

            if viewer is not None:
                viewer.sync()

            if now - last_status >= 1.0:
                last_status = now
                line = (f"Δp=({disp_dp[0]:+.3f},{disp_dp[1]:+.3f},{disp_dp[2]:+.3f}) m "
                        f"p=({p_cur[0]:+.3f},{p_cur[1]:+.3f},{p_cur[2]:+.3f}) "
                        f"roll={roll_cur:+.3f} pitch={pitch_cur:+.3f} "
                        f"{'[clutch] ' if clutch else ''}"
                        f"ik={'ok' if ok else 'LIMIT'} res={res:.4f}")
                if arm is not None:
                    pr, rpr = arm.read_end_pose()
                    line += (f" | real=({pr[0]:+.3f},{pr[1]:+.3f},{pr[2]:+.3f}) "
                             f"rpy=({rpr[0]:+.1f},{rpr[1]:+.1f},{rpr[2]:+.1f})°")
                if handheld is not None:
                    pct = handheld.pct()
                    line += f" grip={'--' if pct is None else f'{pct:.0f}%'}"
                print(line)

            tick += 1
            if args.steps and tick >= args.steps:
                break

            # --- 守时到下一个 tick（control_hz）---
            next_tick += tick_period
            sleep = next_tick - time.monotonic()
            if sleep > 0:
                time.sleep(sleep)
            else:
                next_tick = time.monotonic()
    except KeyboardInterrupt:
        print("\n[exit] Ctrl+C：退出中…")
    finally:
        # 双臂同退：先写停止标记通知另一臂，并立即关相机（VIO 子进程），再回位/断开。
        # 放在最前，保证即使下面回位被再次 Ctrl+C 打断，相机也已经关掉。
        _request_stop()
        _terminate_process_group(vio_proc)
        if kb is not None:
            kb.stop()
        src.close()
        if handheld is not None:
            handheld.close()
        if arm is not None:
            if estop:
                # 急停中：保持急停冻结，不解除、不移动，仅断开连接。
                try:
                    arm.freeze()
                except Exception:
                    arm.close()
                print("[real arm] 急停保持（未解除急停，已断开连接）")
            else:
                # 退出前：平滑回准备姿态，到位后冻结（保持使能位置保持，不 disable 以免
                # 重力下垂），让机械臂停在准备姿态而不是停在退出时的任意位姿。
                try:
                    move_arm_to_ready(arm, ready_q, args.ready_tol,
                                      args.ready_timeout, args.cmd_hz)
                    arm.freeze()
                    print("[real arm] 已回准备姿态并冻结（保持使能）")
                except Exception as exc:
                    print(f"[exit] 回准备姿态失败（{exc}），按断电断开")
                    try:
                        arm.close()
                    except Exception:
                        pass
        if viewer is not None:
            viewer.close()

    q_final = np.asarray(data.qpos[:6])
    print(f"\n[tick {tick}] final q=[{', '.join(f'{v:+.3f}' for v in q_final)}] "
          f"{'IN-LIMITS' if np.all(q_final >= qmin - 1e-6) and np.all(q_final <= qmax + 1e-6) else 'OUT-OF-LIMITS'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
