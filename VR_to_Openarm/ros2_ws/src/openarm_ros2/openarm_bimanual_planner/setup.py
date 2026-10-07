from setuptools import setup

package_name = "openarm_bimanual_planner"

setup(
    name=package_name,
    version="1.0.0",
    packages=[package_name],
    data_files=[
        ("share/ament_index/resource_index/packages", ["resource/" + package_name]),
        ("share/" + package_name, ["package.xml"]),
    ],
    install_requires=["setuptools"],
    zip_safe=True,
    maintainer="Enactic, Inc.",
    maintainer_email="openarm_dev@enactic.ai",
    description="Coordinated 14-DOF bimanual B-spline planner (port of openarm_pinocchio_nsp)",
    license="Apache-2.0",
    entry_points={
        "console_scripts": [
            "bimanual_plan_server = openarm_bimanual_planner.plan_server:main",
            "bimanual_plan_client = openarm_bimanual_planner.plan_client:main",
        ],
    },
)
