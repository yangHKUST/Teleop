# Copyright 2026 Enactic, Inc.
# SPDX-License-Identifier: Apache-2.0
"""URDF path resolution for the OpenArm v1.0 bimanual model.

Generalized from openarm_pinocchio_nsp.urdf_path: the hardcoded /ros2_ws
candidate roots are gone, and there is no import-time ``DEFAULT_URDF`` side
effect (which would make the package unimportable before ROS is sourced).

Resolution order:
  1. ``OPENARM_URDF`` environment variable (explicit override).
  2. ``openarm_description`` ament package share dir (when the workspace is
     sourced).
"""

from __future__ import annotations

import os

# v1.0 example URDF, relative to the openarm_description share root.
_URDF_REL = "assets/robot/openarm_v1.0/urdf/example/v1.urdf"


def resolve_urdf_path(explicit: str | None = None) -> str:
    """Return an existing OpenArm v1.0 URDF path.

    Args:
        explicit: if given and existing, used verbatim (highest priority).

    Raises:
        FileNotFoundError: if no candidate exists.
    """
    if explicit and os.path.isfile(explicit):
        return explicit

    env = os.environ.get("OPENARM_URDF")
    if env and os.path.isfile(env):
        return env

    try:
        from ament_index_python.packages import get_package_share_directory

        share = get_package_share_directory("openarm_description")
        cand = os.path.join(share, _URDF_REL)
        if os.path.isfile(cand):
            return cand
    except Exception:
        pass  # ROS not sourced / package not found

    raise FileNotFoundError(
        f"OpenArm v1.0 URDF not found. Set OPENARM_URDF env var or source the "
        f"openarm_description install setup. Tried share/{_URDF_REL}."
    )
