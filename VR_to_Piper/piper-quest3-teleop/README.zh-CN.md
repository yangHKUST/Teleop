# Piper + Quest 3 遥操作 · 中文使用指南

本文件只讲**怎么用**：如何把程序跑起来、Quest 3 怎么连、以及**在 VR 里怎么操作让机械臂动起来**。
（技术架构、致谢等见原 [README.md](./README.md)）

---

## 0. 一句话总结操作方式

> **右手握把按钮（squeeze）按住 = 机械臂跟着你的右手动；松开 = 机械臂冻结。**
> **右手扳机（trigger） = 夹爪开合。A 按钮 = 机械臂回零位。**

这是安全设计（deadman 开关）：机械臂**只有在你按住握把按钮时才会动**，松手立刻停。

---

## 1. 启动程序

在电脑（已配好 conda 环境 `piper-teleop`）上：

```bash
cd /home/taoqiu/Meta_to_Piper/piper-quest3-teleop

# ① 仿真（安全，不碰真机，用于先熟悉操作流程）
./run_teleop.sh --dry-run

# ② 真机（会连接 CAN 并驱动机械臂 —— 确认机械臂已上电、处于安全位姿后再跑）
#    默认：左臂 = can0，右臂 = can1。两条臂同型号同夹爪、同向并排。
./run_teleop.sh --can-left can0 --can-right can1

./run_teleop.sh --can-left can1 --can-right can0

# 单臂：只连接 can0，只启动一个发送进程，由右手柄控制
./run_teleop.sh --can can0
# 单臂仿真
./run_teleop.sh --can can0 --dry-run

# 可选：开启立体相机流（ZED / USB 双目相机，Quest 3 里显示画面）
./run_teleop.sh --can-left can0 --can-right can1 --camera 0
```

> `run_teleop.sh` 会自动隔离环境（去掉 `~/.local` 和 ROS 的污染），不要用裸 `python -m ...` 直接跑。
> `--can` 不能与 `--can-left/--can-right` 混用；双臂的两个 CAN 口必须不同。
> Ctrl+C 只停止发送并释放资源，不发送回零命令；需要回零时，先使用手柄回零按钮。

## 1.1 CAN 接口配置（真机前必读）

真机模式通过 SocketCAN 直接驱动机械臂，**每次重启 / 重插转接器后都要手动把 `can0`/`can1` 拉起来**（两块臂默认 **1 Mbps**）。
单臂只需配置和检查实际连接的 `can0`，不需要 `can1`。

### ① 拉起 can0 / can1

```bash
sudo ip link set can0 type can bitrate 1000000
sudo ip link set can1 type can bitrate 1000000
sudo ip link set can0 up
sudo ip link set can1 up
```

### ② 检测接口是否连通

```bash
# 看速率与状态（state 应为 UP、bitrate 1000000）
ip -details link show can0 | grep -E "state|bitrate"
ip -details link show can1 | grep -E "state|bitrate"

# 看能否收到机械臂的 CAN 报文（Ctrl+C 退出）
candump can0
candump can1
```

> `candump` 来自 `can-utils`，没装就 `sudo apt install can-utils`。两个口都能刷出持续报文 = 链路通；没有输出就查接线 / 机械臂是否上电 / `sudo dmesg | grep -i can`。

若出现 `Enable timeout`：

- SDK 0.6.1 的 `EnableArm()` 没有返回值，`ret=None` 本身不表示失败；成功以六个电机的反馈使能位为准。
- 日志中的 `missing_feedback=[1, 2, 3, 4, 5, 6]` 表示六个电机都没有低速状态反馈（CAN ID `0x261`–`0x266`）。先检查机械臂电源、CAN 接线和速率。
- 被动检查可运行 `timeout 4s candump -n 30 can0`（只监听，不使能、不发送运动指令）。没有输出且退出码为 124 表示这 4 秒内未收到报文。
- 若已有反馈但 `enabled` 仍包含 `False`，根据 `fault_bits` 和机械臂状态继续检查。`fault_bits` 是驱动器状态字去除使能位后的十六进制值。
- 发送进程使能失败或退出时，主程序会终止并释放资源，不再用零关节角假装初始化成功。

### ③ 左右臂 ↔ can0 / can1 的对应关系

- 默认约定：**左臂 = `can0`，右臂 = `can1`**，启动参数一一对应：`./run_teleop.sh --can-left can0 --can-right can1`。
- **发现「左臂跑成右臂」**（多块 USB-CAN 转接器的插拔顺序会让 `can0`/`can1` 名字对调），两种处理：

  1. **最简单**：直接对调启动参数
     ```bash
     ./run_teleop.sh --can-left can1 --can-right can0
     ```
  2. **一劳永逸**：用 udev 规则按转接器序列号固定设备名（详见 `instruction.md` 第七节）。

- **怎么判断哪块臂挂在哪个口**：把两块臂摆成明显不同的姿态，启动后看日志里的实际关节角读回，对照实物即可：
  ```text
  [sender][left]  joint readback (rad): [...]
  [sender][right] joint readback (rad): [...]
  ```

### ④ 权限（报 Permission denied 时）

程序通过 `piper_sdk` 打开 CAN **raw socket**，需要 root 或 `CAP_NET_RAW`。二选一：

- `sudo -E ./run_teleop.sh --can-left can0 --can-right can1`（`-E` 保留环境让 conda 仍能激活），或
- `sudo setcap cap_net_raw,cap_net_admin+eip "$(conda run -n piper-teleop which python)"`（setcap 后不要再动该 conda 环境）。

---

## 2. Quest 3 连接

1. Quest 3 和电脑连到**同一个 WiFi/局域网**（默认电脑 IP：`10.200.0.222`）。
2. Quest 3 打开浏览器，访问：
   ```
   https://10.200.0.222:8012
   ```
   ⚠️ vuer 0.0.70 客户端有个 bug：用 https 访问时会丢掉端口、去连 443，导致 WebSocket 连不上、头显里看不到画面也收不到手柄数据。本项目已在**服务端加了自动重定向**（`TeleVision.py` 的 `_make_ws_redirect_middleware`），打开上面的地址即可，**不用手动带参数**；服务器会自动把地址补成 `?ws=wss://10.200.0.222:8012`。
3. 因为用的是**自签名证书**，浏览器会弹「不安全/证书」警告 —— 点「高级」→「继续前往」（首次要允许一下）。

> 查电脑当前 IP：`ip -4 addr show wlo1`。如果不是 `10.200.0.222`，用实际 IP 替换（**URL 里的两处 IP 都要一起换**）；证书里已含 `localhost / 127.0.0.1 / 10.200.0.222` 三个 SAN，换 IP 需要重新生成证书。

连上后 Quest 3 里会看到：
- **背景画面** = 相机流（没开 `--camera` 时是黑屏，属正常）；
- **机械臂骨架（skeleton）** = 遥操作时叠加显示机械臂各关节位置，用来判断机械臂当前姿态；
- 两只手柄的位置。

---

## 3. 右手控制器：核心操作（让机械臂动）

Quest 3 的按键在代码里的对应关系（见 `TeleVision.py` + `init_right_controller.py`）：

| 右手按键 | 作用 | 说明 |
|---|---|---|
| **握把按钮（Grip / Squeeze，中指点住的侧键）** | **遥操作使能开关** | **按住不放** → 机械臂末端跟随右手移动/旋转；**松开** → 机械臂冻结（HOLD） |
| **扳机（Trigger，食指）** | **夹爪开合** | 抠到底 = 夹爪闭合（夹物体）；松开 = 夹爪张开。模拟量，按多深开合多大 |
| **A 按钮** | **回零位** | 机械臂自动回到起始姿态 `q=[0,0,0,0,0,0]` |

### 映射方式：**增量（相对）控制**

不是「手在哪机械臂就在哪」的绝对控制，而是：

- 你**按下握把按钮的瞬间**，系统把你右手当时的位置/朝向记作「零点（neutral）」；
- 之后你**手相对这个零点的位移/旋转**，会 1:1 映射成机械臂末端相对当前姿态的位移/旋转（`position_scale = 1.0`，即 1 米 = 1 米，不加缩放）。

所以：
- **按下 → 保持手不动 → 机械臂不动**；
- **按下后手向右挪 → 机械臂末端也向右挪同样的量**；
- 想抓更远的物体，就先把机械臂停到中间，松开再按一次（重新设零点），分几步够过去。

---

## 4. 工作模式（自动状态机，不用手动切）

程序内部有 4 个模式，由你的按键自动切换：

```
启动 ──► RETURNING  机械臂自动回零位
          │  (q 回到 0 附近)
          ▼
        AT_ZERO     到零位，等待
          │  按下「握把按钮」
          ▼
        TELEOP      跟随：右手动，机械臂动
          │  ▲
    松开握把│  │按下握把（重新设零点）
          ▼  │
        HOLD        冻结：机械臂保持当前姿态
          │
   按「A 按钮」 ──► 回到 RETURNING（回零位）
```

- **进入 TELEOP**：在 `AT_ZERO` 或 `HOLD` 时**按下握把按钮**。
- **冻结**：在 TELEOP 时**松开握把按钮** → 进入 HOLD。
- **回零**：在 HOLD 时按 **A 按钮**。

> 想移动机械臂的标准节奏：**按住握把 → 手移动到目标 → 松开握把（冻结）→ 需要时再按住继续**。不要一直按住把手甩来甩去，避免机械臂突跳。

---

## 5. 左手控制器

当前配置里**左手基本不用**（它是给可移动底盘 `vision60` 用的，ROS2 桥接在代码里被注释掉了，`vision_node=None`）：

- 摇杆 → 底盘前后/旋转（当前无效）；
- Y 按钮 → 切换视觉模式（当前无效）。

固定机械臂场景下，**忽略左手即可**。

---

## 6. 安全注意事项（重要）

1. **握把按钮 = 死手开关**：机械臂只在按住时动，感觉不对**立刻松手**，机械臂就停。
2. **A 按钮回零**：任何时候想让它回安全位姿，按 A。
3. **退出（Ctrl+C）**：停止发送并释放资源，不自动回零，也不发送失能指令。需要回零时，在退出前使用 A 按钮。
4. **第一次真机联调**：建议先用 `--dry-run` 在仿真 viewer 里熟悉按键和映射，再上真机；上真机时人不要站在机械臂工作范围内，随时准备按急停。
5. **夹爪方向**：默认「抠扳机=闭合、松开=张开」。如果真机上方向反了，改 `teleop/config.py` 里的 `GRIP_INVERT`（或 `RightControllerConfig.gripper_close_when_high`）。

---

## 7. 常见问题排查

| 现象 | 原因 / 处理 |
|---|---|
| Quest 3 浏览器打不开页面 | 确认电脑 IP 是 `10.200.0.222`、服务在跑（`ss -tlnp \| grep 8012`）；确认 Quest 和电脑同网段 |
| 浏览器报证书错误 | 正常，点「高级 → 继续前往」 |
| VR 里一片黑 | 没开相机流（`--camera`），背景本来就是黑的；骨架 overlay 和手柄仍在 |
| 机械臂不动 | 看日志 `[MODE]` 在哪一模式：只有 TELEOP 才跟手（要**按住握把按钮**）；AT_ZERO 是停在原地等按握把，RETURNING 是正在回零 |
| 日志出现 `no joint readback` / `Permission denied` | CAN 没通，按上文 1.1 节查：接口是否 up、有没有权限、左右臂是不是接反 |
| 机械臂动作方向/幅度不对 | 检查 `VRMapperConfig.P`（VR→机器人坐标轴映射）和 `position_scale`，见 `teleop/mapping/vr_mapper.py` |
| 机械臂乱跳/抖 | 握把按钮松得不够干脆、或手在零点附近抖动；按 A 回零重来 |

---

## 附：调试参数（改后生效）

- 右手夹爪：`teleop/app.py` 里 `RightControllerConfig(...)` 的 `gripper_out_min/max`、`gripper_deadzone_low/high`、`gripper_alpha`。
- 右手遥操作死区/阈值：`RightControllerConfig.threshold`（默认 0.5）。
- 位置缩放 / 坐标轴映射：`teleop/mapping/vr_mapper.py` 的 `VRMapperConfig.position_scale` 和 `P`。
- 夹爪方向：`teleop/config.py` 的 `GRIP_INVERT` / `GRIP_MAX_UM`。

---

## 8. Jetson 部署与运行

本节中的安装、启动和检查命令均在外层 `VR_to_Piper` 目录执行，而不是本 README 所在的 `piper-quest3-teleop` 子目录。电脑端与 Jetson 端的命令分别标明。

### 8.1 设备环境

本次部署记录如下，其他设备需先核对实际配置：

| 项目 | 配置 |
| --- | --- |
| CPU 架构 | aarch64 / ARM64 |
| 系统 | Ubuntu 22.04.5 LTS |
| Jetson Linux | R36.4.7 |
| 内核 | 5.15.148-tegra |
| 用户 | nvidia |
| 本次局域网 IP | 10.200.2.132，使用前需确认 |
| 项目目录 | `/home/nvidia/VR_to_Piper` |
| 项目 Python | 项目内独立 Python 3.11 环境 |

当前源码位于 `piper-quest3-teleop/`，使用 **MuJoCo + mink + DAQP** 计算逆运动学。遥操作部署不需要安装 ACT 训练环境、PyTorch、CUDA 或 ROS。

项目使用独立的 `.runtime/env`，不替换系统 Python，不复用或更新已有 PS2_to_Piper 环境。已安装的 USB-CAN 驱动可继续使用；内核升级后需重新核对驱动匹配情况。

### 8.2 上传项目

在**电脑终端**执行：

```bash
scp /tmp/VR_to_Piper-jetson.tar.gz nvidia@10.200.2.132:/home/nvidia/
ssh nvidia@10.200.2.132
```

上传前确认压缩包确实存在；IP 改变时替换为 Jetson 当前地址。密码在终端输入。上述 `/tmp/VR_to_Piper-jetson.tar.gz` 是本次部署包的位置，其他部署应替换为实际文件路径。

不要把电脑上的 Conda 环境、`.runtime`、虚拟环境或缓存复制到 Jetson。部署包应包含源码、外层部署脚本、模型和许可证，并排除私钥等秘密文件。

在 **Jetson SSH 终端**执行：

```bash
test ! -e ~/VR_to_Piper && tar -xzf ~/VR_to_Piper-jetson.tar.gz -C ~
cd ~/VR_to_Piper
```

如果同名目录已经存在，上述命令不会解压，应先检查已有内容，避免覆盖。

### 8.3 一键安装

在 **Jetson SSH 终端**执行：

```bash
cd ~/VR_to_Piper
bash setup_jetson.sh
```

脚本安装系统工具，在项目内创建独立环境，并检查模型与 IK。安装需要联网，系统依赖安装期间可能要求输入 sudo 密码。安装日志保存在 `.runtime/logs/setup.log`。

本次 ARM64 安装已完成，日志确认：

```text
Python: /home/nvidia/VR_to_Piper/.runtime/env/bin/python
模型和 IK 检查通过：nq=8，solver=daqp；未连接 CAN。
部署完成
```

这里的 `nq=8` 包含六个机械臂关节和两个模型夹爪关节，不表示机械臂有八轴。这个结果证明模型与求解器检查通过，不能替代服务启动和硬件验证。

### 8.4 部署过程中发现的兼容问题

首次部署包存在以下两类问题。后续部署使用修正后的依赖清单、源码和自检脚本；已上传旧包的设备可按本节修复。

**Vuer 依赖与版本兼容**

Vuer 0.0.70 默认安装不包含全部网页服务依赖，而且未限制的依赖解析安装了 `params-proto 3.3.0`。启动曾出现：

```text
ImportError: cannot import name 'Vuer' from 'vuer'
```

Vuer 会将内部 `ImportError` 隐藏为缺少 aiohttp 的提示，因此仅安装 aiohttp 不足以保证修复。采用下面的依赖组合后，程序继续进入后续初始化阶段：

```bash
cd ~/VR_to_Piper
.runtime/env/bin/python -m pip install "vuer[all]==0.0.70" "params-proto==2.13.1"
```

可以直接检查服务器导入，以显示真实错误：

```bash
.runtime/env/bin/python -c "from vuer.server import Vuer; print('Vuer 导入成功')"
```

**Python 3.11 的 dataclass 数组默认值**

`teleop/mapping/vr_mapper.py` 曾直接将 NumPy 数组作为字段 `P` 的默认值，引发：

```text
ValueError: mutable default <class 'numpy.ndarray'> for field P is not allowed
```

源码需要使用 `field(default_factory=...)`：

```python
from dataclasses import dataclass, field

P: np.ndarray = field(default_factory=lambda: np.array(
    [
        [0.0, 0.0, -1.0],
        [0.0, 1.0, 0.0],
        [1.0, 0.0, 0.0],
    ],
    dtype=float,
))
```

这一修正已在电脑的 Python 3.11 环境中通过配置实例检查。最终发布的部署包应包含修正，避免每次手动修改。

### 8.5 无硬件演练

在 **Jetson SSH 终端**执行：

```bash
cd ~/VR_to_Piper
bash start_jetson.sh --dry-run --can can1
```

`--dry-run` 不连接机械臂、不发送硬件命令。SSH 没有显示环境时跳过 MuJoCo 窗口，保留 VR 服务。

电脑不需要打开可视化网页。**Quest 头显仍需要通过浏览器连接 Jetson 的 VR 服务，并进入 VR 模式，才能发送手柄数据。**

在 Quest 浏览器打开：

```text
https://10.200.2.132:8012/
```

也可以直接使用明确指定 WebSocket 的地址：

```text
https://10.200.2.132:8012/?ws=wss://10.200.2.132:8012
```

IP 应替换为 Jetson 当前地址。保持启动终端运行。

### 8.6 HTTPS 与网络排查

部署生成的是自签名证书。浏览器需要认可证书；正式部署建议使用包含 Jetson 局域网 IP 的受信任证书。

遇到“拒绝连接”时，在 **Jetson SSH 终端**执行：

```bash
hostname -I
ss -ltnp | grep ':8012'
curl -k -v --connect-timeout 5 --max-time 10 https://127.0.0.1:8012/ -o /dev/null
```

本次确认服务监听：

```text
0.0.0.0:8012
```

本地通过 Jetson 局域网 IP 发起的 HTTPS 请求返回：

```text
HTTP/1.1 302 Found
Location: /?ws=wss://10.200.2.132:8012
```

这是自动补充 WebSocket 地址的正常跳转。本地请求成功只能证明 Jetson 服务正常，不能证明 Quest 与 Jetson 网络互通。

若头显仍无法访问：

- 确认地址使用 `https`，并带端口 `8012`。
- 确认 Quest 与 Jetson 网络互通，访客网络或校园网络可能隔离设备。
- 用同一网络中的手机访问相同地址，区分网络问题与 Quest 浏览器问题。
- 根据实际防火墙配置检查规则。本次设备未安装 `ufw`，不需要仅为查询状态而安装它。

### 8.7 USB-CAN 检查

本次交接记录中的 USB-CAN 使用 `gs_usb` 驱动，接口为 **can1**，速率为 **1000000**。Jetson 板载 `can0` 不是此次 USB-CAN 连接对应的接口。

接口名可能变化，启动前应检查：

```bash
ip -brief link
ethtool -i can1
ip -details -statistics link show can1
timeout 5s candump can1
```

确认驱动归属、接口 UP、速率正确，并有实时反馈。`ERROR-ACTIVE` 是正常 CAN 状态名称；历史 RX 计数不能替代实时反馈检查。

已有正确配置时复用接口。不要在其他机械臂控制程序运行时将接口 down，也不要同时运行 PS2 和 VR 控制程序控制同一机械臂。

### 8.8 单臂真机启动

在 **Jetson SSH 终端**执行：

```bash
cd ~/VR_to_Piper
bash start_jetson.sh --can can1
```

当前项目默认支持双臂，`--can can1` 明确选择单臂，由右手柄控制。

真机启动会使能机械臂并进入回零流程。启动前清空运动范围，确认急停可用，并停止其他机械臂控制程序。

需要保存启动日志时：

```bash
bash start_jetson.sh --can can1 2>&1 | tee /tmp/vr-piper-real.log
```

### 8.9 当前验证结果与未解决事项

截至本次部署记录（2026-10-07），已确认：

- Jetson ARM64 依赖安装完成。
- MuJoCo 模型和 DAQP 逆运动学自检通过。
- Jetson HTTPS 服务监听 8012，本地请求正常。
- 后续运行日志收到右手柄握把事件。
- 程序能进入 `TELEOP` / `HOLD`，计算出的关节命令角度随操作变化，循环约为 99 Hz。

**真机运动尚未验证成功。**当前反馈是机械臂不动，提供的日志缺少启动时的 CAN 连接、使能和关节读回信息，尚不能确认是否运行了真机模式，或硬件发送链路是否成功。

`[MODE]` 中的关节角是软件命令角度，不是真机实测反馈。VR 骨架和 IK 正常，也不能证明机械臂已连接或使能。

下一步需要检查启动日志是否包含：

```text
[safety] Enable status: True
[Piper] Ready. (can=can1)
[sender][right] joint readback (rad): ...
```

如果出现 `[DRY RUN]`，说明没有控制硬件；如果出现 `Enable timeout`、`failed` 或异常，应先处理连接问题，再继续操作。查看启动日志前 60 行：

```bash
head -n 60 /tmp/vr-piper-real.log
```
