"""Own the isolated visualization process; separate from the robot session."""
import json
import os
from pathlib import Path
import signal
import subprocess
import tempfile
import shutil
from backend import ROOT


class ModelView:
    def __init__(self):self.proc=None;self.directory=None;self.log=None;self.mode='dual'
    @property
    def active(self):return self.proc is not None and self.proc.poll() is None
    def set_mode(self,mode):
        self.mode=mode
        if self.directory:
            path=self.directory/'selection.tmp';path.write_text(json.dumps({'mode':mode}));path.replace(self.directory/'selection.json')
    def start(self):
        if self.active:return
        self.close()
        self.directory=Path(tempfile.mkdtemp(prefix='openarm_ui_view_'));self.set_mode(self.mode)
        self.log=(self.directory/'view.log').open('w')
        env=os.environ.copy()
        for key in ('QT_PLUGIN_PATH','QT_QPA_PLATFORM_PLUGIN_PATH'):env.pop(key,None)
        script=ROOT/'teleop_ui/preview_ros.py'
        self.proc=subprocess.Popen(['bash','-c','source /opt/ros/humble/setup.bash; source /home/taoqiu/ros2_ws/install/setup.bash; exec /usr/bin/python3 "$1" --directory "$2"','ui-view',str(script),str(self.directory)],env=env,start_new_session=True,stdout=self.log,stderr=subprocess.STDOUT)
    def status(self):
        if self.directory:
            try:return json.loads((self.directory/'status.json').read_text())
            except (OSError,ValueError):pass
        return None
    def close(self):
        if self.active:
            os.killpg(self.proc.pid,signal.SIGINT)
            try:self.proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                os.killpg(self.proc.pid,signal.SIGTERM)
                try:self.proc.wait(timeout=2)
                except subprocess.TimeoutExpired:os.killpg(self.proc.pid,signal.SIGKILL);self.proc.wait()
        self.proc=None
        if self.log:self.log.close();self.log=None
        if self.directory:shutil.rmtree(self.directory);self.directory=None
