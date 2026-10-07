#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""UMI (手持 IMU 夹爪) → OpenArm v1.0 机械臂 增量式遥操 —— 共享模块。

移植自 ``piper_umi_core.py``，把松灵 Piper（6-DOF、piper_sdk CAN 直驱）换成
OpenArm（7-DOF、ROS2 ros2_control）。本模块只保留与「运动学 / home / 姿态工具」
相关的公共逻辑，**不**直接驱动硬件——真机下发走 ``openarm_bridge.OpenArmBridge``
（ZMQ 客户端，连 ROS2 侧 ``openarm_umi_bridge`` 节点）。

与 Piper 版的差异（只有这些，控制策略逐行一致）：
  * 关节数 6 → 7；home 关节角 / 限位都是 7 维。
  * home/ready 持久化文件改为 ``cartesian_home_q_openarm[_{side}].json`` /
    ``cartesian_ready_q_openarm[_{side}].json``（右臂无后缀、左臂 _left 后缀，
    与 piper 的 6 关节文件分离）。
  * 内置默认 home = ``[0, ±0.8, 0, 1.2, 0, 0, 0]``（右臂 +0.8、左臂 -0.8，
    夹爪水平指前）。

单位约定：真机关节角经 ``/joint_states`` 读回为 rad；末端位姿由 ``openarm_urdf_ik``
FK 得到（body 系），无 piper_sdk 的 0.001mm/0.001deg 缩放。
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np

# 仓库根 + 持久化 home 关节角（与 piper 的 6 关节文件分离，文件名加 _openarm 后缀）。
REPO_ROOT = Path(__file__).resolve().parents[2]

# 内置默认 home：j1=0, j2=±0.8, j3=0, j4=1.2, j5/j6/j7=0（夹爪水平指前）。
# 左右臂镜像：右臂 j2=+0.8、左臂 j2=-0.8（双臂相向布置）。
_ARM_HOME = {
    "right": np.array([0.0, 0.8, 0.0, 1.2, 0.0, 0.0, 0.0]),
    "left":  np.array([0.0, -0.8, 0.0, 1.2, 0.0, 0.0, 0.0]),
}

# 默认准备姿态：大臂竖直向下，小臂及夹爪水平向前，左右臂对称。
_ARM_READY = np.array([0.0, 0.0, 0.0, np.pi / 2, 0.0, 0.0, 0.0])

# 7 关节限位 (rad)，逐项取自 openarm_description 双臂 URDF（与 openarm_urdf_ik.py 的
# model 限位一致）。左右臂只在 j1/j2 上镜像（其余关节对称）。
# 用于文件读入后的 clamp 兜底；主循环里还会用 openarm_urdf_ik.py 的 URDF 限位再 clip 一次（权威来源）。
_ARM_QMIN = {
    "right": np.array([-1.396263, -0.174533, -1.570796, 0.0, -1.570796, -0.785398, -1.570796]),
    "left":  np.array([-3.490659, -3.316125, -1.570796, 0.0, -1.570796, -0.785398, -1.570796]),
}
_ARM_QMAX = {
    "right": np.array([3.490659, 3.316125, 1.570796, 2.443461, 1.570796, 0.785398, 1.570796]),
    "left":  np.array([1.396263, 0.174533, 1.570796, 2.443461, 1.570796, 0.785398, 1.570796]),
}

# 旧名（右臂）兼容别名：供仍按模块常量引用的代码使用。
HOME_Q = _ARM_HOME["right"]
OPENARM_QMIN = _ARM_QMIN["right"]
OPENARM_QMAX = _ARM_QMAX["right"]
HOME_FILE = REPO_ROOT / "cartesian_home_q_openarm.json"
READY_FILE = REPO_ROOT / "cartesian_ready_q_openarm.json"


def _check_side(side: str) -> str:
    """校验 side 参数，返回归一化后的 left/right。"""
    if side not in ("left", "right"):
        raise ValueError(f"side 必须是 left/right，得到 {side!r}")
    return side


def home_file(side: str = "right") -> Path:
    """home 持久化文件（右臂保留旧名，左臂加 _left 后缀）。"""
    side = _check_side(side)
    if side == "left":
        return REPO_ROOT / "cartesian_home_q_openarm_left.json"
    return REPO_ROOT / "cartesian_home_q_openarm.json"


def ready_file(side: str = "right") -> Path:
    """准备姿态持久化文件（右臂保留旧名，左臂加 _left 后缀）。"""
    side = _check_side(side)
    if side == "left":
        return REPO_ROOT / "cartesian_ready_q_openarm_left.json"
    return REPO_ROOT / "cartesian_ready_q_openarm.json"


def default_home_q(side: str = "right") -> np.ndarray:
    """内置中性 home（不读文件）。"""
    return _ARM_HOME[_check_side(side)].copy()


def clamp_to_limits(q: np.ndarray, side: str = "right") -> np.ndarray:
    """把 7 关节角 (rad) clamp 到 OpenArm 限位。"""
    side = _check_side(side)
    return np.clip(np.asarray(q, dtype=float), _ARM_QMIN[side], _ARM_QMAX[side])


# 左右臂镜像的关节符号：j1/j2/j3/j5/j6/j7 取反，j4 不变（j4 轴 +y，镜像后不变）。
# 由 openarm_urdf_ik 左右臂 FK 对比实测确定（见 mirror_q 说明）。
_MIRROR_SIGNS = np.array([-1.0, -1.0, -1.0, 1.0, -1.0, -1.0, -1.0])


def mirror_q(q7: np.ndarray) -> np.ndarray:
    """把 7 关节角镜像到对侧臂（左右臂互为镜像，再次调用即还原）。

    符号由左右臂 FK 实测确定：对任意右臂 q，``left.fk(mirror_q(q))`` 的姿态等于
    右臂 ``right.fk(q)`` 姿态关于 xz 平面（y→-y）的镜像（rot 误差 ≈0）；位置镜像
    存在 ~1cm 的 y 向系统差，源于 ee 指爪 frame 左右臂定义不对称（finger_joint1
    origin 的 -0.005 未镜像），属 URDF 固有，非镜像错误。
    """
    return np.asarray(q7, dtype=float).reshape(7) * _MIRROR_SIGNS


def load_home_q(side: str = "right") -> np.ndarray:
    """返回已保存的 home 关节角（存在则用，否则内置默认）。"""
    side = _check_side(side)
    try:
        arr = json.loads(home_file(side).read_text())
    except (OSError, ValueError, json.JSONDecodeError):
        return default_home_q(side)
    q = np.asarray(arr, dtype=float)
    if q.shape != (7,):
        return default_home_q(side)
    return clamp_to_limits(q, side)


def save_home_q(q: np.ndarray, side: str = "right") -> None:
    """把 home 关节角写回持久化文件。"""
    home_file(side).write_text(
        json.dumps([round(float(v), 6) for v in np.asarray(q, dtype=float).reshape(7)]) + "\n",
        encoding="utf-8",
    )


def default_ready_q(side: str = "right") -> np.ndarray:
    return clamp_to_limits(_ARM_READY.copy(), _check_side(side))


def ready_source(side: str = "right") -> str:
    return "builtin_default" if np.allclose(load_ready_q(side), default_ready_q(side), atol=1e-6) else "custom"


def load_ready_q(side: str = "right") -> np.ndarray:
    """每侧独立覆盖；没有有效文件则使用内置默认，不继承另一侧自定义。"""
    side = _check_side(side)
    try:
        q = np.asarray(json.loads(ready_file(side).read_text()), dtype=float)
        if q.shape == (7,) and np.all(np.isfinite(q)):
            return clamp_to_limits(q, side)
    except (OSError, ValueError, TypeError):
        pass
    return default_ready_q(side)


def save_ready_q(q: np.ndarray, side: str = "right") -> None:
    """原子写入自定义准备姿态。"""
    import os
    import tempfile
    q = np.asarray(q, dtype=float)
    if q.shape != (7,) or not np.all(np.isfinite(q)):
        raise ValueError("准备姿态必须为七个有限关节角")
    q = clamp_to_limits(q, side)
    path = ready_file(side)
    with tempfile.NamedTemporaryFile(mode="w", dir=path.parent, delete=False, encoding="utf-8") as f:
        temporary = Path(f.name)
        f.write(json.dumps(q.tolist()) + "\n")
    try:
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def restore_default_ready_q(side: str = "right") -> np.ndarray:
    """删除本侧自定义文件；默认值来自内置常量，绝不触发运动。"""
    ready_file(side).unlink(missing_ok=True)
    return default_ready_q(side)


def anchor_home_from_arm(arm, kine, side: str = "right"):
    """真机为主：以真机当前关节角（/joint_states 读回）为 home。

    等 ZMQ 反馈到位后读真机关节角 → clamp 到限位 → URDF FK 求 home 位姿。
    返回 (home_q, T_home)。
    """
    home_q = clamp_to_limits(arm.wait_for_joints(), side)
    T_home = kine.fk(home_q)
    return home_q, T_home


# ============================================================================
# 姿态/旋转工具（与 piper_umi_core / piper_pinocchio 同名同义，纯 numpy 自包含）
# ============================================================================

def so3_log(R: np.ndarray) -> np.ndarray:
    """旋转矩阵 -> 旋转向量 (axis * angle)，小角度鲁棒。"""
    R = np.asarray(R, dtype=float)
    cos_t = float(np.clip((np.trace(R) - 1.0) / 2.0, -1.0, 1.0))
    theta = math.acos(cos_t)
    if theta < 1e-9:
        return np.zeros(3)
    skew = np.array([R[2, 1] - R[1, 2], R[0, 2] - R[2, 0], R[1, 0] - R[0, 1]])
    if theta < math.pi - 1e-6:
        axis = skew / (2.0 * math.sin(theta))
        return axis * theta
    w, v = np.linalg.eig(R)
    idx = int(np.argmin(np.abs(w - 1.0)))
    axis = np.real(v[:, idx])
    axis = axis / np.linalg.norm(axis)
    return axis * theta


def _exp_so3(rv: np.ndarray) -> np.ndarray:
    """旋转向量 -> 旋转矩阵（SO3 指数映射，Rodrigues）。"""
    ang = float(np.linalg.norm(rv))
    if ang < 1e-12:
        return np.eye(3)
    k = np.asarray(rv, dtype=float) / ang
    K = np.array([[0.0, -k[2], k[1]], [k[2], 0.0, -k[0]], [-k[1], k[0], 0.0]])
    return np.eye(3) + math.sin(ang) * K + (1.0 - math.cos(ang)) * (K @ K)


def _mat_to_quat_wxyz(R: np.ndarray) -> np.ndarray:
    """3x3 旋转 -> (w,x,y,z) 四元数（MuJoCo 顺序）。"""
    R = np.asarray(R, dtype=float)
    m00, m01, m02 = R[0]
    m10, m11, m12 = R[1]
    m20, m21, m22 = R[2]
    tr = m00 + m11 + m22
    if tr > 0.0:
        s = math.sqrt(tr + 1.0) * 2.0
        w = 0.25 * s
        x = (m21 - m12) / s
        y = (m02 - m20) / s
        z = (m10 - m01) / s
    elif m00 > m11 and m00 > m22:
        s = math.sqrt(1.0 + m00 - m11 - m22) * 2.0
        w = (m21 - m12) / s
        x = 0.25 * s
        y = (m01 + m10) / s
        z = (m02 + m20) / s
    elif m11 > m22:
        s = math.sqrt(1.0 + m11 - m00 - m22) * 2.0
        w = (m02 - m20) / s
        x = (m01 + m10) / s
        y = 0.25 * s
        z = (m12 + m21) / s
    else:
        s = math.sqrt(1.0 + m22 - m00 - m11) * 2.0
        w = (m10 - m01) / s
        x = (m02 + m20) / s
        y = (m12 + m21) / s
        z = 0.25 * s
    return np.array([w, x, y, z], dtype=float)


def _rot_to_rpy_deg(R: np.ndarray) -> np.ndarray:
    """3x3 旋转 -> (roll, pitch, yaw) 度（固定轴 XYZ，即 R = Rz(yaw)·Ry(pitch)·Rx(roll)）。

    仅用于状态显示（等价 piper 版 read_end_pose 的 rpy 反馈，无精度要求）。
    """
    R = np.asarray(R, dtype=float)
    sy = math.sqrt(R[0, 0] ** 2 + R[1, 0] ** 2)
    if sy > 1e-6:
        roll = math.atan2(R[2, 1], R[2, 2])
        pitch = math.atan2(-R[2, 0], sy)
        yaw = math.atan2(R[1, 0], R[0, 0])
    else:
        roll = math.atan2(-R[1, 2], R[1, 1])
        pitch = math.atan2(-R[2, 0], sy)
        yaw = 0.0
    return np.array([math.degrees(roll), math.degrees(pitch), math.degrees(yaw)])
