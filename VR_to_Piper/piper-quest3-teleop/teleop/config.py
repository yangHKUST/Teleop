# config.py
from pathlib import Path

# config.py가 있는 폴더 = .../TeleVision/teleop
_TELEOP_DIR = Path(__file__).resolve().parent

UDP_IP = "127.0.0.1"
UDP_PORT = 15000

START_POSITION = [0, 0, 0, 0, 0, 0, 0, 0]

RAD_TO_PIPER = 57324.840764  # 1000*180/pi

####### MINK ############
PIPER_MJCF_PATH = str(_TELEOP_DIR / "piper" / "agilex_piper" / "piper.xml")
MINK_EE_SITE = "attachment_site"  # 네 MJCF에서 end-effector site 이름
MINK_SOLVER = "daqp"
MINK_RATE_HZ = 100.0               # 主循环/IK 解算频率 (Hz)，与 SEND_RATE_HZ 对齐
MINK_DT = 0.01                    # IK 적분 dt (config.SLEEP와 맞춰도 됨) —— 废弃，实际用 rate.dt=1/MINK_RATE_HZ
MINK_LM_DAMPING = 1e-4
MINK_POSTURE_COST = 1e-3
#######MINK##############

SEND_RATE_HZ = 100.0               # CAN 下发频率 (Hz)，与 MINK_RATE_HZ 一致，避免 2:1 抽点

# RETURNING 回零时关节空间插值的限速 (rad/s)。任务空间 IK 会把臂带到"翻转"构型、
# 回不到关节零位，所以回零改成关节空间线性插值；此值控制回零速度。
RETURN_JOINT_SPEED = 0.5

####### 1€ 自适应滤波 + 死区（VR 手柄 → 机械臂末端位姿）############
# 作用位置：TELEOP 分支 mapper.compute_target_T() 之后、ik_step 之前。
# 抑制手持遥操的生理性手抖（8–12Hz）。改这里即可调参，无需改代码。
POSE_FILTER_ENABLED = True
POSE_FC_MIN = 1.0            # Hz，静止时最低截止频率（越低抖压得越死、慢速越滞）
POSE_FC_D = 1.0              # Hz，速度估计的低通截止（一般不动）
POSE_BETA_POS = 5.5          # 位置速度系数 Hz/(m/s)（越大越跟手、越抖）
POSE_BETA_ROT = 1.2          # 姿态速度系数 Hz/(rad/s)
POSE_DEADBAND_POS = 0.002       # m，位置死区·解冻阈值 outer（明显动作才解冻）
POSE_DEADBAND_ROT = 0.0105      # rad，姿态死区·解冻阈值 outer（~0.6°）
POSE_DEADBAND_POS_INNER = 0.0007  # m，位置死区·冻结阈值 inner（几乎静止即冻结）
POSE_DEADBAND_ROT_INNER = 0.0035  # rad，姿态死区·冻结阈值 inner（~0.2°）
####### 1€ 自适应滤波 + 死区 ############

# === Gripper mapping ===
GRIPPER_MAX_MM = 70.0          # 매뉴얼: 0~70mm
GRIPPER_UNIT_MM = 0.001        # SDK: 0.001mm 단위
GRIPPER_MAX_UM = int(GRIPPER_MAX_MM / GRIPPER_UNIT_MM)  # 70000

SIM_GRIPPER_RANGE = 0.035      # MuJoCo에서 joint7/8 벌리는 범위

# === 数据录制 (ZMQ pub/sub) ===
# 主循环把每帧遥操数据发布到该 ZMQ PUB 端点；另开终端运行
# `python -m teleop.record_data --endpoint tcp://127.0.0.1:5559` 订阅落盘为 CSV。
RECORD_ENDPOINT = "tcp://127.0.0.1:5559"
# 实际关节角/夹爪开度的读回频率 (Hz)。读回独立于控制回路，仅用于录制。
RECORD_READBACK_HZ = 20.0