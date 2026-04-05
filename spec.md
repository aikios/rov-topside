# Underwater ROV — System Specification

## Overview
An underwater remotely operated vehicle (ROV) controlled from a topside pilot station over a tethered network link. The system uses ROS2 for communication between onboard and topside computers, ArduPilot for low-level thruster/servo control, and a dedicated photogrammetry camera system.

## Architecture

### Topside / Pilot Computer
- **Machine:** Ubuntu 24.04 desktop (this computer)
- **Role:** Pilot interface, joystick input, video display, ROS2 master comms
- **Controller:** DualShock 4 (connected via USB/Bluetooth)
- **Software:**
  - ROS2 Jazzy
  - `joy` node — reads DualShock 4 inputs, publishes to `/joy`
  - Pilot control node — maps joystick axes/buttons to ROV commands
  - Video display node — renders pilot camera feeds
  - MAVProxy/QGroundControl (optional, for ArduPilot monitoring)
- **Network:** Ethernet tether to onboard Pi 5

### Onboard Computer — Raspberry Pi 5
- **IP:** 192.168.1.70
- **Hostname:** Hydromeda
- **User:** hydromeda
- **OS:** Ubuntu (aarch64)
- **Role:** Main onboard computer, ROS2 node host, MAVLink bridge
- **Software:**
  - ROS2 Jazzy
  - MAVROS — bridges ROS2 commands to ArduPilot FC over serial/USB
  - USB camera drivers (2x pilot-view cameras)
  - Network relay to Pi Zero for photogrammetry triggers
- **Connections:**
  - ArduPilot flight controller (USB or serial)
  - 2x USB cameras (pilot view — forward and downward)
  - Pi Zero 2 W (USB data link)
  - Ethernet tether to topside

### Photogrammetry Camera — Raspberry Pi Zero 2 W
- **IP:** 192.168.1.71
- **User:** hydromini
- **OS:** Raspberry Pi OS
- **Role:** High-res still capture for photogrammetry
- **Hardware:** Camera Module 3 (IMX708) via ribbon cable
- **Software:**
  - HTTP capture server (libcamera-based)
  - Triggered by Pi 5 over USB data link
- **Notes:** Not running ROS — lightweight HTTP trigger interface only

### Flight Controller — ArduPilot
- **Board:** Pixhawk1 (STM32F42x, fmuv3-capable, 2MB flash)
- **USB ID:** `1209:5741 Generic Pixhawk1`
- **Firmware:** ArduSub stable (flashed via `uploader.py` from Pi 5)
- **Connection:** USB to Pi 5 → `/dev/ttyACM0` @ 115200 baud
- **Interface:** MAVLink protocol over USB to Pi 5
- **ROS2 bridge:** MAVROS on Pi 5 translates ROS2 topics to MAVLink commands
- **Flash tool:** `~/ardupilot_fw/uploader.py` + `ardusub.apj` on Pi 5

## Data Flow

```
DualShock 4
    │ USB/BT
    ▼
┌──────────────────────┐       Ethernet Tether       ┌──────────────────────┐
│   Topside Computer   │◄──────────────────────────►  │   Pi 5 (Onboard)     │
│                      │    ROS2 DDS (auto-discovery) │                      │
│  joy_node            │                              │  mavros_node         │
│  pilot_control_node  │                              │  camera_driver (x2)  │
│  video_display_node  │                              │  photogrammetry_trig │
└──────────────────────┘                              └─────┬────────┬───────┘
                                                            │ USB    │ USB/Serial
                                                            ▼        ▼
                                                     ┌──────────┐ ┌──────────────┐
                                                     │ Pi Zero  │ │  ArduPilot   │
                                                     │ CM3 Cam  │ │  Flight Ctrl │
                                                     └──────────┘ └──────────────┘
```

## ROS2 Topics (Planned)

| Topic | Type | Direction | Description |
|-------|------|-----------|-------------|
| `/joy` | `sensor_msgs/Joy` | Topside → Onboard | Raw joystick state |
| `/cmd_vel` | `geometry_msgs/Twist` | Topside → Onboard | Velocity commands for ROV |
| `/mavros/rc/override` | `mavros_msgs/OverrideRCIn` | Onboard | RC override to ArduPilot |
| `/camera/pilot_front/image_raw` | `sensor_msgs/Image` | Onboard → Topside | Forward camera feed |
| `/camera/pilot_down/image_raw` | `sensor_msgs/Image` | Onboard → Topside | Downward camera feed |
| `/photogrammetry/trigger` | `std_msgs/Empty` | Onboard | Trigger photogrammetry capture |
| `/mavros/state` | `mavros_msgs/State` | Onboard → Topside | FC connection/arm status |
| `/mavros/imu/data` | `sensor_msgs/Imu` | Onboard → Topside | IMU telemetry |
| `/mavros/battery` | `sensor_msgs/BatteryState` | Onboard → Topside | Battery status |

## DDS Configuration (Cyclone DDS)
- **RMW:** `rmw_cyclonedds_cpp` (set via `RMW_IMPLEMENTATION` env var)
- **Multicast disabled** — uses explicit unicast peer discovery for Docker compatibility
- **Topside config:** `cyclonedds_topside.xml` — peers: `192.168.1.70` (Pi 5), `192.168.1.69` (self)
- **Onboard config:** `cyclonedds_onboard.xml` — peers: `192.168.1.69` (topside), `192.168.1.70` (self)
- **Env vars required on each machine:**
  ```
  RMW_IMPLEMENTATION=rmw_cyclonedds_cpp
  CYCLONEDDS_URI=file:///path/to/cyclonedds.xml
  ```
- **Docker note:** Use `network_mode: host` or map the XML peers to container-accessible addresses

## Deployment Strategy
- All ROS2 nodes will be containerized with Docker for reproducible deployment
- Separate Docker Compose stacks for topside and onboard
- Shared ROS2 workspace images as base layers
- Goal: `docker compose up` on each machine to launch the full system

## ROS2 Workspaces
- **Onboard (Pi 5):** `~/rov_ws/src/rov_cameras/`
  - `photogrammetry_node` — service `/photogrammetry/capture`, publishes `/photogrammetry/image`
  - `joy_to_mavlink` — subscribes `/joy`, translates DS4 → 6-DOF PWM channels (logging mode, MAVROS TBD)
  - Launch: `cameras.launch.py` — photogrammetry node + 2x `usb_cam` for pilot cameras
- **Topside:** `~/rov_topside_ws/src/rov_topside/`
  - `photogrammetry_saver` — subscribes `/photogrammetry/image`, saves to `~/rov_captures/`
  - Launch: `topside.launch.py`

## Repositories
- **`rov-topside`** — Topside/pilot computer ROS2 workspace, Docker configs
- **`rov-onboard`** — Pi 5 onboard ROS2 workspace, MAVROS config, Docker configs

## Quick Start

### 1. Build (one-time, or after code changes)

```bash
# Topside
~/rov_topside_ws/src/rov_topside/scripts/build.sh

# Onboard (Pi 5)
ssh hydromeda@192.168.1.70
~/rov_ws/src/rov_cameras/scripts/build.sh
```

### 2. Start onboard (Pi 5) — 2 SSH sessions

```bash
# Session 1: cameras + photogrammetry
~/rov_ws/src/rov_cameras/scripts/start_onboard.sh

# Session 2: joystick translation
~/rov_ws/src/rov_cameras/scripts/start_joy_translator.sh
```

### 3. Start topside — 2 terminals

```bash
# Terminal 1: main nodes (image saver, etc.)
~/rov_topside_ws/src/rov_topside/scripts/start_topside.sh

# Terminal 2: DualShock 4 joystick
~/rov_topside_ws/src/rov_topside/scripts/start_joy.sh
```

### 4. Operate

```bash
# Trigger a photogrammetry capture (saved to ~/rov_captures/)
~/rov_topside_ws/src/rov_topside/scripts/capture.sh

# Burst of 5 captures
~/rov_topside_ws/src/rov_topside/scripts/capture.sh 5

# Move the DS4 sticks — watch joy_to_mavlink logs on Pi 5
```

## Hardware BOM (To Document)
- [ ] Raspberry Pi 5
- [ ] Raspberry Pi Zero 2 W + Camera Module 3
- [ ] ArduPilot-compatible flight controller
- [ ] Thrusters (type/count TBD)
- [ ] Servos (purpose TBD)
- [ ] 2x USB cameras (pilot view)
- [ ] Ethernet tether
- [ ] DualShock 4 controller
- [ ] Frame / enclosure
- [ ] Power system (batteries, ESCs, voltage regulators)

## Status
- [x] Spec created
- [x] GitHub repos created (aikios/rov-topside, aikios/rov-onboard)
- [x] ROS2 Jazzy installed on topside
- [x] ROS2 Jazzy installed on Pi 5
- [x] Cyclone DDS cross-machine discovery verified
- [x] Photogrammetry capture via ROS2 (Pi Zero → Pi 5 → topside) verified
- [ ] Pilot USB cameras via ROS2 (pending physical cameras)
- [x] Joystick (DS4) → ROS2 → Pi 5 translation node verified (logging mode)
- [x] ArduSub firmware flashed to Pixhawk1 (fmuv3) via USB from Pi 5
- [x] MAVROS connected to ArduSub FC over USB
- [x] ArduSub configured for VECTORED_6DOF (8 thrusters, SERVO1-8 = Motor1-8)
- [x] joy_to_mavlink publishing RC overrides to MAVROS
- [ ] Topside visualization (rqt dashboard for controls + servo outputs)
- [ ] Test RC override → servo output without thrusters connected
- [ ] Pilot USB cameras via ROS2 (pending physical cameras)
- [ ] Docker containerization
