"""Startup regression tests. SDK connections and robot commands are mocked."""
import contextlib
import io
import threading
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

import numpy as np

from teleop import app, teleop_real_arm
from teleop.cli import parse_args
from teleop.piper.driver import PiperDriver
from teleop.piper.safety import enable_and_wait
from teleop.record_data import act_columns, act_row, cmd_columns, cmd_row
from teleop.runtime.init_driver import init_driver
from teleop.runtime.piper_send_process import piper_sender
from teleop.runtime.context import RuntimeContext


class CliTests(unittest.TestCase):
    def test_single_can_selects_only_right_arm(self):
        args = parse_args(["--can", "can0"])
        self.assertEqual(args.arm_ports, {"right": "can0"})
        self.assertIsNone(args.can_left)

    def test_dual_default_and_swapped_ports(self):
        self.assertEqual(parse_args([]).arm_ports, {"right": "can1", "left": "can0"})
        args = parse_args(["--can-left", "can1", "--can-right", "can0"])
        self.assertEqual(args.arm_ports, {"right": "can0", "left": "can1"})

    def test_ambiguous_or_shared_ports_are_rejected(self):
        for argv in (["--can", "can0", "--can-left", "can1"],
                     ["--can-left", "can0", "--can-right", "can0"]):
            with self.subTest(argv=argv), contextlib.redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit) as exc:
                    parse_args(argv)
                self.assertEqual(exc.exception.code, 2)


class DriverTests(unittest.TestCase):
    def test_none_return_can_still_mean_enabled(self):
        driver = Mock(connected=True, can_port="can0")
        driver.enable.return_value = None
        driver.is_enabled.return_value = True
        self.assertTrue(enable_and_wait(driver, timeout_s=0, also_open_gripper=False))

    def test_enable_timeout_closes_driver_without_entering_motion_mode(self):
        driver = Mock(connected=True, can_port="can0")
        with patch("teleop.runtime.init_driver.PiperDriver", return_value=driver), \
             patch("teleop.runtime.init_driver.enable_and_wait", side_effect=RuntimeError("timeout")):
            with self.assertRaisesRegex(RuntimeError, "timeout"):
                init_driver("can0", False)
        driver.close.assert_called_once_with()
        driver.set_motion_mode.assert_not_called()
        driver.set_gripper.assert_not_called()

    def test_timeout_reports_missing_feedback_and_preserves_failure(self):
        driver = Mock(connected=True, can_port="can0")
        driver.is_enabled.return_value = False
        driver.enable_diagnostics.return_value = "missing_feedback=[1, 2, 3, 4, 5, 6]"
        with self.assertRaisesRegex(RuntimeError, r"\[can0\].*missing_feedback"):
            enable_and_wait(driver, timeout_s=0, also_open_gripper=False)

    def test_sdk_disconnect_is_idempotent_and_sends_no_commands(self):
        driver = PiperDriver("can0")
        sdk = Mock()
        driver._piper = sdk
        driver.connected = True
        driver.close()
        driver.close()
        sdk.DisconnectPort.assert_called_once_with()
        sdk.DisableArm.assert_not_called()
        sdk.JointCtrl.assert_not_called()
        self.assertFalse(driver.connected)

    def test_diagnostics_distinguish_missing_feedback_from_disabled_motors(self):
        driver = PiperDriver("can0")
        info = SimpleNamespace(Hz=0.0)
        for i in range(1, 7):
            setattr(info, f"motor_{i}", SimpleNamespace(
                can_id=0, foc_status_code=0,
                foc_status=SimpleNamespace(driver_enable_status=False),
            ))
        driver.get_low_speed_info = Mock(return_value=info)
        self.assertIn("no motor feedback", driver.enable_diagnostics())
        for i in range(1, 7):
            getattr(info, f"motor_{i}").can_id = 0x260 + i
        self.assertIn("missing_feedback=[]", driver.enable_diagnostics())
        self.assertNotIn("no motor feedback", driver.enable_diagnostics())


class SenderTests(unittest.TestCase):
    def test_dry_run_signals_ready_without_connecting_to_hardware(self):
        stop, ready = threading.Event(), threading.Event()
        readback = [float("nan")] * 6
        with patch("teleop.runtime.piper_send_process.signal.signal"), \
             patch("teleop.runtime.init_driver.PiperDriver") as driver_class:
            piper_sender("right", "can0", True, Mock(), stop, 100,
                         q_readback=readback, q_ready=ready)
        driver_class.assert_not_called()
        self.assertTrue(ready.is_set())
        self.assertFalse(stop.is_set())
        self.assertEqual(readback, [0.0] * 6)

    def test_initialization_failure_signals_parent(self):
        stop, ready = threading.Event(), threading.Event()
        with patch("teleop.runtime.piper_send_process.signal.signal"), \
             patch("teleop.runtime.piper_send_process.init_driver", side_effect=RuntimeError("enable timeout")):
            with self.assertRaisesRegex(RuntimeError, "enable timeout"):
                piper_sender("right", "can0", False, Mock(), stop, 100, q_ready=ready)
        self.assertTrue(stop.is_set())
        self.assertFalse(ready.is_set())

    def test_invalid_joint_readback_never_starts_sending(self):
        for readback in (None, [float("nan")] * 6):
            driver = Mock()
            stop, ready = threading.Event(), threading.Event()
            with self.subTest(readback=readback), \
                 patch("teleop.runtime.piper_send_process.signal.signal"), \
                 patch("teleop.runtime.piper_send_process.init_driver", return_value=driver), \
                 patch("teleop.runtime.piper_send_process.read_joint_radians", return_value=readback), \
                 patch("teleop.runtime.piper_send_process.piper_send_jointctrl") as send:
                with self.assertRaisesRegex(RuntimeError, "joint readback failed"):
                    piper_sender("right", "can0", False, Mock(), stop, 100,
                                 q_readback=[0] * 6, q_ready=ready)
                send.assert_not_called()
            self.assertTrue(stop.is_set())
            self.assertFalse(ready.is_set())
            driver.close.assert_called_once_with()


class RuntimeTests(unittest.TestCase):
    def test_single_and_dual_loop_dispatch_only_configured_arms(self):
        for sides in (("right",), ("right", "left")):
            arms = {side: SimpleNamespace(mode="AT_ZERO", last_q=np.zeros(6)) for side in sides}
            tv = Mock()
            tv.step.return_value = np.zeros(7)
            tv.step_left.return_value = np.ones(7)
            rt = RuntimeContext(teleoperator=tv, cam=None, viewers=[], arms=arms, rate=Mock())
            rt.rate.sleep.side_effect = [None, KeyboardInterrupt()]
            with self.subTest(sides=sides), \
                 patch.object(app, "_startup_arm") as startup, \
                 patch.object(app, "_check_sender") as check, \
                 patch.object(app, "_arm_step") as step, \
                 patch("teleop.recorder_pub.RecorderPub") as pub, \
                 patch("teleop.recorder_pub.build_record", return_value={}):
                app.run_loop(SimpleNamespace(dry_run=False), rt)
                self.assertEqual(startup.call_count, len(sides))
                self.assertEqual(check.call_count, len(sides))
                self.assertEqual([call.args[1] for call in step.call_args_list], list(arms.values()))
                pub.return_value.close.assert_called_once_with()

    def test_single_arm_build_has_only_one_sender_target(self):
        args = parse_args(["--can", "can0"])
        arm = Mock()
        with patch.object(app, "VuerTeleop"), patch.object(app, "init_camera", return_value=None), \
             patch.object(app, "_build_arm", return_value=arm) as build:
            rt = app.build_runtime(args)
        build.assert_called_once_with("right", "can0", False, False)
        self.assertEqual(list(rt.arms), ["right"])
        rt.close()
        rt.close()
        arm.stop_sender.assert_called_once_with()

    def test_partial_dual_build_cleans_up_first_arm_and_vuer(self):
        arm, tv = Mock(), Mock()
        with patch.object(app, "VuerTeleop", return_value=tv), \
             patch.object(app, "init_camera", return_value=None), \
             patch.object(app, "_build_arm", side_effect=[arm, RuntimeError("left build failed")]):
            with self.assertRaisesRegex(RuntimeError, "left build failed"):
                app.build_runtime(parse_args([]))
        arm.stop_sender.assert_called_once_with()
        tv.close.assert_called_once_with()

    def test_dead_sender_aborts_before_writing_zero(self):
        arm = SimpleNamespace(side="right", can_port="can0", q_ready=threading.Event(),
                              stop_event=threading.Event(), sender_proc=Mock(), cmd_shared=Mock())
        arm.sender_proc.is_alive.return_value = False
        with self.assertRaisesRegex(RuntimeError, "teleoperation aborted"):
            app._startup_arm(arm)
        arm.cmd_shared.get_lock.assert_not_called()

    def test_ready_with_invalid_readback_aborts(self):
        arm = SimpleNamespace(side="right", can_port="can0", q_ready=threading.Event(),
                              stop_event=threading.Event(), sender_proc=Mock(),
                              q_readback=[float("nan")] * 6, cmd_shared=Mock())
        arm.q_ready.set()
        arm.sender_proc.is_alive.return_value = True
        with self.assertRaisesRegex(RuntimeError, "no valid joint readback"):
            app._startup_arm(arm)
        arm.cmd_shared.get_lock.assert_not_called()

    def test_main_interrupt_and_startup_failure_close_without_zero_on_exit(self):
        for failure in (KeyboardInterrupt(), RuntimeError("enable failed")):
            arm = SimpleNamespace(cmd_shared=None)
            rt = Mock(arms={"right": arm})
            with self.subTest(failure=type(failure).__name__), \
                 patch.object(teleop_real_arm, "parse_args", return_value=parse_args(["--can", "can0"])), \
                 patch.object(app, "build_runtime", return_value=rt), \
                 patch.object(app, "run_loop", side_effect=failure):
                if isinstance(failure, KeyboardInterrupt):
                    teleop_real_arm.main()
                else:
                    with self.assertRaisesRegex(RuntimeError, "enable failed"):
                        teleop_real_arm.main()
            rt.close.assert_called_once_with()

    def test_single_arm_recordings_keep_fixed_csv_columns(self):
        rec = {"t": 1.0, "t_wall": 2.0, "r_cmd_q": list(range(6)), "r_act_q": list(range(6))}
        cmd, actual = cmd_row(rec), act_row(rec)
        self.assertEqual(len(cmd), len(cmd_columns()))
        self.assertEqual(len(actual), len(act_columns()))
        self.assertEqual(cmd[-9:], [""] * 9)
        self.assertEqual(actual[-8:], [""] * 8)


if __name__ == "__main__":
    unittest.main()
