import time
from vuer import Vuer
from vuer.schemas import ImageBackground, DefaultScene
from vuer.schemas import MotionControllers
from multiprocessing import Array, Value, Process, shared_memory
from aiohttp import web
import numpy as np
import asyncio
from pathlib import Path
from .piper_arm_skeleton_vuer import VuerRobotSkeleton  
from vuer.schemas import Sphere

def robot_to_vuer_pos(p_r):
    x, y, z = p_r
    return np.array([x, z, -y], dtype=float)


def _make_ws_redirect_middleware():
    """
    vuer 0.0.70 客户端 bug：https 页面里 getDefaultSocketURI() 会丢掉端口、
    去连 443，导致 Quest 的 WebSocket 永远连不上（看不到骨架、收不到手柄数据）。
    这里在服务端把「入口页面」的 URL 自动补上 ?ws=wss://<host>:<port>，
    用户只要打开 https://<ip>:8012 就能用，不用手动带参数。
    """
    from urllib.parse import urlencode

    @web.middleware
    async def _middleware(request, handler):
        is_page = request.method == "GET" and request.path.rstrip("/") in ("", "/index.html")
        is_ws_upgrade = request.headers.get("Upgrade", "").lower() == "websocket"
        # 只重定向入口页面，不动 WebSocket 握手和静态资源；已带 ws 参数就不重定向（避免循环）
        if is_page and not is_ws_upgrade and "ws" not in request.query:
            host = request.headers.get("Host", "localhost")
            scheme = "wss" if request.scheme == "https" else "ws"
            q = dict(request.query)
            q["ws"] = f"{scheme}://{host}"
            target = request.path + "?" + urlencode(q, doseq=True)
            print(f"[vuer fix] auto-redirect: {request.rel_url} -> {target}", flush=True)
            return web.HTTPFound(target)
        return await handler(request)

    return _middleware


class OpenTeleVision:
    def __init__(self, img_shape, shm_name, stream_mode="image", cert_file="./cert.pem", key_file="./key.pem", ngrok=False):
        base_dir = Path(__file__).resolve().parent
        cert_path = (base_dir / cert_file).resolve() if not Path(cert_file).is_absolute() else Path(cert_file)
        key_path  = (base_dir / key_file).resolve()  if not Path(key_file).is_absolute()  else Path(key_file)

        cert_file = str(cert_path)
        key_file  = str(key_path)

        # self.app=Vuer()
        self.img_shape = (img_shape[0], 2*img_shape[1], 3) ## 한 눈(left or right) 기준의 해상도로 들어옴
        self.img_height, self.img_width = img_shape[:2] ## 한 눈(left or right) 기준의 height/width 

        # ngrok - 로컬에서 돌아가는 서버를 인터넷 어디서나 접속할 수 있게 해주는 터널링 서비스
        if ngrok: ## 참이면 ngrok이 제공하는 https로 열기 
            self.app = Vuer(host='0.0.0.0', queries=dict(grid=False), queue_len=3) ## queries dict(grid=False)는 Vuer 기본 UI 그리드 표시를 끄는 것. queue_len=3은 이벤트 큐 길이를 제한하는 것(지연 방지)
        else: ## 인증서 직접 사용
            self.app = Vuer(host='0.0.0.0', cert=cert_file, key=key_file, queries=dict(grid=False), queue_len=3)
        
        # 컨트롤러 이벤트 핸들러
        self.app.add_handler("CONTROLLER_MOVE")(self.on_controller_move)

        # vuer 0.0.70 客户端 https 丢端口 bug 的自动修复：给入口页面自动补 ?ws=
        self.app.app.middlewares.append(_make_ws_redirect_middleware())

        # 공유메모리
        if stream_mode == "image": # OpenTeleVision -> 브라우저 
            self._existing_shm = shared_memory.SharedMemory(name=shm_name)
            self.img_array = np.ndarray((self.img_shape[0], self.img_shape[1], 3), dtype=np.uint8, buffer=self._existing_shm.buf) 
            self.app.spawn(start=False)(self.main_image) ## vuer 세션마다 실행할 루틴으로 main_image 등록
        else:
            raise ValueError("stream_mode must be 'image'")

        
        # RIGHT 컨트롤러
        self.right_controller_shared = Array('d', 16, lock=True) ## 4x4 (오른손)
        self.right_state_shared = Array('d', 14, lock=True)

        # LEFT 컨트롤러
        self.left_controller_shared = Array('d', 16, lock=True) ## 4x4 (왼손, dual arm 用)
        self.left_state_shared = Array('d', 14, lock=True)

        # Robot skeleton shared memory (joints xyz) — dual arm: 左右臂各一份
        self.max_joints = 8  # 넉넉히
        self._sides = ("left", "right")

        self.robot_n_joints = {s: Value('i', 0, lock=True) for s in self._sides}
        self.robot_joints_shared = {s: Array('d', 3 * self.max_joints, lock=True) for s in self._sides}

        # base->...->ee 연결. FK 조인트 순서에 맞게
        # edges(joint - joint 링크) 는 [(0,1),(1,2)...]
        self.robot_edges = {s: [] for s in self._sides}

        self.skel = {
            s: VuerRobotSkeleton(
                edges=[],
                key=f"robot-skel-{s}",
                joint_radius=0.015,
                link_radius=0.008,
                offset=(0.0, 0.0, 0.0),
                layers=0,
            )
            for s in self._sides
        }

        self._R_yaw = np.array([
            [0.0, 0.0, 1.0],
            [0.0, 1.0, 0.0],
            [-1.0, 0.0, 0.0],
        ], dtype=float)  # yaw +90

        ## 쉽게 이해하기 위한 식은 아래와 같음
        # ee_vuer = ee_fk + (anchor_in_vuer - ee_fk)

        # EE-anchor calibration state (실제 로봇 좌표계에서 계산된 EE 위치를 quest3 위치로 옮기는 평행이동)
        self._world_offset = {s: None for s in self._sides}  # np.array shape (3,) or None

        # Vuer 상에서 EE의 위치(컨트롤러의 위치)
        self._anchor_in_vuer = {s: np.array([0.0, 0.0, 0.0], dtype=float) for s in self._sides}

        # joints_xyz에서 EE 인덱스 (보통 마지막이면 -1)
        self._ee_index = -1

        # 카메라 aspect
        self.aspect_shared = Value('d', 1.0, lock=True) ## 1x1 (카메라 aspect)

        self.process = Process(target=self.run)
        self.process.daemon = True
        self.process.start()

    
    def run(self):
        # vuer 服务跑在子进程里：忽略 SIGINT，让 Ctrl+C 只由主进程处理，
        # 避免 asyncio 循环被 KeyboardInterrupt 打断后与共享内存清理竞争导致段错误。
        import signal
        signal.signal(signal.SIGINT, signal.SIG_IGN)
        self.app.run()

    ## 컨트롤러를 트래킹 
    async def on_controller_move(self, event, session, fps=60):
        data = event.value
        # --- DEBUG: 每秒打印一次 raw rightState，定位握把按键没生效的问题 ---
        _dbg_now = time.time()
        if _dbg_now - getattr(self, "_dbg_last", 0.0) > 1.0:
            self._dbg_last = _dbg_now
            _rs = data.get("rightState") or {}
            print("[DEBUG] rightState keys=", sorted(_rs.keys()), flush=True)
            print("[DEBUG] squeeze=%r squeezeValue=%r trigger=%r aButton=%r" % (
                _rs.get("squeeze"), _rs.get("squeezeValue"),
                _rs.get("trigger"), _rs.get("aButton")), flush=True)
        try:
            # RIGHT
            right = data.get("right") # 길이 16짜리
            if isinstance(right, (list, tuple)) and len(right) == 16:
                self.right_controller_shared[:] = right

            # LEFT (4x4 pose) — dual arm 用
            left = data.get("left")
            if isinstance(left, (list, tuple)) and len(left) == 16:
                self.left_controller_shared[:] = left

            # RIGHT state
            rs = data.get("rightState") or {}
            # right_state_shared 
            if isinstance(rs, dict):
                tp = rs.get("touchpadValue") or [0.0, 0.0]
                ts = rs.get("thumbstickValue") or [0.0, 0.0]

                self.right_state_shared[:] = [
                    1.0 if rs.get("trigger", False) else 0.0,        # 0 얘가 그리퍼
                    1.0 if rs.get("squeeze", False) else 0.0,        # 1 얘는 동작 여부
                    1.0 if rs.get("touchpad", False) else 0.0,       # 2
                    1.0 if rs.get("thumbstick", False) else 0.0,     # 3
                    1.0 if rs.get("aButton", False) else 0.0,        # 4
                    1.0 if rs.get("bButton", False) else 0.0,        # 5

                    float(rs.get("triggerValue", 0.0) or 0.0),       # 6
                    float(rs.get("squeezeValue", 0.0) or 0.0),       # 7
                    float(tp[0] if len(tp) > 0 else 0.0),            # 8
                    float(tp[1] if len(tp) > 1 else 0.0),            # 9
                    float(ts[0] if len(ts) > 0 else 0.0),            # 10
                    float(ts[1] if len(ts) > 1 else 0.0),            # 11

                    1.0 if rs.get("aButtonValue", False) else 0.0,   # 12  
                    1.0 if rs.get("bButtonValue", False) else 0.0,   # 13
                ]

            # LEFT state
            ls = data.get("leftState") or {}
            if isinstance(ls, dict):
                tp = ls.get("touchpadValue") or [0.0, 0.0]
                ts = ls.get("thumbstickValue") or [0.0, 0.0]

                self.left_state_shared[:] = [
                    1.0 if ls.get("trigger", False) else 0.0,        # 0
                    1.0 if ls.get("squeeze", False) else 0.0,        # 1
                    1.0 if ls.get("touchpad", False) else 0.0,       # 2
                    1.0 if ls.get("thumbstick", False) else 0.0,     # 3
                    1.0 if ls.get("aButton", False) else 0.0,        # 4 
                    1.0 if ls.get("bButton", False) else 0.0,        # 5

                    float(ls.get("triggerValue", 0.0) or 0.0),       # 6
                    float(ls.get("squeezeValue", 0.0) or 0.0),       # 7
                    float(tp[0] if len(tp) > 0 else 0.0),            # 8
                    float(tp[1] if len(tp) > 1 else 0.0),            # 9
                    float(ts[0] if len(ts) > 0 else 0.0),            # 10
                    float(ts[1] if len(ts) > 1 else 0.0),            # 11

                    1.0 if ls.get("aButtonValue", False) else 0.0,   # 12
                    1.0 if ls.get("bButtonValue", False) else 0.0,   # 13
                ]


        except Exception as e:
            print("[CONTROLLER_MOVE] error:", e)

    ################### quest3에 그려질 로봇 조인트 스켈레톤 관련 #######################
    def enable_skeleton(self, side: str, anchor_pos_vuer: np.ndarray):
        self._anchor_in_vuer[side] = np.asarray(anchor_pos_vuer, dtype=float).reshape(3,)
        self._world_offset[side] = None

    def clear_robot_joints(self, side: str):
        with self.robot_n_joints[side].get_lock():
            self.robot_n_joints[side].value = 0
        with self.robot_joints_shared[side].get_lock():
            for k in range(3 * self.max_joints):
                self.robot_joints_shared[side][k] = 0.0

    def set_robot_joints(self, side: str, joints_xyz: np.ndarray):
        arr_r = np.asarray(joints_xyz, dtype=float).reshape(-1, 3)

        # robot -> vuer
        arr_v = np.stack([robot_to_vuer_pos(p) for p in arr_r], axis=0)

        # yaw 프레임 통일: 먼저 회전 적용
        if getattr(self, "_R_yaw", None) is not None:
            arr_v = (self._R_yaw @ arr_v.T).T

        # EE 기준 오프셋 캘리브레이션 (yaw 적용된 ee0로)
        if self._world_offset[side] is None and arr_v.shape[0] >= 1:
            ee0 = arr_v[self._ee_index].copy()
            self._world_offset[side] = self._anchor_in_vuer[side] - ee0
            print(f"[CALIB][{side}] ee0={ee0}, world_offset={self._world_offset[side]}")

        # 오프셋 적용
        if self._world_offset[side] is not None:
            arr_v = arr_v + self._world_offset[side]

        n = int(min(arr_v.shape[0], self.max_joints))
        self.robot_edges[side] = [(i, i + 1) for i in range(max(0, n - 1))]

        with self.robot_n_joints[side].get_lock():
            self.robot_n_joints[side].value = n

        with self.robot_joints_shared[side].get_lock():
            flat = self.robot_joints_shared[side]
            for k in range(3 * self.max_joints):
                flat[k] = 0.0
            for i in range(n):
                base = 3 * i
                flat[base + 0] = float(arr_v[i, 0])
                flat[base + 1] = float(arr_v[i, 1])
                flat[base + 2] = float(arr_v[i, 2])
    ########################################################################

    async def main_image(self, session, fps=60):
        # 그리드 끄기
        session.set @ DefaultScene(grid=False, frameloop="always")
        
        # 컨트롤러
        session.upsert @ MotionControllers(stream=True, key="motion-controller", left=True, right=True,)
        
        try:
            while True:
                display_image = self.img_array

                # 카메라 스트리밍
                session.upsert(
                [ImageBackground(
                    display_image[::2, :self.img_width:2],
                    # 'jpg' encoding is significantly faster than 'png'.
                    format="jpeg",
                    quality=80,
                    key="left-image",
                    interpolate=True,
                    # fixed=True,
                    aspect=1.66667,
                    # distanceToCamera=0.5,
                    height = 2,
                    position=[0, 1, 3],
                    # rotation=[0, 0, 0],
                    layers=1, 
                ),
                ImageBackground(
                    display_image[::2, self.img_width::2],
                    # 'jpg' encoding is significantly faster than 'png'.
                    format="jpeg",
                    quality=80,
                    key="right-image",
                    interpolate=True,
                    # fixed=True,
                    aspect=1.66667,
                    # distanceToCamera=0.5,
                    height = 2,
                    position=[0, 1, 3],
                    # rotation=[0, 0, 0],
                    layers=2, 
                )],
                to="bgChildren",
                )

                # 로봇 스켈레톤 그리기 (dual arm: 左右臂各一条)
                for side in self._sides:
                    with self.robot_n_joints[side].get_lock(), self.robot_joints_shared[side].get_lock():
                        n = int(self.robot_n_joints[side].value)
                        if n >= 2:
                            buf = np.array(self.robot_joints_shared[side][: 3 * n], dtype=float)
                        else:
                            buf = None

                    if n >= 2 and buf is not None:
                        joints = buf.reshape(n, 3).copy()

                        # edges 동기화 (체인 형태)
                        self.skel[side].edges = [(i, i + 1) for i in range(n - 1)]

                        self.skel[side].upsert(session, joints)

                await asyncio.sleep(0.03)
        
        except asyncio.CancelledError:
            raise
        except Exception as e: ## Web Socket 끊김 
            print("[main_image] session ended:", repr(e))
            return
            
        
    @property
    def right_controller(self):
        return np.array(self.right_controller_shared[:]).reshape(4, 4, order="F")

    @property
    def left_controller(self):
        return np.array(self.left_controller_shared[:]).reshape(4, 4, order="F")
    
    @property
    def right_state(self) -> np.ndarray:
        """
        right_state shape: (14,)
        """
        return np.array(self.right_state_shared[:], dtype=float)

    @property
    def left_state(self) -> np.ndarray:
        """
        left_state shape: (14,)
        """
        return np.array(self.left_state_shared[:], dtype=float)
    
    @property
    def aspect(self):
        # with self.aspect_shared.get_lock():
            # return float(self.aspect_shared.value)
        return float(self.aspect_shared.value)