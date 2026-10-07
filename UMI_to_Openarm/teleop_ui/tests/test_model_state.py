import math
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from model_state import DisplayModel
URDF=Path(__file__).resolve().parents[2]/'UMI_to_arm/arm/mujoco_sim/urdf/openarm_bimanual.urdf'


class DisplayTests(unittest.TestCase):
    def setUp(self):self.model=DisplayModel(URDF.read_text())
    def test_complete_default_model_without_feedback(self):
        pose,status=self.model.snapshot(1)
        self.assertEqual(pose['openarm_left_joint4'],math.pi/2)
        self.assertEqual(pose['openarm_right_joint4'],math.pi/2)
        for side in ('left','right'):
            self.assertIn('默认姿态预览',status[side])
            self.assertTrue(set(self.model.groups[side]).issubset(pose))
        self.assertEqual(len({j['child'] for j in self.model.joints}),len(self.model.joints))
        for joint in self.model.joints:
            xyz,q=self.model.transform(joint,pose)
            self.assertAlmostEqual(sum(v*v for v in q),1,places=6)
    def test_partial_feedback_never_claims_real_arm(self):
        self.model.receive(['openarm_left_joint1'],[.3],1)
        pose,status=self.model.snapshot(1.1)
        self.assertIn('默认姿态预览',status['left'])
        self.assertEqual(pose['openarm_left_joint1'],0)
    def test_real_feedback_then_hold_last_pose(self):
        names=self.model.groups['left'];self.model.receive(names,[.1]*7,1)
        pose,status=self.model.snapshot(1.1)
        self.assertEqual(status['left'],'实时反馈')
        self.assertEqual(pose[names[3]],.1)
        pose,status=self.model.snapshot(2)
        self.assertIn('反馈中断',status['left'])
        self.assertEqual(pose[names[3]],.1)
        self.assertIn('默认姿态预览',status['right'])
    def test_disabled_arm_is_explicit_preview(self):
        names=self.model.groups['right'];self.model.receive(names,[.2]*7,1)
        pose,status=self.model.snapshot(1.1,mode='left')
        self.assertIn('未启用',status['right'])
        self.assertEqual(pose[names[3]],math.pi/2)
    def test_gripper_mimic_uses_measured_source(self):
        joint=next(j for j in self.model.joints if j['name']=='openarm_left_finger_joint2')
        a,_=self.model.transform(joint,{'openarm_left_finger_joint1':.02})
        b,_=self.model.transform(joint,{'openarm_left_finger_joint1':0})
        self.assertAlmostEqual(sum((x-y)**2 for x,y in zip(a,b)),.02**2)
