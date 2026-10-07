# Shared presentation only. Startup commands/order are unchanged.
init_output_mode() {
  OUTPUT_MODE=teaching
  OUTPUT_SIDE="$1"
  shift
  local previous="" argument
  for argument in "$@"; do
    case "$argument" in
      --output-mode=*) OUTPUT_MODE="${argument#--output-mode=}" ;;
      *)
        [ "$previous" != --output-mode ] || OUTPUT_MODE="$argument"
        if [ "$OUTPUT_SIDE" != dual ]; then
          [ "$previous" != --arm ] || OUTPUT_SIDE="$argument"
          case "$argument" in --arm=*) OUTPUT_SIDE="${argument#--arm=}" ;; esac
        fi
        ;;
    esac
    previous="$argument"
  done
  case "$OUTPUT_MODE" in teaching|developer) ;; *) builtin echo "无效 --output-mode：$OUTPUT_MODE" >&2; exit 2 ;; esac
}
echo() {
  local message="$*" side="$OUTPUT_SIDE"
  if [ "$OUTPUT_MODE" = developer ]; then
    builtin echo "$(date +%H:%M:%S) INFO  [$side][launcher] $message"
  else
    case "$side" in left) side=左臂 ;; right) side=右臂 ;; dual) side=双臂 ;; esac
    case "$message" in
      *ERROR*) builtin echo "[错误][$side] $message" ;;
      *清理残留*) builtin echo "[连接][$side] 正在清理残留连接。" ;;
      *启动\ ROS2*) builtin echo "[1/5][$side] 正在连接机械臂。" ;;
      *等待*ZMQ*) builtin echo "[等待][$side] 等待控制通道连接。" ;;
      *端点*就绪*) builtin echo "[完成][$side] 控制通道已连接。" ;;
      *启动遥操核心*|*启动\ UMI*) builtin echo "[启动][$side] 正在启动手持遥操作。" ;;
      *左相机=*) ;; # Serial numbers belong to developer output.
      *) builtin echo "[提示][$side] $message" ;;
    esac
  fi
}
