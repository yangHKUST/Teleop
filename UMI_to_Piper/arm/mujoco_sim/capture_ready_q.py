#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""记录 Piper 真机「手拖位姿」为启动准备姿态（非 ROS）。

工作流与 arm/agx_arm_teleop/set_ready_pose.py --watch 完全一致，但直接走 piper_sdk，
无需 ROS / agx_arm_ctrl：

  1. 真机按绿色按钮进入示教模式（绿灯长亮，ctrl_mode=0x02），机械臂失电可拖。
  2. 用手把臂拖到想要的初始位置，松手停稳。
  3. 按【回车】确认记录（无需先退出示教）。
     ⚠ 若改成再按绿色按钮退出示教：固件退出瞬间会把关节弹回旧位置，所以不能在
       退出后再读——脚本在示教期间持续缓存手拖位姿，退出边沿时用缓存值兜底记录。

写入 ``cartesian_ready_q.json``；此后 ``run_vio_teleop.sh --can can0`` 启动时会先
自动前往该准备姿态（--ready-q 缺省即读这个文件）。

用法：
    ./arm/mujoco_sim/run_capture_ready_q.sh --can can0          # 手拖 + 回车确认（推荐）
    ./arm/mujoco_sim/run_capture_ready_q.sh --can can0 --enter  # 已摆好位姿，回车记录
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from piper_umi_core import PiperArm, save_ready_q, READY_FILE  # noqa: E402
from keyboard.keyboard_input import KeyboardReader  # noqa: E402

TEACHING_MODE = 0x02  # piper CtrlMode.Teaching_mode（真机绿色按钮切入）
CAN_MODE = 0x01
STATUS_PERIOD = 0.2   # 状态行刷新周期 (s)，避免刷屏


def _fmt(q: np.ndarray) -> str:
    return ", ".join(f"{v:+.4f}" for v in q)


def _fmt_deg(q: np.ndarray) -> str:
    return ", ".join(f"{v * 57.2958:+.1f}°" for v in q)


def _capture_teach(arm: PiperArm, kb: KeyboardReader) -> np.ndarray | None:
    """监听示教模式：示教期间持续缓存关节角；回车确认或退出边沿返回缓存值。"""
    print("\n" + "=" * 72)
    print("手拖记录准备姿态（示教监听）")
    print("  1) 按真机绿色按钮，进入示教模式（绿灯长亮，臂可拖动）")
    print("  2) 把臂拖到你想要的初始位置，松手停稳")
    print("  3) 按【回车】确认记录（无需先退出示教）")
    print("     （也可再按绿色按钮退出示教，会自动记录手拖位姿）")
    print("  （Ctrl+C 随时取消，不写任何东西）")
    print("=" * 72)

    teach_q: np.ndarray | None = None
    last_mode = arm.read_ctrl_mode()
    enter_prev = False
    last_print = 0.0
    while True:
        keys = kb.read_keys()
        enter_now = "enter" in keys
        enter_edge = enter_now and not enter_prev
        enter_prev = enter_now

        try:
            mode = arm.read_ctrl_mode()
            q = arm.read_joints()
        except Exception as exc:
            print(f"\n[warn] 读反馈异常: {exc}")
            time.sleep(0.1)
            continue

        # 示教期间缓存手拖位姿（退出后固件弹回，位置不再可靠，故只在示教时更新）。
        if mode == TEACHING_MODE:
            teach_q = q

        # 状态行（限频 + ANSI 清尾，避免残字/刷屏）
        now = time.monotonic()
        if now - last_print >= STATUS_PERIOD:
            last_print = now
            if mode == TEACHING_MODE:
                state = "示教中(绿灯)：拖臂到目标位姿，按回车确认"
            elif mode == CAN_MODE:
                state = "CAN 控制：等待按绿色按钮进入示教"
            else:
                state = f"ctrl_mode=0x{mode:02X}：等待按绿色按钮进入示教"
            print(f"\r\033[K[{state}] 关节=[{_fmt(q)}]", end="", flush=True)

        # 回车确认：优先记当前（仍示教）位姿，其次记退出前缓存的手拖位姿。
        if enter_edge:
            target = q if mode == TEACHING_MODE else teach_q
            print()  # 换行
            if target is None:
                print("[fail] 尚未进入示教模式（绿灯未亮），没有可记录的手拖位姿。")
                print("        请先按绿色按钮进入示教，拖到目标位置后再按回车。")
                continue
            print(f"[ok] 记录手拖位姿：[{_fmt(target)}] rad")
            return target

        # 退出示教边沿（2 -> 非 2）：自动用缓存的手拖位姿（兜底）。
        if last_mode == TEACHING_MODE and mode != TEACHING_MODE:
            print()  # 换行
            if teach_q is not None:
                print(f"[ok] 退出示教，自动记录手拖位姿：[{_fmt(teach_q)}] rad")
                return teach_q
            print("[fail] 退出示教，但未捕获到手拖位姿（示教期间无关节反馈）。")
            return None

        last_mode = mode
        time.sleep(0.02)


def _capture_enter(arm: PiperArm) -> np.ndarray | None:
    """已把臂摆好（任意方式），回车读当前关节角记录。"""
    print("\n" + "=" * 72)
    print("直接记录当前位姿")
    print("  （适合：已用 VIO 遥操/示教把臂摆好，现在想固定为准备姿态）")
    print("=" * 72)
    try:
        input("回车确认记录当前关节角（Ctrl+C 取消）... ")
        return arm.read_joints()
    except KeyboardInterrupt:
        print("\n已取消。")
        return None
    except EOFError:
        return None
    except Exception as exc:
        print(f"\n[warn] 读反馈异常: {exc}")
        return None


def main() -> int:
    p = argparse.ArgumentParser(description="记录 Piper 真机手拖位姿为启动准备姿态")
    p.add_argument("--can", default="can0", help="真机 CAN 端口")
    p.add_argument("--joint-speed", type=float, default=30.0,
                   help="PiperArm 每拍单关节最大速度 (deg/s)，仅连接时用于限速基准")
    p.add_argument("--enter", action="store_true",
                   help="不监听示教：已摆好位姿，回车直接记录当前关节角")
    args = p.parse_args()

    print(f"[arm] 连接 {args.can} ...")
    arm = PiperArm(args.can, max_joint_speed_deg_s=args.joint_speed)

    kb = None
    try:
        if args.enter:
            q = _capture_enter(arm)
        else:
            kb = KeyboardReader()
            kb.start()
            q = _capture_teach(arm, kb)
        if q is None:
            return 1
        q = np.asarray(q, dtype=float).reshape(6)
        save_ready_q(q)
        print(f"[save] 准备姿态已写入 {READY_FILE}")
        print(f"       q=[{_fmt(q)}] rad = [{_fmt_deg(q)}]")
        print("\n下次启动 ./arm/mujoco_sim/run_vio_teleop.sh --can can0 时会先自动前往该位姿。")
        return 0
    except KeyboardInterrupt:
        print("\n已取消，未写入。")
        return 1
    finally:
        if kb is not None:
            kb.stop()
        arm.close()


if __name__ == "__main__":
    sys.exit(main())
