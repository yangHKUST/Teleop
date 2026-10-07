#!/usr/bin/env bash
# VIO → Piper 增量式遥操（非 ROS）：ORB_SLAM3 位姿(ZMQ) 驱动真机 + MuJoCo 数字孪生。
#
# 激活专用 conda env 并清空 PYTHONPATH，避免 ROS-humble 下损坏的 pinocchio
# （/opt/ros/humble）盖住 conda-forge 的 pinocchio。
set -euo pipefail

source ~/miniconda3/etc/profile.d/conda.sh
conda activate piper_pinocchio
unset PYTHONPATH

cd "$(dirname "$0")/../.."   # repo root (arm/mujoco_sim -> ../..)
exec python3 arm/mujoco_sim/piper_vio_teleop.py "$@"
