#!/usr/bin/env python3
"""双臂合并双目查看器：把两个 VIO 图像流拼进同一个窗口。

每个 cyperstereo_online 进程（VIO_IMG_ZMQ_ENDPOINT）发 3 段 ZMQ 多帧消息：
    [0] timestamp (double, 8B)   [1] left_jpg (bytes)   [2] right_jpg (bytes)
本脚本把每臂左右眼 hconcat，再把臂1/臂2 vconcat 到同一个 OpenCV 窗口，
省得双臂同时跑时 4 个相机窗口看不过来。

退出方式：
  * 按 q / Esc 手动关；
  * 两臂都退出（两个流都静默超过 --stale-s 秒）时自动关，配合「Ctrl+C 全关」。
"""
from __future__ import annotations

import argparse
import time

import cv2
import numpy as np
import zmq


def _make_socket(ctx: zmq.Context, endpoint: str) -> zmq.Socket:
    s = ctx.socket(zmq.SUB)
    s.setsockopt(zmq.SUBSCRIBE, b"")
    s.setsockopt(zmq.LINGER, 0)
    s.setsockopt(zmq.RCVTIMEO, 200)  # ms；非阻塞接收
    s.connect(endpoint)
    return s


def _recv_stereo(sock: zmq.Socket):
    """收一帧，返回左右并排 BGR 图；超时/格式异常返回 None。"""
    try:
        parts = sock.recv_multipart()
    except zmq.Again:
        return None
    if len(parts) != 3:
        return None
    left = cv2.imdecode(np.frombuffer(parts[1], dtype=np.uint8), cv2.IMREAD_COLOR)
    right = cv2.imdecode(np.frombuffer(parts[2], dtype=np.uint8), cv2.IMREAD_COLOR)
    if left is None or right is None:
        return None
    return np.hstack([left, right])


def _placeholder(tag: str, width: int) -> np.ndarray:
    img = np.full((int(width * 0.4), width, 3), 40, dtype=np.uint8)
    cv2.putText(img, f"{tag}: waiting for stream...", (20, int(width * 0.22)),
                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 200, 255), 2)
    return img


def _fit_width(img: np.ndarray, width: int) -> np.ndarray:
    h, w = img.shape[:2]
    if w == width:
        return img
    return cv2.resize(img, (width, max(1, int(round(h * width / w)))))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--ep1", default="tcp://127.0.0.1:5556", help="臂1 图像端点")
    ap.add_argument("--ep2", default="tcp://127.0.0.1:5558", help="臂2 图像端点")
    ap.add_argument("--label1", default="arm1", help="臂1 标签")
    ap.add_argument("--label2", default="arm2", help="臂2 标签")
    ap.add_argument("--width", type=int, default=960, help="每臂并排行的显示宽度 (px)")
    ap.add_argument("--stale-s", type=float, default=3.0,
                    help="两臂都静默超过该秒数即视为全部退出，自动关窗")
    args = ap.parse_args()

    ctx = zmq.Context()
    s1 = _make_socket(ctx, args.ep1)
    s2 = _make_socket(ctx, args.ep2)

    last1: np.ndarray | None = None
    last2: np.ndarray | None = None
    last_t1 = last_t2 = time.monotonic()  # 收帧时间戳
    ever1 = ever2 = False

    win = "dual stereo (arm1 / arm2)"
    cv2.namedWindow(win, cv2.WINDOW_NORMAL)
    print(f"[dual-viewer] {args.ep1} + {args.ep2} → 单窗口合并；q/Esc 退出")

    while True:
        f1 = _recv_stereo(s1)
        if f1 is not None:
            last1, last_t1, ever1 = f1, time.monotonic(), True
        f2 = _recv_stereo(s2)
        if f2 is not None:
            last2, last_t2, ever2 = f2, time.monotonic(), True

        top = _fit_width(last1 if last1 is not None else _placeholder(args.label1, args.width),
                         args.width)
        bot = _fit_width(last2 if last2 is not None else _placeholder(args.label2, args.width),
                         args.width)
        canvas = np.vstack([top, bot])
        cv2.putText(canvas, args.label1, (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.9,
                    (0, 255, 0), 2)
        cv2.putText(canvas, args.label2, (10, top.shape[0] + 25),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 0), 2)
        cv2.imshow(win, canvas)

        key = cv2.waitKey(1) & 0xFF
        if key in (ord("q"), 27):
            print("[dual-viewer] 手动退出")
            break

        # 只要「曾经出过帧」的臂都已静默，就视为全部退出自动关窗（配合「Ctrl+C 全关」）；
        # 两臂都从未出过帧（还没启动）则继续等。
        now = time.monotonic()
        if (ever1 or ever2) and \
                (not ever1 or (now - last_t1) > args.stale_s) and \
                (not ever2 or (now - last_t2) > args.stale_s):
            print("[dual-viewer] 图像流已全部停止，自动退出")
            break

    cv2.destroyAllWindows()
    s1.close()
    s2.close()
    ctx.term()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
