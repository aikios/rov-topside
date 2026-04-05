#!/usr/bin/env bash
# Start the ROV topside dashboard.
# Usage: ./start_dashboard.sh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WS_DIR="$(cd "$SCRIPT_DIR/../../.." && pwd)"

export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp
export CYCLONEDDS_URI=file://${HOME}/cyclonedds_topside.xml

source /opt/ros/jazzy/setup.bash
source "${WS_DIR}/install/setup.bash"

echo "=== ROV Dashboard ==="
ros2 run rov_topside dashboard
