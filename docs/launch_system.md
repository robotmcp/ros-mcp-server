# ROS2 Launch System

## Overview

The ROS-MCP Server uses proper ROS2 launch files for process management.

## Available Launch Files

### `ros_mcp_rosbridge.launch.py`
**Purpose**: Launch only Rosbridge WebSocket server
**Use Case**: External robots, custom setups, testing

```bash
# Basic usage
ros2 launch ros_mcp_rosbridge.launch.py

# Custom port
ros2 launch ros_mcp_rosbridge.launch.py port:=9091

# Specific address
ros2 launch ros_mcp_rosbridge.launch.py address:=127.0.0.1
```

## Benefits

- ✅ **Proper process management** - Automatic cleanup on shutdown
- ✅ **Configuration options** - Parameter passing and validation
- ✅ **ROS2 integration** - Works with `ros2 launch` command
- ✅ **Logging control** - Configurable log levels
- ✅ **Signal handling** - Proper SIGINT/SIGTERM handling

## Common Arguments

| Argument | Default | Description |
|----------|---------|-------------|
| `port` | 9090 | WebSocket server port |
| `address` | "" | Bind address (empty = all interfaces) |
| `log_level` | info | Log level (debug, info, warn, error) |

## Examples

### External Robot Connection
```bash
# Start rosbridge for external robot
ros2 launch ros_mcp_server ros_mcp_rosbridge.launch.py port:=9090

# Connect MCP server to robot IP
# (Configure in MCP client settings)
```

### Debug Mode
```bash
# Enable debug logging
ros2 launch ros_mcp_server ros_mcp_rosbridge.launch.py log_level:=debug
```

## Troubleshooting

### Port Already in Use
```bash
# Check port usage
netstat -tulpn | grep :9090

# Use different port
ros2 launch ros_mcp_server ros_mcp_rosbridge.launch.py port:=9091
```

### Missing Dependencies
```bash
# Install required packages
sudo apt install ros-jazzy-rosbridge-server
```

### Check Node Status
```bash
# List running nodes
ros2 node list

# Check topics
ros2 topic list
```