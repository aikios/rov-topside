#!/usr/bin/env bash
# Trigger a photogrammetry capture via ROS2 service call.
# The image will be saved by the photogrammetry_saver node to ~/rov_captures/.
# Usage: ./capture.sh [count]
set -euo pipefail

COUNT="${1:-1}"

export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp
export CYCLONEDDS_URI=file://${HOME}/cyclonedds_topside.xml

source /opt/ros/jazzy/setup.bash

for i in $(seq 1 "$COUNT"); do
    echo "Capture ${i}/${COUNT}..."
    ros2 service call /photogrammetry/capture std_srvs/srv/Trigger
    [ "$i" -lt "$COUNT" ] && sleep 1
done
