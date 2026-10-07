#!/usr/bin/env bash
# 双 UMI → 双臂遥操：一个脚本开两个终端窗口，各自跑现有单臂 piper_vio_teleop.py。
#
# 与 run_all.sh（单臂）并存，单臂控制不受影响。
# 共享键：空格同时离合双臂、h 同时回准备姿态、esc 同时急停
#        （两个进程各自的 KeyboardReader 全局钩子会同时响应同一按键）。
#
# 每组默认映射（可用环境变量覆盖）：
#   ARM1_SN/ARM1_CAN/ARM1_GRIP/ARM1_POSE/ARM1_IMG   (s200032 / can0 / /dev/ttyACM0 / 5555 / 5556)
#   ARM2_SN/ARM2_CAN/ARM2_GRIP/ARM2_POSE/ARM2_IMG   (s200002 / can1 / /dev/ttyACM1 / 5557 / 5558)
set -euo pipefail

REPO="/home/taoqiu/CyperstereoSDK"
UMI="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONDA_SH="$HOME/miniconda3/etc/profile.d/conda.sh"

ARM1_SN="${ARM1_SN:-s200032}";   ARM1_CAN="${ARM1_CAN:-can0}";          ARM1_GRIP="${ARM1_GRIP:-/dev/ttyACM0}"
ARM2_SN="${ARM2_SN:-s200002}";   ARM2_CAN="${ARM2_CAN:-can1}";          ARM2_GRIP="${ARM2_GRIP:-/dev/ttyACM1}"
ARM1_POSE="${ARM1_POSE:-tcp://127.0.0.1:5555}"; ARM1_IMG="${ARM1_IMG:-tcp://127.0.0.1:5556}"
ARM2_POSE="${ARM2_POSE:-tcp://127.0.0.1:5557}"; ARM2_IMG="${ARM2_IMG:-tcp://127.0.0.1:5558}"
ARM1_MOTOR_ID="${ARM1_MOTOR_ID:-7}"; ARM2_MOTOR_ID="${ARM2_MOTOR_ID:-1}"   # 两套夹爪电机 slave_id 不同（实测 7 / 1）
ARM1_CALIB="${ARM1_CALIB:-}"                                              # 第一套用默认共享标定（gripper_calibration.json）
ARM2_CALIB="${ARM2_CALIB:-$UMI/gripper/config/gripper_calibration_arm2.json}"  # 第二套零点不同，用独立标定

# 双臂同退共享停止标记：任一终端 Ctrl+C → 写入该文件 → 另一臂主循环检测到后回准备姿态并退出。
STOP_FILE="/tmp/dual_teleop_stop"

# ---- 0. 拉起 CAN----
bring_up() {
  local ifc="$1"
  if ip link show "$ifc" 2>/dev/null | grep -q "state UP"; then
    echo "[dual] $ifc 已 UP"
    return 0
  fi
  echo "[dual] $ifc 未 UP，尝试拉起（可能需要 sudo 密码）..."
  if sudo ip link set "$ifc" up type can bitrate 1000000; then
    sudo ip link set "$ifc" txqueuelen 1000
    echo "[dual] $ifc 已拉起"
  else
    echo "[dual] 错误：无法自动拉起 $ifc，请手动执行后重跑："
    echo "         sudo ip link set $ifc up type can bitrate 1000000"
    exit 1
  fi
}
bring_up "$ARM1_CAN"
bring_up "$ARM2_CAN"

# ---- 1. 清理旧进程 ----
pkill -f cyperstereo_online 2>/dev/null || true
pkill -f piper_vio_teleop 2>/dev/null || true
pkill -f dual_stereo_viewer 2>/dev/null || true
rm -f "$STOP_FILE"   # 清掉上次运行残留的停止标记，避免一启动就被误判为「另一臂已退出」
sleep 1

# ---- 2. 生成两组运行脚本（heredoc 展开变量，规避 gnome-terminal 引号嵌套）----
# 关键：相机序列号 + ZMQ 端口用 export 注入遥操进程环境；
#       subprocess.Popen(shell=True) 启动的 VIO 会继承，--vio-cmd 里无需塞环境变量。
mk_runner() {
  local tag="$1" sn="$2" can="$3" grip="$4" pose="$5" img="$6" mid="$7" log="$8" calib="$9"
  local f="/tmp/run_dual_${tag}.sh"
  cat > "$f" <<EOF
#!/usr/bin/env bash
source "$CONDA_SH"
conda activate piper_pinocchio
unset PYTHONPATH
export CYPERSTEREO_SERIAL="$sn"
export VIO_POSE_ZMQ_ENDPOINT="$pose"
export VIO_IMG_ZMQ_ENDPOINT="$img"
export VIO_HEADLESS=1   # 不弹 ORB-SLAM3 地图窗/跟踪窗 + 本进程的双目窗口；显示交给合并查看器
cd "$UMI"
python3 arm/mujoco_sim/piper_vio_teleop.py --staged --can "$can" --gripper-channel "$grip" --gripper-motor-id "$mid" --gripper-calib "$calib" --endpoint "$pose" --vio-log "$log" --stop-file "$STOP_FILE" --vio-cmd "cd $REPO/ORB_SLAM3-Cyperstereo/build && ./cyperstereo_online ../Vocabulary/ORBvoc.txt $REPO/slam/config/orbslam3/cyperstereo_sn_${sn}.yaml"
rc=\$?
echo
echo "=== [dual] 遥操已退出（退出码 \$rc），2 秒后自动关闭本窗口 ==="
sleep 2
EOF
  chmod +x "$f"
  echo "$f"
}

F1="$(mk_runner arm1 "$ARM1_SN" "$ARM1_CAN" "$ARM1_GRIP" "$ARM1_POSE" "$ARM1_IMG" "$ARM1_MOTOR_ID" /tmp/cyperstereo_vio_arm1.log "$ARM1_CALIB")"
F2="$(mk_runner arm2 "$ARM2_SN" "$ARM2_CAN" "$ARM2_GRIP" "$ARM2_POSE" "$ARM2_IMG" "$ARM2_MOTOR_ID" /tmp/cyperstereo_vio_arm2.log "$ARM2_CALIB")"

echo "[dual] arm1: $ARM1_SN → $ARM1_CAN / $ARM1_GRIP (pose $ARM1_POSE)"
echo "[dual] arm2: $ARM2_SN → $ARM2_CAN / $ARM2_GRIP (pose $ARM2_POSE)"
echo "[dual] 运行脚本：$F1 / $F2"
echo "[dual] 打开两个终端窗口 + 一个合并双目查看窗口（两臂原始画面上下拼接）..."
# 合并双目查看器：后台跑，两臂图像流都停止后自动关闭；不占额外终端窗口。
( source "$CONDA_SH" && conda activate piper_pinocchio && unset PYTHONPATH && \
  exec python3 "$UMI/arm/mujoco_sim/dual_stereo_viewer.py" --ep1 "$ARM1_IMG" --ep2 "$ARM2_IMG" ) &
gnome-terminal --title "UMI 双臂 · arm1 ($ARM1_SN)" -- bash "$F1" &
gnome-terminal --title "UMI 双臂 · arm2 ($ARM2_SN)" -- bash "$F2" &
wait
