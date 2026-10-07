#!/usr/bin/env python3
import argparse
import re
from pathlib import Path


def parse_float_list(raw: str):
    return [float(x) for x in re.findall(r"[-+]?(?:\d+\.\d*|\.\d+|\d+)(?:[eE][-+]?\d+)?", raw)]


def parse_matrix4(text: str, label: str):
    idx = text.find(label)
    if idx < 0:
        raise ValueError(f"Cannot find matrix label: {label}")
    m = re.search(r"\[\[(.*?)\]\]", text[idx:], re.DOTALL)
    if not m:
        raise ValueError(f"Cannot parse matrix body for: {label}")
    nums = parse_float_list(m.group(1))
    if len(nums) != 16:
        raise ValueError(f"Expected 16 values for {label}, got {len(nums)}")
    return [nums[i * 4 : (i + 1) * 4] for i in range(4)]


def parse_camera_block(text: str, camera_name: str):
    m = re.search(
        rf"{camera_name}\s*\n-+\s*\n.*?Focal length:\s*\[([^\]]+)\]\s*\n"
        rf"\s*Principal point:\s*\[([^\]]+)\]\s*\n"
        rf".*?Distortion coefficients:\s*\[([^\]]+)\]",
        text,
        re.DOTALL,
    )
    if not m:
        raise ValueError(f"Cannot parse {camera_name} block")
    focal = parse_float_list(m.group(1))
    principal = parse_float_list(m.group(2))
    coeffs = parse_float_list(m.group(3))
    if len(focal) != 2 or len(principal) != 2 or len(coeffs) != 4:
        raise ValueError(f"Unexpected parameter count in {camera_name} block")
    return {
        "fx": focal[0],
        "fy": focal[1],
        "cx": principal[0],
        "cy": principal[1],
        "k1": coeffs[0],
        "k2": coeffs[1],
        "k3": coeffs[2],
        "k4": coeffs[3],
    }


def transpose3x3(m):
    return [[m[j][i] for j in range(3)] for i in range(3)]


def matvec3(m, v):
    return [sum(m[i][j] * v[j] for j in range(3)) for i in range(3)]


def invert_se3_4x4(T):
    R = [row[:3] for row in T[:3]]
    t = [row[3] for row in T[:3]]
    Rt = transpose3x3(R)
    t_inv = [-x for x in matvec3(Rt, t)]
    out = [[0.0] * 4 for _ in range(4)]
    for i in range(3):
        for j in range(3):
            out[i][j] = Rt[i][j]
        out[i][3] = t_inv[i]
    out[3][3] = 1.0
    return out


def fmt(x: float) -> str:
    s = f"{x:.15f}".rstrip("0").rstrip(".")
    if s in {"-0", "-0.0", ""}:
        return "0"
    return s


def format_matrix_data_rows(matrix_rows, data_indent: str, row_indent: str):
    rows = []
    for row in matrix_rows:
        rows.append(", ".join(fmt(v) for v in row))
    if len(rows) == 1:
        return f"{data_indent}data: [ {rows[0]} ]"
    lines = [f"{data_indent}data: [ {rows[0]},"]
    for i in range(1, len(rows)):
        suffix = "," if i < len(rows) - 1 else "]"
        lines.append(f"{row_indent}{rows[i]}{suffix}")
    return "\n".join(lines)


def replace_scalar(yaml_text: str, key: str, value: float):
    pattern = rf"(^\s*{re.escape(key)}:\s*).*$"
    repl = rf"\g<1>{fmt(value)}"
    out, n = re.subn(pattern, repl, yaml_text, flags=re.MULTILINE)
    if n != 1:
        raise ValueError(f"Failed to replace scalar key: {key}")
    return out


def replace_matrix_block(yaml_text: str, key: str, expected_rows: int, new_data_block: str):
    pattern = (
        rf"({re.escape(key)}:\s*!!opencv-matrix\s*\n"
        rf"\s*rows:\s*{expected_rows}\s*\n"
        rf"\s*cols:\s*4\s*\n"
        rf"\s*dt:\s*f\s*\n)"
        rf"\s*data:\s*\[[\s\S]*?\]"
    )
    out, n = re.subn(pattern, rf"\1{new_data_block}", yaml_text, flags=re.DOTALL)
    if n != 1:
        raise ValueError(f"Failed to replace {key} matrix data")
    return out


def main():
    parser = argparse.ArgumentParser(
        description="Convert imucam calibration txt into cyperstereo YAML."
    )
    parser.add_argument("calib_txt", help="Path to cyperstereo_imu_calibra-results-imucam.txt")
    parser.add_argument(
        "-t",
        "--template",
        default="cyperstereo_sn_c72.yaml",
        help="Template YAML path (default: cyperstereo_sn_c72.yaml)",
    )
    parser.add_argument(
        "-o",
        "--output",
        default="cyperstereo_sn_c72.generated.yaml",
        help="Output YAML path",
    )
    parser.add_argument(
        "--swap-cameras",
        action="store_true",
        help=(
            "By default the bag maps /cam0 = C2 (SDK left_image) = physical LEFT "
            "eye and /cam1 = C1 (SDK right_image) = physical RIGHT eye, so "
            "Camera=cam0 (left), Camera2=cam1 (right), Tbc=T_ic(cam0->imu0).  "
            "Pass this flag only if a particular bag recorded /cam0 and /cam1 "
            "the other way around."
        ),
    )
    args = parser.parse_args()

    calib_text = Path(args.calib_txt).read_text(encoding="utf-8")
    yaml_text = Path(args.template).read_text(encoding="utf-8")

    cam0 = parse_camera_block(calib_text, "cam0")
    cam1 = parse_camera_block(calib_text, "cam1")
    T_cam0_cam1 = parse_matrix4(calib_text, "Baseline (cam0 to cam1):")

    if args.swap_cameras:
        # Swap: Camera(left)=cam1, Camera2(right)=cam0. Tlr = right->left =
        # cam0->cam1 = the baseline itself (NOT inverted), so bf stays positive.
        left, right = cam1, cam0
        Tbc = parse_matrix4(calib_text, "T_ic:  (cam1 to imu0):")
        Tlr_full = T_cam0_cam1
    else:
        # Default: Camera(left)=cam0, Camera2(right)=cam1. Tlr = right->left =
        # cam1->cam0 = inverse of the baseline.
        left, right = cam0, cam1
        Tbc = parse_matrix4(calib_text, "T_ic:  (cam0 to imu0):")
        Tlr_full = invert_se3_4x4(T_cam0_cam1)

    Tlr = [row[:4] for row in Tlr_full[:3]]
    bf = left["fx"] * Tlr[0][3]

    scalar_map = {
        "Camera.fx": left["fx"],
        "Camera.fy": left["fy"],
        "Camera.cx": left["cx"],
        "Camera.cy": left["cy"],
        "Camera.k1": left["k1"],
        "Camera.k2": left["k2"],
        "Camera.k3": left["k3"],
        "Camera.k4": left["k4"],
        "Camera2.fx": right["fx"],
        "Camera2.fy": right["fy"],
        "Camera2.cx": right["cx"],
        "Camera2.cy": right["cy"],
        "Camera2.k1": right["k1"],
        "Camera2.k2": right["k2"],
        "Camera2.k3": right["k3"],
        "Camera2.k4": right["k4"],
        "Camera.bf": bf,
    }
    for k, v in scalar_map.items():
        yaml_text = replace_scalar(yaml_text, k, v)

    tlr_data = format_matrix_data_rows(Tlr, data_indent="  ", row_indent="          ")
    tbc_data = format_matrix_data_rows(Tbc, data_indent="   ", row_indent="           ")

    yaml_text = replace_matrix_block(yaml_text, "Tlr", expected_rows=3, new_data_block=tlr_data)
    yaml_text = replace_matrix_block(yaml_text, "Tbc", expected_rows=4, new_data_block=tbc_data)

    Path(args.output).write_text(yaml_text, encoding="utf-8")
    print(f"Generated: {args.output}")


if __name__ == "__main__":
    main()
