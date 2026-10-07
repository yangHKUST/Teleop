#!/usr/bin/env python3
"""
gripper_agx_bridge — 手持夹爪 → AGX 机械臂夹爪遥操桥接。

订阅手持夹爪发布的 /gripper/width_m (Float32, 物理两指间距 m)，做 1:1 线性映射后
发布 JointState{name:[gripper], position:[width], effort:[force]} 到
/control/joint_states，驱动 AGX 机械臂夹爪 (effector_type=agx_gripper)。

宽度映射（默认 1:1，可通过参数切换为归一化满量程）：
    agx_width = clamp(scale * width_m + offset, min_width, max_width)
    1:1:            scale=1.0, max_width=0.1（手持 70mm → 臂 70mm，直观）
    归一化满量程:    scale = 0.1 / 0.07039 ≈ 1.4207（手持全开 → 臂全开 100mm）

AGX 夹爪范围：width ∈ [0.0, 0.1] m，force ∈ [0.5, 3.0] N。
Usage:
    ros2 run gripper_teleop gripper_agx_bridge
"""

import rclpy
from rclpy.node import Node
from std_msgs.msg import Float32
from sensor_msgs.msg import JointState


class GripperAgxBridge(Node):
    def __init__(self):
        super().__init__("gripper_agx_bridge")

        # 主题
        self.declare_parameter("gripper_topic", "/gripper/width_m")
        self.declare_parameter("control_topic", "/control/joint_states")

        # 宽度线性映射 width' = scale * width + offset，再 clamp 到 [min, max]
        self.declare_parameter("width_scale", 1.0)          # 1:1；归一化满量程改为 ~1.4207
        self.declare_parameter("width_offset", 0.0)
        self.declare_parameter("min_width", 0.0)
        self.declare_parameter("max_width", 0.1)            # AGX gripper 最大开度
        self.declare_parameter("force", 1.0)                # 固定夹持力 (N)，[0.5, 3.0]
        self.declare_parameter("deadband", 0.0005)          # 0.5mm 死区，抑制抖动

        self._width_scale = float(self.get_parameter("width_scale").value)
        self._width_offset = float(self.get_parameter("width_offset").value)
        self._min_width = float(self.get_parameter("min_width").value)
        self._max_width = float(self.get_parameter("max_width").value)
        self._force = float(self.get_parameter("force").value)
        self._deadband = float(self.get_parameter("deadband").value)

        # 夹持力夹到 AGX 合法范围
        self._force = max(0.5, min(3.0, self._force))

        self._last_width = None

        self._control_pub = self.create_publisher(
            JointState, self.get_parameter("control_topic").value, 10)
        self._sub = self.create_subscription(
            Float32,
            self.get_parameter("gripper_topic").value,
            self._on_width,
            10,
        )

        self.get_logger().info(
            f"bridge: {self.get_parameter('gripper_topic').value} -> "
            f"{self.get_parameter('control_topic').value} | "
            f"scale={self._width_scale}, offset={self._width_offset}, "
            f"clamp=[{self._min_width},{self._max_width}], force={self._force} N, "
            f"deadband={self._deadband} m")

    def _on_width(self, msg: Float32):
        width_m = float(msg.data)
        agx_width = self._width_scale * width_m + self._width_offset
        agx_width = max(self._min_width, min(self._max_width, agx_width))

        # 死区抑制抖动；首条消息无条件下发，让夹爪进入已知状态
        if (self._last_width is not None and
                abs(agx_width - self._last_width) < self._deadband):
            return
        self._last_width = agx_width

        js = JointState()
        js.header.stamp = self.get_clock().now().to_msg()
        js.name = ["gripper"]
        js.position = [agx_width]
        js.velocity = []
        js.effort = [self._force]
        self._control_pub.publish(js)


def main():
    rclpy.init()
    node = GripperAgxBridge()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
