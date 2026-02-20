"""Node tools testing prompt for ROS1 MCP."""


def register_test_nodes_tools_prompts(mcp):
    """Register node test prompt."""

    @mcp.prompt(name="test-nodes-tools")
    def test_nodes_tools() -> str:
        return """# Test Node Tools (ROS1)

- List nodes:
  - `get_nodes()`
- Inspect one node:
  - `get_node_details('/turtlesim')`

If node details are empty, ensure the exact node name is used and that `rosapi` is active.
"""
