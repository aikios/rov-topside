#!/bin/bash
# ROV Topside — start all services
# Usage: ./start.sh
set -e

echo "=== ROV Topside ==="

# Ensure joystick device is readable
for dev in /dev/input/event*; do
    if [ -r "$dev" ] 2>/dev/null; then continue; fi
    echo "Setting input device permissions..."
    sudo chmod 666 /dev/input/event* /dev/input/js* 2>/dev/null
    break
done

# Clean stale DDS shared memory
rm -f /dev/shm/cyclonedds_* /dev/shm/iox_* 2>/dev/null

# Kill any stale ports
fuser -k 8080/tcp 9090/tcp 2>/dev/null || true
sleep 1

# Start
docker compose up -d
sleep 3

# Verify
echo ""
docker compose ps --format "table {{.Name}}\t{{.Status}}"
echo ""
echo "Dashboard: http://localhost:8080"
echo "Captures saved to: ./captures/"
