# teleop/record_data.py
"""独立数据录制器（ZMQ SUB -> CSV）。

在遥操作运行时，**另开一个终端**执行（不集成进 run_teleop.sh）：

    cd /home/taoqiu/Meta_to_Piper/piper-quest3-teleop
    source ~/miniconda3/etc/profile.d/conda.sh && conda activate piper-teleop
    python -m teleop.record_data --out ~/records/session1

会在 ``--out`` 目录下生成三个 CSV（实际值与指令分开保存）：
    hand.csv        - 时间戳 + 左右手柄位姿(7)与按键/扳机/摇杆状态(14)
    arm_command.csv - 下发关节目标(6)、夹爪目标、状态机模式
    arm_actual.csv  - 实际关节角(6)、实际夹爪开度、读回时间戳

所有文件共用同一主循环时间戳 ``t`` 与墙钟时间 ``t_wall``，用于跨流同步。
"""
from __future__ import annotations

import argparse
import csv
import math
import sys
import time
from pathlib import Path

import zmq

# 与 TeleVision.py 里 right_state/left_state 的 14 个通道布局一致
STATE_NAMES = [
    "trigger", "squeeze", "touchpad", "thumbstick", "aButton", "bButton",
    "triggerValue", "squeezeValue", "touchpadX", "touchpadY",
    "thumbstickX", "thumbstickY", "aButtonValue", "bButtonValue",
]


def _fmt(x) -> str:
    if x is None:
        return ""
    try:
        f = float(x)
    except (TypeError, ValueError):
        return str(x)
    if math.isnan(f):
        return ""  # CSV 里空串，pandas 读作 NaN
    return repr(f)


def hand_columns() -> list:
    cols = ["t", "t_wall"]
    for side in ("right", "left"):
        p = side[0]
        for ax in ("px", "py", "pz", "qx", "qy", "qz", "qw"):
            cols.append(f"{p}_{ax}")
        for name in STATE_NAMES:
            cols.append(f"{p}_{name}")
    return cols


def cmd_columns() -> list:
    cols = ["t", "t_wall"]
    for side in ("right", "left"):
        p = side[0]
        cols.append(f"{p}_mode")
        for i in range(1, 7):
            cols.append(f"{p}_cmd_q{i}")
        cols.append(f"{p}_cmd_grip")
        cols.append(f"{p}_cmd_grip_vg")
    return cols


def act_columns() -> list:
    cols = ["t", "t_wall"]
    for side in ("right", "left"):
        p = side[0]
        for i in range(1, 7):
            cols.append(f"{p}_act_q{i}")
        cols.append(f"{p}_act_grip_um")
        cols.append(f"{p}_act_t")
    return cols


def hand_row(rec: dict) -> list:
    row = [rec["t"], rec["t_wall"]]
    for side in ("right", "left"):
        pose = rec.get(f"{side}_pose") or []
        state = rec.get(f"{side}_state") or []
        row += [_fmt(v) for v in pose[:7]]
        row += [_fmt(v) for v in state[:14]]
    return row


def cmd_row(rec: dict) -> list:
    row = [rec["t"], rec["t_wall"]]
    for side in ("right", "left"):
        p = side[0]
        row.append(rec.get(f"{p}_mode", ""))
        joints = rec.get(f"{p}_cmd_q") or []
        row.extend(_fmt(joints[i]) if i < len(joints) else "" for i in range(6))
        row.append(_fmt(rec.get(f"{p}_cmd_grip")))
        row.append(_fmt(rec.get(f"{p}_cmd_grip_vg")))
    return row


def act_row(rec: dict) -> list:
    row = [rec["t"], rec["t_wall"]]
    for side in ("right", "left"):
        p = side[0]
        joints = rec.get(f"{p}_act_q") or []
        row.extend(_fmt(joints[i]) if i < len(joints) else "" for i in range(6))
        row.append(_fmt(rec.get(f"{p}_act_grip_um")))
        row.append(_fmt(rec.get(f"{p}_act_t")))
    return row


class CsvSink:
    def __init__(self, out_dir: Path) -> None:
        out_dir.mkdir(parents=True, exist_ok=True)
        self._files: dict = {}
        self._writers: dict = {}
        for name, cols in (
            ("hand.csv", hand_columns()),
            ("arm_command.csv", cmd_columns()),
            ("arm_actual.csv", act_columns()),
        ):
            path = out_dir / name
            f = path.open("w", newline="")
            w = csv.writer(f)
            w.writerow(cols)
            f.flush()
            self._files[name] = f
            self._writers[name] = w
        self._last_flush = 0.0

    def write(self, rec: dict) -> None:
        self._writers["hand.csv"].writerow(hand_row(rec))
        self._writers["arm_command.csv"].writerow(cmd_row(rec))
        self._writers["arm_actual.csv"].writerow(act_row(rec))
        now = time.monotonic()
        if now - self._last_flush > 1.0:
            self._last_flush = now
            for f in self._files.values():
                f.flush()

    def close(self) -> None:
        for f in self._files.values():
            try:
                f.flush()
                f.close()
            except Exception:
                pass


def main() -> int:
    parser = argparse.ArgumentParser(
        description="遥操数据录制器：订阅主循环 ZMQ PUB，落盘为 CSV。",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="示例：python -m teleop.record_data --out ~/records/session1",
    )
    parser.add_argument("--out", default="records", help="输出目录（默认 ./records）")
    parser.add_argument("--endpoint", default="tcp://127.0.0.1:5559", help="ZMQ 订阅端点")
    parser.add_argument("--max-seconds", type=float, default=0.0,
                        help="录制时长上限(秒)，0=直到 Ctrl+C")
    args = parser.parse_args()

    out_dir = Path(args.out).expanduser()
    ctx = zmq.Context()
    sock = ctx.socket(zmq.SUB)
    sock.setsockopt(zmq.SUBSCRIBE, b"")
    sock.setsockopt(zmq.RCVTIMEO, 1000)  # 1s 超时，便于 Ctrl+C 退出
    sock.connect(args.endpoint)

    sink = CsvSink(out_dir)
    print(f"[record] subscribing {args.endpoint} -> {out_dir.resolve()}", flush=True)
    print("[record] Ctrl+C to stop.", flush=True)

    t0 = time.monotonic()
    n = 0
    try:
        while True:
            if args.max_seconds > 0 and time.monotonic() - t0 >= args.max_seconds:
                break
            try:
                rec = sock.recv_json()
            except zmq.Again:
                continue
            except zmq.ZMQError:
                break
            if not isinstance(rec, dict):
                continue
            sink.write(rec)
            n += 1
    except KeyboardInterrupt:
        pass
    finally:
        sink.close()
        sock.close(linger=0)
        ctx.term()
    print(f"[record] done: {n} records -> {out_dir.resolve()}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
