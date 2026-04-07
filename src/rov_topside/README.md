# ROV Topside

Pilot station for the underwater ROV. Runs on any machine with Docker and a DualShock 4 controller.

## Quick Start (Docker)

```bash
git clone git@github.com:aikios/rov-topside.git && cd rov-topside

# Edit cyclonedds_topside.xml — set peer IPs for your network:
#   - Your machine's IP (topside)
#   - Pi 5's IP (onboard)

docker compose up -d

# Open http://localhost:8080 in your browser
# Captures saved to ./captures/
```

## Services

| Container | Description |
|-----------|-------------|
| `joy_publisher` | Reads DS4 controller via evdev, publishes `/joy` at 20Hz |
| `web_dashboard` | Serves Aqua-themed web UI on :8080, WebSocket telemetry on :9090 |
| `photogrammetry_saver` | Saves full-res captures to `./captures/` |

## Web Dashboard

Open **http://localhost:8080** from any browser on the network.

Features:
- Live camera preview from Pi Zero (~2fps)
- Joystick axis visualization
- Motor output with per-channel bars
- Depth hold status + PID info
- FC heartbeat, armed state, depth
- Capture flash indicator + count
- Camera rotation button

## DS4 Controller Mapping

| Input | Function |
|-------|----------|
| Left stick Y/X | Surge / Sway |
| Right stick Y/X | Heave / Yaw |
| Square | Toggle depth hold |
| L1 / R1 | Depth setpoint shallower / deeper |
| Circle | Photogrammetry capture |
| Options | Arm / Disarm |

## Native Development

```bash
# Don't use Docker for small changes — run natively:
source /opt/ros/jazzy/setup.bash
source ~/rov_topside_ws/install/setup.bash
export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp
export CYCLONEDDS_URI=file://${HOME}/cyclonedds_topside.xml

ros2 run rov_topside joy_publisher &
ros2 run rov_topside web_dashboard &
```

## DDS Configuration

Cyclone DDS with unicast peers (no multicast). Edit `cyclonedds_topside.xml`:
```xml
<Peers>
  <Peer address="ONBOARD_PI5_IP"/>
  <Peer address="THIS_MACHINE_IP"/>
</Peers>
```
