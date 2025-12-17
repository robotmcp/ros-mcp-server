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
        return """# Testing ROS MCP Server Capabilities

This guide will help you test and explore the capabilities of the ROS MCP Server.

## Step 1: Test Connection Tools

Before testing other capabilities, verify you can connect to a ROS robot:

1. **Ping the robot** to check connectivity:
   ```
   ping_robot(ip='192.168.1.100', port=9090)
   ```

2. **Connect to the robot**:
   ```
   connect_to_robot(ip='192.168.1.100', port=9090)
   ```

## Step 2: Test Discovery Tools

Explore what's available in your ROS system:

1. **Detect ROS version**:
   ```
   detect_ros_version()
   ```

2. **Get all topics**:
   ```
   get_topics()
   ```

3. **Get all services**:
   ```
   get_services()
   ```

4. **Get all nodes**:
   ```
   get_nodes()
   ```

## Step 3: Test Topic Operations

Test topic subscription and publishing:

1. **Get topic details**:
   ```
   get_topic_details('/cmd_vel')
   ```

2. **Subscribe to a topic** (get one message):
   ```
   subscribe_once(topic='/cmd_vel', msg_type='geometry_msgs/msg/Twist')
   ```

3. **Publish to a topic**:
   ```
   publish_once(topic='/cmd_vel', msg_type='geometry_msgs/msg/Twist', msg={'linear': {'x': 1.0}})
   ```

## Step 4: Test Service Operations

Test service calls:

1. **Get service details**:
   ```
   get_service_details('rosapi/Topics')
   ```

2. **Call a service**:
   ```
   call_service(service_name='/rosapi/topics', service_type='rosapi/Topics', request={})
   ```

## Step 5: Test Advanced Features

1. **Inspect all topics** (comprehensive information):
   ```
   inspect_all_topics()
   ```

2. **Get ROS metadata** (all information at once):
   ```
   Resource: ros-mcp://ros-metadata/all
   ```

3. **Test image analysis** (if you have image topics):
   ```
   subscribe_once(topic='/camera/image_raw', msg_type='sensor_msgs/Image', expects_image='true')
   analyze_previously_received_image()
   ```

## Step 6: Test Robot-Specific Features

1. **List verified robots**:
   ```
   get_verified_robots_list()
   ```

2. **Get robot specifications** (if available):
   ```
   get_verified_robot_spec('unitree_go2')
   ```

## Testing Checklist

- [ ] Test connection tools (ping, connect)
- [ ] Test discovery tools (topics, services, nodes)
- [ ] Test topic operations (subscribe, publish)
- [ ] Test service operations (call service)
- [ ] Test parameter operations (if ROS 2)
- [ ] Test action operations (if ROS 2)
- [ ] Test image analysis (if applicable)

## Tips

- Most tools work with both ROS 1 and ROS 2
- Parameters and Actions are ROS 2 only
- Use `inspect_all_*` tools for comprehensive information (may be slow with many items)
- All resources are accessible via their URIs

## Need Help?

- Check ROS metadata: `ros-mcp://ros-metadata/all`
- List verified robots: `ros-mcp://robot-specs/get_verified_robots_list`
"""
