# Copyright 2026 Enactic, Inc.
# SPDX-License-Identifier: Apache-2.0
"""CLI to send a ``BimanualPlan`` goal and print the result.

Example:
    ros2 run openarm_bimanual_planner bimanual_plan_client \
        --left "0.40,0.10,0.35" --right "0.40,-0.10,0.35" --duration 4.0
"""

from __future__ import annotations

import argparse
import re
import sys

import rclpy
from geometry_msgs.msg import Pose
from rclpy.action import ActionClient
from rclpy.node import Node

from openarm_bimanual_planner_msgs.action import BimanualPlan


def _xyz(s: str) -> list[float]:
    parts = [float(x) for x in s.split(",")]
    if len(parts) != 3:
        raise argparse.ArgumentTypeError("expected 'x,y,z'")
    return parts


def _pose(xyz: list[float]) -> Pose:
    p = Pose()
    p.position.x, p.position.y, p.position.z = xyz
    p.orientation.w = 1.0
    return p


def main() -> int:
    ap = argparse.ArgumentParser(description="Send a coordinated bimanual plan goal")
    # allow a leading '-' on a coordinate (e.g. --left "-0.1,0.2,0.3")
    ap._negative_number_matcher = re.compile(r"^-?[0-9]")
    ap.add_argument("--left", type=_xyz, required=True, help="left EE target 'x,y,z' (m)")
    ap.add_argument("--right", type=_xyz, required=True, help="right EE target 'x,y,z' (m)")
    ap.add_argument("--duration", type=float, default=0.0, help="desired duration [s]; 0 = default")
    args = ap.parse_args()

    rclpy.init()
    node = rclpy.create_node("bimanual_plan_client")
    client = ActionClient(node, BimanualPlan, "bimanual_plan")

    if not client.wait_for_server(timeout_sec=5.0):
        print("action server 'bimanual_plan' not available", file=sys.stderr)
        return 1

    goal = BimanualPlan.Goal()
    goal.left_ee_pose = _pose(args.left)
    goal.right_ee_pose = _pose(args.right)
    goal.duration = args.duration

    print(f"sending goal L={args.left} R={args.right} duration={args.duration}")
    future = client.send_goal_async(goal)
    rclpy.spin_until_future_complete(node, future)
    goal_handle = future.result()
    if not goal_handle.accepted:
        print("goal rejected", file=sys.stderr)
        return 1

    result_future = goal_handle.get_result_async()
    rclpy.spin_until_future_complete(node, result_future)
    res = result_future.result()
    print(f"success={res.result.success}")
    print(f"message={res.result.message}")

    node.destroy_node()
    rclpy.shutdown()
    return 0 if res.result.success else 2


if __name__ == "__main__":
    sys.exit(main())
