# OpenArm 进阶参考：MoveIt、示教与诊断

新用户请先阅读[项目部署与 VR 操作指南](../../README.md)。本页保留原有进阶资料，其中耗时和版本兼容性记录来自原开发机，不能作为新机器上的性能保证。

以下旧命令里的 `~/ros2_ws` 指你的实际工作区；本项目默认路径为 `~/Teleop/VR_to_Openarm/ros2_ws`。

本工作区提供 OpenArm v1.0 双臂机械臂的 ROS 2 集成，包含：双臂 bringup（ros2_control + CAN 驱动）、MoveIt 运动规划、RViz 可视化，以及支持**双臂同时规划与执行**的自定义配置。

- 机器人：OpenArm v1.0，7 自由度双臂 + 各一个夹爪（共 14 个臂关节 + 2 个手指关节）
- 环境：ROS 2 **Humble**，Ubuntu 22.04
- 工作区：`~/ros2_ws`

---

## 1. 工作区结构

| 目录 / 包 | 说明 |
|---|---|
| `src/openarm_ros2/openarm` | 元包（metapackage） |
| `src/openarm_ros2/openarm_hardware` | ros2_control 硬件接口，通过 CAN-FD 驱动达妙电机 |
| `src/openarm_ros2/openarm_bringup` | 启动文件 + 控制器参数 |
| `src/openarm_ros2/openarm_bimanual_moveit_config` | MoveIt 双臂规划配置（含 v1.0 / v2.0） |
| `src/openarm_description` | URDF / Xacro 模型描述 |
| `src/openarm_can` | CAN 通信底层库 |
| `src/bio_ik` | 多自由度 IK 解算器（PickNik fork，ros2 分支） |
| `src/pick_ik` | 单链 IK 解算器（PickNik，Pinocchio 内核，源码编译；供 left/right arm） |
| `src/openarm_ros2/openarm_acm_tool` | 双臂自碰撞矩阵（allowed collision matrix）生成器 |
| `src/openarm_ros2/openarm_bimanual_planner_msgs` | 协同 B-spline 规划器的 action 接口定义 |
| `src/openarm_ros2/openarm_bimanual_planner` | 协同双臂 B-spline 规划器（14 自由度 + 自碰撞，独立 action 节点） |

关节命名：左臂 `openarm_left_joint1..7`、右臂 `openarm_right_joint1..7`，夹爪 `openarm_left/right_finger_joint1`。

---

## 2. 编译

```bash
source /opt/ros/humble/setup.bash
cd ~/ros2_ws
colcon build
source ~/ros2_ws/install/setup.bash
```

> 首次编译包含 `bio_ik`，耗时较长（约半分钟）；之后可只编译变更的包：
> ```bash
> colcon build --packages-select openarm_bringup openarm_bimanual_moveit_config
> ```

---

## 3. 启动方式

### 3.1 拉起 CAN 接口（仅真实硬件需要）

本机的 CAN 硬件是 **PEAK PCAN-USB Pro FD**（USB `0c72:0011`）——一块**双通道** USB CAN-FD 适配器，走内核主线驱动 `peak_usb`（子驱动 `pcan_usb_pro_fd`），**不是**官方 OpenArm CAN 设备。插入后内核自动创建两个接口 `can0` / `can1`（一个物理通道对应一个）。

用标准 `ip` 命令拉起（默认右臂 `can0`、左臂 `can1`）：

```bash
# 双通道：1Mbps 仲裁 / 5Mbps 数据、CAN-FD（与硬件接口 can_fd=true 匹配）
# 先 down 再 up：接口已 UP 时直接改 bitrate 会报 "Device or resource busy"
sudo ip link set can0 down && sudo ip link set can0 up type can bitrate 1000000 dbitrate 5000000 fd on
sudo ip link set can1 down && sudo ip link set can1 up type can bitrate 1000000 dbitrate 5000000 fd on
```

拉起后验证：

```bash
ip -details link show type can    # 应看到 can0/can1 <UP>、FD、bitrate/dbitrate 正确
candump can0                      # 监听总线，确认能收到电机回传帧
```

电机诊断仍可用 `openarm-can-cli`（它只走 SocketCAN，与适配器品牌无关）：

```bash
openarm-can-cli -i can0 discover  # 扫描总线上已连接的电机
openarm-can-cli -i can0 monitor   # 实时监控 pos/vel/torque/temp
openarm-can-cli -i can0 diagnose  # 诊断电机状态 / 错误码
```

> - 命令需 root 权限，故加 `sudo`。
> - 硬件接口固定启用 CAN-FD（xacro 默认 `can_fd=true`），上面的 `fd on` 必须保留，不要改用 Classic CAN。
> - **通道 ↔ 手臂的对应**：launch 默认右臂 `can0`、左臂 `can1`。PCAN-USB Pro FD 的两个物理通道（CH1/CH2）分别枚举为 `can0`/`can1`，具体哪根线接哪条臂由你的接线决定；若左右臂反了，交换接线，或在 launch 里对调 `right_can_interface` / `left_can_interface`。
> - 接口名 `can0`/`can1` 按枚举顺序分配、不跨重启保证固定。要稳定绑定可在 `/etc/systemd/network/` 写 `.link`（按 USB 路径 `parentdev`）或用 udev 规则；默认顺序通常稳定，够用即可。

### 3.2 仅可视化（RViz 看模型、拖关节，不驱动硬件）

```bash
ros2 launch openarm_description display_openarm.launch.py arm_type:=v10
```

用 `joint_state_publisher_gui` 手动拖动关节查看模型。

### 3.3 双臂 bringup（ros2_control）

**仿真模式（假硬件，无需机械臂/CAN）**：                                       

```bash
ros2 launch openarm_bringup openarm.bimanual.launch.py \
  arm_type:=v10 use_fake_hardware:=true
```

**真实硬件（先按 3.1 拉起 CAN，默认左臂 can1、右臂 can0）**：

```bash
ros2 launch openarm_bringup openarm.bimanual.launch.py \
  arm_type:=v10 use_fake_hardware:=false \
  right_can_interface:=can0 left_can_interface:=can1
```

常用参数：

| 参数 | 默认值 | 说明 |
|---|---|---|
| `arm_type` | `openarm_v2.0` | 手臂型号，**v1.0 必须传 `v10`/`v1.0`** |
| `use_fake_hardware` | `true` | `true`=假硬件，`false`=真实 CAN |
| `robot_controller` | `joint_trajectory_controller` | 或 `forward_position_controller` |
| `right_can_interface` / `left_can_interface` | `can0` / `can1` | 左右臂 CAN 接口 |
| `gravity_scale` | `0.0` | 重力补偿前馈倍率（`0.0`=关，`1.0`=满），见 3.5 |
| `teaching_mode` | `false` | `true`=带重力补偿的拖动示教模式，见 3.5 |

> ⚠️ 注意：`openarm_bringup/README.md` 里写的 `openarm.launch.py`（单臂）和 `hardware_type:=real` 在当前代码中**并不存在**。实际只有 `openarm.bimanual.launch.py`（双臂），参数是 `use_fake_hardware`。

### 3.4 MoveIt 双臂规划 + 执行（重点）

**仿真模式（假硬件，不驱动真实机械臂）**：

```bash
ros2 launch openarm_bimanual_moveit_config demo.launch.py \
  arm_type:=v10 use_fake_hardware:=true
```

**真实硬件（先按 3.1 拉起 CAN，再 `use_fake_hardware:=false`）**：

```bash
ros2 launch openarm_bimanual_moveit_config demo.launch.py \
  arm_type:=v10 use_fake_hardware:=false \
  right_can_interface:=can0 left_can_interface:=can1
```

这一步一次性拉起：`robot_state_publisher`、`ros2_control_node`、`move_group`、`rviz2`，并自动 spawn `joint_state_broadcaster`、`both_arms_joint_trajectory_controller`（双臂联合控制器）、左右 `gripper_controller`。

> ⚠️ `use_fake_hardware:=true` 是**假硬件**（`mock_generic_system`），真实机械臂不会被驱动；要动真机必须 `:=false`。

### 3.5 带重力补偿的示教模式（拖动示教）

硬件接口在 MIT 控制律上叠加了 Pinocchio 重力补偿前馈：

```
tau = kp*(q_des - q) + kd*(dq_des - dq) + tau_ff
tau_ff = clamp(gravity_scale * G(q) + offset, ±TMAX)
```

`G(q)` 由 v1.0 URDF 实时计算。`gravity_scale = 1.0` 时 PD 环不再对抗重力，稳态下垂 `G(q)/kp` 被抵消，手臂能悬停。

**示教模式**（`teaching_mode:=true`）用于人手拖动示教：

```bash
ros2 launch openarm_bringup openarm.bimanual.launch.py \
  arm_type:=v10 use_fake_hardware:=false teaching_mode:=true
```

- **拖动中**（任一关节转速 > `teaching_drag_vel`）：位置弹簧放开（`kp=0`），只剩粘性阻尼 + 满重力补偿，手臂可被手自由带动。
- **松手**（各关节转速 < `teaching_hold_vel`）：恢复正常刚度弹簧并锁在松手处，靠重力补偿稳定悬停、不往下掉。

示教模式是**启动参数**（Humble 硬件组件没有运行时参数服务），切换需要重启 launch。

**微调残余下垂**：重力模型若偏轻，松手后会有轻微下垂，稳态关系 `sag = ΔG / kp`（ΔG = 真实重力 − 模型重力）。三个旋钮，在 `openarm_description` 的 `openarm.bimanual.ros2_control.xacro` 左右两个 `<hardware>` 块里加 `<param>`：

| 参数 | 默认 | 作用 |
|---|---|---|
| `teaching_gravity_scale` | `1.0` | 前馈倍率，`>1` 补偿「模型偏轻」的全局误差 |
| `teaching_hold_kp_scale` | `1.0` | 保持弹簧倍率，`>1` 松手后夹得更紧 |
| `gravity_tau_offset1..7` | `0.0` | **逐关节**力矩偏移（Nm），精确只补个别下垂关节 |

```xml
<param name="teaching_gravity_scale">1.04</param>
<param name="teaching_hold_kp_scale">1.2</param>
<param name="gravity_tau_offset3">0.8</param>
```

- **全局都往下掉** → 调 `teaching_gravity_scale`：1.0 → 1.03 → 1.05 小步加。
- **只有个别关节掉** → 调 `gravity_tau_offsetN`：看启动日志 `gravity tau_ff (Nm): ...` 那行确定该关节 `G(q)` 的符号和量级，往下垂就加**同号**小偏移（~0.1 Nm 起步）。
- 前馈逐关节有 ±[54, 54, 28, 28, 10, 10, 10] Nm 钳位；这仅限制前馈项，不能保证 PD 与前馈合成的总力矩或运动安全；`teaching_gravity_scale` 不建议超过 ~1.1，否则臂会自己上飘/振荡。

使用 `--symlink-install` 构建且安装文件链接到源码时，修改 xacro 后重启 launch 生效；若为复制安装，先重新编译 `openarm_description` 并 source 工作区。

---

## 4. MoveIt 双臂规划怎么用

1. 启动后，RViz 左侧 **MotionPlanning** 面板。
2. **Planning Group** 选择 `both_arms`。
3. 在 **Planning Request** 区域会出现 **14 个关节滑块**（左右臂各 7 个），分别拖动设目标角度。
4. 勾选 **Query Goal State** → 点 **Plan** → **Execute**，两条臂通过 `both_arms_joint_trajectory_controller` 一次性协同执行。

**Goal State 下拉框** 提供命名姿态：

- `home`：14 关节全 0（初始姿态，规划不会看到移动）
- `hands_up`：双臂 joint4 = 2（有明显动作，适合演示）

**关于 3D 交互标记**：RViz 会显示**两个可拖小球**（左右臂末端各一个），可同时拖两条臂、再一起 Plan & Execute。之所以是两个，是因为 `both_arms` 组在 `kinematics.yaml` 里**不设自己的 IK 解算器**——MoveIt 于是落到子组 `left_arm` / `right_arm`（各带 pick_ik），每个臂放一个标记；若给 `both_arms` 配上解算器，就会退回只放一个标记（锚在右臂上）。

- 只想拖**单臂**：把 Planning Group 切到 `left_arm` 或 `right_arm`。

---

## 5. 本项目对 MoveIt 的双臂改造

为了让「一次 Plan & Execute 驱动两条臂」，在原基础上做了如下改动：

1. **新增 `both_arms` 规划组**（`openarm_bimanual.srdf`）：由 `left_arm` + `right_arm` 子组组成，并补了 `home` / `hands_up` 命名姿态。
2. **新增双臂联合控制器** `both_arms_joint_trajectory_controller`（14 关节），替换了原来的 `left/right_joint_trajectory_controller`（二者会争抢左臂 command interface）。
3. **MoveIt 控制器映射** 改为 `both_arms_joint_trajectory_controller → FollowJointTrajectory`；夹爪控制器保留。
4. **IK 解算器**：
   - `left_arm` / `right_arm`：`pick_ik/PickIkPlugin`（基于 Pinocchio 的单链求解器，比 KDL 更快更稳）
   - `both_arms`：**不设自己的 IK 解算器**。这样 RViz 才会对 `both_arms` 显示两个拖拽标记（左右臂各一）。代价是不能再对 `both_arms` 整体 `setPoseTarget()`（编程式单目标位姿会失败）；若以后要恢复整体位姿规划，把 `bio_ik/BioIKKinematicsPlugin` 条目加回 `kinematics.yaml`（但会退回单小球）。

关键文件：

| 文件 | 作用 |
|---|---|
| `src/openarm_ros2/openarm_bimanual_moveit_config/config/openarm_v1.0/openarm_bimanual.srdf` | 规划组 / 命名姿态 |
| `src/openarm_ros2/openarm_bimanual_moveit_config/config/openarm_v1.0/kinematics.yaml` | IK 解算器 |
| `src/openarm_ros2/openarm_bimanual_moveit_config/config/openarm_v1.0/moveit_controllers.yaml` | MoveIt → 控制器映射 |
| `src/openarm_ros2/openarm_bringup/config/controllers/openarm_bimanual_moveit_controllers.yaml` | ros2_control 控制器参数 |
| `src/openarm_ros2/openarm_bimanual_moveit_config/launch/demo.launch.py` | demo 启动文件 |

---

## 6. 协同 B-spline 规划器（独立 action 节点）

与 MoveIt 并存的一套**双臂协同规划器**（移植自 `openarm_pinocchio_nsp`）。输入双臂末端目标，输出**平滑、同步、自碰撞规避**的 14 自由度轨迹，直接下发给 `both_arms_joint_trajectory_controller`。

**与 MoveIt 的区别**：这里的 B-spline 节点采用另一套优化流程。MoveIt 也支持碰撞检测和双臂联合规划；两者的平滑程度、规划速度和效果需按实际任务比较。

| 包 | 说明 |
|---|---|
| `openarm_bimanual_planner_msgs` | action 接口定义（`BimanualPlan.action`） |
| `openarm_bimanual_planner` | 规划器本体：`BimanualBSplinePlanner` + 碰撞检测 + action server/client |

### 6.1 依赖环境（一次性，必须先建 venv）

规划器用 Pinocchio + numpy<2。系统 `numpy 2.x` 与 `ros-humble-pinocchio` 的 numpy1 ABI 冲突，必须用专用 venv：

```bash
/usr/bin/python3 -m venv --system-site-packages ~/venv-openarm-ik
source ~/venv-openarm-ik/bin/activate
pip install "numpy<2" scipy
```

> `--system-site-packages` 让 venv 里的 `import pinocchio` 落到系统 `ros-humble-pinocchio`（PyPI 上的 `pinocchio` 是无关的同名包，别 pip 装它）。

### 6.2 编译

**必须用 venv python 编译**，否则 entry-point 的 shebang 指向系统 python 会崩：

```bash
cd ~/ros2_ws
source /opt/ros/humble/setup.bash
source ~/venv-openarm-ik/bin/activate
~/venv-openarm-ik/bin/python -m colcon build \
  --packages-select openarm_bimanual_planner_msgs openarm_bimanual_planner --symlink-install
```

### 6.3 使用

先按第 3.3 / 3.4 节把双臂带起来（真机或仿真均可，`joint_state_broadcaster` + `both_arms_joint_trajectory_controller` 已在跑）。再开两个终端：

```bash
# 终端 A：规划 server（常驻，必须先开）
source /opt/ros/humble/setup.bash && source ~/ros2_ws/install/setup.bash && source ~/venv-openarm-ik/bin/activate
ros2 run openarm_bimanual_planner bimanual_plan_server

# 终端 B：发目标（一次性，每要动一次就敲一次）
source /opt/ros/humble/setup.bash && source ~/ros2_ws/install/setup.bash && source ~/venv-openarm-ik/bin/activate
ros2 run openarm_bimanual_planner bimanual_plan_client --left "0.40,0.10,0.35" --right "0.40,-0.10,0.35" --duration 4.0
```

- `--left` / `--right`：左右末端目标位置（米，`x,y,z`），首期只用位置、忽略朝向。
- `--duration`：期望时长（秒），`0` = 默认 4.0。
- 流程：server 读 `/joint_states` 当前姿势 → B-spline 规划（含自碰撞）→ 发布轨迹到 `both_arms_joint_trajectory_controller` → 电机动。

### 6.4 已知限制

1. **慢**：单次规划约 **80 秒**（SLSQP 数值梯度 × 14×10 控制点）。server 参数 `time_budget`（默认 120s）可调，也可调小 `maxiter`/`n_samples` 换速度。
2. **只防自碰撞**：内置 163 对（跨臂 95 + 臂自 54 + 臂↔体 14），不处理外部障碍物。
3. **只认位置**：目标朝向暂忽略。
4. **发目标目前是 CLI**：接 RViz 拖拽 / 上层接口是后续里程碑。

---

## 7. 双臂同时到位姿（两个拖拽标记）

RViz 现在对 `both_arms` 显示两个拖拽标记（见第 4 节），直接同时拖两条臂即可实现双臂同时到位姿，再 Plan & Execute 一次执行。程序化（代码里）同时约束两个末端位姿：当前 `both_arms` 无整体 IK，可对 `left_arm`/`right_arm` 分别 `setPoseTarget` 后一起规划，或改用第 6 节的 B-spline 规划器（推荐）。

---

## 8. 注意事项 / 已知限制

1. **默认型号是 v2.0**：所有 launch 的 `arm_type` 默认 `openarm_v2.0`，用 v1.0 时务必加 `arm_type:=v10`。
2. **bio_ik 来源**：ROS2 版 bio_ik 在 [PickNikRobotics/bio_ik](https://github.com/PickNikRobotics/bio_ik) 的 `ros2` 分支（原厂 [TAMS-Group/bio_ik](https://github.com/TAMS-Group/bio_ik) 只有 ROS1 的 master）。
3. **miniconda 库阴影**：本机 `~/miniconda3/lib` 可能遮蔽系统 `libgomp` / `libcurl`。若 bio_ik 插件加载时报 `undefined symbol` 或 `libgomp` 错误，先 `unset LD_LIBRARY_PATH` 或 `conda deactivate` 再启动。
4. **bio_ik 现状**：`both_arms` 已不再使用 bio_ik（见第 5 节）。若重新启用，推荐 `mode: bio2_memetic`（全局，最稳，较慢）；拖拽卡顿可改 `gd_c` 或 `jac`（更快、局部）。
5. **单臂规划仍可用**：`both_arms_joint_trajectory_controller` 设了 `allow_partial_joints_goal: true`，所以用 `left_arm` / `right_arm` 组单独规划执行也兼容。
6. **pick_ik 需源码编译**：apt 的 `ros-humble-pick-ik` 与本机 MoveIt 2.5.9 ABI 不匹配（插件 dlopen 失败），故采用源码编译（`src/pick_ik`，tag 1.1.2）。构建参数已固化在根目录 `colcon.meta`（关闭测试 + 强制系统 fmt）；全新环境若没有 `colcon.meta`，需手动加 `-DBUILD_TESTING=OFF -Dfmt_DIR=/usr/lib/x86_64-linux-gnu/cmake/fmt`。

---

## 9. 快速命令速查

```bash
source /opt/ros/humble/setup.bash
source ~/ros2_ws/install/setup.bash

# 拉起 CAN 接口（真机，PEAK PCAN-USB Pro FD，双通道 CAN-FD）
sudo ip link set can0 down && sudo ip link set can0 up type can bitrate 1000000 dbitrate 5000000 fd on
sudo ip link set can1 down && sudo ip link set can1 up type can bitrate 1000000 dbitrate 5000000 fd on

# 只看模型
ros2 launch openarm_description display_openarm.launch.py arm_type:=v10

# 双臂 bringup（仿真）
ros2 launch openarm_bringup openarm.bimanual.launch.py arm_type:=v10 use_fake_hardware:=true

# 带重力补偿的示教模式（真机，拖动示教，见 3.5）
ros2 launch openarm_bringup openarm.bimanual.launch.py arm_type:=v10 use_fake_hardware:=false teaching_mode:=true

# MoveIt 双臂规划 + 执行（仿真）
ros2 launch openarm_bimanual_moveit_config demo.launch.py arm_type:=v10 use_fake_hardware:=true

# MoveIt 双臂规划 + 执行（真机）
ros2 launch openarm_bimanual_moveit_config demo.launch.py arm_type:=v10 use_fake_hardware:=false right_can_interface:=can0 left_can_interface:=can1

# 使能/不使能开关（手动，空格切换，q 退出）
openarm-can-enable-switch can0 can1
```

---

## 10. 使能 / 不使能开关（手动安全开关）

独立工具 `openarm-can-enable-switch`，直接通过 SocketCAN 控制所有电机：

- **不使能（默认）**：电机自由转动，手臂可随意推动
- **使能**：电机锁定并保持在**切换瞬间的位置**（MIT 位置保持）
- **空格**切换，`q` / `ESC`（或 `Ctrl-C`）退出；退出时自动回到不使能

```bash
# 双臂（默认 can0=右、can1=左）
openarm-can-enable-switch can0 can1

# 单臂
openarm-can-enable-switch can0
```

> ⚠️ 这个工具**直接占用 CAN 总线**，不能与 ros2_control / MoveIt 真机模式同时运行（会抢总线）。要先用它，再退出后启动 MoveIt，或反过来。
> 使能时会用 `kp/kd` 锁在当前角度；若手臂处于重力下垂姿态，锁住的即下垂后的位置。

---

## 11. 调试 / 诊断 / 标定工具（openarm_can）

`openarm_can` 除作为底层库外，还构建并安装了一批独立命令行工具（`colcon build` 后 source 环境即可直接用）：

| 工具 | 说明 | 占用 CAN 总线 |
|---|---|---|
| `openarm-can-cli` | 电机配置 + 诊断的通用 CLI（见下） | 是 |
| `openarm-can-health` | **只读**健康监视：打印 pos/vel/torque/temp 及其变化，**不使能电机**（臂不会动），可安全长跑；`--toggle` 会每秒使能/不使能一次以统计响应 | 是（但只读） |
| `openarm-can-enable-switch` | 手动使能/不使能开关（见第 10 节） | 是 |
| `openarm-can-demo` | 完整臂控制 demo | 是 |
| `openarm-can-motor-sampling-check` | 电机采样 / 回传检查 | 是 |
| `openarm-can-zero-position-calibration` | 零位标定：依次把各关节运动到机械限位确定零点（`--arm-side right_arm\|left_arm --robot-version v1\|v2`，默认 can0=右 / can1=左） | 是 |
| `openarm-can-calibration-in-cell` | 带升降台的零位标定：先升台到顶，再跑上面同一个标定序列 | 是 |
| `openarm-can-configure-socketcan-4-arms` | SocketCAN 接口配置脚本（官方 CAN 硬件用，`-fd` 开 CAN-FD） | 否 |

`openarm-can-cli` 常用子命令：

```bash
openarm-can-cli -i can0 can_configure                     # 配置接口（默认 1M 仲裁/5M 数据，CAN-FD）
openarm-can-cli -i can0 can_configure -d 1000000 --no-fd  # 改成 Classic CAN 1Mbps
openarm-can-cli -i can0 discover                          # 扫描总线上的电机
openarm-can-cli -i can0 monitor --id 1,2,3                # 监控指定电机 pos/vel/torque/temp
openarm-can-cli -i can0 diagnose                          # 诊断电机状态 / 错误码
openarm-can-cli -i can0 set_zero                          # 把当前位置设为机械零点（标定动作）
openarm-can-cli -h                                        # 完整子命令列表
```

> ⚠️
> - 除 `health`（只读、不使能、臂不动）外，其余工具都**直接占用 CAN 总线**，不能与 ros2_control / MoveIt 真机模式同时运行。
> - `set_zero` 会改写电机零点，属标定动作，误用会改变关节零位；正式标定请优先用 `openarm-can-zero-position-calibration`。
> - 本机 CAN 是 PEAK PCAN-USB Pro FD，接口用第 3.1 节的 `ip link` 命令拉起即可；`openarm-can-configure-socketcan-4-arms` 是给官方 CAN 硬件用的，二者效果等价。
> - Python 绑定 `openarm_can`（`import openarm_can as oa`）目前标记为 🚧 EXPERIMENTAL，接口可能大变、不保证稳定。
> - 各控制模式最小示例（`mit` / `posvel` / `vel` / `posforce` / `gripper_posforce`）会编译成 `build/openarm_can/openarm-can-example-*`，但**不安装**到 `bin/`，需要时直接从 build 目录运行。

---

## 12. 自碰撞矩阵生成（openarm_acm_tool）

`openarm-generate-acm` 通过对可达位形做均匀随机采样，生成双臂的**自碰撞矩阵**（`<disable_collisions>` 片段），避免 MoveIt 规划时把同臂不相邻连杆/躯干误判为碰撞。可执行文件安装路径：

```
~/ros2_ws/install/openarm_acm_tool/lib/openarm_acm_tool/openarm-generate-acm
```

内置安全策略：

- **相邻连杆对**：输入 SRDF 里已禁用，跳过。
- **跨臂对（左 ↔ 右）**：**永不禁用**。两臂装在同一躯干上、间距仅几厘米，工作空间重叠，跨臂碰撞检查必须保留（14 自由度随机采样对跨臂接触的估计不可靠，故不采信）。
- 只有**同臂（左-左 / 右-右）或 躯干-臂**之间、所有采样中从未碰撞的对，才输出为禁用。

用法：

```bash
# 用法：openarm-generate-acm <urdf> <srdf> [samples] [seed] [include_cross]
# 例（SRDF 路径见第 5 节「关键文件」表）：
openarm-generate-acm openarm_v10.urdf openarm_bimanual.srdf 1000000
```

- `samples`：采样次数，默认 1000000（越大「从未碰撞」越可靠）。
- `include_cross`：传 `1` 时也输出跨臂禁用对（**危险**，仅排查用，默认 0 不输出）。
- `<disable_collisions .../>` 片段打印到 stdout，采样统计打到 stderr，回填进 SRDF 即可。

> ⚠️ 该矩阵只是同臂自碰撞的**近似**，只有采样足够大才可靠；跨臂碰撞永远不能靠它禁用。
