#!/usr/bin/env python3
"""Standalone launcher for the PiPER REAL robot (no shell wrapper needed).

Run it directly::

    ./run_real.py            # or: python3 run_real.py

It does three things that a plain ``python main.py`` cannot, all inside one
Python file:

1. **Relaunch under the ``piper`` conda python** if it is not already running
   there (the deps are installed in that env, while the default ``python3`` on
   this machine is the base conda Python 3.13).
2. **Strip the ROS Humble environment** that the shell profile sources: ROS's
   Python 3.10 ``site-packages`` sits on ``PYTHONPATH`` and shadows the conda
   pinocchio, causing ``ModuleNotFoundError: pinocchio.pinocchio_pywrap_default``.
3. **Bring up ``can0`` and run ``main.py``'s control loop** (``main.main()``).

The actual arm control lives in ``main.py`` unchanged; this file is only the
environment bootstrap.
"""

import os
import sys

# Python that has pinocchio / mujoco / piper_sdk installed.
PIPER_PYTHON = os.path.expanduser("~/miniconda3/envs/piper/bin/python")


def _clean_ros_env():
    """Remove ROS Humble from sys.path and the process environment.

    Must be called *before* importing anything that pulls in pinocchio /
    mujoco / piper_sdk, otherwise ROS's Python 3.10 builds win.
    """
    # sys.path entries pointing into /opt/ros (from PYTHONPATH, .pth files, ...).
    sys.path[:] = [p for p in sys.path if "/opt/ros/" not in p]

    for var in (
        "PYTHONPATH",
        "ROS_DISTRO",
        "AMENT_PREFIX_PATH",
        "CMAKE_PREFIX_PATH",
        "COLCON_PREFIX_PATH",
    ):
        os.environ.pop(var, None)

    ld = os.environ.get("LD_LIBRARY_PATH", "")
    if ld:
        os.environ["LD_LIBRARY_PATH"] = ":".join(
            p for p in ld.split(":") if p and "/opt/ros/" not in p
        )

    # pinocchio resolves package://piper_description/meshes/*.STL via this.
    script_dir = os.path.dirname(os.path.realpath(__file__))
    os.environ["ROS_PACKAGE_PATH"] = os.path.join(script_dir, "ros_packages")


def main():
    _clean_ros_env()

    script_dir = os.path.dirname(os.path.realpath(__file__))
    os.chdir(script_dir)
    if script_dir not in sys.path:
        sys.path.insert(0, script_dir)

    # Bring up can0 (1 Mbps). This is what main.py's __main__ block does;
    # doing it here makes the sudo prompt explicit and fails fast if the
    # adapter is unplugged.
    print("==> Bringing up can0 @ 1 Mbps (sudo password may be required) ...")
    ret = os.system("sudo ip link set can0 up type can bitrate 1000000")
    if ret != 0:
        print("[run_real] WARNING: could not bring up can0 (exit %d); "
              "the arm will not move unless can0 is UP." % ret)

    # main.py imports piper_sdk + gamepad_pin at module import time, so import
    # it only after the environment has been cleaned above.
    import main as real_main  # noqa: E402

    real_main.main()


if __name__ == "__main__":
    # If we are not already the piper conda python, re-exec under it with the
    # cleaned environment. _clean_ros_env() mutates os.environ (which writes
    # through to the C environ), so the re-exec'd process inherits a clean env.
    if os.path.realpath(sys.executable) != os.path.realpath(PIPER_PYTHON):
        _clean_ros_env()
        os.execv(PIPER_PYTHON, [PIPER_PYTHON] + sys.argv)
        # Not reached.

    main()
