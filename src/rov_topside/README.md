# ROV Topside

Pilot station for the underwater ROV. Runs on the topside computer (Ubuntu 24.04, ROS2 Jazzy).

## Prerequisites

```bash
# ROS2 Jazzy (should already be installed)
sudo apt install ros-jazzy-desktop

# Required ROS2 packages
sudo apt install \
    ros-jazzy-rmw-cyclonedds-cpp \
    ros-jazzy-joy \
    ros-jazzy-joy-linux \
    ros-jazzy-image-transport \
    ros-jazzy-compressed-image-transport \
    ros-jazzy-image-transport-plugins \
    ros-jazzy-rqt-image-view

# Joystick permissions (log out and back in after)
sudo usermod -aG input $USER
```

## Setup

```bash
# Build the workspace
cd ~/rov_topside_ws
source /opt/ros/jazzy/setup.bash
colcon build --packages-select rov_topside --symlink-install

# Or use the build script
./src/rov_topside/scripts/build.sh
```

## DDS Configuration

Cyclone DDS is used with unicast peer discovery (no multicast) for Docker compatibility.

The config file at `~/cyclonedds_topside.xml` must exist with the correct peer IPs:
- Topside: `192.168.1.69`
- Onboard (Pi 5): `192.168.1.70`

Two environment variables must be set in every terminal:
```bash
export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp
export CYCLONEDDS_URI=file://${HOME}/cyclonedds_topside.xml
```

The startup scripts handle this automatically.

## Running

You need **two terminals** on the topside computer:

### Terminal 1 — Main topside nodes
```bash
./src/rov_topside/scripts/start_topside.sh
```

This starts:
- `photogrammetry_saver` — subscribes to `/photogrammetry/image`, saves full-res JPEGs to `~/rov_captures/`

### Terminal 2 — Joystick
```bash
./src/rov_topside/scripts/start_joy.sh
```

This starts:
- `joy_node` — reads DualShock 4 at `/dev/input/js0`, publishes `sensor_msgs/Joy` on `/joy` at 20Hz

### Triggering a photogrammetry capture
```bash
# Single capture
./src/rov_topside/scripts/capture.sh

# Burst of 5
./src/rov_topside/scripts/capture.sh 5
```

Images are saved to `~/rov_captures/photogrammetry_YYYYMMDD_HHMMSS_ffffff.jpg`.

## Nodes

| Node | Topic/Service | Type | Description |
|------|--------------|------|-------------|
| `photogrammetry_saver` | `/photogrammetry/image` (sub) | `CompressedImage` | Saves incoming photogrammetry images to disk |
| `joy_node` | `/joy` (pub) | `Joy` | DS4 controller input |

## DS4 Controller Mapping

| Input | ROV Function |
|-------|-------------|
| Left stick X | Yaw (rotate) |
| Left stick Y | Forward / Reverse |
| Right stick X | Lateral (strafe) |
| Right stick Y | Pitch (tilt) |
| L2 trigger | Descend |
| R2 trigger | Ascend |
| L1 / R1 | Lights down / up |
| Cross (X) | Arm / Disarm toggle |
| Triangle | Photogrammetry capture |

## Debugging

```bash
# Check DDS is working (should see topics from both machines)
export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp
export CYCLONEDDS_URI=file://${HOME}/cyclonedds_topside.xml
source /opt/ros/jazzy/setup.bash

ros2 topic list
ros2 topic echo /joy --once
ros2 topic hz /joy
ros2 service list
```
