#!/usr/bin/env bash
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
# Qt6 UI and ROS Qt5 RViz keep their own interpreters/environments.
if [ -n "${DISPLAY:-}" ]; then export QT_QPA_PLATFORM=xcb; fi
unset QT_PLUGIN_PATH QT_QPA_PLATFORM_PLUGIN_PATH
exec "${OPENARM_UI_PYTHON:-/home/taoqiu/miniconda3/bin/python}" "$HERE/app.py" "$@"
