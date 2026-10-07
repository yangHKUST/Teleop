# 相机驱动提取包

本目录是从 `UMI_to_arm` 项目及其上游仓库 `CyperstereoSDK` 中提取出的**相机驱动相关文件**，供单独迁移/复用。

相机硬件：**Cyperstereo 双目 + IMU（BMI088）VIO 相机**（UVC 设备，VID:PID `04B4:00F9`）。
完整链路：`Cyperstereo UVC 驱动 → 采集/ISP → ORB-SLAM3(cyperstereo_online) → ZMQ 位姿/图像 → 遥操消费端`。

## 目录结构

```
camera_driver/
├── README.md                    本说明
├── project/                     本项目内的相机接口与启动脚本（消费端）
│   ├── arm/mujoco_sim/piper_vio_teleop.py   订阅 VIO 位姿(ZMQ) + 拉起/回收相机进程 + 手眼标定
│   ├── arm/mujoco_sim/dual_stereo_viewer.py 订阅相机左右眼图像(ZMQ) + OpenCV 合并显示
│   ├── arm/mujoco_sim/run_vio_teleop.sh     单臂遥操启动 wrapper
│   ├── run_all.sh               拼 VIO_CMD 并一键启动
│   └── run_dual.sh              双臂：注入相机序列号/端口环境变量
└── cyperstereo/                 上游仓库的相机驱动本体
    ├── camera.py                Python 版 UVC 驱动（V4L2 打开 + Bayer 去交织 + IMU metadata 解析 + 预览）
    ├── src/                     相机 SDK 源码
    │   ├── usb/uvc/             UVC/V4L2 驱动核心（cyperstereo.h / uvc.h / uvc-v4l2.cc / fast_isp.cc 等）
    │   └── ISP/                 ISP 图像信号处理源码（去 Bayer、白平衡、去噪等模块）
    ├── samples/                 采集样例（capture_image_imu.cc / save_image_imu.cc，已剔除 build）
    ├── scripts/                 相机驱动安装/配置脚本（x86 Linux / OrangePi / RK3588 ISP）
    ├── orbslam3/                ORB-SLAM3-Cyperstereo 完整源码（SLAM 算法核心 + 相机驱动入口）
    │   ├── Examples/            cyperstereo_online.cc / _offline.cc / _isp_stub.cc
    │   ├── src/  include/       ORB-SLAM3 算法核心源码与头文件
    │   ├── Thirdparty/          DBoW2 / g2o / Sophus / usb（相机 SDK 副本，含 linux/uvc-v4l2.cc）
    │   ├── Vocabulary/ORBvoc.txt  词袋（运行时必需）
    │   └── CMakeLists.txt / build.sh / run_cyperstereo.md / Dependencies.md / generate_cyperstereo_yaml.py
    └── calib/                   相机标定配置
        ├── orbslam3_yaml/       ORB-SLAM3 各相机标定 yaml + 生成脚本（slam/config/orbslam3/）
        ├── s200032/             #1 相机 kalibr 标定结果（不含 PDF 报告）
        ├── s200002/             #2 相机 kalibr 标定结果（不含 PDF 报告）
        └── s200002_1/           #2 相机新标定结果
```

## 来源（原始路径）

| 提取后 | 原始位置 |
|---|---|
| `project/*` | `~/Teleop/UMI_to_arm/` 对应路径 |
| `cyperstereo/camera.py` | `~/CyperstereoSDK/camera.py` |
| `cyperstereo/src/` | `~/CyperstereoSDK/src/` |
| `cyperstereo/samples/` | `~/CyperstereoSDK/samples/`（剔除 build/） |
| `cyperstereo/scripts/` | `~/CyperstereoSDK/scripts/` |
| `cyperstereo/orbslam3/` | `~/CyperstereoSDK/ORB_SLAM3-Cyperstereo/`（Examples、src、include、Thirdparty、Vocabulary、CMakeLists 等，完整源码） |
| `cyperstereo/calib/orbslam3_yaml/` | `~/CyperstereoSDK/slam/config/orbslam3/` |
| `cyperstereo/calib/s200xxx/` | `~/CyperstereoSDK/s200xxx/`（剔除 *.pdf） |

## 未纳入的文件（需时从原仓库取）

以下为**编译产物 / 冗余大体积资产**，未复制（可从源码或原仓库重建/取回）：

| 文件 | 原位置 | 体积 | 说明 |
|---|---|---|---|
| `cyperstereo_online` / `cyperstereo_offline` 二进制 | `ORB_SLAM3-Cyperstereo/build/` | ~5MB×2 | 编译产物，可从已含源码重建 |
| `evaluation/` | `ORB_SLAM3-Cyperstereo/evaluation/` | 51MB | 评测工具与数据，与相机驱动无关 |
| `Examples_old/` | `ORB_SLAM3-Cyperstereo/Examples_old/` | 674MB | 旧版示例，与 Cyperstereo 在线驱动无关 |
| `ORBvoc.txt.tar.gz` | `ORB_SLAM3-Cyperstereo/Vocabulary/` | 42MB | 词袋压缩包，与已含的 `ORBvoc.txt` 重复 |
| `cyperstereo_calib-report-*.pdf` | `s200032/`、`s200002/` | ~15-18MB×4 | kalibr 标定可视化报告 |
| `.git` | 各处 | — | 版本历史 |

## 关键文件速览

- **Linux 相机驱动核心**：`cyperstereo/src/usb/uvc/linux/uvc-v4l2.cc`（V4L2 打开 UVC、取帧）、`cyperstereo/src/usb/uvc/cyperstereo.h` / `cyperstereo_api.h`（相机配置/枚举/IMU 解析）、`smartsens_metadata.h`（末行 metadata 中 IMU 解析常量）。
- **Python 驱动**：`cyperstereo/camera.py`（不依赖 SDK 绑定，纯 V4L2 打开相机，复刻 SDK 的 Bayer 去交织 + IMU 解析流程）。
- **在线驱动入口**：`cyperstereo/orbslam3/Examples/cyperstereo_online.cc`（打开相机 → 送 ORB-SLAM3 → ZMQ PUB 位姿/图像）。
- **消费端**：`project/arm/mujoco_sim/piper_vio_teleop.py`（`VioZMQSource` 订阅位姿）、`project/arm/mujoco_sim/dual_stereo_viewer.py`（订阅图像）。

## 说明

- 本机平台为 Linux，实际使用的是 `linux/uvc-v4l2.cc`（V4L2 后端）。`src/usb/uvc/{win,macosx}/` 为跨平台后端（WMF / VVUVCKit）及 macOS 演示工程，一并保留以保持 SDK 完整，与本机运行无关。
- 如需重建 `cyperstereo_online`，直接进入 `cyperstereo/orbslam3/` 按 `build.sh` 编译即可（源码、Thirdparty 依赖与 `Vocabulary/ORBvoc.txt` 均已包含）。
