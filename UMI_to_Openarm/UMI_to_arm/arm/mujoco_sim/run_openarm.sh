#!/usr/bin/env bash
# VIO → OpenArm 遥操 一键启动：ROS2 侧（bringup + umi_bridge）+ UMI 遥操核心。
#
# 两进程分置（rclpy 与 conda pinocchio 冲突）：
#   * 后台启动 ROS2 侧（openarm_umi_bridge），日志 ~/.openarm_umi_logs/ros2.log；
#   * 前台运行 UMI 遥操核心（conda piper_pinocchio env），参数透传给它。
#
# 用法：
#   run_openarm.sh --bridge                 # 真机（默认走 run_openarm_bridge.sh 真机参数）
#   run_openarm.sh --bridge --no-calibrate  # 跳过 R_BW 标定
#   run_openarm.sh --bridge --arm left --staged --vio-cmd "..."  # 左臂真机（自动 enable_left + 左 VIO 端点）
#   run_openarm.sh --synthetic --steps 300   # 离线冒烟（不起 ROS2，仅计算）
#
# 若只想跑仿真/离线（不碰 ROS2），直接调 run_openarm_vio_teleop.sh 即可。
# ROS2 侧参数用 ROS2_EXTRA_ARGS 覆盖，如 ROS2_EXTRA_ARGS="use_fake_hardware:=true"。
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
source "$HERE/output_shell.sh"
init_output_mode right "$@"
REPO_ROOT="$(cd "$HERE/../.." && pwd)"
LOG_DIR="$HOME/.openarm_umi_logs"
mkdir -p "$LOG_DIR"
ROS2_LOG="$LOG_DIR/ros2.log"

# 需要 ROS2 侧吗：真机遥操（--bridge）才需要；纯仿真/离线不需要。
# 顺带解析 --arm left/right（支持 "--arm left" 与 "--arm=left" 两种写法）。
NEED_ROS2=0
ARM="right"
prev=""
for a in "$@"; do
  case "$a" in
    --bridge)    NEED_ROS2=1 ;;
    --arm=*)     ARM="${a#--arm=}" ;;
    --arm)       ;;
    *)           [ "$prev" = "--arm" ] && ARM="$a" ;;
  esac
  prev="$a"
done

ROS_PID=""
if [ "$NEED_ROS2" = "1" ]; then
  # 左臂：额外启动左臂桥（enable_left:=true），并等待左桥 cmd 端点 5566（右臂等 5556）。
  BRIDGE_WAIT_PORT="5556"
  ROS2_ARGS="${ROS2_EXTRA_ARGS:-}"
  if [ "$ARM" = "left" ]; then
    ROS2_ARGS="enable_left:=true ${ROS2_ARGS}"
    BRIDGE_WAIT_PORT="5566"
  fi
  # 先清残留：上一次未退净的 bridge / ros2_control_node 仍占着 ZMQ 端口，会让下面的
  # TCP 握手误判（连到死进程 → 遥操核心 wait_for_joints 收不到反馈超时）。主动 kill 并
  # 等端口真正关闭，再启动新侧。模式与 umi_bridge.launch.py 的 _STALE_PATTERNS 一致。
  echo "[run_openarm] 清理残留 ROS2 进程并等待 ZMQ 端口 ${BRIDGE_WAIT_PORT} 释放 ..."
  pkill -f "/umi_bridg[e]" 2>/dev/null || true
  pkill -f "ros2_control_nod[e]" 2>/dev/null || true
  pkill -f "robot_state_publishe[r]" 2>/dev/null || true
  pkill -f "controller_manager/spawne[r]" 2>/dev/null || true
  for _ in $(seq 1 20); do
    if ! /usr/bin/python3 -c "import socket; s=socket.socket(); s.settimeout(0.3); s.connect(('127.0.0.1',${BRIDGE_WAIT_PORT})); s.close()" 2>/dev/null; then
      break  # 端口已关闭，可以安全启动
    fi
    sleep 0.5
  done

  echo "[run_openarm] 启动 ROS2 侧（bringup + openarm_umi_bridge，arm=${ARM}）... 日志: $ROS2_LOG"
  # 独立进程组，便于退出时连带杀掉 ros2 launch 派生的所有节点。
  setsid bash "$HERE/run_openarm_bridge.sh" ${ROS2_ARGS} > "$ROS2_LOG" 2>&1 &
  ROS_PID=$!

  echo "[run_openarm] 等待 ROS2 侧 ZMQ 命令端点就绪 (tcp://127.0.0.1:${BRIDGE_WAIT_PORT}) ..."
  ready=0
  for _ in $(seq 1 90); do
    if /usr/bin/python3 -c "import socket; s=socket.socket(); s.settimeout(0.5); s.connect(('127.0.0.1',${BRIDGE_WAIT_PORT})); s.close()" 2>/dev/null; then
      ready=1; break
    fi
    if ! kill -0 "$ROS_PID" 2>/dev/null; then
      echo "[run_openarm] ERROR: ROS2 侧提前退出，查看 $ROS2_LOG"; tail -40 "$ROS2_LOG" >&2 || true; exit 1
    fi
    sleep 1
  done
  [ "$ready" = "1" ] || { echo "[run_openarm] ERROR: 90s 内 ZMQ 端点未就绪，查看 $ROS2_LOG"; exit 1; }
  echo "[run_openarm] ZMQ 命令端点已就绪"
fi

cleanup() {
  if [ -n "$ROS_PID" ]; then
    echo "[run_openarm] 停止 ROS2 侧 ..."
    kill -INT -- -"$ROS_PID" 2>/dev/null || kill -INT "$ROS_PID" 2>/dev/null || true
    sleep 2
    kill -KILL -- -"$ROS_PID" 2>/dev/null || true
  fi
}
trap cleanup EXIT
# SIGINT/SIGTERM 只挂一个空 handler，让本脚本在 Ctrl-C 时不立即死亡（否则 EXIT trap
# 不触发、ROS2 侧泄漏）；前台遥操子进程会先收到信号优雅退出，随后脚本走到 EXIT 再清理。
trap ':' INT TERM

# 左臂：遥操核心默认 --endpoint 5565，需让 --staged 拉起的 cyperstereo_online 也发到
# 5565（VIO 默认 5555）；img 端点挪到 5568 避开右桥 cmd 5556 / 左桥 5566、5567。
# CYPERSTEREO_SERIAL 用 LEFT_VIO_SN 覆盖（默认 s200085；两台相机都插着时必须正确）。
if [ "$ARM" = "left" ]; then
  export CYPERSTEREO_SERIAL="${LEFT_VIO_SN:-s200085}"
  export VIO_POSE_ZMQ_ENDPOINT="${LEFT_VIO_POSE_ENDPOINT:-tcp://127.0.0.1:5565}"
  export VIO_IMG_ZMQ_ENDPOINT="${LEFT_VIO_IMG_ENDPOINT:-tcp://127.0.0.1:5568}"
fi

echo "[run_openarm] 启动 UMI 遥操核心（conda piper_pinocchio env）..."
# 不用 exec：exec 会清掉 EXIT trap，导致遥操退出后 ROS2 侧（bringup+bridge）一直残留、
# 端口 5556/5557 不释放。改在前台运行子进程，退出后走 EXIT trap 收尾。
bash "$HERE/run_openarm_vio_teleop.sh" "$@"
