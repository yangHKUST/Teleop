#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""交互式拖动 OpenArm 右臂并记录「准备位姿」（仿真 / 真机通用）。

先启动 ROS2 侧（fake hardware + forward_position_controller + RViz）：
    cd ~/UMI_to_OpenArm/UMI_to_arm/arm/mujoco_sim
    ./run_openarm_bridge.sh use_fake_hardware:=true      # 纯仿真，不起 UMI 遥操核心

再开一个终端跑本脚本（系统 python，含 rclpy）：
    source /opt/ros/humble/setup.bash
    source ~/ros2_ws/install/setup.bash
    python3 nudge_ready_pose.py

原理：向 /right_forward_position_controller/commands 发 7 关节目标（Float64MultiArray），
ForwardCommandController 会锁存最后一个目标并逐周期下发 → 机械臂移动到目标并「保持住」。
本脚本只对目标做增量/绝对值修改，每次改动即时下发。

交互命令：
    show                打印当前目标 7 关节（rad + deg）
    j<N> <+/-><val>     第 N 关节(1..7) 相对增量，如 `j2 +0.1`、`j2 -0.15`；不带符号=设绝对值
    set q1 q2 ... q7    设 7 个绝对关节角(rad)
    home                回到内置默认 home [0, 0.8, 0, 1.2, 0, 0, 0]
    limits              打印各关节限位(rad)
    save                把当前目标写入 cartesian_ready_q_openarm.json（即准备位姿）
    quit                退出
"""
from __future__ import annotations

import json
import sys
import threading
from pathlib import Path

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import JointState
from std_msgs.msg import Float64MultiArray

# 仓库根 = 本文件上两级（arm/mujoco_sim/.. -> UMI_to_arm），与 openarm_umi_core 的
# REPO_ROOT 一致；准备位姿写到 openarm_umi_core 的 READY_FILE。
REPO_ROOT = Path(__file__).resolve().parents[2]
READY_FILE = REPO_ROOT / "cartesian_ready_q_openarm.json"

# 7 关节限位(rad)，与 openarm_umi_core.OPENARM_QMIN/QMAX 一致（权威来源仍以 URDF 为准）。
QMIN = [-1.396263, -0.174533, -1.570796, 0.0, -1.570796, -0.785398, -1.570796]
QMAX = [3.490659, 3.316125, 1.570796, 2.443461, 1.570796, 0.785398, 1.570796]

DEFAULT_HOME = [0.0, 0.8, 0.0, 1.2, 0.0, 0.0, 0.0]
JOINT_NAMES = [f"openarm_right_joint{i}" for i in range(1, 8)]


class Nudger(Node):
    def __init__(self):
        super().__init__("nudge_ready_pose")
        self.pub = self.create_publisher(
            Float64MultiArray, "/right_forward_position_controller/commands", 10
        )
        self.sub = self.create_subscription(
            JointState, "/joint_states", self._on_joint_states, 10
        )
        self.q_state = None  # 最近一次 /joint_states 里的右臂 7 关节

    def _on_joint_states(self, msg: JointState):
        names = list(msg.name)
        pos = list(msg.position)
        q = [None] * 7
        for i, n in enumerate(JOINT_NAMES):
            if n in names:
                q[i] = pos[names.index(n)]
        if all(v is not None for v in q):
            self.q_state = q

    def send(self, q):
        m = Float64MultiArray()
        m.data = list(q)
        self.pub.publish(m)


def clamp(q):
    return [max(mn, min(mx, v)) for v, mn, mx in zip(q, QMIN, QMAX)]


def fmt(q):
    deg = [v * 180.0 / 3.141592653589793 for v in q]
    rad = " ".join(f"{v:+.4f}" for v in q)
    dg = " ".join(f"{v:+7.1f}" for v in deg)
    return rad, dg


def print_help():
    print(
        "命令: show | j<N> <+/-><val> | set q1..q7 | home | limits | save | quit"
    )


def main():
    rclpy.init()
    node = Nudger()
    spin = threading.Thread(target=rclpy.spin, args=(node,), daemon=True)
    spin.start()

    # 等第一帧 /joint_states，把目标初始化为机械臂当前位姿（否则用默认 home）。
    target = None
    for _ in range(50):  # 最多 ~5s
        if node.q_state is not None:
            target = list(node.q_state)
            break
        import time

        time.sleep(0.1)
    if target is None:
        target = list(DEFAULT_HOME)
        print("[warn] 5s 内未收到 /joint_states，目标暂用默认 home")

    rad, dg = fmt(target)
    print(f"当前目标: rad [{rad}]")
    print(f"           deg [{dg}]")
    print_help()

    try:
        while True:
            line = input("> ").strip()
            if not line:
                continue
            parts = line.split()
            cmd = parts[0].lower()

            if cmd in ("q", "quit", "exit"):
                break

            elif cmd == "show":
                rad, dg = fmt(target)
                print(f"目标 rad [{rad}]")
                print(f"     deg [{dg}]")
                if node.q_state is not None:
                    sr, sd = fmt(node.q_state)
                    print(f"反馈 rad [{sr}] (实际关节反馈)")

            elif cmd == "home":
                target = list(DEFAULT_HOME)
                node.send(target)
                rad, dg = fmt(target)
                print(f"→ 默认 home  deg [{dg}]")

            elif cmd == "limits":
                print("关节   qmin        qmax")
                for i in range(7):
                    print(f"  j{i+1}  {QMIN[i]:+.4f}  {QMAX[i]:+.4f}")

            elif cmd.startswith("j"):
                # j<N> <val>：val 带 +/- 为相对增量，否则为设绝对值。
                if len(parts) != 3:
                    print("用法: j<N> <+/-><val>  例: j2 +0.1")
                    continue
                try:
                    idx = int(parts[0][1:]) - 1
                    val = float(parts[2])
                except ValueError:
                    print("无法解析关节号/数值")
                    continue
                if not (0 <= idx < 7):
                    print("关节号须在 1..7")
                    continue
                tok = parts[2]
                if tok.startswith("+") or tok.startswith("-"):
                    target[idx] += val
                else:
                    target[idx] = val
                target = clamp(target)
                node.send(target)
                rad, dg = fmt(target)
                print(f"→ 目标 deg [{dg}]")

            elif cmd == "set":
                if len(parts) != 8:
                    print("用法: set q1 q2 q3 q4 q5 q6 q7")
                    continue
                try:
                    target = [float(x) for x in parts[1:8]]
                except ValueError:
                    print("7 个数值解析失败")
                    continue
                target = clamp(target)
                node.send(target)
                rad, dg = fmt(target)
                print(f"→ 目标 deg [{dg}]")

            elif cmd == "save":
                q = clamp(target)
                READY_FILE.write_text(
                    json.dumps([round(float(v), 6) for v in q]) + "\n",
                    encoding="utf-8",
                )
                rad, dg = fmt(q)
                print(f"已保存准备位姿 → {READY_FILE}")
                print(f"  rad [{rad}]")
                print(f"  deg [{dg}]")

            else:
                print_help()

    except (EOFError, KeyboardInterrupt):
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
