"""Connection tools testing prompt for ROS1 MCP."""


def register_test_connection_tools_prompts(mcp):
    """Register connection test prompt."""

    @mcp.prompt(name="test-connection-tools")
    def test_connection_tools() -> str:
        return """# Test Connection Tools (ROS1)

1. Ensure rosbridge is running:
   - `rosrun rosbridge_server rosbridge_websocket`
2. Verify connectivity:
   - `ping_robot(ip='127.0.0.1', port=9090)`
3. Configure MCP target:
   - `connect_to_robot(ip='127.0.0.1', port=9090)`
4. Confirm ROS distro:
   - `detect_ros_version()`

If detection fails, verify `/rosapi/get_param` is available and `/rosdistro` exists.
"""
