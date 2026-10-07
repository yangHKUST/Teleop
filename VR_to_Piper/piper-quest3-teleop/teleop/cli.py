# teleop/cli.py
import argparse

def parse_args(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("--can-left", type=str, default=None, help="左臂 CAN 口 (默认 can0)")
    p.add_argument("--can-right", type=str, default=None, help="右臂 CAN 口 (默认 can1)")
    p.add_argument("--can", type=str, default=None, help="单臂模式：只连接此 CAN 口，使用右手柄控制")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--config", type=str, default="inspire_hand.yml")
    p.add_argument("--camera", type=int, default=None)
    p.add_argument("--print-freq", action="store_true")
    p.add_argument("--debug-mapper", action="store_true")

    args = p.parse_args(argv)
    # 单口用法只创建一个 sender，禁止两个控制进程向同一条 CAN 总线发指令。
    if args.can is not None:
        if args.can_left is not None or args.can_right is not None:
            p.error("--can 是单臂模式，不能与 --can-left/--can-right 同时使用")
        args.can_right = args.can
        args.arm_ports = {"right": args.can}
    else:
        if args.can_left is None:
            args.can_left = "can0"
        if args.can_right is None:
            args.can_right = "can1"
        if args.can_left == args.can_right:
            p.error("双臂必须使用不同的 CAN 口；单臂请用 --can can0")
        args.arm_ports = {"right": args.can_right, "left": args.can_left}
    return args
