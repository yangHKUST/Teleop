"""Pinocchio kinematics for the AgileX Piper arm (modified-DH -> Pinocchio model).

Replaces the Songling/piper_sdk IK with a Pinocchio model built from the arm's
modified-DH table, so that:

  * Pinocchio's joint vector ``q`` is *directly* the arm's joint-angle convention
    (the exact values you feed to ``piper_sdk.JointCtrl``), and
  * Pinocchio forward kinematics == ``agx_kinematics.fk`` == piper_sdk's own FK
    (validated numerically in ``test_pinocchio_ik.py``).

Why MDH and not the URDF: the real arm's firmware uses modified-DH; the URDF
flange sits a fixed ~1 cm off that (see ``arm/mujoco_sim/README.md``).  Building
from MDH keeps IK consistent with the real arm.

Math note: each MDH link is ``T_i = R_x(alpha) T_x(a) R_z(theta) T_z(d)`` with
``theta = q_i + theta_off``.  Since ``R_z`` commutes with ``T_z``,
``T_i = M_i * R_z(q_i)`` where ``M_i = R_x(alpha) T_x(a) T_z(d) R_z(theta_off)``
is a constant.  ``M_i`` is exactly ``_mdh_link(d, a, alpha, theta_off)``, so each
Pinocchio joint is a ``JointModelRZ`` whose placement is ``_mdh_link(...)`` and
whose joint variable equals the arm's ``q_i``.

This module is pure ``pinocchio`` + ``numpy`` (no ROS, no piper_sdk), so it can be
unit-tested standalone.
"""

from __future__ import annotations

import math
from typing import Tuple

import numpy as np
import pinocchio as pin

ARM_JOINT_NAMES = ["joint1", "joint2", "joint3", "joint4", "joint5", "joint6"]

# Modified-DH table (d, a, alpha, theta_offset), units m / rad. Same values as
# ``agx_kinematics._PIPER_MDH`` (pyAgxArm ``ROBOT_MDH_PRESET["piper"]``).
_PIPER_MDH = (
    (0.123, 0.0, 0.0, 0.0),
    (0.0, 0.0, -math.pi / 2, -3.0058060377846343),
    (0.0, 0.28503, 0.0, -1.793849405199772),
    (0.25075, -0.02198, math.pi / 2, 0.0),
    (0.0, 0.0, -math.pi / 2, 0.0),
    (0.091, 0.0, math.pi / 2, 0.0),
)

# Joint limits (rad). j1..j5 match ``agx_kinematics.PIPER_JOINT_MIN/MAX``; j6 is
# corrected to +/-180 deg (π) to match the DEG preset and agx_kinematics (the
# earlier +/-120 deg here was wrong).
PIPER_JOINT_MIN = np.array([-2.617994, 0.0, -2.967060, -1.745330, -1.221730, -3.141593])
PIPER_JOINT_MAX = np.array([2.617994, 3.141593, 0.0, 1.745330, 1.221730, 3.141593])

FLANGE_FRAME_NAME = "flange"

# 夹爪 TCP（工具中心点）相对法兰/link6 坐标系的原点平移 (m)。
# 从 piper_h.xml 的夹爪几何（与 agx_arm_urdf piper_h_with_gripper_description.xacro
# 一致）实测：flange 在 link6 原点 +0.0103（网格对齐），gripper_base 在 flange
# +0.0045，两手指挂点 gripper_base +0.138、手指长 0.0765，指尖中心落在 link6
# +0.0763 处（沿 +Z，两指在 ±Y 对称）。见 piper_umi_attitude 的 --tcp 参数可覆盖。
TCP_TRANSLATION = np.array([0.0, 0.0, 0.0763])


def _mdh_link(d: float, a: float, alpha: float, theta: float) -> np.ndarray:
    """Modified-DH link transform ``R_x(alpha) T_x(a) R_z(theta) T_z(d)`` (4x4)."""
    ca, sa = math.cos(alpha), math.sin(alpha)
    ct, st = math.cos(theta), math.sin(theta)
    return np.array(
        [
            [ct, -st, 0.0, a],
            [ca * st, ca * ct, -sa, -sa * d],
            [sa * st, sa * ct, ca, ca * d],
            [0.0, 0.0, 0.0, 1.0],
        ]
    )


def _se3_from_4x4(T: np.ndarray) -> pin.SE3:
    """4x4 homogeneous transform -> pinocchio SE3."""
    return pin.SE3(T[:3, :3], T[:3, 3])


def so3_log(R: np.ndarray) -> np.ndarray:
    """Rotation matrix -> rotation vector (axis * angle), robust for small angles."""
    R = np.asarray(R, dtype=float)
    cos_t = (np.trace(R) - 1.0) / 2.0
    cos_t = float(np.clip(cos_t, -1.0, 1.0))
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


def axis_rotation(axis: np.ndarray, angle: float) -> np.ndarray:
    """Rotation matrix (3x3) for a rotation of ``angle`` about a unit ``axis``."""
    axis = np.asarray(axis, dtype=float)
    n = np.linalg.norm(axis)
    if n < 1e-12:
        return np.eye(3)
    axis = axis / n
    kx, ky, kz = axis
    k = np.array([[0.0, -kz, ky], [kz, 0.0, -kx], [-ky, kx, 0.0]])
    return np.eye(3) + math.sin(angle) * k + (1.0 - math.cos(angle)) * (k @ k)


class PiperPinocchio:
    """Pinocchio model + FK/IK for the Piper arm."""

    def __init__(self, tcp_translation=None) -> None:
        self.model = pin.Model()
        parent = 0  # universe == the arm's base frame
        for i, (d, a, alpha, theta_off) in enumerate(_PIPER_MDH):
            placement = _se3_from_4x4(_mdh_link(d, a, alpha, theta_off))
            parent = self.model.addJoint(
                parent, pin.JointModelRZ(), placement, ARM_JOINT_NAMES[i]
            )
        self.model.addFrame(
            pin.Frame(
                FLANGE_FRAME_NAME,
                parent,
                0,
                pin.SE3.Identity(),
                pin.FrameType.OP_FRAME,
            )
        )
        # Enforce the real-arm joint limits (URDF-free model, so set them here).
        self.model.lowerPositionLimit[:] = PIPER_JOINT_MIN
        self.model.upperPositionLimit[:] = PIPER_JOINT_MAX

        self.data = self.model.createData()
        self.flange_id = self.model.getFrameId(FLANGE_FRAME_NAME)
        # 夹爪 TCP 平移（法兰系 -> TCP 系，绕 Z 无旋转）。默认取夹爪指尖中心。
        self.tcp = (TCP_TRANSLATION.copy() if tcp_translation is None
                    else np.asarray(tcp_translation, dtype=float).reshape(3).copy())

    @property
    def qmin(self) -> np.ndarray:
        return self.model.lowerPositionLimit.copy()

    @property
    def qmax(self) -> np.ndarray:
        return self.model.upperPositionLimit.copy()

    def fk(self, q: np.ndarray) -> pin.SE3:
        """Flange pose (SE3, base frame) for the 6 arm joint angles (rad)."""
        q = np.asarray(q, dtype=float)
        if q.shape[0] != 6:
            raise ValueError(f"expected 6 joint values, got {q.shape[0]}")
        pin.forwardKinematics(self.model, self.data, q)
        pin.updateFramePlacements(self.model, self.data)
        return self.data.oMf[self.flange_id].copy()

    def fk_homogeneous(self, q: np.ndarray) -> np.ndarray:
        """Flange pose as a 4x4 numpy matrix (base frame)."""
        return self.fk(q).homogeneous

    def fk_tcp(self, q: np.ndarray) -> pin.SE3:
        """Gripper TCP pose (SE3, base frame) = flange pose 沿 +Z 平移 ``self.tcp``。

        TCP 系与法兰系同向（无旋转），仅把参考点从腕部法兰移到夹爪指尖中心，这样
        遥操/姿态控制的对象就是夹爪 TCP 而不是法兰。
        """
        return self.fk(q) * pin.SE3(np.eye(3), self.tcp)

    def ik_tcp(self, q0: np.ndarray, T_target: pin.SE3, **kwargs):
        """DLS IK for an absolute gripper TCP pose (base frame)。

        先把 TCP 目标反算成法兰目标 ``T_target * SE3(I, -tcp)``，再复用法兰 IK，使解出
        的关节角把**夹爪 TCP**（而非腕部法兰）放到指令位姿。返回 ``(q, ok, residual)``。
        """
        T_flange = T_target * pin.SE3(np.eye(3), -self.tcp)
        return self.ik(q0, T_flange, **kwargs)

    def ik(
        self,
        q0: np.ndarray,
        T_target: pin.SE3,
        damping: float = 1e-3,
        max_iter: int = 25,
        tol_pos: float = 1e-4,
        tol_rot: float = 1e-3,
        locked_joints=None,
    ) -> Tuple[np.ndarray, bool, float]:
        """Damped-least-squares IK for an absolute flange pose (base frame).

        Iteratively corrects the joints toward ``T_target``, clamping to the arm
        joint limits after every step. Returns ``(q, ok, residual)`` where
        ``residual`` is ``max(pos_err_m, rot_err_rad)`` of the final pose.

        ``locked_joints`` (optional) is an iterable of 0-indexed joint numbers
        whose Jacobian columns are zeroed out, freezing them at their ``q0`` value
        (e.g. ``(3,)`` pins joint4 so the solver never drives it).
        """
        q = np.asarray(q0, dtype=float).copy()
        qmin = self.model.lowerPositionLimit
        qmax = self.model.upperPositionLimit
        lam2 = damping * damping
        locked = () if locked_joints is None else tuple(int(j) for j in locked_joints)

        # Geometric error, world frame (matches ``agx_kinematics.ik_solve``):
        # raw position error + rotation-vector error, consistent with the
        # LOCAL_WORLD_ALIGNED spatial Jacobian ``[v; w]``.
        p_err = r_err = float("inf")
        for _ in range(int(max_iter)):
            pin.forwardKinematics(self.model, self.data, q)
            pin.updateFramePlacements(self.model, self.data)
            T_cur = self.data.oMf[self.flange_id]

            err_p = T_target.translation - T_cur.translation
            err_r = so3_log(T_target.rotation @ T_cur.rotation.T)
            p_err = float(np.linalg.norm(err_p))
            r_err = float(np.linalg.norm(err_r))
            if p_err <= tol_pos and r_err <= tol_rot:
                break

            J = pin.computeFrameJacobian(
                self.model,
                self.data,
                q,
                self.flange_id,
                pin.ReferenceFrame.LOCAL_WORLD_ALIGNED,
            )
            # Freeze the locked joints: zero their Jacobian columns so the DLS
            # step leaves them unchanged (dq[j] == 0) and they stay at q0[j].
            for j in locked:
                J[:, j] = 0.0
            err = np.concatenate([err_p, err_r])
            dq = np.linalg.solve(J.T @ J + lam2 * np.eye(6), J.T @ err)
            q = np.clip(q + dq, qmin, qmax)

        residual = max(p_err, r_err)
        ok = residual <= max(tol_pos, tol_rot)
        return q, ok, residual


def clamp_to_limits(q: np.ndarray) -> np.ndarray:
    """Clamp 6 joint angles (rad) into the Piper SDK limits."""
    return np.clip(np.asarray(q, dtype=float), PIPER_JOINT_MIN, PIPER_JOINT_MAX)
