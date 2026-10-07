#!/usr/bin/env bash
# Piper + Quest3 teleop launcher.
# 用干净的 conda 环境运行，隔离掉 ~/.local 和 ROS 的 PYTHONPATH 污染。
set -euo pipefail

# --- 环境隔离（关键） ---
unset PYTHONPATH                              # 去掉 ROS humble 的 site-packages
export PYTHONNOUSERSITE=1                     # 去掉 ~/.local/lib/python3.10 的污染
export PIP_DISABLE_PIP_VERSION_CHECK=1
export PYTHONUNBUFFERED=1                     # 子进程日志立即显示，避免"看起来卡住/没反应"

# --- 激活环境 ---
source "$HOME/miniconda3/etc/profile.d/conda.sh"
conda activate piper-teleop

# --- 环境自检：防止用错解释器（base 环境没有 mujoco，报错很误导） ---
if ! python -c "import mujoco, mink, vuer, piper_sdk" 2>/dev/null; then
    echo "[ERROR] 依赖缺失，当前 python = $(which python)"
    echo "        请确认已创建 piper-teleop conda 环境并安装了依赖。"
    echo "        不要用裸 python 跑，必须通过本脚本 ./run_teleop.sh 启动。"
    exit 1
fi

# --- 运行 ---
# 默认: 真机 (左臂 can0, 右臂 can1)
# 单臂: --can can0 (只启动一条臂，右手柄控制)
# 仿真:  加 --dry-run 参数
# 自定义: --can-left canX --can-right canY
cd "$(dirname "$0")"
exec python -m teleop.teleop_real_arm "$@"
