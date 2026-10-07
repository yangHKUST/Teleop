#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
ROOT="$PWD"
trap 'echo "[ERROR] 部署失败，行号 $LINENO；修复后可重新运行 bash setup_jetson.sh" >&2' ERR
[[ $(uname -s) == Linux && $(uname -m) == aarch64 ]] || { echo '此脚本仅用于 Linux ARM64 Jetson'; exit 1; }
[[ -f piper-quest3-teleop/teleop/teleop_real_arm.py ]] || { echo '缺少项目源码'; exit 1; }
[[ $EUID != 0 ]] || { echo '请以普通用户运行，安装系统包时再输入 sudo 密码'; exit 1; }
unset PYTHONPATH LD_LIBRARY_PATH PYTHONHOME
export PYTHONNOUSERSITE=1
mkdir -p .runtime/bin .runtime/logs
exec > >(tee -a .runtime/logs/setup.log) 2>&1
uname -a
df -h "$ROOT"
free -h
sudo apt-get update
sudo apt-get install -y curl bzip2 ca-certificates openssl iproute2 can-utils ethtool libgl1 libglfw3
if [[ ! -x .runtime/bin/micromamba ]]; then
    curl --fail --location --retry 3 https://micro.mamba.pm/api/micromamba/linux-aarch64/latest -o .runtime/micromamba.tar.bz2
    tar -xjf .runtime/micromamba.tar.bz2 -C .runtime bin/micromamba
fi
export MAMBA_ROOT_PREFIX="$ROOT/.runtime/mamba"
if [[ ! -x .runtime/env/bin/python ]]; then
    .runtime/bin/micromamba create -y --override-channels -c conda-forge -p "$ROOT/.runtime/env" python=3.11 pip
fi
.runtime/env/bin/python -m pip install -r deployment/requirements-jetson.txt
bash start_jetson.sh --check
CERTDIR="$ROOT/piper-quest3-teleop/teleop"
# 不覆盖已有成对证书。缺少其中任一文件时停止，避免覆盖另一文件。
if [[ ! -e "$CERTDIR/cert.pem" && ! -e "$CERTDIR/key.pem" ]]; then
    openssl req -x509 -nodes -newkey rsa:2048 -days 365 \
        -keyout "$CERTDIR/key.pem" -out "$CERTDIR/cert.pem" \
        -subj '/CN=jetson-teleop' -addext 'subjectAltName=DNS:localhost,IP:127.0.0.1'
fi
[[ -f "$CERTDIR/cert.pem" && -f "$CERTDIR/key.pem" ]] || { echo '证书不完整，请补齐 cert.pem / key.pem'; exit 1; }
chmod 600 "$CERTDIR/key.pem"
openssl x509 -in "$CERTDIR/cert.pem" -noout -dates
printf '\n部署完成。无硬件演练：bash start_jetson.sh --dry-run --can can1\n'
echo '证书为自签名；头显需认可证书。正式部署请使用包含 Jetson 局域网 IP 的受信任证书。'
