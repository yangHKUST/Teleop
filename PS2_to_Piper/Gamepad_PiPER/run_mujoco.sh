#!/usr/bin/env bash
# Run the PiPER virtual-arm teleoperation with the MuJoCo native viewer.
#
# This wrapper isolates the project from the ROS Humble environment that is
# sourced in the user's shell profile: ROS's Python 3.10 site-packages (and
# its lib paths) would otherwise shadow the conda pinocchio / mujoco that this
# project needs.

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONDA_BASE="${CONDA_PREFIX:-$HOME/miniconda3}"
PYTHON="${CONDA_BASE}/envs/piper/bin/python"

if [ ! -x "$PYTHON" ]; then
    echo "ERROR: conda env 'piper' not found at: $PYTHON" >&2
    echo "Create it with:" >&2
    echo "  conda create -n piper python=3.11 -y" >&2
    echo "  conda install -n piper -c conda-forge pinocchio=3.6.0 casadi -y" >&2
    echo "  \$HOME/miniconda3/envs/piper/bin/python -m pip install scipy viser yourdfpy 'pygame<2.6.2' piper_sdk 'setuptools<80.9.0' mujoco" >&2
    exit 1
fi

cd "$SCRIPT_DIR"

# Drop ROS pollution from PYTHONPATH and LD_LIBRARY_PATH.
unset PYTHONPATH ROS_DISTRO AMENT_PREFIX_PATH CMAKE_PREFIX_PATH COLCON_PREFIX_PATH 2>/dev/null || true
if [ -n "$LD_LIBRARY_PATH" ]; then
    LD_LIBRARY_PATH="$(printf '%s' "$LD_LIBRARY_PATH" | tr ':' '\n' | grep -v '/opt/ros/' | paste -sd: -)"
fi
export LD_LIBRARY_PATH

# Point pinocchio's `package://` mesh resolver at the minimal package layout
# (ros_packages/piper_description/meshes -> piper/meshes).
export ROS_PACKAGE_PATH="${SCRIPT_DIR}/ros_packages"

exec "$PYTHON" main_mujoco.py "$@"
