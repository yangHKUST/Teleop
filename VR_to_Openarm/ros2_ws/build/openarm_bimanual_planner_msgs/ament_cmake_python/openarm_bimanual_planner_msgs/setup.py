from setuptools import find_packages
from setuptools import setup

setup(
    name='openarm_bimanual_planner_msgs',
    version='1.0.0',
    packages=find_packages(
        include=('openarm_bimanual_planner_msgs', 'openarm_bimanual_planner_msgs.*')),
)
