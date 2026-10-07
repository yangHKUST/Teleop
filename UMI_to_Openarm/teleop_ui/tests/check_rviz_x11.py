"""Explicit desktop integration check: RViz only; no cameras/controllers/arm."""
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication,QWidget
from app import Window
from rviz_embed import find_rviz,NativeEmbedding

root=Path(__file__).resolve().parents[2]
config=root/'openarm_control/src/openarm_description/rviz/bimanual.rviz'
app=QApplication([]);window=Window(demo=True);window.timer.stop();window.show();app.processEvents()
proc=subprocess.Popen(['bash','-c','source /opt/ros/humble/setup.bash; exec rviz2 -d "$1"','rviz-test',str(config)],
    start_new_session=True,stdout=open('/tmp/openarm_ui_rviz_check.log','w'),stderr=subprocess.STDOUT)
embedding=None
try:
    deadline=time.monotonic()+20;xid=None
    while time.monotonic()<deadline and not xid:
        app.processEvents()
        if proc.poll() is not None:raise RuntimeError(f'RViz exited: {proc.returncode}')
        xid=find_rviz(os.getpid());time.sleep(.1)
    assert xid,'session-owned RViz window not found'
    from rviz_embed import X11
    c=X11()
    with c.guarded():print('Found:',xid,c.title(xid),flush=True)
    c.close()
    host=QWidget();host.setAttribute(Qt.WA_NativeWindow)
    window.model_layout.insertWidget(0,host,1);window.model_hint.hide();host.show();app.processEvents()
    ratio=host.devicePixelRatioF()
    host_id=int(host.winId()); QApplication.sync()
    embedding=NativeEmbedding(xid,host_id,int(host.width()*ratio),int(host.height()*ratio))
    assert embedding.is_attached(),'actual X parent mismatch'
    deadline=time.monotonic()+1
    while time.monotonic()<deadline:app.processEvents();time.sleep(.01)
    window.resize(1280,800);app.processEvents()
    embedding.resize(int(host.width()*ratio),int(host.height()*ratio))
    with embedding.connection.guarded():attrs=embedding.connection.attributes(xid)
    assert attrs is not None, f'RViz window disappeared, process status={proc.poll()}, log='+Path('/tmp/openarm_ui_rviz_check.log').read_text()[-1600:]
    assert attrs.width==int(host.width()*ratio) and attrs.height==int(host.height()*ratio),'resize mismatch'
    output=root/'teleop_ui/previews/rviz_embedded.png'
    app.primaryScreen().grabWindow(int(window.winId())).save(str(output))
    embedding.close();embedding=None
    assert proc.poll() is None,'detaching should not terminate RViz'
    print('PASS: real RViz discovery, native parent verification, resize and detach; no robot launched')
finally:
    if embedding:embedding.close()
    if proc.poll() is None:
        os.killpg(proc.pid,signal.SIGINT)
        try:proc.wait(timeout=10)
        except subprocess.TimeoutExpired:os.killpg(proc.pid,signal.SIGTERM);proc.wait(timeout=5)
    window.close()
