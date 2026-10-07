# VR 遥操 OpenArm：从部署到使用

本项目让操作者通过 VR 头显与左右手柄控制 **OpenArm v1.0 双臂机械臂**：你按住手柄侧面的握持键并移动手柄，机械臂就会跟随；食指扳机控制夹爪，X/A 键让对应手臂回到预设姿态。也可以先用假硬件，在屏幕里练习完整流程。

首次使用时，请按顺序完成：**准备环境 → 编译 → 安装 VR 服务 → 假硬件练习 → 连接 CAN → 真机操作**。仅做 VR 遥操，无需启动 MoveIt 或 B-spline 规划器。

> 本文按当前源码与开发机环境整理。ROS 版本为 Humble，开发机安装的 teleop-xr 为 1.3.5。新机器的完整安装和真机操作仍需现场验收；不要把已有 `build/`、`install/` 当成可跨机器运行的软件。

## 先看这里：怎样使用这份指南

如果你没有用过 Linux、终端或机器人软件，请从下面的“打开终端、粘贴命令”开始。暂时不需要理解程序内部原理，先完成每一步并核对结果。

| 你的情况 | 从哪里开始 |
|---|---|
| 一台尚未安装本项目的新电脑 | 从第 1 节准备设备，再依次完成第 2～5 节 |
| 电脑已经由他人配置好，但你第一次使用 | 按第 2.3 节末尾确认软件可用，再完成第 4 节网络检查和第 5 节练习 |
| 已经完成过部署和练习，今天再次使用 | 看第 10 节“以后每次使用时做什么” |
| 只想体验屏幕中的机械臂 | 完成第 2～5 节，不连接真机、不执行第 6～7 节 |

第一次部署需要联网下载软件。下载和编译期间请让电脑保持联网，不要关闭终端。本文以**已经安装 Ubuntu 22.04 桌面系统的电脑**为起点；如果电脑只有 Windows 或 macOS，需要先准备符合要求的 Ubuntu 电脑。以下命令不能直接复制到 Windows 的 PowerShell 中运行。

### 打开终端、粘贴命令

“终端”是输入文字命令来操作电脑的窗口。在 Ubuntu 桌面同时按 **Ctrl + Alt + T** 打开它。你会看到类似下面的一行：

```text
你的用户名@电脑名:~$
```

这行叫“提示符”，表示终端正在等你输入命令。用户名和电脑名因人而异，**不需要复制这行，也不用输入 `$`**。

1. 复制本文灰色代码框内的命令。
2. 切换到终端，按 **Ctrl + Shift + V** 粘贴（终端的粘贴键通常不是 Ctrl + V）。
3. 按 **Enter（回车）** 执行。
4. 等提示符重新出现，确认没有报错，再执行下一步。启动服务的命令会一直运行，此时不会重新出现提示符，这是正常的。

默认按命令的完整逻辑行逐条执行，不要一次粘贴整篇文档。代码行末尾的 `\` 表示“这条命令还没写完，继续下一行”；遇到这种命令，把相连的几行一起复制。后面的证书代码块含有 `if ... fi`，该块按说明整体复制。

| 看到的内容或按键 | 含义 / 怎么做 |
|---|---|
| `sudo` | 这一步要管理员权限；输入你登录 Ubuntu 的密码后回车 |
| 输入密码时没有星号、光标不移动 | 正常的保密行为，继续输入密码再回车 |
| `Do you want to continue? [Y/n]` | 若你正在执行本文安装步骤，输入 `y` 并回车继续 |
| 命令执行后没有任何文字，提示符又出现 | 很多命令成功时不输出文字，按本步骤的检查命令核对 |
| `Ctrl+C` | 按住 Ctrl 再按 C，停止当前运行的命令；不必键入这几个字符 |
| `#` 开头的代码行 | 解释性注释，复制也不会执行操作 |
| `No such file or directory` | 文件或目录不存在，先检查路径与上一安装步骤 |
| `command not found` | 命令不可用，先检查软件是否安装、环境是否加载 |

如果失败，**停在当前步骤**，不要继续执行依赖它的后续命令。记录你执行的命令和报错文字。终端复制文字使用 **Ctrl + Shift + C**；提供给维护者时保留完整错误，而不仅是最后一行。

### 路径、终端 A 和终端 B 是什么

- `~` 表示当前用户的主文件夹，例如 `/home/你的用户名`，不是需要修改的占位符。
- `~/Teleop/VR_to_Openarm` 是本文约定的项目文件夹。按这个位置放好文件，后面的路径就可以直接复制。
- `cd 文件夹路径` 表示切换到该文件夹；`pwd` 显示当前所在位置；`ls` 显示里面的文件。
- **终端 A**：运行主程序，启动后保持打开。
- **终端 B**：再按一次 Ctrl + Alt + T 打开的第二个终端，用来检查状态或输入控制命令。它不需要名字真的叫 B，两个窗口分清即可。
- 一个终端里加载的设置不会自动传给另一个终端，所以本文会在需要的地方重复写 `source ...`。它的意思是“让这个终端认识 ROS 和本项目”。

### 先认识几个常用名称

| 名称 | 本文中指什么 |
|---|---|
| ROS 2 Humble | 让机械臂相关程序交换数据的一套软件；Humble 是版本名 |
| 编译 | 把下载的源码转换为电脑可以使用的程序，首次安装时做 |
| 工作区 `ros2_ws` | 集中放置机器人源码、构建结果和安装结果的文件夹 |
| 虚拟环境 | 单独存放 VR 程序及其依赖的文件夹，避免和其他 Python 软件混在一起 |
| RViz | 显示机械臂三维模型的电脑窗口，用于观察姿态 |
| 假硬件 | 让软件中的机械臂模型动起来，不驱动真实电机 |
| IP 地址 | 电脑在局域网中的地址，头显用它找到电脑 |
| CAN / CAN-FD | 电脑与机械臂电机之间的通信方式，需要适配器和线缆 |
| 使能 | 允许某项功能工作；“桥接允许输出”和“电机通电保持位置”是两个不同状态 |

## 1. 准备什么

| 项目 | 要求 / 用途 |
|---|---|
| 控制电脑 | Ubuntu 22.04，ROS 2 Humble，系统 Python 3.10；以下命令使用 Bash |
| VR 设备 | 支持 WebXR 的头显与左右控制器，例如 Meta Quest；用头显浏览器访问电脑即可 |
| 网络 | 电脑和头显能互访的同一局域网；校园 Wi-Fi 的客户端隔离可能阻止连接 |
| 机械臂 | 已正确装配、供电和标定的 OpenArm v1.0 双臂，各 7 个臂关节和 1 个夹爪关节 |
| CAN 适配器 | Linux SocketCAN 支持的双通道 CAN-FD 设备；开发机使用 PEAK PCAN-USB Pro FD |
| 辅助人员 | 首次真机实验由一人操作 VR、另一人观察机械臂并负责物理停机 |

没有机械臂或 CAN 适配器也能完成第 2～5 节。普通电脑浏览器可用于检查网页能否打开，但不能替代双手柄 VR 控制验收。

真机使用前固定好底座，清空两臂运动范围，检查供电、接线和关节零位，确认现场停机方式。断电或电机不使能时手臂可能下落，停机前应有合适支撑。VR 跟随与 X/A 回位路径不能视为已经经过 MoveIt 碰撞规划的安全轨迹。

## 2. 获取项目与安装 ROS 环境（首次做一次）

### 2.1 放好完整源码

这一步的目标是：电脑里有 `~/Teleop/VR_to_Openarm/ros2_ws/src` 这个文件夹。

如果电脑已经有完整项目，先检查位置，**不要再覆盖原有文件**。如果没有，请从项目提供者获取完整项目压缩包或本项目仓库地址；只下载名字相似的上游项目，会缺少本项目的 VR 功能。

拿到压缩包后，可以用鼠标完成放置：

1. 在 Ubuntu 的“文件”应用中打开“主文件夹”（Home）。
2. 新建文件夹 `Teleop`，注意大小写。
3. 在下载的压缩包上单击右键，选择“提取”或“解压”。
4. 把解压后**直接包含 `README.md` 和 `ros2_ws` 的文件夹**放入 `Teleop`，将它命名为 `VR_to_Openarm`。不要多套一层同名文件夹。
5. 打开终端，执行下面两行检查：

```bash
cd ~/Teleop/VR_to_Openarm
ls
```

应能看到 `README.md` 和 `ros2_ws`。再检查：

```bash
ls ~/Teleop/VR_to_Openarm/ros2_ws/src
```

应能看到 `openarm_description`、`openarm_can`、`openarm_ros2` 等目录。如果提示目录不存在，先检查文件放在哪里，再继续。

下面是项目目录对照表。它是帮助你核对文件的示意，**不是需要输入终端的命令**：

```text
VR_to_Openarm/
├── README.md                       # 本指南
└── ros2_ws/
    ├── colcon.meta                 # pick_ik 的构建设置，保留此文件
    ├── src/
    │   ├── openarm_description/    # 机器人模型
    │   ├── openarm_can/            # CAN 底层通信与工具
    │   ├── bio_ik/                 # 可选规划功能所需的 IK 包
    │   ├── pick_ik/                # MoveIt 的单臂 IK 包
    │   └── openarm_ros2/
    │       ├── openarm_bringup/    # 硬件/假硬件和控制器启动
    │       ├── openarm_hardware/   # 真机接口与重力补偿
    │       ├── openarm_teleop_bridge/ # VR 一键启动与 ROS 桥接
    │       ├── openarm_bimanual_moveit_config/
    │       ├── openarm_bimanual_planner/
    │       ├── openarm_bimanual_planner_msgs/
    │       ├── openarm_umi_bridge/ # 其他输入桥接，不是 VR 必需步骤
    │       └── openarm_acm_tool/   # 碰撞矩阵辅助工具
    └── docs/advanced.md            # MoveIt、示教、规划与诊断参考
```

如果放在其他路径，后文所有 `~/Teleop/VR_to_Openarm` 都换成自己的路径。不要在 `src/` 内部执行整个工作区的编译。

### 2.2 安装 ROS 2 Humble

下面分为“检查系统”“配置软件下载来源”“安装软件”三步。已经安装 Humble 的电脑，先执行步骤 A；若检查通过且 `source /opt/ros/humble/setup.bash` 可用，可以跳过步骤 B，直接进行步骤 C。

**步骤 A：确认系统版本。** 打开终端，执行：

```bash
lsb_release -d
/usr/bin/python3 --version
```

应分别看到 `Ubuntu 22.04...` 和 `Python 3.10...`。如果是 Ubuntu 24.04、其他 Linux 或其他 Python 版本，不要直接套用这套部署命令。本文未提供更换操作系统的流程。

**步骤 B：告诉 Ubuntu 从哪里下载 ROS。** 以下命令用于 Ubuntu 22.04，不需要连接机械臂。

先安装基础工具并设置字符编码：

```bash
sudo apt update
sudo apt install locales curl software-properties-common
sudo locale-gen en_US en_US.UTF-8
sudo update-locale LC_ALL=en_US.UTF-8 LANG=en_US.UTF-8
export LANG=en_US.UTF-8
sudo add-apt-repository universe
```

若要求确认，按回车或输入 `y`，按屏幕提示继续。然后下载并安装 ROS 的软件源配置包：

```bash
curl -fL -o /tmp/openarm-ros2-apt-source.deb https://github.com/ros-infrastructure/ros-apt-source/releases/download/1.3.0/ros2-apt-source_1.3.0.jammy_all.deb
sudo dpkg -i /tmp/openarm-ros2-apt-source.deb
sudo apt update
```

这里的配置包来自 [ROS 官方软件源项目](https://github.com/ros-infrastructure/ros-apt-source)，使用其 [1.3.0 发布版本](https://github.com/ros-infrastructure/ros-apt-source/releases/tag/1.3.0)的 Ubuntu 22.04（jammy）安装包。`curl` 负责下载，`dpkg` 负责安装这个文件，`apt update` 更新可下载的软件列表。如果下载失败或提示软件源签名冲突，先停止并保留错误；不要继续，也不要重复添加不同的软件源。

**步骤 C：安装 ROS 和项目需要的软件。** 完整复制下面的安装命令；下载量可能较大，等待提示符重新出现后再继续：

```bash
sudo apt update
sudo apt install ros-humble-desktop ros-dev-tools \
  python3-colcon-common-extensions python3-rosdep python3-venv python3-pip \
  build-essential cmake git libfmt-dev can-utils iproute2 openssl \
  ros-humble-ros2-control ros-humble-ros2-controllers \
  ros-humble-moveit ros-humble-pinocchio \
  ros-humble-joint-state-publisher-gui ros-humble-cv-bridge
source /opt/ros/humble/setup.bash
```

安装结束后检查 ROS 是否能被当前终端找到：

```bash
printenv ROS_DISTRO
```

应显示 `humble`。如果没有显示，重新执行 `source /opt/ros/humble/setup.bash` 再检查。如果 source 提示文件不存在，说明 ROS 安装尚未成功。

接下来安装各机器人软件包需要的额外依赖。`rosdep` 是自动检查和安装这些依赖的工具。先逐条执行：

```bash
sudo rosdep init
rosdep update
cd ~/Teleop/VR_to_Openarm/ros2_ws
rosdep install --from-paths src --ignore-src --rosdistro humble -r -y
```

若提示 rosdep 已初始化，跳过 `sudo rosdep init`，继续 update。若 apt 找不到 `ros-humble-*`，先检查 ROS 软件源和 Ubuntu 版本。依赖安装失败时先处理具体错误，再继续编译。

### 2.3 编译工作区

这一步把源码变成可运行的软件。先关闭正在运行的本项目程序；新电脑第一次安装时没有程序需要关闭。

再按 Ctrl + Alt + T 打开新终端。暂时不要进入第 3 节的 VR 虚拟环境。如果提示符有 `(base)`，先 `conda deactivate`（必要时重复），执行 `which python3` 检查，应显示 `/usr/bin/python3`。如果你从未安装过 Conda，直接忽略这一项，不要为此安装 Conda。

```bash
source /opt/ros/humble/setup.bash
cd ~/Teleop/VR_to_Openarm/ros2_ws
colcon build --symlink-install --cmake-args -DBUILD_TESTING=OFF
source install/setup.bash
ros2 pkg prefix openarm_teleop_bridge
ros2 pkg prefix openarm_description
```

前两行准备编译环境，第三行 `colcon build ...` 开始编译。**等第三行运行完，再执行剩下三行。**

成功时，编译末尾会出现类似下面的汇总（包的数量可能不同）：

```text
Summary: ... packages finished
```

不应出现 `Failed <<< ...` 或 `... packages failed`。最后两条查询命令应输出类似下面的路径，其中用户名是你自己的：

```text
/home/你的用户名/Teleop/VR_to_Openarm/ros2_ws/install/openarm_teleop_bridge
/home/你的用户名/Teleop/VR_to_Openarm/ros2_ws/install/openarm_description
```

如果编译失败，查看输出中**第一个失败的软件包**及它前面的错误。不要因为生成了 `install` 文件夹就认为编译成功。首次编译时间取决于机器，不要因暂时没有输出就认定失败。如果电脑因内存不足导致编译进程被杀死，在同一工作区使用下面的完整命令重试：

```bash
colcon build --symlink-install --parallel-workers 1 --cmake-args -DBUILD_TESTING=OFF
```

它让包依次构建，通常更慢，但能降低同时编译造成的内存占用。

**每开一个用于 ROS 操作的新终端，都执行以下两行**，包括后文终端 B：

```bash
source /opt/ros/humble/setup.bash
source ~/Teleop/VR_to_Openarm/ros2_ws/install/setup.bash
```

`source` 的作用是让当前终端找到 ROS 命令和本项目的软件包。迁移到新路径或新机器后，在新的源码副本里重新编译；旧安装目录通常包含原机器的绝对路径。

## 3. 安装 VR 服务（首次做一次）

ROS 工作区包含桥接包，但 **teleop_xr 安装在独立 Python 虚拟环境，项目源码里没有包含它**。默认启动文件会寻找 `~/venv-teleop-xr/bin/python`。

### 3.1 创建独立环境并安装依赖

再打开一个新终端，执行下面的命令。前 3 行会创建并进入 `venv-teleop-xr` 文件夹对应的 Python 环境；以后带 `python -m pip` 的安装会使用这个环境。

按顺序执行，遇到最后有 `\` 的命令时一起复制相连的几行：

```bash
source /opt/ros/humble/setup.bash
/usr/bin/python3 -m venv --system-site-packages ~/venv-teleop-xr
source ~/venv-teleop-xr/bin/activate
python -m pip install --upgrade pip
python -m pip install 'teleop-xr==1.3.5'
python -m pip install 'jax>=0.6.2' jaxlie jaxls 'trimesh[easy]>=4.0.0' \
  'yourdfpy>=0.0.60' 'spatialmath-python>=1.1.15' \
  'gitpython>=3.1.46' 'xacro>=2.1.1' 'filelock>=3.20.3' 'viser>=1.0.21'
python -m pip install 'git+https://github.com/chungmin99/pyroki.git'
python -m pip install 'git+https://github.com/chungmin99/ballpark.git'
python -m pip check
python -c "import rclpy, teleop_xr, jax, pyroki, ballpark, jaxls; print('VR dependencies OK')"
```

成功时，最后一行会打印 `VR dependencies OK`。`python -m pip check` 在依赖没有冲突时通常显示 `No broken requirements found.`；如果出现冲突列表，先记录并解决，再启动 VR 服务。

进入环境后，提示符前通常会有 `(venv-teleop-xr)`。也可以执行 `which python`，应看到 `/home/你的用户名/venv-teleop-xr/bin/python`。若指向别处，重新执行 `source ~/venv-teleop-xr/bin/activate` 再安装。

这里不要求安装 CUDA。`--system-site-packages` 让虚拟环境能使用系统 ROS Python 包。按 [teleop_xr 上游安装说明](https://github.com/qrafty-ai/teleop_xr)，pyroki 和 ballpark 需要从 GitHub 安装，因此不要仅依靠 `pip install 'teleop-xr[ik]'`。

GitHub 安装的两个库没有在本项目锁定提交；若将来出现 API 不兼容，请从已验收机器保存安装版本与对应提交，避免直接升级。安装成功后保留环境清单：

```bash
python -m pip freeze > ~/venv-teleop-xr/requirements-installed.txt
```

**不要将此环境与 `~/venv-openarm-ik` 混用**：后者仅供可选的 B-spline 规划器使用，依赖 `numpy<2`；VR 的 JAX 依赖可能需要另一组 NumPy 版本。

完成上述安装与记录后，在这个终端执行下面的命令退出虚拟环境。它不会删除任何软件：

```bash
deactivate
```

后面的启动命令会自动使用 VR 环境中的 Python，**不需要每次手动 activate**。

### 3.2 处理 ROS 图像包与 NumPy 的兼容问题

开发机对 teleop_xr 的 `ros2/__main__.py` 做了兼容修改：将包围 `from cv_bridge import CvBridge` 的 `except ImportError:` 改为 `except (ImportError, AttributeError):`。这样在 NumPy ABI 不匹配时，VR 位姿输入仍能启动，但 ROS 压缩图像解码不可用。

这一步只修改第三方 VR 软件中的一处兼容处理，不修改机械臂控制参数。可以用 Ubuntu 自带的文字编辑器完成：

1. 在终端执行下面命令，它会输出一个完整文件路径：

```bash
~/venv-teleop-xr/bin/python -c \
  "import pathlib, teleop_xr; print(pathlib.Path(teleop_xr.__file__).parent / 'ros2' / '__main__.py')"
```

2. 复制输出的路径。在“文件”应用按 **Ctrl + L**，粘贴路径并回车；用“文本编辑器”打开文件。若系统直接运行 `.py` 文件，请改用右键“打开方式”选择文本编辑器，不要运行它。
3. 在编辑器按 **Ctrl + F** 搜索 `from cv_bridge import CvBridge`。
4. 向下找到**属于这段代码**的 `except ImportError:`，只把这一行中的文字换成 `except (ImportError, AttributeError):`。行首原有的空格保持不变，下面的代码也不改。
5. 按 **Ctrl + S** 保存，关闭编辑器。

修改前的目标行：

```python
    except ImportError:
```

修改后：

```python
    except (ImportError, AttributeError):
```

如果搜索不到 cv_bridge 导入位置，不要随便改别的 `except`；记录当前 teleop-xr 版本并联系项目提供者核对。

若原本已是上述写法，无需修改。升级或重装 teleop-xr 后重新检查。本文主流程不接入摄像头；若需要视频，必须单独解决 cv_bridge 与 NumPy 的兼容性，不能仅靠这个异常处理证明视频可用。

### 3.3 可选：让左右手分别控制左右臂

如果你只想先跑通双手操作，可以读完下面的说明后直接进入第 4 节；本小节的文件复制只在你拿到补丁文件时执行。

“补丁文件”就是包含功能修改的程序文件。开发机还修改了 `teleop_xr/ik/controller.py` 中的握持检测及 `step()`，实现左右手独立参与 IK。**这些修改在开发机虚拟环境内，并未随 ROS 源码交付**，因此标准安装不能直接保证“握一只手只动一条臂”。

如需复现当前开发机行为，可由维护者从已验收的开发机导出该文件，连同 `requirements-installed.txt` 提供给新电脑：

```bash
# 在已有且已验收的开发机执行，导出到当前目录
cp ~/venv-teleop-xr/lib/python3.10/site-packages/teleop_xr/ik/controller.py \
  ./openarm-teleop-ik-controller.py
```

在新电脑上，先检查安装版本：

```bash
~/venv-teleop-xr/bin/python -m pip show teleop-xr
```

应看到 `Version: 1.3.5`。如果不是，不要覆盖文件。把收到的 `openarm-teleop-ik-controller.py` 放入项目根目录，执行 `cd ~/Teleop/VR_to_Openarm`，再备份原文件并覆盖：

```bash
cp ~/venv-teleop-xr/lib/python3.10/site-packages/teleop_xr/ik/controller.py \
  ~/venv-teleop-xr/lib/python3.10/site-packages/teleop_xr/ik/controller.py.original
# 将收到的文件放在当前目录后执行
cp ./openarm-teleop-ik-controller.py \
  ~/venv-teleop-xr/lib/python3.10/site-packages/teleop_xr/ik/controller.py
```

没有补丁文件时，先按双手握持方式在假硬件上验证；只有观察到左、右握持分别符合预期后，才按单臂控制使用。开发机补丁通过 IK 的静止代价约束未参与的一臂，并非硬件锁定；仍应观察另一臂是否存在轻微变化。

## 4. 网络与 HTTPS

### 4.1 找到电脑局域网 IP

先在 Ubuntu 右上角网络菜单连接 Wi-Fi，再在头显的网络设置里连接同一个 Wi-Fi。电脑也可以通过网线接到同一路由器。仅网络名字相同还不一定能互访，部分公共网络会隔离设备。

在电脑终端执行：

```bash
ip -br -4 addr
```

输出可能像下面这样（这是示例，不是命令）：

```text
lo               UNKNOWN        127.0.0.1/8
wlp2s0           UP             192.168.1.100/24
```

这里 `wlp2s0` 这行对应 Wi-Fi，`192.168.1.100/24` 中斜杠前的 **192.168.1.100** 就是要记下的地址。你的网卡可能叫 `wlan0`，有线网卡也可能叫 `enp...`，名字不同是正常的。打开 Ubuntu 网络设置查看当前连接详情，也能找到 IPv4 地址。

选择连接头显所在网络的网卡地址，例如 `192.168.1.100`，不要用 `127.0.0.1`、Docker 网桥地址或其他网络的地址。后文 `192.168.1.100` 是示例，必须换成自己电脑的 IP。原开发机的 `10.200.0.222` 也不是项目固定地址。

### 4.2 生成匹配自己 IP 的证书

浏览器需要 HTTPS 连接才能使用相关 XR 功能。“证书”是 HTTPS 使用的文件；这里生成的是供自己设备连接的自签名证书。

如果主程序正在运行，先在运行它的终端按 Ctrl+C 停止。然后在电脑终端执行下面的完整代码块：

- **唯一必须修改的是第一行等号后面的 IP**。例如查到 `192.168.31.20`，就把第一行改成 `TELEOP_IP=192.168.31.20`。
- 等号左右不要加空格；其他行完整保留。
- 整块复制到同一个终端并回车。电脑会自动找到安装位置，无需你手动拼接路径。

```bash
TELEOP_IP=192.168.1.100
TELEOP_PACKAGE_DIR=$(~/venv-teleop-xr/bin/python -c \
  'import pathlib, teleop_xr; print(pathlib.Path(teleop_xr.__file__).parent)')
# 如有原证书先备份；不要公开 key.pem
if [ -f "$TELEOP_PACKAGE_DIR/cert.pem" ]; then
  cp "$TELEOP_PACKAGE_DIR/cert.pem" "$TELEOP_PACKAGE_DIR/cert.pem.previous"
fi
if [ -f "$TELEOP_PACKAGE_DIR/key.pem" ]; then
  cp "$TELEOP_PACKAGE_DIR/key.pem" "$TELEOP_PACKAGE_DIR/key.pem.previous"
fi
openssl req -x509 -newkey rsa:2048 -sha256 -days 365 -nodes \
  -keyout "$TELEOP_PACKAGE_DIR/key.pem" \
  -out "$TELEOP_PACKAGE_DIR/cert.pem" \
  -subj '/CN=openarm-teleop' \
  -addext "subjectAltName=IP:${TELEOP_IP},IP:127.0.0.1,DNS:localhost"
chmod 600 "$TELEOP_PACKAGE_DIR/key.pem"
```

成功时通常会显示大量 `+`、`.`，最后回到提示符，不需要再输入证书内容。

可以在同一个终端检查文件是否生成：

```bash
ls -l "$TELEOP_PACKAGE_DIR/cert.pem" "$TELEOP_PACKAGE_DIR/key.pem"
openssl x509 -in "$TELEOP_PACKAGE_DIR/cert.pem" -noout -dates -ext subjectAltName
```

应显示两个文件，第二条命令输出的 `IP Address:` 中应有你刚才填写的 IP。检查命令依赖这个终端中刚设置的变量；如果换了终端，请重新执行设置 `TELEOP_PACKAGE_DIR` 的那条命令。

服务尚未启动时，浏览器打不开页面是正常的。等完成第 5.1 节启动后，再在头显访问 `https://你的电脑IP:4443`。例如 IP 为 `192.168.31.20`，完整地址就是 `https://192.168.31.20:4443`，不用输入“你的电脑IP”这几个字。对于自己生成的自签名证书，浏览器可能要求进入“高级”确认继续访问；若仍不能进入 WebXR，检查浏览器的证书信任和 XR 权限。不能将 HTTPS 改为普通 HTTP 来规避问题。IP 变化、证书过期或重装包后重新生成并重启服务。

防火墙是限制网络访问的软件。如果后面出现“电脑上能打开、头显上打不开”，先在电脑执行：

```bash
sudo ufw status
```

- 显示 `Status: inactive`：这个防火墙没有启用，无需添加下面的规则，继续查 IP 和网络。
- 显示 `Status: active`：它已启用，可按实际网段添加访问规则。

下面是一个**条件示例**。只有你的网络确实为 `192.168.1.0/24` 时才直接使用；如果你不知道实际网段，先把网络信息交给负责网络的人确认，不要猜测后照抄：

```bash
# 只在实际局域网为 192.168.1.0/24 时使用此例
sudo ufw allow from 192.168.1.0/24 to any port 4443 proto tcp
```

先解决网页连通，再解决 VR 会话。不要为了访问页面直接关闭整个防火墙或把遥操服务暴露到公网。

## 5. 先在假硬件上完成一次操作

假硬件模拟控制器和关节反馈，真实电机不会被它驱动；它不是物理动力学仿真。

本节不需要给真实机械臂上电。你看到的是电脑上的模型，适合先确认网页、按钮与程序能正常配合。

### 5.1 启动（终端 A，保持打开）

打开终端 A。如果此前启动过模型展示、MoveIt 或其他遥操程序，在对应终端按 Ctrl+C 退出。第一次启动可以直接执行下面三行：

```bash
source /opt/ros/humble/setup.bash
source ~/Teleop/VR_to_Openarm/ros2_ws/install/setup.bash
ros2 launch openarm_teleop_bridge teleop.launch.py
```

运行第三行后，终端开始持续显示日志（程序运行记录），桌面通常会出现 RViz 模型窗口。**不要关闭这个终端，也不要在里面继续输入检查命令。** 如果没有立即出现网页，先等待，不要重复启动。

这一条命令启动机器人模型、假硬件、左右位置控制器、夹爪控制器、桥接节点、RViz 和 VR 服务。服务延迟约 6 秒启动以等待模型；首次 JAX 编译在开发机约需 20～55 秒，其他机器可能更久。等待出现 `Server started at 0.0.0.0:4443`，再访问网页。

> 启动脚本默认 `preflight_cleanup:=true`，按进程名称清理 `robot_state_publisher`、`ros2_control_node`、spawner、`jt_bridge` 和 `teleop_xr`，可能影响同机其他机器人进程。共享电脑上先自行停止旧实例，再使用下面的启动命令。该选项不会让多个实例各自独立使用话题或端口。

如果这台电脑还运行其他机器人的程序，完成上述旧实例检查后，使用这个假硬件启动命令替代第 5.1 节的第三行：

```bash
ros2 launch openarm_teleop_bridge teleop.launch.py preflight_cleanup:=false
```

如果 RViz 打开但看不到模型，可以在模型区域滚动鼠标滚轮缩放；拖动视角查看模型是否在画面外。空白窗口同时伴随终端报错时，先处理报错，不要进入真机流程。

### 5.2 检查（终端 B）

**让终端 A 保持运行**，再按 Ctrl+Alt+T 打开终端 B。按顺序执行：

```bash
source /opt/ros/humble/setup.bash
source ~/Teleop/VR_to_Openarm/ros2_ws/install/setup.bash
ros2 control list_controllers
ros2 topic echo /joint_states --once
ros2 service list -t
```

`ros2 control list_controllers` 是“列出控制机械臂的软件状态”。输出每一行最后会显示 `active` 或 `inactive`；`active` 表示已启动，`inactive` 表示当前没有工作。

应看到以下控制器为 `active`：

- `joint_state_broadcaster`
- `left_forward_position_controller`、`right_forward_position_controller`
- `left_gripper_controller`、`right_gripper_controller`

第二个检查命令 `ros2 topic echo /joint_states --once` 会读取一次关节反馈，然后自动结束。输出里会有 `name:`、`position:` 等字段；name 中应包含 `openarm_left_joint1` 至 `openarm_left_joint7`、对应的 right 关节以及左右 finger 关节。暂时不用计算 position 数字，先确认数据能读到。

如果超过约 10 秒仍没有输出，按 Ctrl+C 停止**终端 B 的检查命令**，回到终端 A 看是否报错，并确认控制器是否 active。不要关闭终端 A 来结束检查。

第三个检查命令会列出软件提供的操作入口，其中应有 `/enable [std_srvs/srv/SetBool]`。VR 使用 **forward_position_controller**；不要切换成轨迹控制器后仍期待桥接的同一组话题生效。

### 5.3 在头显中连接与练习

1. 先用电脑的 Firefox 或 Chrome 打开 `https://电脑IP:4443`，把“电脑IP”换成第 4.1 节记录的数字地址。能看到 TeleopXR 页面后，再戴上头显进行下一步。不要在浏览器地址栏输入 `0.0.0.0`，那是服务器日志中的监听地址。
2. 头显与电脑连到同一网络，打开头显浏览器，访问同一个完整地址。
3. 确认证书提示后，按网页提供的 VR/沉浸式入口进入会话，允许所需的 XR 权限，确保左右控制器都被识别。按钮文字可能随前端版本变化。
4. 先保持手柄不动，再按住侧面握持键，缓慢移动手柄几厘米，观察 RViz 的机械臂是否跟随；松开后观察是否停止跟随。
5. 若没有安装单臂补丁，使用双手同时握持进行验收；有补丁时分别测试左右手，再测试双手。
6. 分别测试扳机与 X/A，核对下面的操作表。不要在不了解回位动作时直接切到真机。

| 输入 | 当前桥接行为 |
|---|---|
| 侧面握持键 Grip / Squeeze | 一般用中指或无名指按住；按住时移动手柄，机械臂参与跟随。带单臂补丁时左右手独立参与 |
| 松开握持键 | 普通遥操停止跟随，控制器通常保持上一条目标；不是关闭电机 |
| 手柄前面的食指扳机 | 缓慢按下和松开，观察对应夹爪开合。先确认方向，不要一开始就夹物体；方向调整见第 9 节 |
| 左手 X 键 | 按一次，左臂自行移动到预设回位姿态；不要连续乱按 |
| 右手 A 键 | 按一次，右臂自行移动到预设回位姿态 |
| 回位过程中按对应握持键 | 取消该侧回位，并可能重新参与遥操；先保持手柄稳定 |

**夹爪和 X/A 回位不要求按住握持键**，只要求桥接已启用。回位通常约 3 秒，期间手臂会自动运动到预设姿态，并非“所有关节归零”；没有完整 `/joint_states` 时代码会直接发送目标，所以必须先确认反馈正常再回位。

验收标准：网页可连接，关节反馈正常，双臂跟随与松手行为符合预期，夹爪方向已确认，X/A 和取消回位经过练习。最后在终端 A 按 `Ctrl+C` 退出。

## 6. 连接真实机械臂与 CAN

### 6.1 检查连接

CAN 适配器相当于电脑与机械臂之间的通信转换器。连接关系是：

```text
电脑 USB 接口 → 双通道 CAN-FD 适配器
                        ├→ 右臂 CAN 接口
                        └→ 左臂 CAN 接口
机械臂电源 → 按设备说明连接机械臂供电
```

这个图只说明通信关系，**不是电气接线图**。本项目文件没有给出所有适配器的针脚和供电接线标准；因此不能仅凭本文猜测接线。首次连接请使用设备配套的接线说明与线缆，或由设备提供者确认。不要把 USB 通信线当成机械臂电源。

断电状态下按设备说明连接两臂、供电和 CAN 总线，核对终端电阻与接线，再按硬件要求上电。默认 **右臂 can0、左臂 can1**；实际接口按适配器枚举与接线确认，不能只凭线缆颜色判断。

```bash
lsusb
ip -br link
ip -details link show type can
```

第一条 `lsusb` 查看电脑识别到的 USB 设备，第二条查看通信接口名称，第三条专门查看 CAN 接口详细状态。在第二条或第三条输出里找到 `can0` 和 `can1`。如果实际名称不同，后面的 CAN 命令也必须相应修改。

开发机的 PEAK 设备使用内核 `peak_usb` 驱动。若没有 `can0`/`can1`，先排查 USB、驱动和适配器，不能直接跳到 ROS 启动。

### 6.2 配置双通道 CAN-FD

这一小节是设置电脑与电机通信的速率，不是让机械臂运动的操作。先确认所有真机控制程序已经退出；如果第一次部署还没启动过真机程序，可以直接继续。

在电脑终端按顺序执行：

```bash
sudo ip link set can0 down
sudo ip link set can0 up type can bitrate 1000000 dbitrate 5000000 fd on
sudo ip link set can1 down
sudo ip link set can1 up type can bitrate 1000000 dbitrate 5000000 fd on
ip -details link show type can
```

前四行分别关闭再重新打开两条 CAN 通道，最后一行查看结果。输出中应有 `UP`、`fd on`（或等价的 FD 标记）、`bitrate 1000000` 和 `dbitrate 5000000`，表示通信设置为本文要求的 CAN-FD 速率。

如果出现 `Cannot find device "can0"`，说明接口未识别或名称不同，返回第 6.1 节检查；如果出现 `Operation not supported`，检查适配器与驱动是否支持 CAN-FD，不要直接改成普通 CAN 后继续。重新插拔或重启后可能需要重做，接口名也可能变化。

可用下面命令查看右臂总线上是否有数据，它会一直运行：

```bash
candump can0
```

按 Ctrl+C 停止监听，才继续执行下一条命令。查看左臂时把 `can0` 换成 `can1`。未有主机请求时没有帧不一定是故障。进一步诊断请先停止 ROS 真机程序，在电脑终端执行：

```bash
source /opt/ros/humble/setup.bash
source ~/Teleop/VR_to_Openarm/ros2_ws/install/setup.bash
openarm-can-cli -i can0 discover
openarm-can-cli -i can1 discover
```

不要在初次部署时执行 `set_zero` 或零位标定程序来“尝试修复”；它们会改变零点或驱动关节运动。若关节反馈与实际姿态明显不符，先由维护者确认标定。

## 7. 真机启动、操作与结束

### 7.1 启动前核对

确认假硬件练习已通过，左右总线对应无误，两臂姿态与反馈一致，工作区无人，现场观察人员已准备好。**同一时间只运行一套真机控制程序**：VR、MoveIt、示教、CAN 使能工具和标定程序不要并行驱动同一机械臂。

### 7.2 启动（终端 A）

从假硬件切换到真机前，在原终端 A 按 Ctrl+C，等待原程序退出。然后确认本次 CAN 设置完成，再打开或使用终端 A，执行下面的完整命令；后面有 `\` 的三行属于同一条启动命令：

```bash
source /opt/ros/humble/setup.bash
source ~/Teleop/VR_to_Openarm/ros2_ws/install/setup.bash
ros2 launch openarm_teleop_bridge teleop_real.launch.py \
  right_can_interface:=can0 left_can_interface:=can1 \
  enable_on_start:=false return_to_zero:=false
```

**执行这条命令后，就要按真机已启动来对待设备，不要伸手进入两臂运动范围。**

最后一行中的 `enable_on_start:=false` 表示暂时不接收手柄的新动作，`return_to_zero:=false` 表示不要求启动时自动归零；这些选项先保留，不要修改。

这里先关闭**桥接的新输入**，便于检查状态。该命令仍会激活真机硬件，电机可能开始保持位置；并不等于“电机未使能”。真机入口默认 `use_fake_hardware:=false`、`gravity_scale:=1.0`，VR 型号默认 v1.0。

观察日志应使用 `openarm_hardware/OpenArmHW`；如果出现 `mock_generic_system`，停止并排查旧模型发布者或参数。按第 5.2 节确认所有控制器 active、反馈与实际姿态一致，等待 VR 服务 ready。

### 7.3 开始操作（终端 B）

头显连接后保持手柄稳定，在终端 B 执行：

```bash
source /opt/ros/humble/setup.bash
source ~/Teleop/VR_to_Openarm/ros2_ws/install/setup.bash
ros2 service call /enable std_srvs/srv/SetBool '{data: true}'
```

这条命令的意思是“允许把手柄输入转成机械臂命令”，末尾的 `true` 表示允许。输出中应有 `success: true` 与 `jt_bridge enabled`，成功后回到终端提示符。

若显示服务不可用或持续等待，先在终端 B 按 Ctrl+C 停止这条命令，再检查终端 A 是否仍在正常运行。不要反复启动另一套主程序。

允许输出后，从几厘米的小幅移动开始，再逐步使用夹爪、双臂与回位功能。不要立即大幅甩动手柄或把手臂推到限位；若响应不符合预期，停止实验并检查配置。

### 7.4 暂停与停机

“暂时不跟随手柄”“关闭新输入”和“让整个设备停止工作”不是同一步操作。普通遥操暂停时松开握持键；如正在回位，先保持手柄稳定并按对应握持键取消回位。随后可以关闭桥接的新输入：

```bash
ros2 service call /enable std_srvs/srv/SetBool '{data: false}'
```

这里的 `false` 表示不再处理新的遥操输入。以后重新允许输入时，在确认设备状态正常、手柄保持稳定后，执行第 7.3 节的 `true` 命令。

**`/enable=false` 不是急停**：它不关闭电机，当前程序负责自动回位的部分也不受该开关控制，已开始的回位仍可能继续。网络断开时也不能把页面断开当作可靠的电机停机机制。异常情况下由观察人员使用现场确认过的物理停机方式。

正常结束流程：

1. 停止手柄运动，取消正在进行的回位，关闭桥接新输入。
2. 确认两臂有合适支撑，避免解除电机使能后坠落。
3. 在终端 A 按 `Ctrl+C`，等待进程退出；程序正常退出并停用硬件时会发送关闭电机使能的命令，但强制终止或异常崩溃不保证完成这个流程。
4. 按设备停机流程关闭电源，退出头显 VR 页面。不要把 X/A 回位当成断电前的安全停放姿态。

## 8. 常见问题：按这一顺序排查

| 现象 | 检查与处理 |
|---|---|
| `ros2: command not found` | source `/opt/ros/humble/setup.bash`；若文件不存在，先安装 Humble |
| `Package ... not found` | 工作区是否编译成功；是否 source 正确的 `install/setup.bash` |
| 找不到 `~/venv-teleop-xr/bin/python` | 完成第 3 节；自定义路径使用 `teleop_python:=/绝对路径/bin/python` |
| 编译时找不到 Pinocchio / fmt | 检查 apt 依赖、rosdep 输出与 `colcon.meta`；退出 Conda 后重新编译 |
| `pyroki`、`ballpark`、`jaxls` 导入失败 | 使用 VR 虚拟环境执行第 3.1 节导入检查；补装依赖并运行 `pip check` |
| NumPy / cv_bridge 错误导致退出 | 检查第 3.2 节异常处理；若需视频，另外修复 ABI 兼容 |
| `Link openarm_left_link7 not found` | VR 必须使用 v1.0 模型；保留 `arm_type:=openarm_v1.0`，v2.0 不能直接套用 |
| `/robot_description` 超时 | 先检查模型发布者和前面的错误；较慢电脑可用 `teleop_delay:=15.0` |
| 启动后很久没有网页 | 初次 IK 编译可能较慢；观察是否报错，等待 ready 日志 |
| 网页打不开 | 电脑 IP 是否正确、头显是否同网、服务是否 ready；再检查防火墙与 Wi-Fi 客户端隔离 |
| 证书过期 / IP 不匹配 | 按第 4.2 节重建证书，确认设备时间并重启服务 |
| 网页打开但无 VR/控制器 | 确认头显浏览器支持 WebXR、进入沉浸式会话并授予权限 |
| `Address already in use` | `ss -ltnp 'sport = :4443'` 检查占用进程，关闭旧服务后重启 |
| 控制器 inactive / 机械臂不动 | 先用 `ros2 control list_controllers` 检查，再确认桥接 enable、握持与 `/joint_trajectory` 输入 |
| 只握一只手不动 | 新安装可能没有单臂补丁；先双手握持测试，按第 3.3 节确认补丁来源 |
| 真机启动却显示假硬件 | 查 `ros2 node list` 是否有重复节点，关闭旧 launch；核对 `use_fake_hardware` |
| CAN 报错、无反馈或反馈错位 | 检查接口 UP/FD/速率、供电、左右接线与标定；有问题先停止真机实验 |
| 运动时振荡、下垂或异常发热 | 停止真机实验；由维护者核对模型、重力补偿、增益与电机状态，避免直接增大增益 |

连接头显后，下面的命令可帮助维护者逐层检查数据。`ros2 topic hz` 会一直运行，必须按 Ctrl+C 停止后才能执行后面的命令：

```bash
ros2 topic echo /xr/controller_left/joy --once
ros2 topic echo /xr/controller_right/joy --once
# 握持并移动手柄时检查 IK 输出
ros2 topic hz /joint_trajectory
ros2 topic echo /left_forward_position_controller/commands --once
ros2 topic echo /right_forward_position_controller/commands --once
```

检查顺序为 **手柄 Joy → IK 关节轨迹 → 桥接位置命令 → 控制器 → CAN 与机械臂**。没有消息时 `--once` 会等待，不代表命令执行失败。

## 9. 可选参考：参数与内部数据流

**日常使用不需要修改本节参数，也不需要理解每个话题名称。** 前面的默认命令已经设置好正常 VR 流程。只有需要自定义或排查时再看本节。

IK 是把手柄的位置与朝向换算成关节角度的计算过程；“桥接”是把 VR 软件给出的数据转换成机械臂控制器所需格式的程序。数据按下面的顺序流动：

```text
头显浏览器 + 左右手柄
  → HTTPS / WebXR → teleop_xr（独立 Python 环境，IK）
  → /joint_trajectory 与 /xr/controller_{left,right}/joy
  → jt_bridge（ROS 2 桥接）
  → 左右 forward_position_controller + gripper_controller
  → ros2_control → 假硬件 或 OpenArmHW → CAN-FD 电机
```

| 启动参数 | 普通 VR 入口默认值 | 说明 |
|---|---|---|
| `arm_type` | `openarm_v1.0` | VR 模型要求 v1.0；普通 bringup/MoveIt 默认 v2.0，不要混淆 |
| `robot_controller` | `forward_position_controller` | 与桥接输出匹配，VR 流程保留此值 |
| `use_fake_hardware` | `true` | 真机入口默认 `false` |
| `gravity_scale` | `0.0` | 真机入口默认 `1.0`；重力补偿效果取决于模型和安装情况 |
| `enable_on_start` | `true` | 本文真机示例显式设 `false` 后人工启用；不是硬件使能开关 |
| `return_to_zero` | `false` | 保持当前启动位置；设 true 会触发启动归零运动，初次使用保留 false |
| `teaching_mode` | `false` | VR 保留 false，拖动示教使用独立流程 |
| `right_can_interface` / `left_can_interface` | `can0` / `can1` | 按现场接线确认 |
| `teleop_python` | `~/venv-teleop-xr/bin/python` | 自定义时传展开后的绝对路径 |
| `teleop_delay` | `6.0` | 等待模型就绪的秒数 |
| `preflight_cleanup` | `true` | 按进程名称清理旧实例，共享机器谨慎使用 |

默认夹爪目标范围为 0～0.044 米；默认回位姿态按左臂 `[0, -0.8, 0, 1.2, 0, 0, 0]`、右臂 `[0, 0.8, 0, 1.2, 0, 0, 0]` 设置，单位为弧度。这些数字供配置核对，日常操作无需输入它们。

桥接还提供 `left_home`、`right_home`、`home_duration`、`invert_gripper` 等 ROS 节点参数，但它们**没有全部暴露为一键 launch 参数**；不能直接写 `teleop.launch.py invert_gripper:=true` 就认为生效。维护者应修改启动文件中桥接 Node 的 `parameters` 或使用独立节点启动，并先在假硬件验证。

只启动桥接：`ros2 launch openarm_teleop_bridge bridge.launch.py`，默认关闭输出；该命令不会启动机器人或 VR 服务。无需在完整 VR launch 后再运行一次。

可选功能及历史技术资料见 [MoveIt、示教、规划与诊断参考](ros2_ws/docs/advanced.md)。这些功能是独立使用路径，切换前先退出 VR 真机栈。首次使用请依次确认环境与假硬件运行正常、头显与控制器响应正确，再在现场观察人员配合下进行真机小幅运动测试。


## 10. 以后每次使用时做什么

下面仅适用于你已经完成前面的安装、假硬件练习和相应功能检查。**平时不需要重新 apt 安装、pip 安装或编译。** 换电脑、移动项目目录、修改源码、重装第三方包时，再回到对应部署步骤。

### 10.1 再次使用假硬件

1. 电脑与头显连接同一局域网。按第 4.1 节检查电脑 IP；如果和证书中的 IP 不同，先按第 4.2 节重新生成证书。
2. 打开终端 A，执行：

```bash
source /opt/ros/humble/setup.bash
source ~/Teleop/VR_to_Openarm/ros2_ws/install/setup.bash
ros2 launch openarm_teleop_bridge teleop.launch.py
```

3. 等终端显示服务 ready，头显访问 `https://电脑IP:4443`，进入 VR 会话。
4. 按第 5 节操作表练习。使用结束后，在终端 A 按 Ctrl+C，再退出头显页面。

### 10.2 再次使用真机

1. 检查机械臂固定、工作范围、供电、左右 CAN 接线与现场停机条件，准备好观察人员。
2. 连接电脑与头显网络，确认 IP 和证书。检查适配器仍对应右臂 can0、左臂 can1。
3. 打开终端 A，设置 CAN（如果重启或重新插拔过，尤其要重新检查）：

```bash
sudo ip link set can0 down
sudo ip link set can0 up type can bitrate 1000000 dbitrate 5000000 fd on
sudo ip link set can1 down
sudo ip link set can1 up type can bitrate 1000000 dbitrate 5000000 fd on
ip -details link show type can
```

4. 确认 CAN 状态正确，在终端 A 启动真机：

```bash
source /opt/ros/humble/setup.bash
source ~/Teleop/VR_to_Openarm/ros2_ws/install/setup.bash
ros2 launch openarm_teleop_bridge teleop_real.launch.py \
  right_can_interface:=can0 left_can_interface:=can1 \
  enable_on_start:=false return_to_zero:=false
```

5. 终端 A 保持运行。打开终端 B，检查控制器和关节数据：

```bash
source /opt/ros/humble/setup.bash
source ~/Teleop/VR_to_Openarm/ros2_ws/install/setup.bash
ros2 control list_controllers
ros2 topic echo /joint_states --once
```

6. 控制器正常、反馈与姿态一致、服务 ready 后，在头显连接页面并进入 VR。保持手柄稳定，在终端 B 执行：

```bash
ros2 service call /enable std_srvs/srv/SetBool '{data: true}'
```

7. 按住握持键，从小幅移动开始使用。结束时按第 7.4 节顺序取消回位、关闭新输入、支撑两臂、在终端 A 按 Ctrl+C，再按设备流程关闭电源。

### 10.3 哪些变化需要重新设置

| 发生的变化 | 要做的事 |
|---|---|
| 只是关闭程序后再打开 | 重做启动步骤，不必重装软件 |
| 电脑或 CAN 适配器重新插拔 / 重启 | 重新检查接口名称与 CAN 通信设置 |
| 换 Wi-Fi、路由器分配了新 IP | 核对 IP，必要时重新生成证书；头显使用新地址 |
| 证书过期 | 重新生成证书并重启 VR 服务 |
| 换电脑或项目目录位置 | 在目标位置重新部署 / 编译，不能只复制 install 目录 |
| 升级或重装 teleop-xr | 核对版本、兼容修改、单臂补丁和证书，再通过假硬件测试 |

如果需要请求支持，请提供：Ubuntu 版本、执行到哪一节哪一步、完整命令、终端错误输出，以及当前是假硬件还是真机。请勿发送密码或 `key.pem` 文件。
