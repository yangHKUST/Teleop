import sys
if sys.prefix == '/usr':
    sys.real_prefix = sys.prefix
    sys.prefix = sys.exec_prefix = '/home/taoqiu/ros2_ws/install/openarm_umi_bridge'
