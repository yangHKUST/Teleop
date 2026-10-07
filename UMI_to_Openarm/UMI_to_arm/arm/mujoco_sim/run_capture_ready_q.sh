#!/usr/bin/env bash
# 记录 Piper 真机手拖位姿为启动准备姿态（非 ROS）。
#
# 同 run_vio_teleop.sh：激活 piper_pinocchio env 并清空 PYTHONPATH，
# 避免 ROS-humble 下损坏的 pinocchio 盖住 conda-forge 的 pinocchio。
set -euo pipefail

source ~/miniconda3/etc/profile.d/conda.sh
conda activate piper_pinocchio
unset PYTHONPATH

cd "$(dirname "$0")/../.."   # repo root (arm/mujoco_sim -> ../..)
exec python3 arm/mujoco_sim/capture_ready_q.py "$@"
