# teleop/app.py
import time
import numpy as np
import mujoco

from .VuerTeleop import VuerTeleop
from . import config
from .runtime.context import RuntimeContext, ArmRuntime
from .runtime.init_camera import init_camera
from .runtime.init_fk_mapper import init_fk_and_start, init_mapper
from .runtime.init_mink import init_mink
from .runtime.init_viewer import init_viewer
from .runtime.init_mujoco import init_T_zero
from .runtime.init_mujoco import init_mujoco_state_zero
from .runtime.init_mujoco import init_gripper_indices
from .runtime.init_right_controller import RightController, RightControllerConfig

from .utils.joint123_near_zero import joints123_near_zero
from .utils.runtime_reset import reset_to_zero_like_init
from .control.ik_stepper import ik_step
from .control.pose_filter import PoseFilter, PoseFilterConfig

from multiprocessing import Process, Event, Array, Value
from .runtime.piper_send_process import piper_sender

from .utils.profiler import LoopProfiler


def _make_controller() -> RightController:
    # 左右手按键布局完全同构（TeleVision.py 里 left_state/right_state 都是 14 个数），
    # 所以左右臂可复用同一个 RightController 配置。
    ctrl = RightController(RightControllerConfig(
        gripper_mode="analog",
        gripper_out_min=0,
        gripper_out_max=1000,
        gripper_close_when_high=True,
        gripper_alpha=0.35,
        idx_squeeze_pressed=1,
        idx_return_pressed=4,
    ))
    ctrl.reset(open_gripper=True)
    return ctrl


def _build_arm(side: str, can_port: str, dry_run: bool, debug_mapper: bool) -> ArmRuntime:
    fk, q_zero, EE_START, R_ee0 = init_fk_and_start()
    mapper = init_mapper(EE_START, R_ee0, debug=debug_mapper)
    model, data, configuration, tasks, limits, solver, rate = init_mink(q_zero)

    T_zero = init_T_zero(EE_START, R_ee0)
    init_mujoco_state_zero(model, data)
    mujoco.mj_forward(model, data)

    q_idx7, q_idx8 = init_gripper_indices(model)

    # VR→末端目标位姿滤波（1€ 自适应 + 死区），抑制手持遥操的手抖
    pose_filter = PoseFilter(PoseFilterConfig(
        enabled=bool(getattr(config, "POSE_FILTER_ENABLED", True)),
        fc_min=float(getattr(config, "POSE_FC_MIN", 1.0)),
        fc_d=float(getattr(config, "POSE_FC_D", 1.0)),
        beta_pos=float(getattr(config, "POSE_BETA_POS", 14.0)),
        beta_rot=float(getattr(config, "POSE_BETA_ROT", 3.0)),
        deadband_pos=float(getattr(config, "POSE_DEADBAND_POS", 0.002)),
        deadband_rot=float(getattr(config, "POSE_DEADBAND_ROT", 0.0105)),
        deadband_pos_inner=float(getattr(config, "POSE_DEADBAND_POS_INNER", 0.0007)),
        deadband_rot_inner=float(getattr(config, "POSE_DEADBAND_ROT_INNER", 0.0035)),
    ))

    # shared memory：每个臂独立一份 cmd/读回/事件
    cmd_shared = Array('d', 7, lock=True)
    stop_event = Event()
    q_readback = Array('d', 6, lock=True)
    q_readback[:] = [float("nan")] * 6
    q_ready = Event()

    # 录制读回：sender 进程周期性写实际关节角/夹爪开度
    q_actual = Array('d', 6, lock=True)
    q_actual[:] = [float("nan")] * 6
    gripper_actual = Value('d', float("nan"), lock=True)
    actual_time = Value('d', 0.0, lock=True)

    with cmd_shared.get_lock():
        for i in range(6):
            cmd_shared[i] = 0.0
        cmd_shared[6] = 0.0

    send_hz = float(getattr(config, "SEND_RATE_HZ", 100.0))
    readback_hz = float(getattr(config, "RECORD_READBACK_HZ", 20.0))
    sender_proc = Process(
        target=piper_sender,
        args=(side, can_port, dry_run, cmd_shared, stop_event, send_hz, q_readback, q_ready,
              q_actual, gripper_actual, actual_time, readback_hz),
        daemon=True,
    )
    sender_proc.start()

    return ArmRuntime(
        side=side,
        can_port=can_port,
        controller=_make_controller(),
        fk=fk, mapper=mapper,
        model=model, data=data, configuration=configuration,
        tasks=tasks, limits=limits, solver=solver, rate=rate,
        T_zero=T_zero,
        last_q=q_zero.copy(),
        q_idx7=q_idx7, q_idx8=q_idx8,
        pose_filter=pose_filter,
        cmd_shared=cmd_shared,
        stop_event=stop_event,
        sender_proc=sender_proc,
        q_readback=q_readback,
        q_ready=q_ready,
        q_actual=q_actual,
        gripper_actual=gripper_actual,
        actual_time=actual_time,
    )


def build_runtime(args) -> RuntimeContext:
    print("[INIT] Arm configuration: " + ", ".join(
        f"{side}={port}" for side, port in args.arm_ports.items()
    ))
    teleoperator = VuerTeleop()
    rt = RuntimeContext(
        teleoperator=teleoperator,
        cam=None,
        viewers=[],
        arms={},
        rate=None,
    )
    try:
        rt.cam = init_camera(teleoperator, args.camera)
        for side, can_port in args.arm_ports.items():
            rt.arms[side] = _build_arm(side, can_port, args.dry_run, args.debug_mapper)
        rt.rate = next(iter(rt.arms.values())).rate

        # dry-run：只为实际配置的臂创建窗口。
        if args.dry_run:
            for arm in rt.arms.values():
                v = init_viewer(arm.model, arm.data, dry_run=True)
                if v is not None:
                    rt.viewers.append(v)
    except BaseException:
        rt.close()
        raise
    return rt


def _check_sender(arm: ArmRuntime) -> None:
    if (arm.stop_event is not None and arm.stop_event.is_set()) or (
        arm.sender_proc is None or not arm.sender_proc.is_alive()
    ):
        raise RuntimeError(
            f"[sender][{arm.side}][{arm.can_port}] stopped; "
            "teleoperation aborted. Check the sender/safety log above."
        )


def _startup_arm(arm: ArmRuntime, dry_run: bool = False) -> None:
    # 等 sender 读回机械臂实际关节角（避免不在零位时启动即被命令到 [0..0] 跳变）
    deadline = time.monotonic() + 10.0
    if arm.q_ready is None:
        raise RuntimeError(f"[startup][{arm.side}] missing sender readiness event")
    while not arm.q_ready.wait(timeout=0.1):
        _check_sender(arm)
        if time.monotonic() >= deadline:
            raise RuntimeError(f"[startup][{arm.side}][{arm.can_port}] joint readback timeout")
    if not dry_run:
        _check_sender(arm)
    rb = None
    if arm.q_readback is not None:
        cand = np.array(arm.q_readback[:], dtype=float)
        if cand.size == 6 and np.all(np.isfinite(cand)):
            rb = cand
    if rb is None:
        raise RuntimeError(f"[startup][{arm.side}] no valid joint readback; aborting")
    else:
        print(f"[startup][{arm.side}] initialize last_q from readback (rad):",
              [round(float(x), 4) for x in rb])
    arm.last_q[:6] = rb

    # viewer/MuJoCo 状态也同步到 last_q
    for k in range(6):
        j = arm.model.joint(f"joint{k+1}")
        adr = int(np.asarray(j.qposadr).item())
        arm.data.qpos[adr] = float(arm.last_q[k])
        vadr = int(np.asarray(j.dofadr).item())
        arm.data.qvel[vadr] = 0.0
    mujoco.mj_forward(arm.model, arm.data)

    with arm.cmd_shared.get_lock():
        for i in range(6):
            arm.cmd_shared[i] = float(arm.last_q[i])
        arm.cmd_shared[6] = 0.0


def _arm_step(rt: RuntimeContext, arm: ArmRuntime, pose7, controller_mat_vuer, prof) -> None:
    """单个臂的一帧：手柄状态 -> 状态机 -> IK -> 骨架 -> 写共享内存。"""

    t = time.perf_counter()
    state = rt.teleoperator.right_state if arm.side == "right" else rt.teleoperator.left_state
    r = arm.controller.update(rt.teleoperator, state=state)
    prof.add(f"{arm.side}_update", time.perf_counter() - t)

    grip_hw = r.grip_out
    squeeze_holding = r.holding
    squeeze_just_pressed = r.just_pressed

    # 记录下发的夹爪目标（录制用）
    arm.last_grip_out = float(grip_hw)
    arm.last_grip_vg = float(getattr(r, "grip_vg", 0.0))

    t = time.perf_counter()
    T_cur = arm.fk.compute_fk(arm.last_q)
    prof.add(f"{arm.side}_fk", time.perf_counter() - t)

    t = time.perf_counter()
    transition = False
    target_T = None

    if arm.mode == "RETURNING":
        # 关节空间直接回零（避免任务空间 IK 把臂带进翻转构型回不到零）
        q_cur = np.asarray(arm.last_q[:6], dtype=float)
        q_zero = np.zeros(6, dtype=float)
        step_rad = float(getattr(config, "RETURN_JOINT_SPEED", 0.5)) * float(rt.rate.dt)
        dq = np.clip(q_zero - q_cur, -step_rad, step_rad)
        arm.last_q[:6] = q_cur + dq

        q_full = arm.configuration.q.copy()
        q_full[:6] = arm.last_q[:6]
        arm.configuration.update(q=q_full)
        arm.data.qpos[:] = arm.configuration.q
        mujoco.mj_forward(arm.model, arm.data)

        if joints123_near_zero(arm.last_q, tol_deg=5.0):
            arm.mode = "AT_ZERO"
            arm.mapper.reset_state(keep_neutral_target=False)
            if not arm.sent_joint_zero:
                reset_to_zero_like_init(arm, np.zeros(6, dtype=float))
                arm.sent_joint_zero = True

    elif arm.mode == "AT_ZERO":
        target_T = arm.T_zero
        if squeeze_just_pressed:
            controller_anchor = np.asarray(controller_mat_vuer)[:3, 3].copy()
            rt.teleoperator.tv.enable_skeleton(arm.side, controller_anchor)

            reset_to_zero_like_init(arm, np.zeros(6, dtype=float))
            arm.mapper.set_neutral(arm.T_zero, pose7)
            if arm.pose_filter is not None:
                arm.pose_filter.reset()
            arm.mode = "TELEOP"
            transition = True

    elif arm.mode == "HOLD":
        target_T = arm.hold_target if arm.hold_target is not None else T_cur

        if squeeze_just_pressed:
            controller_anchor = np.asarray(controller_mat_vuer)[:3, 3].copy()
            rt.teleoperator.tv.enable_skeleton(arm.side, controller_anchor)

            arm.mapper.set_neutral(target_T, pose7)
            arm.T_filt = None
            arm.vel_filt = None
            if arm.pose_filter is not None:
                arm.pose_filter.reset()
            arm.mode = "TELEOP"
            transition = True
        elif r.go_to_zero:
            arm.mode = "RETURNING"
            arm.T_filt = None
            arm.vel_filt = None
            arm.sent_joint_zero = False
            if hasattr(arm.mapper, "neutral_target_T"):
                arm.mapper.neutral_target_T = None

    elif arm.mode == "TELEOP":
        target_T = arm.mapper.compute_target_T(pose7)
        if target_T is not None and arm.pose_filter is not None:
            target_T = arm.pose_filter.filter(target_T, dt=float(rt.rate.dt))
        if not squeeze_holding:
            rt.teleoperator.tv.clear_robot_joints(arm.side)
            arm.hold_target = T_cur.copy()
            arm.mode = "HOLD"
            arm.T_filt = None
            arm.vel_filt = None

    prof.add(f"{arm.side}_mode", time.perf_counter() - t)

    # 进入 TELEOP 的过渡帧：本帧跳过 IK/骨架/发送（与单臂版 continue 语义一致）
    if transition:
        return

    # IK step（target_T 为 None 或解算结果非有限时，本帧保持 last_q 不动，避免 NaN 下发给电机）
    if arm.mode not in ("AT_ZERO", "RETURNING") and target_T is not None:
        t = time.perf_counter()
        try:
            dt = float(rt.rate.dt)
            new_q = ik_step(
                arm.model, arm.data, arm.configuration,
                arm.tasks, arm.limits, arm.solver, dt,
                arm.last_q, target_T,
                grip_hw, arm.q_idx7, arm.q_idx8,
                debug_qpos_check=False,
            )
            if np.all(np.isfinite(new_q)):
                arm.last_q = new_q
            else:
                print(f"[mink IK][{arm.side}] non-finite result -> keep last_q")
        except Exception as e:
            print(f"[mink IK][{arm.side}] Failed -> keep last_q:", repr(e))
        prof.add(f"{arm.side}_ik", time.perf_counter() - t)

    # skeleton render（仅 TELEOP）
    if arm.mode == "TELEOP":
        t = time.perf_counter()
        joints_xyz = arm.fk.fk_all_joint_positions(arm.last_q)
        rt.teleoperator.tv.set_robot_joints(arm.side, joints_xyz)
        prof.add(f"{arm.side}_skeleton", time.perf_counter() - t)

    # send to robot
    t = time.perf_counter()
    with arm.cmd_shared.get_lock():
        for i in range(6):
            arm.cmd_shared[i] = float(arm.last_q[i])
        arm.cmd_shared[6] = float(grip_hw * 1000.0)
    prof.add(f"{arm.side}_cmd", time.perf_counter() - t)


def run_loop(args, rt: RuntimeContext):
    prof = LoopProfiler(report_period=1.0)

    # 数据录制发布器（ZMQ PUB，record_data.py 独立订阅落盘）。被动且非阻塞：
    # 没有订阅者时消息直接丢弃，不影响控制回路。绑定失败则禁用录制。
    rec_pub = None
    try:
        from .recorder_pub import RecorderPub, build_record
        endpoint = getattr(config, "RECORD_ENDPOINT", "tcp://127.0.0.1:5559")
        rec_pub = RecorderPub(endpoint)
        print(f"[record] publishing teleop data on {endpoint}", flush=True)
    except Exception as e:
        print(f"[record] publisher disabled: {e}", flush=True)

    try:
        while True:
            t_loop0 = time.perf_counter()

            # viewer 存活检查
            t = time.perf_counter()
            if rt.viewers:
                for v in list(rt.viewers):
                    if not v.is_running():
                        print("[DRY RUN] MuJoCo viewer closed; continuing without it.")
                        rt.viewers.remove(v)
            prof.add("viewer_alive_check", time.perf_counter() - t)

            # startup（两个臂都完成读回后再进主循环）
            if not rt.startup_sent_zero:
                t_startup = time.perf_counter()
                for arm in rt.arms.values():
                    _startup_arm(arm, dry_run=args.dry_run)
                rt.startup_sent_zero = True
                prof.add("startup_block", time.perf_counter() - t_startup)

                t = time.perf_counter()
                rt.rate.sleep()
                prof.add("rate_sleep", time.perf_counter() - t)

                prof.add("loop_total", time.perf_counter() - t_loop0)
                prof.tick_loop()
                if prof.should_report():
                    prof.report_and_reset()
                continue

            if not args.dry_run:
                for arm in rt.arms.values():
                    _check_sender(arm)

            # 左右手柄位姿
            t = time.perf_counter()
            right_pose_T = rt.teleoperator.step()
            left_pose_T = rt.teleoperator.step_left()
            prof.add("teleop_step", time.perf_counter() - t)

            right_mat_vuer = rt.teleoperator.tv.right_controller.copy()
            left_mat_vuer = rt.teleoperator.tv.left_controller.copy()

            poses = {"right": right_pose_T, "left": left_pose_T}
            matrices = {"right": right_mat_vuer, "left": left_mat_vuer}
            for side, arm in rt.arms.items():
                pose7, mat_vuer = poses[side], matrices[side]
                _arm_step(rt, arm, pose7, mat_vuer, prof)

            # 发布本帧录制数据
            if rec_pub is not None:
                rec_pub.publish(build_record(rt, right_pose_T, left_pose_T))

            # debug：每秒打印两个臂的模式与关节角
            _mn = time.perf_counter()
            if _mn - getattr(rt, "_dbg_mode_last", 0.0) > 1.0:
                rt._dbg_mode_last = _mn
                parts = []
                for side, arm in rt.arms.items():
                    parts.append(
                        f"{side}:mode={arm.mode} q123={np.degrees(arm.last_q[:3]).round(1).tolist()} "
                        f"q456={np.degrees(arm.last_q[3:6]).round(1).tolist()}"
                    )
                print("[MODE] " + " | ".join(parts), flush=True)

            # camera
            if rt.cam is not None:
                t = time.perf_counter()
                rt.cam.step()
                prof.add("camera_step", time.perf_counter() - t)

            # viewer sync（dry-run）
            for v in rt.viewers:
                t = time.perf_counter()
                v.sync()
                prof.add("viewer_sync", time.perf_counter() - t)

            t = time.perf_counter()
            rt.rate.sleep()
            prof.add("rate_sleep", time.perf_counter() - t)

            prof.add("loop_total", time.perf_counter() - t_loop0)
            prof.tick_loop()

            if prof.should_report():
                prof.report_and_reset()

    except KeyboardInterrupt:
        pass
    finally:
        if rec_pub is not None:
            try:
                rec_pub.close()
            except Exception:
                pass
