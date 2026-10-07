"""Offline regression tests: no ROS, CAN, VIO or robot connection."""
import sys
import unittest
import threading
import time
from pathlib import Path
import numpy as np
import pinocchio as pin
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from openarm_urdf_ik import OpenArmDecoupledIk, _exp_so3, _so3_log
from openarm_umi_core import default_home_q
from openarm_bridge import OpenArmBridge

class IkRegression(unittest.TestCase):
    def initialized(self, side='right', **kwargs):
        k = OpenArmDecoupledIk(side=side, **kwargs)
        q = default_home_q(side)
        k.reset(q)
        k.set_posture(q)
        return k, q

    def test_stationary_both_arms(self):
        for side in ['left', 'right']:
            k, q = self.initialized(side)
            target = k.fk(q)
            for _ in range(20):
                result, ok, _ = k.ik6d(target)
                self.assertTrue(ok)
                np.testing.assert_allclose(result, q, atol=1e-10)

    def test_probe_and_failed_solve_do_not_change_state(self):
        k, q = self.initialized()
        warm = k._q_warm.copy()
        target = k.fk(q)
        target.translation += np.array([0.01, 0., 0.])
        k.ik6d(target, commit=False)
        np.testing.assert_array_equal(k._q_warm, warm)
        target.translation += np.array([10., 0., 0.])
        _, ok, _ = k.ik6d(target)
        self.assertFalse(ok)
        np.testing.assert_array_equal(k._q_warm, warm)

    def test_final_residual_and_orientation_rejection(self):
        k, q = self.initialized(max_iter=1, orientation_tol=1e-8)
        target = k.fk(q)
        target.rotation = target.rotation @ _exp_so3(np.array([0.5, 0., 0.]))
        result, ok, err = k.ik6d(target, max_delta=1e-6)
        final = k.fk(result)
        self.assertFalse(ok)
        self.assertAlmostEqual(err, np.linalg.norm(final.translation-target.translation), places=12)
        self.assertAlmostEqual(k.last_diagnostics['orientation_error_rad'],
                               np.linalg.norm(_so3_log(final.rotation.T@target.rotation)), places=12)

    def test_continuous_round_trip_and_rate_limit(self):
        for side in ['left', 'right']:
            k, q = self.initialized(side, reach_tol=0.001, orientation_tol=0.005)
            home = q.copy()
            target0 = k.fk(home)
            for phase in np.linspace(0, 2*np.pi, 121):
                target = target0.copy()
                target.translation += np.array([0.008*np.sin(phase), 0., 0.004*np.sin(phase)])
                target.rotation = target.rotation @ _exp_so3(np.array([0., 0.02*np.sin(phase), 0.]))
                result, ok, _ = k.ik6d(target, q_seed=q, max_delta=0.01)
                self.assertTrue(ok)
                self.assertLessEqual(np.max(np.abs(result-q)), 0.010000001)
                q = result
            self.assertLess(np.max(np.abs(q-home)), 0.03)

    def test_feedback_freshness_and_startup_timeout(self):
        # Construct only the feedback container, without opening ZMQ sockets.
        bridge = OpenArmBridge.__new__(OpenArmBridge)
        bridge._lock = threading.Lock()
        bridge._q_fb = None
        bridge._last_recv = 0.0
        self.assertIsNone(bridge.joint_feedback()[0])
        with self.assertRaises(TimeoutError):
            bridge.wait_for_joints(timeout=0.001, interval=0.001)
        bridge._q_fb = np.zeros(7)
        bridge._last_recv = time.monotonic() - 2.0
        with self.assertRaises(TimeoutError):
            bridge.wait_for_joints(timeout=0.001, interval=0.001)
        bridge._last_recv = time.monotonic()
        np.testing.assert_array_equal(bridge.wait_for_joints(), np.zeros(7))

    def test_rate_limited_target_advances_instead_of_stalling(self):
        for side in ['left', 'right']:
            k, seed = self.initialized(side, reach_tol=0.001, orientation_tol=0.005)
            goal_q = seed.copy()
            goal_q[0] += 0.15
            target = k.fk(goal_q)
            _, one_tick_ok, _ = k.ik6d(target, seed, commit=False, max_delta=0.005)
            self.assertFalse(one_tick_ok)
            warm = k._q_warm.copy()
            previous = seed.copy()
            moved = False
            for _ in range(120):
                result, ok, err = k.track_step(target, previous, max_delta=0.005)
                self.assertTrue(ok)
                self.assertLessEqual(np.max(np.abs(result-previous)), 0.005000001)
                moved |= np.max(np.abs(result-previous)) > 1e-7
                previous = result
                if err < 1e-5:
                    break
            self.assertTrue(moved)
            self.assertLess(err, 1e-5)
            np.testing.assert_array_equal(k._q_warm, warm)

    def test_invalid_inputs(self):
        k, q = self.initialized()
        with self.assertRaises(ValueError):
            k.reset(np.full(7, np.nan))
        with self.assertRaises(ValueError):
            k.set_posture(q, [-1]*7)
        with self.assertRaises(ValueError):
            k.ik6d(k.fk(q), dt=0)

if __name__ == '__main__':
    unittest.main()
