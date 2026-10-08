# Jetson 部署与运行指南

本节中的安装、启动和检查命令均在外层 `VR_to_Piper` 目录执行，而不是本指南所在的 `piper-quest3-teleop` 子目录。电脑端与 Jetson 端的命令分别标明。

## 1. 设备环境

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

## 2. 上传项目

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

## 3. 一键安装

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

## 4. 部署过程中发现的兼容问题

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

## 5. 无硬件演练

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

## 6. HTTPS 与网络排查

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

## 7. USB-CAN 检查

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

## 8. 单臂真机启动

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

## 9. 当前验证结果与未解决事项

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
