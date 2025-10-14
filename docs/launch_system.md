# ROS2 Launch System for Robot Integration

## Overview

This guide provides template launch files for developers to integrate their robots with the ROS-MCP Server. These templates demonstrate how to combine your robot's existing launch files with rosbridge for MCP communication.

## Template Launch Files

### `ros_mcp_rosbridge.launch.py` - Basic Rosbridge Template
**Purpose**: Minimal rosbridge WebSocket server for robot integration
**Use Case**: Add MCP communication to any existing robot setup

```bash
# Basic usage
ros2 launch ros_mcp_rosbridge.launch.py

# Custom port
ros2 launch ros_mcp_rosbridge.launch.py port:=9090

# Specific address
ros2 launch ros_mcp_rosbridge.launch.py address:=127.0.0.1
```

## Integration Patterns

### How to add Rosbridge to Existing Robot

#### Method 1: Include Rosbridge Launch File
```python
# Your existing robot launch file (e.g., my_robot.launch.py)
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch_ros.actions import Node

def generate_launch_description():
    # Your existing robot nodes
    robot_node = Node(
        package='my_robot_pkg',
        executable='robot_node',
        name='my_robot'
    )
    
    sensor_node = Node(
        package='my_robot_pkg',
        executable='sensor_node',
        name='sensor_node'
    )
    
    # Include rosbridge for MCP communication
    rosbridge_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource([
            'ros_mcp_server', '/launch/ros_mcp_rosbridge.launch.py'
        ]),
        launch_arguments={
            'port': '9090',
            'address': '',
            'log_level': 'info'
        }.items()
    )
    
    return LaunchDescription([
        robot_node,
        sensor_node,
        rosbridge_launch,  # Add this line
    ])
```

#### Method 2: Add Rosbridge Node Directly

```python
# Add rosbridge node to your existing launch file
from launch.actions import DeclareLaunchArgument, LogInfo
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node

from launch import LaunchDescription


def generate_launch_description():
    """Generate the launch description for rosbridge only."""

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
        "log_level", default_value="info", description="Log level for rosbridge server"
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

    return LaunchDescription(
        [
            port_arg,
            address_arg,
            log_level_arg,
            rosbridge_node,
        ]
    )
```


#### Method 3: Separate Launch Files (Recommended)
```bash
# Terminal 1: Launch your robot
ros2 launch my_robot_pkg my_robot.launch.py

# Terminal 2: Launch rosbridge for MCP
ros2 launch ros_mcp_server ros_mcp_rosbridge.launch.py port:=9090
```

| Argument | Default | Description |
|----------|---------|-------------|
| `port` | 9090 | WebSocket server port |
| `address` | "" | Bind address (empty = all interfaces) |
| `log_level` | info | Log level (debug, info, warn, error) |