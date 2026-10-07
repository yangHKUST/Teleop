#!/usr/bin/env python3
"""
B9 Gripper Publisher — DM3507 夹爪数据发布到 ROS2（使用标定文件，无交互标定）。

从 config/gripper_calibration.json 读取 encoder_min/encoder_max 与物理宽度
width_min_m/width_max_m，按规范 §4.6 的线性映射把原始编码器计数 (16-bit q_uint)
换算成开合百分比与物理两指间距，并发布：
  - /gripper/state          Float32  开合百分比 0~100（Rerun 波形图）
  - /gripper/width_m        Float32  物理两指间距 (m)，供遥操桥接与数据集采集
  - /gripper/encoder_count  Float32  原始编码器计数，供数据集 encoder_count 字段

Usage:
    ros2 run gripper_teleop gripper_publisher
    ros2 run gripper_teleop gripper_publisher --ros-args -p channel:=/dev/ttyACM0 -p motor_id:=7 -p master_id:=17
"""

import json
from collections import deque
from pathlib import Path

import rclpy
from rclpy.node import Node
from std_msgs.msg import Float32

from gripper_teleop.dm_canable2 import DM_Motor_Type, Motor, MotorControl


# ==============================================================================
# Calibration file helpers
# ==============================================================================

def _find_calib_path():
    """Locate config/gripper_calibration.json (installed share dir, then source tree)."""
    try:
        from ament_index_python.packages import get_package_share_directory
        p = Path(get_package_share_directory("gripper_teleop")) / "config" / "gripper_calibration.json"
        if p.exists():
            return p
    except Exception:
        pass
    # 源码树直接运行时的回退路径
    p = Path(__file__).resolve().parents[1] / "config" / "gripper_calibration.json"
    if p.exists():
        return p
    raise FileNotFoundError("gripper_calibration.json not found")


def load_calibration(path):
    if not path.exists():
        return None
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def encoder_to_width_pct(raw_encoder, calib):
    """原始编码器计数 → (物理宽度 m, 开合百分比 %)。规范 §4.6 线性映射。"""
    c_min = float(calib["encoder_min"])
    c_max = float(calib["encoder_max"])
    w_min = float(calib["width_min_m"])
    w_max = float(calib["width_max_m"])
    if c_min == c_max:
        raise ValueError("gripper_calibration.json encoder_min == encoder_max")
    frac = (float(raw_encoder) - c_min) / (c_max - c_min)
    frac = max(0.0, min(1.0, frac))
    return w_min + frac * (w_max - w_min), frac * 100.0


# ==============================================================================
# ROS2 Gripper Publisher Node
# ==============================================================================

class GripperPublisher(Node):
    def __init__(self):
        super().__init__("gripper_publisher")

        # Parameters (overridable via --ros-args -p channel:=...)
        # 注意：实物电机 id=7（见 config/gripper_calibration.json 的 note），
        # 参考程序默认 0x01 是错的；串口 ACM 编号随 USB 枚举顺序变化，当前是 ACM0。
        self.declare_parameter("channel", "/dev/ttyACM0")
        self.declare_parameter("motor_id", 0x07)
        self.declare_parameter("master_id", 0x11)
        channel = self.get_parameter("channel").value
        motor_id = int(self.get_parameter("motor_id").value)
        master_id = int(self.get_parameter("master_id").value)

        # Publishers
        self._pct_pub = self.create_publisher(Float32, "/gripper/state", 10)
        self._width_pub = self.create_publisher(Float32, "/gripper/width_m", 10)
        self._encoder_pub = self.create_publisher(Float32, "/gripper/encoder_count", 10)

        # CAN motor setup
        self._motor = Motor(DM_Motor_Type.DM3507, motor_id, master_id)
        self._control = MotorControl(
            channel=channel, can_bitrate=1000000, tty_baudrate=115200)
        self._control.addMotor(self._motor)

        # 标定只从文件读取，不做交互标定
        self._calib = self._load_calibration()
        self.get_logger().info(
            f"Gripper calib: encoder {self._calib['encoder_min']}~{self._calib['encoder_max']}, "
            f"width {self._calib['width_min_m']:.5f}~{self._calib['width_max_m']:.5f} m")

        # Periodic timer: read position + publish at 20 Hz
        self._timer = self.create_timer(0.05, self._publish_state)

        # Filter: moving average to reject vibration noise (raw encoder domain)
        self._raw_history = deque(maxlen=10)
        self._last_published_pct = None

    def _load_calibration(self):
        calib_path = _find_calib_path()
        calib = load_calibration(calib_path)
        for key in ("encoder_min", "encoder_max", "width_min_m", "width_max_m"):
            if key not in calib:
                raise ValueError(f"gripper_calibration.json missing key: {key}")
        return calib

    def _publish_state(self):
        """Read raw encoder, filter noise, publish percentage / width / raw encoder."""
        try:
            self._control.refresh_motor_status(self._motor)
            raw = self._motor.getRawEncoder()
            self._raw_history.append(raw)
            # Moving average to suppress vibration noise (raw 编码器域)
            avg_raw = sum(self._raw_history) / len(self._raw_history)
            width_m, pct = encoder_to_width_pct(avg_raw, self._calib)

            # 原始编码器 + 物理宽度：全速发布（供遥操桥接与数据集采集）
            self._encoder_pub.publish(Float32(data=float(raw)))
            self._width_pub.publish(Float32(data=float(width_m)))

            # 百分比：死区抑制漂移，仅变化 >0.3% 时发布（供 Rerun 波形图）
            if (self._last_published_pct is None or
                    abs(pct - self._last_published_pct) > 0.3):
                self._last_published_pct = pct
                self._pct_pub.publish(Float32(data=float(pct)))

        except Exception as e:
            self.get_logger().error(f"Motor read error: {e}", throttle_duration_sec=2.0)

    def destroy_node(self):
        self._control.close()
        super().destroy_node()


# ==============================================================================
# Entry point
# ==============================================================================

def main():
    rclpy.init()
    node = GripperPublisher()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
