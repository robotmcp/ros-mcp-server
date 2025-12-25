from setuptools import find_packages, setup

package_name = 'go2_control'

setup(
    name=package_name,
    version='1.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='Bharat Jain',
    maintainer_email='bharat.jain@plaksha.edu.in',
    description='ROS 2 control node for Unitree Go2 quadruped robot',
    license='MIT',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'go2_services = go2_control.go2_service_node:main',
        ],
    },
)
