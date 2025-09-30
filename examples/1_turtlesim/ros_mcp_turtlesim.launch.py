#!/usr/bin/env python3

"""
ROS2 Launch file for ROS-MCP Server
Replaces the functionality of scripts/launch_ros.sh with proper ROS2 launch system.

This launch file starts:
- rosbridge_websocket server
- turtlesim node
- Provides proper process management and cleanup
"""

from launch.actions import DeclareLaunchArgument, LogInfo
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node

from launch import LaunchDescription


def generate_launch_description():
    """Generate the launch description for ROS-MCP Server."""

    # Declare launch arguments
    rosbridge_port_arg = DeclareLaunchArgument(
        "port", default_value="9090", description="Port for rosbridge websocket server"
    )

    rosbridge_address_arg = DeclareLaunchArgument(
        "address",
        default_value="",
        description="Address for rosbridge websocket server (empty for all interfaces)",
    )

    turtlesim_name_arg = DeclareLaunchArgument(
        "turtlesim_name", default_value="turtlesim", description="Name for the turtlesim node"
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

    # Turtlesim node
    turtlesim_node = Node(
        package="turtlesim",
        executable="turtlesim_node",
        name=LaunchConfiguration("turtlesim_name"),
        output="screen",
        arguments=["--ros-args", "--log-level", "info"],
    )

    # Log info about what's being launched
    log_info = LogInfo(
        msg=[
            "Starting ROS-MCP Server with:",
            "  - Rosbridge WebSocket on port: ",
            LaunchConfiguration("port"),
            "  - Turtlesim node: ",
            LaunchConfiguration("turtlesim_name"),
        ]
    )

    return LaunchDescription(
        [
            rosbridge_port_arg,
            rosbridge_address_arg,
            turtlesim_name_arg,
            log_info,
            rosbridge_node,
            turtlesim_node,
        ]
    )
