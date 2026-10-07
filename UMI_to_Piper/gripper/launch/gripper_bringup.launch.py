"""gripper_teleop 完整串联：手持夹爪检测 -> AGX 夹爪桥接。

注意：AGX 机械臂本体需另行启动（不同 colcon 工作区 agx_arm_ros），并指定
effector_type:=agx_gripper：
    ros2 launch agx_arm_ctrl start_single_agx_arm.launch.py \
        arm_type:=piper effector_type:=agx_gripper
"""

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    channel_arg = DeclareLaunchArgument("channel", default_value="/dev/ttyACM0")
    scale_arg = DeclareLaunchArgument("width_scale", default_value="1.0")
    force_arg = DeclareLaunchArgument("force", default_value="1.0")

    pkg_share = FindPackageShare("gripper_teleop")

    publisher = IncludeLaunchDescription(
        PythonLaunchDescriptionSource([
            PathJoinSubstitution([pkg_share, "launch", "gripper_publisher.launch.py"]),
        ]),
        launch_arguments={
            "channel": LaunchConfiguration("channel"),
        }.items(),
    )

    bridge = IncludeLaunchDescription(
        PythonLaunchDescriptionSource([
            PathJoinSubstitution([pkg_share, "launch", "gripper_agx_bridge.launch.py"]),
        ]),
        launch_arguments={
            "width_scale": LaunchConfiguration("width_scale"),
            "force": LaunchConfiguration("force"),
        }.items(),
    )

    return LaunchDescription([channel_arg, scale_arg, force_arg, publisher, bridge])
