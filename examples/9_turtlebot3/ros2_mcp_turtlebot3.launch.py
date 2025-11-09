#!/usr/bin/env python3

"""
ROS2 Launch file for ROS-MCP Server with TurtleBot3
This launch file starts:
- rosbridge_websocket server
- TurtleBot3 robot
- Provides proper process management and cleanup
"""

import os

from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, LogInfo
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare

from launch import LaunchDescription


def generate_launch_description():
    """Generate the launch description for ROS-MCP Server with TurtleBot3."""

    # Declare launch arguments
    rosbridge_port_arg = DeclareLaunchArgument(
        "port", default_value="9090", description="Port for rosbridge websocket server"
    )

    rosbridge_address_arg = DeclareLaunchArgument(
        "address",
        default_value="",
        description="Address for rosbridge websocket server (empty for all interfaces)",
    )

    # Rosbridge websocket server node
    rosbridge_node = Node(
        package="rosbridge_server",
        executable="rosbridge_websocket",
        name="rosbridge_websocket",
        output="screen",
        parameters=[
            {
                "port": LaunchConfiguration("port"),
                "address": LaunchConfiguration("address"),
                "use_compression": False,
                "max_message_size": 10000000,
                "send_action_goals_in_new_thread": True,
                "call_services_in_new_thread": True,
            }
        ],
        arguments=["--ros-args", "--log-level", "info"],
    )

    # Include TurtleBot3 bringup launch file
    turtlebot3_bringup_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            [
                os.path.join(
                    FindPackageShare("turtlebot3_bringup").find("turtlebot3_bringup"),
                    "launch",
                    "robot.launch.py",
                )
            ]
        )
    )

    # Log info about what's being launched
    log_info = LogInfo(
        msg=[
            "Starting ROS-MCP Server with:",
            "  - Rosbridge WebSocket on port: ",
            LaunchConfiguration("port"),
            "  - TurtleBot3 robot bringup",
        ]
    )

    return LaunchDescription(
        [
            rosbridge_port_arg,
            rosbridge_address_arg,
            log_info,
            rosbridge_node,
            turtlebot3_bringup_launch,
        ]
    )
