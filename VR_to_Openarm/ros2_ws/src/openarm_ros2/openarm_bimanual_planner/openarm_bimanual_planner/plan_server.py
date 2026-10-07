# Copyright 2026 Enactic, Inc.
# SPDX-License-Identifier: Apache-2.0
"""ROS 2 action server for coordinated bimanual B-spline planning.

Goal: two end-effector target poses (position only in this milestone). The
server reads the current 14 arm joints from ``/joint_states``, forward-kinematics
them, builds straight-line Cartesian ways for each arm, runs the 14-D B-spline
optimizer (with full self-collision avoidance), verifies the result, and
publishes a ``JointTrajectory`` to ``both_arms_joint_trajectory_controller``.

Planning happens in this process (Pinocchio model + geometry). Because the
planner is pure Python and the numeric gradient dominates, a plan can take
tens of seconds; ``time_budget`` (ROS param) caps the optimizer.
"""

from __future__ import annotations

import numpy as np
import rclpy
from rclpy.action import ActionServer
from rclpy.node import Node
from sensor_msgs.msg import JointState
from trajectory_msgs.msg import JointTrajectory

from openarm_bimanual_planner_msgs.action import BimanualPlan
from openarm_bimanual_planner.bimanual_planner import BimanualBSplinePlanner
from openarm_bimanual_planner.serializer import JOINT_NAMES, to_joint_trajectory


class BimanualPlanServer(Node):
    def __init__(self):
        super().__init__("bimanual_plan_server")

        # Declare tunables before building the (expensive) planner.
        self.declare_parameter("time_budget", 120.0)
        self.declare_parameter("ee_tolerance", 0.02)
        self.declare_parameter("collision_margin", 0.02)

        self.get_logger().info("building Pinocchio model + collision geometry...")
        self.planner = BimanualBSplinePlanner()
        self.get_logger().info(
            "collision checker ready: %d pairs [%s]"
            % (self.planner.chk.n_pairs,
               self.planner.chk.summarize(self.planner.chk.cat_counts))
        )

        self._joint_state: dict[str, float] = {}
        self.create_subscription(JointState, "/joint_states", self._on_joint_state, 10)

        self._publisher = self.create_publisher(
            JointTrajectory,
            "/both_arms_joint_trajectory_controller/joint_trajectory",
            10,
        )

        self._action_server = ActionServer(
            self, BimanualPlan, "bimanual_plan",
            execute_callback=self._execute_callback)

    # ------------------------------------------------------------- callbacks
    def _on_joint_state(self, msg: JointState) -> None:
        self._joint_state = dict(zip(msg.name, msg.position))

    def _current_arm_q(self):
        """Return (q_left7, q_right7) from the latest /joint_states or (None, None)."""
        js = self._joint_state
        if not js or any(n not in js for n in JOINT_NAMES):
            return None, None
        return (
            np.array([js[n] for n in JOINT_NAMES[:7]], dtype=float),
            np.array([js[n] for n in JOINT_NAMES[7:]], dtype=float),
        )

    def _pose_xyz(self, pose):
        return np.array([pose.position.x, pose.position.y, pose.position.z], dtype=float)

    # ------------------------------------------------------------------ exec
    def _execute_callback(self, goal_handle):
        result = BimanualPlan.Result()
        feedback = BimanualPlan.Feedback()
        goal = goal_handle.request

        q0_left, q0_right = self._current_arm_q()
        if q0_left is None:
            result.success = False
            result.message = "no /joint_states received yet (is the controller running?)"
            goal_handle.abort()
            return result

        q14 = np.concatenate([q0_left, q0_right])
        q16, _, _ = self.planner.split(q14)
        p0_left = self.planner.ee_pos(q16, "left")
        p0_right = self.planner.ee_pos(q16, "right")

        t_left = self._pose_xyz(goal.left_ee_pose)
        t_right = self._pose_xyz(goal.right_ee_pose)

        n_way = 20
        way_left = np.linspace(p0_left, t_left, n_way)
        way_right = np.linspace(p0_right, t_right, n_way)

        duration = goal.duration if goal.duration > 0 else 4.0
        budget = float(self.get_parameter("time_budget").value)

        self.get_logger().info(
            "planning L %s -> %s  R %s -> %s  (duration %.1fs)"
            % (np.round(p0_left, 3), np.round(t_left, 3),
               np.round(p0_right, 3), np.round(t_right, 3), duration)
        )

        feedback.progress = 0.1
        goal_handle.publish_feedback(feedback)

        times, q14_path, res = self.planner.plan(
            way_left, way_right, q0_left, q0_right,
            duration=duration, time_budget=budget, verbose=False)

        # Task-level acceptance: did we reach the goals, and is the path clear?
        q16_last, _, _ = self.planner.split(np.asarray(q14_path[-1], float))
        e_left = float(np.linalg.norm(self.planner.ee_pos(q16_last, "left") - t_left))
        e_right = float(np.linalg.norm(self.planner.ee_pos(q16_last, "right") - t_right))
        e_final = max(e_left, e_right)

        margin = float(self.get_parameter("collision_margin").value)
        viol = self.planner.chk.check_trajectory(
            [self.planner.split(np.asarray(q, float))[0] for q in q14_path], margin)

        tol = float(self.get_parameter("ee_tolerance").value)
        if viol is not None or e_final > tol:
            result.success = False
            result.message = (
                f"plan rejected: max_ee_err={e_final:.3f}m (tol {tol:.3f}) "
                f"collision_at_sample={viol}")
            self.get_logger().warn(result.message)
            goal_handle.abort()
            return result

        jt = to_joint_trajectory(times, q14_path)
        self._publisher.publish(jt)

        result.success = True
        result.message = (
            f"published {len(q14_path)}-pt {duration:.1f}s trajectory; "
            f"max_ee_err={e_final:.3f}m; opt_success={bool(res.success)}")
        self.get_logger().info(result.message)
        goal_handle.succeed()
        return result


def main(args=None):
    rclpy.init(args=args)
    node = BimanualPlanServer()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
