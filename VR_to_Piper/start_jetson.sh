#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
ROOT="$PWD"
unset PYTHONPATH LD_LIBRARY_PATH PYTHONHOME
export PYTHONNOUSERSITE=1 PYTHONUNBUFFERED=1
PYTHON="$ROOT/.runtime/env/bin/python"
[[ -x "$PYTHON" ]] || { echo '先运行 bash setup_jetson.sh'; exit 1; }
if [[ ${1:-} == --check ]]; then
    exec "$PYTHON" deployment/check_jetson.py
fi
if [[ $# == 0 ]]; then
    echo '无硬件演练：bash start_jetson.sh --dry-run --can can1'
    echo '单臂真机：bash start_jetson.sh --can can1'
    echo '不带参数不会启动真机。'
    exit 0
fi
# 实际 CAN 启停由用户完成；这里不自动 down 总线，不影响其他项目。
cd "$ROOT/piper-quest3-teleop"
exec "$PYTHON" -m teleop.teleop_real_arm "$@"
