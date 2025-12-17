"""Test connection tools prompts for ROS MCP Server."""


def register_test_connection_tools_prompts(mcp):
    """Register test connection tools prompts with the MCP server."""

    @mcp.prompt(name="test-connection-tools")
    def test_connection_tools() -> str:
        """
        Guide users on how to test and explore the ROS connection tools.

        This prompt provides step-by-step instructions for testing connection operations,
        including connecting to robots, pinging robots, and detecting ROS versions.

        Returns:
            str: Comprehensive guide for testing connection tools
        """
        return """# Testing ROS Connection Tools - Detailed Guide

This is a detailed guide for testing connection tools. For a quick overview of all ROS MCP Server tools, see `test-server-tools`.

## When to Use This Guide

Use this detailed guide when:
- The main connection tools from `test-server-tools` are not working
- You need step-by-step instructions for each connection tool
- You need troubleshooting help for specific connection issues
- You want to understand connection tool details and advanced usage
- You're having network or connectivity problems

For a quick high-level overview, see `test-server-tools`.

## Prerequisites

Before testing connection tools, ensure you have:

1. **Network access** to the robot or ROS system
2. **Rosbridge server** running on the target system (typically on port 9090)
3. **IP address and port** of the rosbridge server

## Connection Tools Overview

The ROS MCP Server provides the following connection tools:

1. **connect_to_robot** - Connect to a robot by setting IP/port and test connectivity
2. **ping_robot** - Ping a robot's IP address and check if a specific port is open
3. **detect_ros_version** - Detect the ROS version and distribution via rosbridge

## Step 1: Ping a Robot (Test Connectivity)

Before connecting, you can test if a robot is reachable and if the rosbridge port is open:

```
ping_robot(ip='192.168.1.100', port=9090)
```

This will:
- Ping the IP address to check if the host is reachable
- Check if the specified port is open
- Return connectivity status

**Example:**
```
ping_robot(ip='127.0.0.1', port=9090)
ping_robot(ip='192.168.1.50', port=9090, ping_timeout=2.0, port_timeout=2.0)
```

**Parameters:**
- `ip` (required): The IP address of the robot/rosbridge server
- `port` (required): The port number (typically 9090 for rosbridge)
- `ping_timeout` (optional): Timeout for ping in seconds (default: 2.0)
- `port_timeout` (optional): Timeout for port check in seconds (default: 2.0)

**Response:**
The response includes:
- `ping_successful`: Whether the IP address is reachable
- `port_open`: Whether the port is open
- `message`: Status message

**Note:** A successful ping to the IP but not the port can indicate that rosbridge is not running.

## Step 2: Connect to a Robot

Connect to a robot by setting the IP and port for the WebSocket connection:

```
connect_to_robot(ip='192.168.1.100', port=9090)
```

This will:
- Set the WebSocket connection IP and port
- Test connectivity (ping and port check)
- Return connection status

**Example:**
```
connect_to_robot(ip='127.0.0.1', port=9090)
connect_to_robot(ip='192.168.1.50', port=9090, ping_timeout=3.0, port_timeout=3.0)
```

**Parameters:**
- `ip` (optional): The IP address (default: 127.0.0.1)
- `port` (optional): The port number (default: 9090)
- `ping_timeout` (optional): Timeout for ping in seconds (default: 2.0)
- `port_timeout` (optional): Timeout for port check in seconds (default: 2.0)

**Response:**
The response includes:
- `message`: Confirmation message with IP and port
- `connectivity_test`: Results of ping and port checks

## Step 3: Detect ROS Version

After connecting, detect the ROS version and distribution:

```
detect_ros_version()
```

This will:
- Attempt to detect ROS 1 or ROS 2
- Return the version number and distribution name
- Work via rosbridge WebSocket connection

**Example:**
```
detect_ros_version()
```

**Response:**
The response includes:
- `version`: ROS version (1 or 2)
- `distro`: Distribution name (e.g., "humble", "noetic", "melodic")

**Note:** This tool requires an active rosbridge connection. Make sure you've connected first using `connect_to_robot()`.

## Common Connection Scenarios

### Scenario 1: Connect to Local ROS System

For testing with a local ROS system (rosbridge running on the same machine):

```
connect_to_robot(ip='127.0.0.1', port=9090)
detect_ros_version()
```

### Scenario 2: Connect to Remote Robot

For connecting to a robot on the network:

```
# First, test connectivity
ping_robot(ip='192.168.1.100', port=9090)

# If successful, connect
connect_to_robot(ip='192.168.1.100', port=9090)

# Verify ROS version
detect_ros_version()
```

### Scenario 3: Connect with Custom Port

If rosbridge is running on a non-standard port:

```
connect_to_robot(ip='192.168.1.100', port=9091)
ping_robot(ip='192.168.1.100', port=9091)
```


## Troubleshooting

### Connection Timeout Errors

**Problem:** `ping_robot()` or `connect_to_robot()` times out

**Solutions:**
- Verify the IP address is correct
- Check if the robot is on the same network
- Ensure rosbridge is running on the target system
- Try increasing timeout values: `ping_timeout=5.0, port_timeout=5.0`
- Check firewall settings that might block the port

### Port Not Open

**Problem:** Ping succeeds but port check fails

**Solutions:**
- Verify rosbridge is running: `rosrun rosbridge_server rosbridge_websocket` (ROS 1) or `ros2 run rosbridge_server rosbridge_websocket` (ROS 2)
- Check if rosbridge is listening on the correct port
- Verify no firewall is blocking the port
- Check rosbridge configuration for port settings

### Cannot Detect ROS Version

**Problem:** `detect_ros_version()` fails or returns error

**Solutions:**
- Ensure you've connected first using `connect_to_robot()`
- Verify rosbridge connection is active
- Check that rosbridge is properly configured
- Try reconnecting: `connect_to_robot()` again

### IP Address Not Reachable

**Problem:** Ping fails for the IP address

**Solutions:**
- Verify the IP address is correct
- Check network connectivity (can you ping from terminal?)
- Ensure the robot is powered on and connected to network
- Check network configuration (subnet, gateway, etc.)
- Try using hostname instead of IP if DNS is configured

## Tips

- Always use `ping_robot()` first to test connectivity before connecting
- The default port for rosbridge is 9090, but it can be configured differently
- Connection settings persist until you call `connect_to_robot()` again
- Use `detect_ros_version()` after connecting to verify the connection works
- For local testing, use `127.0.0.1` or `localhost`
- For remote robots, ensure both systems are on the same network or VPN

## Related Guides

- **`test-server-tools`** - High-level overview of all ROS MCP Server tools
"""
