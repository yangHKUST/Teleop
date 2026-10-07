# Copyright 2026 Enactic, Inc.
# SPDX-License-Identifier: Apache-2.0
"""ROS 2 bridge: UMI teleop core (non-ROS, Process A) -> OpenArm right arm.

The UMI teleop core (``openarm_vio_teleop.py``) runs in the conda ``piper_pinocchio``
env, which cannot import rclpy (its pinocchio 4.1.0 clashes with /opt/ros/humble's
broken pinocchio). So the two sides are split across a ZMQ boundary:

  Process A (conda, non-ROS)          Process B (this node, rclpy)
  ────────────────────────────        ─────────────────────────────────────────
  OpenArmBridge.send(q7)      ──PUSH──▶  receive "joints" → joint-space slew
  OpenArmBridge.send_gripper  ──PUSH──▶  receive "gripper" → gripper JointTrajectory
  OpenArmBridge.emergency_stop/freeze ─▶  receive "estop"/"freeze" → hold (stop publishing)
  OpenArmBridge.read_joints   ◀──SUB───  republish /joint_states (right arm 7 joints)

This node owns the safety-critical joint-space slew: the ``ForwardCommandController``
has *no* interpolation or velocity limit, so every "joints" command is rate-limited
here (per-tick max joint delta from ``max_joint_speed_deg_s``) before publishing to
``right_forward_position_controller/commands``. All output is gated by an enable latch
(default on, ``enable_on_start``) and a hold flag (estop/freeze).

Single-arm: only the *right* arm is commanded (UMI single-arm teleop). The left arm
is left in whatever state the bringup put it (gravity-compensated hold).
"""
from __future__ import annotations

import json
import math
import threading

import numpy as np
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import JointState
from std_msgs.msg import Float64MultiArray
from std_srvs.srv import SetBool
from trajectory_msgs.msg import JointTrajectory, JointTrajectoryPoint


class UmiBridge(Node):
    def __init__(self):
        super().__init__("openarm_umi_bridge")

        # ---- ZMQ endpoints (bound by this node, connected by Process A) ----
        self.declare_parameter("cmd_endpoint", "tcp://127.0.0.1:5556")
        self.declare_parameter("fb_endpoint", "tcp://127.0.0.1:5557")

        # ---- arm / gripper topics + joint names ----
        self.declare_parameter(
            "arm_controller_topic", "/right_forward_position_controller/commands")
        self.declare_parameter(
            "gripper_controller_topic", "/right_gripper_controller/joint_trajectory")
        self.declare_parameter(
            "arm_joints", [f"openarm_right_joint{i}" for i in range(1, 8)])
        self.declare_parameter("gripper_joint", "openarm_right_finger_joint1")
        self.declare_parameter("joint_states_topic", "/joint_states")

        # ---- gating / slew ----
        self.declare_parameter("enable_on_start", True)
        self.declare_parameter("max_joint_speed_deg_s", 30.0)
        self.declare_parameter("gripper_max_m", 0.044)
        self.declare_parameter("gripper_deadband", 0.001)
        self.declare_parameter("control_hz", 100.0)
        self.declare_parameter("feedback_hz", 50.0)

        self._arm_joints = [str(n) for n in self.get_parameter("arm_joints").value]
        self._gripper_joint = str(self.get_parameter("gripper_joint").value)
        self._gripper_max_m = float(self.get_parameter("gripper_max_m").value)
        self._gripper_deadband = float(self.get_parameter("gripper_deadband").value)
        self._control_hz = max(1.0, float(self.get_parameter("control_hz").value))

        # ---- state (guarded by _lock; the ZMQ recv thread writes, rclpy reads) ----
        self._lock = threading.Lock()
        self._enabled = bool(self.get_parameter("enable_on_start").value)
        self._hold = False                 # estop / freeze -> stop publishing
        self._target_q = None              # latest client target (7,) or None
        self._current_q = None             # slewed/commanded q (7,) or None (no feedback yet)
        self._latest_feedback = None       # actual q from /joint_states (7,)
        self._gripper_w = None             # latest gripper target (m)
        self._gripper_pending = False
        self._gripper_last = None          # last published gripper (deadband)
        self._max_delta = (math.radians(
            float(self.get_parameter("max_joint_speed_deg_s").value)) / self._control_hz)

        # ---- publishers ----
        self._pub_arm = self.create_publisher(
            Float64MultiArray,
            str(self.get_parameter("arm_controller_topic").value), 10)
        self._pub_gripper = self.create_publisher(
            JointTrajectory,
            str(self.get_parameter("gripper_controller_topic").value), 10)

        # ---- subscriptions ----
        self.create_subscription(
            JointState, str(self.get_parameter("joint_states_topic").value),
            self._on_joint_states, 10)

        # ---- enable service ----
        self._enable_srv = self.create_service(SetBool, "enable", self._on_enable)

        # ---- ZMQ ----
        import zmq
        self._ctx = zmq.Context()
        self._cmd = self._ctx.socket(zmq.PULL)
        self._cmd.setsockopt(zmq.LINGER, 0)
        self._cmd.setsockopt(zmq.RCVHWM, 10)
        self._cmd.bind(str(self.get_parameter("cmd_endpoint").value))

        self._fb = self._ctx.socket(zmq.PUB)
        self._fb.setsockopt(zmq.LINGER, 0)
        self._fb.setsockopt(zmq.SNDHWM, 10)
        self._fb.bind(str(self.get_parameter("fb_endpoint").value))

        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._zmq_loop, name="umi_bridge_zmq",
                                        daemon=True)
        self._thread.start()

        # ---- timers ----
        self._control_timer = self.create_timer(1.0 / self._control_hz, self._control_tick)
        fb_hz = max(1.0, float(self.get_parameter("feedback_hz").value))
        self._fb_timer = self.create_timer(1.0 / fb_hz, self._fb_tick)

        self.get_logger().info(
            f"openarm_umi_bridge ready: cmd={self.get_parameter('cmd_endpoint').value} "
            f"fb={self.get_parameter('fb_endpoint').value} -> "
            f"{self.get_parameter('arm_controller_topic').value} "
            f"(enabled={self._enabled}, "
            f"max_joint_speed={self.get_parameter('max_joint_speed_deg_s').value} deg/s)")

    # ------------------------------------------------------------- ZMQ recv
    def _zmq_loop(self) -> None:
        import zmq
        poller = zmq.Poller()
        poller.register(self._cmd, zmq.POLLIN)
        while not self._stop.is_set():
            try:
                events = dict(poller.poll(timeout=200))
            except Exception:
                break
            if self._cmd not in events:
                continue
            try:
                raw = self._cmd.recv()
            except Exception:
                break
            try:
                msg = json.loads(raw.decode("utf-8", "replace"))
            except (ValueError, UnicodeDecodeError):
                continue
            self._handle_msg(msg)

    def _handle_msg(self, msg: dict) -> None:
        t = msg.get("type")
        if t == "config":
            deg_s = float(msg.get("max_joint_speed_deg_s", 30.0))
            with self._lock:
                self._max_delta = math.radians(max(0.1, deg_s)) / self._control_hz
            print(f"[umi_bridge] config: max_joint_speed={deg_s:g} deg/s")
        elif t == "joints":
            q = msg.get("q")
            if isinstance(q, (list, tuple)) and len(q) == 7:
                with self._lock:
                    self._target_q = np.array([float(v) for v in q])
        elif t == "gripper":
            w = msg.get("width")
            if isinstance(w, (int, float)):
                with self._lock:
                    self._gripper_w = float(w)
                    self._gripper_pending = True
        elif t == "estop":
            with self._lock:
                self._hold = True
                if self._current_q is not None:
                    self._target_q = self._current_q.copy()
            print("[umi_bridge] ESTOP: 停止发布，保持当前位姿")
        elif t == "freeze":
            with self._lock:
                self._hold = True
                if self._current_q is not None:
                    self._target_q = self._current_q.copy()
            print("[umi_bridge] FREEZE: 停止发布，保持当前位姿")
        elif t == "resume":
            with self._lock:
                self._hold = False
            print("[umi_bridge] RESUME: 恢复发布")
        elif t == "enable":
            with self._lock:
                self._enabled = bool(msg.get("data", True))
            print(f"[umi_bridge] enable={'true' if self._enabled else 'false'}")

    # ------------------------------------------------------------- ROS callbacks
    def _on_enable(self, req: SetBool.Request, resp: SetBool.Response) -> SetBool.Response:
        with self._lock:
            self._enabled = bool(req.data)
        resp.success = True
        resp.message = f"openarm_umi_bridge {'enabled' if self._enabled else 'disabled'}"
        self.get_logger().info(resp.message)
        return resp

    def _on_joint_states(self, msg: JointState) -> None:
        lookup = dict(zip(msg.name, msg.position))
        q = []
        for name in self._arm_joints:
            if name not in lookup:
                return  # incomplete message; wait for a full one
            q.append(float(lookup[name]))
        with self._lock:
            self._latest_feedback = np.array(q)
            if self._current_q is None:
                # First real position: initialize the slew state from the actual
                # arm pose so the first command never jumps from 0.
                self._current_q = np.array(q)

    # ------------------------------------------------------------- timers
    def _control_tick(self) -> None:
        with self._lock:
            target = None if self._target_q is None else self._target_q.copy()
            current = None if self._current_q is None else self._current_q.copy()
            max_delta = self._max_delta
            publish_ok = self._enabled and not self._hold
            # gripper
            g_w = self._gripper_w
            g_pending = self._gripper_pending
            self._gripper_pending = False

        # --- arm slew (rate-limited toward target) ---
        if target is not None and current is not None:
            d = target - current
            d = np.clip(d, -max_delta, max_delta)
            new_q = current + d
            with self._lock:
                self._current_q = new_q
            if publish_ok:
                self._pub_arm.publish(Float64MultiArray(data=new_q.tolist()))

        # --- gripper ---
        if g_pending and g_w is not None and publish_ok:
            w = max(0.0, min(g_w, self._gripper_max_m))
            if self._gripper_last is None or abs(w - self._gripper_last) >= self._gripper_deadband:
                self._gripper_last = w
                jt = JointTrajectory()
                jt.joint_names = [self._gripper_joint]
                pt = JointTrajectoryPoint()
                pt.positions = [w]
                pt.time_from_start.sec = 0
                pt.time_from_start.nanosec = 20000000  # 20 ms
                jt.points = [pt]
                self._pub_gripper.publish(jt)

    def _fb_tick(self) -> None:
        with self._lock:
            q = None if self._latest_feedback is None else self._latest_feedback.copy()
        if q is None:
            return
        try:
            self._fb.send(json.dumps(
                {"type": "state", "q": [float(v) for v in q]}).encode("utf-8"))
        except Exception:
            pass

    # ------------------------------------------------------------- shutdown
    def destroy_node(self) -> None:
        self._stop.set()
        try:
            self._cmd.close(linger=0)
        except Exception:
            pass
        try:
            self._fb.close(linger=0)
        except Exception:
            pass
        try:
            self._ctx.term()
        except Exception:
            pass
        if self._thread.is_alive():
            self._thread.join(timeout=1.0)
        super().destroy_node()


def main(args=None):
    rclpy.init(args=args)
    node = UmiBridge()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
