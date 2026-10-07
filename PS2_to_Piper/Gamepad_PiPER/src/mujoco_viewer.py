"""
MuJoCo-based visualization for the PiPER robotic arm.

This module converts the PiPER URDF into an MJCF model and renders it in
MuJoCo's native interactive viewer, running in a separate process. It mirrors
the viser-based visualization in gamepad_base.py: the control loop pushes the
8-DOF joint configuration (6 arm joints in radians + 2 gripper prismatic
joints in meters) onto a multiprocessing queue, and this process reads it and
updates the MuJoCo `qpos` accordingly.

Usage is transparent from the rest of the codebase: set
``visualization_backend="mujoco"`` when constructing the controller.
"""

import os
import time
import queue
import xml.etree.ElementTree as ET

import numpy as np

try:
    import mujoco
    import mujoco.viewer
    _HAS_MUJOCO = True
except ImportError:  # pragma: no cover - fallback when mujoco is missing
    _HAS_MUJOCO = False

try:
    from scipy.spatial.transform import Rotation as R
    _HAS_SCIPY = True
except ImportError:  # pragma: no cover
    _HAS_SCIPY = False


# --------------------------------------------------------------------------- #
# URDF -> MJCF conversion
# --------------------------------------------------------------------------- #

def _fmt(values):
    """Format an iterable of numbers as a space-separated string."""
    return " ".join(f"{float(v):g}" for v in values)


def _parse_vec(attr_value, default=(0.0, 0.0, 0.0)):
    """Parse a whitespace-separated attribute into a list of floats."""
    if attr_value is None:
        return list(default)
    return [float(v) for v in attr_value.split()]


def _rpy_to_wxyz(rpy):
    """Convert xyz euler angles (rad) to a MuJoCo wxyz quaternion."""
    rpy = [float(v) for v in rpy]
    if _HAS_SCIPY and any(v != 0.0 for v in rpy):
        q = R.from_euler("xyz", rpy).as_quat()  # xyzw
        return [q[3], q[0], q[1], q[2]]          # wxyz
    return [1.0, 0.0, 0.0, 0.0]


def _parse_origin(element):
    """Return (pos, wxyz_quat) from a URDF <origin> element."""
    origin = element.find("origin")
    if origin is None:
        return [0.0, 0.0, 0.0], [1.0, 0.0, 0.0, 0.0]
    pos = _parse_vec(origin.get("xyz"), (0.0, 0.0, 0.0))
    quat = _rpy_to_wxyz(_parse_vec(origin.get("rpy"), (0.0, 0.0, 0.0)))
    return pos, quat


def _parse_axis(element):
    """Return the URDF joint axis, defaulting to the z axis."""
    axis = element.find("axis")
    if axis is None:
        return [0.0, 0.0, 1.0]
    return _parse_vec(axis.get("xyz"), (0.0, 0.0, 1.0))


def _mesh_basename(filename):
    """Resolve a ``package://...`` mesh filename to its bare file name."""
    return filename.split("/")[-1]


def _link_geoms(link):
    """Return a list of MJCF <geom> lines for a URDF link's <visual> element."""
    visual = link.find("visual")
    if visual is None:
        return []

    vpos, vquat = _parse_origin(visual)
    pos_str = _fmt(vpos)
    quat_str = _fmt(vquat)

    color = "0.72 0.72 0.75 1.0"
    material = visual.find("material")
    if material is not None:
        color_el = material.find("color")
        if color_el is not None and color_el.get("rgba"):
            color = color_el.get("rgba")

    geometry = visual.find("geometry")
    if geometry is None:
        return []

    mesh = geometry.find("mesh")
    if mesh is not None:
        fname = _mesh_basename(mesh.get("filename"))
        mname = os.path.splitext(fname)[0]
        return [
            f'<geom type="mesh" mesh="{mname}" pos="{pos_str}" '
            f'quat="{quat_str}" rgba="{color}"/>'
        ]

    box = geometry.find("box")
    if box is not None:
        size = box.get("size", "0.005 0.005 0.005")
        return [
            f'<geom type="box" size="{size}" pos="{pos_str}" '
            f'quat="{quat_str}" rgba="{color}"/>'
        ]

    return []


def urdf_to_mjcf(urdf_path, mesh_dir):
    """Convert a URDF file into an MJCF XML string (visualization only).

    Only ``visual`` geometry is emitted (this viewer is kinematic, not a
    physics simulation). Meshes referenced via ``package://`` URIs are
    resolved against ``mesh_dir``.

    Args:
        urdf_path: Absolute path to the URDF file.
        mesh_dir: Absolute path to the directory holding the STL/OBJ meshes.

    Returns:
        An MJCF XML string ready for ``mujoco.MjModel.from_xml_string``.
    """
    tree = ET.parse(urdf_path)
    robot = tree.getroot()

    links = {link.get("name"): link for link in robot.findall("link")}
    joints = {joint.get("name"): joint for joint in robot.findall("joint")}

    # Root links are links that are never a child of any joint.
    child_links = {j.find("child").get("link") for j in joints.values()}
    root_links = [name for name in links if name not in child_links]

    # Collect every mesh referenced so it can be declared in <asset>.
    meshes = {}
    for link in links.values():
        visual = link.find("visual")
        if visual is None:
            continue
        geometry = visual.find("geometry")
        if geometry is None:
            continue
        mesh = geometry.find("mesh")
        if mesh is not None:
            fname = _mesh_basename(mesh.get("filename"))
            meshes[os.path.splitext(fname)[0]] = fname

    def build_body(link_name, indent):
        """Recursively build a <body> block for a link and its descendants."""
        pad = "  " * indent
        lines = []

        # The body transform comes from the joint whose child is this link.
        parent_joint = next(
            (j for j in joints.values() if j.find("child").get("link") == link_name),
            None,
        )
        if parent_joint is not None:
            pos, quat = _parse_origin(parent_joint)
            jtype = parent_joint.get("type")
            axis = _parse_axis(parent_joint)
        else:
            pos, quat = [0.0, 0.0, 0.0], [1.0, 0.0, 0.0, 0.0]
            jtype = "fixed"
            axis = None

        lines.append(
            f'{pad}<body name="{link_name}" pos="{_fmt(pos)}" quat="{_fmt(quat)}">'
        )

        if jtype == "revolute":
            limit = parent_joint.find("limit")
            lower = _parse_vec(limit.get("lower"), (-3.1416,))[0] if limit is not None else -3.1416
            upper = _parse_vec(limit.get("upper"), (3.1416,))[0] if limit is not None else 3.1416
            lines.append(
                f'{pad}  <joint name="{parent_joint.get("name")}" type="hinge" '
                f'axis="{_fmt(axis)}" range="{lower:g} {upper:g}"/>'
            )
        elif jtype == "prismatic":
            limit = parent_joint.find("limit")
            lower = _parse_vec(limit.get("lower"), (-1.0,))[0] if limit is not None else -1.0
            upper = _parse_vec(limit.get("upper"), (1.0,))[0] if limit is not None else 1.0
            lines.append(
                f'{pad}  <joint name="{parent_joint.get("name")}" type="slide" '
                f'axis="{_fmt(axis)}" range="{lower:g} {upper:g}"/>'
            )

        for geom in _link_geoms(links[link_name]):
            lines.append(f"{pad}  {geom}")

        for joint in joints.values():
            if joint.find("parent").get("link") == link_name:
                child = joint.find("child").get("link")
                lines.extend(build_body(child, indent + 1))

        lines.append(f"{pad}</body>")
        return lines

    worldbody = []
    for root in root_links:
        worldbody.extend(build_body(root, 1))

    asset = "".join(
        f'  <mesh name="{name}" file="{fname}"/>' for name, fname in sorted(meshes.items())
    )

    mjcf = (
        '<mujoco>\n'
        f'  <compiler angle="radian" meshdir="{mesh_dir}"/>\n'
        "  <asset>\n"
        f"{asset}\n"
        "  </asset>\n"
        "  <worldbody>\n"
        '    <light directional="true" diffuse="0.75 0.75 0.75" specular="0.25 0.25 0.25" pos="0.5 0.5 1.5" dir="-0.3 -0.3 -1"/>\n'
        '    <light directional="true" diffuse="0.4 0.4 0.45" specular="0.1 0.1 0.1" pos="-0.6 -0.4 1.0" dir="0.5 0.3 -1"/>\n'
        '    <geom type="plane" size="0.5 0.5 0.01" pos="0 0 -0.01" rgba="0.85 0.85 0.85 1"/>\n'
        + "\n".join(worldbody)
        + "\n  </worldbody>\n"
        "</mujoco>\n"
    )
    return mjcf


# --------------------------------------------------------------------------- #
# Visualization process
# --------------------------------------------------------------------------- #

def mujoco_visualization_process(urdf_path, mesh_dir, joint_queue, shutdown_event):
    """Independent process running the MuJoCo interactive viewer.

    Reads 8-DOF configurations (radians for joints 1-6, meters for the two
    gripper prismatic joints) from ``joint_queue`` and updates the viewer.
    """
    if not _HAS_MUJOCO:
        print("[mujoco_viewer] mujoco is not installed; visualization disabled")
        return

    mjcf = urdf_to_mjcf(urdf_path, mesh_dir)
    model = mujoco.MjModel.from_xml_string(mjcf)
    data = mujoco.MjData(model)

    viewer = None
    try:
        with mujoco.viewer.launch_passive(model, data) as viewer:
            mujoco.mj_forward(model, data)
            viewer.sync()

            while not shutdown_event.is_set() and viewer.is_running():
                joints = None
                try:
                    joints = joint_queue.get(timeout=0.05)
                    # Drain the queue, keep only the newest configuration.
                    for _ in range(joint_queue.qsize()):
                        joints = joint_queue.get_nowait()
                except queue.Empty:
                    pass

                if joints is not None:
                    qpos = np.asarray(joints, dtype=np.float64).flatten()
                    n = min(len(qpos), model.nq)
                    data.qpos[:n] = qpos[:n]
                    mujoco.mj_forward(model, data)

                viewer.sync()
                time.sleep(0.005)
    except Exception as e:
        print(f"[mujoco_viewer] error in visualization process: {e}")
    finally:
        try:
            if viewer is not None:
                viewer.close()
        except Exception:
            pass
