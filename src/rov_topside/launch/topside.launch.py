from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    # Saves photogrammetry images arriving from onboard
    photogrammetry_saver = Node(
        package='rov_topside',
        executable='photogrammetry_saver',
        name='photogrammetry_saver',
        parameters=[{
            'save_dir': '/home/ahmad/rov_captures',
        }],
        output='screen',
    )

    return LaunchDescription([
        photogrammetry_saver,
    ])
