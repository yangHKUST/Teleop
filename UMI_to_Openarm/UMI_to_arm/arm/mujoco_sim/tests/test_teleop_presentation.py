"""Offline tests for terminal/logging, persistence, keyboard and missing gripper."""
import contextlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from teleop_output import TeleopOutput
from teleop_keys import KeyRelay
import openarm_umi_core as core

class PresentationTests(unittest.TestCase):
    def test_modes_log_full_data_but_terminal_only_summary(self):
        for mode in ['teaching','developer']:
            with tempfile.TemporaryDirectory() as folder:
                stream=io.StringIO()
                with contextlib.redirect_stdout(stream):
                    out=TeleopOutput('right',mode,Path(folder)/'run.log')
                    metrics=dict(state='RUNNING',ik='accepted',vio_fresh=True,vio_age_s=0.01,
                                 feedback_ok=True,feedback_age_s=None,position_error_m=0,
                                 orientation_error_rad=0,max_joint_delta_rad=0,tracking_error_rad=0,
                                 step_fraction=1,gripper='disabled')
                    out.status(metrics,dict(q_measured=None,q_command=[0]*7,ee_measured=None,
                                            ee_command={'position_m':[0,0,0]},ee_target={'position_m':[1,0,0]}))
                    out.close()
                text=stream.getvalue()
                self.assertNotIn('q_command',text)
                self.assertNotIn('ee_target',text)
                record=json.loads((Path(folder)/'run.log').read_text().splitlines()[0])
                self.assertIsNone(record['q_measured'])
                self.assertEqual(record['q_command'],[0]*7)
                self.assertTrue('STAT' in text if mode=='developer' else '跟随运行中' in text)
                self.assertFalse(list(Path(folder).glob('*.csv')))

    def test_transitions_only_print_on_change(self):
        stream=io.StringIO()
        with contextlib.redirect_stdout(stream):
            out=TeleopOutput('left')
            for _ in range(5):
                out.transition('control','PAUSED_FEEDBACK',{'PAUSED_FEEDBACK':'反馈暂停','RUNNING':'恢复'})
            out.transition('control','RUNNING',{'RUNNING':'恢复'})
        self.assertEqual(stream.getvalue().count('反馈暂停'),1)
        self.assertEqual(stream.getvalue().count('恢复'),1)

    def test_save_restore_each_arm_is_independent(self):
        with tempfile.TemporaryDirectory() as folder, patch.object(core,'REPO_ROOT',Path(folder)):
            right=core.default_ready_q('right'); right[0]=0.1
            left=core.default_ready_q('left'); left[0]=-0.2
            core.save_ready_q(right,'right');core.save_ready_q(left,'left')
            core.restore_default_ready_q('left')
            np.testing.assert_allclose(core.load_ready_q('left'),core.default_ready_q('left'))
            np.testing.assert_allclose(core.load_ready_q('right'),right)
            core.restore_default_ready_q('right')
            self.assertFalse(core.ready_file('right').exists())
            np.testing.assert_allclose(core.load_ready_q('right'),core.default_ready_q('right'))

    def test_restore_failure_keeps_custom_file(self):
        with tempfile.TemporaryDirectory() as folder, patch.object(core,'REPO_ROOT',Path(folder)):
            q=core.default_ready_q();q[0]=0.1;core.save_ready_q(q)
            with patch.object(Path,'unlink',side_effect=PermissionError('denied')):
                with self.assertRaises(PermissionError):core.restore_default_ready_q()
            np.testing.assert_allclose(core.load_ready_q(),q)

    def test_dual_relay_delayed_reader_gets_events_once(self):
        with tempfile.TemporaryDirectory() as folder:
            left=KeyRelay(Path(folder)/'keys.json');right=KeyRelay(left.path)
            left.publish(['s']);left.publish([]);left.publish(['r']);left.publish(['h'])
            self.assertEqual(right.consume(),['s','r','h'])
            self.assertEqual(right.consume(),[])

    def test_main_keyboard_updates_ready_and_missing_gripper_skips(self):
        import openarm_vio_teleop as app
        class FakeArm:
            gripper_max_m=0.044
            def __init__(self,**kwargs):
                self.q=core.default_ready_q();self.q[0]=0.05
            def wait_for_joints(self):return self.q.copy()
            def joint_feedback(self):return self.q.copy(),0.001
            def send(self,q):self.q=q.copy()
            def read_joints(self):return self.q.copy()
            def emergency_stop(self):pass
            def resume(self):pass
            def freeze(self):pass
            def close(self):pass
        class FakeKeys:
            def __init__(self):self.count=0
            def start(self):pass
            def stop(self):pass
            def read_keys(self):
                self.count+=1
                if self.count<=3:return [['s'],['r'],['h']][self.count-1]
                raise KeyboardInterrupt
        with tempfile.TemporaryDirectory() as folder:
            log=Path(folder)/'run.log'
            argv=['teleop','--synthetic','--bridge','--no-ready-move','--log-file',str(log)]
            with patch.object(core,'REPO_ROOT',Path(folder)),patch.object(sys,'argv',argv), \
                 patch.object(app,'OpenArmBridge',FakeArm),patch.object(app,'KeyboardReader',FakeKeys), \
                 patch.object(app,'HandheldGripper',side_effect=OSError('device missing')), \
                 patch.object(app,'save_home_q'),patch.object(app,'move_arm_to_ready'), \
                 contextlib.redirect_stdout(io.StringIO()) as stream:
                self.assertEqual(app.main(),0)
                app.output.close()
            self.assertIn('已自动跳过开合跟随',stream.getvalue())
            self.assertFalse((Path(folder)/'cartesian_ready_q_openarm.json').exists())
            records=[json.loads(line) for line in log.read_text().splitlines()]
            saved=[r for r in records if r.get('category')=='ready' and r.get('data',{} ) and r['data'].get('source')=='custom']
            restored=[r for r in records if r.get('category')=='ready' and r.get('data',{}) and r['data'].get('immediate_motion') is False and r['data'].get('source')=='builtin_default']
            self.assertTrue(saved);self.assertTrue(restored)
            self.assertFalse(list(Path(folder).glob('*.csv')))

if __name__=='__main__':unittest.main()
