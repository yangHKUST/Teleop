"""Damiao motor control over CANable2/SLCAN.

This package mirrors the official Python ``DM_CAN.py`` API where practical,
but sends raw CAN frames through python-can instead of the old USB-CAN serial
packet format.
"""

from .core import (
    Control_Mode,
    Control_Mode_Code,
    Control_Type,
    DM_REG,
    DM_Motor_Type,
    DM_variable,
    Feedback,
    Motor,
    MotorControl,
    Motor_Control,
    pack_f32_le,
    parse_feedback,
)

__all__ = [
    "Control_Type",
    "Control_Mode",
    "Control_Mode_Code",
    "DM_REG",
    "DM_Motor_Type",
    "DM_variable",
    "Feedback",
    "Motor",
    "MotorControl",
    "Motor_Control",
    "pack_f32_le",
    "parse_feedback",
]
