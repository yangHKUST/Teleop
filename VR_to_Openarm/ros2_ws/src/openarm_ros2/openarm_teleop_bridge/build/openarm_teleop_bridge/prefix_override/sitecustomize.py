import sys
if sys.prefix == '/home/taoqiu/venv-openarm-ik':
    sys.real_prefix = sys.prefix
    sys.prefix = sys.exec_prefix = '/home/taoqiu/ros2_ws/src/openarm_ros2/openarm_teleop_bridge/install/openarm_teleop_bridge'
