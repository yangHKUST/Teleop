# teleop/recorder_pub.py
"""ZMQ PUB 发布器：主遥操循环每帧发布一条 JSON 记录。

`record_data.py`（另开终端独立运行）订阅该端点并把数据落盘为 CSV。
发布器用 NOBLOCK 发送，没有订阅者时直接丢弃，不影响控制回路。
"""
from __future__ import annotations

import time
from typing import Any, Dict

import numpy as np
import zmq


def _flat(arr) -> list:
    """任意数组/列表 -> Python float 列表（JSON 可序列化）。"""
    return [float(x) for x in np.asarray(arr, dtype=float).reshape(-1)]


class RecorderPub:
    def __init__(self, endpoint: str = "tcp://127.0.0.1:5559") -> None:
        self._ctx = zmq.Context()
        self._sock = self._ctx.socket(zmq.PUB)
        self._sock.setsockopt(zmq.SNDHWM, 1000)
        self._sock.setsockopt(zmq.LINGER, 0)
        self._sock.bind(endpoint)

    def publish(self, record: Dict[str, Any]) -> None:
        try:
            self._sock.send_json(record, flags=zmq.NOBLOCK)
        except zmq.ZMQError:
            pass

    def close(self) -> None:
        try:
            self._sock.close(linger=0)
        except zmq.ZMQError:
            pass
        try:
            self._ctx.term()
        except Exception:
            pass


def build_record(rt, right_pose, left_pose) -> Dict[str, Any]:
    """从当前运行时状态组装一帧平铺记录。

    字段（供 record_data.py 拆分到三个 CSV）：
      t / t_wall              主循环时间戳 / 墙钟时间
      {right,left}_pose       手柄位姿 7 维 (x,y,z,qx,qy,qz,qw)
      {right,left}_state      手柄状态 14 维（trigger/squeeze/.../bButtonValue）
      {r,l}_mode              机械臂状态机模式
      {r,l}_cmd_q             下发关节目标 6 维 (rad)
      {r,l}_cmd_grip          下发夹爪目标 (0..1000)
      {r,l}_cmd_grip_vg       归一化夹爪目标 (0..1)
      {r,l}_act_q             实际关节角 6 维 (rad，无硬件时为 NaN)
      {r,l}_act_grip_um       实际夹爪开度 (um，无硬件时为 NaN)
      {r,l}_act_t             实际值最近读回时间 (monotonic)
    """
    tv = rt.teleoperator
    rec: Dict[str, Any] = {
        "t": float(time.perf_counter()),
        "t_wall": float(time.time()),
        "right_pose": _flat(right_pose),
        "left_pose": _flat(left_pose),
        "right_state": _flat(tv.right_state),
        "left_state": _flat(tv.left_state),
    }
    for side, arm in rt.arms.items():
        p = side[0]  # "r" / "l"
        rec[f"{p}_mode"] = str(arm.mode)
        rec[f"{p}_cmd_q"] = _flat(np.asarray(arm.last_q[:6], dtype=float))
        rec[f"{p}_cmd_grip"] = float(getattr(arm, "last_grip_out", 0.0) or 0.0)
        rec[f"{p}_cmd_grip_vg"] = float(getattr(arm, "last_grip_vg", 0.0) or 0.0)
        if arm.q_actual is not None:
            rec[f"{p}_act_q"] = _flat(np.asarray(arm.q_actual[:], dtype=float))
            rec[f"{p}_act_grip_um"] = float(arm.gripper_actual.value)
            rec[f"{p}_act_t"] = float(arm.actual_time.value)
        else:
            rec[f"{p}_act_q"] = [float("nan")] * 6
            rec[f"{p}_act_grip_um"] = float("nan")
            rec[f"{p}_act_t"] = 0.0
    return rec
