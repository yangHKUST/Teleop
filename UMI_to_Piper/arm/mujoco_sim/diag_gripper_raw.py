#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""诊断手持 DM3507 编码器读取：实时打印 raw 编码器 + 映射宽度。

用法（conda piper_pinocchio，unset PYTHONPATH）：
    python arm/mujoco_sim/diag_gripper_raw.py [/dev/ttyACM0] [motor_id]

捏合/松开手持夹爪，观察 raw 是否变化：
  * raw 恒为 0        → 电机反馈没被解析（CAN ID 不匹配 / 电机没应答 / SLCAN 没数据）。
  * raw 恒定非 0      → 反馈收到了但编码器不动（电机没上电 / 夹爪机械卡住）。
  * raw 随捏合变化    → 读取链路正常，问题在后续映射/AGX 下发。
"""
import json
import sys
import time
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO / "gripper"))

from gripper_teleop.dm_canable2 import DM_Motor_Type, Motor, MotorControl  # noqa: E402


def main() -> None:
    dev = sys.argv[1] if len(sys.argv) > 1 else "/dev/ttyACM0"
    motor_id = int(sys.argv[2]) if len(sys.argv) > 2 else 7
    calib_path = _REPO / "gripper" / "config" / "gripper_calibration.json"
    calib = json.loads(calib_path.read_text())
    c_min, c_max = float(calib["encoder_min"]), float(calib["encoder_max"])
    w_min, w_max = float(calib["width_min_m"]), float(calib["width_max_m"])

    motor = Motor(DM_Motor_Type.DM3507, motor_id, 17)
    ctrl = MotorControl(channel=dev, can_bitrate=1000000, tty_baudrate=115200)
    ctrl.addMotor(motor)

    print(f"读取 {dev}：捏合/松开夹爪，观察 raw 是否变化。ctrl-c 退出。")
    print(f"标定: encoder {c_min}~{c_max} -> width {w_min:.5f}~{w_max:.5f} m")
    print("-" * 64)

    last = None
    while True:
        try:
            ctrl.refresh_motor_status(motor)
            raw = motor.getRawEncoder()
        except Exception as exc:  # noqa: BLE001
            print(f"[异常] {exc}")
            time.sleep(0.5)
            continue

        frac = max(0.0, min(1.0, (raw - c_min) / (c_max - c_min)))
        w = w_min + frac * (w_max - w_min)
        tag = "  <== 变化" if (last is not None and raw != last) else ""
        print(f"raw={raw:6d}  width={w * 1000:6.2f}mm{tag}")
        last = raw
        time.sleep(0.1)


if __name__ == "__main__":
    main()
