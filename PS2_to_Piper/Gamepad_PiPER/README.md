# PS2 手柄遥操作松灵 PiPER 机械臂

用 USB 游戏手柄控制松灵（AgileX）PiPER 六轴机械臂及夹爪，支持逐关节控制和末端位姿控制。可以先在电脑上操作虚拟机械臂，再连接真机开展遥操作、演示和实验。

本文按第一次使用的顺序编写。**主线使用 Python 3.11 + Pinocchio，不需要安装 ROS，也不需要 NVIDIA 显卡。** 完成虚拟练习后再进行真机部署。

> 本文对应本目录当前代码。`run_real.py`、`run_mujoco.sh`、`main_mujoco.py`、`src/mujoco_viewer.py` 和 `ros_packages/` 是当前工作副本里的配套文件；分发项目时请一起打包。仅克隆上游仓库未必包含这些文件，应先核对目录。

## 目录

- [1. 准备设备和软件](#1-准备设备和软件)
- [2. 获取项目并安装环境](#2-获取项目并安装环境)
- [3. 检查手柄及按键映射](#3-检查手柄及按键映射)
- [4. 先操作虚拟机械臂](#4-先操作虚拟机械臂)
- [5. 连接和启动真机](#5-连接和启动真机)
| BACK / START / HOME | button 6 / 7 / 8 |
| L3 / R3（摇杆按下） | button 9 / 10，目前没有控制动作 |
| 左摇杆左右 / 上下 | axis 0 / 1 |
| 右摇杆左右 / 上下 | axis 3 / 4 |
| LT / RT | axis 2 / 5 |
- [6. 手柄操作速查](#6-手柄操作速查)
- [7. 结束实验与再次启动](#7-结束实验与再次启动)
- [8. 常见问题](#8-常见问题)
- [9. 项目结构与进阶开发](#9-项目结构与进阶开发)

## 1. 准备设备和软件

| 项目 | 虚拟练习 | 真机实验 | 说明 |
| --- | --- | --- | --- |
| Ubuntu 电脑 | 必需 | 必需 | 建议使用有桌面环境的 Ubuntu 22.04/24.04；其他发行版需自行适配 |
| Miniconda 或 Anaconda | 必需 | 必需 | 本文用 Conda 隔离 Python 依赖 |
| PS2 风格手柄及 USB 接收器/转换器 | 必需 | 必需 | 必须能被电脑识别为游戏手柄；不同型号的按键编号可能不同 |
| PiPER 机械臂及配套电源 | 无需 | 必需 | 固定在稳定台面上，按
| BACK / START / HOME | button 6 / 7 / 8 |
| L3 / R3（摇杆按下） | button 9 / 10，目前没有控制动作 |
| 左摇杆左右 / 上下 | axis 0 / 1 |
| 右摇杆左右 / 上下 | axis 3 / 4 |
| LT / RT | axis 2 / 5 |设备手册接线、上电 |
| 支持 Linux SocketCAN 的 USB-CAN 模块及线缆 | 无需 | 必需 | 优先用机械臂配套模块；本项目默认接口名 `can0`，速率 1 Mbps |
| PiPER 电动夹爪 | 可看虚拟夹爪 | 使用夹爪功能时需要 | 当前代码会发送夹爪指令，其他末端工具需适配 |

“PS2 手柄”是外观或型号描述，不能保证 USB 输出格式一致。传统 PS2 接口不能直接插电脑，需兼容的 USB 转换器。程序使用 pygame 读取游戏手柄，预设映射接近 Xbox 布局；请务必完成第 3 节测试。

首次使用请先完成环境检查和虚拟操作验证，再连接真机。真机首测前，清空机械臂、夹爪和回零路径周围的物品，提前确认硬件急停或设备规定的紧急停止方式。

**当前程序的操作边界：**

- 连接使能真机时会立即发出六关节回零指令，夹爪随后会接收当前开合指令（启动默认 0%，即关闭）。
- 默认底层速度是 **100%**，并非初次操作所需的低速；应在连接前按第 5 节调低。
- 手柄掉线没有自动失能/急停逻辑，主循环可能继续发送最后的目标；松开摇杆只停止增加目标，不能取消机械臂尚未完成的动作。
- 可视化显示的是程序目标，不能当作真机反馈或障碍物检测。MuJoCo 窗口在这里用于运动学显示，不是动力学仿真。

## 2. 获取项目并安装环境

下面的命令在 Ubuntu 的“终端”中执行（通常按 `Ctrl+Alt+T` 打开）。复制代码块中的命令即可，不要复制终端提示符。遇到 `sudo` 密码提示时输入电脑登录密码，输入过程中不显示字符是正常现象。

### 2.1 找到项目目录

如果已经获取了整个项目文件夹，直接进入包含 `main.py` 的目录。本工作区的命令为：

```bash
cd /home/taoqiu/Teleop/PS2_to_Piper/Gamepad_PiPER
ls
```

换电脑时把路径换成自己的实际位置。若从上游获取基础项目：

```bash
sudo apt update
sudo apt install -y git iproute2 can-utils
mkdir -p ~/Teleop
cd ~/Teleop
git clone https://github.com/kehuanjack/Gamepad_PiPER.git
cd Gamepad_PiPER
```

成功标志：`ls` 能看到 `main.py`、`main_virtual.py`、`requirements_common.txt`、`src/` 和 `piper/`。还应核对开头列出的配套文件。后续除特别说明外，都在这个目录执行。

### 2.2 安装 Conda（已有则跳过）

```bash
conda --version
```

若提示 `command not found`，按 [Conda 官方 Linux 安装说明](https://docs.conda.io/projects/conda/en/stable/user-guide/install/linux.html
| BACK / START / HOME | button 6 / 7 / 8 |
| L3 / R3（摇杆按下） | button 9 / 10，目前没有控制动作 |
| 左摇杆左右 / 上下 | axis 0 / 1 |
| 右摇杆左右 / 上下 | axis 3 / 4 |
| LT / RT | axis 2 / 5 |) 安装适合电脑架构的 Miniconda。本文的快捷启动脚本假定安装目录是 `~/miniconda3`，环境名是 `piper`；安装在其他目录也可用，按下文的手动启动方法运行。

安装并初始化 Bash 后，关闭终端再重新打开，确认 `conda --version` 能输出版本。

### 2.3 创建环境并安装依赖

```bash
conda create -n piper python=3.11 -y
conda install -n piper -c conda-forge pinocchio=3.6.0 casadi -y
conda activate piper
python -m pip install scipy viser yourdfpy 'pygame<2.6.2' piper_sdk 'setuptools<80.9.0' mujoco
```

首次安装需联网，耗时取决于网络。不要用 `sudo pip`，也不要同时安装四套运动学库。

这里没有直接使用 `requirements_common.txt`：该文件包含 `numpy<=1.26.0` 的旧约束，而当前本机 Pinocchio 环境使用 NumPy 2.x。主线采用上面的安装命令，避免覆盖 Conda 已求解的依赖。MuJoCo 也没有包含在该通用依赖文件中，需要单独安装。

本机检查到的版本（供复现和排查参考，并不代表其他组合均已验证）：

| Python | Pinocchio | CasADi | NumPy | pygame | piper_sdk | MuJoCo |
| --- | --- | --- | --- | --- | --- | --- |
| 3.11.15 | 3.6.0 | 3.7.2 | 2.4.6 | 2.6.1 | 0.6.2 | 3.13.0 |

本项目使用 `piper_sdk.C_PiperInterface_V2`。真机固件与 SDK 的兼容性请查阅 [PiPER SDK 官方说明](https://github.com/agilexrobotics/piper_sdk/blob/master/README(ZH).MD)，不要仅因存在新 SDK 就替换接口。

### 2.4 设置模型路径并检查环境

URDF 是描述机械臂关节和几何模型的文件；STL 是外观网格。项目已附带
| BACK / START / HOME | button 6 / 7 / 8 |
| L3 / R3（摇杆按下） | button 9 / 10，目前没有控制动作 |
| 左摇杆左右 / 上下 | axis 0 / 1 |
| 右摇杆左右 / 上下 | axis 3 / 4 |
| LT / RT | axis 2 / 5 |它们，不必额外安装 `piper_ros`。

```bash
mkdir -p ros_packages/piper_description
```

若下面命令列出了 STL 文件，就无需重建链接：

```bash
ls ros_packages/piper_description/meshes/
```

若提示路径不存在，执行：

```bash
ln -s ../../piper/meshes ros_packages/piper_description/meshes
```

| BACK / START / HOME | button 6 / 7 / 8 |
| L3 / R3（摇杆按下） | button 9 / 10，目前没有控制动作 |
| 左摇杆左右 / 上下 | axis 0 / 1 |
| 右摇杆左右 / 上下 | axis 3 / 4 |
| LT / RT | axis 2 / 5 |
新终端中先激活环境，再清除可能由 ROS 带入的 Python/库路径，并设置本项目模型路径：

```bash
conda activate piper
unset PYTHONPATH LD_LIBRARY_PATH
export ROS_PACKAGE_PATH="$PWD/ros_packages"
python -c "import sys, pinocchio, casadi, mujoco, pygame, viser, yourdfpy; from pinocchio import casadi as cpin; from piper_sdk import C_PiperInterface_V2; print('Python:', sys.executable); print('依赖导入成功')"
python -c "from src.kinematic_pin import Arm_IK; import numpy as np; ik = Arm_IK('piper/piper.urdf'); print('关节数:', ik.model.nq); print('零位末端位姿:', ik.get_fk(np.zeros(ik.model.nq)))"
```

成功标志：Python 路径包含 `envs/piper`，输出“依赖导入成功”，关节数为 `6`，并打印六个末端位姿数值。这些检查不会连接或使能真机。若报错，先看第 8 节。

> 这里只清理当前终端的环境变量，不修改系统 ROS 安装。需要运行 ROS 时，另开终端。

## 3. 检查手柄及按键映射

1. 先插入手柄配套的 USB 接收器，打开手柄下方电源（从右往左拨动），完成配对（当左上角POWER对应的指示灯亮红即是配对成功）。指示灯含义和 MODE/ANALOG 键用途以手柄说明为准。
2. **不要运行真机程序。** 在已激活 `piper` 的终端中运行以下测试，一次只操作一个按钮或摇杆，记下编号；`Ctrl+C` 退出。

```bash
python - <<'PY'
import pygame
pygame.init()
pygame.joystick.init()
if pygame.joystick.get_count() == 0:
    raise SystemExit('未检测到手柄：检查接收器、电源和配对后重试')
j = pygame.joystick.Joystick(0)
j.init()
print('名称:', j.get_name())
| BACK / START / HOME | button 6 / 7 / 8 |
| L3 / R3（摇杆按下） | button 9 / 10，目前没有控制动作 |
| 左摇杆左右 / 上下 | axis 0 / 1 |
| 右摇杆左右 / 上下 | axis 3 / 4 |
| LT / RT | axis 2 / 5 |
print('按钮数:', j.get_numbuttons(), '轴数:', j.get_numaxes(), '方向键组数:', j.get_numhats())
print('依次按键、移动摇杆和扳机；Ctrl+C 退出')
try:
    while True:
        for e in pygame.event.get():
            if e.type in (pygame.JOYBUTTONDOWN, pygame.JOYBUTTONUP):
                print('button', e.button, '按下' if e.type == pygame.JOYBUTTONDOWN else '松开')
            elif e.type == pygame.JOYAXISMOTION:
                print('axis', e.axis, round(e.value, 2))
            elif e.type == pygame.JOYHATMOTION:
                print('hat', e.hat, e.value)
        pygame.time.wait(20)
except KeyboardInterrupt:
    pass
finally:
    pygame.quit()
PY
```

当前 Ubuntu 分支的预设映射位于 [`src/gamepad_base.py`](src/gamepad_base.py) 的 `_setup_platform_mappings()`：

| 逻辑名称 | pygame 编号 |
| --- | --- |
| A / B / X / Y | button 0 / 1 / 2 / 3 |
| LB / RB | button 4 / 5 |
| BACK / START / HOME | button 6 / 7 / 8 |
| L3 / R3（摇杆按下） | button 9 / 10，目前没有控制动作 |
| 左摇杆左右 / 上下 | axis 0 / 1 |
| 右摇杆左右 / 上下 | axis 3 / 4 |
| LT / RT | axis 2 / 5 |
| 十字方向键 | hat 0 |

**PS2 面板上的叉、圆、方、三角或 MODE 不一定对应 A、B、X、Y、HOME。** 以测试得到的编号为准；只有 MODE 实际输出 button 8 时，它才具有本程序的 HOME 功能。START 不是连接开关。

若编号不同，根据测试结果修改 Ubuntu 分支（`else` 内）的 `button_map`、`axis_map`、`hat_map`，再在虚拟机械臂中验证。当前代码的长按检测还会直接读取 A/X/START/LB/RB 编号，按钮数量不足可能产生读取错误，不能只忽略缺失按钮。

扳机预设原始值是松开 `-1`、按到底 `+1`；程序会转换为 0～1。若手柄 L2/R2 仅输出按钮，或松开值是 `0`，需要修改扳机读取逻辑，不能直接用于真机。只连接一只手柄，避免输入设备被切换。

## 4. 先操作虚拟机械臂

虚拟模式不需要机械臂、CAN 模块或 `sudo`。完成第 2 节环境设置后，选择一个入口：

配套电源 → PiPER
```
```bash
# 原生窗口（需要桌面和可用的 OpenGL）
python main_mujoco.py
```

```bash
# 网页窗口
python main_virtual.py
```

网页模式打开 [http://localhost:8080](http://localhost:8080)，若端口被占用，以终端实际打印的地址为准。网页只显示模型，手柄仍要插在运行 Python 的电脑上；pygame 初始化通常也需要可用的显示环境，不能保证在无桌面的服务器上直接运行。

验收步骤：

1. 确认终端 `Joystick status: Connected`，模型窗口/网页正常显示。程序刚启动时 `Robot arm status: Disconnected/Disabled` 是正常的。
2. 短按映射为 **HOME** 的按钮，终端应变为 `Connected/Enabled`。虚拟模式的“连接”只是在软件中启用操作。
3. 默认 `up_level_mode: joint`、`low_level_mode: joint`。轻推左摇杆，确认 J1/J2 和模型有响应，再逐一验证右摇杆和十字键。
4. 长按 LB 两次，把 `Speed factor` 从 `x1.0` 降到 `x0.25`。每次按住至少 0.3 秒后松开，确认数值变化。
5. 短按 START，把 `up_level_mode` 切成 `pose`，体验末端移动；初学者保持 `low_level_mode: joint`。
6. 测试 LT/RT，确认松开时夹爪不会持续变化；按 Y 验证回零。按第 6 节练习保存和恢复位置。
7. 用终端 `Ctrl+C` 退出。仅关闭模型窗口不一定会结束主程序。

若当前副本没有 `main_mujoco.py`，可以先用 `main_virtual.py` 完成网页练习。不要跳过手柄和虚拟验收直接连接真机。

### 可选：现有快捷脚本

在 `~/miniconda3` 下已有 `piper` 环境时：

```bash
CONDA_PREFIX="$HOME/miniconda3" bash run_mujoco.sh
```

脚本会清理 ROS 路径并设置模型目录。这里显式指定 Conda 根目录，是因为
配套电源 → PiPER
```脚本会把 `CONDA_PREFIX` 后接 `/envs/piper`；直接在已激活的 `piper` 环境里运行 `./run_mujoco.sh` 可能错误地查找 `envs/piper/envs/piper/bin/python`。

## 5. 连接和启动真机

### 5.1 接线与 CAN 检查

先停止所有虚拟/真机控制程序，按设备手册接线：

```text
PS2 手柄 → USB 接收器/转换器 → Ubuntu 电脑
Ubuntu 电脑 → USB-CAN 模块 → CAN 线 → PiPER
配套电源 → PiPER
```

CAN-H、CAN-L、接地、终端电阻和供电接法以机械臂及模块手册为准，不凭线色猜测。固定机械臂、清空运动区域后，按设备要求上电并检查急停状态。

```bash
sudo apt update
sudo apt install -y iproute2 can-utils
ip -brief link
```

应看到 `can0`。若仅看到 `/dev/ttyUSB*` 或没有 CAN 接口，当前模块可能需要专用驱动/固件或串口 CAN 配置；`ip link` 命令不会自动把任意 USB-CAN 变成 SocketCAN。先按供应商文档配置。

确认 `can0` 是这台机械臂的接口，并且没有其他程序使用它，再配置：

```bash
sudo ip link set can0 down
sudo ip link set can0 type can bitrate 1000000
sudo ip link set can0 up
ip -details -statistics link show can0
candump can0
```

成功标志：接口为 `UP`、`bitrate 1000000`，通常 CAN 状态为 `ERROR-ACTIVE`，且上电机械臂能产生接收帧（`candump` 显示不断出现的数据）。`ERROR-ACTIVE` 是正常 CAN 状态名称。用 `Ctrl+C` 结束 `candump`，它不会使能机械臂。

无接收帧时，先检查电源、接线、速率和模块，不要尝试靠反复按 HOME 解决。若接口是 `can1`，需要同时修改 `main.py` 的 SDK 初始化接口参数和启动入口的 CAN 命令；当前代码没有命令行接口选择选项。接口参数用法见 [官方 SDK](https://github.com/agilexrobotics/piper_sdk/blob/master/README(ZH).MD)。

### 5.2 启动程序，但先不要连接使能

在项目目录、完成环境设置的终端中：

```bash
python main.py
```

该入口也会尝试激活 `can0`，可能要求 `sudo` 密码；**不要用 `sudo python main.py`**。确认可视化正常，终端的手柄状态是 `Connected`，机械臂状态仍为 `Disconnected/Disabled`。

默认 Miniconda 安装路径也可以用：

```bash
python run_real.py
```

`run_real.py` 会自动切换到 `~/miniconda3/envs/piper/bin/python`、清理 ROS 路径并尝试激活 CAN。它固定使用这个路径；Anaconda/其他安装位置请用上面的 `python main.py` 手动入口。若 CAN 激活失败，它只打印警告并继续，必须自己确认 CAN 检查已通过。

### 5.3 调低速度，再使能

1. **保持机械臂未连接状态，不触碰 HOME。** 长按 LB 两次，将 `Speed factor` 调为 `x0.25`。
2. 长按 RB 九次，将 `Movement speed` 从 `100%` 调为 `10%`；每次松开后查看终端。速度列表会循环，降到 10% 后再长按会跳回 100%。
3. 确认 `up_level_mode: joint`、`low_level_mode: joint`、`Command mode: 0x00`。检查机械臂回零路线及夹爪内没有障碍物。
4. 短按 **HOME**：程序连接 CAN、等待使能，然后立即发出回零命令；此时不要推动摇杆，观察实际机械臂，等它完成动作。
5. 终端应显示 `Connected/Enabled`。轻推一个摇杆后松开，确认真实关节与目标方向一致，逐关节测试，再测试小范围夹爪开合。
6. 关节模式稳定后才尝试短按 START 进入上层 `pose`。初学实验保持底层 `joint` 和命令模式 `0x00`，不要尝试长按 START 或 BACK 切换。

使能等待没有超时。若 HOME 后一直无响应，停止尝试并排查 CAN、供电、急停和固件兼容性；不要反复按键。

## 6. 手柄操作速查

这里的按键名称是**程序逻辑名称**，具体对应哪个实体按钮取决于第 3 节映射。对支持长按的键，短按/长按动作在**松开时**执行，长按阈值是 **0.3 秒**。

| 按键 | 短按 | 长按 |
| --- | --- | --- |
| HOME | 连接并使能 / 回零后执行停止、复位流程，清除连接状态 | 无独立长按功能 |
| START | 切换上层 `joint` / `pose` | 切换底层 `joint` / `pose` |
| BACK | 切换命令模式 `0x00` / `0xAD`（已连接时） | 无独立长按功能 |
| Y | 六关节回零（已连接时） | 无独立长按功能 |
| A | 保存当前目标关节角和夹爪状态 | 删除当前索引对应的保存位置 |
| B | 恢复下一个回放位置（已连接时，每按一次一个点） | 无独立长按功能 |
| X | 切换回放方向 | 清空全部保存位置 |
| LB | 提高上层速度因子 | 降低上层速度因子 |
| RB | 提高底层运动速度百分比 | 降低底层运动速度百分比 |

**上层模式**决定如何把手柄输入转换成目标：`joint` 是逐关节增量，`pose` 是通过逆运动学求末端目标对应的关节角。**底层模式**决定发给机械臂的是关节指令还是末端位姿指令。上层 `pose` 配合底层 `joint` 已能实现末端遥操，不必同时切换两层。

| 输入 | 上层关节模式 | 上层位姿模式（当前末端局部坐标系） |
| --- | --- | --- |
| 左摇杆左右 | J1 | Y 方向平移 |
| 左摇杆上下 | J2 | X 方向平移 |
| 右摇杆上下 | J3 | Z 方向平移 |
| 右摇杆左右 | J6 | 绕 Z 旋转 |
| 十字键左右 | J4 | 绕 X 旋转 |
| 十字键上下 | J5 | 绕 Y 旋转 |
| LT | 关闭夹爪 | 关闭夹爪 |
| RT | 打开夹爪 | 打开夹爪 |

局部坐标系会随末端方向旋转，同一摇杆方向不一定始终对应桌面上的同一方向。正负方向以虚拟测试为准。Pinocchio 默认末端参考位于第六关节处，不等同于夹爪指尖或自定义工具中心。

速度因子列表为 `0.25 / 0.5 / 1 / 2 / 3 / 4 / 5`，底层速度为 `10%～100%`，两者独立且都循环切换。原始关节步长为每次更新 `0.05°`，平移步长 `1 mm`，旋转步长 `0.5°`，再乘输入量和速度因子；它们不是每秒速度，实际更新频率会受计算和打印耗时影响。

### 夹爪和位置记忆

- 夹爪状态范围为 `0%～100%`，代码配置最大开口 `0.07 m`。夹爪在 0% 时，LT 释放后再次按下可能跳到 100%；在 100% 时，RT 释放后再次按下可能跳到 0%。端点重复按扳机可能突然反向，不要用手测试。
- A 保存的是程序的**目标**，不是读取到的真机位置，且只存在内存中，退出程序就丢失。项目没有自动生成轨迹文件或采集数据文件的功能。
- 依次保存 P1、P2、P3 后，默认 `Reverse`，按 B 会回放 P2、P1、P3，循环执行；按 X 切为 `Sequence` 后按索引递增回放。每次只恢复一个目标点，途中是否有障碍物要自行检查。
- `0xAD` 是进阶命令模式。切回 `0x00` 的代码会调用回零/停止/复位及重新使能流程，可能产生动作；首次使用时保持默认命令模式。

## 7. 结束实验与再次启动

### 虚拟模式

在运行程序的终端按 `Ctrl+C`。重新启动后保存位置、速度及连接状态都会恢复初始值。

### 真机模式

正常收尾时先松开手柄，将物品取下，并清空回零路径。**`Ctrl+C` 不是急停**：已连接使能时，它会持续发送回零指令，最多等待约 10 秒，再发送约 1 秒保持指令后退出，意图保持使能；若未连接则直接退出。

即使回零超时，程序仍会退出。退出后的实际姿态、使能状态和能否持续保持，应检查真机并按设备手册确认，不能只根据终端“锁定”提示判断。程序退出不等于断电。

HOME 再次按下也不是急停：它先发回零、关闭夹爪，再等待并发送停止/复位命令，软件状态变为未连接。此过程可能失去保持力，不能当作安全下电保证。最终停机、支撑和切断电源按设备手册执行。

发生失控、碰撞风险或手柄掉线时，优先使用设备规定的硬件紧急停止方式；不要等待回零或用关闭窗口代替急停。

下次使用：进入项目目录 → `conda activate piper` → 清理路径并设置 `ROS_PACKAGE_PATH`（第 2.4 节）→ 插好手柄 → 检查 CAN（真机）→ 启动 → 调低两个速度 → 确认路径 → HOME 连接。每次重启默认底层速度又是 100%。

## 8. 常见问题

| 现象 | 检查与处理 |
| --- | --- |
| `conda: command not found` | 完成 Conda 安装/初始化后重开终端；查看第 2.2 节 |
| `ModuleNotFoundError` | 检查 `python -c "import sys; print(sys.executable)"` 是否在 `envs/piper`，在该环境重装缺失依赖 |
| `pinocchio_pywrap_default` 导入失败或加载 ROS 版本 | 在当前终端 `unset PYTHONPATH LD_LIBRARY_PATH` 后重试；不要混用系统 Python 和 Conda Python |
| 找不到 `piper_description/meshes` 或 STL | 确认在项目目录，执行第 2.4 节链接和 `ROS_PACKAGE_PATH` 设置；复制项目时保留符号链接 |
| `run_real.py` 提示 Python 文件不存在 | 它固定使用 `~/miniconda3/envs/piper/bin/python`；改用激活环境后的 `python main.py` |
| `run_mujoco.sh` 查找路径中出现两次 `envs/piper` | 使用第 4 节显式指定 `CONDA_PREFIX` 的命令，或直接 `python main_mujoco.py` |
| 手柄状态 `Disconnected` | 先用第 3 节独立检查，确认配对；启动后重新插入接收器，等待设备加入事件；仍失败则重启程序 |
| 按键错位、右摇杆不动、夹爪自己变化 | 核对编号和扳机松开值；只在虚拟模式修改映射并验证，不能直接真机试错 |
| 手柄已连接但模型不动 | 软件状态是否 `Connected/Enabled`？需要 HOME；START 只切换模式 |
| 模型不显示或 OpenGL/GLFW 报错 | 用本地桌面终端，确认显卡驱动和显示环境；可尝试网页入口，检查浏览器地址及子进程报错 |
| 网页无法打开 | 查看终端实际端口；本机用 `localhost`，不要将它理解为另一台电脑地址；不要只关闭网页来结束程序 |
| `Cannot find device can0` | 用 `ip -brief link` 核对接口；确认模块支持 SocketCAN、驱动/固件已配置及接口名正确 |
| `Device or resource busy` / 修改 CAN 速率失败 | 停止其他控制程序后按第 5.1 节先 down 再配置；运行中的接口不能直接改速率 |
| CAN 为 `BUS-OFF` 或无接收帧 | 检查线缆、终端电阻、速率、供电，修复后重新激活；不要仅反复重启程序 |
| HOME 后程序一直等待，真机不动 | 使能循环没有超时；检查 CAN 数据、硬件急停、供电及 SDK/固件兼容性 |
| 位姿模式无响应或 IK 收敛报错 | 目标可能不可达或碰到自碰撞约束；降低速度，切回关节模式移离边界，先在虚拟环境复现 |
| 末端接近边界时关节跳动 | 逆运动学可能切换解；降低速度、避开奇异姿态，不能把模型约束当成完整避障 |
| 退出后仍保持通电，或实际没到零位 | 查看第 7 节；正常退出只尝试回零并保持使能，不能替代设备停机流程 |

向项目维护者反馈问题时，提供：启动命令、Python 路径、依赖版本、手柄名称/编号、CAN 状态、完整错误文本，以及是否在虚拟模式也能复现。不要只提供终端被刷新后的最后一行。

## 9. 项目结构与进阶开发
解压缩后会消耗 33.7 MB 的额外空间。
获取:1 http://mirror.sysu.edu.cn/ubuntu/ jammy/universe amd64 gh amd64 2.4.0+dfsg1-2 [6,242 kB]
已下载 6,242 kB，耗时 2秒 (3,366 kB/s)
正在选中未选择的软件包 gh。
(正在读取数据库 ... 系统当前共安装有 345716 个文件和目录。)
准备解压 .../gh_2.4.0+dfsg1-2_amd64.deb  ...
正在解压 gh (2.4.0+dfsg1-2) ...
正在设置 gh (2.4.0+dfsg1-2) ...
正在处理用于 man-db (2.10.2-1) 的触发器 ...
? What account do you want to log into? GitHub.com
? What is your preferred protocol for Git operations? HTTPS
? Authenticate Git with your GitHub credentials? Yes
? How would you like to authenticate GitHub CLI? Login with a web browser

! First copy your one-time code: 45EC-7B8B
- Press Enter to open github.com in your browser... 
Gtk-Message: 18:34:01.329: Not loading module "atk-bridge": The functionality is provided by GTK natively. Please try to not load it.

```text
Gamepad_PiPER/
├── README.md                 # 中文部署和操作教程（本文）
├── README(EN).md             # 英文说明，可能与当前副本功能不同步
├── requirements_common.txt  # 原通用依赖清单，含旧 NumPy 约束
├── main.py                  # 真机入口，默认 Pinocchio + MuJoCo
├── run_real.py              # 真机环境引导，固定 Miniconda Python 路径
├── main_virtual.py          # 虚拟机械臂，viser 网页显示
├── main_mujoco.py           # 虚拟机械臂，MuJoCo 原生显示
├── run_mujoco.sh            # MuJoCo 环境引导脚本
├── piper/
│   ├── piper.urdf           # 机械臂模型、关节限制
│   └── meshes/              # STL 网格
├── ros_packages/piper_description/meshes -> ../../piper/meshes
└── src/
    ├── gamepad_base.py      # 手柄映射、速度、记忆位置、公共显示逻辑
    ├── gamepad_pin.py       # 默认 Pinocchio 控制器
    ├── kinematic_pin.py     # 正/逆运动学，部分自碰撞检查
    ├── mujoco_viewer.py     # URDF 转换与运动学显示
    ├── gamepad_*.py         # 其他运动学后端的控制器
    └── kinematic_*.py       # 其他运动学后端实现
```

按本文完成部署和操作无需理解这些文件的内部实现。进阶实验可阅读以下后端，但应分别建立环境、按各自官方说明安装，先进行虚拟验证：

| 后端 | 控制器 | 参考 |
| --- | --- | --- |
| Pinocchio + CasADi（当前默认） | `src.gamepad_pin` | [Pinocchio](https://github.com/stack-of-tasks/pinocchio) |
| PyRoKi（带/不带额外约束的实现） | `src.gamepad_limit` / `src.gamepad_no_limit` | [PyRoKi](https://github.com/chungmin99/pyroki)，代码原说明引用提交 `f234516` |
| TRAC-IK Python 封装 | `src.gamepad_trac_ik` | [pytracik](https://github.com/chenhaox/pytracik) |
| cuRobo | `src.gamepad_curobo` | [cuRobo](https://github.com/NVlabs/curobo)，需要适配 CUDA/PyTorch 环境 |

切换后端需修改实际启动入口的 `RoboticArmController` 导入，不是安装库后自动切换；`main.py`、`main_virtual.py` 和 `main_mujoco.py` 是三个不同入口。更换后端后还需重新确认坐标、单位、关节限制和运动连续性。

当前 Pinocchio 上层 FK/IK 的姿态使用弧度，而真机底层 `pose` 分支将 `xyz_rpy` 直接乘 1000 发送，存在与 SDK 角度单位不一致的风险。该分支需要进一步核对并修正后再用于真机；这是本文保持底层 `joint` 的原因。

完成部署验证后，可记录环境供同一平台复现：

```bash
conda env export -n piper > environment-local.yml
conda activate piper
python -m pip freeze > requirements-local.txt
```

保存电脑系统、机械臂固件、手柄映射和实验步骤记录。项目许可证见 [LICENSE](LICENSE)。
