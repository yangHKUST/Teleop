from glob import glob
from setuptools import find_packages, setup

package_name = "gripper_teleop"

setup(
    name=package_name,
    version="0.1.0",
    packages=find_packages(exclude=["test"]),
    data_files=[
        ("share/ament_index/resource_index/packages", [f"resource/{package_name}"]),
        (f"share/{package_name}", ["package.xml"]),
        (f"share/{package_name}/config", glob("config/*.json")),
        (f"share/{package_name}/launch", glob("launch/*.launch.py")),
    ],
    install_requires=["setuptools"],
    zip_safe=True,
    maintainer="cyperstereo_team",
    maintainer_email="2470428938@qq.com",
    description="Handheld DM3507 gripper detection + AGX gripper teleop bridge.",
    license="BSD",
    entry_points={
        "console_scripts": [
            "gripper_publisher = gripper_teleop.gripper_publisher:main",
            "gripper_agx_bridge = gripper_teleop.gripper_agx_bridge:main",
        ],
    },
)
