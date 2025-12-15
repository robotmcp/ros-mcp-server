#!/usr/bin/env python3

"""
ROS2 Launch file for Turtlesim with Rosbridge WebSocket Server
Launches both turtlesim node and rosbridge server for MCP integration.
"""

from launch.actions import DeclareLaunchArgument, LogInfo
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node

from launch import LaunchDescription


def generate_launch_description():
    """Generate the launch description for turtlesim with rosbridge."""

    # Declare launch arguments
    port_arg = DeclareLaunchArgument(
        "port", default_value="9090", description="Port for rosbridge websocket server"
    )

    address_arg = DeclareLaunchArgument(
        "address",
        default_value="",
        description="Address for rosbridge websocket server (empty for all interfaces)",
    )

    log_level_arg = DeclareLaunchArgument(
        "log_level", default_value="info", description="Log level for nodes"
    )

    # Turtlesim node
    turtlesim_node = Node(
        package="turtlesim",
        executable="turtlesim_node",
        name="turtlesim",
        output="screen",
        arguments=["--ros-args", "--log-level", LaunchConfiguration("log_level")],
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
                "default_call_service_timeout": 5.0,
            }
        ],
        arguments=["--ros-args", "--log-level", LaunchConfiguration("log_level")],
    )

    # ROS API node (needed for some rosbridge operations)
    rosapi_node = Node(
        package="rosapi",
        executable="rosapi_node",
        name="rosapi",
        output="screen",
        arguments=["--ros-args", "--log-level", LaunchConfiguration("log_level")],
    )

    # Log info
    log_info = LogInfo(
        msg=[
            "Starting Turtlesim with Rosbridge WebSocket Server:",
            "  - Port: ",
            LaunchConfiguration("port"),
            "  - Log level: ",
            LaunchConfiguration("log_level"),
        ]
    )

    return LaunchDescription(
        [
            port_arg,
            address_arg,
            log_level_arg,
            log_info,
            rosbridge_node,
            rosapi_node,
            turtlesim_node,
        ]
    )
