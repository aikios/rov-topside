#!/bin/bash
# ROV Topside — stop all services
set -e
docker compose down
rm -f /dev/shm/cyclonedds_* /dev/shm/iox_* 2>/dev/null
echo "Topside stopped."
