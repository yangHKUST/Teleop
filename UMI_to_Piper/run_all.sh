#!/usr/bin/env bash
# 一键启动：ORB-SLAM3(VIO) + MuJoCo 仿真 + 真机(可选) + 夹爪(可选)
#
# 分阶段流程（与手动三终端等价，但只需一个终端）：
#   [1] 机械臂回准备姿态（仅真机模式）
#   [2] 启动 VIO 系统 → 提示你移动相机完成 VIO 初始化 → 回车
#   [3] Z/X 标定（沿 base +Z 上 / +X 前 推手持夹爪）
#   [4] 回车开启遥操（空格=离合  h=回准备姿态  s=记录准备姿态  esc=急停）
#
# 用法（三个模式，只改一个参数）：
#   ./run_all.sh                 # 全量：ORB-SLAM3 + 仿真 + 真机 + 夹爪(CAN 直驱)
#   ./run_all.sh --sim-only      # 只仿真：真机不动，仿真臂+仿真夹爪(跟随手持)正常遥操
#   ./run_all.sh --synthetic --no-viewer --steps 300   # 离线冒烟（无相机/无夹爪/无真机）
#
# 额外参数会透传给 piper_vio_teleop.py（如 --scale 0.6 --pitch-gain 2.5 --no-calibrate）
#
# 环境变量覆盖：
#   VIO_SN=s200002  CAN_IF=can0  GRIPPER_CHANNEL=/dev/ttyACM0  SIM_ONLY=1
#
# 停止：Ctrl-C（遥操自身回收 VIO；本脚本回收夹爪链）
set -euo pipefail

REPO="/home/taoqiu/CyperstereoSDK"
UMI="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"   # 本脚本所在目录 = 副本根目录
ROS_DISTRO="${ROS_DISTRO:-humble}"
GRIPPER_CHANNEL="${GRIPPER_CHANNEL:-/dev/ttyACM0}"
CAN_IF="${CAN_IF:-can0}"
VIO_SN="${VIO_SN:-s200032}"

# ---- 模式解析：--sim-only / --synthetic / 其余透传给遥操 ----
SIM_ONLY="${SIM_ONLY:-0}"          # 环境变量 SIM_ONLY=1 等价于 --sim-only
SYNTHETIC=0
TELEOP_USER_ARGS=()
for _a in "$@"; do
  case "$_a" in
    --sim-only)  SIM_ONLY=1 ;;
    --synthetic) SYNTHETIC=1; TELEOP_USER_ARGS+=("$_a") ;;
    *)           TELEOP_USER_ARGS+=("$_a") ;;
  esac
done

MODE="全量(真机+夹爪)"
[[ "$SIM_ONLY" == "1" ]] && MODE="只仿真(真机不动)"
[[ "$SYNTHETIC" == "1" ]] && MODE="离线冒烟"

# ---- 0. 清理残留进程（夹爪/遥操/VIO），保证一键即全新状态 ----
echo "[run_all] 清理残留进程（夹爪链 / 遥操 / VIO）..."
pkill -f "gripper_publisher"  2>/dev/null || true
pkill -f "gripper_agx_bridge" 2>/dev/null || true
pkill -f "piper_vio_teleop"   2>/dev/null || true
pkill -f "cyperstereo_online" 2>/dev/null || true
sleep 1

# ---- 1. 夹爪 ROS2 链（可选：USE_ROS2_GRIPPER=1 才启用。默认关闭，夹爪由遥操 --can 直驱。
#         ROS2 链需要 agx_arm_ctrl 订阅 /control/joint_states，而 agx_arm_ctrl 也占 can0，
#         会与遥操 --can can0 冲突，故默认不走这条）----
GRIPPER_PID=""
if [[ "${USE_ROS2_GRIPPER:-0}" == "1" ]]; then
  echo "[run_all] ① 启动夹爪链（ROS2 gripper_bringup, channel=$GRIPPER_CHANNEL）..."
  (
    set +u   # ROS2 setup.bash 引用未绑定的 AMENT_TRACE_SETUP_FILES，与脚本顶部 set -u 冲突
    source "/opt/ros/$ROS_DISTRO/setup.bash"
    source "$REPO/ros2/install/setup.bash"
    exec ros2 launch gripper_teleop gripper_bringup.launch.py channel:="$GRIPPER_CHANNEL"
  ) > /tmp/gripper_bringup.log 2>&1 &
  GRIPPER_PID=$!
  echo "[run_all]    夹爪链 PID=$GRIPPER_PID，日志 /tmp/gripper_bringup.log"
fi

cleanup() {
  echo
  echo "[run_all] 停止夹爪链..."
  if [[ -n "$GRIPPER_PID" ]]; then kill "$GRIPPER_PID" 2>/dev/null || true; fi
  pkill -f "gripper_publisher"  2>/dev/null || true
  pkill -f "gripper_agx_bridge" 2>/dev/null || true
}
trap cleanup EXIT

# ---- 2. 机械臂遥操（conda piper_pinocchio，前台，分阶段）----
source ~/miniconda3/etc/profile.d/conda.sh
conda activate piper_pinocchio
unset PYTHONPATH

# VIO 启动命令（ORB-SLAM3 须从 build/ 目录跑以解析 ../Vocabulary 相对路径）
VIO_CMD="cd $REPO/ORB_SLAM3-Cyperstereo/build && ./cyperstereo_online ../Vocabulary/ORBvoc.txt $REPO/slam/config/orbslam3/cyperstereo_sn_${VIO_SN}.yaml"

TELEOP_ARGS=()
if [[ "$SYNTHETIC" == "1" ]]; then
  :   # 离线冒烟：只透传 --synthetic/--no-viewer/--steps 等
elif [[ "$SIM_ONLY" == "1" ]]; then
  # 无 --can（真机不动）；无 --no-gripper（遥操直读手持 → 仿真夹爪跟随）
  TELEOP_ARGS+=(--staged --vio-cmd "$VIO_CMD")
else
  # 全量：真机 + 夹爪都由遥操经 CAN 直驱（piper_sdk）。遥操自读手持 /dev/ttyACM0，
  # 经 arm.send_gripper() 下发臂夹爪，无需 ROS2 夹爪链。
  TELEOP_ARGS+=(--staged --can "$CAN_IF" --vio-cmd "$VIO_CMD")
fi

cd "$UMI"
echo "[run_all] ② 启动遥操（模式：$MODE）"
echo "          [1] 回准备姿态 → [2] VIO 初始化 → [3] Z/X 标定 → 回车开启遥操"
echo
python3 arm/mujoco_sim/piper_vio_teleop.py "${TELEOP_ARGS[@]}" "${TELEOP_USER_ARGS[@]}"
