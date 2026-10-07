#!/usr/bin/env bash
# Add the missing USB-CAN driver without replacing the running Jetson kernel.
set -Eeuo pipefail
trap 'echo "USB-CAN 驱动安装未完成（第 $LINENO 行）。请保留上方完整报错。" >&2' ERR
REPAIR_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
KERNEL_RELEASE="$(uname -r)"
if [ "$EUID" -eq 0 ]; then
    echo "请以普通用户运行 bash install_gs_usb.sh，不要 sudo bash。" >&2
    exit 1
fi
if [ "$(uname -m)" != aarch64 ] || [ "$KERNEL_RELEASE" != 5.15.148-tegra ]; then
    echo "此修复包仅用于 ARM64 Jetson 的 5.15.148-tegra 内核。" >&2
    exit 1
fi
HEADERS="/lib/modules/$KERNEL_RELEASE/build"
if [ ! -f "$HEADERS/Makefile" ] || [ ! -s "$HEADERS/Module.symvers" ]; then
    echo "匹配的内核头文件或 Module.symvers 缺失，停止编译。" >&2
    exit 1
fi
sudo apt-get update
sudo apt-get install -y build-essential bc flex bison libssl-dev kmod can-utils iproute2 ethtool
HEADER_RELEASE="$(make -s -C "$HEADERS" kernelrelease)"
if [ "$HEADER_RELEASE" != "$KERNEL_RELEASE" ]; then
    echo "头文件版本 $HEADER_RELEASE 与运行内核 $KERNEL_RELEASE 不一致，停止。" >&2
    exit 1
fi
if ! modinfo gs_usb >/dev/null 2>&1; then
    WORK_DIR="$REPAIR_DIR/.runtime/gs-usb-build-$KERNEL_RELEASE"
    mkdir -p "$WORK_DIR"
    EXPECTED_SOURCE_SHA="d1ee028fd35e29f1c120577f62d1c3d670731b3b5104f4107278d061a7e5ac06"
    ACTUAL_SOURCE_SHA="$(sha256sum "$REPAIR_DIR/drivers/gs_usb.c" | cut -d ' ' -f 1)"
    if [ "$ACTUAL_SOURCE_SHA" != "$EXPECTED_SOURCE_SHA" ]; then
        echo "驱动源码校验失败，停止。" >&2
        exit 1
    fi
    cp "$REPAIR_DIR/drivers/gs_usb.c" "$WORK_DIR/gs_usb.c"
    printf 'obj-m += gs_usb.o\n' > "$WORK_DIR/Makefile"
    make -C "$HEADERS" M="$WORK_DIR" -j2 modules
    VERMAGIC="$(modinfo -F vermagic "$WORK_DIR/gs_usb.ko")"
    if [ "${VERMAGIC%% *}" != "$KERNEL_RELEASE" ]; then
        echo "编译出的模块版本不匹配，停止安装：$VERMAGIC" >&2
        exit 1
    fi
    sudo install -D -m 0644 "$WORK_DIR/gs_usb.ko" \
        "/lib/modules/$KERNEL_RELEASE/updates/piper-usb-can/gs_usb.ko"
    sudo depmod -a "$KERNEL_RELEASE"
else
    echo "已存在 gs_usb 模块，复用已有模块。"
fi
sudo modprobe can_dev
sudo modprobe can_raw
sudo modprobe gs_usb
printf '\nUSB-CAN 驱动已加载。不会使能机械臂或发送运动指令。\n'
printf '请拔插 USB-CAN，然后执行 lsusb -t 和 ip -brief link。\n'
printf '用 ethtool -i 接口名确认 driver: gs_usb，不能继续使用板载 mttcan 接口。\n'
printf '确认接口后再配置 1 Mbps 并用 candump 检查机械臂反馈。\n'
ip -brief link
