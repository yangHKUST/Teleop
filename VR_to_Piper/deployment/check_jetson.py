"""只检查导入、模型和 IK；不创建 VR 服务，不连接 CAN。"""
import sys
import aiohttp
import aiohttp_cors
from vuer.server import Vuer
from pathlib import Path
import numpy as np
import mujoco
import mink
import cv2
import zmq
from piper_sdk import C_PiperInterface_V2
from vuer.schemas import MotionControllers, ImageBackground, DefaultScene, group, Sphere, Cylinder
from qpsolvers import available_solvers
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'piper-quest3-teleop'))
from teleop.app import build_runtime, run_loop
from teleop.mapping.vr_mapper import VRMapperConfig
from teleop.runtime.init_mink import init_mink
print('Python:', sys.executable)
model, data, configuration, tasks, limits, solver, rate = init_mink(np.zeros(6))
assert solver in available_solvers, f'未安装求解器 {solver}'
for task in tasks:
    task.set_target_from_configuration(configuration)
velocity = mink.solve_ik(configuration, tasks, 0.01, solver=solver, limits=limits)
assert np.all(np.isfinite(velocity))
assert all(model.joint(f'joint{i}').id >= 0 for i in range(1, 9))
print(f'模型和 IK 检查通过：nq={model.nq}，solver={solver}；未连接 CAN。')
