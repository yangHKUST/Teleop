# 迁移部署 + Quest 3 配对说明

> 目标读者：把 `piper-quest3-teleop` 迁到一台**新主机**、并重新打通 Quest 3 的工程师。
> 本文只讲「迁移后怎么把环境配好」+「Quest 3 怎么连」；**运行时的 VR 操作方式见 [README.zh-CN.md](./README.zh-CN.md)**（握把=使能、扳机=夹爪、A=回零）。
>
> 下文所有路径、环境名、IP 都以**原主机实测值**为准，换机后需要按新主机实际情况替换。

---

## 一、迁移的是什么

| 内容 | 说明 |
|---|---|
| 代码目录 | `piper-quest3-teleop/`（**不是 git 仓库**，直接整目录拷贝即可） |
| 依赖清单 | `requirements.txt`（唯一安装依据，已在新机实测逐项对上） |
| 启动脚本 | `run_teleop.sh`（会做环境隔离 + 自检，**必须用它启动**，不要裸 `python -m ...`） |
| 主程序入口 | `teleop/teleop_real_arm.py`（脚本里 `python -m teleop.teleop_real_arm "$@"`） |
| 机器人模型 | `teleop/piper/agilex_piper/piper.xml`（MuJoCo MJCF，6 关节 + 夹爪 2 关节） |
| 自签名证书 | `teleop/cert.pem` + `teleop/key.pem`（**换 IP 后必须重签**，见第八节） |

`act/` 子目录是 ACT 模仿学习训练部分（依赖 torch + 单独环境 `aloha`，Python 3.9），**遥操作本身用不到它**，迁移时一并拷走即可，不用配它的环境。

---

## 二、拷贝代码到新主机

任意方式整目录拷贝，例如：

```bash
# 在原主机打包
tar czf piper-quest3-teleop.tgz piper-quest3-teleop/

# 到新主机解压到任意位置（下文以 ~/piper-quest3-teleop 为例）
scp piper-quest3-teleop.tgz user@新主机IP:~/
ssh user@新主机IP 'tar xzf piper-quest3-teleop.tgz'
```

> ⚠️ `.gitignore` 里写了 `*.pem`，所以**如果走 git 迁移，证书不会被带过去**；请确认 `teleop/cert.pem`、`teleop/key.pem` 两个文件都在（缺少就按第八节直接生成）。

---

## 三、系统前提

- **OS**：Ubuntu 22.04 x86_64（实测环境）。
- **miniconda**：路径必须是 `~/miniconda3`（`run_teleop.sh` 里写死 `source "$HOME/miniconda3/etc/profile.d/conda.sh"`）。如果新主机装在别处，改这一行。
- **CAN 硬件**：两块 Piper 臂各一路 CAN。原主机约定 **左臂 = `can0`，右臂 = `can1`**（USB-CAN 转接器或板载 CAN 均可）。
- **GPU（可选）**：遥操作本身不需要 CUDA；只有 `act/` 训练才需要 NVIDIA 驱动 + torch cu121。
- **Quest 3**：与主机**同一局域网/WiFi**。

---

## 四、创建 conda 环境

环境名固定叫 `piper-teleop`（脚本里 `conda activate piper-teleop` 写死），Python 3.10：

```bash
conda create -n piper-teleop python=3.10 -y
conda activate piper-teleop
```

---

## 五、安装 Python 依赖

```bash
cd ~/piper-quest3-teleop
pip install -r requirements.txt
```

关键版本（原主机实测，与 `requirements.txt` 完全一致）：

| 包 | 版本 | 备注 |
|---|---|---|
| python | 3.10 | 环境 |
| numpy / scipy | 1.23.0 / 1.10.1 | **必须被隔离**（见第六节） |
| mujoco | 3.13.0 | 由 `mink` 依赖自动装出，若装到其它版本可手动 `pip install mujoco==3.13.0` |
| mink | 0.0.13 | IK 求解 |
| vuer | 0.0.70 | VR 服务端（含 Quest 客户端） |
| piper-sdk | 0.6.1 | Piper 臂 CAN 驱动 |
| python-can | 4.5.0 | socketcan |
| opencv-python | 4.9.0.80 | 相机流（`--camera` 才用） |
| torch / torchvision | 2.3.0 / 0.18.0 | 仅 ACT 训练用 |

> **torch 说明**：`requirements.txt` 里 `torch==2.3.0` 从 PyPI 装是 CPU 版。遥操作**不 import torch**，纯遥操作用 CPU 版即可；要跑 `act/` 训练再按需补 CUDA 版：
> ```bash
> pip install torch==2.3.0 torchvision==0.18.0 --index-url https://download.pytorch.org/whl/cu121
> ```

---

## 六、环境隔离（关键，否则跑不起来或报错很误导）

`run_teleop.sh` 开头会做三件事，**不要绕过它裸跑 python**：

```bash
unset PYTHONPATH            # 去掉 ROS(如 /opt/ros/humble) 的 site-packages 污染
export PYTHONNOUSERSITE=1   # 去掉 ~/.local（常被 numpy 2.x / opencv 5 污染）
conda activate piper-teleop
```

原主机出过的问题：`~/.local` 里装了 **numpy 2.2.6 / opencv 5**，一旦没隔离就会让 mink/mujoco 报错，报错信息还指向别处。新主机如果也有 `pip install --user` 装过东西，务必用脚本启动。

自检（脚本里也有）：`python -c "import mujoco, mink, vuer, piper_sdk"` 应无报错。

---

## 七、CAN 接口配置

两块臂的 CAN 口默认 **1 Mbps**（原主机 `can0` 实测 `bitrate 1000000`）。新主机首次需把接口拉起来：

```bash
sudo ip link set can0 type can bitrate 1000000
sudo ip link set can1 type can bitrate 1000000
sudo ip link set can0 up
sudo ip link set can1 up
# 验证
ip -details link show can0 | grep bitrate
candump can0   # 能看到臂的 CAN 报文即通
```

两个注意点：

1. **权限**：程序通过 `piper_sdk` 打开 CAN **raw socket**，需要 root 或 `CAP_NET_RAW`。报 `Permission denied` 时：
   - 用 `sudo ./run_teleop.sh ...`（注意 sudo 下要保证 conda 环境仍能激活：`sudo -E` 或给 sudo 保留 HOME），或
   - `sudo setcap cap_net_raw,cap_net_admin+eip "$(conda run -n piper-teleop which python)"`（**setcap 后不要再动该 conda 环境**，否则二进制被替换会失效）。
2. **命名一致性**：多块 USB-CAN 转接器插拔顺序可能让 `can0/can1` 对调。建议用 udev 规则按转接器序列号固定设备名，避免「左臂跑成右臂」。启动参数 `--can-left can0 --can-right can1` 要和实际接法对上。

---

## 八、自签名证书重签（**IP 变了必须做**）

`TeleVision.py` 会按自身目录解析 `./cert.pem`、`./key.pem`，用自签名证书起 **https**（端口 `8012`）。原证书 SAN 里写死 `localhost / 127.0.0.1 / 10.200.0.222` 三个名字，**换到新主机（新 IP）后浏览器会因证书不匹配反复报错，且 WebSocket/手柄数据可能拿不到**，需要按新 IP 重签：

```bash
cd ~/piper-quest3-teleop/teleop
# 把 NEW_IP 换成新主机实际 IP（如 192.168.1.50）
openssl req -x509 -newkey rsa:2048 -nodes \
  -keyout key.pem -out cert.pem -days 825 \
  -subj "/CN=piper-teleop" \
  -addext "subjectAltName=DNS:localhost,IP:127.0.0.1,IP:NEW_IP"
```

生成后确认：

```bash
openssl x509 -in cert.pem -noout -subject -ext subjectAltName -dates
```

> 证书只用于让 Quest 浏览器建立加密的 WebSocket，不影响机械臂控制。`*.pem` 在 `.gitignore` 里，属本机私有文件，别提交。

---

## 九、自检

```bash
cd ~/piper-quest3-teleop
./run_teleop.sh --dry-run
```

- `--dry-run` 是**纯仿真**：不连 CAN、不给真臂发任何命令，只开 MuJoCo viewer + VR 服务。用它验证「环境 OK + Quest 能连上」最安全。
- 若报 `[ERROR] 依赖缺失`，说明环境没建好或没走脚本启动。
- `--dry-run` 要开 MuJoCo 可视化窗口，**需要图形界面**（X11/Wayland）；真机模式（`--can ...`）不需要显示器，头显里的骨架 overlay 就是「屏幕」。

---

## 十、启动（先仿真，后真机）

```bash
# ① 仿真：验证按键映射 / Quest 连接，不碰真机
./run_teleop.sh --dry-run

# ② 真机（双臂）：左臂 can0、右臂 can1 —— 确认机械臂已上电、处于安全位姿后再跑
./run_teleop.sh --can-left can0 --can-right can1

# 兼容旧单臂用法：--can 同时作用于左右
./run_teleop.sh --can can0

# 可选：开相机流（ZED/USB，Quest 里显示背景画面）
./run_teleop.sh --can-left can0 --can-right can1 --camera 0
```

> **安全底线**：真机模式会 `EnableArm` 并持续下发关节命令。第一次上真机务必：机械臂上电、工作范围内无人、随时准备按急停 / Ctrl+C（退出时会尽力把臂回零）。

---

## 十一、Quest 3 配对流程

1. **查主机 IP**（和 Quest 同一 WiFi 下）：
   ```bash
   ip -4 addr show   # 无线网卡通常是 wlo1；或 hostname -I
   ```
2. **先启动程序**（`--dry-run` 即可，VR 服务 `8012` 端口会随程序一起起）。确认端口在监听：
   ```bash
   ss -tlnp | grep 8012
   ```
3. **Quest 3 打开浏览器**（Meta Quest Browser），地址栏输入：
   ```
   https://<主机IP>:8012
   ```
   例：`https://10.200.0.222:8012`（换成第二步查到的 IP）。

4. **证书警告**：因为自签名证书，浏览器弹「不安全/证书错误」→ 点「高级」→「继续前往」（首次允许一次）。证书 SAN 已包含新 IP 就不会反复跳警告。

5. **自动重定向（不用手动做任何事）**：本项目已在服务端加了中间件（`TeleVision.py::_make_ws_redirect_middleware`），vuer 0.0.70 客户端 https 丢端口的 bug 会被自动修掉——打开上面的地址后，服务器会自动把地址补成 `/?ws=wss://<IP>:8012`。**不要**手动加 `?ws=` 参数，直接开 `https://<IP>:8012` 即可。

6. **确认连上**：
   - 服务器日志出现 `websocket is connected`；
   - **左右晃动两下手柄**，让浏览器把手柄识别出来（服务器日志会出现 `rightState keys=...` 的每秒 debug 输出，含 `squeeze/trigger/aButton`）。

7. 连上后 Quest 里应看到：
   - 背景 = 相机流（没开 `--camera` 时是黑屏，**属正常**）；
   - 机械臂**骨架 overlay**（遥操作时叠加显示各关节位置，判断当前姿态）；
   - 两只手柄的位置。

> 之后的操作（握把按住=臂动、扳机=夹爪、A=回零、增量映射）见 [README.zh-CN.md](./README.zh-CN.md) 第 3、4 节。

---

## 十二、上真机前检查清单

- [ ] `./run_teleop.sh --dry-run` 能起、Quest 能看到骨架和手柄。
- [ ] `can0` / `can1` 已 `up`，`candump` 能收到臂的报文，左右臂接法和 `--can-left/--can-right` 一致。
- [ ] 证书 SAN 含当前主机 IP（`openssl x509 -in teleop/cert.pem -noout -ext subjectAltName`）。
- [ ] 机械臂上电，处于安全位姿（关节零位附近），工作范围内无人，急停可达。
- [ ] 夹爪方向对：默认「抠扳机=闭合、松开=张开」，反了改 `teleop/config.py` 的 `GRIP_INVERT` / `gripper_close_when_high`。

---

## 十三、常见问题排查

| 现象 | 处理 |
|---|---|
| Quest 浏览器打不开页面 | 确认 IP 对、`ss -tlnp \| grep 8012` 在监听、Quest 与主机同网段 |
| 浏览器反复报证书错 | 证书 SAN 没含当前 IP，按第八节重签 |
| VR 里一片黑 | 没开 `--camera`，背景本来就是黑的；骨架和手柄仍在 |
| 机械臂不动 | 确认在 TELEOP 模式（要**按住握把**）；先晃手柄确认已被浏览器识别 |
| 连接 CAN 报 `Permission denied` | 用 sudo 跑或 `setcap cap_net_raw,cap_net_admin`（见第七节） |
| `[ERROR] 依赖缺失` | 没走 `./run_teleop.sh`，或被 `~/.local`/ROS 污染，见第六节 |
| 机械臂方向/幅度不对 | 查 `teleop/mapping/vr_mapper.py` 的 `VRMapperConfig.P`（轴映射）与 `position_scale` |
| 乱跳/抖 | 松握把不够干脆、或手在零点附近抖；按 A 回零重来；抖可调 `teleop/config.py` 的 `POSE_*` 滤波参数 |
