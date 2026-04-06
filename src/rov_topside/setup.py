import os
from glob import glob
from setuptools import find_packages, setup

package_name = 'rov_topside'

setup(
    name=package_name,
    version='0.2.0',
    packages=find_packages(exclude=['test']),
    package_data={package_name: ['web_dashboard/static/*']},
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        (os.path.join('share', package_name, 'launch'),
            glob('launch/*.launch.py')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='ahmad',
    maintainer_email='mahkgamer@gmail.com',
    description='ROV topside pilot station — image saving, joystick, display',
    license='MIT',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'photogrammetry_saver = rov_topside.photogrammetry_saver:main',
            'dashboard = rov_topside.dashboard:main',
            'joy_publisher = rov_topside.joy_publisher:main',
            'web_dashboard = rov_topside.web_dashboard.server:main',
        ],
    },
)
