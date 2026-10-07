"""Desktop check: complete isolated URDF preview, no arm/camera/controller startup."""
import json
from pathlib import Path
import sys
import time
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from PySide6.QtWidgets import QApplication
from app import Window

root=Path(__file__).resolve().parents[2]
app=QApplication([]);window=Window(demo=True);window.demo=False
window.resize(1200,800);window.show();app.processEvents()
window.model_view.start()
try:
    deadline=time.monotonic()+30
    while time.monotonic()<deadline and not window.embedding:
        app.processEvents();time.sleep(.02)
        if window.model_view.proc.poll() is not None:
            raise RuntimeError((window.model_view.directory/'view.log').read_text()[-4000:])
    assert window.embedding,'isolated preview did not embed'
    assert window.embedding.is_attached()
    deadline=time.monotonic()+4
    while time.monotonic()<deadline:app.processEvents();time.sleep(.02)
    status=window.model_view.status();assert status,'no model state'
    assert all('默认姿态预览' in state for state in status.values()),status
    output=root/'teleop_ui/previews/complete_static_model.png'
    app.primaryScreen().grabWindow(int(window.winId())).save(str(output))
    log=(window.model_view.directory/'view.log').read_text()
    assert 'Error retrieving file' not in log,log[-3000:]
    print('PASS: isolated model, full joint transforms, default preview labels, real RViz embedding; no hardware')
    print('DISPLAY LOG:',log[-2200:])
finally:window.close()
