# Jetson 部署与使用指南

本文介绍如何把 PS2_to_Piper 部署到 Jetson，通过接在 Jetson 上的 USB 游戏手柄控制 PiPER 机械臂。首次完成安装和设备检查后，后续只需进入项目目录并启动程序。

## 1. 本次验证的设备环境

| 项目 | 本次环境 |
| --- | --- |
| 架构 | aarch64（ARM64） |
| 系统 | Ubuntu 22.04.5 LTS |
| Jetson Linux | R36.4.7 |
| 内核 | 5.15.148-tegra |
| 系统 Python | 3.10.12 |
| 项目 Python | 独立 Python 3.11 环境，本次安装为 3.11.17 |
| Jetson 登录用户 | nvidia |
| 项目目录 | /home/nvidia/PS2_to_Piper/Gamepad_PiPER |
| 手柄 | USB 标识 045e:028e，识别为 Xbox 360 Controller |
| USB-CAN | USB 标识 1d50:606f，驱动 gs_usb |
| 本次 USB-CAN 接口 | can1；板载 can0 使用 mttcan |

上述设备已完成环境安装、手柄识别、USB-CAN 驱动加载和 CAN 接收检查。其他设备请核对实际系统和接口名。本文的驱动修复脚本仅适用于 ARM64 的 `5.15.148-tegra` 内核。

复制命令时只复制代码块内容，不要带终端提示符或 `<br/>` 等网页标记。`sudo` 密码输入时不显示字符是正常现象。

## 2. 通过 SSH 登录 Jetson

第一次在 **Jetson 本地终端**执行：

```bash
sudo apt update
sudo apt install -y openssh-server
sudo systemctl enable --now ssh
hostname -I
```

记下 IP 地址，让电脑和 Jetson 处于可互相访问的网络。在 **电脑终端**执行，把 `JETSON_IP` 换成实际地址。本次地址为 `10.200.2.132`，以后可能变化。

```bash
ssh nvidia@JETSON_IP
```

首次连接时核对目标设备，确认后输入 `yes`，再输入 Jetson 登录密码。看到 `nvidia@nvidia-desktop:~$` 表示已经进入 Jetson，之后这个终端的命令运行在 Jetson 上。用户名不是 `nvidia` 时，请替换文中的用户名和对应家目录。

输入 `exit` 可以回到电脑终端。插入手柄或 USB-CAN 通常无需重新登录 SSH；修改用户组后需要重新登录使权限生效。

## 3. 将项目从电脑传到 Jetson

在 **电脑终端**进入 `PS2_to_Piper` 的上一级目录。

路径不同则换成自己的目录。打包并上传完整源码，排除旧运行环境和本地管理目录：

```bash
tar --exclude='.git' --exclude='.github-upload' --exclude='.runtime' \
    --exclude='__pycache__' --exclude='*.pyc' --exclude='.agents' \
    --exclude='.codex' --exclude='.aws' --exclude='.env' \
    -czf /tmp/PS2_to_Piper-jetson.tar.gz PS2_to_Piper
scp /tmp/PS2_to_Piper-jetson.tar.gz nvidia@JETSON_IP:/home/nvidia/
```

这两条命令在电脑上执行。如果在 Jetson 上执行 `scp`，它会寻找 Jetson 自己的 `/tmp/`，可能提示源文件不存在。

通过 SSH 登录后，在 **Jetson 终端**解压：

```bash
tar -xzf ~/PS2_to_Piper-jetson.tar.gz -C ~
cd ~/PS2_to_Piper/Gamepad_PiPER
ls setup.sh start.sh deployment/install_xpad.sh deployment/install_gs_usb.sh
```

如果 Jetson 已有同名项目，先备份旧目录再解压，避免混入旧文件。不要复制电脑上的 `.runtime/`，需要在 Jetson 重新安装。以下命令除特别说明外，都在 `~/PS2_to_Piper/Gamepad_PiPER` 执行。

## 4. 一键安装环境

以普通登录用户运行：

```bash
bash setup.sh
```

首次安装需要联网和 sudo 密码。脚本安装系统依赖、下载 micromamba，在项目 `.runtime/` 中创建 Python 3.11 环境，安装 Pinocchio、CasADi、pygame、PiPER SDK 等依赖，并检查模型和运动学。

无需替换系统 Python，也无需手动安装 Conda 或 ROS。安装过程不会连接或使能机械臂。看到“运动学检查通过”和“部署完成”后继续下一步。

重复运行会复用环境并补齐依赖。不要移动已安装的项目目录，移动后应重新安装。若旧版脚本下载 micromamba 返回 404，核对下载地址应为 `https://micro.mamba.pm/api/micromamba/$PLATFORM/latest`；本项目当前脚本已使用此地址。

## 5. 检查手柄及修复驱动

将手柄 USB 接收器插在 **Jetson** 上，打开手柄并完成配对：

```bash
bash start.sh virtual --check
```

本次识别结果为 `Xbox 360 Controller`，11 个按钮、6 个轴、1 组方向键。`--check` 检查环境、模型和手柄枚举，不发送 CAN 指令；仍需验证实际按键、摇杆和扳机映射。

### 5.1 提示“未发现手柄”

```bash
lsusb
lsusb -t
cat /proc/bus/input/devices
sudo modprobe xpad
```

本次故障表现：USB 列表有 `045e:028e`，但对应 `Driver=` 为空，输入设备列表没有手柄，`modprobe` 提示找不到 xpad 模块。这是驱动缺失，单纯重新插拔或改权限无法解决。

内核与本文一致时，使用项目内脚本修复：

```bash
bash deployment/install_xpad.sh
```

不要用 `sudo bash` 启动脚本。脚本通过匹配的内核头文件编译安装驱动，并添加针对本次手柄的输入权限规则。完成后拔插接收器；如果新增了用户组，退出 SSH 后重新登录，再进入项目目录检查：

```bash
lsusb -t
bash start.sh virtual --check
```

设备应显示 `Driver=xpad`。驱动已加载但读取失败时，再检查 `/dev/input/` 权限和用户组。

### 5.2 确认 HOME 和 START 编号

SSH 下运行以下测试，依次按实体按钮，查看编号；用 `Ctrl+C` 退出：

```bash
SDL_VIDEODRIVER=dummy .runtime/env/bin/python - <<'PY'
import pygame
pygame.init()
pygame.joystick.init()
if pygame.joystick.get_count() == 0:
    pygame.quit()
    raise SystemExit("未发现手柄")
j = pygame.joystick.Joystick(0)
j.init()
print("依次按下实体按钮，查看编号；Ctrl+C 退出", flush=True)
try:
    while True:
        for event in pygame.event.get():
            if event.type == pygame.JOYBUTTONDOWN:
                print("按下按钮编号:", event.button, flush=True)
        pygame.time.wait(20)
except KeyboardInterrupt:
    pass
finally:
    pygame.quit()
PY
```

本次 HOME 是 `8`，START 是 `7`。不同手柄可能不同。完整映射及轴检查见 [README 的手柄检查章节](README.md#3-检查手柄及按键映射)，先在虚拟模式确认全部控制，再使用真机。

## 6. 先运行虚拟模式

SSH 下推荐网页显示：

```bash
bash start.sh virtual --backend viser
```

电脑浏览器访问终端显示的端口，地址中的 `localhost` 或 `127.0.0.1` 换成 Jetson IP。网页展示目标模型，手柄仍接在 Jetson 上。确认按键、摇杆方向和夹爪行为后，用 `Ctrl+C` 结束虚拟程序。

仅看终端状态：

```bash
bash start.sh virtual --backend none
```

无桌面显示时默认关闭可视化，pygame 使用 dummy 显示驱动读取手柄。默认部署不安装 MuJoCo，不能在普通 SSH 无桌面环境直接打开其原生窗口。

## 7. 检查 USB-CAN 及修复驱动

将 USB-CAN 插在 **Jetson** 上，按机械臂设备手册完成供电和接线：

```bash
lsusb
lsusb -t
ip -brief link
sudo modprobe gs_usb
```

本次适配器为 `1d50:606f`。最初 USB 已识别，但驱动为空，只有板载 `can0`；`modprobe` 提示缺少模块，内核配置为 `# CONFIG_CAN_GS_USB is not set`。

内核与本文一致、遇到同样问题时运行：

```bash
bash deployment/install_gs_usb.sh
```

脚本使用匹配的内核头文件编译安装驱动，加载 CAN 模块，不会使能机械臂或发送运动指令。完成后拔插 USB-CAN，再执行：

```bash
lsusb -t
ip -brief link
ethtool -i can1
```

本次对应设备显示 `Driver=gs_usb`，新增 `can1`，`ethtool` 显示 `driver: gs_usb`。**实际编号不同，请将下面所有 `can1` 替换成检查到的 USB-CAN 接口。** 板载 `can0` 使用 `mttcan`，不能仅凭名字选择它。

修复脚本及源码都在项目中，无需下载对话附件：

- [手柄驱动修复脚本](deployment/install_xpad.sh)
- [USB-CAN 驱动修复脚本](deployment/install_gs_usb.sh)
- [驱动源码及许可证](deployment/drivers/)

脚本会检查内核及头文件。缺少匹配头文件时先处理报错，不要强行加载其他版本模块。内核升级后应重新检查驱动，旧内核编译的模块不能直接复用。

## 8. 配置 CAN 并确认反馈

退出其他使用该接口的控制程序，再执行：

```bash
sudo ip link set can1 down
sudo ip link set can1 type can bitrate 1000000
sudo ip link set can1 up
ip -details -statistics link show can1
timeout 5s candump can1
```

这一步配置总线并监听，不主动发送运动指令。正确结果：

- 接口为 `UP`，速率为 `1000000`。
- CAN 状态为 `ERROR-ACTIVE`，这是正常状态名称。
- `candump` 在监听期间持续出现接收帧。

`timeout` 到 5 秒结束监听是正常现象。RX 累计数很大不能单独证明当前仍有反馈，应查看实时接收帧。

若无反馈或出现 `BUS-OFF`，检查接口、机械臂电源、CAN-H/CAN-L、终端电阻和速率。若出现 `Device or resource busy`，停止控制程序后先将接口 down，再设置速率。

## 9. 启动真机

确认手柄映射正确、CAN 有实时反馈，清空回零路径和夹爪周围物品，并准备好设备规定的硬件紧急停止方式。

当前启动脚本会配置 CAN 速率，因此完成监听后，先将接口 down 再启动：

```bash
sudo ip link set can1 down
bash start.sh real --backend none --can can1
```

需要网页目标模型时，启动命令换成：

```bash
bash start.sh real --backend viser --can can1
```

不要同时运行两个真机控制程序。`start.sh` 默认底层速度 `10%`、速度因子 `0.25`、底层模式 `joint`。旧 `python main.py` / `run_real.py` 入口默认速度不同，不能套用这里的低速结论。

### 9.1 已启动，但机械臂没有动

初始 `Robot arm status: Disconnected/Disabled` 表示程序等待连接。确认回零路径安全后，按已验证的 **HOME（本次按钮 8）** 才会连接使能，并立即发送回零指令，夹爪随后接收开合指令（启动默认关闭）。成功后状态应为 `Connected/Enabled`。

START（本次按钮 7）切换模式，不能代替 HOME 连接。刷新时间变化只说明程序在运行，关节显示全零也不能证明已收到真机反馈。

如果状态一直未连接，先确认 HOME 编号和本次命令的 `--can can1`；若按 HOME 后一直等待，检查 CAN、供电、硬件急停及 SDK/固件兼容性。当前使能循环没有超时。

完整操作见 [README 的手柄操作速查](README.md#6-手柄操作速查)。当前真机底层 `pose` 分支有角度单位风险，首次使用保持底层 `joint`。

### 9.2 退出程序

**真机模式的 `Ctrl+C` 不是急停。** 已使能时，程序会尝试回零，再发送保持指令后退出；退出不等于断电。正常结束前取下物品并清空回零路径，最终停机按设备手册执行。

手柄掉线没有自动失能/急停逻辑。出现碰撞风险或失控时使用设备规定的硬件紧急停止方式。可视化展示目标模型，不能代替真机反馈或障碍物检测。详细退出行为见 [README 的结束章节](README.md#7-结束实验与再次启动)。

## 10. 下次启动速查

已完成安装时，无需重装环境和驱动。在电脑终端登录：

```bash
ssh nvidia@JETSON_IP
```

在 Jetson 上确认设备接线、实际 USB-CAN 接口和回零路径，再执行：

```bash
cd ~/PS2_to_Piper/Gamepad_PiPER
sudo ip link set can1 down
bash start.sh real --backend none --can can1
```

等待 HOME 连接使能。仅在其他程序没有使用该接口时执行 down。重新插拔设备或更新内核后，先核对驱动和接口编号。

在同一 Jetson 部署另一个项目时，可以复用已安装的系统驱动，但应建立独立 Python 环境，避免两个程序同时控制同一机械臂。
