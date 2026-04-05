#!/usr/bin/env bash
# Start all topside ROV nodes.
# Usage: ./start_topside.sh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WS_DIR="$(cd "$SCRIPT_DIR/../../.." && pwd)"

# DDS config
export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp
export CYCLONEDDS_URI=file://${HOME}/cyclonedds_topside.xml

# Source ROS2 and workspace
source /opt/ros/jazzy/setup.bash
source "${WS_DIR}/install/setup.bash"

echo "=== ROV Topside ==="
echo "  DDS:       Cyclone (unicast peers)"
echo "  Workspace: ${WS_DIR}"
echo ""

# Launch everything
ros2 launch rov_topside topside.launch.py
