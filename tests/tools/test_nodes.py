"""Tests for ros_mcp.tools.nodes module."""

import pytest
from unittest.mock import MagicMock

from ros_mcp.tools.nodes import register_node_tools


class MockFastMCP:
    """Mock FastMCP for capturing registered tools."""

    def __init__(self):
        self.tools = {}

    def tool(self, description=None):
        def decorator(func):
            self.tools[func.__name__] = func
            return func
        return decorator


@pytest.fixture
def mock_mcp():
    """Create a mock FastMCP instance."""
    return MockFastMCP()


@pytest.fixture
def node_tools(mock_mcp, mock_ws_manager):
    """Register node tools and return them."""
    register_node_tools(mock_mcp, mock_ws_manager)
    return mock_mcp.tools


class TestGetNodes:
    """Test cases for get_nodes tool."""

    def test_returns_node_list(self, node_tools, mock_ws_manager):
        """Test that get_nodes returns list of nodes."""
        mock_ws_manager.add_response({
            "result": True,
            "values": {
                "nodes": ["/turtlesim", "/rosbridge_websocket", "/rosapi"]
            }
        })

        result = node_tools["get_nodes"]()

        assert "nodes" in result
        assert len(result["nodes"]) == 3
        assert "/turtlesim" in result["nodes"]
        assert result["node_count"] == 3

    def test_empty_node_list(self, node_tools, mock_ws_manager):
        """Test when no nodes are running."""
        mock_ws_manager.add_response({
            "result": True,
            "values": {"nodes": []}
        })

        result = node_tools["get_nodes"]()

        assert "nodes" in result
        assert result["nodes"] == []
        assert result["node_count"] == 0

    def test_service_call_failure(self, node_tools, mock_ws_manager):
        """Test when service call fails."""
        mock_ws_manager.add_response({
            "result": False,
            "values": {"message": "Service unavailable"}
        })

        result = node_tools["get_nodes"]()

        assert "error" in result
        assert "Service call failed" in result["error"]

    def test_no_response(self, node_tools, mock_ws_manager):
        """Test when no response is received."""
        mock_ws_manager.add_response(None)

        result = node_tools["get_nodes"]()

        assert "warning" in result
        assert "No nodes found" in result["warning"]

    def test_missing_values(self, node_tools, mock_ws_manager):
        """Test when response has no values."""
        mock_ws_manager.add_response({"result": True})

        result = node_tools["get_nodes"]()

        assert "warning" in result


class TestGetNodeDetails:
    """Test cases for get_node_details tool."""

    def test_empty_node_name(self, node_tools, mock_ws_manager):
        """Test with empty node name."""
        result = node_tools["get_node_details"]("")

        assert "error" in result
        assert "cannot be empty" in result["error"]

    def test_whitespace_node_name(self, node_tools, mock_ws_manager):
        """Test with whitespace-only node name."""
        result = node_tools["get_node_details"]("   ")

        assert "error" in result
        assert "cannot be empty" in result["error"]

    def test_successful_get_node_details(self, node_tools, mock_ws_manager):
        """Test getting details for an existing node."""
        mock_ws_manager.add_response({
            "result": True,
            "values": {
                "publishing": ["/turtle1/pose", "/turtle1/color_sensor"],
                "subscribing": ["/turtle1/cmd_vel"],
                "services": [
                    "/turtle1/set_pen",
                    "/turtle1/teleport_absolute",
                    "/turtle1/teleport_relative"
                ]
            }
        })

        result = node_tools["get_node_details"]("/turtlesim")

        assert result["node"] == "/turtlesim"
        assert result["publisher_count"] == 2
        assert result["subscriber_count"] == 1
        assert result["service_count"] == 3
        assert "/turtle1/pose" in result["publishers"]
        assert "/turtle1/cmd_vel" in result["subscribers"]
        assert "/turtle1/set_pen" in result["services"]

    def test_node_not_found(self, node_tools, mock_ws_manager):
        """Test when node doesn't exist."""
        mock_ws_manager.add_response({
            "result": True,
            "values": {
                "publishing": [],
                "subscribing": [],
                "services": []
            }
        })

        result = node_tools["get_node_details"]("/nonexistent_node")

        assert "error" in result
        assert "not found" in result["error"]

    def test_service_call_failure(self, node_tools, mock_ws_manager):
        """Test when service call fails."""
        mock_ws_manager.add_response({
            "result": False,
            "values": {"message": "Node not found"}
        })

        result = node_tools["get_node_details"]("/turtlesim")

        assert "error" in result
        assert "Service call failed" in result["error"]

    def test_only_publishers(self, node_tools, mock_ws_manager):
        """Test node with only publishers."""
        mock_ws_manager.add_response({
            "result": True,
            "values": {
                "publishing": ["/topic1", "/topic2"],
                "subscribing": [],
                "services": []
            }
        })

        result = node_tools["get_node_details"]("/publisher_node")

        assert result["publisher_count"] == 2
        assert result["subscriber_count"] == 0
        assert result["service_count"] == 0

    def test_only_subscribers(self, node_tools, mock_ws_manager):
        """Test node with only subscribers."""
        mock_ws_manager.add_response({
            "result": True,
            "values": {
                "publishing": [],
                "subscribing": ["/input_topic"],
                "services": []
            }
        })

        result = node_tools["get_node_details"]("/subscriber_node")

        assert result["publisher_count"] == 0
        assert result["subscriber_count"] == 1
        assert result["service_count"] == 0

    def test_only_services(self, node_tools, mock_ws_manager):
        """Test node with only services."""
        mock_ws_manager.add_response({
            "result": True,
            "values": {
                "publishing": [],
                "subscribing": [],
                "services": ["/my_service"]
            }
        })

        result = node_tools["get_node_details"]("/service_node")

        assert result["publisher_count"] == 0
        assert result["subscriber_count"] == 0
        assert result["service_count"] == 1

    def test_node_name_with_special_characters(self, node_tools, mock_ws_manager):
        """Test node name with special characters in ID."""
        mock_ws_manager.add_response({
            "result": True,
            "values": {
                "publishing": ["/data"],
                "subscribing": [],
                "services": []
            }
        })

        result = node_tools["get_node_details"]("/my_robot/sensor_node")

        assert result["node"] == "/my_robot/sensor_node"
        # Should have made a request with sanitized ID
        request = mock_ws_manager.get_request_history()[-1]
        assert "_my_robot_sensor_node" in request["id"]

    def test_missing_values_in_response(self, node_tools, mock_ws_manager):
        """Test when response has partial data."""
        mock_ws_manager.add_response({
            "result": True,
            "values": {
                "publishing": ["/topic1"]
                # Missing subscribing and services
            }
        })

        result = node_tools["get_node_details"]("/partial_node")

        assert result["publisher_count"] == 1
        assert result["subscriber_count"] == 0
        assert result["service_count"] == 0


class TestNodeToolsIntegration:
    """Integration tests for node tools."""

    def test_get_nodes_then_details(self, node_tools, mock_ws_manager):
        """Test getting nodes then getting details for each."""
        # First get nodes
        mock_ws_manager.add_response({
            "result": True,
            "values": {"nodes": ["/turtlesim", "/rosbridge"]}
        })

        nodes_result = node_tools["get_nodes"]()
        assert nodes_result["node_count"] == 2

        # Then get details for first node
        mock_ws_manager.add_response({
            "result": True,
            "values": {
                "publishing": ["/turtle1/pose"],
                "subscribing": ["/turtle1/cmd_vel"],
                "services": ["/spawn"]
            }
        })

        details_result = node_tools["get_node_details"]("/turtlesim")
        assert details_result["node"] == "/turtlesim"
        assert details_result["publisher_count"] == 1
