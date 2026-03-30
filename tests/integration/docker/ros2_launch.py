"""ROS2 launch file for integration tests: rosbridge + turtlesim + rosapi."""

from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node

from launch import LaunchDescription


def generate_launch_description():
    return LaunchDescription(
        [
            DeclareLaunchArgument("port", default_value="9090"),
            DeclareLaunchArgument("address", default_value=""),
            Node(
                package="turtlesim",
                executable="turtlesim_node",
                name="turtlesim",
                output="screen",
            ),
            Node(
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
                        "unregister_timeout": 10.0,
                        "service_timeout": 5,
                        "send_action_goals_in_new_thread": True,
                        "call_services_in_new_thread": True,
                    }
                ],
            ),
            Node(
                package="rosapi",
                executable="rosapi_node",
                name="rosapi",
                output="screen",
            ),
        ]
    )
