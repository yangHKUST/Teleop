#!/usr/bin/env bash
set -euo pipefail
PROJECT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR"
PYTHON="$PROJECT_DIR/.runtime/env/bin/python"
if [ ! -x "$PYTHON" ]; then
    echo "尚未部署，请先运行 bash setup.sh。" >&2
    exit 1
fi
unset PYTHONPATH LD_LIBRARY_PATH ROS_DISTRO AMENT_PREFIX_PATH CMAKE_PREFIX_PATH COLCON_PREFIX_PATH
export ROS_PACKAGE_PATH="$PROJECT_DIR/ros_packages"
export PYTHONNOUSERSITE=1
export OPENBLAS_NUM_THREADS="${OPENBLAS_NUM_THREADS:-1}"
export OMP_NUM_THREADS="${OMP_NUM_THREADS:-1}"
exec "$PYTHON" launch.py "$@"
