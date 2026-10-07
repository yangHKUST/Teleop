# OpenArm Bringup

This package provides launch files to bring up the OpenArm robot system.

## Quick Start

Dual-arm (bimanual) with fake hardware:

```bash
ros2 launch openarm_bringup openarm.bimanual.launch.py arm_type:=v1.0 use_fake_hardware:=true
```

Real hardware:

```bash
ros2 launch openarm_bringup openarm.bimanual.launch.py arm_type:=v1.0 use_fake_hardware:=false
```

## Launch Files

- `openarm.bimanual.launch.py` - Dual-arm configuration (left + right arm).

## Launch Arguments

| Argument | Default | Description |
|---|---|---|
| `arm_type` | `openarm_v2.0` | Arm type (`v1.0`, `v10`, `openarm_v1.0`, `v2.0`, ...). |
| `use_fake_hardware` | `true` | Use `mock_components` instead of the real CAN hardware. |
| `robot_controller` | `joint_trajectory_controller` | `joint_trajectory_controller` or `forward_position_controller`. |
| `right_can_interface` | `can0` | CAN interface for the right arm. |
| `left_can_interface` | `can1` | CAN interface for the left arm. |
| `return_to_zero` | `false` | Sweep to zero on activate (`false` = hold current pose). |
| `gravity_scale` | `0.0` | Gravity-compensation feedforward scale (`0.0` = off, `1.0` = full). |
| `teaching_mode` | `false` | Zero-gravity teaching mode (drag to move, release to hold). |

## What Gets Launched

- Robot state publisher
- Controller manager (`ros2_control_node`)
- Joint state broadcaster
- Robot controller (`both_arms_joint_trajectory_controller`, or the left/right
  forward-position controllers)
- Gripper controllers (left + right)
- RViz2

## Gravity Compensation & Teaching Mode

The hardware interface (`openarm_hardware/OpenArmHW`) adds a Pinocchio gravity
compensation feedforward to the MIT control law:

```
tau = kp * (q_des - q) + kd * (dq_des - dq) + tau_ff
tau_ff = clamp(dir * gravity_scale * G(q) + offset, +/- TMAX)
```

`G(q)` is computed from the v1.0 URDF. With `gravity_scale = 1.0` the PD loop no
longer has to fight gravity, so the steady-state sag `G(q)/kp` is cancelled and
the arm holds its pose.

### Teaching mode (hand guiding)

Set `teaching_mode:=true` to enter zero-gravity teaching mode:

```bash
ros2 launch openarm_bringup openarm.bimanual.launch.py \
  arm_type:=v1.0 use_fake_hardware:=false teaching_mode:=true
```

- While the arm is being dragged (any joint speed above `teaching_drag_vel`),
  the position spring is released (`kp = 0`): only viscous damping plus full
  gravity compensation apply, so the arm moves freely by hand.
- When released (all joint speeds below `teaching_hold_vel`), the normal
  position spring re-engages at the latched position, so the arm holds where
  it was let go.

Teaching mode is a launch-time argument (Humble hardware components have no
runtime parameter service), so switching it requires a relaunch.

### Tuning residual sag

A light gravity model leaves a small residual sag: at rest `sag = dG / kp`,
where `dG` is the difference between the true gravity torque and the model's.
Two levers reduce it, plus a per-joint offset for precise trim:

| Parameter | Where | Default | Effect |
|---|---|---|---|
| `teaching_gravity_scale` | xacro `<param>` | `1.0` | Feedforward multiplier; `> 1` over-compensates a light model. |
| `teaching_hold_kp_scale` | xacro `<param>` | `1.0` | Hold-spring multiplier; `> 1` stiffens the release hold. |
| `teaching_drag_vel` | xacro `<param>` | `0.15` | rad/s; above this the arm is treated as being dragged. |
| `teaching_hold_vel` | xacro `<param>` | `0.05` | rad/s; below this the arm re-engages the hold. |
| `gravity_tau_offset1..7` | xacro `<param>` | `0.0` | Per-joint torque offset (Nm) added to the feedforward. |
| `gravity_tau_dir1..7` | xacro `<param>` | `1.0` | Per-joint gravity direction; `-1` flips a joint whose motor is inverted vs the URDF. |

These are set in `openarm_description`'s
`openarm.bimanual.ros2_control.xacro`, in each of the two `<hardware>` blocks
(left + right arm), for example:

```xml
<param name="teaching_gravity_scale">1.04</param>
<param name="teaching_hold_kp_scale">1.2</param>
<param name="gravity_tau_offset3">0.8</param>
```

`gravity_tau_offsetN` is a manual per-joint trim (Nm): it is added directly to
the feedforward before clamping, so it compensates exactly the joints that still
sag (or float) after tuning the global scale. To counter sag, add an offset with
the same sign as that joint's `G(q)` — the per-joint values are printed at
startup in the `gravity tau_ff (Nm): ...` log line. Go in small steps
(~0.1 Nm) and check that the joint neither sags nor floats/oscillates. The
feedforward is clamped per joint to +/- [54, 54, 28, 28, 10, 10, 10] Nm, so it
cannot exceed the motor's rated torque.

If a joint is compensated in the *wrong direction* (it actively pushes away
instead of holding, and no offset sign fixes it), the joint's motor is likely
inverted relative to the URDF axis. In that case flip the sign of its gravity
term with `gravity_tau_dirN = -1` (and re-tune `gravity_tau_offsetN` from 0),
rather than fighting it with a large offset — an offset cannot fix a sign-flipped
`G(q)`.

### Bimanual mirror: joint7 offset sign

The two arms' joint7 axes are mirrored in the URDF (left `(0,-1,0)`, right
`(0,1,0)`), so `G(q)` for joint7 comes out **opposite-signed** between the arms
across most of its range. In a symmetric pose the left wrist reads ~+0.4 Nm and
the right wrist ~-0.4 Nm. Do **not** copy a joint7 offset from one arm to the
other — mirror it (the values currently in the xacro):

| Arm | `gravity_tau_offset7` |
|---|---|
| left | `-0.3` (negative, because its `G(q)` is positive) |
| right | `+0.3` (positive, because its `G(q)` is negative) |

Use the sign of each arm's *own* `G(q)` — printed at startup in the
`gravity tau_ff (Nm): ...` log line — to choose the offset sign, then trim the
magnitude in ~0.1 Nm steps as above. Joints 1-6 have identical axes between the
two arms, so only joint7 needs this mirror treatment.

A practical consequence: setting `-0.3` on the right arm (copying the left) makes
it sag, `-0.05` still sags, and `+0.8` over-compensates so the wrist rises to its
limit — the correct value sits in between and has the opposite sign to the left
arm's.
