#!/usr/bin/env bash
# 双臂 OpenArm 遥操：两臂并行准备，两路 VIO 并行启动，一次回车分别标定。
# 流程：控制连接 → 两臂同时准备 → 两路 VIO 同时启动
# → 两侧新鲜位姿就绪 → 统一回车标定 → 两侧标定成功 → 回车开启遥操。
# 编排脚本独占启动确认输入；运行键由左臂广播给右臂。
#
# 用法：
#   run_openarm_dual.sh --bridge                 # 真机双臂（并行准备、统一确认标定）
#   run_openarm_dual.sh --bridge --no-calibrate  # 跳过 R_BW 标定（标定旗标仍会写，不阻塞）
#   run_openarm_dual.sh --synthetic --steps 300  # 离线冒烟（不起 ROS2/相机，仅计算）
#
# 相机序列号 / yaml 路径用环境变量覆盖：
#   LEFT_VIO_SN=s200085  RIGHT_VIO_SN=s200086
#   LEFT_YAML=...        RIGHT_YAML=...
# 不要在参数里再传 --arm / --vio-cmd / --dual-state / --stop-file（本脚本自行管理）。
# 其它控制参数（--scale/--flip-*/--no-calibrate/--steps 等）会透传给两个遥操核心。
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
source "$HERE/output_shell.sh"
init_output_mode dual "$@"
export OPENARM_DUAL_RUN=1
REPO_ROOT="$(cd "$HERE/../.." && pwd)"
LOG_DIR="$HOME/.openarm_umi_logs"
mkdir -p "$LOG_DIR"

# ---- 相机 / VIO 命令（可覆盖）----
LEFT_SN="${LEFT_VIO_SN:-s200085}"
RIGHT_SN="${RIGHT_VIO_SN:-s200086}"
LEFT_YAML="${LEFT_YAML:-$REPO_ROOT/camera_driver/cyperstereo/calib/orbslam3_yaml/cyperstereo_sn_${LEFT_SN}.yaml}"
RIGHT_YAML="${RIGHT_YAML:-/home/taoqiu/CyperstereoSDK/slam/config/orbslam3/cyperstereo_sn_${RIGHT_SN}.yaml}"
CYPER_BUILD="/home/taoqiu/CyperstereoSDK/ORB_SLAM3-Cyperstereo/build"

LEFT_VIO_CMD="cd $CYPER_BUILD && ./cyperstereo_online ../Vocabulary/ORBvoc.txt $LEFT_YAML"
RIGHT_VIO_CMD="cd $CYPER_BUILD && ./cyperstereo_online ../Vocabulary/ORBvoc.txt $RIGHT_YAML"

# ---- 模式：--synthetic 离线冒烟；否则真机分阶段 ----
SYNTHETIC=0
for a in "$@"; do
  [ "$a" = "--synthetic" ] && SYNTHETIC=1
done

STATE_DIR="$(mktemp -d /tmp/openarm_dual_state.XXXXXX)"
STOP_FILE="$(mktemp /tmp/openarm_dual_stop.XXXXXX)"
rm -f "$STOP_FILE"

ROS_PID=""; LEFT_PID=""; RIGHT_PID=""

cleanup() {
  for p in "$LEFT_PID" "$RIGHT_PID"; do
    [ -n "$p" ] && kill -INT "$p" 2>/dev/null || true
  done
  sleep 2
  if [ -n "$ROS_PID" ]; then
    kill -INT -- -"$ROS_PID" 2>/dev/null || kill -INT "$ROS_PID" 2>/dev/null || true
    sleep 2
    kill -KILL -- -"$ROS_PID" 2>/dev/null || true
  fi
  rm -f "$STOP_FILE"
  rm -rf "$STATE_DIR"
}
trap cleanup EXIT
# SIGINT/SIGTERM 只挂空 handler，让前台 wait/read 先收到信号，再由 EXIT trap 统一收尾。
trap ':' INT TERM

# ---- 离线冒烟：两个核心 --synthetic，不起 ROS2/相机，不标定 ----
if [ "$SYNTHETIC" = "1" ]; then
  echo "[dual] 离线冒烟：左右臂 --synthetic（无 ROS2/相机/标定），共享停止标记 $STOP_FILE"
  bash "$HERE/run_openarm_vio_teleop.sh" --arm left --synthetic "$@" --stop-file "$STOP_FILE" &
  LEFT_PID=$!
  sleep 0.5
  bash "$HERE/run_openarm_vio_teleop.sh" --arm right --synthetic "$@" --stop-file "$STOP_FILE" &
  RIGHT_PID=$!
  wait "$LEFT_PID" "$RIGHT_PID" || true
  echo "[dual] 双臂离线冒烟已退出"
  exit 0
fi

# ---- 1. ROS2 侧（bringup + 左右两路 umi_bridge，enable_left:=true）----
echo "[dual] 启动 ROS2 侧（bringup + 左右两路 umi_bridge，enable_left:=true）..."
setsid bash "$HERE/run_openarm_bridge.sh" enable_left:=true ${ROS2_EXTRA_ARGS:-} \
  > "$LOG_DIR/ros2_dual.log" 2>&1 &
ROS_PID=$!

for ep in 5556 5566; do
  echo "[dual] 等待 ZMQ 命令端点 tcp://127.0.0.1:$ep ..."
  ready=0
  for _ in $(seq 1 90); do
    if /usr/bin/python3 -c "import socket; s=socket.socket(); s.settimeout(0.5); s.connect(('127.0.0.1',$ep)); s.close()" 2>/dev/null; then
      ready=1; break
    fi
    if ! kill -0 "$ROS_PID" 2>/dev/null; then
      echo "[dual] ERROR: ROS2 侧提前退出，查看 $LOG_DIR/ros2_dual.log"
      tail -40 "$LOG_DIR/ros2_dual.log" >&2 || true
      exit 1
    fi
    sleep 1
  done
  [ "$ready" = "1" ] || { echo "[dual] ERROR: 90s 内端点 $ep 未就绪，查看 $LOG_DIR/ros2_dual.log"; exit 1; }
  echo "[dual] 端点 $ep 已就绪"
done

# ---- 2. 启动两个遥操核心（共同就绪后并行准备，各自相机 + VIO 端点）----
echo "[dual] 启动遥操核心：左臂(--arm left) + 右臂(--arm right)，协调目录 $STATE_DIR"
echo "[dual] 左相机=$LEFT_SN (pose 5565)   右相机=$RIGHT_SN (pose 5555)"
env CYPERSTEREO_SERIAL="$LEFT_SN" \
    VIO_POSE_ZMQ_ENDPOINT=tcp://127.0.0.1:5565 \
    VIO_IMG_ZMQ_ENDPOINT=tcp://127.0.0.1:5568 \
  bash "$HERE/run_openarm_vio_teleop.sh" --arm left --bridge --staged \
    --dual-state "$STATE_DIR" --stop-file "$STOP_FILE" \
    --vio-cmd "$LEFT_VIO_CMD" "$@" --vio-log "$LOG_DIR/vio_left.log" &
LEFT_PID=$!
env CYPERSTEREO_SERIAL="$RIGHT_SN" \
    VIO_POSE_ZMQ_ENDPOINT=tcp://127.0.0.1:5555 \
    VIO_IMG_ZMQ_ENDPOINT=tcp://127.0.0.1:5558 \
  bash "$HERE/run_openarm_vio_teleop.sh" --arm right --bridge --staged \
    --dual-state "$STATE_DIR" --stop-file "$STOP_FILE" \
    --vio-cmd "$RIGHT_VIO_CMD" "$@" --vio-log "$LOG_DIR/vio_right.log" &
RIGHT_PID=$!

# ---- 3. 两路 VIO 就绪后，一次回车释放两个独立标定计算 ----
echo "[dual] 等待两路 VIO 新鲜位姿就绪 ..."
while [ ! -f "$STATE_DIR/vio.left" ] || [ ! -f "$STATE_DIR/vio.right" ]; do
  if ! kill -0 "$LEFT_PID" 2>/dev/null || ! kill -0 "$RIGHT_PID" 2>/dev/null; then
    echo "[dual] ERROR: 遥操核心提前退出，两路 VIO 未全部就绪，查看上方日志及 VIO 日志"
    exit 1
  fi
  sleep 0.2
done
if [[ " $* " != *" --no-calibrate "* ]]; then
  echo "[标定][双臂] 请摆好左右手持夹爪：按原标定要求，手指水平指向工作区，相机保持俯视夹爪。"
  read -r -p "[标定][双臂] 保持两侧夹爪静止，按 Enter 同时确认左右方向标定 ..." _ || {
    echo "[dual] 已取消标定，回收中 ..."; exit 1
  }
else
  echo "[dual] 已按参数跳过两侧方向标定。"
fi
touch "$STATE_DIR/calibrate_go"

# ---- 两条臂分别完成独立标定后，才允许开始遥操 ----
echo "[dual] 等待左臂 + 右臂 Z/X 标定完成 ..."
while [ ! -f "$STATE_DIR/calib.left" ] || [ ! -f "$STATE_DIR/calib.right" ]; do
  if [ ! -f "$STATE_DIR/calib.left" ] && ! kill -0 "$LEFT_PID" 2>/dev/null; then
    echo "[dual] ERROR: 左臂核心已退出但未完成标定，查看 $LOG_DIR/vio_left.log / 上方日志"
    exit 1
  fi
  if [ ! -f "$STATE_DIR/calib.right" ] && ! kill -0 "$RIGHT_PID" 2>/dev/null; then
    echo "[dual] ERROR: 右臂核心已退出但未完成标定，查看 $LOG_DIR/vio_right.log / 上方日志"
    exit 1
  fi
  sleep 0.5
done
echo "[dual] 两条臂 Z/X 标定完成。"

# ---- 4. 回车统一开遥操 ----
read -r -p "[操作][双臂] 按 Enter 开始（Space 暂停/恢复；H 返回；S 保存；R 恢复默认；Esc 软件急停）..." _ || {
  echo; echo "[dual] 已取消，回收中 ..."; exit 1
}
touch "$STATE_DIR/go"
echo "[dual] go 已下发，双臂同步开遥操。"

wait "$LEFT_PID" "$RIGHT_PID" || true
echo "[dual] 双臂遥操已退出"
