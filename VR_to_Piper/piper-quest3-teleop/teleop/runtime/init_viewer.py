# teleop/runtime/init_viewer.py
import queue
import os
import threading

import mujoco
import mujoco.viewer


def init_viewer(model, data, dry_run: bool):
    if not dry_run:
        return None
    if not os.environ.get("DISPLAY") and not os.environ.get("WAYLAND_DISPLAY"):
        print("[DRY RUN] No display; skipping MuJoCo viewer. VR service remains available.")
        return None

    # 复刻 mujoco.viewer.launch_passive，但额外保留渲染线程的句柄。
    # 原因：官方 launch_passive 把 render_loop() 跑在 daemon 线程里，close() 只调
    # sim.exit() 设置退出标志、不 join 线程；退出时 atexit 的 glfw.terminate() 会和
    # 仍在 GLFW 里的渲染线程竞争，导致 use-after-free 段错误（Ctrl+C 时的
    # "段错误 核心已转储"）。这里自己起线程，把句柄挂在 Handle 上，供 context.close() join。
    mujoco.mj_forward(model, data)
    handle_return = queue.Queue(1)

    launch_internal = getattr(mujoco.viewer, "_launch_internal", None)
    if launch_internal is None:
        # 未来 mujoco 版本改了内部 API 时兜底：退回官方实现（仍可能有退出段错误，但不影响运行）。
        viewer = mujoco.viewer.launch_passive(
            model=model, data=data, show_left_ui=False, show_right_ui=False
        )
    else:
        thread = threading.Thread(
            target=launch_internal,
            args=(model, data),
            kwargs=dict(
                run_physics_thread=False,
                handle_return=handle_return,
                key_callback=None,
                show_left_ui=False,
                show_right_ui=False,
            ),
        )
        thread.daemon = True
        thread.start()
        viewer = handle_return.get()
        viewer._render_thread = thread  # 供 context.close() 退出前 join

    mujoco.mjv_defaultFreeCamera(model, viewer.cam)
    print("[DRY RUN] MuJoCo viewer launched.")
    return viewer
