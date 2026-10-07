"""Arrival tolerance boundary; no actual robot."""
from pathlib import Path
import math
import sys
import unittest
from unittest.mock import patch
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import openarm_vio_teleop as teleop


class Arm:
    def __init__(self, degrees):self.q=np.full(7, math.radians(degrees))
    def send(self,q):pass
    def read_joints(self):return self.q.copy()
    def joint_feedback(self):return self.q.copy(),0.01


class ReadyToleranceTests(unittest.TestCase):
    def test_default_is_two_degrees(self):
        with patch.object(sys,'argv',['teleop']):
            self.assertAlmostEqual(teleop.parse_args().ready_tol,math.radians(2))
    def test_two_degree_boundary_accepted(self):
        with patch.object(teleop,'print'):
            for angle in (1.9,2.0):
                teleop.move_arm_to_ready(Arm(angle),np.zeros(7),math.radians(2),0.05,1000)
                self.assertTrue(teleop.output.last_ready_reached)
    def test_larger_error_not_accepted(self):
        with patch.object(teleop,'print'):
            teleop.move_arm_to_ready(Arm(2.1),np.zeros(7),math.radians(2),0.005,1000)
            self.assertFalse(teleop.output.last_ready_reached)

    def test_missing_or_stale_feedback_not_arrival(self):
        with patch.object(teleop,'print'):
            for measured,age in [(None,float('inf')),(np.zeros(7),1.0)]:
                arm=Arm(0)
                with patch.object(arm,'joint_feedback',return_value=(measured,age)):
                    teleop.move_arm_to_ready(arm,np.zeros(7),math.radians(2),0.005,1000)
                self.assertFalse(teleop.output.last_ready_reached)
