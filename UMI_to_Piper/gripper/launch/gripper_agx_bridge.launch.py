from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    scale_arg = DeclareLaunchArgument(
        "width_scale", default_value="1.0",
        description="1:1 -> 1.0；归一化满量程 -> ~1.4207 (0.1/0.07039).")
    offset_arg = DeclareLaunchArgument("width_offset", default_value="0.0")
    min_w_arg = DeclareLaunchArgument("min_width", default_value="0.0")
    max_w_arg = DeclareLaunchArgument("max_width", default_value="0.1")
    force_arg = DeclareLaunchArgument("force", default_value="1.0")
    deadband_arg = DeclareLaunchArgument("deadband", default_value="0.0005")
    gripper_topic_arg = DeclareLaunchArgument(
        "gripper_topic", default_value="/gripper/width_m")
    control_topic_arg = DeclareLaunchArgument(
        "control_topic", default_value="/control/joint_states")

    node = Node(
        package="gripper_teleop",
        executable="gripper_agx_bridge",
        name="gripper_agx_bridge",
        output="screen",
        parameters=[{
            "width_scale": LaunchConfiguration("width_scale"),
            "width_offset": LaunchConfiguration("width_offset"),
            "min_width": LaunchConfiguration("min_width"),
            "max_width": LaunchConfiguration("max_width"),
            "force": LaunchConfiguration("force"),
            "deadband": LaunchConfiguration("deadband"),
            "gripper_topic": LaunchConfiguration("gripper_topic"),
            "control_topic": LaunchConfiguration("control_topic"),
        }],
    )

    return LaunchDescription([
        scale_arg, offset_arg, min_w_arg, max_w_arg, force_arg, deadband_arg,
        gripper_topic_arg, control_topic_arg, node,
    ])
