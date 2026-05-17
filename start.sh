#!/bin/bash
# ROV Topside — start all nodes natively
# Usage: ./start.sh        (foreground logs)
#        ./start.sh -d     (background/daemon mode)

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_DIR="$SCRIPT_DIR/logs"
mkdir -p "$LOG_DIR"

echo "=== ROV Topside (native) ==="

# --- Ensure joystick devices are readable ---
for dev in /dev/input/event*; do
    if [ -r "$dev" ] 2>/dev/null; then continue; fi
    echo "[start] Setting input device permissions..."
    sudo chmod 666 /dev/input/event* /dev/input/js* 2>/dev/null
    break
done

# --- Cleanup stale DDS state ---
echo "[start] Cleaning up stale DDS shared memory..."
rm -f /dev/shm/cyclonedds_* /dev/shm/iox_* 2>/dev/null || true

# --- Kill any existing ROV nodes ---
echo "[start] Killing stale ROV processes..."
pkill -f 'joy_publisher' 2>/dev/null || true
pkill -f 'web_dashboard\|rov_dashboard' 2>/dev/null || true
pkill -f 'photogrammetry_saver\|rov_photogrammetry.*saver' 2>/dev/null || true
fuser -k 8080/tcp 9090/tcp 2>/dev/null || true
sleep 1

# --- Environment ---
source /opt/ros/jazzy/setup.bash
source "$SCRIPT_DIR/install/setup.bash"
export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp
export CYCLONEDDS_URI=file://$SCRIPT_DIR/cyclonedds_topside.xml

DAEMON=false
if [[ "$1" == "-d" ]]; then
    DAEMON=true
fi

launch_node() {
    local name="$1"
    shift
    if $DAEMON; then
        echo "[start] Launching $name (background, log: $LOG_DIR/$name.log)"
        nohup "$@" > "$LOG_DIR/$name.log" 2>&1 &
        echo $! > "$LOG_DIR/$name.pid"
    else
        echo "[start] Launching $name"
        "$@" &
    fi
}

# --- 1. joy_publisher (DS4 joystick, start first for DDS discovery) ---
launch_node joy_publisher ros2 run rov_joystick joy_publisher
sleep 2

# --- 2. web_dashboard (HTTP :8080, WebSocket :9090) ---
launch_node web_dashboard ros2 run rov_dashboard server
sleep 1

# --- 3. photogrammetry_saver (saves captures to ./captures/) ---
launch_node photogrammetry_saver ros2 run rov_photogrammetry saver --ros-args -p save_dir:="$SCRIPT_DIR/captures"

echo "[start] All topside nodes launched."
echo "[start] Dashboard: http://localhost:8080"
echo "[start] Captures saved to: $SCRIPT_DIR/captures/"

if ! $DAEMON; then
    echo "[start] Press Ctrl+C to stop all nodes."
    trap 'echo "[start] Stopping..."; kill 0; exit' SIGINT SIGTERM
    wait
fi
