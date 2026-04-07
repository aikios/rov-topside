"""
Web dashboard server — serves HTML + WebSocket for browser-based ROV control UI.

Subscribes to all relevant ROS topics, pushes JSON state to connected
browsers at 10Hz. Camera preview sent as binary WebSocket frames.

Serves static files on HTTP :8080, WebSocket on :9090.
"""

import os
import json
import threading
import asyncio
from http.server import HTTPServer, SimpleHTTPRequestHandler
from functools import partial

import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, DurabilityPolicy
from sensor_msgs.msg import Joy, BatteryState, CompressedImage
from std_msgs.msg import Float64, Bool, String
from mavros_msgs.msg import State, OverrideRCIn, RCOut, VfrHud

try:
    import websockets
    HAS_WEBSOCKETS = True
except ImportError:
    HAS_WEBSOCKETS = False


STATIC_DIR = os.path.join(os.path.dirname(__file__), 'static')


class WebDashboardNode(Node):
    def __init__(self):
        super().__init__('web_dashboard')

        sensor_qos = QoSProfile(
            reliability=ReliabilityPolicy.BEST_EFFORT,
            durability=DurabilityPolicy.VOLATILE, depth=10)

        self.create_subscription(Joy, '/joy', self.joy_cb, 10)
        self.create_subscription(State, '/mavros/state', self.state_cb, 10)
        self.create_subscription(OverrideRCIn, '/mavros/mavros/override', self.override_cb, 10)
        self.create_subscription(BatteryState, '/mavros/battery', self.battery_cb, sensor_qos)
        self.create_subscription(VfrHud, '/mavros/vfr_hud', self.vfr_cb, sensor_qos)
        self.create_subscription(RCOut, '/mavros/mavros/out', self.servo_cb, 10)
        self.create_subscription(RCOut, '/mavros/mavros/out', self.servo_cb, sensor_qos)
        self.create_subscription(Float64, '/rov/depth_setpoint', self.depth_sp_cb, 10)
        self.create_subscription(Float64, '/rov/depth_current', self.depth_cur_cb, 10)
        self.create_subscription(Bool, '/rov/depth_hold_active', self.dh_cb, 10)
        self.create_subscription(String, '/rov/pid_status', self.pid_cb, 10)
        self.create_subscription(Bool, '/rov/fc_heartbeat', self.hb_cb, 10)
        self.create_subscription(CompressedImage, '/photogrammetry/preview', self.preview_cb, 1)
        self.create_subscription(CompressedImage, '/photogrammetry/image', self.capture_cb, 10)

        # State dict pushed to all WS clients
        self.state = {
            'fc_connected': False, 'armed': False, 'mode': '--',
            'battery_v': 0.0, 'depth': 0.0, 'heading': 0.0,
            'fc_heartbeat': False, 'depth_hold': False,
            'depth_setpoint': None, 'pid_status': 'MANUAL',
            'joy_axes': [0.0] * 8, 'cmd_channels': [1500] * 8,
            'servo_channels': [0] * 8,
            'capture_count': 0, 'capture_flash': False,
        }
        self.state_lock = threading.Lock()
        self.preview_jpeg = None
        self.preview_lock = threading.Lock()
        self.ws_clients = set()

        self.get_logger().info(f'Web dashboard: http://0.0.0.0:8080  ws://0.0.0.0:9090')

    # --- Callbacks ---
    def joy_cb(self, msg):
        with self.state_lock:
            self.state['joy_axes'] = [round(a, 3) for a in msg.axes[:8]]

    def state_cb(self, msg):
        with self.state_lock:
            self.state['fc_connected'] = msg.connected
            self.state['armed'] = msg.armed
            self.state['mode'] = msg.mode or '--'

    def override_cb(self, msg):
        with self.state_lock:
            self.state['cmd_channels'] = [int(c) for c in msg.channels[:8]]

    def battery_cb(self, msg):
        with self.state_lock:
            self.state['battery_v'] = round(msg.voltage, 2)

    def vfr_cb(self, msg):
        with self.state_lock:
            self.state['heading'] = round(msg.heading, 1)
            self.state['depth'] = round(-msg.altitude, 2)

    def servo_cb(self, msg):
        with self.state_lock:
            self.state['servo_channels'] = list(msg.channels[:8])

    def depth_sp_cb(self, msg):
        with self.state_lock:
            self.state['depth_setpoint'] = round(msg.data, 2)

    def depth_cur_cb(self, msg):
        with self.state_lock:
            self.state['depth'] = round(msg.data, 2)

    def dh_cb(self, msg):
        with self.state_lock:
            self.state['depth_hold'] = msg.data
            if not msg.data:
                self.state['depth_setpoint'] = None

    def pid_cb(self, msg):
        with self.state_lock:
            self.state['pid_status'] = msg.data

    def hb_cb(self, msg):
        with self.state_lock:
            self.state['fc_heartbeat'] = msg.data

    def preview_cb(self, msg):
        with self.preview_lock:
            self.preview_jpeg = bytes(msg.data)

    def capture_cb(self, msg):
        with self.state_lock:
            self.state['capture_count'] += 1
            self.state['capture_flash'] = True

    def get_state_json(self):
        with self.state_lock:
            data = json.dumps(self.state)
            # Reset flash after sending
            if self.state['capture_flash']:
                self.state['capture_flash'] = False
            return data

    def get_preview(self):
        with self.preview_lock:
            return self.preview_jpeg


async def ws_handler(node, websocket):
    """Handle a single WebSocket client."""
    node.ws_clients.add(websocket)
    node.get_logger().info(f'WS client connected ({len(node.ws_clients)} total)')
    last_frame = None
    try:
        while True:
            # Send state JSON
            await websocket.send(node.get_state_json())
            # Send camera frame if new
            frame = node.get_preview()
            if frame and frame is not last_frame:
                await websocket.send(frame)
                last_frame = frame
            await asyncio.sleep(0.1)  # 10Hz
    except websockets.exceptions.ConnectionClosed:
        pass
    finally:
        node.ws_clients.discard(websocket)
        node.get_logger().info(f'WS client disconnected ({len(node.ws_clients)} total)')


async def ws_server(node):
    """Run WebSocket server."""
    async with websockets.serve(partial(ws_handler, node), '0.0.0.0', 9090):
        await asyncio.Future()  # run forever


def run_http(static_dir):
    """Run static file HTTP server in a thread."""
    handler = partial(SimpleHTTPRequestHandler, directory=static_dir)
    httpd = HTTPServer(('0.0.0.0', 8080), handler)
    httpd.serve_forever()


def main(args=None):
    rclpy.init(args=args)
    node = WebDashboardNode()

    if not HAS_WEBSOCKETS:
        node.get_logger().error('websockets not installed! pip install websockets')
        return

    # HTTP server in background thread
    http_thread = threading.Thread(
        target=run_http, args=(STATIC_DIR,), daemon=True)
    http_thread.start()

    # ROS spin in background thread with multi-threaded executor
    from rclpy.executors import MultiThreadedExecutor
    executor = MultiThreadedExecutor()
    executor.add_node(node)
    spin_thread = threading.Thread(
        target=executor.spin, daemon=True)
    spin_thread.start()

    # WebSocket server in main thread (asyncio)
    asyncio.run(ws_server(node))

    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
