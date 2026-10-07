# Copyright 2026 Enactic, Inc.
# SPDX-License-Identifier: Apache-2.0
"""ROS 2 bridge: teleop_xr -> OpenArm forward-position controllers.

teleop_xr (``--mode ik``) publishes a ``trajectory_msgs/JointTrajectory`` on
``/joint_trajectory`` whose ``joint_names`` are the actuated joints of the robot
model it fetched from ``/robot_description``. This workspace commands the arms
through the two ``ForwardCommandController`` instances (``Float64MultiArray``,
7 joints each).

The bridge has three responsibilities:

1. **Arm teleop** — map ``/joint_trajectory`` arm joints by *name*
   (order-independent) to ``/left|right_forward_position_controller/commands``.

2. **Gripper** — the index-finger trigger (gamepad button 0, analog ``value``)
   carried in the ``sensor_msgs/Joy`` published by teleop_xr on
   ``xr/controller_{left,right}/joy`` is mapped to the prismatic finger joint
   ``openarm_{left,right}_finger_joint1`` (``gripper_min_m`` .. ``gripper_max_m``).

3. **Home** — a rising edge on the primary button (index 4 = X on the left
   controller / A on the right) commands that arm to its ``left_home`` /
   ``right_home`` joint configuration.

All commands are gated by an enable latch (default off). When teleop_xr stops
publishing (e.g. IK not engaged because the grips are released), the bridge
publishes nothing and the forward-position controllers hold their last command.
"""

from __future__ import annotations

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import JointState, Joy
from std_msgs.msg import Float64MultiArray
from std_srvs.srv import SetBool
from trajectory_msgs.msg import JointTrajectory, JointTrajectoryPoint

# xr-standard gamepad button indices (see teleop_xr.events._BUTTON_INDEX_MAP).
BTN_TRIGGER = 0    # index-finger trigger (analog value)
BTN_PRIMARY = 4    # X (left) / A (right)


class JointTrajectoryBridge(Node):
    def __init__(self):
        super().__init__("jt_bridge")

        self.declare_parameter("input_topic", "/joint_trajectory")
        self.declare_parameter(
            "left_arm_controller_topic", "/left_forward_position_controller/commands")
        self.declare_parameter(
            "right_arm_controller_topic", "/right_forward_position_controller/commands")
        self.declare_parameter(
            "left_gripper_controller_topic", "/left_gripper_controller/joint_trajectory")
        self.declare_parameter(
            "right_gripper_controller_topic", "/right_gripper_controller/joint_trajectory")
        self.declare_parameter(
            "left_arm_joints", [f"openarm_left_joint{i}" for i in range(1, 8)])
        self.declare_parameter(
            "right_arm_joints", [f"openarm_right_joint{i}" for i in range(1, 8)])
        self.declare_parameter("left_gripper_joint", "openarm_left_finger_joint1")
        self.declare_parameter("right_gripper_joint", "openarm_right_finger_joint1")
        self.declare_parameter("enable_on_start", False)
        self.declare_parameter("gripper_deadband", 0.001)

        # --- VR input (gripper + home) ---
        self.declare_parameter("left_joy_topic", "xr/controller_left/joy")
        self.declare_parameter("right_joy_topic", "xr/controller_right/joy")
        self.declare_parameter("gripper_min_m", 0.0)
        self.declare_parameter("gripper_max_m", 0.044)
        self.declare_parameter("invert_gripper", False)
        self.declare_parameter("home_button_index", BTN_PRIMARY)
        self.declare_parameter(
            "left_home", [0.0, -0.8, 0.0, 1.2, 0.0, 0.0, 0.0])
        self.declare_parameter(
            "right_home", [0.0, 0.8, 0.0, 1.2, 0.0, 0.0, 0.0])

        # --- Smooth home motion (quintic interpolation over time) ---
        self.declare_parameter("joint_states_topic", "/joint_states")
        self.declare_parameter("home_duration", 3.0)   # seconds
        self.declare_parameter("home_rate", 50.0)      # waypoint publish Hz
        self.declare_parameter("home_cancel_button_index", 1)  # grip (squeeze)

        self._enabled = bool(self.get_parameter("enable_on_start").value)
        self._gripper_deadband = float(self.get_parameter("gripper_deadband").value)

        self._arm_joints = {
            "left": [str(n) for n in self.get_parameter("left_arm_joints").value],
            "right": [str(n) for n in self.get_parameter("right_arm_joints").value],
        }
        self._gripper_joint = {
            "left": str(self.get_parameter("left_gripper_joint").value),
            "right": str(self.get_parameter("right_gripper_joint").value),
        }
        self._home = {
            "left": [float(x) for x in self.get_parameter("left_home").value],
            "right": [float(x) for x in self.get_parameter("right_home").value],
        }

        self._pub_arm = {
            "left": self.create_publisher(
                Float64MultiArray,
                str(self.get_parameter("left_arm_controller_topic").value), 10),
            "right": self.create_publisher(
                Float64MultiArray,
                str(self.get_parameter("right_arm_controller_topic").value), 10),
        }
        self._pub_gripper = {
            "left": self.create_publisher(
                JointTrajectory,
                str(self.get_parameter("left_gripper_controller_topic").value), 10),
            "right": self.create_publisher(
                JointTrajectory,
                str(self.get_parameter("right_gripper_controller_topic").value), 10),
        }
        self._gripper_last = {"left": None, "right": None}
        self._prev_home_button = {"left": False, "right": False}
        self._warned_missing = set()

        # --- smooth home state ---
        self._joint_positions: dict[str, float] = {}
        self._home_start = {"left": None, "right": None}   # list[float] | None
        self._home_target = {"left": None, "right": None}  # list[float] | None
        self._home_begin = {"left": None, "right": None}   # seconds | None

        self._enable_srv = self.create_service(SetBool, "enable", self._on_enable)

        self.create_subscription(
            JointTrajectory,
            str(self.get_parameter("input_topic").value),
            self._on_trajectory,
            10,
        )

        self.create_subscription(
            Joy, str(self.get_parameter("left_joy_topic").value),
            lambda msg: self._on_joy("left", msg), 10)
        self.create_subscription(
            Joy, str(self.get_parameter("right_joy_topic").value),
            lambda msg: self._on_joy("right", msg), 10)

        self.create_subscription(
            JointState,
            str(self.get_parameter("joint_states_topic").value),
            self._on_joint_states,
            10,
        )

        home_rate = float(self.get_parameter("home_rate").value)
        self._home_timer = self.create_timer(1.0 / home_rate, self._home_tick)

        self.get_logger().info(
            f"jt_bridge ready: {self.get_parameter('input_topic').value} -> "
            f"{self.get_parameter('left_arm_controller_topic').value} / "
            f"{self.get_parameter('right_arm_controller_topic').value} "
            f"(enabled={self._enabled})")

    # ------------------------------------------------------------- callbacks
    def _on_enable(self, req: SetBool.Request, resp: SetBool.Response) -> SetBool.Response:
        self._enabled = bool(req.data)
        resp.success = True
        resp.message = f"jt_bridge {'enabled' if self._enabled else 'disabled'}"
        self.get_logger().info(resp.message)
        return resp

    def _on_trajectory(self, msg: JointTrajectory) -> None:
        if not self._enabled:
            return
        if not msg.points or not msg.joint_names:
            return
        # teleop_xr streams single-point trajectories (fresh IK target each tick);
        # take the last point so a multi-point message still commands its final pose.
        lookup = dict(zip(msg.joint_names, msg.points[-1].positions))

        for side in ("left", "right"):
            if self._home_start[side] is not None:
                continue  # a smooth home motion owns this arm right now
            q = self._extract_ordered(lookup, self._arm_joints[side], side)
            if q is None:
                continue  # hold previous command
            self._pub_arm[side].publish(Float64MultiArray(data=q))

    def _on_joy(self, side: str, msg: Joy) -> None:
        if not self._enabled:
            return
        trigger = self._trigger_value(msg)
        if trigger is not None:
            self._command_gripper(side, self._trigger_to_finger(trigger))
        if self._home_button_edge(side, msg):
            self._command_home(side)
        elif self._home_start[side] is not None and self._cancel_pressed(msg):
            self._cancel_home(side)

    # ------------------------------------------------------------- helpers
    def _extract_ordered(self, lookup, joint_names, side):
        """Return positions in ``joint_names`` order, or None if any joint is
        missing from the trajectory (hold the previous command instead)."""
        q = []
        for name in joint_names:
            if name not in lookup:
                if name not in self._warned_missing:
                    self._warned_missing.add(name)
                    self.get_logger().warn(
                        f"{name} missing from trajectory; holding {side} arm")
                return None
            q.append(float(lookup[name]))
        return q

    def _trigger_value(self, msg: Joy):
        """Recover the analog trigger value from teleop_xr's Joy message.

        teleop_xr's ``build_joy`` appends one value per button onto the gamepad
        axes: ``axes = gamepad_axes + [b.value for b in buttons]``. The trigger
        is button 0, so its value sits right after the gamepad axes.
        """
        n_buttons = len(msg.buttons)
        idx = len(msg.axes) - n_buttons + BTN_TRIGGER
        if 0 <= idx < len(msg.axes):
            return float(msg.axes[idx])
        return None

    def _trigger_to_finger(self, trigger: float) -> float:
        lo = float(self.get_parameter("gripper_min_m").value)
        hi = float(self.get_parameter("gripper_max_m").value)
        t = float(trigger)
        if self.get_parameter("invert_gripper").value:
            t = 1.0 - t
        return lo + t * (hi - lo)

    def _command_gripper(self, side: str, finger: float) -> None:
        last = self._gripper_last[side]
        if last is not None and abs(last - finger) < self._gripper_deadband:
            return
        self._gripper_last[side] = finger

        jt = JointTrajectory()
        jt.joint_names = [self._gripper_joint[side]]
        pt = JointTrajectoryPoint()
        pt.positions = [finger]
        pt.time_from_start.sec = 0
        pt.time_from_start.nanosec = 20000000  # 20 ms
        jt.points = [pt]
        self._pub_gripper[side].publish(jt)

    def _home_button_edge(self, side: str, msg: Joy) -> bool:
        idx = int(self.get_parameter("home_button_index").value)
        pressed = 0 <= idx < len(msg.buttons) and bool(msg.buttons[idx])
        prev = self._prev_home_button[side]
        self._prev_home_button[side] = pressed
        return pressed and not prev  # rising edge only

    def _on_joint_states(self, msg: JointState) -> None:
        for name, pos in zip(msg.name, msg.position):
            self._joint_positions[name] = float(pos)

    def _cancel_pressed(self, msg: Joy) -> bool:
        idx = int(self.get_parameter("home_cancel_button_index").value)
        return 0 <= idx < len(msg.buttons) and bool(msg.buttons[idx])

    def _current_arm_q(self, side: str):
        """Return the arm's last-seen joint positions in arm order, or None if
        /joint_states has not reported every joint yet."""
        q = []
        for name in self._arm_joints[side]:
            if name not in self._joint_positions:
                return None
            q.append(self._joint_positions[name])
        return q

    def _command_home(self, side: str) -> None:
        home = self._home[side]
        if len(home) != len(self._arm_joints[side]):
            self.get_logger().warn(
                f"{side}_home has {len(home)} joints, expected "
                f"{len(self._arm_joints[side])}; ignoring")
            return
        start = self._current_arm_q(side)
        if start is None:
            # No joint feedback yet (e.g. fake hardware still spinning up):
            # fall back to a single direct command rather than silently dropping it.
            self.get_logger().warn(
                f"{side} arm: no /joint_states yet; commanding home directly")
            self._pub_arm[side].publish(Float64MultiArray(data=home))
            return
        self._home_start[side] = start
        self._home_target[side] = home
        self._home_begin[side] = self.get_clock().now().nanoseconds / 1e9
        self.get_logger().info(
            f"{side} arm -> home over {self.get_parameter('home_duration').value}s "
            f"(smooth)")

    def _home_tick(self) -> None:
        duration = float(self.get_parameter("home_duration").value)
        now = self.get_clock().now().nanoseconds / 1e9
        for side in ("left", "right"):
            start = self._home_start[side]
            if start is None:
                continue
            target = self._home_target[side]
            s = (now - self._home_begin[side]) / duration
            if s >= 1.0:
                q = target
                self._pub_arm[side].publish(Float64MultiArray(data=q))
                self._finish_home(side)
                continue
            e = self._quintic(s)
            q = [a + e * (b - a) for a, b in zip(start, target)]
            self._pub_arm[side].publish(Float64MultiArray(data=q))

    @staticmethod
    def _quintic(s: float) -> float:
        """Minimum-jerk (quintic) easing: zero velocity/accel at both ends."""
        s = min(max(s, 0.0), 1.0)
        return 10.0 * s ** 3 - 15.0 * s ** 4 + 6.0 * s ** 5

    def _finish_home(self, side: str) -> None:
        self._home_start[side] = None
        self._home_target[side] = None
        self._home_begin[side] = None
        self.get_logger().info(f"{side} arm arrived home")

    def _cancel_home(self, side: str) -> None:
        self._finish_home(side)
        self.get_logger().info(f"{side} home motion cancelled (grip pressed)")


def main(args=None):
    rclpy.init(args=args)
    node = JointTrajectoryBridge()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
