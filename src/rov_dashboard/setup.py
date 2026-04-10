from setuptools import find_packages, setup

package_name = 'rov_dashboard'

setup(
    name=package_name,
    version='0.1.0',
    packages=find_packages(exclude=['test']),
    package_data={package_name: ['static/*']},
    include_package_data=True,
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
    ],
    install_requires=['setuptools'],
    zip_safe=False,
    maintainer='ahmad',
    maintainer_email='mahkgamer@gmail.com',
    description='Web-based dashboard server (HTTP + WebSocket) for ROV topside',
    license='MIT',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'server = rov_dashboard.server:main',
        ],
    },
)
