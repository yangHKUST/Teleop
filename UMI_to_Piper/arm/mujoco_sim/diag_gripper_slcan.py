#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""裸 SLCAN 逐字节诊断（v2）：区分 ACK 与无应答，全波特率扫描 + 错误帧。

用法（conda piper_pinocchio）：
    python arm/mujoco_sim/diag_gripper_slcan.py [/dev/ttyACM0]
"""
import sys
import time

import serial

# slcan 标准波特率索引 S0..S8
BITRATES = [
    ("S8", 1000000), ("S7", 800000), ("S6", 500000), ("S5", 250000),
    ("S4", 125000), ("S3", 100000), ("S2", 50000), ("S1", 20000),
    ("S0", 10000),
]


def tx(ser, cmd: str) -> None:
    ser.write((cmd + "\r").encode("ascii"))
    ser.flush()


def read_lines(ser, seconds: float, label: str) -> int:
    print(f"--- {label} ({seconds}s) ---")
    end = time.monotonic() + seconds
    n = 0
    buf = b""
    while time.monotonic() < end:
        b = ser.read(ser.in_waiting or 1)
        if not b:
            continue
        buf += b
        while b"\r" in buf:
            line, buf = buf.split(b"\r", 1)
            n += 1
            if line == b"":
                print("  <== (ACK 空行 \\r)")
            else:
                print(f"  <== {line!r}")
    if buf:
        n += 1
        print(f"  <== (tail 无\\r) {buf!r}")
    if n == 0:
        print("  （无应答）")
    return n


def command(ser, cmd: str, wait: float = 0.3) -> int:
    tx(ser, cmd)
    time.sleep(wait)
    print(f"  >> {cmd!r}")
    return read_lines(ser, 0.3, "resp")


def main() -> None:
    dev = sys.argv[1] if len(sys.argv) > 1 else "/dev/ttyACM0"
    ser = serial.Serial(dev, 115200, timeout=0.1)
    print(f"已打开 {dev}（115200 8N1）")

    print("\n[1] SLCAN 握手（ACK=空行\\r 才算成功）")
    command(ser, "V")
    command(ser, "N")
    command(ser, "S8")
    command(ser, "O")
    command(ser, "F1")   # 尝试打开 status/error 帧（部分固件支持）

    print("\n[2] 发 enable(ID=0x007) + 状态查询(0x7FF) 后监听")
    tx(ser, "t0078FFFFFFFFFFFFFFFC")
    time.sleep(0.1)
    tx(ser, "t7FF80700CC00000000")
    read_lines(ser, 1.0, "发帧后")

    print("\n[3] 全波特率扫描")
    for scmd, bitrate in BITRATES:
        tx(ser, "C"); time.sleep(0.05)
        tx(ser, scmd); time.sleep(0.05)
        tx(ser, "O"); time.sleep(0.05)
        tx(ser, "t7FF80700CC00000000")
        read_lines(ser, 0.9, f"{scmd} ({bitrate} bps)")

    tx(ser, "C")
    ser.close()
    print("\n结束。")


if __name__ == "__main__":
    main()
