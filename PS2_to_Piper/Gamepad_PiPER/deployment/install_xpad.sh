#!/usr/bin/env bash
# Build only xpad against the running Jetson kernel; do not replace kernel Image.
set -Eeuo pipefail
trap 'echo "驱动安装未完成（第 $LINENO 行）。请保留上方完整报错。" >&2' ERR
REPAIR_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
KERNEL_RELEASE="$(uname -r)"
if [ "$EUID" -eq 0 ]; then
    echo "请以普通用户运行 bash install_xpad.sh，脚本在需要时调用 sudo。" >&2
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
sudo apt-get install -y build-essential bc flex bison libssl-dev kmod
HEADER_RELEASE="$(make -s -C "$HEADERS" kernelrelease)"
if [ "$HEADER_RELEASE" != "$KERNEL_RELEASE" ]; then
    echo "头文件版本 $HEADER_RELEASE 与运行内核 $KERNEL_RELEASE 不一致，停止。" >&2
    exit 1
fi
if ! modinfo xpad >/dev/null 2>&1; then
    WORK_DIR="$REPAIR_DIR/.runtime/xpad-build-$KERNEL_RELEASE"
    mkdir -p "$WORK_DIR"
    EXPECTED_SOURCE_SHA="34a522dc1a3bdb8434334a1b1a67bde678adcaa0eafa14b38ee1f9c02d2070e7"
    ACTUAL_SOURCE_SHA="$(sha256sum "$REPAIR_DIR/drivers/xpad.c" | cut -d ' ' -f 1)"
    if [ "$ACTUAL_SOURCE_SHA" != "$EXPECTED_SOURCE_SHA" ]; then
        echo "驱动源码校验失败，停止。" >&2
        exit 1
    fi
    cp "$REPAIR_DIR/drivers/xpad.c" "$WORK_DIR/xpad.c"
    printf 'obj-m += xpad.o\n' > "$WORK_DIR/Makefile"
    # Rumble/LED extras are not required for the input-only teleoperation driver.
    make -C "$HEADERS" M="$WORK_DIR" -j2 modules
    VERMAGIC="$(modinfo -F vermagic "$WORK_DIR/xpad.ko")"
    if [ "${VERMAGIC%% *}" != "$KERNEL_RELEASE" ]; then
        echo "编译出的模块版本不匹配，停止安装：$VERMAGIC" >&2
        exit 1
    fi
    sudo install -D -m 0644 "$WORK_DIR/xpad.ko" \
        "/lib/modules/$KERNEL_RELEASE/updates/piper-gamepad/xpad.ko"
    sudo depmod -a "$KERNEL_RELEASE"
else
    echo "已存在 xpad 模块，复用已有模块。"
fi
sudo modprobe xpad
# Grant only this controller's event devices; do not grant all keyboard input.
sudo groupadd -f piper-gamepad
sudo usermod -a -G piper-gamepad "$(id -un)"
printf '%s\n' 'SUBSYSTEM=="input", KERNEL=="event*", ATTRS{idVendor}=="045e", ATTRS{idProduct}=="028e", GROUP="piper-gamepad", MODE="0660"' \
    | sudo tee /etc/udev/rules.d/70-piper-gamepad.rules >/dev/null
sudo udevadm control --reload-rules
sudo udevadm trigger --subsystem-match=input
printf '\n驱动已加载，手柄权限规则已设置。\n'
printf '请拔插接收器，完成配对，然后 exit 退出并重新 SSH 登录，让新用户组生效。\n'
printf '重新登录后运行 bash start.sh virtual --check，仍须验证按键映射。\n'
printf '内核升级后需针对新内核重新编译；本脚本不会替换内核或自动重启。\n'
