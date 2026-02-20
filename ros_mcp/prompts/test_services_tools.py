"""Service tools testing prompt for ROS1 MCP."""


def register_test_services_tools_prompts(mcp):
    """Register service test prompt."""

    @mcp.prompt(name="test-services-tools")
    def test_services_tools() -> str:
        return """# Test Service Tools (ROS1)

- List services:
  - `get_services()`
- Inspect one service:
  - `get_service_type('/turtle1/teleport_absolute')`
  - `get_service_details('/turtle1/teleport_absolute')`
- Call a service:
  - `call_service('/turtle1/teleport_absolute', 'turtlesim/TeleportAbsolute', {'x': 5.5, 'y': 5.5, 'theta': 0.0})`

Tip: `get_service_details()` returns field names already formatted for rosbridge args.
"""
