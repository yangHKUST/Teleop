#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""URDF 建模的 Piper 解耦逆解（移植自 ``switch_to_arm/src/kinematic_dls.py``）。

规避 home 位形（joint4/joint6 近似共线的腕部奇异）导致的全 6D DLS IK 翻腕/翻肘：

  * 位置：joint1/2/3 用 3×3 位置雅可比做 Gauss-Newton（``ReferenceFrame.LOCAL``，
    max_step=0.3、damping=1e-3、tol=1e-8）。
  * 姿态：joint5 = 俯仰(pitch)、joint6 = 滚转(roll) 直接映射（clip 到限位），
    joint4 保持中性(0)，yaw 丢弃（跟随摆臂）。
  * 不可达：``err_norm > reach_tol(0.01)`` 时保持上次 q[:3]，避免甩到限位。

模型用 SolidWorks URDF（``switch_to_arm/piper/piper.urdf``）。该 URDF 的 link 长度与
MDH 一致（joint4 origin y=-0.25075、joint6 origin y=-0.091），实测 URDF FK 与
``piper_pinocchio`` MDH FK 相差 <0.1mm / 0.005°，因此 URDF FK == MDH FK ==
MuJoCo ``piper_h.xml`` == 真机，无 1cm 法兰偏差。构建时只取运动学树（剥掉
``<visual>``/``<collision>``，不加载 mesh），并把 joint6 限位覆写为 ±π（URDF 的
SolidWorks 导出把 joint6 误写成了 ±2.967，与已修正的真机限位 ±180° 不符）。
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Optional, Tuple

import numpy as np
import pinocchio as pin

# 默认 URDF（switch_to_arm 参考工程里那份，与 MDH 逐点一致）。
_URDF_PATH = Path(__file__).resolve().parents[2] / "switch_to_arm" / "piper" / "piper.urdf"

# joint6 修正后的限位（rad），与 piper_pinocchio.PIPER_JOINT_MAX[5] 一致。
_J6_LIMIT = np.pi


def _strip_meshes(xml: str) -> str:
    """剥掉 <visual>/<collision>（含 mesh 引用），只留运动学树。"""
    for tag in ("visual", "collision"):
        xml = re.sub(rf"<{tag}>.*?</{tag}>", "", xml, flags=re.S)
    return xml


class PiperDecoupledIk:
    """基于 URDF 的解耦逆解。q 为 6 个臂关节角（rad，与真机 1:1，无偏移/翻号）。"""

    def __init__(self, urdf_path: Optional[str] = None, damping: float = 1e-3,
                 max_iter: int = 60, tol: float = 1e-8, max_step: float = 0.3,
                 wrist_pitch_limit: float = 1.2, reach_tol: float = 0.01):
        path = Path(urdf_path) if urdf_path else _URDF_PATH
        xml = _strip_meshes(path.read_text(encoding="utf-8"))
        self.model = pin.buildModelFromXML(xml, None)  # 固定基座（base_footprint 折叠）

        # ee 坐标系挂在 joint6（法兰/link6 原点），与 MDH 法兰 / MuJoCo link6 一致。
        self.model.addFrame(
            pin.Frame("ee", self.model.getJointId("joint6"),
                      pin.SE3.Identity(), pin.FrameType.OP_FRAME)
        )
        # 覆写 joint6 限位为 ±π（URDF 导出误写成 ±2.967）。
        self.model.lowerPositionLimit[5] = -_J6_LIMIT
        self.model.upperPositionLimit[5] = _J6_LIMIT

        self.data = self.model.createData()
        self.ee_id = self.model.getFrameId("ee")

        self.damping = damping
        self.max_iter = max_iter
        self.tol = tol
        self.max_step = max_step
        self.wrist_pitch_limit = wrist_pitch_limit  # joint5 俯仰限位(rad)，1.2≈69°
        self.reach_tol = reach_tol                  # 位置不可达判定阈值(m)
        self._q_warm = np.zeros(self.model.nq)      # 逆解热启动（8 维，含夹爪）

    # ------------------------------------------------------------------ #
    # 限位
    # ------------------------------------------------------------------ #
    @property
    def qmin(self) -> np.ndarray:
        return self.model.lowerPositionLimit[:6].copy()

    @property
    def qmax(self) -> np.ndarray:
        return self.model.upperPositionLimit[:6].copy()

    def clamp(self, q6: np.ndarray) -> np.ndarray:
        return np.clip(np.asarray(q6, dtype=float), self.qmin, self.qmax)

    # ------------------------------------------------------------------ #
    # 正解
    # ------------------------------------------------------------------ #
    def fk(self, q6: np.ndarray) -> pin.SE3:
        """6 臂关节角 -> 法兰(ee)位姿（base 系，SE3）。"""
        q = np.zeros(self.model.nq)
        q[:6] = np.asarray(q6, dtype=float)
        pin.framesForwardKinematics(self.model, self.data, q)
        return self.data.oMf[self.ee_id].copy()

    def fk_homogeneous(self, q6: np.ndarray) -> np.ndarray:
        return self.fk(q6).homogeneous

    # ------------------------------------------------------------------ #
    # 解耦逆解
    # ------------------------------------------------------------------ #
    def ik(self, p_target: np.ndarray, roll: float, pitch: float,
           ) -> Tuple[np.ndarray, bool, float]:
        """解耦逆解 -> ``(q6, ok, pos_err_m)``。

        ``p_target`` 末端位置（base 系，m）；``roll`` -> joint6（夹爪滚转）、
        ``pitch`` -> joint5（夹爪俯仰），单位 rad；joint4 恒 0。位置由 joint1/2/3
        数值 IK 解出；目标不可达时保持上次位置链，``ok=False``。
        """
        lo = self.model.lowerPositionLimit
        hi = self.model.upperPositionLimit

        q = self._q_warm.astype(float).copy()
        q_pos_prev = q[:3].copy()  # 上次位置链（不可达时保持，避免跳变）

        # 腕部直接映射：joint4 中性，joint5=俯仰，joint6=滚转；夹爪置 0。
        q[3] = 0.0
        q[4] = np.clip(pitch, -self.wrist_pitch_limit, self.wrist_pitch_limit)
        q[5] = np.clip(roll, lo[5], hi[5])
        q[6:8] = 0.0

        # 位置 IK：只解 joint1/2/3，使 ee 位置到 p_target。
        p_target = np.asarray(p_target, dtype=float)
        mu = self.damping
        err_norm = float("inf")
        for _ in range(self.max_iter):
            pin.framesForwardKinematics(self.model, self.data, q)
            oMf = self.data.oMf[self.ee_id]
            err = oMf.rotation.T @ (p_target - oMf.translation)  # LOCAL 帧（WORLD 有 bug）
            err_norm = float(np.linalg.norm(err))
            if err_norm < self.tol:
                break
            J = np.asarray(
                pin.computeFrameJacobian(
                    self.model, self.data, q, self.ee_id, pin.ReferenceFrame.LOCAL,
                )[:3, :3],
                dtype=float,
            )
            H = J.T @ J + mu * np.eye(3)
            dq = np.linalg.solve(H, J.T @ err)
            dq = np.clip(dq, -self.max_step, self.max_step)
            q[:3] = np.clip(q[:3] + dq, lo[:3], hi[:3])

        if err_norm > self.reach_tol:
            q[:3] = q_pos_prev

        self._q_warm = q
        ok = err_norm <= self.reach_tol
        return q[:6].copy(), ok, err_norm
