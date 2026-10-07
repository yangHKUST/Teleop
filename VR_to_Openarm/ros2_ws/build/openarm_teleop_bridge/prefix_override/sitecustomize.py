import sys
if sys.prefix == '/home/taoqiu/venv-openarm-ik':
    sys.real_prefix = sys.prefix
    sys.prefix = sys.exec_prefix = '/home/taoqiu/ros2_ws/install/openarm_teleop_bridge'
