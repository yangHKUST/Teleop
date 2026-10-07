# Copyright 2026 Enactic, Inc.
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

"""Shared launch helpers for the OpenArm bringup and MoveIt demo.

Centralises arm_type resolution, robot_description generation, and the
ros2_control node spawners so the two launch paths cannot drift apart.

robot_description is generated exactly once per launch and passed to
robot_state_publisher, which publishes it as a latched topic. The
controller_manager (ros2_control_node) reads it from that topic rather than
receiving it directly as a (deprecated) parameter.
"""

import os

import xacro
from ament_index_python.packages import get_package_share_directory
from launch import LaunchContext
from launch_ros.actions import Node

# All accepted arm_type values
VALID_ARM_TYPES = {
    "v1.0", "v10", "v1_0", "openarm_v1.0", "openarm_v10", "openarm_v1_0",
    "v2.0", "v20", "v2_0", "openarm_v2.0", "openarm_v20", "openarm_v2_0",
}


def resolve_arm_config(arm_type_str: str):
    """Resolve the (folder_name, xacro_file_name) for an arm_type string."""
    if arm_type_str not in VALID_ARM_TYPES:
        raise ValueError(
            f"Invalid arm_type: '{arm_type_str}'. "
            "Please specify openarm_v1.0 or openarm_v2.0."
        )
    if any(x in arm_type_str for x in ("1.0", "10", "1_0")):
        return "openarm_v1.0", "openarm_v10.urdf.xacro"
    return "openarm_v2.0", "openarm_v20.urdf.xacro"


def config_dir_for(arm_type_str: str) -> str:
    """Resolve the MoveIt config directory name for an arm_type string."""
    if any(x in arm_type_str for x in ("1.0", "10", "1_0")):
        return "openarm_v1.0"
    return "openarm_v2.0"


def namespace_from_context(context: LaunchContext, arm_prefix):
    """Resolve the topic namespace from the arm_prefix launch configuration."""
    arm_prefix_str = context.perform_substitution(arm_prefix)
    if arm_prefix_str:
        return arm_prefix_str.strip("/")
    return None


def _resolve_param(context: LaunchContext, substitution, default: str) -> str:
    """Perform a launch substitution, or return `default` when it is None.

    Newer parameters default to None so launch files that predate them keep
    working without passing the argument (they fall back to a safe default
    instead of hitting a required-positional-argument error).
    """
    if substitution is None:
        return default
    return context.perform_substitution(substitution)


def generate_robot_description(
    context: LaunchContext,
    description_package,
    arm_type,
    use_fake_hardware,
    right_can_interface,
    left_can_interface,
    return_to_zero,
    gravity_scale=None,
    teaching_mode=None,
):
    """Process the robot xacro once and return the URDF string."""
    description_package_str = context.perform_substitution(description_package)
    arm_type_str = context.perform_substitution(arm_type)
    use_fake_hardware_str = context.perform_substitution(use_fake_hardware)
    right_can_interface_str = context.perform_substitution(right_can_interface)
    left_can_interface_str = context.perform_substitution(left_can_interface)
    return_to_zero_str = context.perform_substitution(return_to_zero)
    gravity_scale_str = _resolve_param(context, gravity_scale, "0.0")
    teaching_mode_str = _resolve_param(context, teaching_mode, "false")

    folder_name, file_name = resolve_arm_config(arm_type_str)
    xacro_path = os.path.join(
        get_package_share_directory(description_package_str),
        "assets", "robot", folder_name, "urdf", file_name,
    )

    return xacro.process_file(
        xacro_path,
        mappings={
            "arm_type": arm_type_str,
            "bimanual": "true",
            "use_fake_hardware": use_fake_hardware_str,
            "ros2_control": "true",
            "right_can_interface": right_can_interface_str,
            "left_can_interface": left_can_interface_str,
            "return_to_zero": return_to_zero_str,
            "gravity_scale": gravity_scale_str,
            "teaching_mode": teaching_mode_str,
        },
    ).toprettyxml(indent="  ")


def robot_state_publisher_node(robot_description, namespace=None):
    """Node that publishes robot_description (parameter + latched topic)."""
    return Node(
        package="robot_state_publisher",
        executable="robot_state_publisher",
        name="robot_state_publisher",
        output="screen",
        namespace=namespace,
        parameters=[{"robot_description": robot_description}],
    )


def controller_manager_node(controllers_file_str, namespace=None):
    """ros2_control_node.

    robot_description is intentionally NOT passed as a parameter: passing it
    directly is deprecated. ros2_control_node subscribes to the
    ~/robot_description topic published by robot_state_publisher instead.

    ros2_control_node subscribes on its *private* topic ``~/robot_description``
    (i.e. ``/controller_manager/robot_description``), while robot_state_publisher
    publishes ``/robot_description``. Without the remap below the two never
    connect: the controller_manager never receives the URDF, so it never calls
    ``init_resource_manager`` (no hardware load, no motor enable) nor
    ``init_services`` (no ``list_controllers`` → spawners hang forever).
    """
    return Node(
        package="controller_manager",
        executable="ros2_control_node",
        output="both",
        namespace=namespace,
        parameters=[controllers_file_str],
        remappings=[("~/robot_description", "robot_description")],
    )


def robot_nodes_spawner(
    context: LaunchContext,
    description_package,
    arm_type,
    use_fake_hardware,
    controllers_file,
    right_can_interface,
    left_can_interface,
    arm_prefix,
    return_to_zero,
    gravity_scale=None,
    teaching_mode=None,
):
    """Spawn robot_state_publisher and ros2_control_node with a shared description."""
    namespace = namespace_from_context(context, arm_prefix)

    robot_description = generate_robot_description(
        context, description_package, arm_type, use_fake_hardware,
        right_can_interface, left_can_interface, return_to_zero, gravity_scale,
        teaching_mode,
    )

    controllers_file_str = context.perform_substitution(controllers_file)
    if namespace:
        controllers_file_str = controllers_file_str.replace(
            "openarm_bimanual_controllers.yaml",
            "openarm_bimanual_controllers_namespaced.yaml",
        )

    return [
        robot_state_publisher_node(robot_description, namespace),
        controller_manager_node(controllers_file_str, namespace),
    ]


def controller_spawner(context: LaunchContext, robot_controller, arm_prefix):
    """Spawn the active arm controller(s) based on robot_controller."""
    namespace = namespace_from_context(context, arm_prefix)
    controller_manager_ref = (
        f"/{namespace}/controller_manager" if namespace else "/controller_manager"
    )

    robot_controller_str = context.perform_substitution(robot_controller)

    if robot_controller_str == "forward_position_controller":
        controllers = ["left_forward_position_controller",
                       "right_forward_position_controller"]
    elif robot_controller_str == "joint_trajectory_controller":
        controllers = ["both_arms_joint_trajectory_controller"]
    else:
        raise ValueError(f"Unknown robot_controller: {robot_controller_str}")

    return [
        Node(
            package="controller_manager",
            executable="spawner",
            namespace=namespace,
            arguments=controllers + ["-c", controller_manager_ref],
        )
    ]


def joint_state_broadcaster_spawner(context: LaunchContext, arm_prefix):
    namespace = namespace_from_context(context, arm_prefix)
    controller_manager_ref = (
        f"/{namespace}/controller_manager" if namespace else "/controller_manager"
    )
    return [
        Node(
            package="controller_manager",
            executable="spawner",
            namespace=namespace,
            arguments=["joint_state_broadcaster", "-c", controller_manager_ref],
        )
    ]


def gripper_controller_spawner(context: LaunchContext, arm_prefix):
    namespace = namespace_from_context(context, arm_prefix)
    controller_manager_ref = (
        f"/{namespace}/controller_manager" if namespace else "/controller_manager"
    )
    return [
        Node(
            package="controller_manager",
            executable="spawner",
            namespace=namespace,
            arguments=["left_gripper_controller", "right_gripper_controller",
                       "-c", controller_manager_ref],
        )
    ]
