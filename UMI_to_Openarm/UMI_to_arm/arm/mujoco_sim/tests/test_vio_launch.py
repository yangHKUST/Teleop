"""No camera or robot needed: verify the environment seen by the VIO child."""
import os
from pathlib import Path
import subprocess
import sys
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from vio_launch import vio_environment


class VioLaunchTests(unittest.TestCase):
    def test_default_disables_windows_and_preserves_camera_settings(self):
        original = {"CYPERSTEREO_SERIAL": "s200085", "VIO_POSE_ZMQ_ENDPOINT": "tcp://127.0.0.1:5565"}
        env = vio_environment(environ=original)
        self.assertEqual(env["VIO_HEADLESS"], "1")
        self.assertEqual(env["CYPERSTEREO_SERIAL"], original["CYPERSTEREO_SERIAL"])
        self.assertEqual(env["VIO_POSE_ZMQ_ENDPOINT"], original["VIO_POSE_ZMQ_ENDPOINT"])
        self.assertNotIn("VIO_HEADLESS", original)

    def test_explicit_viewer_removes_presence_flag_even_zero(self):
        for value in ("1", "0", ""):
            original = {"VIO_HEADLESS": value}
            self.assertNotIn("VIO_HEADLESS", vio_environment(True, original))
            self.assertEqual(original["VIO_HEADLESS"], value)

    def test_child_receives_both_modes(self):
        for enabled in (False, True):
            env = vio_environment(enabled)
            result = subprocess.check_output([sys.executable, "-c", "import os; print('VIO_HEADLESS' in os.environ)"], env=env, text=True)
            self.assertEqual(result.strip(), str(not enabled))
