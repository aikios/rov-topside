"""
Photogrammetry image saver node.

Runs on topside. Subscribes to /photogrammetry/image from the onboard Pi 5
and saves full-resolution images to disk for photogrammetry processing.
"""

import os
from datetime import datetime

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import CompressedImage


class PhotogrammetrySaver(Node):
    def __init__(self):
        super().__init__('photogrammetry_saver')

        self.declare_parameter('save_dir', os.path.expanduser('~/rov_captures'))

        self.save_dir = self.get_parameter('save_dir').value
        os.makedirs(self.save_dir, exist_ok=True)

        self.subscription = self.create_subscription(
            CompressedImage,
            '/photogrammetry/image',
            self.image_callback,
            10,
        )

        self.save_count = 0
        self.get_logger().info(f'Photogrammetry saver ready. Saving to: {self.save_dir}')

    def image_callback(self, msg):
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
        filename = f'photogrammetry_{timestamp}.jpg'
        filepath = os.path.join(self.save_dir, filename)

        with open(filepath, 'wb') as f:
            f.write(bytes(msg.data))

        self.save_count += 1
        size_kb = len(msg.data) / 1024
        self.get_logger().info(
            f'Saved #{self.save_count}: {filename} ({size_kb:.0f} KB)'
        )


def main(args=None):
    rclpy.init(args=args)
    node = PhotogrammetrySaver()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
