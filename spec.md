# Underwater ROV — System Specification

## Overview
An underwater remotely operated vehicle (ROV) controlled from a topside pilot station over a tethered network link. Uses ROS2 Jazzy for inter-machine communication, ArduSub on a Pixhawk1 for flight control, and a dedicated Pi Zero photogrammetry camera.

## Architecture

```
DualShock 4
    │ USB (evdev)
    ▼
┌───────────────────────────┐     Ethernet Tether     ┌────────────────────────────┐
│   Topside Computer        │◄───────────────────────► │   Pi 5 (Onboard)           │
│   Ubuntu 24.04            │   Cyclone DDS (unicast)  │   Ubuntu 24.04 (aarch64)   │
│                           │                          │                            │
│ joy_publisher (evdev→ROS) │──── /joy ───────────────►│ joy_to_mavlink             │
│ dashboard (tkinter GUI)   │◄── /mavros/* ────────────│   ├─ MANUAL_CONTROL → FC   │
│ photogrammetry_saver      │◄── /photogrammetry/* ────│   ├─ arms/disarms FC       │
│                           │                          │   └─ forwards telem → UDP  │
│                           │                          │                            │
│                           │                          │ MAVROS (reads UDP:14550)   │
│                           │                          │   └─ publishes ROS topics  │
│                           │                          │                            │
│                           │                          │ photogrammetry_node        │
└───────────────────────────┘                          └─────┬────────┬─────────────┘
                                                             │ USB    │ /dev/ttyACM0
                                                             ▼        ▼
                                                      ┌──────────┐ ┌──────────────┐
                                                      │ Pi Zero  │ │  Pixhawk1    │
                                                      │ CM3 Cam  │ │  ArduSub     │
                                                      └──────────┘ └──────────────┘
```

### MAVLink Data Path
```
joy_to_mavlink ──MANUAL_CONTROL──► /dev/ttyACM0 (FC serial, pymavlink)
      │
      └──raw FC telemetry bytes──► UDP:14550 → MAVROS → ROS2 topics
```

**Why not MAVROS for commands?** MAVROS 2.14.0 (ROS2 Jazzy) does not forward ManualControl messages published on its ROS topics to the FC. Verified by publishing 100+ messages to `/mavros/mavros/send` with zero servo output change. Direct serial via pymavlink is the working solution.

### Topside Computer
- **IP:** 192.168.1.69
- **Nodes:**
  - `joy_publisher` — custom evdev-based DS4 reader (replaces `ros2 joy` which has DS4 issues)
  - `dashboard` — tkinter GUI: joystick, commanded values, servo output, FC state, depth hold, heartbeat
  - `photogrammetry_saver` — saves photogrammetry images to `~/rov_captures/`

### Onboard — Raspberry Pi 5
- **IP:** 192.168.1.70 | **User:** hydromeda
- **Nodes:**
  - `joy_to_mavlink` — owns FC serial, sends MANUAL_CONTROL, forwards telemetry to MAVROS via UDP
  - MAVROS — reads FC telemetry from UDP:14550, publishes ROS topics only
  - `photogrammetry_node` — HTTP-triggers Pi Zero camera, publishes images

### Photogrammetry Camera — Pi Zero 2 W
- **IP:** 192.168.1.71 (WiFi) / 192.168.7.2 (USB)
- HTTP capture server on port 8080, Camera Module 3 (IMX708, 4608x2592)
- Not running ROS — triggered by Pi 5 via HTTP

### Flight Controller — Pixhawk1
- **Board:** Pixhawk1 fmuv3 (STM32F42x, 2MB flash, 8 MAIN + 6 AUX outputs)
- **Firmware:** ArduSub 4.5.7 fmuv3
- **Frame:** FRAME_CONFIG=2 (VECTORED_6DOF, 8 motors)
- **Connection:** USB → `/dev/ttyACM0` @ 115200 baud
- **Depth sensor:** Blue Robotics Bar30 on I2C
- **USB power cycle:** `echo 0/1 > /sys/bus/usb/devices/2-1/authorized`
- **Flash tool:** `~/ardupilot_fw/uploader.py`

## Control Scheme (DualShock 4)

| Input | Function |
|-------|----------|
| Left stick Y | Surge (forward/reverse) |
| Left stick X | Sway (lateral) |
| Right stick Y | Heave (rise/sink) |
| Right stick X | Yaw (rotate) |
| D-pad left | Toggle depth hold |
| D-pad up/down | Adjust depth hold setpoint ±0.25m |
| Options | Arm / Disarm |
| Triangle | Photogrammetry capture |

## DDS Configuration (Cyclone DDS)
- **RMW:** `rmw_cyclonedds_cpp`
- **Multicast disabled** — unicast peer discovery for Docker compatibility
- **Important:** Start joy_publisher BEFORE joy_to_mavlink (DDS discovery order)
- **Important:** Clear `/dev/shm/cyclonedds_*` between restarts to avoid zombie participants

## Depth Hold (PID)
- Reads depth from `/mavros/vfr_hud` (negative altitude = depth in meters)
- PID: kp=1.0, ki=0.1, kd=0.5 (tunable via ROS params)
- D-pad left toggles; captures current depth as setpoint
- D-pad up/down adjusts ±0.25m per press
- Output maps to MANUAL_CONTROL `z` axis

## Quick Start

```bash
# Full system launch (kills stale processes, starts everything in order)
bash /tmp/launch_rov.sh

# Diagnostics (checks data flow at each step)
bash /tmp/rov_diag.sh
```

## Repositories
- **[aikios/rov-topside](https://github.com/aikios/rov-topside)**
- **[aikios/rov-onboard](https://github.com/aikios/rov-onboard)**

## Known Issues
- MAVROS 2.14.0 cannot forward ManualControl to FC — using direct serial
- ArduSub 4.5.7 VECTORED_6DOF mixer broken for forward/lateral — MANUAL_CONTROL works directly
- DDS zombie participants require full cleanup between restarts
- Standard `ros2 joy` node unreliable with DS4 — custom evdev publisher required

## Status
- [x] ROS2 Jazzy on topside + Pi 5
- [x] Cyclone DDS unicast cross-machine discovery
- [x] Photogrammetry pipeline (Pi Zero → Pi 5 → topside)
- [x] Custom DS4 joystick publisher (evdev)
- [x] ArduSub 4.5.7, FRAME_CONFIG=2 (VECTORED_6DOF)
- [x] MANUAL_CONTROL driving motor outputs via direct serial
- [x] Arm/disarm via Options button
- [x] Depth sensor (Bar30) + depth hold PID
- [x] Dashboard with heartbeat, joystick, commands, servo output
- [x] Deadzone + noise filtering
- [x] USB power cycle (software, no unplug)
- [x] Launch + diagnostics scripts
- [ ] Pilot USB cameras
- [ ] PID auto-tuner
- [ ] Docker containerization
