# dm_canable2

Python package for Damiao motor control over CANable2/SLCAN.

The API mirrors the official `motor-control-routine/Python例程/u2can/DM_CAN.py`
where practical. The transport is different:

- official `DM_CAN.py`: serial device receives a vendor USB-CAN packet format
- this package: `python-can` sends standard CAN frames through CANable2 `slcan`

## Requirements

Install `python-can` before running the tools:

```bash
sudo apt install python3-can
```

If the system package is unavailable:

```bash
python3 -m pip install --user python-can
```

## Supported API

- `Motor`
- `MotorControl` / `Motor_Control`
- `enable`, `enable_old`, `disable`, `set_zero_position`
- `controlMIT` / `control_mit`
- `control_Pos_Vel` / `control_pos_vel`
- `control_Vel` / `control_vel`
- `control_pos_force`
- `control_Pos_Vel_CSP`, `control_Vel_CSP`, `control_Tor_CSP`
- `switchControlMode`
- `read_motor_param`, `change_motor_param`, `save_motor_param`
- `refresh_motor_status`

## Minimal DM3507 Example

```python
from dm_canable2 import Motor, MotorControl, DM_Motor_Type, Control_Type

motor = Motor(DM_Motor_Type.DM3507, 0x07, 0x11)  # 实物 motor_id=7，不是 0x01

with MotorControl(channel="/dev/ttyACM0", can_bitrate=1000000, tty_baudrate=115200) as control:
    control.addMotor(motor)
    control.switchControlMode(motor, Control_Type.VEL)
    control.enable(motor)
    control.control_Vel(motor, 5.0)
    control.disable(motor)
```

## Notes

- DM3507 limits are set to `PMAX=12.566`, `VMAX=50`, `TMAX=5`.
- `save_motor_param()` follows the official Python example and sends save code
  `0x00` by default. If your firmware follows the u2canfd C++ example, call
  `save_motor_param(motor, save_code=0x01)`.
- Hardware behavior has to be verified on the actual CAN bus. The package
  itself only defines the frame format and transport.
