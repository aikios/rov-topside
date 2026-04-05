# ROV Topside

Pilot station for the underwater ROV. Runs on the topside computer (Ubuntu 24.04, ROS2 Jazzy).

## Nodes

| Node | Description |
|------|-------------|
| `joy_publisher` | Custom evdev-based DS4 joystick reader. Publishes `sensor_msgs/Joy` at 20Hz with axes (8) and buttons (13). Replaces `ros2 joy` which has reliability issues with DS4. |
| `dashboard` | Tkinter GUI showing joystick axes, commanded motor values, FC servo output, FC state (armed/mode), battery, depth, depth hold status, and blinking heartbeat indicator. |
| `photogrammetry_saver` | Subscribes to `/photogrammetry/image`, saves full-res JPEGs to `~/rov_captures/`. |

## Prerequisites

```bash
sudo apt install ros-jazzy-desktop ros-jazzy-rmw-cyclonedds-cpp \
    ros-jazzy-image-transport ros-jazzy-compressed-image-transport \
    ros-jazzy-image-transport-plugins ros-jazzy-rqt-image-view \
    ros-jazzy-mavros ros-jazzy-mavros-msgs
sudo pip3 install --break-system-packages evdev
sudo usermod -aG input $USER  # for joystick access
```

## Build

```bash
cd ~/rov_topside_ws
source /opt/ros/jazzy/setup.bash
colcon build --packages-select rov_topside --symlink-install
```

## DDS Configuration

Cyclone DDS with unicast peers (no multicast, Docker-compatible). Config at `~/cyclonedds_topside.xml`.

```bash
export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp
export CYCLONEDDS_URI=file://${HOME}/cyclonedds_topside.xml
```

## Running

### Recommended: use the full launcher script
```bash
bash /tmp/launch_rov.sh
```

### Manual:
```bash
# Terminal 1: Joystick
ros2 run rov_topside joy_publisher

# Terminal 2: Dashboard
ros2 run rov_topside dashboard

# Terminal 3: Photogrammetry saver
ros2 run rov_topside photogrammetry_saver
```

## DS4 Controller Mapping

| Input | ROV Function |
|-------|-------------|
| Left stick Y | Surge (forward/reverse) |
| Left stick X | Sway (lateral) |
| Right stick Y | Heave (rise/sink) |
| Right stick X | Yaw (rotate) |
| D-pad left | Toggle depth hold |
| D-pad up/down | Depth hold setpoint ±0.25m |
| Options | Arm / Disarm |
| Triangle | Photogrammetry capture |

## Diagnostics

```bash
bash /tmp/rov_diag.sh
```
