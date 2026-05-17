# ROV Topside

Pilot station software for the underwater ROV. Runs on the topside Ubuntu laptop connected to the ROV via Ethernet tether.

## Hardware

| Component | Details |
|-----------|---------|
| Computer | Ubuntu 24.04 desktop (`192.168.1.69`) |
| Controller | DualShock 4 (USB or Bluetooth) |
| Tether | Ethernet to Pi 5 at `192.168.1.70` |

## Quick Start

### Native (recommended for development)

```bash
git clone git@github.com:aikios/rov-topside.git ~/rov_topside_ws
cd ~/rov_topside_ws
source /opt/ros/jazzy/setup.bash
colcon build --symlink-install
source install/setup.bash

export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp
export CYCLONEDDS_URI=file://$HOME/rov_topside_ws/cyclonedds_topside.xml

./start.sh          # foreground (Ctrl+C to stop)
./start.sh -d       # daemon mode (logs in ./logs/)
./stop.sh           # stop everything
```

Open dashboard: **http://localhost:8080**

### Docker

```bash
./start-docker.sh   # builds image if needed, starts all containers
./stop-docker.sh    # stops and removes containers
```

## ROS2 Packages

### `rov_joystick` — DualShock 4 publisher

**Node:** `joy_publisher`

Custom DS4 driver using `evdev` (replaces `ros2-joy` which has DS4 issues):

- Reads `/dev/input/event*` directly via evdev
- Publishes `sensor_msgs/Joy` on `/joy` at 20 Hz
- Normalises axes to `−1.0…+1.0`, applies ROS conventions (Y-inverted sticks, triggers mapped `1.0`→`−1.0`)
- Correctly identifies the DS4 main gamepad vs touchpad/motion sensor devices

### `rov_dashboard` — Web UI

**Node:** `server`

Browser-based operator dashboard:

- **HTTP `:8080`** — serves `static/index.html`
- **WebSocket `:9090`** — pushes JSON state to all connected browsers at 10 Hz, binary frames for camera preview

Dashboard panels:
- Live camera preview from Pi Zero (~2 fps MJPEG)
- Joystick axis bars + motor output visualisation (8 channels)
- FC heartbeat indicator, armed state, flight mode, depth readout
- Depth hold status and live PID gains (P/I/D)
- Photogrammetry capture flash indicator and count
- Camera rotation toggle button

Subscribes to: `/joy`, `/mavros/state`, `/mavros/battery`, `/mavros/vfr_hud`, `/mavros/mavros/override`, `/mavros/mavros/out`, `/rov/depth_setpoint`, `/rov/depth_current`, `/rov/depth_hold_active`, `/rov/pid_status`, `/rov/fc_heartbeat`, `/photogrammetry/preview`, `/photogrammetry/image`

### `rov_photogrammetry` — Image saver

**Node:** `saver`

- Subscribes `/photogrammetry/image` (`sensor_msgs/CompressedImage`)
- Saves each frame as a timestamped JPEG to `./captures/`
- Configurable save path via `save_dir` ROS parameter

## Controller Mapping

| Input | Action |
|-------|--------|
| Left stick Y / X | Surge / Sway |
| Right stick Y / X | Heave / Yaw (manual mode) |
| Square | Toggle depth hold |
| L1 / R1 | Depth setpoint −0.25 m / +0.25 m |
| Circle | Photogrammetry capture |
| Options | Arm / Disarm |

## Network & DDS

CycloneDDS with unicast peer discovery (no multicast). Edit `cyclonedds_topside.xml` if IPs change:

```xml
<Peer address="192.168.1.70"/>  <!-- Pi 5 onboard -->
<Peer address="192.168.1.69"/>  <!-- this machine (self) -->
```

All containers use `network_mode: host`. `RMW_IMPLEMENTATION=rmw_cyclonedds_cpp` is set in start scripts and Dockerfile.

## Captures

Photogrammetry images are saved to `./captures/` (relative to the workspace root). In Docker, this folder is bind-mounted into the container.

## Dependencies

Installed by Dockerfile / native prerequisites:

- `ros-jazzy-rmw-cyclonedds-cpp`
- `ros-jazzy-mavros-msgs`
- `ros-jazzy-image-transport`, `ros-jazzy-compressed-image-transport`
- `python3-evdev`, `python3-websockets`

## Related Repo

Onboard Pi 5 software: [`aikios/rov-onboard`](https://github.com/aikios/rov-onboard)
