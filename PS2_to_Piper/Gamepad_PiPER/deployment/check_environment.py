"""Read-only install verification: no CAN connection or robot motion."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import numpy as np
import pygame
import viser
import yourdfpy
from pinocchio import casadi as cpin
from piper_sdk import C_PiperInterface_V2
from src.kinematic_pin import Arm_IK

root = Path(__file__).resolve().parents[1]
ik = Arm_IK(str(root / "piper/piper.urdf"))
assert ik.model.nq == 6
print("Python:", sys.executable)
print("运动学检查通过，零位位姿:", ik.get_fk(np.zeros(6)))
