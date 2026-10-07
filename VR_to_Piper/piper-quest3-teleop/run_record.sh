#!/usr/bin/env bash
# 数据录制器启动脚本（独立于 run_teleop.sh）。
#
# 用法：先按正常方式运行遥操作（./run_teleop.sh --dry-run 或 --can can0），
#      再另开一个终端执行本脚本，即可把遥操作数据落盘为 CSV：
#
#       ./run_record.sh --out ~/records/session1
#
# 环境隔离与 run_teleop.sh 保持一致（piper-teleop 环境，屏蔽 ~/.local 与 ROS）。
set -euo pipefail

unset PYTHONPATH
export PYTHONNOUSERSITE=1
export PYTHONUNBUFFERED=1

source "$HOME/miniconda3/etc/profile.d/conda.sh"
conda activate piper-teleop

cd "$(dirname "$0")"
exec python -m teleop.record_data "$@"
