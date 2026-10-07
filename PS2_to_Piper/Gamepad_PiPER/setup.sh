#!/usr/bin/env bash
# Install an isolated environment without replacing JetPack's system Python.
set -Eeuo pipefail
trap 'echo "安装未完成（第 $LINENO 行）。修复上方错误后重新运行 bash setup.sh。" >&2' ERR
PROJECT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR"
if [ "${EUID}" -eq 0 ]; then
    echo "请使用普通用户运行 bash setup.sh，不要 sudo bash setup.sh。" >&2
    exit 1
fi
case "$(uname -m)" in
    aarch64) PLATFORM=linux-aarch64 ;;
    x86_64) PLATFORM=linux-64 ;;
    *) echo "不支持的 CPU 架构" >&2; exit 1 ;;
esac
. /etc/os-release
if [ "$ID" != ubuntu ] || [ "${VERSION_ID%%.*}" -lt 22 ]; then
    echo "该安装入口针对 Ubuntu 22.04 或更高版本。" >&2
    exit 1
fi
sudo apt-get update
sudo apt-get install -y curl ca-certificates bzip2 tar iproute2 can-utils \
    build-essential pkg-config libsdl2-dev libsdl2-image-dev libsdl2-mixer-dev \
    libsdl2-ttf-dev libportmidi-dev libgl1 libglfw3
mkdir -p .runtime/tools
export MAMBA_ROOT_PREFIX="$PROJECT_DIR/.runtime/mamba"
MAMBA="$PROJECT_DIR/.runtime/tools/bin/micromamba"
if [ ! -x "$MAMBA" ]; then
    curl --fail --location --retry 3 "https://micro.mamba.pm/api/micromamba/$PLATFORM/latest" \
        -o .runtime/micromamba.tar.bz2
    tar -xjf .runtime/micromamba.tar.bz2 -C .runtime/tools bin/micromamba
fi
ENV_DIR="$PROJECT_DIR/.runtime/env"
unset PYTHONPATH LD_LIBRARY_PATH
export PYTHONNOUSERSITE=1
if [ ! -x "$ENV_DIR/bin/python" ]; then
    "$MAMBA" create -y -p "$ENV_DIR" --override-channels -c conda-forge \
        'python=3.11' 'pinocchio=3.6.0' 'casadi=3.7.2' 'numpy<3' scipy pip
else
    echo "检测到已有 Python 环境，检查并补齐依赖。"
    "$MAMBA" install -y -p "$ENV_DIR" --override-channels -c conda-forge \
        'python=3.11' 'pinocchio=3.6.0' 'casadi=3.7.2' 'numpy<3' scipy pip
fi
"$ENV_DIR/bin/python" -m pip install -r deployment/requirements-jetson.txt
mkdir -p ros_packages/piper_description
if [ ! -e ros_packages/piper_description/meshes ] && [ ! -L ros_packages/piper_description/meshes ]; then
    ln -s ../../piper/meshes ros_packages/piper_description/meshes
fi
if [ ! -f ros_packages/piper_description/meshes/link1.STL ]; then
    echo "模型链接无效，请检查 ros_packages/piper_description/meshes。" >&2
    exit 1
fi
export ROS_PACKAGE_PATH="$PROJECT_DIR/ros_packages"
"$ENV_DIR/bin/python" deployment/check_environment.py
"$ENV_DIR/bin/python" -m pip freeze > .runtime/installed-requirements.txt
printf '\n部署完成。先运行 bash start.sh virtual，再运行 bash start.sh real。\n'
printf '此安装过程没有连接或使能机械臂。环境保存在 .runtime/，不要跨电脑复制。\n'
