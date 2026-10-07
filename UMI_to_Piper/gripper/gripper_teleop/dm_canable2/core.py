from __future__ import annotations

import struct
import time
from dataclasses import dataclass
from enum import IntEnum
from typing import Any, Dict, Optional, Tuple


class DM_Motor_Type(IntEnum):
    DM4310 = 0
    DM4310_48V = 1
    DM4340 = 2
    DM4340_48V = 3
    DM6006 = 4
    DM8006 = 5
    DM8009 = 6
    DM10010L = 7
    DM10010 = 8
    DMH3510 = 9
    DMH6215 = 10
    DMG6220 = 11
    DMJH11 = 12
    DM6248P = 13
    DM3507 = 14


class DM_variable(IntEnum):
    UV_Value = 0
    KT_Value = 1
    OT_Value = 2
    OC_Value = 3
    ACC = 4
    DEC = 5
    MAX_SPD = 6
    MST_ID = 7
    ESC_ID = 8
    TIMEOUT = 9
    CTRL_MODE = 10
    Damp = 11
    Inertia = 12
    hw_ver = 13
    sw_ver = 14
    SN = 15
    NPP = 16
    Rs = 17
    LS = 18
    Flux = 19
    Gr = 20
    PMAX = 21
    VMAX = 22
    TMAX = 23
    I_BW = 24
    KP_ASR = 25
    KI_ASR = 26
    KP_APR = 27
    KI_APR = 28
    OV_Value = 29
    GREF = 30
    Deta = 31
    V_BW = 32
    IQ_c1 = 33
    VL_c1 = 34
    can_br = 35
    sub_ver = 36
    u_off = 50
    v_off = 51
    k1 = 52
    k2 = 53
    m_off = 54
    dir = 55
    p_m = 80
    xout = 81


class Control_Type(IntEnum):
    MIT = 1
    POS_VEL = 2
    VEL = 3
    Torque_Pos = 4
    POS_VEL_CSP = 5
    VEL_CSP = 6
    Torque_CSP = 7


Control_Mode = Control_Type
Control_Mode_Code = Control_Type
DM_REG = DM_variable

CONTROL_ID_OFFSET = {
    Control_Type.MIT: 0x000,
    Control_Type.POS_VEL: 0x100,
    Control_Type.VEL: 0x200,
    Control_Type.Torque_Pos: 0x300,
    Control_Type.POS_VEL_CSP: 0x400,
    Control_Type.VEL_CSP: 0x500,
    Control_Type.Torque_CSP: 0x600,
}

LIMIT_PARAM: Dict[DM_Motor_Type, Tuple[float, float, float]] = {
    DM_Motor_Type.DM4310: (12.5, 30.0, 10.0),
    DM_Motor_Type.DM4310_48V: (12.5, 50.0, 10.0),
    DM_Motor_Type.DM4340: (12.5, 10.0, 28.0),
    DM_Motor_Type.DM4340_48V: (12.5, 10.0, 28.0),
    DM_Motor_Type.DM6006: (12.5, 45.0, 20.0),
    DM_Motor_Type.DM8006: (12.5, 45.0, 40.0),
    DM_Motor_Type.DM8009: (12.5, 45.0, 54.0),
    DM_Motor_Type.DM10010L: (12.5, 25.0, 200.0),
    DM_Motor_Type.DM10010: (12.5, 20.0, 200.0),
    DM_Motor_Type.DMH3510: (12.5, 280.0, 1.0),
    DM_Motor_Type.DMH6215: (12.5, 45.0, 10.0),
    DM_Motor_Type.DMG6220: (12.5, 45.0, 10.0),
    DM_Motor_Type.DMJH11: (12.5, 10.0, 12.0),
    DM_Motor_Type.DM6248P: (12.566, 20.0, 120.0),
    DM_Motor_Type.DM3507: (12.566, 50.0, 5.0),
}

UINT_PARAM_RIDS = set(range(7, 11)) | set(range(13, 17)) | {35, 36}


@dataclass
class Feedback:
    q: float
    dq: float
    tau: float
    err: int
    q_raw: int = 0  # 16-bit raw encoder count (q_uint), for traceability


@dataclass
class _RawMessage:
    arbitration_id: int
    data: bytes
    is_extended_id: bool = False


def _import_can():
    try:
        import can  # type: ignore
    except ImportError as exc:
        raise RuntimeError(
            "python-can is required. Install dependencies with: pip install -r requirements.txt"
        ) from exc
    return can


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, float(value)))


def float_to_uint(value: float, minimum: float, maximum: float, bits: int) -> int:
    value = clamp(value, minimum, maximum)
    span = maximum - minimum
    return int((value - minimum) * ((1 << bits) - 1) / span)


def uint_to_float(raw: int, minimum: float, maximum: float, bits: int) -> float:
    span = maximum - minimum
    return (raw / ((1 << bits) - 1)) * span + minimum


def pack_f32_le(value: float) -> bytes:
    return struct.pack("<f", float(value))


def pack_u32_le(value: int) -> bytes:
    return struct.pack("<I", int(value) & 0xFFFFFFFF)


def unpack_f32_le(data4: bytes) -> float:
    return struct.unpack("<f", bytes(data4))[0]


def unpack_u32_le(data4: bytes) -> int:
    return struct.unpack("<I", bytes(data4))[0]


def parse_feedback(data: bytes, limits: Tuple[float, float, float]) -> Optional[Feedback]:
    if len(data) < 6:
        return None

    q_max, dq_max, tau_max = limits
    err = (data[0] >> 4) & 0x0F
    q_uint = ((data[1] << 8) | data[2]) & 0xFFFF
    dq_uint = ((data[3] << 4) | (data[4] >> 4)) & 0x0FFF
    tau_uint = (((data[4] & 0x0F) << 8) | data[5]) & 0x0FFF

    return Feedback(
        q=uint_to_float(q_uint, -q_max, q_max, 16),
        dq=uint_to_float(dq_uint, -dq_max, dq_max, 12),
        tau=uint_to_float(tau_uint, -tau_max, tau_max, 12),
        err=err,
        q_raw=q_uint,
    )


class Motor:
    def __init__(self, MotorType: DM_Motor_Type, SlaveID: int, MasterID: int):
        self.Pd = 0.0
        self.Vd = 0.0
        self.state_q = 0.0
        self.state_dq = 0.0
        self.state_tau = 0.0
        self.state_err = 0
        self.state_q_raw = 0
        self.SlaveID = int(SlaveID)
        self.MasterID = int(MasterID)
        self.MotorType = DM_Motor_Type(MotorType)
        self.NowControlMode = Control_Type.MIT
        self.isEnable = False
        self.temp_param_dict: Dict[int, Any] = {}
        self._last_time = time.monotonic()
        self._delta_time = 0.0
        self.limit_param = LIMIT_PARAM[self.MotorType]

    def recv_data(self, q: float, dq: float, tau: float, err: int):
        self.receive_data(q, dq, tau, err)

    def receive_data(self, q: float, dq: float, tau: float, err: int, raw_q: int = 0):
        now = time.monotonic()
        self._delta_time = now - self._last_time
        self._last_time = now
        self.state_q = q
        self.state_dq = dq
        self.state_tau = tau
        self.state_err = err
        self.state_q_raw = raw_q

    def getPosition(self) -> float:
        return self.state_q

    def getRawEncoder(self) -> int:
        return self.state_q_raw

    def getVelocity(self) -> float:
        return self.state_dq

    def getTorque(self) -> float:
        return self.state_tau

    def getError(self) -> int:
        return self.state_err

    def getParam(self, RID: int):
        return self.temp_param_dict.get(int(RID))

    def getTimeInterval(self) -> float:
        return self._delta_time

    def get_limit_param(self) -> Tuple[float, float, float]:
        return self.limit_param

    # C++/u2canfd-style accessors.
    def GetMotorType(self) -> DM_Motor_Type:
        return self.MotorType

    def GetMotorMode(self) -> Control_Type:
        return self.NowControlMode

    def GetMasterId(self) -> int:
        return self.MasterID

    def GetSlaveId(self) -> int:
        return self.SlaveID

    def GetCanId(self) -> int:
        return self.SlaveID

    def Get_Position(self) -> float:
        return self.state_q

    def Get_Velocity(self) -> float:
        return self.state_dq

    def Get_tau(self) -> float:
        return self.state_tau

    def Get_Err(self) -> int:
        return self.state_err

    def Get_err(self) -> int:
        return self.state_err


class MotorControl:
    def __init__(
        self,
        channel: str = "/dev/ttyACM0",
        can_bitrate: int = 1000000,
        tty_baudrate: int = 115200,
        *,
        bus: Any = None,
        auto_open: bool = True,
        receive_timeout: float = 0.01,
    ):
        self.channel = channel
        self.can_bitrate = int(can_bitrate)
        self.tty_baudrate = int(tty_baudrate)
        self.bus = bus
        self.receive_timeout = receive_timeout
        self.motors_map: Dict[int, Motor] = {}
        if auto_open and self.bus is None:
            self.open()

    def __enter__(self) -> "MotorControl":
        if self.bus is None:
            self.open()
        return self

    def __exit__(self, exc_type, exc, tb):
        self.close()

    def open(self):
        if self.bus is not None:
            return
        can = _import_can()
        self.bus = can.interface.Bus(
            interface="slcan",
            channel=self.channel,
            bitrate=self.can_bitrate,
            ttyBaudrate=self.tty_baudrate,
        )

    def close(self):
        if self.bus is not None:
            self.bus.shutdown()
            self.bus = None

    def addMotor(self, motor: Motor):
        self.motors_map[motor.SlaveID] = motor
        if motor.MasterID:
            self.motors_map[motor.MasterID] = motor

    def add_motor(self, motor: Motor):
        self.addMotor(motor)

    def getMotor(self, motor_id: int) -> Optional[Motor]:
        return self.motors_map.get(int(motor_id))

    def send_std(self, arbitration_id: int, payload: bytes, *, pad_to_8: bool = True):
        if self.bus is None:
            self.open()
        data = bytes(payload[:8])
        if pad_to_8:
            data = data.ljust(8, b"\x00")
        try:
            can = _import_can()
            msg = can.Message(arbitration_id=int(arbitration_id), data=data, is_extended_id=False)
        except RuntimeError:
            msg = _RawMessage(arbitration_id=int(arbitration_id), data=data)
        self.bus.send(msg, timeout=0.2)

    def recv_once(self, timeout: Optional[float] = None):
        if self.bus is None:
            self.open()
        msg = self.bus.recv(timeout=self.receive_timeout if timeout is None else timeout)
        if msg is None:
            return None
        self._process_rx_message(msg)
        return msg

    def recv(self, timeout: Optional[float] = None):
        return self.recv_once(timeout)

    def drain_rx(self, timeout: float = 0.0, limit: int = 64):
        messages = []
        for _ in range(limit):
            msg = self.recv_once(timeout=timeout)
            if msg is None:
                break
            messages.append(msg)
        return messages

    def _process_rx_message(self, msg):
        data = bytes(msg.data)
        if len(data) >= 4 and data[2] in (0x33, 0x55, 0xAA) and self.motors_map.get(data[0] | (data[1] << 8)):
            self._process_param_feedback(data)
            return

        motor = self.motors_map.get(int(msg.arbitration_id))
        if motor is None and data:
            motor = self.motors_map.get(data[0] & 0x0F)
        if motor is None:
            return

        feedback = parse_feedback(data, motor.limit_param)
        if feedback is not None:
            motor.receive_data(feedback.q, feedback.dq, feedback.tau, feedback.err, feedback.q_raw)

    def _process_param_feedback(self, data: bytes):
        if len(data) < 8:
            return
        slave_id = data[0] | (data[1] << 8)
        motor = self.motors_map.get(slave_id)
        if motor is None:
            return
        rid = int(data[3])
        raw = data[4:8]
        if rid in UINT_PARAM_RIDS:
            value = unpack_u32_le(raw)
        else:
            value = unpack_f32_le(raw)
        motor.temp_param_dict[rid] = value
        if rid == int(DM_variable.CTRL_MODE):
            try:
                motor.NowControlMode = Control_Type(value)
            except ValueError:
                pass

    def _send_control_cmd(self, motor: Motor, cmd: int, can_id: Optional[int] = None):
        target_id = motor.SlaveID if can_id is None else int(can_id)
        self.send_std(target_id, bytes([0xFF] * 7 + [cmd & 0xFF]))
        self.recv_once(timeout=self.receive_timeout)

    def control_cmd(self, motor_or_id, cmd: int):
        if isinstance(motor_or_id, Motor):
            can_id = motor_or_id.SlaveID
        else:
            can_id = int(motor_or_id)
        self.send_std(can_id, bytes([0xFF] * 7 + [cmd & 0xFF]))
        self.recv_once(timeout=self.receive_timeout)

    def enable(self, motor: Motor):
        self._send_control_cmd(motor, 0xFC)
        motor.isEnable = True

    def enable_old(self, motor: Motor, ControlMode: Control_Type):
        enable_id = ((int(ControlMode) - 1) << 2) + motor.SlaveID
        self._send_control_cmd(motor, 0xFC, can_id=enable_id)
        motor.isEnable = True

    def disable(self, motor: Motor):
        self._send_control_cmd(motor, 0xFD)
        motor.isEnable = False

    def enable_all(self):
        seen = set()
        for motor in self.motors_map.values():
            if motor.SlaveID in seen:
                continue
            seen.add(motor.SlaveID)
            self.enable(motor)

    def disable_all(self):
        seen = set()
        for motor in self.motors_map.values():
            if motor.SlaveID in seen:
                continue
            seen.add(motor.SlaveID)
            self.disable(motor)

    def set_zero_position(self, motor: Motor):
        self._send_control_cmd(motor, 0xFE)

    def refresh_motor_status(self, motor: Motor):
        payload = bytes([motor.SlaveID & 0xFF, (motor.SlaveID >> 8) & 0xFF, 0xCC, 0, 0, 0, 0, 0])
        self.send_std(0x7FF, payload)
        self.recv_once(timeout=self.receive_timeout)

    def controlMIT(self, motor: Motor, kp: float, kd: float, q: float, dq: float, tau: float):
        if motor.SlaveID not in self.motors_map:
            raise KeyError(f"motor id 0x{motor.SlaveID:X} is not registered")

        q_max, dq_max, tau_max = motor.limit_param
        kp_uint = float_to_uint(kp, 0.0, 500.0, 12)
        kd_uint = float_to_uint(kd, 0.0, 5.0, 12)
        q_uint = float_to_uint(q, -q_max, q_max, 16)
        dq_uint = float_to_uint(dq, -dq_max, dq_max, 12)
        tau_uint = float_to_uint(tau, -tau_max, tau_max, 12)

        data = bytearray(8)
        data[0] = (q_uint >> 8) & 0xFF
        data[1] = q_uint & 0xFF
        data[2] = (dq_uint >> 4) & 0xFF
        data[3] = ((dq_uint & 0x0F) << 4) | ((kp_uint >> 8) & 0x0F)
        data[4] = kp_uint & 0xFF
        data[5] = (kd_uint >> 4) & 0xFF
        data[6] = ((kd_uint & 0x0F) << 4) | ((tau_uint >> 8) & 0x0F)
        data[7] = tau_uint & 0xFF

        self.send_std(motor.SlaveID + CONTROL_ID_OFFSET[Control_Type.MIT], bytes(data))
        self.recv_once(timeout=self.receive_timeout)

    def control_mit(self, motor: Motor, kp: float, kd: float, q: float, dq: float, tau: float):
        self.controlMIT(motor, kp, kd, q, dq, tau)

    def control_Pos_Vel(self, motor: Motor, P_desired: float, V_desired: float):
        payload = pack_f32_le(P_desired) + pack_f32_le(V_desired)
        self.send_std(motor.SlaveID + CONTROL_ID_OFFSET[Control_Type.POS_VEL], payload)
        self.recv_once(timeout=self.receive_timeout)

    def control_pos_vel(self, motor: Motor, pos: float, vel: float):
        self.control_Pos_Vel(motor, pos, vel)

    def control_Vel(self, motor: Motor, Vel_desired: float):
        payload = pack_f32_le(Vel_desired) + b"\x00\x00\x00\x00"
        self.send_std(motor.SlaveID + CONTROL_ID_OFFSET[Control_Type.VEL], payload)
        self.recv_once(timeout=self.receive_timeout)

    def control_vel(self, motor: Motor, vel: float):
        self.control_Vel(motor, vel)

    def control_pos_force(self, motor: Motor, Pos_des: float, Vel_des: int, i_des: int):
        payload = pack_f32_le(Pos_des) + struct.pack("<HH", int(Vel_des) & 0xFFFF, int(i_des) & 0xFFFF)
        self.send_std(motor.SlaveID + CONTROL_ID_OFFSET[Control_Type.Torque_Pos], payload)
        self.recv_once(timeout=self.receive_timeout)

    def control_Pos_Vel_CSP(self, motor: Motor, P_desired: float, V_desired: float):
        payload = pack_f32_le(P_desired) + pack_f32_le(V_desired)
        self.send_std(motor.SlaveID + CONTROL_ID_OFFSET[Control_Type.POS_VEL_CSP], payload)
        self.recv_once(timeout=self.receive_timeout)

    def control_pos_vel_csp(self, motor: Motor, pos: float, vel: float):
        self.control_Pos_Vel_CSP(motor, pos, vel)

    def control_Vel_CSP(self, motor: Motor, Vel_desired: float):
        payload = pack_f32_le(Vel_desired) + b"\x00\x00\x00\x00"
        self.send_std(motor.SlaveID + CONTROL_ID_OFFSET[Control_Type.VEL_CSP], payload)
        self.recv_once(timeout=self.receive_timeout)

    def control_vel_csp(self, motor: Motor, vel: float):
        self.control_Vel_CSP(motor, vel)

    def control_Tor_CSP(self, motor: Motor, Tor_desired: float):
        payload = pack_f32_le(Tor_desired) + b"\x00\x00\x00\x00"
        self.send_std(motor.SlaveID + CONTROL_ID_OFFSET[Control_Type.Torque_CSP], payload)
        self.recv_once(timeout=self.receive_timeout)

    def control_tor_csp(self, motor: Motor, tor: float):
        self.control_Tor_CSP(motor, tor)

    def __read_RID_param(self, motor: Motor, RID: int):
        payload = bytes([motor.SlaveID & 0xFF, (motor.SlaveID >> 8) & 0xFF, 0x33, int(RID) & 0xFF, 0, 0, 0, 0])
        self.send_std(0x7FF, payload)

    def __write_motor_param_bytes(self, motor: Motor, RID: int, data4: bytes):
        data4 = bytes(data4[:4]).ljust(4, b"\x00")
        payload = bytes([motor.SlaveID & 0xFF, (motor.SlaveID >> 8) & 0xFF, 0x55, int(RID) & 0xFF]) + data4
        self.send_std(0x7FF, payload)

    def __write_motor_param(self, motor: Motor, RID: int, value):
        rid = int(RID)
        if rid in UINT_PARAM_RIDS:
            data4 = pack_u32_le(int(value))
        else:
            data4 = pack_f32_le(float(value))
        self.__write_motor_param_bytes(motor, rid, data4)

    def write_motor_param(self, motor: Motor, RID: int, data):
        if isinstance(data, (bytes, bytearray)):
            self.__write_motor_param_bytes(motor, int(RID), bytes(data))
        elif isinstance(data, (list, tuple)):
            self.__write_motor_param_bytes(motor, int(RID), bytes(int(x) & 0xFF for x in data[:4]))
        else:
            self.__write_motor_param(motor, int(RID), data)

    def recv_set_param_data(self, timeout: Optional[float] = None):
        return self.recv_once(timeout=self.receive_timeout if timeout is None else timeout)

    def switchControlMode(self, motor: Motor, ControlMode: Control_Type) -> bool:
        rid = int(DM_variable.CTRL_MODE)
        motor.temp_param_dict.pop(rid, None)
        self.__write_motor_param_bytes(motor, rid, pack_u32_le(int(ControlMode)))
        return self._wait_param(motor, rid, expected=int(ControlMode), is_uint=True)

    def read_motor_param(self, motor: Motor, RID: int):
        rid = int(RID)
        motor.temp_param_dict.pop(rid, None)
        self.__read_RID_param(motor, rid)
        deadline = time.time() + 1.0
        while time.time() < deadline:
            self.recv_set_param_data(timeout=0.05)
            if rid in motor.temp_param_dict:
                return motor.temp_param_dict[rid]
        return None

    def change_motor_param(self, motor: Motor, RID: int, data) -> bool:
        rid = int(RID)
        motor.temp_param_dict.pop(rid, None)
        self.__write_motor_param(motor, rid, data)
        return self._wait_param(
            motor,
            rid,
            expected=int(data) if rid in UINT_PARAM_RIDS else float(data),
            is_uint=rid in UINT_PARAM_RIDS,
        )

    def save_motor_param(self, motor: Motor, save_code: int = 0x00):
        self.disable(motor)
        payload = bytes([motor.SlaveID & 0xFF, (motor.SlaveID >> 8) & 0xFF, 0xAA, save_code & 0xFF, 0, 0, 0, 0])
        self.send_std(0x7FF, payload)
        time.sleep(0.1)
        self.recv_once(timeout=self.receive_timeout)

    def change_limit_param(self, Motor_Type: DM_Motor_Type, PMAX: float, VMAX: float, TMAX: float):
        LIMIT_PARAM[DM_Motor_Type(Motor_Type)] = (float(PMAX), float(VMAX), float(TMAX))

    def changeMotorLimit(self, motor: Motor, P_MAX: float, Q_MAX: float, T_MAX: float):
        self.change_limit_param(motor.MotorType, P_MAX, Q_MAX, T_MAX)
        motor.limit_param = LIMIT_PARAM[motor.MotorType]

    def _wait_param(self, motor: Motor, rid: int, *, expected, is_uint: bool, timeout: float = 1.0) -> bool:
        deadline = time.time() + timeout
        while time.time() < deadline:
            self.recv_set_param_data(timeout=0.05)
            if rid not in motor.temp_param_dict:
                continue
            value = motor.temp_param_dict[rid]
            if is_uint:
                return int(value) == int(expected)
            return abs(float(value) - float(expected)) < 0.1
        return False


Motor_Control = MotorControl
