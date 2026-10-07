#!/usr/bin/env python3
"""Read-only visualization and PTY controls for existing UMI/OpenArm launchers."""
import argparse
import os
import re
import sys
import time
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont, QTextCursor
from PySide6.QtWidgets import (QApplication, QCheckBox, QComboBox, QFrame, QGridLayout,
    QHBoxLayout, QLabel, QMainWindow, QPushButton, QSplitter, QTextEdit,
    QVBoxLayout, QWidget)
from backend import Session, camera_config
from rviz_embed import find_rviz, NativeEmbedding, hide_window
from model_view import ModelView


class Terminal(QTextEdit):
    def __init__(self, confirm, action):
        super().__init__(); self.setReadOnly(True)
        self.confirm_callback = confirm; self.action_callback = action
        self.setFont(QFont('DejaVu Sans Mono', 11))
        self.document().setMaximumBlockCount(5000)
        self.setPlaceholderText('启动后的终端输出将显示在这里。点击此区域后按 Enter 确认当前提示。')

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key_Return, Qt.Key_Enter):
            if not event.isAutoRepeat(): self.confirm_callback()
            return
        keys = {Qt.Key_Space:' ', Qt.Key_H:'h', Qt.Key_S:'s', Qt.Key_R:'r', Qt.Key_Escape:'\x1b'}
        if event.key() in keys and event.modifiers() == Qt.NoModifier:
            if not event.isAutoRepeat(): self.action_callback(keys[event.key()])
            return
        # Read-only browsing and copying; Ctrl+C copies selected text, never exits.
        super().keyPressEvent(event)


class Window(QMainWindow):
    def __init__(self, demo=False):
        super().__init__(); self.setWindowTitle('遥操作'); self.resize(1440, 900)
        self.setMinimumSize(1050, 700)
        self.session = Session(); self.model_view = ModelView(); self.demo = demo; self.close_after_stop = False
        self.states = {}; self.card_values = {}; self.last_telemetry = {}
        self.foreign = None; self.rviz_container = None; self.last_embed = 0; self.embedding = None; self.embed_error = None
        self.exited_reported = True
        body=QWidget(); self.setCentralWidget(body); layout=QVBoxLayout(body)
        layout.setContentsMargins(24,16,24,16); layout.setSpacing(16)
        top=QHBoxLayout(); top.addStretch(1)  # Reserved upper-left space.
        self.mode=QComboBox(); self.mode.addItem('双臂','dual'); self.mode.addItem('左臂','left'); self.mode.addItem('右臂','right')
        self.output=QComboBox(); self.output.addItems(['教学','开发者'])
        self.theme=QComboBox(); self.theme.addItems(['浅色','深色'])
        for title, widget in [('控制模式',self.mode),('输出',self.output),('主题',self.theme)]:
            top.addWidget(QLabel(title)); top.addWidget(widget); top.addSpacing(12)
        layout.addLayout(top)
        self.lock_hint=QLabel('启动后锁定控制模式、输出方案及 VIO 窗口选项，退出完成后可更改。')
        self.lock_hint.setAlignment(Qt.AlignRight); self.lock_hint.setObjectName('muted'); layout.addWidget(self.lock_hint)
        split=QSplitter(Qt.Horizontal); layout.addWidget(split,1)
        model=QFrame(); model.setObjectName('panel'); ml=QVBoxLayout(model)
        self.model_layout=ml
        self.model_hint=QLabel('RViz 双臂实时模型\n\n启动控制系统后自动连接本会话的 RViz 窗口。\n显示机械臂反馈，不发送运动指令。')
        self.model_hint.setAlignment(Qt.AlignCenter); self.model_hint.setWordWrap(True); ml.addWidget(self.model_hint,1)
        self.model_footer=QLabel('鼠标拖动：旋转视角　　滚轮：缩放\n模型：尚无实时反馈')
        self.model_footer.setObjectName('muted'); ml.addWidget(self.model_footer)
        split.addWidget(model)
        right=QWidget(); rl=QVBoxLayout(right); rl.setContentsMargins(0,0,0,0); rl.setSpacing(16)
        cards=QFrame(); cards.setObjectName('panel'); grid=QGridLayout(cards)
        for col, side in enumerate(['left','right']):
            title=QLabel('左臂' if side=='left' else '右臂'); title.setObjectName('heading'); grid.addWidget(title,0,col*2,1,2)
            grid.addWidget(QLabel('相机：'+camera_config(side)[0]),1,col*2,1,2)
            for row,key,label in [(2,'connection','控制连接'),(3,'vision','视觉位姿'),(4,'gripper','手持夹爪'),(5,'ready','准备动作'),(6,'source','准备配置')]:
                grid.addWidget(QLabel(label),row,col*2)
                value=QLabel('未启动'); value.setWordWrap(True); grid.addWidget(value,row,col*2+1)
                self.card_values[side,key]=value
        rl.addWidget(cards)
        launch=QHBoxLayout(); launch.setContentsMargins(16,0,12,0); self.viewer=QCheckBox('显示 VIO 窗口'); launch.addWidget(self.viewer); launch.addStretch()
        self.start_button=QPushButton('启动系统'); self.start_button.setObjectName('primary'); self.start_button.clicked.connect(self.start)
        launch.addWidget(self.start_button); rl.addLayout(launch)
        console=QFrame(); console.setObjectName('panel'); cl=QVBoxLayout(console)
        header=QHBoxLayout(); self.console_title=QLabel('终端输出 · 教学'); header.addWidget(self.console_title); header.addStretch()
        self.follow=QCheckBox('跟随最新'); self.follow.setChecked(True); header.addWidget(self.follow); cl.addLayout(header)
        self.terminal=Terminal(self.confirm,self.action); cl.addWidget(self.terminal,1)
        self.terminal.verticalScrollBar().valueChanged.connect(self.scroll_changed)
        self.prompt_hint=QLabel('点击终端区域后按 Enter；不支持文字或命令输入。'); self.prompt_hint.setWordWrap(True); cl.addWidget(self.prompt_hint)
        rl.addWidget(console,1); split.addWidget(right); split.setSizes([630,770]); split.setChildrenCollapsible(False)
        buttons=QGridLayout(); self.controls={}
        items=[(' ','暂停跟随'),('h','返回准备位姿'),('s','保存新准备姿态'),('r','恢复默认准备姿态'),('exit','退出系统'),('\x1b','软件急停')]
        for col,(key,label) in enumerate(items):
            b=QPushButton(label); self.controls[key]=b; buttons.addWidget(b,0,col)
            b.clicked.connect(lambda checked=False,k=key: self.stop() if k=='exit' else self.action(k))
            if key=='\x1b': b.setObjectName('danger')
        tips={' ':'暂停手持增量跟随；原有平滑可能继续收敛到已有目标。', 'h':'返回准备末端位姿；不保证恢复相同关节构型。现有 H 操作也会解除软件急停。', 's':'分别保存有效实测关节角；双臂分别报告成功或失败。', 'r':'恢复默认配置，不直接回位；继续使用现有准备姿态参考逻辑。', 'exit':'正常退出时尝试回准备姿态；急停状态下退出保持冻结。', '\x1b':'仅运行阶段可用，执行原程序 Esc 软件急停。'}
        for k,b in self.controls.items(): b.setToolTip(tips[k])
        layout.addLayout(buttons)
        self.operation_hint=QLabel('双臂模式下操作作用于两侧；恢复默认仅修改配置，不立即执行回位动作。')
        self.operation_hint.setWordWrap(True); self.operation_hint.setObjectName('muted'); layout.addWidget(self.operation_hint)
        self.mode.currentIndexChanged.connect(self.reset_cards); self.mode.currentIndexChanged.connect(lambda: self.model_view.set_mode(self.mode.currentData())); self.theme.currentIndexChanged.connect(self.style)
        self.output.currentIndexChanged.connect(lambda: self.console_title.setText('终端输出 · '+self.output.currentText()))
        self.style(); self.reset_cards(); self.update_controls()
        self.timer=QTimer(self); self.timer.timeout.connect(self.poll); self.timer.start(100)
        if demo: self.demo_view()

    def style(self):
        dark=self.theme.currentIndex()==1
        bg,panel,ink,border,muted=('#181A20','#23262E','#F1F3F8','#393D48','#B5BDCE') if dark else ('#F5F6F8','#FFFFFF','#232735','#DDE1EA','#626B7C')
        self.setStyleSheet(f'''QMainWindow,QWidget {{background:{bg};color:{ink};font-family:"Noto Sans CJK SC","DejaVu Sans";font-size:15px;}}
            QFrame#panel {{background:{panel};border:1px solid {border};border-radius:12px;}}
            QFrame#panel QLabel,QFrame#panel QCheckBox {{background:transparent;}}
            QLabel#heading {{font-size:20px;font-weight:600;}} QLabel#muted {{color:{muted};font-size:14px;}}
            QPushButton,QComboBox {{background:{panel};border:1px solid {border};border-radius:8px;padding:10px 12px;min-height:22px;}}
            QPushButton:hover {{border-color:#5E6AD2;}} QPushButton:disabled {{color:{muted};background:{bg};}}
            QPushButton#primary {{background:#5E6AD2;color:white;border-color:#5E6AD2;}}
            QPushButton#danger {{background:#B42332;color:white;border-color:#B42332;}}
            QPushButton#danger:disabled,QPushButton#primary:disabled {{background:{bg};color:{muted};border-color:{border};}}
            QTextEdit {{background:{panel};border:1px solid {border};border-radius:8px;padding:12px;}}
            QTextEdit:focus {{border:2px solid #5E6AD2;}} QSplitter::handle {{background:{border};width:4px;}}
        ''')

    def selected_sides(self):
        mode=self.mode.currentData(); return ['left','right'] if mode=='dual' else [mode]

    def set_value(self,side,key,text):
        if side in self.selected_sides():
            label=self.card_values[side,key]; label.setText(text)
            color='#16805D' if text.startswith(('●','✓')) else '#A46500' if text.startswith('⚠') else ''
            label.setStyleSheet('color:'+color+';' if color else '')

    def reset_cards(self):
        for (side,key),label in self.card_values.items():
            label.setText('未启动' if side in self.selected_sides() else '未启用')
        for side in self.selected_sides():
            self.set_value(side,'source','启动后读取')
        self.operation_hint.setText(('双臂模式下操作作用于两侧' if len(self.selected_sides())==2 else '操作仅作用于当前选中的机械臂')+'；恢复默认仅修改配置，不立即执行回位动作。')

    def append(self,text):
        text=re.sub(r'\x1b\[[0-9;?]*[A-Za-z]', '', text)
        bar=self.terminal.verticalScrollBar(); previous=bar.value()
        self._appending=True
        cursor=QTextCursor(self.terminal.document()); cursor.movePosition(QTextCursor.End); cursor.insertText(text)
        bar.setValue(bar.maximum() if self.follow.isChecked() else previous)
        self._appending=False

    def scroll_changed(self,value):
        if not getattr(self,'_appending',False) and value < self.terminal.verticalScrollBar().maximum()-3:
            self.follow.setChecked(False)

    def start(self):
        if self.demo: return
        try:
            self.states={}; self.last_telemetry={}; self.reset_cards()
            self.session.start(self.mode.currentData(),'teaching' if self.output.currentIndex()==0 else 'developer',self.viewer.isChecked())
            self.terminal.clear(); self.exited_reported=False
            self.append('[界面] 已启动现有脚本，等待程序输出。\n')
            self.model_view.set_mode(self.mode.currentData()); self.model_view.start()
        except Exception as exc:
            self.append(f'[界面错误] 启动失败：{exc}\n')
        self.update_controls()

    def confirm(self):
        if self.session.confirm():
            self.append('\n'); self.update_controls()

    def action(self,key):
        if self.session.action(key):
            self.terminal.setFocus()

    def stop(self):
        if self.session.stopping: return
        try:
            self.session.stop()
            self.append('\n[界面] 正在执行原程序退出流程，请等待清理完成。\n')
        except OSError as exc:
            self.append(f'[界面错误] 退出请求失败：{exc}\n')
        self.update_controls()

    def record(self,r):
        side=r.get('side'); kind=r.get('kind'); category=r.get('category'); message=r.get('message',''); data=r.get('data') or {}
        if category=='hardware':
            for selected in self.selected_sides():
                self.set_value(selected,'connection','⚠ CAN 初始化失败')
                self.set_value(selected,'ready','⚠ 无反馈，无法确认到位')
            self.model_footer.setText('模型缺少双臂姿态：CAN 初始化失败，没有关节反馈。\n躯干固定部分仍可能显示；这不是完整的实时模型。')
            self.append('[界面][错误] '+message+' 请检查适配器、电源和 CAN 接口配置。\n')
        if side not in ('left','right'): return
        if kind=='event' and category=='system' and '关节反馈' in str(data.get('error','')):
            self.set_value(side,'connection','⚠ 未收到关节反馈')
            self.set_value(side,'ready','⚠ 无反馈，无法确认到位')
            self.model_footer.setText('模型缺少关节反馈，双臂姿态无法完整显示。请查看终端连接错误。')
        if kind=='telemetry':
            self.last_telemetry[side]=time.monotonic(); self.states[side]=r.get('state')
            self.set_value(side,'connection','● 已连接' if r.get('feedback_ok') else '⚠ 反馈异常')
            self.set_value(side,'vision','● 正常' if r.get('vio_fresh') else '⚠ 位姿中断')
            self.set_value(side,'gripper',{'disabled':'○ 未启用','unavailable':'⚠ 数据不可用'}.get(r.get('gripper'),'● 跟随已启用'))
        if kind=='stage' or (category=='startup' and '[2/5]' in message):
            if r.get('number')==2 or '[2/5]' in message: self.set_value(side,'ready','移动中')
        if category=='feedback': self.set_value(side,'connection','● 已连接')
        if category=='ready' and message=='准备配置':
            self.set_value(side,'source',{'builtin_default':'默认','custom':'自定义','command_line':'命令行指定'}.get(data.get('source'),str(data.get('source'))))
        if '已到位' in message or '已到达准备姿态' in message: self.set_value(side,'ready','✓ 已到位')
        if '准备姿态超时' in message or '未在规定时间内到达准备姿态' in message: self.set_value(side,'ready','⚠ 超时')
        if '已收到视觉位姿' in message or '已收到 VIO 位姿' in message: self.set_value(side,'vision','● 已收到位姿')
        if category=='gripper':
            if '已连接' in message: self.set_value(side,'gripper','● 开合已启用')
            elif '跳过' in message: self.set_value(side,'gripper','○ 已跳过')
        if category=='ready':
            if '已保存' in message: self.set_value(side,'source','自定义')
            if '自定义姿态已清除' in message: self.set_value(side,'source','默认')

    def update_controls(self):
        active=self.session.active
        for widget in [self.mode,self.output,self.viewer,self.start_button]: widget.setEnabled(not active and not self.demo)
        enabled=active and not self.session.stopping and set(self.selected_sides()).issubset(self.session.running)
        for key,b in self.controls.items(): b.setEnabled(active and not self.session.stopping if key=='exit' else enabled)
        paused=all(self.states.get(side)=='CLUTCH' for side in self.selected_sides())
        self.controls[' '].setText('恢复跟随' if paused else '暂停跟随')
        if self.session.stopping: self.prompt_hint.setText('正在退出，请等待原程序返回／保持和进程清理完成。')
        elif self.session.prompt: self.prompt_hint.setText('等待确认：点击终端区域后按 Enter。请保持夹爪静止。')
        else: self.prompt_hint.setText('点击终端区域可使用原有快捷键；Enter 仅在程序等待确认时有效。')

    def poll(self):
        if self.demo: return
        try:
            text=self.session.read()
            if text: self.append(text)
            for record in self.session.records(): self.record(record)
            now=time.monotonic()
            if self.session.active:
                for side,last in self.last_telemetry.items():
                    if now-last>3: self.set_value(side,'connection','⚠ 状态更新中断')
            elif not self.exited_reported:
                self.exited_reported=True; self.session.close_fd()
                self.append(f'\n[界面] 启动脚本已退出，返回码 {self.session.proc.returncode}。\n')
                for side in self.selected_sides(): self.set_value(side,'connection','已退出'); self.set_value(side,'vision','已退出')
                # Visualization remains available after a failed hardware start.
                if self.close_after_stop: self.close();return
            self.poll_model(now)
            self.update_controls()
        except Exception as exc:
            self.append(f'[界面错误] {exc}\n')

    def poll_model(self,now):
        status=self.model_view.status()
        if status:
            self.model_footer.setText('左臂：'+status['left']+'\n右臂：'+status['right']+'\n预览仅用于显示，不向机械臂发送命令。')
        if not self.model_view.active:
            if self.model_view.proc and self.model_view.proc.returncode is not None:
                self.model_hint.setText('独立模型显示进程已退出，请查看显示日志。\n'+str(self.model_view.directory/'view.log'))
            return
        if now-self.last_embed<=1:return
        self.last_embed=now
        if not os.environ.get('DISPLAY') or QApplication.platformName()!='xcb':
            self.model_hint.setText('模型已独立加载；当前平台不支持 X11 嵌入。');return
        if self.session.active:
            owned={pid for pid,stamp in self.session.owned.items() if self.session.process_stamp(pid)==stamp}
            original=find_rviz(self.session.proc.pid,owned)
            if original:hide_window(original)
        if self.embedding:
            if self.embedding.is_attached():
                ratio=self.rviz_container.devicePixelRatioF()
                self.embedding.resize(int(self.rviz_container.width()*ratio),int(self.rviz_container.height()*ratio))
                return
            self.release_model()
        try:
            window=find_rviz(self.model_view.proc.pid)
            if not window:
                self.model_hint.setText('正在加载完整双臂模型……');return
            host=QWidget(); host.setAttribute(Qt.WA_NativeWindow)
            self.model_layout.insertWidget(0,host,1); self.model_hint.hide()
            host.show();self.model_layout.activate()
            try:
                ratio=host.devicePixelRatioF();host_id=int(host.winId());QApplication.sync()
                embedding=NativeEmbedding(window,host_id,int(host.width()*ratio),int(host.height()*ratio))
            except Exception:
                self.model_layout.removeWidget(host);host.deleteLater();self.model_hint.show();raise
            self.rviz_container=host;self.embedding=embedding;self.embed_error=None
            self.append('[界面] 完整双臂模型已嵌入；无反馈时使用明确标注的默认姿态预览。\n')
        except Exception as exc:
            message=str(exc);self.model_hint.setText('模型窗口嵌入失败，正在重试。\n'+message)
            if message!=self.embed_error:self.append('[界面] 模型嵌入失败：'+message+'\n')
            self.embed_error=message

    def release_model(self):
        if self.embedding:
            self.embedding.close();self.embedding=None
        if self.rviz_container:
            self.model_layout.removeWidget(self.rviz_container)
            self.rviz_container.deleteLater();self.rviz_container=None
        self.model_hint.show()

    def demo_view(self):
        self.model_hint.setText('RViz 双臂实时模型\n\n离线界面预览\n未连接相机或机械臂，不下发任何命令。')
        for side in self.selected_sides():
            for key,text in [('connection','● 已连接（演示）'),('vision','● 正常（演示）'),('ready','✓ 已到位（演示）'),('source','默认（演示）')]: self.set_value(side,key,text)
            self.set_value(side,'gripper','● 开合已启用（演示）' if side=='left' else '○ 已跳过（演示）')
        self.append('[离线预览] 以下为模拟输出，不连接硬件。\n\n[完成][双臂] 控制通道已连接。\n[完成][双臂] 两路视觉位姿已就绪。\n[标定][双臂] 请摆好左右手持夹爪并保持静止。\n\n▶ 按 Enter 同时确认左右方向标定……\n')

    def closeEvent(self,event):
        if self.session.active:
            self.close_after_stop=True; self.stop(); event.ignore()
        else:
            self.release_model(); self.model_view.close(); self.session.close_fd(); event.accept()


def main():
    parser=argparse.ArgumentParser(); parser.add_argument('--demo',action='store_true'); parser.add_argument('--screenshot')
    args=parser.parse_args(); app=QApplication(sys.argv[:1]); window=Window(args.demo); window.show()
    if args.screenshot:
        if not args.demo: parser.error('--screenshot requires --demo')
        QTimer.singleShot(700,lambda: (window.grab().save(args.screenshot),app.quit()))
    return app.exec()

if __name__=='__main__': sys.exit(main())
