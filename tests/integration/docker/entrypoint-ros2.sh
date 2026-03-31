#!/bin/bash
set -e
source /opt/ros/${ROS_DISTRO}/setup.bash
exec ros2 launch /ros2_ws/ros2_launch.py
