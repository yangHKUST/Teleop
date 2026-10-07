#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""UMI (手持 IMU 夹爪) → 松灵(Piper) 机械臂 数字孪生遥操 —— 共享模块（绝对式）。

本模块只保留「绝对映射」所需的公共逻辑：真机末端 6D 位姿 / 关节角读回、home 点
识别、Fusion 初始化、以及**有界外无归一化**的 IMU 位移积分。所有标定（方向符号
dir_sign、两者归一化映射 dmax/arm_max、姿态缩放 att_scale、死区标定）都已移除。

绝对式约定（完全映射一致）：
  * MuJoCo ``piper_h.xml`` 按 modified-DH 搭建，``data.qpos[:6]`` == 真机关节角，
    MuJoCo link6 体坐标系 == 真机末端 6D 位姿（与 ``piper_pinocchio.fk`` 逐点一致）。
  * 位移：IMU 积分出的位移 d (m) **1:1** 直接加到 home 上（无归一化、无翻号）。
  * 姿态：Fusion AHRS 姿态角 roll/pitch/yaw **1:1** 直接映射（无翻号、无缩放）。

单位约定与 piper_imu_fusion_sim.py / piper_sdk v0.6.2 完全一致：
  * 真机末端位姿 ``GetArmEndPoseMsgs()``：X/Y/Z 为 0.001mm，RX/RY/RZ 为 0.001deg。
  * 真机关节角 ``GetArmJointMsgs()``：joint_1..6 为 0.001deg。
  * Fusion AHRS：gyro 喂 dps（rad/s × 180/π），acc 喂 g，输出 [w,x,y,z]。
"""

from __future__ import annotations

import json
import math
import time
from pathlib import Path

import numpy as np
import pinocchio as pin

import imufusion  # noqa: E402  (conda piper_pinocchio env)
from piper_pinocchio import clamp_to_limits  # noqa: E402  (同目录)

GRAVITY = 9.81                       # g -> m/s^2
DEG = 180.0 / math.pi                # rad/s -> dps
DEFAULT_GRAVITY_G = np.array([0.0, 0.0, 1.0])  # 静止比力 ~ +1g 沿 +Z（base 系 Z 上）

# 仓库根 + 持久化 home 关节角（与 piper_cartesian_sim / piper_imu_* 共用同一文件）。
REPO_ROOT = Path(__file__).resolve().parents[2]
HOME_FILE = REPO_ROOT / "cartesian_home_q.json"
HOME_Q = np.array([0.0, 0.7, -0.62, 0.0, 0.0, 0.0])

# 启动准备姿态（--can 模式下真机自动前往的初始位姿）。与 cartesian_home_q.json 分离：
# 后者每次 --can 启动都会被真机当前关节角覆盖（anchor_home_from_arm），前者只在用户
# 显式「记录初始位置」时写入（capture_ready_q.py 或遥操 's' 键），不会被自动覆盖。
READY_FILE = REPO_ROOT / "cartesian_ready_q.json"


def load_home_q() -> np.ndarray:
    """返回已保存的 home 关节角（存在则用，否则内置默认）。"""
    try:
        arr = json.loads(HOME_FILE.read_text())
    except (OSError, ValueError, json.JSONDecodeError):
        return HOME_Q.copy()
    q = np.asarray(arr, dtype=float)
    if q.shape != (6,):
        return HOME_Q.copy()
    return clamp_to_limits(q)


def save_home_q(q: np.ndarray) -> None:
    """把 home 关节角写回 cartesian_home_q.json（供无真机/后续程序复用）。"""
    HOME_FILE.write_text(
        json.dumps([round(float(v), 6) for v in np.asarray(q, dtype=float).reshape(6)]) + "\n",
        encoding="utf-8",
    )


def load_ready_q() -> np.ndarray:
    """返回已保存的准备姿态（存在则用，否则内置 HOME_Q）。"""
    try:
        arr = json.loads(READY_FILE.read_text())
    except (OSError, ValueError, json.JSONDecodeError):
        return HOME_Q.copy()
    q = np.asarray(arr, dtype=float)
    if q.shape != (6,):
        return HOME_Q.copy()
    return clamp_to_limits(q)


def save_ready_q(q: np.ndarray) -> None:
    """把准备姿态关节角写回 cartesian_ready_q.json（--can 启动时自动前往）。"""
    READY_FILE.write_text(
        json.dumps([round(float(v), 6) for v in np.asarray(q, dtype=float).reshape(6)]) + "\n",
        encoding="utf-8",
    )


def anchor_home_from_arm(arm, kine):
    """真机为主：以真机当前关节角（绝对编码器读数）为 home。

    读真机关节角 → clamp 到限位 → MDH FK 求 home 位姿。返回 (home_q, T_home)。
    """
    home_q = clamp_to_limits(arm.read_joints())
    T_home = kine.fk(home_q)
    return home_q, T_home


def _exp_so3(rv: np.ndarray) -> np.ndarray:
    """旋转向量 -> 旋转矩阵（SO3 指数映射，Rodrigues）。"""
    ang = float(np.linalg.norm(rv))
    if ang < 1e-12:
        return np.eye(3)
    k = np.asarray(rv, dtype=float) / ang
    K = np.array([[0.0, -k[2], k[1]], [k[2], 0.0, -k[0]], [-k[1], k[0], 0.0]])
    return np.eye(3) + math.sin(ang) * K + (1.0 - math.cos(ang)) * (K @ K)


def _rotx(a: float) -> np.ndarray:
    c, s = math.cos(a), math.sin(a)
    return np.array([[1, 0, 0], [0, c, -s], [0, s, c]])


def _roty(a: float) -> np.ndarray:
    c, s = math.cos(a), math.sin(a)
    return np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]])


def _rotz(a: float) -> np.ndarray:
    c, s = math.cos(a), math.sin(a)
    return np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]])


def quat_to_euler_rot(q_wxyz) -> np.ndarray:
    """Fusion 姿态四元数 [w,x,y,z] -> 旋转矩阵（**绝对式 1:1**，无翻号、无缩放）。

    等价于 Rz(yaw) @ Ry(pitch) @ Rx(roll)，欧拉角取 Fusion 的 zyx 约定。
    """
    e = imufusion.quaternion_to_euler(np.asarray(q_wxyz, dtype=float))  # [roll,pitch,yaw] deg
    roll, pitch, yaw = (math.radians(e[0]), math.radians(e[1]), math.radians(e[2]))
    return _rotz(yaw) @ _roty(pitch) @ _rotx(roll)


def _mat_to_quat_wxyz(R: np.ndarray) -> np.ndarray:
    """3x3 旋转 -> (w,x,y,z) 四元数（MuJoCo 顺序）。"""
    c = pin.Quaternion(R).coeffs()   # pinocchio: (x,y,z,w)
    return np.array([c[3], c[0], c[1], c[2]])


def initialise_umi(src, Rt, ahrs, seconds) -> tuple[np.ndarray, np.ndarray]:
    """静止初始化：测陀螺零偏 + 重力零偏(acc_bias) + 完成 Fusion startup。

    与 ``imu_ball_fusion.initialise`` 一致（喂原始陀螺，startup 完成即提前结束），
    额外同时累加 acc_N 均值作为位移去重力的零偏。返回 (w_bias rad/s, acc_bias g)。
    """
    print("\n" + "=" * 64)
    print(f"Fusion 初始化：保持夹爪**静止**（自然工作姿态），最多 {seconds:g}s，"
          "startup 完成自动继续")
    print("=" * 64)
    gyros, accs = [], []
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        out = src.read_samples()
        if out is None:
            time.sleep(0.005)
            continue
        _, _, samples = out
        for s in samples:
            acc_N = Rt @ np.asarray(s["acc"], dtype=float)
            gyro_N = Rt @ np.asarray(s["gyro"], dtype=float)
            gyros.append(gyro_N)
            accs.append(acc_N)
            ahrs.update_no_magnetometer(gyro_N * DEG, acc_N)   # dps + g
        if not ahrs.get_flags().startup:
            break
    w_bias = np.mean(gyros, axis=0) if gyros else np.zeros(3)
    acc_bias = np.mean(accs, axis=0) if accs else DEFAULT_GRAVITY_G.copy()
    print(f"  gyro 零偏 w_bias = [{w_bias[0]:+.4f}, {w_bias[1]:+.4f}, {w_bias[2]:+.4f}] rad/s")
    print(f"  acc 零偏 bias   = [{acc_bias[0]:+.4f}, {acc_bias[1]:+.4f}, {acc_bias[2]:+.4f}] g "
          f"(期望接近 [0,0,+1])")
    print(f"  startup={'完成' if not ahrs.get_flags().startup else '未完成(静止时间不足)'}")
    print("=" * 64)
    return w_bias, acc_bias


# ============================================================================
# 真机末端 6D 位姿 / 关节角读回
# ============================================================================

def read_end_pose(iface) -> tuple[np.ndarray, np.ndarray]:
    """读真机末端位姿 -> (p_xyz_m (3,), rpy_deg (3,))。

    piper_sdk 反馈单位：X/Y/Z = 0.001mm，RX/RY/RZ = 0.001deg（绕 X/Y/Z 的固定角）。
    """
    m = iface.GetArmEndPoseMsgs()
    ep = m.end_pose
    p = np.array([ep.X_axis, ep.Y_axis, ep.Z_axis], dtype=float) * 1e-6   # 0.001mm -> m
    rpy = np.array([ep.RX_axis, ep.RY_axis, ep.RZ_axis], dtype=float) * 1e-3  # 0.001deg -> deg
    return p, rpy


def read_joints(iface) -> np.ndarray:
    """读真机关节角 -> q (6,) 单位 rad（0.001deg -> rad）。"""
    m = iface.GetArmJointMsgs()
    js = m.joint_state
    deg = np.array([js.joint_1, js.joint_2, js.joint_3,
                    js.joint_4, js.joint_5, js.joint_6], dtype=float) * 1e-3
    return np.deg2rad(deg)


class PiperArm:
    """piper_sdk 薄封装：下发关节角（每拍速度上限）+ 读回末端位姿/关节角 + 急停。"""

    def __init__(self, can_name: str, max_joint_speed_deg_s: float = 30.0) -> None:
        from piper_sdk import C_PiperInterface_V2  # local import: 需要 python-can
        self.iface = C_PiperInterface_V2(can_name=can_name)
        try:
            self.iface.ConnectPort()
            # 上次正常退出时 freeze() 会保持 6 电机使能+位置保持，臂仍处于使能态；此时
            # EmergencyStop(0x02) 实为“复位”（与 SDK ResetPiper 同款 0x150 帧，会令臂失电
            # 下坠），导致「第二次运行臂砸下来、使能失败」。因此先直接使能（对已使能臂幂等），
            # 只有使能失败（如上次急停退出残留错误态）才复位清除错误后重试。
            if not self.enable_arm():
                self.iface.EmergencyStop(0x02)               # 复位清除急停/错误标志
                self.enable_arm()                            # 复位后重试使能
            self.iface.ModeCtrl(ctrl_mode=0x01, move_mode=0x01)  # CAN 控制 + MOVE J
        except Exception:
            self.close()
            raise

        # 每拍单关节最大增量（rad）；作为「一次性确认后跟随」的安全阀。
        self.max_joint_speed = math.radians(float(max_joint_speed_deg_s))
        # 以下发/读回的实体臂实际关节角为速度限幅起点，避免第一次下发时从 0 跳变。
        # 刚连接后 CAN 反馈可能还没到，read_joints 会返回全 0；轮询直到读到非零反馈。
        self._last_q = self._read_joints_with_retry()
        self._last_t = time.monotonic()

        # 夹爪开度上限（米）。SDK 参数管理器默认 [0, 0.07]（70mm 满开），真机若校准
        # 过会改；GripperCtrl 的 gripper_angle 单位 0.001mm（= m × 1e6）。
        try:
            _g_min, _g_max = self.iface.GetSDKGripperRangeParam()
            self.gripper_max_m = float(_g_max)
        except Exception:
            self.gripper_max_m = 0.07
        self._gripper_enabled = False

    def enable_arm(self, timeout: float = 3.0, interval: float = 0.05) -> bool:
        """使能全部 6 电机并校验 driver_enable_status。

        ``EnableArm(7)`` 只是发一条 CAN 使能指令，可能被漏收/未生效；官方 demo 用
        ``while not EnablePiper()`` 重试，即读回低中速反馈里的 ``driver_enable_status``
        确认 6 个电机都置位才算使能成功。这里做同样的事，返回是否全部使能。
        """
        deadline = time.monotonic() + timeout
        status: list = []
        while time.monotonic() < deadline:
            self.iface.EnableArm(7)
            try:
                status = self.iface.GetArmEnableStatus()
            except Exception:
                status = []
            if len(status) == 6 and all(status):
                print(f"[arm] 6 电机已使能 enable_status={status}")
                return True
            time.sleep(interval)
        print(f"[arm] WARN: 使能校验超时（{timeout:.0f}s）enable_status={status}（继续，下发可能无效）")
        return False

    def send(self, q: np.ndarray) -> np.ndarray:
        """下发 6 关节角 (rad) —— piper_sdk 单位 0.001deg，做每拍速度上限后返回实际下发 q。

        每拍重发 ``ModeCtrl``（官方 demo 里 ``MotionCtrl_2`` 也是每拍发），确保长时间
        SIM 冻结后真机仍处于 CAN 控制 + MOVE J，不因空闲掉回待机而忽略 JointCtrl。
        速度上限让 R 复位、首次跟随、目标跳变时臂平滑过渡，而不是瞬间甩到目标。
        """
        q = np.asarray(q, dtype=float).copy()
        dt = max(time.monotonic() - self._last_t, 1e-3)
        max_delta = self.max_joint_speed * dt
        q_limited = self._last_q + np.clip(q - self._last_q, -max_delta, max_delta)

        self.iface.ModeCtrl(ctrl_mode=0x01, move_mode=0x01)
        mdeg = [int(round(float(r) * 180.0 / math.pi * 1000.0)) for r in q_limited]
        self.iface.JointCtrl(*mdeg)

        self._last_q = q_limited
        self._last_t = time.monotonic()
        return q_limited

    def enable_gripper(self, effort_nm: float = 1.0) -> None:
        """夹爪使能（失能清错误 -> 使能，开度归零）。effort 单位 N·m（0~5）。"""
        effort = int(round(max(0.0, min(float(effort_nm), 5.0)) * 1000))
        self.iface.GripperCtrl(0, effort, 0x02, 0)   # 失能 + 清错误
        self.iface.GripperCtrl(0, effort, 0x01, 0)   # 使能
        self._gripper_enabled = True

    def send_gripper(self, width_m: float, effort_nm: float = 1.0) -> None:
        """下发夹爪开度 (m)。gripper_angle 单位 0.001mm（= m × 1e6），0=闭合。

        开度 clamp 到 [0, SDK 上限]（默认 0.07 m）；首次调用先执行 enable 序列。
        每拍 code=0x01（使能），与官方 demo ``piper_ctrl_gripper.py`` 一致。
        """
        if not self._gripper_enabled:
            self.enable_gripper(effort_nm)
        w = max(0.0, min(float(width_m), self.gripper_max_m))
        effort = int(round(max(0.0, min(float(effort_nm), 5.0)) * 1000))
        angle = int(round(w * 1e6))
        self.iface.GripperCtrl(angle, effort, 0x01, 0)

    def _read_joints_with_retry(self, timeout: float = 2.0, interval: float = 0.05) -> np.ndarray:
        """连接后读一次有效关节角，作为速度限幅起点。

        ConnectPort/EnableArm 之后首帧 CAN 反馈可能还没到，``read_joints`` 会返回全 0；
        全 0 不是真实位形（j2=0、j3=0 都是关节限位），因此轮询直到读到非零反馈。
        """
        deadline = time.monotonic() + timeout
        last = np.zeros(6)
        while time.monotonic() < deadline:
            try:
                q = self.read_joints()
            except Exception:
                q = np.zeros(6)
            if np.any(q):
                print(f"[arm] 初始关节角(°) = {[f'{a * 57.2958:+.1f}' for a in q]}")
                return q
            last = q
            time.sleep(interval)
        print("[arm] WARN: 未读到非零关节反馈，速度限幅起点按 0 处理（首次下发可能跳变）")
        return last

    def read_end_pose(self) -> tuple[np.ndarray, np.ndarray]:
        return read_end_pose(self.iface)

    def read_joints(self) -> np.ndarray:
        return read_joints(self.iface)

    def read_ctrl_mode(self) -> int:
        """读真机当前控制模式：0x00 待机 / 0x01 CAN 指令控制 / 0x02 示教（手拖）。

        示教模式由真机绿色按钮切入/切出（非 SDK 指令）。读失败返回 -1。
        """
        try:
            return int(self.iface.GetArmStatus().arm_status.ctrl_mode)
        except Exception:
            return -1

    def emergency_stop(self) -> None:
        self.iface.EmergencyStop(0x01)

    def freeze(self) -> None:
        """冻结在位：保持 6 电机使能 + 位置保持，仅断开连接（**不** DisableArm）。

        用于退出前「回准备姿态后冻结」：到位后调用，让臂停在目标位姿不回弹（DisableArm
        会让电机掉电、重力下垂）。若后续仍需彻底断电，调用方自行 ``close()``。
        """
        try:
            self.iface.DisconnectPort()
        except Exception:
            pass

    def close(self) -> None:
        for fn in ("DisableArm", "DisconnectPort"):
            try:
                getattr(self.iface, fn)(7) if fn == "DisableArm" else getattr(self.iface, fn)()
            except Exception:
                pass


# ============================================================================
# 位移：a_lin -> v (ZUPT+梯形) -> d (二次积分)，绝对式 1:1，无归一化、无 clamp
# ============================================================================

class UmiDisplacement:
    """原始 IMU (200 Hz) -> 位移 d (m, base 系)，**绝对式 1:1**（无归一化、无有界 clamp）。

    信号链（沿用 ``piper_imu_sim.ImuStepCore`` 的前半段）：
      1. align（S->N）; 2. EMA 低通（fc Hz）; 3. 去重力 -> a_lin;
      4. ZUPT（|a_lin|<vel_zero_accel -> v=0）+ 梯形积分 -> v;
      5. v 过死区 -> d += v·dt（二次积分）; 6. 可选 leak 回中（漂移抑制，默认 0）。

    位移直接等于夹爪在 base 系中的平移（米），由遥操层 1:1 加到 home 上；超出行程时
    由遥操层的 IK 可达性守卫拦截（不在此处 clamp）。
    """

    def __init__(self, sample_rate: float = 200.0, fc: float = 5.0,
                 vel_zero_accel: float = 0.2, vel_threshold: float = 0.03,
                 leak: float = 0.0, acc_bias: np.ndarray | None = None,
                 align: np.ndarray | None = None):
        self.sample_rate = float(sample_rate)
        self.dt = 1.0 / self.sample_rate
        self.alpha = math.exp(-2.0 * math.pi * fc / sample_rate)  # 旧样本权重（低通）
        self.vel_zero_accel = float(vel_zero_accel)
        self.vel_threshold = float(vel_threshold)
        self.leak = float(leak)
        self.align = np.eye(3) if align is None else np.asarray(align, dtype=float)
        self.acc_bias = (DEFAULT_GRAVITY_G.copy() if acc_bias is None
                         else np.asarray(acc_bias, dtype=float))
        self.reset()

    def reset(self) -> None:
        self._a_lp = None            # EMA 状态（acc, g）
        self._a_lin_prev = None      # 上一拍去重力加速度（梯形积分）
        self._v = np.zeros(3)        # 线速度（m/s）
        self._d = np.zeros(3)        # 位移（m）

    @property
    def velocity(self) -> np.ndarray:
        return self._v.copy()

    @property
    def displacement(self) -> np.ndarray:
        return self._d.copy()

    def feed(self, acc_g, gyro_radps) -> np.ndarray:
        """喂一个样本（acc 单位 g、gyro 单位 rad/s，传感器系），返回位移 d (m)。"""
        acc = self.align @ np.asarray(acc_g, dtype=float)
        # 2) EMA 低通
        a = self.alpha
        self._a_lp = acc.copy() if self._a_lp is None else a * self._a_lp + (1.0 - a) * acc
        # 3) 去重力 -> 线加速度 (m/s²)
        a_lin = (self._a_lp - self.acc_bias) * GRAVITY
        # 4) ZUPT + 梯形积分 -> v
        if self._a_lin_prev is None:
            self._a_lin_prev = a_lin.copy()
        elif float(np.linalg.norm(a_lin)) < self.vel_zero_accel:
            self._v = np.zeros(3)                       # 零速更新
            self._a_lin_prev = a_lin.copy()
        else:
            self._v = self._v + 0.5 * (a_lin + self._a_lin_prev) * self.dt
            self._a_lin_prev = a_lin.copy()
        # 5) v 过死区 -> d += v·dt（二次积分到位移）
        v_db = np.where(np.abs(self._v) < self.vel_threshold, 0.0, self._v)
        self._d = self._d + v_db * self.dt
        # 6) 可选回中 leak（默认 0 = 位置保持）
        if self.leak > 0.0:
            self._d = self._d * (1.0 - self.leak)
        return self._d.copy()
