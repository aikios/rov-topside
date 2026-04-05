"""
ROV Topside Dashboard.

Real-time visualization of:
- DS4 joystick axes and buttons
- RC override channels being sent to ArduSub
- Servo/motor outputs from the FC
- FC state (armed, mode, battery, attitude)

Run alongside the other topside/onboard nodes.
"""

import tkinter as tk
from tkinter import ttk
import threading

import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, DurabilityPolicy
from sensor_msgs.msg import Joy, BatteryState
from std_msgs.msg import Float64, Bool, String
from mavros_msgs.msg import State, OverrideRCIn, RCOut, VfrHud


# Control output channel names (what we command)
RC_CHANNEL_NAMES = [
    'Surge', 'Sway', 'Heave', 'Yaw',
    '—', '—', 'Vert Ex 1', 'Vert Ex 2',
]

# DS4 axis names (mapped to ROV functions)
DS4_AXES = [
    'Lateral', 'Forward', 'L2',
    'Yaw', 'Vertical', 'R2',
    'D-Pad X', 'D-Pad Y',
]

DS4_BUTTONS = [
    'Cross', 'Circle', 'Triangle', 'Square',
    'L1', 'R1', 'L2', 'R2',
    'Share', 'Options', 'L3', 'R3', 'PS',
]


class DashboardNode(Node):
    def __init__(self):
        super().__init__('rov_dashboard')

        # QoS to match MAVROS (some topics use best-effort)
        sensor_qos = QoSProfile(
            reliability=ReliabilityPolicy.BEST_EFFORT,
            durability=DurabilityPolicy.VOLATILE,
            depth=10,
        )

        # Subscriptions
        self.create_subscription(Joy, '/joy', self.joy_cb, 10)
        self.create_subscription(State, '/mavros/state', self.state_cb, 10)
        self.create_subscription(OverrideRCIn, '/mavros/mavros/override', self.rc_override_cb, 10)
        self.create_subscription(BatteryState, '/mavros/battery', self.battery_cb, sensor_qos)
        self.create_subscription(VfrHud, '/mavros/vfr_hud', self.vfr_cb, sensor_qos)

        # Servo output from FC (multi-type topic, try both QoS profiles)
        self.create_subscription(RCOut, '/mavros/mavros/out', self.servo_out_cb, 10)
        self.create_subscription(RCOut, '/mavros/mavros/out', self.servo_out_cb, sensor_qos)

        # Depth hold topics
        self.create_subscription(Float64, '/rov/depth_setpoint', self.depth_sp_cb, 10)
        self.create_subscription(Float64, '/rov/depth_current', self.depth_cur_cb, 10)
        self.create_subscription(Bool, '/rov/depth_hold_active', self.depth_hold_cb, 10)
        self.create_subscription(String, '/rov/pid_status', self.pid_status_cb, 10)
        self.create_subscription(Bool, '/rov/fc_heartbeat', self.heartbeat_cb, 10)

        # Auto-tune trigger publisher
        self.autotune_pub = self.create_publisher(Bool, '/rov/autotune_trigger', 10)

        # State storage
        self.joy_axes = [0.0] * 8
        self.joy_buttons = [0] * 13
        self.rc_channels = [1500] * 8
        self.servo_channels = [0] * 8
        self.fc_connected = False
        self.fc_armed = False
        self.fc_mode = '—'
        self.battery_v = 0.0
        self.battery_pct = 0.0
        self.heading = 0.0
        self.depth = 0.0
        self.depth_setpoint = None
        self.depth_hold_active = False
        self.pid_status = 'MANUAL'
        self.fc_heartbeat = False
        self.hb_blink_state = False
        self.hb_blink_counter = 0
        self.servo_updated = False

        self.get_logger().info('Dashboard node started')

    def joy_cb(self, msg):
        self.joy_axes = list(msg.axes[:8]) + [0.0] * max(0, 8 - len(msg.axes))
        self.joy_buttons = list(msg.buttons[:13]) + [0] * max(0, 13 - len(msg.buttons))

    def state_cb(self, msg):
        self.fc_connected = msg.connected
        self.fc_armed = msg.armed
        self.fc_mode = msg.mode or '—'

    def rc_override_cb(self, msg):
        self.rc_channels = list(msg.channels[:8])

    def servo_out_cb(self, msg):
        self.servo_channels = list(msg.channels[:8]) + [0] * max(0, 8 - len(msg.channels))
        self.servo_updated = True

    def battery_cb(self, msg):
        self.battery_v = msg.voltage
        self.battery_pct = max(0.0, msg.percentage * 100)

    def vfr_cb(self, msg):
        self.heading = msg.heading
        self.depth = -msg.altitude  # positive down for ROV

    def depth_sp_cb(self, msg):
        self.depth_setpoint = msg.data

    def depth_cur_cb(self, msg):
        self.depth = msg.data

    def depth_hold_cb(self, msg):
        self.depth_hold_active = msg.data
        if not msg.data:
            self.depth_setpoint = None

    def pid_status_cb(self, msg):
        self.pid_status = msg.data

    def heartbeat_cb(self, msg):
        self.fc_heartbeat = msg.data


class Dashboard:
    def __init__(self, node):
        self.node = node
        self.root = tk.Tk()
        self.root.title('ROV Topside Dashboard')
        self.root.configure(bg='#1a1a2e')
        self.root.geometry('1100x700')

        style = ttk.Style()
        style.theme_use('clam')

        self._build_ui()
        self._schedule_update()

    def _build_ui(self):
        bg = '#1a1a2e'
        fg = '#e0e0e0'
        accent = '#0f3460'
        bar_bg = '#16213e'

        # Main grid: 3 columns
        self.root.columnconfigure(0, weight=1)
        self.root.columnconfigure(1, weight=1)
        self.root.columnconfigure(2, weight=1)
        self.root.rowconfigure(1, weight=1)

        # === Status Bar (top) ===
        status_frame = tk.Frame(self.root, bg=accent, padx=10, pady=8)
        status_frame.grid(row=0, column=0, columnspan=3, sticky='ew')

        # Heartbeat blinker
        self.hb_indicator = tk.Label(status_frame, text='\u2764', fg='#555', bg=accent,
                                     font=('monospace', 14, 'bold'))
        self.hb_indicator.pack(side='left', padx=(10, 5))

        self.status_labels = {}
        for i, key in enumerate(['FC', 'Armed', 'Mode', 'Battery', 'Heading', 'Depth']):
            lbl = tk.Label(status_frame, text=f'{key}: —', fg=fg, bg=accent,
                           font=('monospace', 11, 'bold'))
            lbl.pack(side='left', padx=15)
            self.status_labels[key] = lbl

        # === Column 0: Joystick ===
        joy_frame = tk.LabelFrame(self.root, text=' DS4 Joystick ', fg='#e94560',
                                  bg=bg, font=('monospace', 11, 'bold'), padx=5, pady=5)
        joy_frame.grid(row=1, column=0, sticky='nsew', padx=5, pady=5)

        self.axis_bars = {}
        for i, name in enumerate(DS4_AXES):
            row_frame = tk.Frame(joy_frame, bg=bg)
            row_frame.pack(fill='x', pady=1)
            tk.Label(row_frame, text=f'{name:>12}', fg=fg, bg=bg,
                     font=('monospace', 9), width=12, anchor='e').pack(side='left')
            canvas = tk.Canvas(row_frame, width=200, height=16, bg=bar_bg,
                               highlightthickness=0)
            canvas.pack(side='left', padx=5)
            val_lbl = tk.Label(row_frame, text=' 0.00', fg=fg, bg=bg,
                               font=('monospace', 9), width=6)
            val_lbl.pack(side='left')
            self.axis_bars[i] = (canvas, val_lbl)

        # Button indicators
        tk.Label(joy_frame, text='Buttons:', fg='#e94560', bg=bg,
                 font=('monospace', 10, 'bold')).pack(anchor='w', pady=(8, 2))
        self.btn_frame = tk.Frame(joy_frame, bg=bg)
        self.btn_frame.pack(fill='x')
        self.btn_indicators = {}
        for i, name in enumerate(DS4_BUTTONS):
            lbl = tk.Label(self.btn_frame, text=f' {name} ', fg='#555', bg='#222',
                           font=('monospace', 8), relief='raised', padx=2, pady=1)
            lbl.grid(row=i // 5, column=i % 5, padx=2, pady=1)
            self.btn_indicators[i] = lbl

        # === Column 1: RC Override ===
        rc_frame = tk.LabelFrame(self.root, text=' RC Override → FC ', fg='#e94560',
                                 bg=bg, font=('monospace', 11, 'bold'), padx=5, pady=5)
        rc_frame.grid(row=1, column=1, sticky='nsew', padx=5, pady=5)

        self.rc_bars = {}
        for i, name in enumerate(RC_CHANNEL_NAMES):
            row_frame = tk.Frame(rc_frame, bg=bg)
            row_frame.pack(fill='x', pady=2)
            tk.Label(row_frame, text=f'{name:>14}', fg=fg, bg=bg,
                     font=('monospace', 9), width=14, anchor='e').pack(side='left')
            canvas = tk.Canvas(row_frame, width=200, height=20, bg=bar_bg,
                               highlightthickness=0)
            canvas.pack(side='left', padx=5)
            val_lbl = tk.Label(row_frame, text='1500', fg=fg, bg=bg,
                               font=('monospace', 9, 'bold'), width=5)
            val_lbl.pack(side='left')
            self.rc_bars[i] = (canvas, val_lbl)

        # === Column 2: Servo Output ===
        servo_frame = tk.LabelFrame(self.root, text=' Servo Output (FC) ', fg='#e94560',
                                    bg=bg, font=('monospace', 11, 'bold'), padx=5, pady=5)
        servo_frame.grid(row=1, column=2, sticky='nsew', padx=5, pady=5)

        self.servo_bars = {}
        for i in range(8):
            row_frame = tk.Frame(servo_frame, bg=bg)
            row_frame.pack(fill='x', pady=2)
            tk.Label(row_frame, text=f'Motor {i+1:>2}', fg=fg, bg=bg,
                     font=('monospace', 9), width=14, anchor='e').pack(side='left')
            canvas = tk.Canvas(row_frame, width=200, height=20, bg=bar_bg,
                               highlightthickness=0)
            canvas.pack(side='left', padx=5)
            val_lbl = tk.Label(row_frame, text='—', fg=fg, bg=bg,
                               font=('monospace', 9, 'bold'), width=5)
            val_lbl.pack(side='left')
            self.servo_bars[i] = (canvas, val_lbl)

        self.servo_status = tk.Label(servo_frame, text='Waiting for servo data...',
                                     fg='#888', bg=bg, font=('monospace', 9))
        self.servo_status.pack(pady=5)

        # Depth hold section
        dh_frame = tk.LabelFrame(servo_frame, text=' Depth Hold ', fg='#e94560',
                                 bg=bg, font=('monospace', 10, 'bold'), padx=5, pady=5)
        dh_frame.pack(fill='x', pady=(10, 0))

        self.dh_status_lbl = tk.Label(dh_frame, text='MANUAL', fg='#888', bg=bg,
                                      font=('monospace', 11, 'bold'))
        self.dh_status_lbl.pack()

        self.dh_depth_lbl = tk.Label(dh_frame, text='Depth: —  Setpoint: —',
                                     fg=fg, bg=bg, font=('monospace', 9))
        self.dh_depth_lbl.pack()

        self.dh_pid_lbl = tk.Label(dh_frame, text='PID: —', fg='#888', bg=bg,
                                   font=('monospace', 9))
        self.dh_pid_lbl.pack()

        self.autotune_btn = tk.Button(
            dh_frame, text='Auto-Tune PID', fg='#fff', bg='#0f3460',
            font=('monospace', 9, 'bold'), padx=10, pady=3,
            command=self._trigger_autotune)
        self.autotune_btn.pack(pady=5)

    def _draw_axis_bar(self, canvas, value):
        """Draw a centered bar for -1.0..1.0 axis value."""
        canvas.delete('all')
        w = canvas.winfo_width() or 200
        h = canvas.winfo_height() or 16
        center = w // 2

        # Center line
        canvas.create_line(center, 0, center, h, fill='#444', width=1)

        # Bar
        bar_len = int(value * (w // 2 - 2))
        color = '#4ecca3' if value >= 0 else '#e94560'
        if abs(bar_len) > 1:
            x1 = center
            x2 = center + bar_len
            canvas.create_rectangle(min(x1, x2), 2, max(x1, x2), h - 2,
                                    fill=color, outline='')

    def _draw_pwm_bar(self, canvas, pwm, min_v=1100, max_v=1900):
        """Draw a bar for PWM value (1100-1900, center at 1500)."""
        canvas.delete('all')
        w = canvas.winfo_width() or 200
        h = canvas.winfo_height() or 20
        center = w // 2

        # Center line
        canvas.create_line(center, 0, center, h, fill='#444', width=1)

        if pwm == 0 or pwm == 65535:
            return

        # Normalize to -1..1
        norm = (pwm - 1500) / 400.0
        norm = max(-1.0, min(1.0, norm))
        bar_len = int(norm * (w // 2 - 2))

        color = '#4ecca3' if norm >= 0 else '#e94560'
        if abs(bar_len) > 1:
            x1 = center
            x2 = center + bar_len
            canvas.create_rectangle(min(x1, x2), 2, max(x1, x2), h - 2,
                                    fill=color, outline='')

    def _trigger_autotune(self):
        msg = Bool()
        msg.data = True
        self.node.autotune_pub.publish(msg)

    def _schedule_update(self):
        self._update_display()
        self.root.after(50, self._schedule_update)  # 20 Hz

    def _update_display(self):
        n = self.node

        # Status bar
        # Heartbeat blinker
        if n.fc_connected and n.fc_heartbeat:
            n.hb_blink_counter = (n.hb_blink_counter + 1) % 10  # blink every 10 frames (~0.5s)
            if n.hb_blink_counter < 5:
                self.hb_indicator.config(fg='#e94560')  # red heart visible
            else:
                self.hb_indicator.config(fg='#4ecca3')  # green heart
            fc_text = 'FC: CONNECTED'
            fc_color = '#4ecca3'
        elif n.fc_connected:
            self.hb_indicator.config(fg='#555')
            fc_text = 'FC: CONNECTED [no HB]'
            fc_color = '#e9a560'
        else:
            self.hb_indicator.config(fg='#333')
            fc_text = 'FC: DISCONNECTED'
            fc_color = '#e94560'
        self.status_labels['FC'].config(text=fc_text, fg=fc_color)

        arm_color = '#e94560' if n.fc_armed else '#888'
        self.status_labels['Armed'].config(
            text=f'Armed: {"YES" if n.fc_armed else "NO"}', fg=arm_color)

        self.status_labels['Mode'].config(text=f'Mode: {n.fc_mode}')
        self.status_labels['Battery'].config(
            text=f'Batt: {n.battery_v:.1f}V ({n.battery_pct:.0f}%)')
        self.status_labels['Heading'].config(text=f'Hdg: {n.heading:.0f}\u00b0')
        if n.depth_setpoint is not None:
            self.status_labels['Depth'].config(
                text=f'Depth: {n.depth:.1f}m [DH: {n.depth_setpoint:.1f}m]',
                fg='#4ecca3')
        else:
            self.status_labels['Depth'].config(text=f'Depth: {n.depth:.1f}m')

        # Joystick axes
        for i in range(min(8, len(n.joy_axes))):
            if i in self.axis_bars:
                canvas, lbl = self.axis_bars[i]
                val = n.joy_axes[i]
                self._draw_axis_bar(canvas, val)
                lbl.config(text=f'{val:+.2f}')

        # Joystick buttons
        for i in range(min(13, len(n.joy_buttons))):
            if i in self.btn_indicators:
                pressed = n.joy_buttons[i]
                self.btn_indicators[i].config(
                    bg='#e94560' if pressed else '#222',
                    fg='#fff' if pressed else '#555'
                )

        # RC Override channels
        for i in range(8):
            if i in self.rc_bars:
                canvas, lbl = self.rc_bars[i]
                pwm = n.rc_channels[i] if i < len(n.rc_channels) else 1500
                self._draw_pwm_bar(canvas, pwm)
                lbl.config(text=f'{pwm}')

        # Servo outputs
        for i in range(8):
            if i in self.servo_bars:
                canvas, lbl = self.servo_bars[i]
                pwm = n.servo_channels[i] if i < len(n.servo_channels) else 0
                self._draw_pwm_bar(canvas, pwm)
                # Always show value, color-code deviation from center
                if pwm > 0:
                    delta = pwm - 1500
                    if abs(delta) > 5:
                        color = '#4ecca3' if delta > 0 else '#e94560'
                        lbl.config(text=f'{pwm}', fg=color)
                    else:
                        lbl.config(text=f'{pwm}', fg='#e0e0e0')
                else:
                    lbl.config(text='—', fg='#555')

        if n.servo_updated:
            self.servo_status.config(text='LIVE', fg='#4ecca3')
        elif n.fc_connected:
            self.servo_status.config(text='Waiting (arm to see outputs)', fg='#888')
        else:
            self.servo_status.config(text='No FC', fg='#e94560')

        # Depth hold display
        if n.depth_hold_active:
            if 'TUNING' in n.pid_status:
                self.dh_status_lbl.config(text=n.pid_status, fg='#e9a560')
            else:
                self.dh_status_lbl.config(text='DEPTH HOLD', fg='#4ecca3')
            sp_str = f'{n.depth_setpoint:.2f}m' if n.depth_setpoint is not None else '—'
            self.dh_depth_lbl.config(
                text=f'Depth: {n.depth:.2f}m  Setpoint: {sp_str}')
        else:
            self.dh_status_lbl.config(text='MANUAL', fg='#888')
            self.dh_depth_lbl.config(text=f'Depth: {n.depth:.2f}m')
        self.dh_pid_lbl.config(text=n.pid_status, fg='#aaa')

    def run(self):
        self.root.mainloop()


def main(args=None):
    rclpy.init(args=args)
    node = DashboardNode()

    # Spin ROS in a background thread
    spin_thread = threading.Thread(target=rclpy.spin, args=(node,), daemon=True)
    spin_thread.start()

    # Run tkinter in the main thread
    dashboard = Dashboard(node)
    try:
        dashboard.run()
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
