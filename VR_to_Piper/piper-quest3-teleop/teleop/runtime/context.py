from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Any
import numpy as np

from ..VuerTeleop import VuerTeleop
from .init_right_controller import RightController


@dataclass
class ArmRuntime:
    """Per-arm runtime state (dual arm). 左右臂各一个实例。"""

    side: str            # "left" / "right"
    can_port: str

    controller: RightController

    # FK / mapping
    fk: Any
    mapper: Any
    T_zero: np.ndarray
    last_q: np.ndarray

    # mink / mujoco（每个臂各自一份 model/data/configuration/tasks/solver）
    model: Any
    data: Any
    configuration: Any
    tasks: list
    limits: list
    solver: Any
    rate: Any

    # gripper qpos indices in MuJoCo
    q_idx7: int
    q_idx8: int

    # loop state
    mode: str = "RETURNING"
    startup_sent_zero: bool = False
    sent_joint_zero: bool = False
    hold_target: Optional[np.ndarray] = None
    T_filt: Optional[np.ndarray] = None
    vel_filt: Optional[np.ndarray] = None

    # VR→末端目标位姿滤波器（1€ 自适应 + 死区），每臂独立一份
    pose_filter: Optional[Any] = None

    # sender / shared memory
    cmd_shared: Optional[Any] = None   # multiprocessing.Array('d', 7)
    stop_event: Optional[Any] = None   # multiprocessing.Event()
    sender_proc: Optional[Any] = None  # multiprocessing.Process
    q_readback: Optional[Any] = None   # multiprocessing.Array('d', 6)
    q_ready: Optional[Any] = None      # multiprocessing.Event()

    # recording readback（sender 进程持续写，主进程录制读）
    q_actual: Optional[Any] = None        # multiprocessing.Array('d', 6) 实际关节角(rad)
    gripper_actual: Optional[Any] = None  # multiprocessing.Value('d') 实际夹爪开度(um)
    actual_time: Optional[Any] = None     # multiprocessing.Value('d') 最近读回时间(monotonic)

    # 最近下发的夹爪目标（主进程在 _arm_step 里写，录制用）
    last_grip_out: float = 0.0            # 0..1000
    last_grip_vg: float = 0.0             # 0..1

    def stop_sender(self) -> None:
        try:
            if self.stop_event is not None:
                self.stop_event.set()
            if self.sender_proc is not None:
                self.sender_proc.join(timeout=2.0)
                if self.sender_proc.is_alive():
                    self.sender_proc.terminate()
                    self.sender_proc.join(timeout=1.0)
        except Exception:
            pass
        self.sender_proc = None
        self.stop_event = None
        self.cmd_shared = None


@dataclass
class RuntimeContext:
    # shared handles
    teleoperator: VuerTeleop
    cam: Optional[Any]
    viewers: list             # dry-run 时每个臂一个 MuJoCo viewer
    arms: dict                # {"left": ArmRuntime, "right": ArmRuntime}
    rate: Any                 # 主循环限速器（取某个臂的 rate 复用）

    startup_sent_zero: bool = False
    _closed: bool = False

    @property
    def right(self) -> ArmRuntime:
        return self.arms["right"]

    @property
    def left(self) -> ArmRuntime:
        return self.arms["left"]

    def close(self) -> None:
        """Release resources safely (idempotent)."""
        if self._closed:
            return
        self._closed = True

        # --- 先停所有臂的 sender 进程 ---
        for arm in self.arms.values():
            arm.stop_sender()

        # --- viewers ---
        for v in list(self.viewers):
            try:
                if hasattr(v, "close") and callable(v.close):
                    v.close()
            except Exception:
                pass
            # 渲染线程退出后再让 atexit 的 glfw.terminate() 执行；
            # 否则主线程关 GLFW 时渲染线程还在跑，会 use-after-free 段错误。
            t = getattr(v, "_render_thread", None)
            if t is not None and t.is_alive():
                try:
                    t.join(timeout=2.0)
                except Exception:
                    pass
        self.viewers = []

        # --- camera ---
        c = self.cam
        if c is not None:
            try:
                if hasattr(c, "close") and callable(c.close):
                    c.close()
            except Exception:
                pass
            self.cam = None

        # --- teleoperator ---
        t = self.teleoperator
        if t is not None:
            try:
                if hasattr(t, "close") and callable(t.close):
                    t.close()
            except Exception:
                pass
