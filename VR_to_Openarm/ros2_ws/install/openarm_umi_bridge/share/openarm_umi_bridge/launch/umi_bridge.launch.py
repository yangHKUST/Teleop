# Copyright 2026 Enactic, Inc.
# SPDX-License-Identifier: Apache-2.0
"""One-shot launch of the OpenArm bringup + UMI ZMQ bridge (ROS2 side).

Starts, in order:
  1. openarm_bringup  (v1.0 URDF, forward-position controllers, real hardware)
  2. openarm_umi_bridge  (ZMQ <-> right_forward_position_controller)

The UMI teleop *core* (openarm_vio_teleop.py) is a separate non-ROS process; it
connects to the bridge over ZMQ (cmd tcp://127.0.0.1:5556, fb tcp://127.0.0.1:5557).
This launch only brings up the ROS2 side. Start the core afterwards (see
run_openarm.sh in the UMI repo).

Usage (real hardware):
    ros2 launch openarm_umi_bridge umi_bridge.launch.py

Simulation (fake hardware, no motors):
    ros2 launch openarm_umi_bridge umi_bridge.launch.py use_fake_hardware:=true \
        gravity_scale:=0.0

Single-arm: only the right arm is commanded by the bridge; both arms are still
brought up (gravity-compensated) by the bimanual bringup.
"""

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import (
    DeclareLaunchArgument,
    IncludeLaunchDescription,
    OpaqueFunction,
    TimerAction,
)
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.logging import get_logger
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node

_logger = get_logger("umi_bridge.launch")

# Same stale-process poisoning as teleop.launch.py: a leftover robot_state_publisher
# latches a (possibly fake) URDF on /robot_description, and a leftover
# controller_manager/bridge collides on node names. Kill them before starting.
_STALE_PATTERNS = {
    "robot_state_publisher": r"robot_state_publishe[r]",
    "ros2_control_node": r"ros2_control_nod[e]",
    "controller_manager spawner": r"controller_manager/spawne[r]",
    # 前缀 `/`：节点进程由安装路径启动（.../openarm_umi_bridge/umi_bridge），
    # 而本 launch 进程命令行是 `ros2 launch openarm_umi_bridge umi_bridge.launch.py`
    # （"umi_bridge" 前是空格/下划线，无 `/`）。若用裸 `umi_bridg[e]` 会把 launch
    # 自身匹配杀掉（自毁）。`/umi_bridg[e]` 只命中残留节点，不命中 launch。
    "umi_bridge": r"/umi_bridg[e]",
}


def _preflight_cleanup(context, preflight_cleanup):
    import subprocess
    import time

    if context.perform_substitution(preflight_cleanup).lower() != "true":
        return []

    killed = []
    for label, pattern in _STALE_PATTERNS.items():
        try:
            if subprocess.run(["pkill", "-f", pattern], check=False).returncode == 0:
                killed.append(label)
        except OSError:
            pass

    if killed:
        _logger.info("preflight: killed stale node(s): " + ", ".join(killed))
        time.sleep(1.5)
    else:
        _logger.info("preflight: no stale openarm nodes found")
    return []


def generate_launch_description():
    bringup = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            PathJoinSubstitution([
                get_package_share_directory("openarm_bringup"),
                "launch",
                "openarm.bimanual.launch.py",
            ])
        ),
        launch_arguments={
            "arm_type": LaunchConfiguration("arm_type"),
            "robot_controller": LaunchConfiguration("robot_controller"),
            "use_fake_hardware": LaunchConfiguration("use_fake_hardware"),
            "gravity_scale": LaunchConfiguration("gravity_scale"),
            "return_to_zero": LaunchConfiguration("return_to_zero"),
            "teaching_mode": LaunchConfiguration("teaching_mode"),
            "left_can_interface": LaunchConfiguration("left_can_interface"),
            "right_can_interface": LaunchConfiguration("right_can_interface"),
        }.items(),
    )

    bridge = Node(
        package="openarm_umi_bridge",
        executable="umi_bridge",
        name="openarm_umi_bridge",
        output="screen",
        parameters=[{
            "enable_on_start": LaunchConfiguration("enable_on_start"),
            "max_joint_speed_deg_s": LaunchConfiguration("max_joint_speed_deg_s"),
            "cmd_endpoint": LaunchConfiguration("cmd_endpoint"),
            "fb_endpoint": LaunchConfiguration("fb_endpoint"),
        }],
    )

    # 左臂桥：可选第二实例（--enable_left:=true），下发到 left_forward_position_controller，
    # ZMQ 端点独立（5566/5567）以免与右臂桥（5556/5557）冲突。
    left_bridge = Node(
        package="openarm_umi_bridge",
        executable="umi_bridge",
        name="openarm_umi_bridge_left",
        output="screen",
        parameters=[{
            "enable_on_start": LaunchConfiguration("enable_on_start"),
            "max_joint_speed_deg_s": LaunchConfiguration("max_joint_speed_deg_s"),
            "cmd_endpoint": LaunchConfiguration("left_cmd_endpoint"),
            "fb_endpoint": LaunchConfiguration("left_fb_endpoint"),
            "arm_controller_topic": "/left_forward_position_controller/commands",
            "gripper_controller_topic": "/left_gripper_controller/joint_trajectory",
            "arm_joints": [f"openarm_left_joint{i}" for i in range(1, 8)],
            "gripper_joint": "openarm_left_finger_joint1",
        }],
    )

    # Give the bringup a moment to spawn the controllers and start streaming
    # /joint_states before the bridge binds ZMQ and starts serving. The bridge is
    # robust to start order, but this avoids a burst of "waiting for /joint_states".
    bridge_delayed = TimerAction(period=LaunchConfiguration("bridge_delay"),
                                 actions=[bridge])
    left_bridge_delayed = TimerAction(
        period=LaunchConfiguration("bridge_delay"),
        actions=[left_bridge],
        condition=IfCondition(LaunchConfiguration("enable_left")),
    )

    cleanup = OpaqueFunction(
        function=_preflight_cleanup,
        args=[LaunchConfiguration("preflight_cleanup")],
    )

    return LaunchDescription([
        DeclareLaunchArgument("arm_type", default_value="openarm_v1.0"),
        DeclareLaunchArgument(
            "robot_controller", default_value="forward_position_controller"),
        DeclareLaunchArgument("use_fake_hardware", default_value="false"),
        DeclareLaunchArgument("gravity_scale", default_value="1.0"),
        DeclareLaunchArgument("return_to_zero", default_value="false"),
        DeclareLaunchArgument("teaching_mode", default_value="false"),
        DeclareLaunchArgument("left_can_interface", default_value="can1"),
        DeclareLaunchArgument("right_can_interface", default_value="can0"),
        DeclareLaunchArgument("enable_on_start", default_value="true"),
        DeclareLaunchArgument("max_joint_speed_deg_s", default_value="30.0"),
        DeclareLaunchArgument("cmd_endpoint", default_value="tcp://127.0.0.1:5556"),
        DeclareLaunchArgument("fb_endpoint", default_value="tcp://127.0.0.1:5557"),
        DeclareLaunchArgument("enable_left", default_value="false",
                              description="额外启动左臂桥（第二 umi_bridge 实例）"),
        DeclareLaunchArgument("left_cmd_endpoint", default_value="tcp://127.0.0.1:5566"),
        DeclareLaunchArgument("left_fb_endpoint", default_value="tcp://127.0.0.1:5567"),
        DeclareLaunchArgument("bridge_delay", default_value="3.0"),
        DeclareLaunchArgument(
            "preflight_cleanup", default_value="true",
            description="Kill leftover openarm nodes before starting."),
        cleanup,
        bringup,
        bridge_delayed,
        left_bridge_delayed,
    ])
