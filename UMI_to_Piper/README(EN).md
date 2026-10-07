# UMI_to_arm — Handheld Gripper (DM3507) → AgileX Piper Arm Teleoperation

## Summary

This project closes the "handheld gripper → robot arm" teleoperation loop: the 6-DoF VIO pose of a handheld gripper (Daimao DM3507 motor, published by ORB-SLAM3-Cyperstereo over ZMQ PUB `tcp://127.0.0.1:5555`) is incrementally mapped to the end-effector of an AgileX Piper arm, while the handheld gripper opening is mapped by percentage to the arm's AGX gripper, all synchronized with a MuJoCo digital twin. Its purpose is to provide a non-ROS day-to-day teleoperation pipeline supporting both direct-CAN real-arm control and pure simulation. Its value is enabling low-cost handheld trajectory demonstration/data collection that is first-order immune to VIO pose drift — a practical tool for robot teaching and data capture. This directory is a self-contained copy (layout mirrors the original `CyperstereoSDK/`, relative paths work unchanged).

## Hardware preparation

- **Handheld gripper**: a Daimao DM3507 motor (CAN id default 7; do not confuse with master id 17).
- **VIO camera**: ORB-SLAM3-Cyperstereo (stereo/inertial, serial default `s200032`), publishing the handheld gripper's 6-DoF pose.
- **Robot arm**: an AgileX Piper 6-axis arm + AGX gripper (optional).
- **Handheld gripper CAN link**: a CANable2 / SLCAN device, serial port default `/dev/ttyACM0` (reads the DM3507 encoder).
- **Real-arm CAN link**: a CANable / USB-CAN adapter, interface `can0` (real-arm mode).
- **Control PC**: the MuJoCo window needs a graphics environment; the gripper bridge needs a ROS2 humble workspace.

> The three run modes need different hardware: full (real arm + gripper + VIO), `--sim-only` (VIO + sim only, real arm frozen), `--synthetic` (no camera/gripper/arm; scripted poses).

## Environment setup

### Teleop main chain (conda env: `piper_pinocchio`)

- Python packages: `numpy`, `mujoco`, `pinocchio`, `imufusion` (imu-fusion), `python-can`, `pyzmq` (ZMQ subscription)
- Real-arm use additionally needs: `piper_sdk` (pip, direct CAN), a CANable2 device
- Startup **must** `unset PYTHONPATH` (so the broken pinocchio under `/opt/ros/humble` does not shadow the conda-forge build); `run_vio_teleop.sh` / `run_all.sh` already do this.

### Handheld gripper ROS2 bridge (separate workspace, needs `/usr/bin/python3` + humble)

`gripper/` is a standalone lightweight colcon package (`gripper_teleop`) with a pure-Python CANable2/SLCAN driver for the Daimao DM3507. It is symlinked into `~/CyperstereoSDK/ros2/src/gripper_teleop`; build it with:

```bash
cd ~/CyperstereoSDK/ros2
source /opt/ros/humble/setup.bash
colcon build --packages-select gripper_teleop   # do NOT add --symlink-install (setuptools 83 vs colcon incompatibility)
source install/setup.bash
```

> ⚠️ With setuptools 83 + colcon-core 0.20.1, `--symlink-install` calls `setup.py develop --editable`, which fails with `error: option --editable not recognized`; ament_python packages need a normal install.

## Startup

### One-click startup (single terminal, recommended)

```bash
cd ~/Teleop/UMI_to_arm
./run_all.sh                     # Full: ORB-SLAM3 + sim + real arm + gripper (staged flow)
./run_all.sh --sim-only          # Sim only: real arm frozen, sim arm + sim gripper teleop normally
./run_all.sh --no-calibrate      # Skip Z/X calibration (R_BW=identity)
./run_all.sh --synthetic --no-viewer --steps 300   # Offline smoke test (no hardware)
```

`run_all.sh` runs: ① start the gripper ROS2 chain (`gripper_bringup`) in the background → ② run teleop in the foreground with `--staged`. The staged flow is **go to ready pose → start VIO and prompt to complete initialization → prompt to complete Z/X calibration → press Enter to start teleop**. Three modes differ by a single parameter:

| Mode | Real arm | Gripper | VIO |
|---|---|---|---|
| (default) full | driven via `--can can0` | ROS2 chain drives AGX gripper via `/control/joint_states`; teleop `--no-gripper` avoids the serial conflict | ORB-SLAM3 launched |
| `--sim-only` | no `--can`, arm frozen | teleop reads handheld `/dev/ttyACM0` directly → sim gripper follows | ORB-SLAM3 launched |
| `--synthetic` | none | none | scripted poses (no camera) |

Press Ctrl-C to stop: the teleop reaps its own VIO child process, and the script's `trap` reaps the gripper chain. Env overrides: `VIO_SN` (default s200032), `CAN_IF` (default can0), `GRIPPER_CHANNEL` (default /dev/ttyACM0), `SIM_ONLY=1` (equivalent to `--sim-only`).

> **Dependency note**: `run_all.sh`'s VIO binary (`ORB_SLAM3-Cyperstereo/build/cyperstereo_online`) and ROS2 workspace (`ros2/install`) still point at the original repo `/home/taoqiu/CyperstereoSDK`; the full/sim modes require that repo to exist.

### Manual multi-terminal (equivalent)

```bash
# First make sure ORB-SLAM3 Cyperstereo is running (publishing ZMQ poses), then:
cd ~/Teleop/UMI_to_arm

./arm/mujoco_sim/run_vio_teleop.sh                        # VIO + MuJoCo (calibrate R_BW first)
./arm/mujoco_sim/run_vio_teleop.sh --can can0             # + real arm (goes to ready pose)
./arm/mujoco_sim/run_vio_teleop.sh --no-calibrate         # skip calibration, R_BW=identity
./arm/mujoco_sim/run_vio_teleop.sh --synthetic --no-viewer --steps 300  # offline smoke test
```

Handheld gripper open/close (ROS2 bridge, separate workspace):

```bash
cd ~/CyperstereoSDK/ros2
source /opt/ros/humble/setup.bash
source install/setup.bash
ros2 launch gripper_teleop gripper_bringup.launch.py   # channel:=/dev/ttyACM0
```

## Control instructions

### Handheld gripper → arm end-effector mapping

- **Translation**: incremental. Per-frame VIO-world displacement `Δ_t` is rotated into the base frame by `R_BW`, then `delta_p = scale · gain · R_BW · Δ_t`, accumulated onto the target.
- **Rotation**: incremental, local frame. `rv_f = R_CF · so3_log(Δ_R_local)` is mapped to the flange frame: roll→joint6, pitch→joint5 (×`pitch_gain`), yaw **discarded** (gripper pointing is determined by the arm's swing).
- **Gripper opening**: handheld 0–100% mapped by percentage to the arm gripper stroke (independent of translation/rotation).

### Keyboard shortcuts (during teleop)

| Key | Action |
|---|---|
| `space` | clutch: freeze / resume following (frozen = no follow, no increment accumulation) |
| `h` | return to ready pose (reset target and re-anchor reference) |
| `s` | record the current real-arm pose as the ready pose (writes `cartesian_ready_q.json`) |
| `esc` | emergency stop |

### Startup calibration R_BW (world → base)

After VIO initialization, keep the arm at its home pose and push the handheld gripper along two base-frame directions: **+Z (straight up)** and **+X (straight forward)** (left = up × forward is derived automatically). For each axis: press Enter at the start → translate → press Enter at the end. `--no-calibrate` skips it (R_BW = identity).

### Key tunable parameters (`piper_vio_teleop.py`, overridable on the command line)

| Parameter | Default | Meaning |
|---|---|---|
| `--scale` | 0.51 | Translation scale (world m → base m); larger = arm follows farther |
| `--x-gain` / `--y-gain` / `--z-gain` | 1.5 / 1.0 / 1.5 | Per-axis gains; final multiplier = scale × gain |
| `--pitch-gain` | 3.0 | Wrist pitch sensitivity |
| `--trans-deadzone` | 0.005 | Translation deadzone (m) |
| `--rot-deadzone` | 0.001 | Roll deadzone (rad, ~0.057°; ≈1.7°/s at 30 Hz) |
| `--pitch-deadzone` | 0.0029 | Pitch deadzone (rad, ~0.17°; ≈5°/s at 30 Hz) |
| `--max-angular` | 0.6 | Roll smoothing slew (rad/s, ≈34°/s) |
| `--pitch-slew` | 0.45 | Pitch smoothing slew (rad/s, ≈26°/s) |
| `--handeye-pitch-deg` | 20.0 | Camera→flange hand-eye pitch angle |
| `--gripper-motor-id` | 7 | Handheld gripper DM3507 CAN id |
| `--gripper-channel` | /dev/ttyACM0 | Handheld gripper CANable2 serial port |

## FAQ

### No VIO pose received ("没有收到 VIO 位姿" during calibration/teleop)
- **Why**: ORB-SLAM3 not started or not initialized / not tracking, or the ZMQ endpoint differs.
- **Check**: watch the ORB-SLAM3 window for tracking; confirm the endpoint `tcp://127.0.0.1:5555`.
- **Fix**: slowly move the handheld camera to complete VIO initialization, wait until tracking, then press Enter to proceed.

### pinocchio conflict on import (ROS humble)
- **Symptom**: `ModuleNotFoundError: pinocchio.pinocchio_pywrap_default`, or a pinocchio loaded from `/opt/ros/humble`.
- **Why**: ROS-humble's broken pinocchio on `PYTHONPATH` shadows the conda-forge build.
- **Fix**: launch via `run_vio_teleop.sh` / `run_all.sh` (they already `unset PYTHONPATH`); when running manually, `unset PYTHONPATH` first.

### Handheld gripper unavailable (`[warn] 手持夹爪不可用`)
- **Why**: the CANable2/SLCAN is not connected or the serial port is wrong, or the motor id differs.
- **Check**: confirm `/dev/ttyACM0` exists; confirm `--gripper-motor-id` is 7.
- **Fix**: check the serial connection and id, then reconnect; use `--no-gripper` to skip gripper following in pure simulation.

### Real arm does not move
- **Why**: CAN not up, arm unpowered, `--can` not passed, or still in the ready-pose phase.
- **Check**: `ip -details link show can0` should be `ERROR-ACTIVE`; confirm `--can can0` was passed.
- **Fix**: configure CAN and power up, then rerun; watch the `[ready]` phase to see whether it reached the pose.

### Up/down, forward/back, or left/right directions are reversed
- **Why**: the calibration direction was pushed the wrong way, or the hand-eye mount orientation differs.
- **Fix**: use `--flip-z` (up/down), `--flip-yaw` (forward/back and left/right both reversed, 180° yaw), `--flip-y` (left/right), `--flip-roll` / `--flip-pitch` (roll/pitch); or recalibrate.

### Calibration fails (`+X direction almost parallel to +Z`)
- **Why**: the handheld gripper had a large vertical component while pushing along +X, making "forward" nearly collinear with "up".
- **Fix**: push strictly horizontally (keep height) and recalibrate.

### End jitters / sluggish following
- **Why**: VIO noise, or unsuitable filter parameters.
- **Fix**: the default is the 1€ adaptive filter (`--filter one_euro`); tune `--one-euro-min-cutoff` (lower = smoother), `--one-euro-beta` (higher = more responsive on fast motion), or increase `--trans-deadzone` / `--rot-deadzone` / `--pitch-deadzone`.

### Gripper bridge build fails with `error: option --editable not recognized`
- **Why**: setuptools 83 + colcon-core 0.20.1 are incompatible; `--symlink-install` runs `develop --editable` and fails.
- **Fix**: build with `colcon build --packages-select gripper_teleop` and do **not** add `--symlink-install`.
