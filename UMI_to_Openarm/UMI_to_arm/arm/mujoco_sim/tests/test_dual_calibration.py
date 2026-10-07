"""Offline shared confirmation and independent per-camera calibration tests."""
from pathlib import Path
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import patch
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import openarm_vio_teleop as teleop


class Source:
    def __init__(self, rotation, age=0.01):
        self.pose = np.eye(4)
        self.pose[:3, :3] = rotation
        self.elapsed = age
    def latest(self):
        return self.pose
    def age(self):
        return self.elapsed


class DualCalibrationTests(unittest.TestCase):
    def test_one_gate_releases_both_without_keyboard_reads(self):
        with tempfile.TemporaryDirectory() as folder:
            state = Path(folder)
            results = {}
            errors = []
            rotations = {'left': np.eye(3),
                         'right': np.array([[0., -1., 0.], [1., 0., 0.], [0., 0., 1.]])}
            # Flange approach points horizontally; two cameras have independent yaw.
            rcf = np.array([[1., 0., 0.], [0., 0., -1.], [0., 1., 0.]])
            def worker(side):
                try:
                    teleop._dual_mark(state, 'vio', side)
                    if teleop._dual_wait(state, 'calibrate_go', None, 'test'):
                        results[side] = teleop.calibrate_rbw_base(Source(rotations[side]), rcf, confirm=False, max_age=0.5)
                        teleop._dual_mark(state, 'calib', side)
                except Exception as exc:
                    errors.append(exc)
            with patch.object(teleop, '_tty_input', side_effect=AssertionError('worker must not read terminal')), patch.object(teleop, 'print'):
                threads = [threading.Thread(target=worker, args=(side,), daemon=True) for side in rotations]
                for thread in threads:
                    thread.start()
                try:
                    deadline = time.monotonic() + 2
                    while not all((state / f'vio.{side}').exists() for side in rotations):
                        if time.monotonic() > deadline:
                            self.fail('workers did not announce readiness')
                        time.sleep(0.01)
                    self.assertEqual(results, {})
                finally:
                    (state / 'calibrate_go').touch()
                    for thread in threads:
                        thread.join(2)
                self.assertFalse(errors)
                self.assertTrue(all(not thread.is_alive() for thread in threads))
                for side in rotations:
                    self.assertIsNotNone(results[side])
                    np.testing.assert_allclose(results[side] @ results[side].T, np.eye(3), atol=1e-12)
                    self.assertTrue((state / f'calib.{side}').exists())
                self.assertFalse(np.allclose(results['left'], results['right']))

    def test_stale_or_missing_pose_does_not_calibrate(self):
        with patch.object(teleop, '_tty_input', side_effect=AssertionError('unexpected prompt')), patch.object(teleop, 'print'):
            self.assertIsNone(teleop.calibrate_rbw_base(Source(np.eye(3), age=2), np.eye(3), confirm=False, max_age=0.5))
            missing = Source(np.eye(3)); missing.pose = None
            self.assertIsNone(teleop.calibrate_rbw_base(missing, np.eye(3), confirm=False, max_age=0.5))

    def test_stop_cancels_gate_wait(self):
        with tempfile.TemporaryDirectory() as folder, patch.object(teleop, 'print'):
            stop = Path(folder) / 'stop'; stop.touch()
            self.assertFalse(teleop._dual_wait(Path(folder), 'calibrate_go', stop, 'test'))

    def test_single_arm_still_asks_for_confirmation(self):
        with patch.object(teleop, '_tty_input') as prompt, patch.object(teleop, 'print'):
            teleop.calibrate_rbw_base(Source(np.eye(3)), np.eye(3))
            prompt.assert_called_once()


class DualPreparationTests(unittest.TestCase):
    def test_both_start_before_either_completes(self):
        with tempfile.TemporaryDirectory() as folder, patch.object(teleop, 'print'):
            state = Path(folder)
            started = {side: threading.Event() for side in ('left', 'right')}
            finish = threading.Event()
            errors = []
            def worker(side):
                try:
                    if teleop._dual_prepare_gate(state, side, None):
                        started[side].set()
                        if not finish.wait(3):
                            raise AssertionError('preparation was never released')
                        teleop._dual_mark(state, 'ready', side)
                except Exception as exc:
                    errors.append(exc)
            left = threading.Thread(target=worker, args=('left',), daemon=True)
            right = threading.Thread(target=worker, args=('right',), daemon=True)
            left.start()
            try:
                deadline = time.monotonic() + 2
                while not (state / 'prepare.left').exists():
                    if time.monotonic() > deadline:
                        self.fail('left did not join preparation gate')
                    time.sleep(0.01)
                self.assertFalse(started['left'].is_set())
                right.start()
                self.assertTrue(started['left'].wait(2))
                self.assertTrue(started['right'].wait(2))
                # Both ready movements have started while neither has finished.
                self.assertFalse((state / 'ready.left').exists())
                self.assertFalse((state / 'ready.right').exists())
            finally:
                finish.set()
                (state / 'prepare.right').touch()
                left.join(2)
                if right.ident is not None:
                    right.join(2)
            self.assertFalse(errors)

    def test_cancelled_preparation_gate(self):
        with tempfile.TemporaryDirectory() as folder, patch.object(teleop, 'print'):
            state = Path(folder)
            stop = state / 'stop'; stop.touch()
            self.assertFalse(teleop._dual_prepare_gate(state, 'right', stop))
