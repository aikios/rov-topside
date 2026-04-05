"""
Custom DS4 joystick publisher using evdev.

Replaces ros2 joy/joy_linux nodes which have issues with the DS4.
Reads /dev/input/event* directly and publishes sensor_msgs/Joy.
"""

import threading
import evdev
from evdev import ecodes

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Joy


# DS4 evdev axis codes → Joy axes index
# ABS_X=0 (LX), ABS_Y=1 (LY), ABS_Z=2 (L2), ABS_RX=3 (RX), ABS_RY=4 (RY), ABS_RZ=5 (R2)
# ABS_HAT0X=16 (dpad X), ABS_HAT0Y=17 (dpad Y)
DS4_AXIS_MAP = {
    ecodes.ABS_X: 0,      # Left stick X
    ecodes.ABS_Y: 1,      # Left stick Y
    ecodes.ABS_Z: 2,      # L2 trigger
    ecodes.ABS_RX: 3,     # Right stick X
    ecodes.ABS_RY: 4,     # Right stick Y
    ecodes.ABS_RZ: 5,     # R2 trigger
    ecodes.ABS_HAT0X: 6,  # D-pad X
    ecodes.ABS_HAT0Y: 7,  # D-pad Y
}

# DS4 evdev button codes → Joy buttons index
DS4_BTN_MAP = {
    ecodes.BTN_SOUTH: 0,   # Cross
    ecodes.BTN_EAST: 1,    # Circle
    ecodes.BTN_NORTH: 2,   # Triangle
    ecodes.BTN_WEST: 3,    # Square
    ecodes.BTN_TL: 4,      # L1
    ecodes.BTN_TR: 5,      # R1
    ecodes.BTN_TL2: 6,     # L2 button
    ecodes.BTN_TR2: 7,     # R2 button
    ecodes.BTN_SELECT: 8,  # Share
    ecodes.BTN_START: 9,   # Options
    ecodes.BTN_THUMBL: 10, # L3
    ecodes.BTN_THUMBR: 11, # R3
    ecodes.BTN_MODE: 12,   # PS button
}


def find_ds4():
    """Find the DS4 evdev device (main controller, not touchpad/motion)."""
    for path in evdev.list_devices():
        dev = evdev.InputDevice(path)
        if 'wireless controller' in dev.name.lower() or 'dualshock' in dev.name.lower():
            caps = dev.capabilities(verbose=False)
            # Must have buttons (EV_KEY) AND axes (EV_ABS) — excludes motion sensors
            if ecodes.EV_ABS not in caps or ecodes.EV_KEY not in caps:
                continue
            key_codes = [c for c in caps[ecodes.EV_KEY]]
            abs_codes = [c[0] for c in caps[ecodes.EV_ABS]]
            # Must have gamepad buttons (BTN_SOUTH) AND both sticks (ABS_X + ABS_RX)
            if (ecodes.BTN_SOUTH in key_codes and
                    ecodes.ABS_X in abs_codes and ecodes.ABS_RX in abs_codes):
                return dev
    return None


class JoyPublisher(Node):
    def __init__(self):
        super().__init__('joy_publisher')

        self.declare_parameter('rate', 20.0)
        rate = self.get_parameter('rate').value

        self.pub = self.create_publisher(Joy, '/joy', 10)
        self.timer = self.create_timer(1.0 / rate, self.publish_joy)

        self.axes = [0.0] * 8      # 8 axes
        self.buttons = [0] * 13    # 13 buttons

        self.dev = find_ds4()
        if self.dev is None:
            self.get_logger().error('DS4 controller not found!')
            return

        self.get_logger().info(f'Opened DS4: {self.dev.name} ({self.dev.path})')

        # Get axis ranges for normalization
        self.axis_info = {}
        caps = self.dev.capabilities(verbose=False)
        if ecodes.EV_ABS in caps:
            for code, info in caps[ecodes.EV_ABS]:
                self.axis_info[code] = info

        # Read initial state
        self._read_initial_state()

        # Start evdev reader thread
        self.reader_thread = threading.Thread(target=self._read_loop, daemon=True)
        self.reader_thread.start()

    def _read_initial_state(self):
        """Read current axis values at startup."""
        for code, idx in DS4_AXIS_MAP.items():
            if code in self.axis_info:
                val = self.dev.absinfo(code).value
                self.axes[idx] = self._normalize_axis(code, val)

    def _normalize_axis(self, code, value):
        """Normalize evdev axis to -1.0..1.0 (or 1.0..-1.0 for triggers)."""
        if code not in self.axis_info:
            return 0.0
        info = self.axis_info[code]
        min_val = info.min
        max_val = info.max

        if code == ecodes.ABS_HAT0X:
            return -float(value)  # left=+1, right=-1 (ROS convention)
        if code == ecodes.ABS_HAT0Y:
            return -float(value)  # up=+1, down=-1 (ROS convention)

        # Normalize to -1..1
        center = (min_val + max_val) / 2.0
        half_range = (max_val - min_val) / 2.0
        if half_range == 0:
            return 0.0
        normalized = -(value - center) / half_range  # invert Y axes

        # Triggers (L2/R2): range 0..255, map to 1.0(released)..-1.0(pressed)
        if code in (ecodes.ABS_Z, ecodes.ABS_RZ):
            normalized = 1.0 - (value - min_val) / (max_val - min_val) * 2.0

        return max(-1.0, min(1.0, normalized))

    def _read_loop(self):
        """Background thread reading evdev events."""
        try:
            for event in self.dev.read_loop():
                if event.type == ecodes.EV_ABS:
                    if event.code in DS4_AXIS_MAP:
                        idx = DS4_AXIS_MAP[event.code]
                        self.axes[idx] = self._normalize_axis(event.code, event.value)
                elif event.type == ecodes.EV_KEY:
                    if event.code in DS4_BTN_MAP:
                        idx = DS4_BTN_MAP[event.code]
                        self.buttons[idx] = event.value
        except Exception as e:
            self.get_logger().error(f'Evdev read error: {e}')

    def publish_joy(self):
        msg = Joy()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = 'joy'
        msg.axes = list(self.axes)
        msg.buttons = list(self.buttons)
        self.pub.publish(msg)


def main(args=None):
    rclpy.init(args=args)
    node = JoyPublisher()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
