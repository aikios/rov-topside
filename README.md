# ROV Topside

Pilot station for the underwater ROV. Runs on any machine with Docker and a DualShock 4 controller. Dashboard served as a web app — no native dependencies required on the host.

## Prerequisites

- Docker + Docker Compose
- DualShock 4 controller (USB or Bluetooth)
- Network access to the onboard Pi 5

## Production Deployment

```bash
# 1. Clone
git clone git@github.com:aikios/rov-topside.git
cd rov-topside

# 2. Configure network — edit cyclonedds_topside.xml:
#    Set <Peer address="..."/> to:
#      - This machine's IP
#      - Onboard Pi 5's IP
nano cyclonedds_topside.xml

# 3. Start
./start.sh

# 4. Open dashboard
#    http://localhost:8080

# 5. Stop
./stop.sh
```

## ROS2 Packages

| Package | Container | Purpose |
|---------|-----------|---------|
| `rov_joystick` | `joy_publisher` | Reads DS4 via evdev, publishes `/joy` at 20Hz |
| `rov_dashboard` | `web_dashboard` | HTTP :8080 + WebSocket :9090 + camera preview |
| `rov_photogrammetry` | `photogrammetry_saver` | Saves full-res captures to `./captures/` |

## Dashboard

Open **http://localhost:8080** from any browser.

- Live camera preview from Pi Zero (~2fps)
- Joystick axis bars + motor output visualization
- FC heartbeat, armed state, mode, depth
- Depth hold status + PID info
- Capture flash indicator + count
- Camera rotation button

## Controller Mapping

| Input | Function |
|-------|----------|
| Left stick Y / X | Surge / Sway |
| Right stick Y / X | Heave / Yaw |
| Square | Toggle depth hold |
| L1 / R1 | Depth setpoint shallower / deeper |
| Circle | Photogrammetry capture |
| Options | Arm / Disarm |

## Native Development

For faster iteration, run without Docker:

```bash
sudo apt install ros-jazzy-desktop ros-jazzy-rmw-cyclonedds-cpp ros-jazzy-mavros-msgs
sudo pip3 install --break-system-packages evdev websockets

cd ~/rov_topside_ws
source /opt/ros/jazzy/setup.bash
colcon build --symlink-install
source install/setup.bash

export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp
export CYCLONEDDS_URI=file://$HOME/cyclonedds_topside.xml

ros2 run rov_joystick joy_publisher &
ros2 run rov_dashboard server &
ros2 run rov_photogrammetry saver &
# http://localhost:8080
```

## Network

Cyclone DDS with unicast peers (no multicast). Edit `cyclonedds_topside.xml` with your IPs. All containers use `network_mode: host`.
