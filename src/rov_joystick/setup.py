from setuptools import find_packages, setup

package_name = 'rov_joystick'

setup(
    name=package_name,
    version='0.1.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='ahmad',
    maintainer_email='mahkgamer@gmail.com',
    description='DS4 joystick publisher (evdev-based) for ROV topside',
    license='MIT',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'joy_publisher = rov_joystick.joy_publisher:main',
        ],
    },
)
