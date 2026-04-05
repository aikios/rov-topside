#!/usr/bin/env bash
# Start the joystick node for the DualShock 4 controller.
# Run this in a separate terminal alongside start_topside.sh.
# Usage: ./start_joy.sh [device_id]
set -euo pipefail

DEVICE_ID="${1:-0}"

export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp
export CYCLONEDDS_URI=file://${HOME}/cyclonedds_topside.xml

source /opt/ros/jazzy/setup.bash

echo "=== ROV Joystick ==="
echo "  Device: /dev/input/js${DEVICE_ID}"
echo ""

ros2 run joy joy_node --ros-args \
    -p device_id:=${DEVICE_ID} \
    -p autorepeat_rate:=20.0 \
    -p deadzone:=0.05
