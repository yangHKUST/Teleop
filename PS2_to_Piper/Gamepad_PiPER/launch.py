"""Portable launcher; installing or starting does not enable the real arm."""
import argparse
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parent


def parse_args():
    parser = argparse.ArgumentParser(description="PiPER 统一启动入口（默认低速）")
    parser.add_argument("mode", choices=["real", "virtual"])
    parser.add_argument("--backend", choices=["auto", "viser", "none", "mujoco"], default="auto")
    parser.add_argument("--can", default="can0", help="SocketCAN 接口名")
    parser.add_argument("--check", action="store_true", help="仅检查环境和手柄，不连接真机")
    return parser.parse_args()


def main():
    args = parse_args()
    os.chdir(ROOT)
    if not os.environ.get("DISPLAY") and not os.environ.get("WAYLAND_DISPLAY"):
        os.environ["SDL_VIDEODRIVER"] = "dummy"
    os.environ.setdefault("ROS_PACKAGE_PATH", str(ROOT / "ros_packages"))
    backend = args.backend
    if backend == "auto":
        backend = "none" if os.environ.get("SDL_VIDEODRIVER") == "dummy" else "viser"
    if backend == "mujoco":
        if os.environ.get("SDL_VIDEODRIVER") == "dummy":
            raise SystemExit("MuJoCo 原生窗口需要桌面显示；改用 --backend none 或 viser。")
        try:
            import mujoco
        except ImportError:
            raise SystemExit("默认部署不安装 MuJoCo。请安装兼容版本，或使用默认 viser 后端。")

    import pygame
    pygame.init()
    pygame.joystick.init()
    try:
        if pygame.joystick.get_count() == 0:
            raise SystemExit("未发现手柄，请插入 USB 接收器、完成配对后重试。")
        joystick = pygame.joystick.Joystick(0)
        joystick.init()
        print("手柄:", joystick.get_name(), "按钮:", joystick.get_numbuttons(),
              "轴:", joystick.get_numaxes(), "方向键组:", joystick.get_numhats())
        if joystick.get_numbuttons() < 11 or joystick.get_numaxes() < 6 or joystick.get_numhats() < 1:
            raise SystemExit("手柄布局不符合当前默认映射。先按 README 检查并适配映射。")
    finally:
        # Controllers initialize pygame again; leave their device-added events intact.
        pygame.quit()

    if args.check:
        from deployment.check_environment import ik
        print("环境及手柄基础检查通过；按键和扳机实际映射仍需虚拟验证。")
        return

    if args.mode == "real":
        try:
            subprocess.run(["ip", "link", "show", "dev", args.can], check=True)
            # Do not take down an already running bus. Invalid bitrate/config fails.
            subprocess.run(["sudo", "ip", "link", "set", args.can, "up", "type",
                            "can", "bitrate", "1000000"], check=True)
        except (subprocess.CalledProcessError, FileNotFoundError):
            raise SystemExit("CAN 配置失败，未启动真机控制。按 README 检查接口、模块和速率。")
        print("启动低速遥操：速度 10%，因子 0.25；HOME 会使能并回零。", flush=True)
        import main as real_main
        real_main.main(can_name=args.can, visualization_backend=backend,
                       movement_speed=10, speed_factor=0.25)
    else:
        from src.gamepad_pin import RoboticArmController
        controller = RoboticArmController(str(ROOT / "piper/piper.urdf"),
                                          str(ROOT / "piper/meshes"), "/base_link", "link6",
                                          visualization_backend=backend)
        controller.movement_speed_index = 0
        controller.speed_factor_index = 0
        try:
            while True:
                controller.update()
                controller.print_state()
                pygame.time.wait(5)
        except KeyboardInterrupt:
            pygame.quit()
        finally:
            if controller.shutdown_event is not None:
                controller.shutdown_event.set()
            if controller.visualization_process is not None:
                controller.visualization_process.join(timeout=2)


if __name__ == "__main__":
    main()
