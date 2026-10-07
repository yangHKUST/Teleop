# Copyright 2026 Enactic, Inc.
# SPDX-License-Identifier: Apache-2.0
"""Serialize a 14-D bimanual plan into a ``trajectory_msgs/JointTrajectory``.

The joint order is fixed to match ``both_arms_joint_trajectory_controller``:
``[openarm_left_joint1..7, openarm_right_joint1..7]`` — the same layout the
B-spline optimizer emits (q14 = [left7, right7]), so conversion is positional.
"""

from __future__ import annotations

from builtin_interfaces.msg import Duration
from trajectory_msgs.msg import JointTrajectory, JointTrajectoryPoint

# Must match both_arms_joint_trajectory_controller (see
# openarm_bringup/config/controllers/openarm_bimanual_controllers.yaml).
JOINT_NAMES = [
    f"openarm_{side}_joint{i}"
    for side in ("left", "right")
    for i in range(1, 8)
]


def to_joint_trajectory(times, q14_path, joint_names=None) -> JointTrajectory:
    """Convert (times, q14_path[n×14]) into a JointTrajectory message."""
    jt = JointTrajectory()
    jt.joint_names = list(joint_names) if joint_names else list(JOINT_NAMES)
    for t, q in zip(times, q14_path):
        p = JointTrajectoryPoint()
        p.positions = [float(x) for x in q]
        sec = int(t)
        p.time_from_start = Duration(sec=sec, nanosec=int(round((t - sec) * 1e9)))
        jt.points.append(p)
    return jt
