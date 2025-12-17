"""Test server tools prompts for ROS MCP Server."""


def register_test_server_tools_prompts(mcp):
    """Register test server tools prompts with the MCP server."""

    @mcp.prompt(name="test-server-tools")
    def test_server_tools() -> str:
        """
        Guide users on how to test and explore the ROS MCP server tools.

        This prompt provides step-by-step instructions for testing the server,
        including how to access capabilities information, test tools, and verify connections.

        Returns:
            str: Comprehensive guide for testing server tools
        """
        return """# Testing ROS MCP Server - Quick Start Guide

This is a high-level overview guide for testing the ROS MCP Server. For detailed testing instructions and troubleshooting, see the category-specific guides listed at the end.

## Prerequisites

Before testing, ensure you have:
1. **Turtlesim running**: `ros2 run turtlesim turtlesim_node` (ROS 2) or `rosrun turtlesim turtlesim_node` (ROS 1)
2. **Rosbridge running**: `ros2 run rosbridge_server rosbridge_websocket` (ROS 2) or `rosrun rosbridge_server rosbridge_websocket` (ROS 1)

## Quick Test Workflow

### 1. Connect and Discover

```python
# Connect
connect_to_robot(ip='127.0.0.1', port=9090)
detect_ros_version()

# Discover what's available
get_topics()      # Lists all topics
get_services()    # Lists all services
get_nodes()       # Lists all nodes
get_actions()     # Lists all actions (ROS 2 only)
```

### 2. Test Main Tools by Category

**Topics** - Subscribe and publish:
```python
subscribe_once(topic='/turtle1/pose', msg_type='turtlesim/msg/Pose')
publish_once(topic='/turtle1/cmd_vel', msg_type='geometry_msgs/msg/Twist', 
             msg={'linear': {'x': 2.0, 'y': 0.0, 'z': 0.0}})
```

**Services** - Call services:
```python
call_service(service_name='/turtle1/teleport_absolute', 
             service_type='turtlesim/srv/TeleportAbsolute', 
             request={'x': 5.5, 'y': 5.5, 'theta': 0.0})
```

**Nodes** - Inspect nodes:
```python
get_node_details('/turtlesim')
```

**Parameters** (ROS 2 only) - Get and set parameters:
```python
get_parameters('turtlesim')
set_parameter('/turtlesim:background_r', '255')
```

**Actions** (ROS 2 only) - Send goals:
```python
send_action_goal(action_name='/turtle1/rotate_absolute', 
                 action_type='turtlesim/action/RotateAbsolute', 
                 goal={'theta': 1.57})
```

## Main Tools by Category

### Connection Tools
- `connect_to_robot()` - Connect to ROS system
- `ping_robot()` - Test connectivity
- `detect_ros_version()` - Detect ROS version

### Discovery Tools
- `get_topics()` - List all topics
- `get_services()` - List all services
- `get_nodes()` - List all nodes
- `get_actions()` - List all actions (ROS 2)

### Topic Tools
- `get_topic_details()` - Get topic information
- `subscribe_once()` - Subscribe and get one message
- `publish_once()` - Publish a message

### Service Tools
- `get_service_details()` - Get service information
- `call_service()` - Call a service

### Node Tools
- `get_node_details()` - Get node information

### Parameter Tools (ROS 2)
- `get_parameters()` - List parameters for a node
- `get_parameter()` - Get a parameter value
- `set_parameter()` - Set a parameter value

### Action Tools (ROS 2)
- `get_action_details()` - Get action information
- `send_action_goal()` - Send an action goal
- `get_action_status()` - Get action status

## Resources

Access comprehensive information via resources:
- `ros-mcp://ros-metadata/all` - All ROS metadata
- `ros-mcp://ros-metadata/topics/all` - All topics details
- `ros-mcp://ros-metadata/services/all` - All services details
- `ros-mcp://ros-metadata/nodes/all` - All nodes details
- `ros-mcp://ros-metadata/actions/all` - All actions details (ROS 2)
- `ros-mcp://ros-metadata/parameters/all` - All parameters details (ROS 2)

## Quick Testing Checklist

- [ ] Connect: `connect_to_robot()`, `detect_ros_version()`
- [ ] Discover: `get_topics()`, `get_services()`, `get_nodes()`, `get_actions()`
- [ ] Topics: `subscribe_once()`, `publish_once()`
- [ ] Services: `call_service()`
- [ ] Nodes: `get_node_details()`
- [ ] Parameters: `get_parameters()`, `set_parameter()` (ROS 2)
- [ ] Actions: `send_action_goal()`, `get_action_status()` (ROS 2)

## If Something Fails

If the main tools above don't work, refer to the detailed category-specific guides for troubleshooting:

- **Connection issues?** → See `test-connection-tools` for detailed connection troubleshooting
- **Topic tools not working?** → See `test-topics-tools` for detailed topic testing and troubleshooting
- **Service tools not working?** → See `test-services-tools` for detailed service testing and troubleshooting
- **Node tools not working?** → See `test-nodes-tools` for detailed node testing and troubleshooting
- **Parameter tools not working?** → See `test-parameters-tools` for detailed parameter testing and troubleshooting (ROS 2)
- **Action tools not working?** → See `test-actions-tools` for detailed action testing and troubleshooting (ROS 2)

## Tips

- Most tools work with both ROS 1 and ROS 2
- Parameters and Actions are ROS 2 only
- Turtlesim is a great example for testing all tool categories
- Use resources for comprehensive system overview
- Individual test guides provide detailed troubleshooting steps

## Category-Specific Test Guides

For detailed testing instructions, troubleshooting, and advanced usage:

- **`test-connection-tools`** - Detailed connection tool testing
- **`test-topics-tools`** - Detailed topic tool testing
- **`test-services-tools`** - Detailed service tool testing
- **`test-nodes-tools`** - Detailed node tool testing
- **`test-parameters-tools`** - Detailed parameter tool testing (ROS 2)
- **`test-actions-tools`** - Detailed action tool testing (ROS 2)
"""
