import os
os.environ['QT_QPA_PLATFORM']='offscreen'
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from app import Window


class UiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.app=QApplication.instance() or QApplication([])
    def setUp(self):self.window=Window();self.window.timer.stop()
    def tearDown(self):self.window.close()
    def test_terminal_is_not_command_entry(self):
        terminal=self.window.terminal; terminal.setFocus()
        QTest.keyClicks(terminal,'dangerous command')
        self.assertEqual(terminal.toPlainText(),'')
        QTest.keyClick(terminal,Qt.Key_Return)
        self.assertTrue(terminal.isReadOnly())
    def test_modes_and_original_ready_source(self):
        self.window.mode.setCurrentIndex(1)
        self.assertEqual(self.window.card_values['right','connection'].text(),'未启用')
        self.window.record({'side':'left','kind':'event','category':'ready','message':'准备配置','data':{'source':'builtin_default'}})
        self.assertEqual(self.window.card_values['left','source'].text(),'默认')
    def test_not_running_controls_disabled(self):
        self.assertTrue(self.window.start_button.isEnabled())
        self.assertTrue(all(not button.isEnabled() for button in self.window.controls.values()))
    def test_demo_never_launches_robot(self):
        demo=Window(demo=True);demo.timer.stop()
        demo.start()
        self.assertIsNone(demo.session.proc)
        self.assertFalse(demo.start_button.isEnabled());demo.close()


class RunningUiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.app=QApplication.instance() or QApplication([])
    def test_session_locks_selections_and_pause_label_follows_state(self):
        from unittest.mock import patch, PropertyMock
        window=Window();window.timer.stop()
        with patch('backend.Session.active',new_callable=PropertyMock,return_value=True):
            window.session.running={'left','right'}
            window.states={'left':'CLUTCH','right':'CLUTCH'}
            window.update_controls()
            self.assertFalse(window.mode.isEnabled())
            self.assertFalse(window.output.isEnabled())
            self.assertFalse(window.viewer.isEnabled())
            self.assertEqual(window.controls[' '].text(),'恢复跟随')
            self.assertTrue(window.controls['s'].isEnabled())
            window.session.stopping=True;window.update_controls()
            self.assertFalse(window.controls['s'].isEnabled())
        window.close()

    def test_hardware_failure_does_not_show_complete_model(self):
        window=Window();window.timer.stop()
        window.record({'side':'dual','kind':'event','category':'hardware','message':'CAN can1 初始化失败'})
        self.assertIn('CAN 初始化失败',window.card_values['left','connection'].text())
        self.assertIn('CAN 初始化失败',window.card_values['right','connection'].text())
        self.assertIn('没有关节反馈',window.model_footer.text())
        self.assertIn('can1',window.terminal.toPlainText())
        window.close()

if __name__=='__main__':unittest.main()
