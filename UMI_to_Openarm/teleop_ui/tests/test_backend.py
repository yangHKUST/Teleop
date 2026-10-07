import json
import os
from pathlib import Path
import sys
import tempfile
import time
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from backend import Session, command


class BackendTests(unittest.TestCase):
    def test_commands_match_existing_modes(self):
        for mode in ['left','right','dual']:
            args,env=command(mode,'developer',True,Path('/tmp/example'))
            self.assertIn('--bridge',args); self.assertIn('--vio-viewer',args)
            self.assertEqual(args[args.index('--output-mode')+1],'developer')
            if mode=='dual':
                self.assertNotIn('--arm',args)
            else:
                self.assertEqual(args[args.index('--arm')+1],mode)
                self.assertIn('--staged',args); self.assertIn('CYPERSTEREO_SERIAL',env)

    def test_real_controlling_tty_confirmation_and_control(self):
        session=Session()
        code="""import os,sys,termios,tty,time
with open('/dev/tty','r') as t:
 print('按 Enter 同时确认左右方向标定……',flush=True)
 t.readline()
 print('CONFIRMED',flush=True)
 tty.setraw(0)
 k=os.read(0,1)
 print('KEY='+k.decode(),flush=True)
"""
        session.start('dual','teaching',False,argv=[sys.executable,'-u','-c',code])
        try:
            text=''; deadline=time.monotonic()+3
            while not session.prompt and time.monotonic()<deadline:
                text+=session.read();time.sleep(.01)
            self.assertTrue(session.prompt,text)
            self.assertFalse(session.action('s')) # No running cores yet.
            self.assertTrue(session.confirm())
            self.assertFalse(session.confirm()) # Duplicate confirmation rejected.
            deadline=time.monotonic()+3
            while 'CONFIRMED' not in text and time.monotonic()<deadline:
                text+=session.read();time.sleep(.01)
            session.running={'left','right'}
            self.assertTrue(session.action('s'))
            session.proc.wait(timeout=3)
            text+=session.read()
            self.assertIn('KEY=s',text)
        finally:
            if session.active: session.stop();session.proc.wait(timeout=3)
            session.close_fd()

    def test_record_tail_partial_line_and_side_gate(self):
        session=Session()
        with tempfile.TemporaryDirectory() as folder:
            session.logs=Path(folder); path=session.logs/'left.log'
            record=json.dumps({'kind':'telemetry','side':'left','state':'RUNNING'})
            path.write_text(record)
            self.assertEqual(session.records(),[])
            with path.open('a') as file:file.write('\n')
            self.assertEqual(len(session.records()),1)
            self.assertEqual(session.running,{'left'})
            self.assertEqual(session.records(),[])

    def test_enter_does_not_accept_arbitrary_output(self):
        session=Session(); self.assertFalse(session.confirm())

    def test_mode_stays_locked_during_child_cleanup(self):
        session=Session()
        code="import os,time,signal; signal.signal(signal.SIGHUP,signal.SIG_IGN); pid=os.fork(); time.sleep(.7 if pid==0 else .2)"
        session.start('right','teaching',False,argv=[sys.executable,'-u','-c',code])
        try:
            deadline=time.monotonic()+2
            while session.proc.poll() is None and time.monotonic()<deadline:
                self.assertTrue(session.active)
                time.sleep(.01)
            self.assertIsNotNone(session.proc.poll())
            self.assertTrue(session.active, 'child cleanup must keep the session active')
            while session.active and time.monotonic()<deadline:
                time.sleep(.01)
            self.assertFalse(session.active)
        finally:
            session.close_fd()

    def test_ros_can_failure_reported_once(self):
        session=Session()
        with tempfile.TemporaryDirectory() as folder:
            session.ros_log=Path(folder)/'ros2.log'
            session.ros_log.write_text('[ERROR] Socket error: Failed to initialize socket for interface: can1\n')
            records=session.records()
            self.assertEqual(len(records),1)
            self.assertEqual(records[0]['category'],'hardware')
            self.assertIn('can1',records[0]['message'])
            self.assertEqual(session.records(),[])

if __name__=='__main__':unittest.main()
