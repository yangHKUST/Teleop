import time
import signal
import numpy as np

from .init_driver import init_driver
from ..control.sender import piper_send_jointctrl
from ..piper.safety import read_joint_radians
from .. import config

def piper_sender(side: str, can_port: str, dry_run: bool, cmd_shared, stop_event, send_hz: float,
                 q_readback=None, q_ready=None,
                 q_actual=None, gripper_actual=None, actual_time=None,
                 readback_hz: float = 20.0):
    # 主进程统一处理 Ctrl+C，再通过 stop_event 通知 sender 退出。
    signal.signal(signal.SIGINT, signal.SIG_IGN)
    driver = None
    try:
        driver = init_driver(can_port, dry_run)
        if driver is None:
            # dry-run：无硬件，读回置零并通知主进程，避免主进程阻塞等待
            if q_readback is not None:
                q_readback[:] = [0.0] * 6
            if q_ready is not None:
                q_ready.set()
            return

        # 启动时读回机械臂实际关节角，主进程据此初始化 last_q，
        # 避免机械臂不在零位时启动即被命令到 [0..0] 造成位姿跳变。
        if q_readback is not None:
            try:
                rad = read_joint_radians(driver, config.RAD_TO_PIPER)
                if rad is not None and len(rad) >= 6 and np.all(np.isfinite(rad[:6])):
                    q_readback[:] = rad[:6]
                    # 同时把实际关节角写回 cmd_shared，这样发送循环首帧发的就是当前位姿，
                    # 而不是 cmd_shared 里初始的零，避免启动瞬间命令跳变。
                    with cmd_shared.get_lock():
                        for i in range(6):
                            cmd_shared[i] = float(rad[i])
                    print(f"[sender][{side}] joint readback (rad):", [round(float(x), 4) for x in rad[:6]])
                else:
                    raise RuntimeError("joint readback returned None/unexpected")
            except Exception as e:
                raise RuntimeError(f"[sender][{side}] joint readback failed") from e
        if q_ready is not None:
            q_ready.set()

        send_period = 1.0 / max(float(send_hz), 1e-6)
        readback_period = 1.0 / max(float(readback_hz), 1e-6)
        next_send = time.monotonic()
        last_readback = 0.0

        while not stop_event.is_set():
            now = time.monotonic()

            # 周期读回实际关节角 + 夹爪开度，仅用于录制（不参与控制回路）。
            if (q_actual is not None or gripper_actual is not None) and now - last_readback >= readback_period:
                last_readback = now
                try:
                    rad = read_joint_radians(driver, config.RAD_TO_PIPER)
                    if rad is not None and len(rad) >= 6 and q_actual is not None:
                        with q_actual.get_lock():
                            q_actual[:] = rad[:6]
                    g = driver.get_gripper_position()
                    if g is not None and gripper_actual is not None:
                        with gripper_actual.get_lock():
                            gripper_actual.value = float(g[0])  # um
                    if actual_time is not None:
                        actual_time.value = now
                except Exception:
                    pass  # 读回失败不影响控制回路

            if now < next_send:
                time.sleep(min(next_send - now, 0.005))
                continue

            with cmd_shared.get_lock():
                q = np.array(cmd_shared[0:6], dtype=float)
                grip_hw = int(cmd_shared[6])

            next_send = piper_send_jointctrl(
                driver, dry_run, q, grip_hw,
                next_send, send_period, config.RAD_TO_PIPER
            )

    except Exception as exc:
        stop_event.set()
        print(f"[sender][{side}][{can_port}] failed: {exc!r}", flush=True)
        raise
    finally:
        try:
            if driver is not None:
                driver.close()
        except Exception:
            pass
