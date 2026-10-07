#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Kalibr camchain*.yaml → ORB-SLAM3 Cyperstereo yaml 转换器。

把 Kalibr 标定输出（camchain.yaml + camchain-imucam.yaml）转换成
ORB-SLAM3-Cyperstereo 的相机配置文件（Camera/Camera2 内参 + 畸变 + Tlr + Tbc）。

用法：
    python3 kalibr_to_orbslam3_yaml.py \
        --camchain      s200032/camchain.yaml \
        --camchain-imu  s200032/camchain-imucam.yaml \
        -t              cyperstereo_sn_c72.yaml \
        -o              cyperstereo_sn_s200032.yaml \
        --swap-cameras

左右眼映射：
    默认 Camera(左)=cam0, Camera2(右)=cam1。
    --swap-cameras → Camera(左)=cam1, Camera2(右)=cam0。
    s200032 需要 --swap-cameras：见 cyperstereo_online.cc 注释，
    SDK "left_image"(C1)=cam1=物理左眼, "right_image"(C2)=cam0=物理右眼。

约定（与 ORB-SLAM3 / Kalibr 一致）：
    - Camera.type 用 KannalaBrandt8，系数与 Kalibr equidistant 的 4 个系数一一对应。
    - Tlr = 右相机 → 左相机（3x4），bf = left.fx * Tlr[0][3]。
    - Tbc = T_cam_imu（左相机），Kalibr 的 T_cam_imu 即 body(imu)→camera。
    - 分辨率取 camchain.yaml 的 resolution，同时写 Camera.width/height 与 lapping。
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import numpy as np

try:
    import yaml
except ImportError:
    sys.exit("需要 PyYAML：pip install pyyaml")


def load_yaml(path: Path) -> dict:
    return yaml.safe_load(Path(path).read_text(encoding="utf-8"))


def invert_se3(T):
    """4x4 齐次变换求逆。"""
    R = np.array(T, dtype=float)[:3, :3]
    t = np.array(T, dtype=float)[:3, 3]
    out = np.eye(4, dtype=float)
    out[:3, :3] = R.T
    out[:3, 3] = -R.T @ t
    return out


def fmt_matrix_rows(M):
    """把 numpy 矩阵格式化成 ORB-SLAM3 yaml 的 data 行（单行，缩进由 head 保留）。"""
    vals = [f"{v:.12g}" for v in np.asarray(M, dtype=float).ravel().tolist()]
    body = ", ".join(vals)
    return f"data: [ {body}]"


def replace_block(yaml_text: str, label: str, rows: int, M) -> str:
    """替换 !!opencv-matrix 块的 data 行（Tlr/Tbc）。"""
    pattern = re.compile(
        rf"(?P<head>{re.escape(label)}: !!opencv-matrix\s*\n(?:[ \t]*rows: {rows}\s*\n"
        rf"[ \t]*cols: \d+\s*\n[ \t]*dt: f\s*\n)[ \t]*)data: \[[^\]]*\]",
        re.MULTILINE,
    )
    m = pattern.search(yaml_text)
    if not m:
        raise ValueError(f"模板里找不到 matrix block: {label}")
    new_data = fmt_matrix_rows(M)
    return yaml_text[: m.start()] + m.group("head") + new_data + yaml_text[m.end():]


def replace_scalar(yaml_text: str, key: str, value) -> str:
    pattern = re.compile(rf"(?m)^({re.escape(key)}:)\s*[-+0-9.eE]+")
    new = f"\\1 {value:.12g}"
    out, n = pattern.subn(new, yaml_text, count=1)
    if n == 0:
        raise ValueError(f"模板里找不到标量字段: {key}")
    return out


def replace_int(yaml_text: str, key: str, value: int) -> str:
    pattern = re.compile(rf"(?m)^({re.escape(key)}:)\s*\d+")
    out, n = pattern.subn(rf"\1 {value}", yaml_text, count=1)
    if n == 0:
        raise ValueError(f"模板里找不到整数字段: {key}")
    return out


def parse_camera(chain: dict, name: str) -> dict:
    c = chain[name]
    fx, fy, cx, cy = [float(v) for v in c["intrinsics"]]
    k1, k2, k3, k4 = [float(v) for v in c["distortion_coeffs"]]
    return {"fx": fx, "fy": fy, "cx": cx, "cy": cy,
            "k1": k1, "k2": k2, "k3": k3, "k4": k4}


def main() -> None:
    ap = argparse.ArgumentParser(description="Kalibr -> ORB-SLAM3 Cyperstereo yaml")
    ap.add_argument("--camchain", required=True, help="Kalibr camchain.yaml")
    ap.add_argument("--camchain-imu", required=True, help="Kalibr camchain-imucam.yaml")
    ap.add_argument("-t", "--template", default="cyperstereo_sn_c72.yaml")
    ap.add_argument("-o", "--output", required=True)
    ap.add_argument("--swap-cameras", action="store_true",
                    help="Camera(左)=cam1, Camera2(右)=cam0（s200032 需要）")
    args = ap.parse_args()

    chain = load_yaml(Path(args.camchain))
    chain_imu = load_yaml(Path(args.camchain_imu))
    template = Path(args.template).read_text(encoding="utf-8")

    cam0 = parse_camera(chain, "cam0")
    cam1 = parse_camera(chain, "cam1")
    T_cam0_cam1 = np.array(chain["cam1"]["T_cn_cnm1"], dtype=float)  # cam0 -> cam1

    # 分辨率：取 cam0 的 resolution
    res = chain["cam0"].get("resolution", [1280, 1024])
    width, height = int(res[0]), int(res[1])

    if args.swap_cameras:
        left, right = cam1, cam0
        Tbc = np.array(chain_imu["cam1"]["T_cam_imu"], dtype=float)
        Tlr_full = T_cam0_cam1            # 右(cam0) -> 左(cam1)
    else:
        left, right = cam0, cam1
        Tbc = np.array(chain_imu["cam0"]["T_cam_imu"], dtype=float)
        Tlr_full = invert_se3(T_cam0_cam1)  # 右(cam1) -> 左(cam0)

    Tlr = Tlr_full[:3, :]  # 3x4
    bf = left["fx"] * float(Tlr[0, 3])

    scalars = {
        "Camera.fx": left["fx"], "Camera.fy": left["fy"],
        "Camera.cx": left["cx"], "Camera.cy": left["cy"],
        "Camera.k1": left["k1"], "Camera.k2": left["k2"],
        "Camera.k3": left["k3"], "Camera.k4": left["k4"],
        "Camera2.fx": right["fx"], "Camera2.fy": right["fy"],
        "Camera2.cx": right["cx"], "Camera2.cy": right["cy"],
        "Camera2.k1": right["k1"], "Camera2.k2": right["k2"],
        "Camera2.k3": right["k3"], "Camera2.k4": right["k4"],
        "Camera.bf": bf,
    }
    text = template
    for k, v in scalars.items():
        text = replace_scalar(text, k, v)

    text = replace_block(text, "Tlr", rows=3, M=Tlr)
    text = replace_block(text, "Tbc", rows=4, M=Tbc)

    # 分辨率与 lapping（整幅）
    for key in ("Camera.width",):
        text = replace_int(text, key, width)
    for key in ("Camera.height",):
        text = replace_int(text, key, height)
    for key in ("Camera.lappingEnd", "Camera2.lappingEnd"):
        text = replace_int(text, key, width - 1)

    Path(args.output).write_text(text, encoding="utf-8")

    print(f"生成: {args.output}")
    print(f"  左眼 Camera  = {'cam1' if args.swap_cameras else 'cam0'}  fx={left['fx']:.4f} cy={left['cy']:.2f}")
    print(f"  右眼 Camera2 = {'cam0' if args.swap_cameras else 'cam1'}  fx={right['fx']:.4f} cy={right['cy']:.2f}")
    print(f"  baseline = {abs(float(Tlr[0,3]))*1000:.2f} mm,  bf = {bf:.3f}")
    print(f"  分辨率 = {width}x{height}")


if __name__ == "__main__":
    main()
