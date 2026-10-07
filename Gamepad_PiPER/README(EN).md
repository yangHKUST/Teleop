# Gamepad Teleoperation for Robotic Arm — A New Intuitive Control Experience

## Summary

This project enables intuitive teleoperation of the AgileX Piper arm with a standard PS2 gamepad, supporting both joint-space and Cartesian pose control modes, plus two visualization backends (a native MuJoCo window and the viser web page). Its purpose is to make robotic-arm control as natural and precise as playing a game via sticks, triggers, and buttons. Its value is providing a low-barrier, ready-to-use gamepad teleoperation solution for robot education, demos, and data collection — testable with a virtual arm before touching the real one.

## Hardware preparation

- **Robot arm**: an AgileX Piper arm + power supply (not needed in virtual mode).
- **PS2 gamepad**: a standard PS2 controller + its USB wireless receiver (looks like a wireless-mouse receiver).
- **Control PC**: Ubuntu 20.04 or higher; the MuJoCo backend needs a graphics environment, the viser backend only needs a browser.
- **CAN link (required for real-robot mode)**: a CANable / USB-CAN adapter, interface `can0`, bitrate **1 Mbps**.
- **End gripper (optional)**: an electric gripper, 0–100% opening range.

> For first-time use, test with the virtual arm (`main_virtual.py` or `./run_mujoco.sh`) before using the real robot.

## Environment setup

OS: Ubuntu 20.04 or higher; Python 3.9+, Anaconda / Miniconda recommended.

Clone and enter the project root:

```bash
git clone https://github.com/kehuanjack/Gamepad_PiPER.git
cd Gamepad_PiPER
```

Install the common deps + a kinematics library (**pick one of four; pytracik is recommended**):

- **Based on [pinocchio](https://github.com/stack-of-tasks/pinocchio)** (Python == 3.9, requires [piper_ros](https://github.com/agilexrobotics/piper_ros) and sourcing the arm's ROS workspace, otherwise meshes are not found):

  ```bash
  conda create -n test_pinocchio python=3.9.* -y
  conda activate test_pinocchio
  pip3 install -r requirements_common.txt --upgrade
  conda install pinocchio=3.6.0 -c conda-forge
  pip install meshcat
  pip install casadi
  ```

  In `main.py` and `main_virtual.py`, select `from src.gamepad_pin import RoboticArmController`.

- **Based on [PyRoKi](https://github.com/chungmin99/pyroki)** (Python >= 3.10):

  ```bash
  conda create -n test_pyroki python=3.10.* -y
  conda activate test_pyroki
  pip3 install -r requirements_common.txt --upgrade
  pip3 install pyroki@git+https://github.com/chungmin99/pyroki.git@f234516
  ```

  In `main.py` and `main_virtual.py`, select `from src.gamepad_limit import RoboticArmController` or `from src.gamepad_no_limit import RoboticArmController`.

- **Based on [cuRobo](https://github.com/NVlabs/curobo)** (Python >= 3.8, CUDA 11.8 recommended):

  ```bash
  conda create -n test_curobo python=3.10.* -y
  conda activate test_curobo
  pip3 install -r requirements_common.txt --upgrade
  sudo apt install git-lfs && cd ../
  git clone https://github.com/NVlabs/curobo.git && cd curobo
  pip3 install "numpy<2.0" "torch==2.0.0" pytest lark
  pip3 install -e . --no-build-isolation
  python3 -m pytest .
  cd ../Gamepad_PiPER
  ```

  In `main.py` and `main_virtual.py`, select `from src.gamepad_curobo import RoboticArmController`.

- **Based on [pytracik](https://github.com/chenhaox/pytracik)** (Python >= 3.10):

  ```bash
  conda create -n test_tracik python=3.10.* -y
  conda activate test_tracik
  pip3 install -r requirements_common.txt --upgrade
  git clone https://github.com/chenhaox/pytracik.git
  cd pytracik
  pip install -r requirements.txt
  sudo apt install g++ libboost-all-dev libeigen3-dev liborocos-kdl-dev libnlopt-dev libnlopt-cxx-dev
  python setup_linux.py install --user
  ```

  In `main.py` and `main_virtual.py`, select `from src.gamepad_trac_ik import RoboticArmController`.

### Local deployment (conda + Pinocchio + MuJoCo)

```bash
conda create -n piper python=3.11 -y
conda install -n piper -c conda-forge pinocchio=3.6.0 casadi -y
$HOME/miniconda3/envs/piper/bin/python -m pip install \
    scipy viser yourdfpy "pygame<2.6.2" piper_sdk "setuptools<80.9.0" mujoco
```

> **Note**: if your shell profile sources ROS (e.g. `/opt/ros/humble`), its Python 3.10 site-packages shadow the conda pinocchio. `run_mujoco.sh` and `run_real.py` automatically clear ROS's `PYTHONPATH`/`LD_LIBRARY_PATH` and point `ROS_PACKAGE_PATH` at `ros_packages/` (which symlinks `package://piper_description/meshes` to `piper/meshes`) so Pinocchio finds the STL meshes.

## Startup

1. **Connect the arm and activate CAN** (real-robot mode):

   ```bash
   sudo ip link set can0 up type can bitrate 1000000
   ```

2. **Connect the PS2 gamepad**:
   1. Plug the USB wireless receiver into a USB port.
   2. Slide the power switch on the bottom from right to left until the "POWER" LED on the upper-left lights up (red).
   3. After launching the program, press **MODE** to return the arm to its ready posture, then press **START** to begin teleoperating the real robot.

3. **Enable the control service** (run in the project directory):

   ```bash
   ./run_mujoco.sh        # virtual arm (native MuJoCo window, no browser)
   ./run_real.py          # real robot (Pinocchio + MuJoCo; brings up can0, sudo password required)
   python3 main_virtual.py  # virtual arm (viser web)
   ```

   Test with the virtual arm first.

4. **Gamepad connection verification**: after startup, check the console output to confirm the gamepad is recognized.

5. **Visualization**: with viser, open `http://localhost:8080` in a browser; with MuJoCo, look at the pop-up native window.

6. **Start controlling**: operate the arm per the mapping below.

## Control instructions

### Button function mapping

| Button | Short press | Long press |
|--------|-------------|------------|
| **HOME** | Connect / disconnect arm | None |
| **START** | Switch upper control mode (joint/pose) | Switch lower control mode (joint/pose) |
| **BACK** | Switch lower command mode (position-velocity 0x00 / quick-response 0xAD) | None |
| **Y** | Return to zero position | None |
| **A** | Save current position | Clear current saved position |
| **B** | Restore last saved position | None |
| **X** | Toggle position playback order | Clear all saved positions |
| **LB** | Increase speed factor (upper) | Decrease speed factor (upper) |
| **RB** | Increase movement speed (lower) | Decrease movement speed (lower) |

### Joystick and trigger functions

| Control element | Joint mode | Pose mode |
|-----------------|------------|-----------|
| **Left stick** | J1 (base rotation): left/right / J2 (shoulder): up/down | End-effector X/Y movement |
| **Right stick** | J3 (elbow): up/down / J6 (wrist rotation): left/right | End-effector Z movement and rotation about Z |
| **D-pad** | J4 (wrist yaw): left/right / J5 (wrist pitch): up/down | End-effector rotation about X/Y |
| **Left trigger (LT)** | Close gripper | Close gripper |
| **Right trigger (RT)** | Open gripper | Open gripper |

### Special function notes

1. **Gripper**: 0–100% opening; when fully closed (0%) or fully open (100%), a quick press-and-release of the trigger toggles the state.
2. **Speed**: speed factors 0.25x / 0.5x / 1.0x / 2.0x / 3.0x / 4.0x / 5.0x (LB); movement speed 10%–100% (RB). The joint-mode default step is reduced to **0.05°** (was 0.5°), then multiplied by the speed factor; pose-mode steps are unchanged.
3. **Position memory**: multiple position points can be saved; supports sequential and reverse-order playback.

## FAQ

### Gamepad connected but not recognized by the program
- **Why**: receiver not seated / controller off / program started before the gamepad connected.
- **Check**: confirm the POWER LED is on and the receiver is plugged in; re-plug the receiver.
- **Fix**: plug the receiver and power on the gamepad first, then run the program; check the console for the gamepad recognition message.

### Real robot does not move
- **Why**: CAN not up, arm unpowered, or MODE → START not pressed.
- **Check**: `ip -details link show can0` should be `ERROR-ACTIVE`; confirm power; confirm you pressed MODE then START.
- **Fix**: run `sudo ip link set can0 up type can bitrate 1000000` and reconnect; first verify with the virtual arm.

### Import fails with `ModuleNotFoundError: pinocchio.pinocchio_pywrap_default` or loads ROS's pinocchio
- **Why**: your shell sources ROS, whose Python 3.10 site-packages shadow the conda pinocchio.
- **Fix**: launch via `./run_mujoco.sh` or `./run_real.py` (they clean the ROS env); when running manually, `unset PYTHONPATH` first.

### Meshes not found (pinocchio library)
- **Why**: pinocchio needs `package://piper_description/meshes`, which depends on the ROS workspace or `ROS_PACKAGE_PATH`.
- **Fix**: the local deployment resolves this via `ROS_PACKAGE_PATH` → `ros_packages/` (`run_real.py` / `run_mujoco.sh` set it for you); when running manually, source the arm's ROS workspace.

### Large joint jumps near critical points
- **Why**: numerical IK solutions can jump near singular/critical points.
- **Fix**: keep a safe distance, avoid workspace boundaries/singularities, and lower the speed first.

### Quick-response mode (0xAD) caution
- **Note**: this mode is responsive but dangerous.
- **Fix**: use with extreme caution; keep a safe distance if used.

### Real-robot exit behavior
- **Note**: pressing Ctrl+C once **returns home and locks, then exits** while staying enabled (no power-off); the arm is locked at the zero position and will not go limp. To actually power down, use the HOME button to disconnect.
