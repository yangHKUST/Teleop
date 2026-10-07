#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""CyperstereoSDK 双目 + IMU 实时预览 (纯 Python / V4L2)。

本 SDK 没有 Python 绑定，也没有 extern "C" 接口，所以这里直接以普通 UVC 设备
打开相机，并在 Python 侧复刻 SDK 的解析流程:

    UVC YUYV 帧  ->  双 Bayer 平面去交织  ->  demosaic  ->  末行 metadata 解析 IMU

参数在下面 "用户配置" 区调节，改任意一个，其余会自动匹配 (见 resolve_config)。

用法:
    python3 camera.py            # 预览
    python3 camera.py --no-gui   # 无显示，只打印统计
按 q 或 ESC 退出，s 保存当前左右图。
"""

import fcntl
import os
import sys
import time
import glob
import argparse

import cv2
import numpy as np

# ============================================================================
# 用户配置 —— 只改这里
# ============================================================================

# 分辨率。None 或 "max" = 自动选设备支持的最高分辨率。
# 也可写成 (1280, 1024)。若填写的值设备不支持，会自动吸附到最接近的支持模式。
TARGET_RESOLUTION = "max"

# 相机帧率。None = 自动 (取该分辨率下满足 IMU 需求的最高帧率)。
TARGET_FPS = None

# IMU 目标频率 (Hz)。None = 自动 (使用传感器固有速率)。
# 注意: 本硬件 IMU 固定 200Hz 且不可编程，此项用于推导所需帧率并校验，
#       实际生效值 = min(硬件速率, fps × 每帧槽位数)，见下方说明。
TARGET_IMU_HZ = None

# 预览缩放 (1.0 = 原始大小)。1280x1024 双目并排为 2560x1024，通常需要缩小。
DISPLAY_SCALE = 0.45

# 灰度世界白平衡。Bayer 原图未做白平衡时偏绿，开启后观感正常。
ENABLE_AWB = True

# 左右图 Bayer 相位互换。若预览颜色明显不对 (红蓝翻转) 就把它改成 True。
SWAP_BAYER_PHASE = False

# ============================================================================
# 以下为 SDK 常量与实现，一般不需要修改
# ============================================================================

# --- src/usb/uvc/smartsens_metadata.h ---------------------------------------
META_IMU_BASE_COL = 5           # kMetaImuBaseCol
IMU_WORDS_PER_SAMPLE = 9        # kImuWordsPerSample
IMU_SLOTS_LEGACY = 7            # 固件 2/3, 2/4
IMU_SLOTS_V5 = 13               # 固件 2/5

# --- src/usb/uvc/cyperstereo_api.h (BMI088) ---------------------------------
BMI088_ACCEL_SEN = 0.00018310546875     # ±6g   -> 单位 g
BMI088_GYRO_SEN = 0.0010652644178602    # ±2000dps -> 单位 rad/s

# IMU 传感器固有采样率。SDK 未提供修改接口，实测时间戳步长恒为 5ms。
IMU_NATIVE_HZ = 200.0

# --- CameraProfile 表 (cyperstereo_api.h:372-446)，用作枚举失败时的兜底 ------
#   frame_width, frame_height, fps, num_cameras, 是否彩色(Bayer)
FALLBACK_PROFILES = [
    (2560, 1024, 30, 4, True),    # SmartSens (Cyper-ego)
    (1280, 1024, 30, 2, True),    # SmartSens (Cyper-duo)
    (752, 480, 60, 2, False),     # MT9V034 (M150 / M60)
]

CYPER_VID, CYPER_PID = 0x04B4, 0x00F9


# ============================================================================
# V4L2 能力枚举 (ioctl)，用于真正地"按设备支持情况"自动匹配
# ============================================================================

def _ioc(direction, type_char, nr, size):
    return (direction << 30) | (size << 16) | (ord(type_char) << 8) | nr


_IOC_WRITE, _IOC_READ = 1, 2
VIDIOC_QUERYCAP = _ioc(_IOC_READ, 'V', 0, 104)
VIDIOC_ENUM_FRAMESIZES = _ioc(_IOC_READ | _IOC_WRITE, 'V', 74, 44)
VIDIOC_ENUM_FRAMEINTERVALS = _ioc(_IOC_READ | _IOC_WRITE, 'V', 75, 52)

V4L2_CAP_VIDEO_CAPTURE = 0x00000001
FOURCC_YUYV = cv2.VideoWriter_fourcc(*'YUYV')


def _fourcc_u32(s):
    return ord(s[0]) | (ord(s[1]) << 8) | (ord(s[2]) << 16) | (ord(s[3]) << 24)


def enum_frame_sizes(path, pixfmt=_fourcc_u32('YUYV')):
    """返回 [(width, height), ...]，仅离散尺寸。"""
    sizes = []
    try:
        fd = os.open(path, os.O_RDWR | os.O_NONBLOCK)
    except OSError:
        return sizes
    try:
        for index in range(64):
            vals = np.zeros(11, dtype=np.uint32)   # struct v4l2_frmsizeenum
            vals[0] = index
            vals[1] = pixfmt
            buf = bytearray(vals.tobytes())
            try:
                fcntl.ioctl(fd, VIDIOC_ENUM_FRAMESIZES, buf)
            except OSError:
                break
            out = np.frombuffer(bytes(buf), dtype=np.uint32)
            if out[2] != 1:          # 只处理 V4L2_FRMSIZE_TYPE_DISCRETE
                break
            sizes.append((int(out[3]), int(out[4])))
    finally:
        os.close(fd)
    return sizes


def enum_frame_rates(path, width, height, pixfmt=_fourcc_u32('YUYV')):
    """返回该分辨率下支持的 fps 列表 (降序)。"""
    rates = []
    try:
        fd = os.open(path, os.O_RDWR | os.O_NONBLOCK)
    except OSError:
        return rates
    try:
        for index in range(64):
            vals = np.zeros(13, dtype=np.uint32)
            vals[0] = index
            vals[1] = pixfmt
            vals[2] = width
            vals[3] = height
            buf = bytearray(vals.tobytes())
            try:
                fcntl.ioctl(fd, VIDIOC_ENUM_FRAMEINTERVALS, buf)
            except OSError:
                break
            out = np.frombuffer(bytes(buf), dtype=np.uint32)
            if out[4] != 1:          # V4L2_FRMIVAL_TYPE_DISCRETE
                break
            numerator, denominator = int(out[5]), int(out[6])
            if numerator:
                rates.append(denominator / numerator)
    finally:
        os.close(fd)
    return sorted(rates, reverse=True)


def is_capture_device(path):
    """区分图像采集节点与 UVC metadata 节点 (本设备两者都会出现)。"""
    try:
        fd = os.open(path, os.O_RDWR | os.O_NONBLOCK)
    except OSError:
        return False
    try:
        buf = bytearray(104)
        fcntl.ioctl(fd, VIDIOC_QUERYCAP, buf)
        device_caps = int(np.frombuffer(bytes(buf[92:96]), dtype=np.uint32)[0])
        caps = int(np.frombuffer(bytes(buf[88:92]), dtype=np.uint32)[0])
        effective = device_caps if device_caps else caps
        return bool(effective & V4L2_CAP_VIDEO_CAPTURE)
    except OSError:
        return False
    finally:
        os.close(fd)


def find_camera():
    """找到 Cyperstereo 的图像采集节点，返回 (path, index)。"""
    candidates = []
    for path in sorted(glob.glob('/dev/video*'),
                       key=lambda p: int(''.join(filter(str.isdigit, p)) or 0)):
        name = os.path.basename(path)
        modalias = f'/sys/class/video4linux/{name}/device/modalias'
        is_cyper = False
        try:
            with open(modalias) as handle:
                alias = handle.read()
            is_cyper = (f'V{CYPER_VID:04X}P{CYPER_PID:04X}' in alias.upper())
        except OSError:
            pass
        if not is_capture_device(path):
            continue
        candidates.append((path, is_cyper))

    for path, is_cyper in candidates:
        if is_cyper:
            return path, int(''.join(filter(str.isdigit, os.path.basename(path))))
    if candidates:
        path = candidates[0][0]
        print(f'[warn] 未匹配到 {CYPER_VID:04x}:{CYPER_PID:04x}，回退到 {path}')
        return path, int(''.join(filter(str.isdigit, os.path.basename(path))))
    return None, None


# ============================================================================
# 参数自动匹配
# ============================================================================

class Config:
    """解析后的最终配置，附带每一项的决策理由。"""

    def __init__(self):
        self.width = self.height = self.fps = 0
        self.cam_width = 0        # 单目宽度: 交织发生在字节通道上，不是像素上，
                                  # 所以 = frame_width * 2 / num_cameras
        self.num_cameras = 2
        self.is_color = True
        self.imu_slots = IMU_SLOTS_LEGACY
        self.imu_hz = IMU_NATIVE_HZ
        self.notes = []


def resolve_config(path):
    """把用户配置吸附到设备真实支持的模式上。

    匹配规则:
      R1 分辨率 -> 吸附到设备枚举出的离散尺寸 (max 则取像素最多的)
      R2 帧率   -> 吸附到该分辨率支持的帧率
      R3 IMU 挂在图像帧的 metadata 行上，每帧固定槽位数 (7 或 13)。
         因此可承载的 IMU 速率上限 = fps × 槽位数，
         实际 IMU 速率 = min(传感器固有 200Hz, fps × 槽位数)。
         若用户指定了 IMU 频率而未指定 fps，则反推 fps >= imu_hz / 槽位数。
    """
    cfg = Config()

    sizes = enum_frame_sizes(path)
    if not sizes:
        sizes = [(w, h) for w, h, _, _, _ in FALLBACK_PROFILES]
        cfg.notes.append('V4L2 尺寸枚举失败，使用 SDK CameraProfile 兜底表')

    # ---- R1 分辨率 ---------------------------------------------------------
    if TARGET_RESOLUTION in (None, 'max', 'MAX'):
        cfg.width, cfg.height = max(sizes, key=lambda s: s[0] * s[1])
        cfg.notes.append(f'分辨率: 自动取最高 {cfg.width}x{cfg.height}')
    else:
        want_w, want_h = TARGET_RESOLUTION
        cfg.width, cfg.height = min(
            sizes, key=lambda s: abs(s[0] * s[1] - want_w * want_h))
        if (cfg.width, cfg.height) != (want_w, want_h):
            cfg.notes.append(
                f'分辨率: 设备不支持 {want_w}x{want_h}，'
                f'已吸附到 {cfg.width}x{cfg.height} '
                f'(支持: {", ".join(f"{w}x{h}" for w, h in sizes)})')
        else:
            cfg.notes.append(f'分辨率: {cfg.width}x{cfg.height} (设备原生支持)')

    # ---- 由帧宽推断相机数与是否彩色 ---------------------------------------
    for w, h, _, cams, color in FALLBACK_PROFILES:
        if (w, h) == (cfg.width, cfg.height):
            cfg.num_cameras, cfg.is_color = cams, color
            break
    else:
        cfg.num_cameras, cfg.is_color = 2, True
        cfg.notes.append('未知帧尺寸，按 2 目彩色处理')
    cfg.cam_width = cfg.width * 2 // cfg.num_cameras

    # ---- R2 帧率 -----------------------------------------------------------
    rates = enum_frame_rates(path, cfg.width, cfg.height)
    if not rates:
        rates = [float(f) for w, h, f, _, _ in FALLBACK_PROFILES
                 if (w, h) == (cfg.width, cfg.height)] or [30.0]
        cfg.notes.append('V4L2 帧率枚举失败，使用 CameraProfile 兜底帧率')

    # IMU 槽位数需读到 metadata 才能确定固件版本，这里先按 legacy 估算，
    # 首帧拿到 hw/sw 后会在 update_from_metadata() 里回填并复核。
    slots = cfg.imu_slots

    if TARGET_FPS is not None:
        cfg.fps = min(rates, key=lambda r: abs(r - TARGET_FPS))
        if abs(cfg.fps - TARGET_FPS) > 0.01:
            cfg.notes.append(
                f'帧率: 设备不支持 {TARGET_FPS}fps，已吸附到 {cfg.fps:g}fps '
                f'(支持: {", ".join(f"{r:g}" for r in rates)})')
        else:
            cfg.notes.append(f'帧率: {cfg.fps:g}fps (设备原生支持)')
    elif TARGET_IMU_HZ is not None:
        # 先按硬件固有速率封顶，否则会用一个达不到的 IMU 速率去反推帧率。
        want = min(TARGET_IMU_HZ, IMU_NATIVE_HZ)
        need = want / slots
        ok = [r for r in rates if r >= need - 1e-6]
        cfg.fps = min(ok) if ok else max(rates)
        cfg.notes.append(
            f'帧率: 自动 -> 由 IMU {want:g}Hz 反推需要 >= {need:.1f}fps，'
            f'选择 {cfg.fps:g}fps'
            + ('' if ok else ' (设备最高帧率仍不足，IMU 会丢样)'))
    else:
        cfg.fps = max(rates)
        cfg.notes.append(f'帧率: 自动取最高 {cfg.fps:g}fps')

    cfg.imu_hz = _match_imu(cfg, slots)
    return cfg


def _match_imu(cfg, slots):
    """R3: 计算实际可达的 IMU 速率，并在被帧率限制时给出提示。"""
    capacity = cfg.fps * slots
    want = TARGET_IMU_HZ if TARGET_IMU_HZ is not None else IMU_NATIVE_HZ
    effective = min(want, IMU_NATIVE_HZ, capacity)

    if want > IMU_NATIVE_HZ:
        cfg.notes.append(
            f'IMU: 请求 {want:g}Hz 超过传感器固有 {IMU_NATIVE_HZ:g}Hz '
            f'(不可编程)，按 {IMU_NATIVE_HZ:g}Hz 处理')
    if capacity < min(want, IMU_NATIVE_HZ) - 1e-6:
        cfg.notes.append(
            f'IMU: 警告 — {cfg.fps:g}fps × {slots} 槽/帧 = {capacity:.0f}Hz '
            f'承载能力不足，IMU 将丢样，实际约 {effective:.0f}Hz。'
            f'需要 >= {min(want, IMU_NATIVE_HZ) / slots:.1f}fps 才能跑满')
    else:
        cfg.notes.append(
            f'IMU: {effective:.0f}Hz (承载上限 {cfg.fps:g}fps × {slots} = '
            f'{capacity:.0f}Hz，充足)')
    return effective


def update_from_metadata(cfg, hardware_version, software_version):
    """首帧读到固件版本后，回填真实槽位数并复核 IMU 匹配。"""
    slots = (IMU_SLOTS_V5 if (hardware_version == 2 and software_version == 5)
             else IMU_SLOTS_LEGACY)
    if slots == cfg.imu_slots:
        return False
    cfg.imu_slots = slots
    cfg.notes.append(
        f'固件 {hardware_version}/{software_version} -> 每帧 {slots} 个 IMU 槽位')
    cfg.imu_hz = _match_imu(cfg, slots)
    return True


# ============================================================================
# 帧解析
# ============================================================================

def deinterleave(frame, num_cameras):
    """UVC 帧的字节通道即各相机的 Bayer 平面。

    2 目: lo 通道 = C1 = 右图, hi 通道 = C2 = 左图 (smartsens_metadata.h 的
          DeinterleaveTwoPlanes 说明了这个 lane 反转)。
    4 目: DQ 通道顺序为 C1,C2,C4,C3。
    返回按显示顺序排列的平面列表。
    """
    height = frame.shape[0]
    flat = frame.reshape(height, -1)
    if num_cameras >= 4:
        lanes = [np.ascontiguousarray(flat[:, i::4]) for i in range(4)]
        return lanes                       # 显示序即 C1,C2,C4,C3
    lo = np.ascontiguousarray(flat[:, 0::2])
    hi = np.ascontiguousarray(flat[:, 1::2])
    return [hi, lo]                        # [左(C2), 右(C1)]


def demosaic(planes, is_color, hardware_version, software_version):
    """按 bayer_format.h 的 SelectBayerConversion 选择相位。

    固件 2/4 与 2/5 对 C1/C4 做了 mirror+flip，红蓝相位相反。2 目时显示平面 0
    读到的是 C2(未镜像) -> RG，平面 1 读到的是 C1(镜像) -> BG。
    """
    if not is_color:
        return [cv2.cvtColor(p, cv2.COLOR_GRAY2BGR) for p in planes]

    mirrored = (hardware_version == 2 and software_version in (4, 5))
    out = []
    for i, plane in enumerate(planes):
        if len(planes) >= 4:
            flip = mirrored and i in (0, 2)
        else:
            flip = mirrored and i == 1
        if SWAP_BAYER_PHASE:
            flip = not flip
        code = cv2.COLOR_BayerBG2BGR if flip else cv2.COLOR_BayerRG2BGR
        out.append(cv2.cvtColor(plane, code))
    return out


def gray_world_awb(image):
    """便宜的灰度世界白平衡，只为预览观感，不改变原始数据。"""
    small = cv2.resize(image, (160, 128), interpolation=cv2.INTER_NEAREST)
    means = small.reshape(-1, 3).mean(axis=0)
    if means.min() < 1.0:
        return image
    gains = means.mean() / means
    lut = np.clip(np.arange(256)[:, None] * gains[None, :], 0, 255).astype(np.uint8)
    return cv2.merge([lut[:, c][image[:, :, c]] for c in range(3)])


def parse_imu(frame, slots):
    """从末行 metadata 解析 IMU。16bit 字 = (hi << 8) | lo。

    返回 (hw, sw, samples)，samples 为 dict 列表。零填充的空槽会被跳过 ——
    200Hz IMU 除以 30fps 得 6.67 样/帧，所以第 7 个槽经常是空的。
    """
    row = frame[-1]
    words = (row[:, 1].astype(np.uint16) << 8) | row[:, 0].astype(np.uint16)
    signed = words.astype(np.int32)
    signed[signed > 32767] -= 65536

    hardware_version, software_version = int(words[0]), int(words[1])

    samples = []
    for i in range(slots):
        base = META_IMU_BASE_COL + i * IMU_WORDS_PER_SAMPLE
        if base + IMU_WORDS_PER_SAMPLE > words.size:
            break
        sub, sec = int(words[base]), int(words[base + 1])
        if sub == 0 and sec == 0:
            continue                       # 未使用的槽位
        temperature = int(signed[base + 8])
        if temperature > 1023:
            temperature -= 2048
        samples.append({
            't': sec + sub / 10000.0,
            'acc': (signed[base + 2] * BMI088_ACCEL_SEN,
                    signed[base + 3] * BMI088_ACCEL_SEN,
                    signed[base + 4] * BMI088_ACCEL_SEN),
            'gyro': (signed[base + 5] * BMI088_GYRO_SEN,
                     signed[base + 6] * BMI088_GYRO_SEN,
                     signed[base + 7] * BMI088_GYRO_SEN),
            'temp': temperature * 0.125 + 23.0,
        })
    return hardware_version, software_version, samples


# ============================================================================
# 主流程
# ============================================================================

def open_capture(index, cfg):
    cap = cv2.VideoCapture(index, cv2.CAP_V4L2)
    if not cap.isOpened():
        return None
    # 顺序重要: 先关掉 OpenCV 的自动 RGB 转换，才能拿到原始交织字节。
    cap.set(cv2.CAP_PROP_FOURCC, FOURCC_YUYV)
    cap.set(cv2.CAP_PROP_CONVERT_RGB, 0)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, cfg.width)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, cfg.height)
    cap.set(cv2.CAP_PROP_FPS, cfg.fps)
    if cap.get(cv2.CAP_PROP_CONVERT_RGB) != 0:
        print('[warn] 无法关闭 CONVERT_RGB，画面可能已被 OpenCV 转换过')
    return cap


def main():
    parser = argparse.ArgumentParser(description='Cyperstereo 双目 + IMU 预览')
    parser.add_argument('--no-gui', action='store_true', help='不开预览窗口')
    parser.add_argument('--device', help='指定设备节点，如 /dev/video1')
    args = parser.parse_args()

    if args.device:
        path = args.device
        index = int(''.join(filter(str.isdigit, os.path.basename(path))))
    else:
        path, index = find_camera()
    if path is None:
        print('[error] 未找到相机采集节点，请确认模组已连接 (lsusb 应有 04b4:00f9)')
        return 1

    cfg = resolve_config(path)

    print('=' * 68)
    print(f'设备      : {path}')
    print(f'分辨率    : UVC 帧 {cfg.width}x{cfg.height} -> 单目 '
          f'{cfg.cam_width}x{cfg.height - 1}, {cfg.num_cameras} 目, '
          f'{"彩色" if cfg.is_color else "单色"}')
    print(f'帧率      : {cfg.fps:g} fps')
    print(f'IMU       : {cfg.imu_hz:.0f} Hz')
    print('-' * 68)
    for note in cfg.notes:
        print(f'  · {note}')
    print('=' * 68)

    cap = open_capture(index, cfg)
    if cap is None:
        print(f'[error] 打开 {path} 失败 (是否被其他程序占用?)')
        return 1

    show = not args.no_gui and bool(os.environ.get('DISPLAY'))
    if not args.no_gui and not show:
        print('[warn] 无 DISPLAY，转为无窗口模式')

    window = 'Cyperstereo  |  q=退出  s=保存'
    if show:
        cv2.namedWindow(window, cv2.WINDOW_NORMAL)

    frames = 0
    imu_total = 0
    hardware_version = software_version = 0
    metadata_checked = False
    last_imu_t = None
    imu_dt_sum, imu_dt_n = 0.0, 0
    t_start = time.time()
    t_report = t_start

    try:
        while True:
            ok, frame = cap.read()
            if not ok or frame is None:
                print('[warn] 读帧失败，重试中...')
                time.sleep(0.05)
                continue
            if frame.ndim == 2:
                frame = frame.reshape(cfg.height, cfg.width, 2)
            frames += 1

            hardware_version, software_version, samples = parse_imu(
                frame, cfg.imu_slots)

            if not metadata_checked:
                metadata_checked = True
                if update_from_metadata(cfg, hardware_version, software_version):
                    print('[auto] 依据固件版本重新匹配:')
                    for note in cfg.notes[-2:]:
                        print(f'  · {note}')

            imu_total += len(samples)
            for sample in samples:
                if last_imu_t is not None:
                    dt = sample['t'] - last_imu_t
                    if 0 < dt < 1.0:
                        imu_dt_sum += dt
                        imu_dt_n += 1
                last_imu_t = sample['t']

            planes = deinterleave(frame, cfg.num_cameras)
            images = demosaic(planes, cfg.is_color,
                              hardware_version, software_version)
            # 末行是 metadata，不是图像，显示时裁掉。
            images = [img[:-1] for img in images]
            if ENABLE_AWB and cfg.is_color:
                images = [gray_world_awb(img) for img in images]

            now = time.time()
            if now - t_report >= 1.0:
                fps_measured = frames / (now - t_start)
                imu_measured = (1.0 / (imu_dt_sum / imu_dt_n)) if imu_dt_n else 0.0
                line = (f'\r帧 {frames:6d} | 实测 {fps_measured:5.1f} fps | '
                        f'IMU {imu_measured:6.1f} Hz ({len(samples)} 样/帧) | '
                        f'固件 {hardware_version}/{software_version}')
                if samples:
                    acc = samples[-1]['acc']
                    gyro = samples[-1]['gyro']
                    line += (f' | acc({acc[0]:+.2f},{acc[1]:+.2f},{acc[2]:+.2f})g'
                             f' gyr({gyro[0]:+.2f},{gyro[1]:+.2f},{gyro[2]:+.2f})'
                             f' {samples[-1]["temp"]:.1f}C')
                sys.stdout.write(line + '   ')
                sys.stdout.flush()
                t_report = now

            if show:
                canvas = np.hstack(images)
                if DISPLAY_SCALE != 1.0:
                    canvas = cv2.resize(canvas, None, fx=DISPLAY_SCALE,
                                        fy=DISPLAY_SCALE,
                                        interpolation=cv2.INTER_AREA)
                labels = (['cam1', 'cam2', 'cam3', 'cam4']
                          if cfg.num_cameras >= 4 else ['left', 'right'])
                step = canvas.shape[1] // len(images)
                for i, label in enumerate(labels[:len(images)]):
                    cv2.putText(canvas, label, (12 + i * step, 26),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.7,
                                (0, 255, 0), 2, cv2.LINE_AA)
                cv2.imshow(window, canvas)
                key = cv2.waitKey(1) & 0xFF
                if key in (ord('q'), 27):
                    break
                if key == ord('s'):
                    stamp = time.strftime('%Y%m%d_%H%M%S')
                    for i, img in enumerate(images):
                        name = f'cam{i + 1}_{stamp}.png'
                        cv2.imwrite(name, img)
                    print(f'\n[save] 已保存 {len(images)} 张 -> *_{stamp}.png')
    except KeyboardInterrupt:
        pass
    finally:
        cap.release()
        if show:
            cv2.destroyAllWindows()

    elapsed = time.time() - t_start
    print(f'\n共 {frames} 帧 / {elapsed:.1f}s '
          f'= {frames / max(elapsed, 1e-6):.1f} fps，IMU 样本 {imu_total} 个 '
          f'({imu_total / max(elapsed, 1e-6):.1f} Hz)')
    return 0


if __name__ == '__main__':
    sys.exit(main())
