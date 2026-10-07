"""Teaching/developer presentation; independent of motion control."""
import builtins
import datetime as dt
import json
from pathlib import Path
import time

class TeleopOutput:
    def __init__(self, side='system', mode='teaching', log_path=None):
        self.side, self.mode = side, mode
        self.started = time.monotonic()
        self.states = {}
        self.counts = {}
        self.summary = {}
        self.last_ready_reached = False
        self.write_failed = False
        self.file = None
        self.path = None
        if log_path:
            self.path = Path(log_path)
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.file = self.path.open('a', encoding='utf-8', buffering=1)

    def record(self, kind, **data):
        if self.file:
            try:
                self.file.write(json.dumps(dict(time=dt.datetime.now().astimezone().isoformat(),
                                               side=self.side, kind=kind, **data),
                                           ensure_ascii=False, allow_nan=False) + '\n')
            except OSError as exc:
                self.write_failed = True
                self.file.close()
                self.file = None
                builtins.print(f'[注意][{self.side}] 详细日志写入失败，继续控制：{exc}',flush=True)

    def event(self, message, level='INFO', category='system', data=None):
        self.record('event', level=level, category=category, message=message, data=data)
        if self.mode == 'teaching' and category == 'configuration':
            return
        if self.mode == 'teaching' and message == '准备配置':
            return
        if self.mode == 'developer':
            stamp = dt.datetime.now().strftime('%H:%M:%S.%f')[:-3]
            level = 'INFO' if level == 'DONE' else level
            line = f'{stamp} {level:<5} [{self.side}][{category}] {message}'
            if data:
                line += '\n  ' + json.dumps(data, ensure_ascii=False)
        else:
            label = {'INFO':'提示','WARN':'注意','ERROR':'错误','INPUT':'操作','DONE':'完成'}.get(level,level)
            side = {'left':'左臂','right':'右臂','dual':'双臂'}.get(self.side,self.side)
            line = f'[{label}][{side}] {message}'
        builtins.print(line, flush=True)

    def stage(self, number, message):
        if self.mode == 'developer':
            self.event(f'[{number}/5] {message}', category='startup')
        else:
            self.record('stage', number=number, message=message)
            side={'left':'左臂','right':'右臂'}.get(self.side,self.side)
            builtins.print(f'[{number}/5][{side}] {message}',flush=True)

    def transition(self, key, value, messages):
        old = self.states.get(key)
        if old == value:
            return
        self.states[key] = value
        self.counts[f'{key}:{value}'] = self.counts.get(f'{key}:{value}',0)+1
        if old is None and value == 'normal':
            self.record('initial_state', category=key, state=value)
            return
        self.event(messages[value], level='WARN' if value not in ('RUNNING','normal','CLUTCH') else 'INFO',
                   category=key, data={'previous':old,'state':value})

    def legacy(self, *args, **kwargs):
        message = kwargs.get('sep',' ').join(str(x) for x in args).strip()
        if not message or set(message) <= {'='}:
            return
        self.record('diagnostic', message=message)
        if kwargs.get('end','\n') != '\n':
            self.event(message, level='INPUT', category='input')
            return
        if self.mode == 'developer':
            level = 'WARN' if '[warn]' in message.lower() or 'WARN:' in message else 'INFO'
            self.event(message, level, 'diagnostic')
            return
        # Technical arrays/configurations remain in the detailed log.
        technical = ('rotation:', '=== R_BW', '[info] base', '[info] 世界', '[handeye]',
                     '[arm]', '[home]', '[filter]', '[control]', '[vio] 订阅', '[tick ',
                     'VIO → OpenArm', '平移 <-', '姿态 <-', '每拍受', '验证：', '若前后/左右',
                     'R_BW 已写入', '[ready] 前往准备姿态中', '[vio] VIO 进程已启动')
        if message.startswith(technical):
            return
        if message.startswith('[vio] 启动 VIO 系统:'):
            message='正在启动视觉位姿进程。'
        elif '[ready] 真机自动前往' in message:
            message='正在移动到准备姿态。'
        elif '[ready] 已到位' in message:
            message='已到达准备姿态。'
        elif '准备姿态超时' in message:
            message='未在规定时间内到达准备姿态，将以当前位置继续启动。'
        elif '已收到 VIO 位姿' in message:
            message='已收到视觉位姿。'
        elif '未提供 --vio-cmd' in message:
            message='使用已在外部运行的视觉位姿进程。'
        if message.startswith('[info] --synthetic'):
            message='使用合成视觉位姿，跳过相机连接和方向标定。'
        elif message.startswith('启动 Z/X 标定'):
            message='方向标定：将视觉位移映射到机械臂坐标。'
        elif message.startswith('[dual]'):
            message=message.replace('Z/X 标定','方向标定').replace('编排脚本回车（go）','统一开始确认')
        level='WARN' if any(x in message for x in ('[warn]','WARN:','[fail]','超时','失败')) else 'INFO'
        import re
        message=re.sub(r'^\[[^]]+\]\s*','',message)
        self.event(message,level,'startup')

    def status(self, metrics, telemetry):
        self.record('telemetry', **metrics, **telemetry)
        if self.mode == 'developer':
            stamp=dt.datetime.now().strftime('%H:%M:%S.%f')[:-3]
            fmt=lambda v: '--' if v is None else f'{v:.3f}'
            text=(f'{stamp} STAT  [{self.side}] state={metrics["state"]} '
                  f'vio_age={fmt(metrics["vio_age_s"])}s fb_age={fmt(metrics["feedback_age_s"])}s\n'
                  f'  ik={metrics["ik"]} step={metrics["step_fraction"]:.3f} '
                  f'pos_err={metrics["position_error_m"]:.4f}m rot_err={metrics["orientation_error_rad"]:.4f}rad\n'
                  f'  dq_max={metrics["max_joint_delta_rad"]:.4f}rad '
                  f'track_err={metrics["tracking_error_rad"]:.3f}rad gripper={metrics["gripper"]}')
            builtins.print(text,flush=True)
        else:
            side='左臂' if self.side=='left' else '右臂'
            state={'RUNNING':'跟随运行中','CLUTCH':'手持跟随已暂停','ESTOP':'软件急停保持',
                   'PAUSED_FEEDBACK':'关节反馈异常，保持指令','PAUSED_IK':'暂无有效运动步骤，保持指令'}[metrics['state']]
            vision='视觉更新正常' if metrics['vio_fresh'] else '视觉更新中断'
            feedback='关节反馈正常' if metrics['feedback_ok'] else '关节反馈异常'
            if metrics['feedback_age_s'] is None and not metrics.get('hardware_connected',False):
                feedback='离线模式，无实测反馈'
            gripper={'disabled':'跟随未启用','unavailable':'数据暂不可用'}.get(metrics['gripper'],metrics['gripper'])
            builtins.print(f'[{side}] {state} | {vision} | {feedback} | 夹爪 {gripper}',flush=True)

    def close(self):
        self.event('运行结束',category='summary',data={'duration_s':round(time.monotonic()-self.started,3),
                                                    'state_events':self.counts,'log_file':str(self.path) if self.path else None, **self.summary})
        if self.file:
            self.file.close()
            self.file=None
