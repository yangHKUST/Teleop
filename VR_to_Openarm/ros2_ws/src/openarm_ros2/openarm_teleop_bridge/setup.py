from setuptools import setup

package_name = "openarm_teleop_bridge"

setup(
    name=package_name,
    version="1.0.0",
    packages=[package_name],
    data_files=[
        ("share/ament_index/resource_index/packages", ["resource/" + package_name]),
        ("share/" + package_name, ["package.xml"]),
        ("share/" + package_name + "/launch", ["launch/bridge.launch.py",
                                              "launch/teleop.launch.py",
                                              "launch/teleop_real.launch.py"]),
    ],
    install_requires=["setuptools"],
    zip_safe=True,
    maintainer="Enactic, Inc.",
    maintainer_email="openarm_dev@enactic.ai",
    description="Bridge teleop_xr JointTrajectory output to OpenArm forward-position controllers",
    license="Apache-2.0",
    entry_points={
        "console_scripts": [
            "jt_bridge = openarm_teleop_bridge.jt_bridge:main",
        ],
    },
)
