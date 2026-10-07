#!/usr/bin/env bash
# ROS2 侧：OpenArm 双臂 bringup + openarm_umi_bridge（ZMQ 桥）。
#
# 必须在 ROS2 Humble 系统 python 下运行（rclpy 在 /opt/ros/humble，与 conda 的
# pinocchio 冲突）。默认真机（use_fake_hardware:=false, gravity_scale:=1.0），
# 可用 ros2 launch 参数覆盖：run_openarm_bridge.sh use_fake_hardware:=true
# 注意：不用 `set -u`——/opt/ros/humble/setup.bash 等 ROS 启动脚本会引用未定义变量
# （如 $AMENT_TRACE_SETUP_FILES），在 nounset 下 source 会报"未绑定的变量"。
set -eo pipefail

# 若 conda 处于激活态则退出，避免其 python 抢在系统 python 之前导致 rclpy 找不到。
if [ -n "${CONDA_PREFIX:-}" ]; then
  source ~/miniconda3/etc/profile.d/conda.sh
  conda deactivate
fi

source /opt/ros/humble/setup.bash
source "$HOME/ros2_ws/install/setup.bash"

exec ros2 launch openarm_umi_bridge umi_bridge.launch.py "$@"
