# teleop/teleop_real_arm.py
from .cli import parse_args


def main():
    args = parse_args()
    # 先验证参数，避免 Vuer 导入时的参数解析截获 --help。
    from .app import build_runtime, run_loop

    rt = None
    try:
        rt = build_runtime(args)
        run_loop(args, rt)
    except KeyboardInterrupt:
        print("\n[Main] Interrupted")
    finally:
        # Ctrl+C/启动失败仅停止发送并释放资源，回零通过手柄按钮显式触发。
        if rt is not None:
            rt.close()


if __name__ == "__main__":
    main()
