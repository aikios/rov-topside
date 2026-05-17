#!/bin/bash
# ROV Topside — stop all nodes (native + Docker)

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_DIR="$SCRIPT_DIR/logs"

echo "[stop] Stopping topside ROV..."

# Stop Docker containers if any are running
cd "$SCRIPT_DIR"
docker compose down 2>/dev/null || true

# Kill native processes by PID files
for pidfile in "$LOG_DIR"/*.pid; do
    if [[ -f "$pidfile" ]]; then
        pid=$(cat "$pidfile")
        kill "$pid" 2>/dev/null && echo "[stop] Killed $(basename "$pidfile" .pid) (PID $pid)"
        rm -f "$pidfile"
    fi
done

# Kill by name in case of foreground mode or missed PIDs
pkill -f 'joy_publisher' 2>/dev/null || true
pkill -f 'web_dashboard\|rov_dashboard' 2>/dev/null || true
pkill -f 'photogrammetry_saver\|rov_photogrammetry.*saver' 2>/dev/null || true

# Free ports
fuser -k 8080/tcp 9090/tcp 2>/dev/null || true

# Clean DDS shared memory
rm -f /dev/shm/cyclonedds_* /dev/shm/iox_* 2>/dev/null || true

echo "[stop] All topside nodes stopped."
