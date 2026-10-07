# gripper_teleop

手持夹爪 (DM3507) 开合检测 + AGX 机械臂夹爪遥操桥接，独立轻量 colcon 包。

## 组成

| 节点 | 可执行名 | 作用 |
|------|----------|------|
| `gripper_publisher` | `gripper_teleop.gripper_publisher:main` | 读 DM3507 编码器 → 发布 `/gripper/state`(%), `/gripper/width_m`(m), `/gripper/encoder_count` |
| `gripper_agx_bridge` | `gripper_teleop.gripper_agx_bridge:main` | 订阅 `/gripper/width_m` → 1:1 映射 → 发布 `/control/joint_states` 驱动 AGX 夹爪 |

## 依赖

- ROS2 (humble/jazzy)，`rclpy` / `sensor_msgs` / `std_msgs`
- `python-can`（DM3507 SLCAN 驱动需要，pip 安装）

## 编译

本包以符号链接纳入 CyperstereoSDK 的 ROS2 工作区（`ros2/src/gripper_teleop -> ../../gripper`），
源码仍独立保留在仓库根目录。

```bash
cd ~/CyperstereoSDK/ros2
source /opt/ros/humble/setup.bash
colcon build --packages-select gripper_teleop   # 不要加 --symlink-install，见下
source install/setup.bash
```

> ⚠️ 本机 setuptools 83 与 colcon-core 0.20.1 不兼容：`--symlink-install` 会调用
> `setup.py develop --editable`，而 setuptools 83 的 `develop` 已移除 `--editable`，
> 报 `error: option --editable not recognized`。ament_python 包（本包）需用普通 install
> 构建；CMake 包（data_cap）不受影响，仍可 `--symlink-install`。

## 运行

### 1. AGX 机械臂本体（另一个工作区 agx_arm_ros）

```bash
ros2 launch agx_arm_ctrl start_single_agx_arm.launch.py \
    arm_type:=piper effector_type:=agx_gripper
```

### 2. 手持夹爪检测

```bash
ros2 launch gripper_teleop gripper_publisher.launch.py
# 或指定设备
ros2 launch gripper_teleop gripper_publisher.launch.py channel:=/dev/ttyACM0
```

### 3. 桥接（1:1 宽度映射）

```bash
ros2 launch gripper_teleop gripper_agx_bridge.launch.py
```

或一键串联 2+3：

```bash
ros2 launch gripper_teleop gripper_bringup.launch.py
```

## 宽度映射

桥接默认 **1:1**（手持 70mm → 臂 70mm）：

```
agx_width = clamp(scale * width_m + offset, min_width, max_width)
```

- 1:1：`width_scale:=1.0`（默认，直观、精度高）
- 归一化满量程（手持全开 70.39mm → 臂全开 100mm）：`width_scale:=1.4207`，
  可防止机械结构差异导致开度不对应。

```bash
ros2 launch gripper_teleop gripper_agx_bridge.launch.py width_scale:=1.4207
```

## 参数

`gripper_publisher`：`channel`(/dev/ttyACM0), `motor_id`(7), `master_id`(17)

`gripper_agx_bridge`：`gripper_topic`, `control_topic`, `width_scale`(1.0),
`width_offset`(0.0), `min_width`(0.0), `max_width`(0.1), `force`(1.0N),
`deadband`(0.0005m)

## 标定

标定真源位于 `config/gripper_calibration.json`（安装后位于
`share/gripper_teleop/config/`）。手持夹爪编码器随开度增大而递减
（全闭 38079 → 全开 34247），线性映射已正确处理方向。
