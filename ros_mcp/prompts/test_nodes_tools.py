"""Test node tools prompts for ROS MCP Server."""


def register_test_nodes_tools_prompts(mcp):
    """Register test node tools prompts with the MCP server."""

    @mcp.prompt(name="test-nodes-tools")
    def test_nodes_tools() -> str:
        """
        Guide users on how to test and explore the ROS node tools.

        This prompt provides step-by-step instructions for testing node operations,
        including getting node lists, node details, and comprehensive node inspection.

        Returns:
            str: Comprehensive guide for testing node tools
        """
        return """# Testing ROS Node Tools - Detailed Guide

This is a detailed guide for testing node tools. For a quick overview of all ROS MCP Server tools, see `test-server-tools`.

## When to Use This Guide

Use this detailed guide when:
- The main node tools from `test-server-tools` are not working
- You need step-by-step instructions for each node tool
- You need troubleshooting help for specific node tool issues
- You want to understand node tool details and advanced usage
- You need to test node resources or advanced features

For a quick high-level overview, see `test-server-tools`.

## Prerequisites

Before testing node tools, ensure you have:

1. **Active ROS connection** - Connect to a ROS system first:
   ```
   connect_to_robot(ip='127.0.0.1', port=9090)
   ```

2. **Running ROS nodes** - Make sure you have some nodes running in your ROS system.
   Common nodes include:
   - `/turtlesim` - Turtlesim simulator
   - `/rosbridge_websocket` - Rosbridge server
   - `/rosapi` - ROS API service provider
   - `/cam2image` - Camera image publisher

## Node Tools Overview

The ROS MCP Server provides the following node tools:

1. **get_nodes()** - Get list of all currently running ROS nodes
2. **get_node_details(node)** - Get detailed information about a specific node

Additionally, comprehensive information about all nodes is available as a resource:
- **ros-mcp://ros-metadata/nodes/all** - Get detailed information about all nodes (publishers, subscribers, services)

## Step 1: Get List of All Nodes

Start by discovering what nodes are running in your ROS system:

```
get_nodes()
```

This will return:
- `nodes`: List of all active node names
- `node_count`: Total number of nodes

**Example:**
```
get_nodes()
```

**Expected Response:**
```json
{
  "nodes": ["/turtlesim", "/rosbridge_websocket", "/rosapi"],
  "node_count": 3
}
```

## Step 2: Get Details for a Specific Node

Get detailed information about a specific node, including what it publishes, subscribes to, and what services it provides:

```
get_node_details('/node_name')
```

**Examples:**
```
get_node_details('/turtlesim')
get_node_details('/rosapi')
get_node_details('/cam2image')
```

**Response includes:**
- `node`: The node name
- `publishers`: List of topics this node publishes to
- `subscribers`: List of topics this node subscribes to
- `services`: List of services this node provides
- `publisher_count`: Number of publishers
- `subscriber_count`: Number of subscribers
- `service_count`: Number of services

**Example Response:**
```json
{
  "node": "/turtlesim",
  "publishers": ["/turtle1/pose", "/turtle1/color_sensor"],
  "subscribers": ["/turtle1/cmd_vel"],
  "services": ["/turtle1/teleport_absolute", "/turtle1/teleport_relative"],
  "publisher_count": 2,
  "subscriber_count": 1,
  "service_count": 2
}
```

## Step 3: Get All Nodes Details (Resource)

Get comprehensive information about all nodes at once using the resource:

**Resource URI:** `ros-mcp://ros-metadata/nodes/all`

This resource provides:
- Details for every node in the system
- Publishers, subscribers, and services for each node
- Connection counts and statistics
- Any errors encountered during inspection

**How to access:**
The resource can be accessed through the MCP resource interface. It returns a JSON string with comprehensive node information.

**Response includes:**
- `total_nodes`: Total number of nodes
- `nodes`: Dictionary with details for each node
- `node_errors`: List of any errors encountered (if any)

**Example Response:**
```json
{
  "total_nodes": 3,
  "nodes": {
    "/turtlesim": {
      "publishers": ["/turtle1/pose", "/turtle1/color_sensor"],
      "subscribers": ["/turtle1/cmd_vel"],
      "services": ["/turtle1/teleport_absolute"],
      "publisher_count": 2,
      "subscriber_count": 1,
      "service_count": 1
    },
    "/rosapi": {
      "publishers": [],
      "subscribers": [],
      "services": ["/rosapi/topics", "/rosapi/services"],
      "publisher_count": 0,
      "subscriber_count": 0,
      "service_count": 2
    }
  },
  "node_errors": []
}
```

## Node Naming Convention

ROS nodes use the format: `/node_name`

- Node names always start with `/`
- Node names are case-sensitive
- Common nodes include:
  - `/turtlesim` - Turtlesim simulator
  - `/rosbridge_websocket` - Rosbridge server
  - `/rosapi` - ROS API service provider
  - `/rosapi_params` - ROS API parameters service (ROS 2)


## Troubleshooting

### "No nodes found" or Empty Node List

**Problem:** `get_nodes()` returns no nodes or a warning

**Solutions:**
- Verify ROS connection: `connect_to_robot()`
- Check if ROS system is running: `detect_ros_version()`
- Ensure nodes are actually running in your ROS system
- Try launching some nodes: `rosrun` (ROS 1) or `ros2 run` (ROS 2)

### "Node not found" Error

**Problem:** `get_node_details()` returns "Node not found"

**Solutions:**
- Verify the node name is correct (case-sensitive)
- Check if the node is actually running: `get_nodes()`
- Ensure node name starts with `/`
- Node might have stopped running - check again with `get_nodes()`

### "Service call failed" Error

**Problem:** Service call to get node information fails

**Solutions:**
- Verify rosbridge connection is active
- Check if `/rosapi/nodes` or `/rosapi/node_details` services are available
- Try reconnecting: `connect_to_robot()`
- Check ROS system is responsive

### Empty Publishers/Subscribers/Services

**Problem:** Node exists but has no publishers, subscribers, or services

**Solutions:**
- This is normal for some nodes (e.g., service-only nodes)
- Node might be in initialization phase
- Check if node is fully started
- Some nodes only provide services and don't publish/subscribe

## Tips

- **Start with `get_nodes()`** - Always start by discovering what nodes are available
- **Use `get_node_details()` for specific nodes** - More efficient than getting all nodes details
- **Use the resource `ros-mcp://ros-metadata/nodes/all` for complete overview** - Provides comprehensive information about all nodes
- **Node names are case-sensitive** - `/Turtlesim` is different from `/turtlesim`
- **Nodes can be added/removed dynamically** - Re-run `get_nodes()` if you expect changes
- **Combine with topic tools** - Use node details to understand topic connections
- **Combine with service tools** - Use node details to discover available services

## Related Guides

- **`test-server-tools`** - High-level overview of all ROS MCP Server tools
"""
