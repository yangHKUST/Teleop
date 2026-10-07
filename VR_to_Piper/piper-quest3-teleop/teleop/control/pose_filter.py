# teleop/control/pose_filter.py
"""1€ 自适应滤波 + 死区，用于 VR 手柄 → 机械臂末端目标位姿。

作用位置：TELEOP 分支里 mapper.compute_target_T() 之后、ik_step 之前，
对目标 4x4 位姿（机器人基坐标系）做滤波，抑制手持遥操的生理性手抖（8–12Hz）。

结构（两级级联）：
  1. 死区（增量式 deadband，带滞回）：相对"上次滤波输出"的增量小于阈值则冻结输出，
     让"手想停就真停"，并避免 100Hz 下发微米级抖动造成的电机发热/磨损。
  2. 1€ 滤波（Casiez 2012）：截止频率随信号速度自适应——
     动得快→截止高→延迟小；动得慢/静止→截止低→抖压得死。
     - 位置：逐轴 1€
     - 姿态：SLERP + 自适应 α（角速度决定截止频率）

参数见 PoseFilterConfig，实际值在 config.py 里调（无需改本文件）。
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import numpy as np

from .rotation_smoothing import (
    rotmat_to_quat,
    quat_to_rotmat,
    slerp_quat,
    relative_rotation_angle,
)


@dataclass
class PoseFilterConfig:
    enabled: bool = True

    # --- 1€ 滤波 ---
    fc_min: float = 1.0        # Hz，静止时最低截止频率（越低抖压得越死）
    fc_d: float = 1.0          # Hz，速度估计的低通截止（一般固定）
    beta_pos: float = 14.0     # 位置速度系数，单位 Hz/(m/s)（越大越跟手、越抖）
    beta_rot: float = 3.0      # 姿态速度系数，单位 Hz/(rad/s)

    # --- 死区（增量式，带滞回）---
    deadband_pos: float = 0.002       # m，解冻阈值 outer（明显动作才解冻）
    deadband_rot: float = 0.0105      # rad，解冻阈值 outer（~0.6°）
    deadband_pos_inner: float = 0.0007   # m，冻结阈值 inner（几乎静止即冻结）
    deadband_rot_inner: float = 0.0035   # rad，冻结阈值 inner（~0.2°）

    dt_default: float = 0.01   # s，采样周期兜底（主循环 100Hz，与 MINK_RATE_HZ 一致）


class PoseFilter:
    """Per-arm 目标位姿滤波器（左/右臂各一个实例，状态互不影响）。"""

    def __init__(self, cfg: Optional[PoseFilterConfig] = None):
        self.cfg = cfg or PoseFilterConfig()
        self.enabled = bool(self.cfg.enabled)
        self.frozen = False        # 上一帧是否被死区冻结（调试/调参用）
        self._p_filt = None        # (3,) 滤波后位置
        self._q_filt = None        # (4,) 滤波后四元数 (w,x,y,z)
        self._dx_hat = None        # (3,) 平滑后的位置速度
        self._omega_hat = None     # 标量，平滑后的角速度
        self._initialized = False

    # ------------------------------------------------------------------
    def reset(self) -> None:
        """清空状态，下次 filter() 会以首帧目标热启动（不跳变）。"""
        self.frozen = False
        self._p_filt = None
        self._q_filt = None
        self._dx_hat = None
        self._omega_hat = None
        self._initialized = False

    # ------------------------------------------------------------------
    def filter(self, T_target: np.ndarray, dt: Optional[float] = None) -> np.ndarray:
        """对一帧目标位姿做滤波，返回滤波后的 4x4。

        T_target: (4,4) 齐次矩阵（机器人基坐标系）。
        dt: 采样周期（秒），默认用 cfg.dt_default。
        """
        if not self.enabled:
            return np.asarray(T_target, dtype=float)

        dt = self.cfg.dt_default if dt is None else float(dt)
        if not np.isfinite(dt) or dt <= 0.0:
            dt = self.cfg.dt_default

        p_new = np.asarray(T_target[:3, 3], dtype=float).reshape(3).copy()
        R_new = np.asarray(T_target[:3, :3], dtype=float).copy()

        # 首帧：直接以目标热启动，不滤波、不跳变
        if not self._initialized:
            self._p_filt = p_new.copy()
            self._q_filt = rotmat_to_quat(R_new)
            self._dx_hat = np.zeros(3, dtype=float)
            self._omega_hat = 0.0
            self._initialized = True
            self.frozen = False
            return self._build_T()

        R_filt = quat_to_rotmat(self._q_filt)

        # ---- 死区（增量式，带滞回/Schmitt 触发）----
        # 单一阈值会在边界来回 freeze/unfreeze，造成"抓取时轻微抖"；
        # 用两个阈值消除边界抖动：移动中 → 增量小于 inner 才冻结；冻结中 → 增量大于 outer 才解冻。
        dp = float(np.linalg.norm(p_new - self._p_filt))
        dtheta = float(relative_rotation_angle(R_filt, R_new))
        if self.frozen:
            # 解冻：需要明显动作（outer 阈值）
            if dp <= self.cfg.deadband_pos and dtheta <= self.cfg.deadband_rot:
                self._dx_hat[:] = 0.0
                self._omega_hat = 0.0
                return self._build_T()
            self.frozen = False
        else:
            # 冻结：几乎静止（inner 阈值）；速度估计清零，避免解冻瞬间残留导数误判
            if dp < self.cfg.deadband_pos_inner and dtheta < self.cfg.deadband_rot_inner:
                self._dx_hat[:] = 0.0
                self._omega_hat = 0.0
                self.frozen = True
                return self._build_T()

        # ---- 位置 1€（逐轴）----
        dx = (p_new - self._p_filt) / dt
        alpha_d = self._alpha(self.cfg.fc_d, dt)
        self._dx_hat = self._dx_hat + alpha_d * (dx - self._dx_hat)
        f_cut_pos = self.cfg.fc_min + self.cfg.beta_pos * float(np.linalg.norm(self._dx_hat))
        alpha_p = self._alpha(f_cut_pos, dt)
        self._p_filt = self._p_filt + alpha_p * (p_new - self._p_filt)

        # ---- 姿态 1€（SLERP + 自适应 α）----
        omega = dtheta / dt
        self._omega_hat = self._omega_hat + alpha_d * (omega - self._omega_hat)
        f_cut_rot = self.cfg.fc_min + self.cfg.beta_rot * abs(self._omega_hat)
        alpha_r = self._alpha(f_cut_rot, dt)
        q_new = rotmat_to_quat(R_new)
        self._q_filt = slerp_quat(self._q_filt, q_new, alpha_r)

        return self._build_T()

    # ------------------------------------------------------------------
    @staticmethod
    def _alpha(f_cut: float, dt: float) -> float:
        tau = 1.0 / (2.0 * np.pi * max(float(f_cut), 1e-6))
        return 1.0 / (1.0 + tau / dt)

    def _build_T(self) -> np.ndarray:
        T = np.eye(4, dtype=float)
        T[:3, :3] = quat_to_rotmat(self._q_filt)
        T[:3, 3] = self._p_filt
        return T
