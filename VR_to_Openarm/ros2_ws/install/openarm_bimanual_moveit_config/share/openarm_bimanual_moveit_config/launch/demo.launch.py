# Copyright 2025 Enactic, Inc.
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
from moveit_configs_utils import MoveItConfigsBuilder

# Shared helpers live in openarm_description (a package both bringup and the
# MoveIt demo already depend on), which avoids a dependency cycle between them.
sys.path.insert(
    0, os.path.join(get_package_share_directory("openarm_description"), "launch"))
import openarm_common  # noqa: E402


def nodes_spawner(
    context,
    description_package,
    arm_type,
    use_fake_hardware,
    controllers_file,
    right_can_interface,
    left_can_interface,
    arm_prefix,
    return_to_zero,
):
    """Generate robot_description once and spawn ros2_control + MoveIt nodes."""
    namespace = openarm_common.namespace_from_context(context, arm_prefix)

    # Generate exactly once and reuse the same URDF string for the
    # ros2_control nodes and for MoveIt, so they can never disagree about the
    # hardware (CAN interfaces, gripper type, etc.).
    robot_description = openarm_common.generate_robot_description(
        context, description_package, arm_type, use_fake_hardware,
        right_can_interface, left_can_interface, return_to_zero,
    )

    controllers_file_str = context.perform_substitution(controllers_file)
    if namespace:
        controllers_file_str = controllers_file_str.replace(
            "openarm_bimanual_controllers.yaml",
            "openarm_bimanual_controllers_namespaced.yaml",
        )

    nodes = [
        openarm_common.robot_state_publisher_node(robot_description, namespace),
        openarm_common.controller_manager_node(controllers_file_str, namespace),
    ]

    arm_type_str = context.perform_substitution(arm_type)
    config_dir = openarm_common.config_dir_for(arm_type_str)
    moveit_pkg_path = get_package_share_directory(
        "openarm_bimanual_moveit_config")

    builder = (
        MoveItConfigsBuilder("openarm", package_name="openarm_bimanual_moveit_config")
        .robot_description_semantic(
            file_path=f"config/{config_dir}/openarm_bimanual.srdf")
        .robot_description_kinematics(
            file_path=f"config/{config_dir}/kinematics.yaml")
        .joint_limits(file_path=f"config/{config_dir}/joint_limits.yaml")
        .trajectory_execution(
            file_path=f"config/{config_dir}/moveit_controllers.yaml")
        .planning_pipelines(
            pipelines=["ompl"], default_planning_pipeline="ompl")
    )
    # Inject the already-generated description instead of letting the builder
    # process the xacro a second time (and with a different set of mappings).
    # This reaches into the builder's private MoveItConfigs; replace with a
    # public setter if MoveItConfigsBuilder ever grows one.
    builder._MoveItConfigsBuilder__moveit_configs.robot_description = {
        "robot_description": robot_description,
    }
    moveit_config = builder.to_moveit_configs()
    moveit_params = moveit_config.to_dict()

    pilz_cartesian_limits_path = os.path.join(
        moveit_pkg_path, "config", config_dir, "pilz_cartesian_limits.yaml")
    if os.path.exists(pilz_cartesian_limits_path):
        import yaml
        with open(pilz_cartesian_limits_path, "r") as f:
            config_data = yaml.safe_load(f)
            if "cartesian_limits" in config_data:
                if "robot_description_planning" not in moveit_params:
                    moveit_params["robot_description_planning"] = {}
                moveit_params["robot_description_planning"].update(config_data)

    rviz_cfg = os.path.join(moveit_pkg_path, "config", config_dir, "moveit.rviz")

    nodes += [
        Node(
            package="moveit_ros_move_group",
            executable="move_group",
            output="screen",
            parameters=[moveit_params],
        ),
        Node(
            package="rviz2",
            executable="rviz2",
            name="rviz2",
            output="log",
            arguments=["-d", rviz_cfg],
            parameters=[moveit_params],
        ),
    ]
    return nodes


def generate_launch_description():
    declared_arguments = [
        DeclareLaunchArgument(
            "description_package", default_value="openarm_description"),
        DeclareLaunchArgument(
            "arm_type",
            default_value="openarm_v2.0",
            description="Arm type. Accepts: v1.0, v10, openarm_v1.0, v2.0, v20, openarm_v2.0, etc."
        ),
        DeclareLaunchArgument("use_fake_hardware", default_value="true"),
        DeclareLaunchArgument(
            "robot_controller",
            default_value="joint_trajectory_controller",
            choices=["forward_position_controller",
                     "joint_trajectory_controller"],
        ),
        DeclareLaunchArgument(
            "runtime_config_package", default_value="openarm_bringup"),
        DeclareLaunchArgument("arm_prefix", default_value=""),
        DeclareLaunchArgument("right_can_interface", default_value="can0"),
        DeclareLaunchArgument("left_can_interface", default_value="can1"),
        DeclareLaunchArgument(
            "return_to_zero",
            default_value="false",
            description="Sweep to zero on activate (false = hold current position).",
        ),
        DeclareLaunchArgument(
            "controllers_file", default_value="openarm_bimanual_controllers.yaml"),
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
    arm_prefix = LaunchConfiguration("arm_prefix")

    controllers_file = PathJoinSubstitution(
        [FindPackageShare(runtime_config_package), "config",
         "controllers", controllers_file]
    )

    nodes_spawner_func = OpaqueFunction(
        function=nodes_spawner,
        args=[
            description_package,
            arm_type,
            use_fake_hardware,
            controllers_file,
            right_can_interface,
            left_can_interface,
            arm_prefix,
            return_to_zero,
        ],
    )

    jsb_spawner = OpaqueFunction(
        function=openarm_common.joint_state_broadcaster_spawner,
        args=[arm_prefix],
    )

    controller_spawner_func = OpaqueFunction(
        function=openarm_common.controller_spawner,
        args=[robot_controller, arm_prefix],
    )

    gripper_spawner = OpaqueFunction(
        function=openarm_common.gripper_controller_spawner,
        args=[arm_prefix],
    )

    return LaunchDescription(
        declared_arguments
        + [
            nodes_spawner_func,
            TimerAction(period=2.0, actions=[jsb_spawner]),
            TimerAction(period=1.0, actions=[controller_spawner_func]),
            TimerAction(period=1.0, actions=[gripper_spawner]),
        ]
    )
