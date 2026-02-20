"""Parameter tools testing prompt for ROS1 MCP."""


def register_test_parameters_tools_prompts(mcp):
    """Register parameter test prompt."""

    @mcp.prompt(name="test-parameters-tools")
    def test_parameters_tools() -> str:
        return """# Test Parameter Tools (ROS1)

- List parameter names:
  - `get_parameters()`
- Read a parameter:
  - `get_parameter('/turtlesim/background_r')`
- Check existence:
  - `has_parameter('/turtlesim/background_r')`
- Set parameter:
  - `set_parameter('/turtlesim/background_r', '255')`
- Delete parameter:
  - `delete_parameter('/my_temp_param')`
- Detailed read:
  - `get_parameter_details('/turtlesim/background_r')`

Note: Values are returned as rosapi strings; use `type` in output for parsed type hints.
"""
