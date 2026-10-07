from setuptools import setup

package_name = "openarm_umi_bridge"

setup(
    name=package_name,
    version="1.0.0",
    packages=[package_name],
    data_files=[
        ("share/ament_index/resource_index/packages", ["resource/" + package_name]),
        ("share/" + package_name, ["package.xml"]),
        ("share/" + package_name + "/launch", ["launch/umi_bridge.launch.py"]),
    ],
    install_requires=["setuptools"],
    zip_safe=True,
    maintainer="Enactic, Inc.",
    maintainer_email="openarm_dev@enactic.ai",
    description="ZMQ bridge from the UMI teleop core (non-ROS) to the OpenArm right-arm forward-position controller",
    license="Apache-2.0",
    entry_points={
        "console_scripts": [
            "umi_bridge = openarm_umi_bridge.umi_bridge:main",
        ],
    },
)
