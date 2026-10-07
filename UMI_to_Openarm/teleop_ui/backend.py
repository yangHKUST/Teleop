"""Existing launchers hosted on a controlling PTY. No robot commands here."""
import codecs
import errno
import fcntl
import json
import os
from pathlib import Path
import pty
import signal
import subprocess
import termios
import time
import uuid
from rviz_embed import descendants

ROOT = Path(__file__).resolve().parents[1]
ARM = ROOT / 'UMI_to_arm/arm/mujoco_sim'


def camera_config(side):
    prefix = "LEFT" if side == "left" else "RIGHT"
    sn = os.environ.get(prefix + "_VIO_SN", "s200085" if side == "left" else "s200086")
    folder = ROOT / "UMI_to_arm/camera_driver/cyperstereo/calib/orbslam3_yaml" if side == "left" else Path("/home/taoqiu/CyperstereoSDK/slam/config/orbslam3")
    return sn, Path(os.environ.get(prefix + "_YAML", str(folder / f"cyperstereo_sn_{sn}.yaml")))


def command(mode, output, viewer, logs):
    if mode not in ('left', 'right', 'dual') or output not in ('teaching', 'developer'):
        raise ValueError('invalid launch selection')
    common = ['--bridge', '--output-mode', output, '--log-file', str(logs / '{arm}.log')]
    if viewer:
        common.append('--vio-viewer')
    if mode == 'dual':
        return ['bash', str(ARM / 'run_openarm_dual.sh'), *common], {}
    sn, yaml = camera_config(mode)
    import shlex
    vio = 'cd /home/taoqiu/CyperstereoSDK/ORB_SLAM3-Cyperstereo/build && ./cyperstereo_online ../Vocabulary/ORBvoc.txt ' + shlex.quote(str(yaml))
    return ['bash', str(ARM / 'run_openarm.sh'), *common, '--arm', mode, '--staged', '--vio-cmd', vio], {'CYPERSTEREO_SERIAL': sn}


def controlling_terminal():
    os.setsid()
    fcntl.ioctl(0, termios.TIOCSCTTY, 0)


class Session:
    def __init__(self):
        self.proc = None
        self.fd = None
        self.decoder = codecs.getincrementaldecoder('utf-8')('replace')
        self.offsets = {}
        self.pending = ''
        self.prompt = False
        self.running = set()
        self.mode = 'dual'
        self.logs = None
        self.stopping = False
        self.owned = {}
        self.ros_offset = 0
        self.ros_error_reported = False
        self.start_time = 0
        self.ros_log = None

    @staticmethod
    def process_stamp(pid):
        try:
            fields = Path(f"/proc/{pid}/stat").read_text().rsplit(")", 1)[1].split()
            return fields[19] if fields[0] not in ("Z", "X") else None
        except (OSError, IndexError):
            return None

    @property
    def active(self):
        if self.proc is None:
            return False
        if self.proc.poll() is None:
            for pid in descendants(self.proc.pid):
                stamp = self.process_stamp(pid)
                if stamp is not None:
                    self.owned[pid] = stamp
            return True
        # A launcher can finish its trap before a core completes ready-return.
        # Keep mode locked until every observed child has finished cleanup.
        return any(self.process_stamp(pid) == stamp for pid, stamp in self.owned.items())

    def start(self, mode, output, viewer, argv=None):
        if self.active:
            raise RuntimeError('已有运行会话')
        self.mode = mode
        self.owned = {}
        self.start_time = time.time()
        self.ros_offset = 0; self.ros_error_reported = False
        self.ros_log = Path.home() / '.openarm_umi_logs' / ('ros2_dual.log' if mode == 'dual' else 'ros2.log')
        self.logs = ROOT / 'teleop_ui/logs' / (time.strftime('%Y%m%d_%H%M%S_') + uuid.uuid4().hex[:6])
        self.logs.mkdir(parents=True)
        args, extra = command(mode, output, viewer, self.logs)
        master, slave = pty.openpty()
        env = os.environ.copy(); env.update(extra); env['PYTHONUNBUFFERED'] = '1'
        # Do not leak Qt6 plugin locations into ROS RViz's Qt5 process.
        for key in ('QT_PLUGIN_PATH', 'QT_QPA_PLATFORM_PLUGIN_PATH'):
            env.pop(key, None)
        try:
            self.proc = subprocess.Popen(argv or args, cwd=ROOT / 'UMI_to_arm', env=env,
                stdin=slave, stdout=slave, stderr=slave, preexec_fn=controlling_terminal)
        except Exception:
            os.close(master); raise
        finally:
            os.close(slave)
        self.fd = master; os.set_blocking(master, False)
        self.offsets = {}; self.pending = ''; self.prompt = False; self.running = set(); self.stopping = False
        self.decoder.reset()

    def read(self):
        chunks = []
        if self.fd is not None:
            while True:
                try:
                    data = os.read(self.fd, 65536)
                    if not data:
                        break
                    chunks.append(self.decoder.decode(data))
                except OSError as exc:
                    if exc.errno in (errno.EAGAIN, errno.EIO):
                        break
                    raise
        text = ''.join(chunks).replace('\r\n', '\n')
        # Only the two original confirmation prompts enable Enter.
        self.pending = (self.pending + text)[-6000:]
        if any(token in self.pending for token in ('按 Enter 同时确认', '按 Enter 开始', '回车确定 ...', '按回车开启遥操')):
            self.prompt = True
        return text

    def confirm(self):
        if not self.active or not self.prompt or self.stopping:
            return False
        self.prompt = False; self.pending = ''
        os.write(self.fd, b'\n')
        return True

    def action(self, key):
        expected = {'left', 'right'} if self.mode == 'dual' else {self.mode}
        if not self.active or self.stopping or not expected.issubset(self.running):
            return False
        if key not in (' ', 'h', 's', 'r', '\x1b'):
            raise ValueError('unsupported control')
        os.write(self.fd, key.encode())
        return True

    def stop(self):
        if self.active and not self.stopping:
            self.stopping = True; self.prompt = False
            try:
                os.killpg(self.proc.pid, signal.SIGINT)
            except ProcessLookupError:
                # A child may still be finishing cleanup after the launcher exit.
                pass

    def records(self):
        result = []
        if self.logs:
            for path in self.logs.glob('*.log'):
                offset = self.offsets.get(path, 0)
                with path.open('rb') as file:
                    file.seek(offset)
                    for line in file:
                        if not line.endswith(b'\n'):
                            break
                        offset += len(line)
                        try:
                            record = json.loads(line)
                        except (ValueError, UnicodeError):
                            continue
                        result.append(record)
                        if record.get('kind') == 'telemetry':
                            self.running.add(record['side'])
                self.offsets[path] = offset
        # The original ROS launcher writes hardware errors to a separate file.
        # Report the explicit CAN failure; never invent missing joint positions.
        if self.ros_log and not self.ros_error_reported:
            try:
                stat = self.ros_log.stat()
                if stat.st_mtime >= self.start_time:
                    with self.ros_log.open('rb') as file:
                        file.seek(self.ros_offset)
                        for line in file:
                            if not line.endswith(b'\n'):break
                            self.ros_offset += len(line)
                            message = line.decode('utf-8',errors='replace')
                            if 'Failed to initialize socket for interface:' in message:
                                self.ros_error_reported = True
                                interface = message.split('Failed to initialize socket for interface:',1)[1].strip()
                                result.append({'side':self.mode,'kind':'event','category':'hardware',
                                    'message':f'CAN 接口 {interface} 初始化失败，机械臂关节反馈不可用。',
                                    'data':{'interface':interface}})
            except OSError:
                pass
        return result

    def close_fd(self):
        if self.fd is not None:
            os.close(self.fd); self.fd = None
