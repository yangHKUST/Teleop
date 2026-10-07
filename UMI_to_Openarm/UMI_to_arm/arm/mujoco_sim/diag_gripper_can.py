#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""裸 SLCAN 抓包：确认 DM3507 是否应答状态查询、以及应答的 CAN ID / 数据。

用法（conda piper_pinocchio）：
    python arm/mujoco_sim/diag_gripper_can.py [/dev/ttyACM0] [motor_id]

会依次做三件事：
  1) 静默监听 1s（看电机是否在自发广播）
  2) 发 DM 状态查询帧 0x7FF + [id,0xCC...]，收 1s
  3) 发 enable(0xFC) 后再查一次，收 1s
"""
import sys
import time

import can


def listen(bus, seconds, label):
    print(f"\n--- {label} ({seconds}s) ---")
    end = time.monotonic() + seconds
    n = 0
    while time.monotonic() < end:
        msg = bus.recv(timeout=0.2)
        if msg is None:
            continue
        n += 1
        print(f"  ID=0x{msg.arbitration_id:03X}  DLC={len(msg.data)}  "
              f"data={msg.data.hex(' ').upper()}")
    if n == 0:
        print("  （无任何帧）")
    return n


def main() -> None:
    dev = sys.argv[1] if len(sys.argv) > 1 else "/dev/ttyACM0"
    motor_id = int(sys.argv[2]) if len(sys.argv) > 2 else 7
    bus = can.interface.Bus(interface="slcan", channel=dev,
                            bitrate=1000000, ttyBaudrate=115200)
    print(f"已打开 {dev}（SLCAN，1 Mbps），motor_id=0x{motor_id:02X}")

    # 1) 静默监听：DM 电机有时会自发广播
    listen(bus, 1.0, "静默监听")

    # 2) 状态查询 motor id
    q = can.Message(arbitration_id=0x7FF, is_extended_id=False,
                    data=bytes([motor_id, 0x00, 0xCC, 0x00, 0x00, 0x00, 0x00, 0x00]))
    bus.send(q)
    listen(bus, 1.0, f"状态查询 0x7FF[id={motor_id},0xCC] 后")

    # 3) enable 后再查（有些电机 enable 后才报状态）
    en = can.Message(arbitration_id=motor_id, is_extended_id=False,
                     data=bytes([0xFF] * 7 + [0xFC]))
    bus.send(en)
    listen(bus, 0.5, "enable 0xFC 后")
    bus.send(q)
    listen(bus, 1.0, "enable 后再次状态查询")

    bus.shutdown()
    print("\n抓包结束。若全程无任何帧 → 电机没上电 / CAN 线没接 / SLCAN 没数据。")


if __name__ == "__main__":
    main()
