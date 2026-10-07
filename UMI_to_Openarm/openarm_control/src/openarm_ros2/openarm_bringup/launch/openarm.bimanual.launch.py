# Copyright 2025 Enactic, Inc.
# Copyright 2024 Stogl Robotics Consulting UG (haftungsbeschränkt)
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os
import sys

from ament_index_python.packages import get_package_share_directory

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, TimerAction, OpaqueFunction
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare

# Shared helpers live in openarm_description (a package both bringup and the
# MoveIt demo already depend on), which avoids a dependency cycle between them.
sys.path.insert(
    0, os.path.join(get_package_share_directory("openarm_description"), "launch"))
import openarm_common  # noqa: E402


def generate_launch_description():
    """Generate launch description for OpenArm bimanual configuration."""

    declared_arguments = [
        DeclareLaunchArgument(
            "description_package",
            default_value="openarm_description",
            description="Description package with robot URDF/xacro files.",
        ),
        DeclareLaunchArgument(
            "arm_type",
            default_value="openarm_v2.0",
            description="Arm type. Accepts: v1.0, v10, openarm_v1.0, v2.0, v20, openarm_v2.0, etc.",
        ),
        DeclareLaunchArgument(
            "use_fake_hardware",
            default_value="true",
            description="Use fake hardware instead of real hardware.",
        ),
        DeclareLaunchArgument(
            "robot_controller",
            default_value="joint_trajectory_controller",
            choices=["forward_position_controller",
                     "joint_trajectory_controller"],
            description="Robot controller to start.",
        ),
        DeclareLaunchArgument(
            "runtime_config_package",
            default_value="openarm_bringup",
            description="Package with the controller's configuration in config folder.",
        ),
        DeclareLaunchArgument(
            "arm_prefix",
            default_value="",
            description="Prefix for the arm for topic namespacing.",
        ),
        DeclareLaunchArgument(
            "right_can_interface",
            default_value="can0",
            description="CAN interface to use for the right arm.",
        ),
        DeclareLaunchArgument(
            "left_can_interface",
            default_value="can1",
            description="CAN interface to use for the left arm.",
        ),
        DeclareLaunchArgument(
            "return_to_zero",
            default_value="false",
            description="Sweep to zero on activate (false = hold current position).",
        ),
        DeclareLaunchArgument(
            "gravity_scale",
            default_value="0.0",
            description="Gravity-compensation feedforward scale (0.0 = off, 1.0 = full).",
        ),
        DeclareLaunchArgument(
            "teaching_mode",
            default_value="false",
            description="Zero-gravity teaching mode (kp=0 + full gravity comp; drag to move).",
        ),
        DeclareLaunchArgument(
            "controllers_file",
            default_value="openarm_bimanual_controllers.yaml",
            description="Controllers file to use.",
        ),
    ]

    description_package = LaunchConfiguration("description_package")
    arm_type = LaunchConfiguration("arm_type")
    use_fake_hardware = LaunchConfiguration("use_fake_hardware")
    robot_controller = LaunchConfiguration("robot_controller")
    runtime_config_package = LaunchConfiguration("runtime_config_package")
    controllers_file = LaunchConfiguration("controllers_file")
    right_can_interface = LaunchConfiguration("right_can_interface")
    left_can_interface = LaunchConfiguration("left_can_interface")
    return_to_zero = LaunchConfiguration("return_to_zero")
    gravity_scale = LaunchConfiguration("gravity_scale")
    teaching_mode = LaunchConfiguration("teaching_mode")
    arm_prefix = LaunchConfiguration("arm_prefix")

    controllers_file = PathJoinSubstitution(
        [FindPackageShare(runtime_config_package), "config",
         "controllers", controllers_file]
    )

    robot_nodes_spawner_func = OpaqueFunction(
        function=openarm_common.robot_nodes_spawner,
        args=[description_package, arm_type, use_fake_hardware, controllers_file,
              right_can_interface, left_can_interface, arm_prefix,
              return_to_zero, gravity_scale, teaching_mode]
    )

    rviz_config_file = PathJoinSubstitution(
        [FindPackageShare(description_package), "rviz", "bimanual.rviz"]
    )

    rviz_node = Node(
        package="rviz2",
        executable="rviz2",
        name="rviz2",
        output="log",
        arguments=["-d", rviz_config_file],
    )

    joint_state_broadcaster_spawner = OpaqueFunction(
        function=openarm_common.joint_state_broadcaster_spawner,
        args=[arm_prefix],
    )

    controller_spawner_func = OpaqueFunction(
        function=openarm_common.controller_spawner,
        args=[robot_controller, arm_prefix],
    )

    gripper_controller_spawner = OpaqueFunction(
        function=openarm_common.gripper_controller_spawner,
        args=[arm_prefix],
    )

    LAUNCH_DELAY_SECONDS = 1.0

    return LaunchDescription(
        declared_arguments + [
            robot_nodes_spawner_func,
            rviz_node,
            TimerAction(period=LAUNCH_DELAY_SECONDS, actions=[
                        joint_state_broadcaster_spawner]),
            TimerAction(period=LAUNCH_DELAY_SECONDS,
                        actions=[controller_spawner_func]),
            TimerAction(period=LAUNCH_DELAY_SECONDS, actions=[
                        gripper_controller_spawner]),
        ]
    )
