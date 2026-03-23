"""Integration tests for node tools (step 2).

These tests call the actual MCP tool functions (get_nodes, get_node_details)
against a live rosbridge container.

Note: calling get_node_details for nonexistent nodes crashes rosapi_node
on ROS 2 (#273). Tests only query nodes confirmed to exist.
"""

import pytest

pytestmark = [pytest.mark.integration]


class TestGetNodes:
    """Verify get_nodes MCP tool returns the running node list."""

    def test_returns_nodes(self, tools):
        """get_nodes should return nodes and node_count."""
        result = tools["get_nodes"]()
        assert "nodes" in result
        assert "node_count" in result
        assert result["node_count"] > 0
        assert result["node_count"] == len(result["nodes"])

    def test_includes_turtlesim(self, tools):
        """turtlesim node should be present (launched by Docker container)."""
        result = tools["get_nodes"]()
        nodes = result["nodes"]
        assert any("/turtlesim" in n for n in nodes), f"turtlesim not in {nodes}"

    def test_includes_rosbridge(self, tools):
        """rosbridge node should be present."""
        result = tools["get_nodes"]()
        nodes = result["nodes"]
        assert any("rosbridge" in n for n in nodes), f"rosbridge not in {nodes}"

    def test_node_count_at_least_three(self, tools):
        """Should have at least 3 nodes: turtlesim, rosbridge, rosapi."""
        result = tools["get_nodes"]()
        assert result["node_count"] >= 3, (
            f"Expected >= 3, got {result['node_count']}: {result['nodes']}"
        )

    def test_all_nodes_are_ros_names(self, tools):
        """Every node name should be a string starting with /."""
        result = tools["get_nodes"]()
        for node in result["nodes"]:
            assert isinstance(node, str), f"Expected string, got {type(node)}: {node}"
            assert node.startswith("/"), f"Node name should start with /: {node}"


class TestGetNodeDetails:
    """Verify get_node_details MCP tool returns publishers/subscribers/services.

    Only queries nodes confirmed to exist — calling get_node_details for
    nonexistent nodes crashes rosapi_node on ROS 2 (#273).
    """

    def test_turtlesim_details(self, tools):
        """get_node_details for /turtlesim should return publishers and subscribers."""
        result = tools["get_node_details"](node="/turtlesim")
        assert result["node"] == "/turtlesim"
        assert result["publisher_count"] > 0, "turtlesim should have publishers"
        assert result["subscriber_count"] > 0, "turtlesim should have subscribers"
        assert any("pose" in p for p in result["publishers"]), f"No pose in {result['publishers']}"
        assert any("cmd_vel" in s for s in result["subscribers"]), (
            f"No cmd_vel in {result['subscribers']}"
        )

    def test_rosbridge_has_services(self, tools):
        """get_node_details for rosbridge should return services."""
        # Find rosbridge node name dynamically (varies by distro)
        nodes_result = tools["get_nodes"]()
        rosbridge = next((n for n in nodes_result["nodes"] if "rosbridge" in n), None)
        assert rosbridge is not None

        result = tools["get_node_details"](node=rosbridge)
        assert result["node"] == rosbridge
        assert result["service_count"] > 0, "rosbridge should have services"

    def test_detail_counts_match_lists(self, tools):
        """publisher_count/subscriber_count/service_count should match list lengths."""
        result = tools["get_node_details"](node="/turtlesim")
        assert result["publisher_count"] == len(result["publishers"])
        assert result["subscriber_count"] == len(result["subscribers"])
        assert result["service_count"] == len(result["services"])

    def test_empty_node_name_returns_error(self, tools):
        """get_node_details with empty string should return error dict."""
        result = tools["get_node_details"](node="")
        assert "error" in result

    def test_whitespace_node_name_returns_error(self, tools):
        """get_node_details with whitespace should return error dict."""
        result = tools["get_node_details"](node="   ")
        assert "error" in result
