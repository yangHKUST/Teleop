#!/usr/bin/env bash
# VIO → OpenArm 增量式遥操（非 ROS 核心）：ORB_SLAM3 位姿(ZMQ) 驱动真机（RViz 可视化）。
#
# 激活专用 conda env 并清空 PYTHONPATH，避免 /opt/ros/humble 下损坏的 pinocchio
# 盖住 conda-forge 的 pinocchio。真机下发需先启动 ROS2 侧（run_openarm_bridge.sh）。
set -euo pipefail

source ~/miniconda3/etc/profile.d/conda.sh
conda activate piper_pinocchio
unset PYTHONPATH

cd "$(dirname "$0")/../.."   # repo root (arm/mujoco_sim -> ../..)
exec python3 arm/mujoco_sim/openarm_vio_teleop.py "$@"
