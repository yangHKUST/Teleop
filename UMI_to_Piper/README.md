# UMI_to_arm —— 手持夹爪（DM3507）→ 松灵 Piper 机械臂 遥操

## 摘要

本项目实现「手持夹爪 → 机械臂」的遥操闭环：手持夹爪（达妙 DM3507 电机）的 VIO 六自由度位姿（ORB-SLAM3-Cyperstereo 经 ZMQ PUB `tcp://127.0.0.1:5555` 发布）被增量式映射到松灵 Piper 机械臂末端，同时把手持夹爪开度按百分比映射到机械臂 AGX 夹爪，并以 MuJoCo 数字孪生同步显示。目的是提供一套非 ROS 的日常遥操链路，支持真机 CAN 直驱与纯仿真两种模式。意义在于用低成本手持装置即可采集/演示机械臂运动轨迹，且对 VIO 位姿漂移一阶免疫，是机器人示教与数据采集的实用工具。本目录是自包含副本（结构与原仓库 `CyperstereoSDK/` 一致，相对路径无需改动）。

## 硬件准备

- **手持夹爪**：达妙 DM3507 电机（CAN id 默认 7，勿与 master id 17 混淆）。
- **VIO 相机**：ORB-SLAM3-Cyperstereo（双目/惯性，序列号默认 `s200032`），用于发布手持夹爪 6DoF 位姿。
- **机械臂本体**：松灵 Piper 六轴机械臂 + AGX 夹爪（可选）。
- **手持夹爪 CAN 链路**：CANable2 / SLCAN 设备，串口默认 `/dev/ttyACM0`（读 DM3507 编码器）。
- **真机 CAN 链路**：CANable / USB-CAN 适配器，接口 `can0`（真机模式）。
- **控制电脑**：MuJoCo 窗口需图形环境；夹爪桥接需 ROS2 humble 工作区。

> 三种运行模式所需硬件不同：全量（真机 + 夹爪 + VIO）、`--sim-only`（仅 VIO + 仿真，真机不动）、`--synthetic`（无相机/夹爪/真机，脚本化位姿冒烟）。

## 环境配置

### 遥操主链（conda env：`piper_pinocchio`）

- Python 包：`numpy`、`mujoco`、`pinocchio`、`imufusion`（imu-fusion）、`python-can`、`pyzmq`（ZMQ 订阅）
- 真机另需：`piper_sdk`（pip 版，CAN 直驱）、CANable2 设备
- 启动**必须** `unset PYTHONPATH`（避免 `/opt/ros/humble` 下损坏的 pinocchio 盖住 conda-forge 版），`run_vio_teleop.sh` / `run_all.sh` 已内置该步骤。

### 手持夹爪 ROS2 桥接（独立工作区，需 `/usr/bin/python3` + humble）

`gripper/` 是独立轻量 colcon 包（`gripper_teleop`），含达妙 DM3507 的 CANable2/SLCAN 纯 Python 驱动。以符号链接纳入 `~/CyperstereoSDK/ros2/src/gripper_teleop`，编译：

```bash
cd ~/CyperstereoSDK/ros2
source /opt/ros/humble/setup.bash
colcon build --packages-select gripper_teleop   # 不要加 --symlink-install（setuptools 83 与 colcon 不兼容）
source install/setup.bash
```

> ⚠️ 本机 setuptools 83 与 colcon-core 0.20.1 不兼容，`--symlink-install` 会报 `error: option --editable not recognized`，ament_python 包需用普通 install 构建。

## 启动流程

### 一键启动（单终端，推荐）

```bash
cd ~/Teleop/UMI_to_arm
./run_all.sh                     # 全量：ORB-SLAM3 + 仿真 + 真机 + 夹爪（分阶段流程）
./run_all.sh --sim-only          # 只仿真：真机不动，仿真臂+仿真夹爪(跟随手持)正常遥操
./run_all.sh --no-calibrate      # 跳过 Z/X 标定（R_BW=单位阵）
./run_all.sh --synthetic --no-viewer --steps 300   # 离线冒烟（不接硬件）
```

`run_all.sh` 依次：① 后台启动夹爪 ROS2 链（`gripper_bringup`）→ ② 前台跑遥操 `--staged`，分阶段流程为 **回准备姿态 → 启动 VIO 并提示完成初始化 → 提示完成 Z/X 标定 → 回车开启遥操**。三种模式只需改一个参数：

| 模式 | 真机 | 夹爪 | VIO |
|---|---|---|---|
| （默认）全量 | `--can can0` 驱动 | ROS2 链经 `/control/joint_states` 驱动 AGX 夹爪，遥操 `--no-gripper` 避免串口冲突 | ORB-SLAM3 启动 |
| `--sim-only` | 无 `--can`，真机不动 | 遥操直读手持 `/dev/ttyACM0` → 仿真夹爪跟随 | ORB-SLAM3 启动 |
| `--synthetic` | 无 | 无 | 脚本化位姿（无相机） |

停止按 Ctrl-C：遥操自身回收 VIO 子进程，脚本 `trap` 回收夹爪链。环境变量可覆盖：`VIO_SN`（默认 s200032）、`CAN_IF`（默认 can0）、`GRIPPER_CHANNEL`（默认 /dev/ttyACM0）、`SIM_ONLY=1`（等价 `--sim-only`）。

> **依赖说明**：`run_all.sh` 中的 VIO（`ORB_SLAM3-Cyperstereo/build/cyperstereo_online`）与 ROS2 工作区（`ros2/install`）仍指向原仓库 `/home/taoqiu/CyperstereoSDK`，全量/仿真模式需保证该仓库存在。

### 手动多终端（等价）

```bash
# 先保证 ORB-SLAM3 Cyperstereo 在跑（发布 ZMQ 位姿），然后：
cd ~/Teleop/UMI_to_arm

./arm/mujoco_sim/run_vio_teleop.sh                        # VIO + MuJoCo（先标定 R_BW）
./arm/mujoco_sim/run_vio_teleop.sh --can can0             # + 真机（回准备姿态）
./arm/mujoco_sim/run_vio_teleop.sh --no-calibrate         # 跳过标定，R_BW=单位阵
./arm/mujoco_sim/run_vio_teleop.sh --synthetic --no-viewer --steps 300  # 离线冒烟
```

手持夹爪开合（ROS2 桥接，独立工作区）：

```bash
cd ~/CyperstereoSDK/ros2
source /opt/ros/humble/setup.bash
source install/setup.bash
ros2 launch gripper_teleop gripper_bringup.launch.py   # channel:=/dev/ttyACM0
```

## 控制说明

### 手持夹爪 → 机械臂末端映射

- **平动**：增量式。VIO 世界系逐帧位移 `Δ_t` 经 `R_BW` 转到 base 系，`delta_p = scale · gain · R_BW · Δ_t`，累加到目标位置。
- **转动**：增量式、局部系。`rv_f = R_CF · so3_log(Δ_R_local)` 映射到法兰系，roll→joint6、pitch→joint5（×`pitch_gain`），yaw **丢弃**（夹爪指向由臂摆向决定）。
- **夹爪开度**：手持 0~100% 按百分比映射到臂夹爪行程（与平动/转动无关）。

### 键盘快捷键（遥操过程中）

| 按键 | 功能 |
|---|---|
| `空格` | 离合：冻结/恢复跟随（冻结时不跟随、不累积增量） |
| `h` | 回准备姿态（复位目标并重锁参考） |
| `s` | 记录当前真机位姿为准备姿态（写入 `cartesian_ready_q.json`） |
| `esc` | 急停 |

### 启动标定 R_BW（world → base）

VIO 初始化后，机械臂保持 home 位姿不动，手持夹爪沿 base 系两个方向推动：**+Z（竖直向上）** 与 **+X（水平向前）**（左 = 上 × 前 自动导出）。每个轴：起点回车 → 平移 → 终点回车。`--no-calibrate` 可跳过（R_BW = 单位阵）。

### 关键可调参数（`piper_vio_teleop.py`，命令行可覆盖）

| 参数 | 默认 | 含义 |
|---|---|---|
| `--scale` | 0.51 | 平移缩放（world m → base m），越大跟随距离越远 |
| `--x-gain` / `--y-gain` / `--z-gain` | 1.5 / 1.0 / 1.5 | 分轴增益，最终倍率 = scale × gain |
| `--pitch-gain` | 3.0 | 腕部俯仰灵敏度 |
| `--trans-deadzone` | 0.005 | 平移死区（m） |
| `--rot-deadzone` | 0.001 | 滚转(roll)死区（rad，~0.057°，30Hz 下 ≈1.7°/s） |
| `--pitch-deadzone` | 0.0029 | 俯仰(pitch)死区（rad，~0.17°，30Hz 下 ≈5°/s） |
| `--max-angular` | 0.6 | 滚转(roll)平滑限速（rad/s，≈34°/s） |
| `--pitch-slew` | 0.45 | 俯仰平滑限速（rad/s，≈26°/s） |
| `--handeye-pitch-deg` | 20.0 | 相机→法兰手眼俯仰角 |
| `--gripper-motor-id` | 7 | 手持夹爪 DM3507 CAN id |
| `--gripper-channel` | /dev/ttyACM0 | 手持夹爪 CANable2 串口 |

## 常见问题

### 收不到 VIO 位姿（标定/遥操提示「没有收到 VIO 位姿」）
- **原因**：ORB-SLAM3 未启动或未完成初始化 / 未 tracking，或 ZMQ 端点不一致。
- **排查**：观察 ORB-SLAM3 窗口是否 tracking；确认端点 `tcp://127.0.0.1:5555`。
- **解决**：缓慢移动手持相机完成 VIO 初始化，待 tracking 后再回车进入标定/遥操。

### import 时 pinocchio 冲突（ROS humble）
- **现象**：`ModuleNotFoundError: pinocchio.pinocchio_pywrap_default` 或加载到 `/opt/ros/humble` 的 pinocchio。
- **原因**：`PYTHONPATH` 里 ROS-humble 损坏的 pinocchio 盖住 conda-forge 版。
- **解决**：使用 `run_vio_teleop.sh` / `run_all.sh` 启动（已 `unset PYTHONPATH`）；手动运行时先 `unset PYTHONPATH`。

### 手持夹爪不可用（`[warn] 手持夹爪不可用`）
- **原因**：CANable2/SLCAN 未接或串口不对，或电机 id 不符。
- **排查**：确认 `/dev/ttyACM0` 存在；确认 `--gripper-motor-id` 为 7。
- **解决**：检查串口连接与 id 后重连；纯仿真可用 `--no-gripper` 跳过夹爪跟随。

### 真机不动
- **原因**：CAN 未激活、机械臂未上电、未加 `--can`，或正处于准备姿态阶段。
- **排查**：`ip -details link show can0` 应为 `ERROR-ACTIVE`；确认已加 `--can can0`。
- **解决**：配好 CAN 并上电后重跑；观察 `[ready]` 阶段是否到位。

### 上下/前后/左右方向反了
- **原因**：标定方向推反或手眼安装方向差异。
- **解决**：用 `--flip-z`（上下反）、`--flip-yaw`（前后左右都反，180° yaw）、`--flip-y`（左右反）、`--flip-roll` / `--flip-pitch`（滚转/俯仰反）翻转对应轴；或重新标定。

### 标定失败（`+X 方向与 +Z 几乎平行`）
- **原因**：手持夹爪沿 +X 推动时带有明显上下分量，导致「前」与「上」接近共线。
- **解决**：水平向前推动（保持高度），重新标定。

### 末端抖 / 跟手迟钝
- **原因**：VIO 抖动或滤波参数不合适。
- **解决**：默认用 1€ 自适应滤波（`--filter one_euro`）；调 `--one-euro-min-cutoff`（越小越平滑）、`--one-euro-beta`（越大快速转动越跟手）；或调大 `--trans-deadzone` / `--rot-deadzone` / `--pitch-deadzone` 抑制抖动。

### 夹爪桥接编译报 `error: option --editable not recognized`
- **原因**：本机 setuptools 83 与 colcon-core 0.20.1 不兼容，`--symlink-install` 走 `develop --editable` 失败。
- **解决**：`colcon build --packages-select gripper_teleop` 时**不要加** `--symlink-install`。
