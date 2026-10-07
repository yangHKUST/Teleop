#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""URDF 建模的 OpenArm 左/右臂 7 关节全 6D 逆解（自写 pinocchio DLS IK）。

OpenArm v1.0 是 7-DOF 机械臂，关节轴依次为 j1(z) / j2(-x) / j3(z) / j4(y) /
j5(z) / j6(x) / j7(y)。腕部 j5/j6/j7 三轴交汇于 link7 原点（球腕中心）。本模块求解
**完整 6D 位姿（x,y,z,roll,pitch,yaw）+ 7 关节全部可动**：对 ee 坐标系（挂在
openarm_{side}_right_finger 指尖，方向与 link7 一致）的 6×7 雅可比
（``ReferenceFrame.LOCAL``）做阻尼最小二乘，冗余自由度（7 关节 vs 6D 目标）用零空间
投影到**关节居中**消解（等价 pick_ik 的 CenterJointsGoal）。

模型用 ``openarm_description`` 的双臂 URDF（``urdf/openarm_bimanual.urdf``）构建，只
取单侧（左或右）7 关节（其余关节置 0）。基座 = body 系（+z 上 / +x 前 / +y 左），与启动标定
R_BW 的基座约定一致。``openarm_hardware`` 直接用电机位置作为 URDF 关节角（无
motor→URDF 偏移），故本 IK 输出的 q7 直接等于 forward_position_controller 的下发值。
"""
from __future__ import annotations

import math
import re
from pathlib import Path
from typing import Optional, Tuple

import numpy as np
import pinocchio as pin

# 默认 URDF：由 openarm_description xacro 生成（bimanual，含双臂 mounting rpy=1.5708）。
_URDF_PATH = Path(__file__).resolve().parent / "urdf" / "openarm_bimanual.urdf"


def _joint_names(side: str) -> list:
    """7 个臂关节名（与 forward_position_controller / joint_states 命名一致）。"""
    return [f"openarm_{side}_joint{i}" for i in range(1, 8)]


def _strip_meshes(xml: str) -> str:
    """剥掉 <visual>/<collision>（含 mesh 引用）与 <mimic>，只留运动学树。"""
    for tag in ("visual", "collision"):
        xml = re.sub(rf"<{tag}>.*?</{tag}>", "", xml, flags=re.S)
    xml = re.sub(r"<mimic[^>]*/>", "", xml)
    return xml


def _so3_log(R: np.ndarray) -> np.ndarray:
    """旋转矩阵 -> 旋转向量 (axis*angle)，小角度鲁棒（同 openarm_umi_core.so3_log）。"""
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


class OpenArmDecoupledIk:
    """基于 URDF 的 OpenArm 左/右臂全 6D 逆解。q 为 7 个臂关节角（rad，与下发值 1:1）。

    ``side`` 选 ``"left"`` / ``"right"``（默认右臂），决定关节名（openarm_{side}_joint1..7）、
    ee 帧（openarm_{side}_finger_joint1 → openarm_{side}_right_finger）与限位。

    名字沿用历史（``Decoupled`` 已不再指解耦求解，而是说明与 UMI 6D 遥操配套），
    实际是 6D 位姿 + 7 关节全动的 DLS IK。
    """

    def __init__(self, urdf_path: Optional[str] = None, side: str = "right",
                 damping: float = 1e-3, max_iter: int = 60, tol: float = 1e-8,
                 max_step: float = 0.3, center_gain: float = 0.02,
                 reach_tol: float = 0.01):
        if side not in ("left", "right"):
            raise ValueError(f"side 必须是 left/right，得到 {side!r}")
        self.side = side

        path = Path(urdf_path) if urdf_path else _URDF_PATH
        xml = _strip_meshes(path.read_text(encoding="utf-8"))
        self.model = pin.buildModelFromXML(xml, None)  # 固定基座（body 系折叠为 world）

        # 单侧 7 关节的 joint 索引 / q 下标 / 限位。
        self._jids = [self.model.getJointId(name) for name in _joint_names(side)]
        self._qidx = [self.model.idx_qs[j] for j in self._jids]
        self._nq = [self.model.nqs[j] for j in self._jids]

        # ee 坐标系挂在 openarm_{side}_right_finger（openarm_{side}_finger_joint1 的
        # child link）原点，与夹爪右指尖一致。指爪 prismatic 关节在 IK 中恒为 0（闭合位），
        # 故 ee 相对 link7 是固定偏移 (0, -0.005, 0.1025)（link7 系），方向与 link7 相同。
        self.model.addFrame(
            pin.Frame("ee", self.model.getJointId(f"openarm_{side}_finger_joint1"),
                      pin.SE3.Identity(), pin.FrameType.OP_FRAME)
        )

        self.data = self.model.createData()
        self.ee_id = self.model.getFrameId("ee")

        self.damping = damping
        self.max_iter = max_iter
        self.tol = tol
        self.max_step = max_step
        self.center_gain = center_gain              # 零空间关节居中增益
        self.reach_tol = reach_tol                  # 位置不可达判定阈值 (m)

        # 逆解热启动（全模型 nq 维，只单侧非零）。
        self._q_warm = np.zeros(self.model.nq)

    # ------------------------------------------------------------------ #
    # 限位
    # ------------------------------------------------------------------ #
    @property
    def qmin(self) -> np.ndarray:
        return np.array([self.model.lowerPositionLimit[i] for i in self._qidx])

    @property
    def qmax(self) -> np.ndarray:
        return np.array([self.model.upperPositionLimit[i] for i in self._qidx])

    def clamp(self, q7: np.ndarray) -> np.ndarray:
        return np.clip(np.asarray(q7, dtype=float), self.qmin, self.qmax)

    # ------------------------------------------------------------------ #
    # 正解
    # ------------------------------------------------------------------ #
    def _set_arm(self, q7: np.ndarray) -> np.ndarray:
        """把 7 关节角写入全模型 q（其余关节 0），返回全模型 q。"""
        q = np.zeros(self.model.nq)
        for val, qi, nq in zip(np.asarray(q7, dtype=float), self._qidx, self._nq):
            q[qi:qi + nq] = val
        return q

    def fk(self, q7: np.ndarray) -> pin.SE3:
        """7 臂关节角 -> ee(openarm_{side}_right_finger 指尖)位姿（body 系，SE3）。"""
        q = self._set_arm(q7)
        pin.framesForwardKinematics(self.model, self.data, q)
        return self.data.oMf[self.ee_id].copy()

    def fk_homogeneous(self, q7: np.ndarray) -> np.ndarray:
        return self.fk(q7).homogeneous

    # ------------------------------------------------------------------ #
    # 全 6D 逆解
    # ------------------------------------------------------------------ #
    def ik6d(self, T_target, q_seed: Optional[np.ndarray] = None,
             ) -> Tuple[np.ndarray, bool, float]:
        """全 6D 逆解 -> ``(q7, ok, pos_err_m)``。

        ``T_target`` ee(openarm_{side}_right_finger 指尖) 目标位姿（body 系），``pin.SE3`` 或 4×4 齐次矩阵。
        7 关节全动：阻尼最小二乘解 6D 误差，冗余自由度零空间投影到关节居中
        （``center_gain`` 控制强度）。``ok`` = 位置误差 <= ``reach_tol``。
        """
        if isinstance(T_target, np.ndarray):
            T_target = pin.SE3(T_target[:3, :3], T_target[:3, 3])
        p_target = np.asarray(T_target.translation, dtype=float)
        R_target = np.asarray(T_target.rotation, dtype=float)

        lo = self.qmin
        hi = self.qmax
        q_center = 0.5 * (lo + hi)

        q = self._q_warm.astype(float).copy()
        if q_seed is not None:
            for val, qi in zip(np.asarray(q_seed, dtype=float), self._qidx):
                q[qi] = val

        vel_cols = [self.model.idx_vs[j] for j in self._jids]
        mu = self.damping
        pos_err = float("inf")
        for _ in range(self.max_iter):
            pin.framesForwardKinematics(self.model, self.data, q)
            oMf = self.data.oMf[self.ee_id]
            e_p = oMf.rotation.T @ (p_target - oMf.translation)  # LOCAL 帧
            e_o = _so3_log(oMf.rotation.T @ R_target)            # LOCAL 帧
            e = np.concatenate([e_p, e_o])
            pos_err = float(np.linalg.norm(e_p))
            if float(np.linalg.norm(e)) < self.tol:
                break
            J = np.asarray(
                pin.computeFrameJacobian(
                    self.model, self.data, q, self.ee_id, pin.ReferenceFrame.LOCAL,
                )[:6, vel_cols],
                dtype=float,
            )
            M = J @ J.T + mu * np.eye(6)
            dq = J.T @ np.linalg.solve(M, e)
            # 冗余自由度零空间投影到关节居中（等价 pick_ik 的 CenterJointsGoal）。
            # 用精确伪逆做零空间投影（阻尼投影会漏到任务空间，留下 ~1e-4 残差）。
            q_arm = np.array([q[qi] for qi in self._qidx], dtype=float)
            J_pinv = np.linalg.pinv(J)
            N = np.eye(7) - J_pinv @ J
            dq = dq + N @ (self.center_gain * (q_center - q_arm))
            dq = np.clip(dq, -self.max_step, self.max_step)
            for d, qi, l, h in zip(dq, self._qidx, lo, hi):
                q[qi] = float(np.clip(q[qi] + d, l, h))

        self._q_warm = q
        ok = pos_err <= self.reach_tol
        return np.array([q[qi] for qi in self._qidx]), ok, pos_err


if __name__ == "__main__":
    # 快速自检：左/右臂 home 位形 FK -> ik6d -> FK 往返，打印关键帧与误差。
    for side, home in (("right", np.array([0.0, 0.8, 0.0, 1.2, 0.0, 0.0, 0.0])),
                       ("left", np.array([0.0, -0.8, 0.0, 1.2, 0.0, 0.0, 0.0]))):
        kine = OpenArmDecoupledIk(side=side)
        print(f"\n===== {side} arm =====")
        T = kine.fk(home)
        print("home ee(finger) pos:", np.round(T.translation, 4))
        print("qmin:", np.round(kine.qmin, 4))
        print("qmax:", np.round(kine.qmax, 4))

        q, ok, err = kine.ik6d(T)
        T_fk = kine.fk(q)
        p_err = float(np.linalg.norm(T_fk.translation - T.translation))
        o_err = float(np.linalg.norm(_so3_log(T_fk.rotation.T @ T.rotation)))
        print(f"\nik6d(home pose): ok={ok} pos_err={err:.5f}")
        print("q:", np.round(q, 4))
        print(f"roundtrip: pos_err={p_err:.2e} m  rot_err={o_err:.2e} rad")

        # 位置 + 姿态（含 yaw）扰动，验证 6D 全部跟随。
        T2 = T.copy()
        T2.translation = T.translation + np.array([0.05, 0.0, 0.03])
        T2.rotation = T.rotation @ _exp_so3(np.array([0.2, -0.15, 0.1]))  # [yaw, pitch, roll]
        q2, ok2, err2 = kine.ik6d(T2)
        T2_fk = kine.fk(q2)
        p2_err = float(np.linalg.norm(T2_fk.translation - T2.translation))
        o2_err = float(np.linalg.norm(_so3_log(T2_fk.rotation.T @ T2.rotation)))
        print(f"\nik6d(perturbed): ok={ok2} pos_err={err2:.5f}")
        print("q:", np.round(q2, 4))
        print(f"roundtrip: pos_err={p2_err:.2e} m  rot_err={o2_err:.2e} rad")
