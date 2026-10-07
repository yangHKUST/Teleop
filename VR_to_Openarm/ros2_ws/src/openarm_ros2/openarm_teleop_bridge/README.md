# openarm_teleop_bridge — OpenArm VR teleoperation

> 新用户请先阅读[中文部署与操作指南](../../../../README.md)。下文保留开发机技术记录；固定 IP 和虚拟环境补丁不是新电脑自动具备的配置。

VR teleoperation of the OpenArm **v1.0** dual-arm robot (7-DOF arms + prismatic
grippers) via [qrafty-ai/teleop_xr](https://github.com/qrafty-ai/teleop_xr)
(Apache-2.0, WebXR/WebRTC) + a ROS 2 bridge node.

The human wears a Meta Quest (or opens the page in any WebXR-capable browser),
moves their hands, and the two arms follow in real time via differentiable IK.

## Architecture

```
 Quest / phone browser (WebXR)
        │  WebRTC / viser  (https://10.200.0.222:4443)
        ▼
 teleop_xr  (python -m teleop_xr.ros2 --mode ik --robot-class openarm)
        │   JAX differentiable IK (pyroki), fetches URDF from /robot_description
        │   EE = openarm_left/right_link7  → 14-DOF bimanual solve
        ├── /joint_trajectory            (trajectory_msgs/JointTrajectory)
        └── xr/controller_{left,right}/joy  (sensor_msgs/Joy)
        ▼
 jt_bridge  (this package)
        ├── arm IK  → /left|right_forward_position_controller/commands  (Float64MultiArray, 7)
        ├── trigger → openarm_left|right_finger_joint1  (gripper, 0..0.044 m)
        └── X/A     → smooth return-to-home  (quintic, uses /joint_states)
        ▼
 ros2_control  (forward_position_controller / gripper_controller)
        ▼
 OpenArmHW  (MIT position PD + gravity compensation, real CAN)  or  mock_components (fake)
```

The arm gripper is **not** part of the IK solve (IK solves only the 7 arm
joints); the finger joint is driven directly by the bridge from the trigger.

## Quick start

```bash
# Simulation (fake hardware, gravity comp off)
ros2 launch openarm_teleop_bridge teleop.launch.py

# Real hardware (real CAN motors, gravity comp on)
ros2 launch openarm_teleop_bridge teleop_real.launch.py
```

Wait for the ready signal (~20–55 s of one-time JIT compilation):

```
Server started at 0.0.0.0:4443
The phone web app should be available at https://10.200.0.222:4443
```

Then open **https://10.200.0.222:4443** in the Quest browser (or a phone).
The certificate is self-signed — click *Advanced → Proceed* once per device.
If the WiFi IP ever changes, the cert SAN must be regenerated (see
[Troubleshooting](#troubleshooting)).

## Controller mapping

| Input (xr-standard) | Left controller | Right controller | Action |
|---|---|---|---|
| grip / squeeze (button 1) | hold | hold | **Deadman** — engages IK for that arm (single-arm: grip one hand to move only that arm) |
| index trigger (button 0, analog) | | | **Gripper** open↔close, mapped 0..`gripper_max_m` (0.044 m) |
| X (button 4) | press | | **Home** — smooth return of the *left* arm to `left_home` |
| A (button 4) | | press | **Home** — smooth return of the *right* arm to `right_home` |
| grip during home | | | **Cancel** the in-progress home motion |

Deadman is **single-arm**: `teleop_xr/ik/controller.py` was patched so each
controller engages independently (gripping only one hand moves only that arm;
the other arm is held by the solver's rest cost). Gripping both = bimanual.

## Launch files

- `launch/teleop.launch.py` — one-shot stack: bringup (v1.0 + forward-position
  controllers) + `jt_bridge` + `teleop_xr` (delayed 6 s so `/robot_description`
  is up first). Defaults to **fake** hardware.
- `launch/teleop_real.launch.py` — same stack with real-hardware defaults
  (`use_fake_hardware:=false`, `gravity_scale:=1.0`).
- `launch/bridge.launch.py` — the bridge node alone (starts disabled).

Both entry points accept the full set of overrides:

| Argument | Default | Notes |
|---|---|---|
| `arm_type` | `openarm_v1.0` | **must stay v1.0** — teleop_xr hardcodes `link7` |
| `robot_controller` | `forward_position_controller` | the other choice is `joint_trajectory_controller` |
| `use_fake_hardware` | `true` (`false` in real) | `false` → `openarm_hardware/OpenArmHW` |
| `gravity_scale` | `0.0` (`1.0` in real) | gravity-comp feedforward |
| `return_to_zero` | `false` | sweep to zero on activate (opt-in) |
| `teaching_mode` | `false` | zero-gravity drag-to-teach |
| `left_can_interface` / `right_can_interface` | `can1` / `can0` | CAN interfaces |
| `enable_on_start` | `true` | bridge enable latch |
| `teleop_python` | `~/venv-teleop-xr/bin/python` | interpreter for teleop_xr |
| `teleop_delay` | `6.0` | seconds before teleop_xr starts |
| `preflight_cleanup` | `true` | kill leftover openarm nodes first (see below) |

## jt_bridge parameters

Arm / gripper topics, joint names:

- `input_topic` (`/joint_trajectory`)
- `left_arm_controller_topic` / `right_arm_controller_topic`
- `left_gripper_controller_topic` / `right_gripper_controller_topic`
- `left_arm_joints` / `right_arm_joints` (default `openarm_left/right_joint1..7`)
- `left_gripper_joint` / `right_gripper_joint` (default `openarm_left/right_finger_joint1`)

VR input (gripper + home):

- `left_joy_topic` / `right_joy_topic` (`xr/controller_left/joy`, `xr/controller_right/joy`)
- `gripper_min_m` (`0.0`), `gripper_max_m` (`0.044`), `invert_gripper` (`false`)
- `gripper_deadband` (`0.001` m)
- `home_button_index` (`4` = X/A)
- `left_home` / `right_home` (default `[0, ∓0.8, 0, 1.2, 0, 0, 0]`)
- `joint_states_topic` (`/joint_states`) — feedback for smooth home
- `home_duration` (`3.0` s), `home_rate` (`50` Hz) — quintic minimum-jerk home motion
- `home_cancel_button_index` (`1` = grip)

Gating:

- `enable_on_start` (`false` in the bridge's own default; the consolidated
  launch sets it `true`)
- service `enable` (`std_srvs/srv/SetBool`) — master gate on all output

## Safety (real hardware)

- The enable latch gates new trajectory/joy inputs, but the current home timer does not check it: an ongoing home motion can continue after `/enable=false`. This service is not an emergency stop or motor-disable command.
- Home motion normally uses quintic interpolation over 3 s and cancels on re-grip; without joint feedback it sends the home target directly. Validate joint feedback first. Gripper and home buttons do not require the grip to be held.
- `gravity_scale:=1.0` is **required** on hardware so the arms hold their own
  weight; `gravity_scale:=0.0` lets them sag.
- Keep the workspace clear and start with small, slow hand motions.

## Troubleshooting

- **Motors never enable / `mock_generic_system` in the log.** A leftover
  `robot_state_publisher` (from a previous fake-hardware run) is still latching
  a fake URDF onto `/robot_description`, and the new `controller_manager` grabs
  it before the fresh publisher writes the real one. The launch now runs a
  **preflight cleanup** (`preflight_cleanup:=true`) that kills stale
  `robot_state_publisher` / `ros2_control_node` / `jt_bridge` / `teleop_xr` /
  spawners first. If you see `[mock_generic_system]` in the `ros2_control_node`
  log anyway, check `ros2 node list` for a second stack and stop it.
- **VR page won't load.** The bundled self-signed cert expires and modern
  browsers hard-block it (`ERR_CERT_DATE_INVALID`). Regenerate in
  `~/venv-teleop-xr/lib/python3.10/site-packages/teleop_xr/`:
  ```bash
  openssl req -x509 -newkey rsa:2048 -sha256 -days 3650 -nodes \
    -keyout key.pem -out cert.pem -subj "/CN=openarm-teleop" \
    -addext "subjectAltName=IP:10.200.0.222,IP:127.0.0.1,DNS:localhost"
  ```
- **`ValueError: Link openarm_left_link7 not found in URDF`.** You launched the
  v2.0 URDF; teleop_xr needs v1.0 — keep `arm_type:=openarm_v1.0`.
- **teleop_xr is quiet for ~20–55 s.** Normal one-time JIT compile; wait for
  `Server started at 0.0.0.0:4443`.
- **Port 4443 unreachable.** `ufw` may block it; check `sudo ufw status` and
  allow 4443 on the WiFi interface.

## Install notes (already done on this machine)

- teleop_xr lives in `~/venv-teleop-xr` (Python 3.10; deps: `teleop-xr`,
  `pyroki`/`ballpark`, `jaxls`). Do **not** use `~/venv-openarm-ik` for it.
- Two source patches (the independent-hand change also modifies `step()`) are applied in that venv (re-apply after any
  `pip install -U teleop-xr`):
  1. `teleop_xr/ros2/__main__.py` — broaden the cv_bridge import guard to
     `except (ImportError, AttributeError):` (numpy 2 warning).
  2. `teleop_xr/ik/controller.py` — single-arm deadman (`_get_engaged_hands`)
     instead of requiring both grips.
- Build this package with `conda deactivate` then
  `~/venv-openarm-ik/bin/python -m colcon build --packages-select openarm_teleop_bridge --symlink-install`.
