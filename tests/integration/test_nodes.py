"""Integration tests for node tools (step 2).

These tests verify get_nodes and get_node_details return correct
results using rosapi_service()/rosapi_type() resolved paths.

Note: calling node_details for nonexistent nodes crashes rosapi_node
on ROS 2 (#273). Tests only query nodes confirmed to exist.
"""

import pytest

from ros_mcp.utils.rosapi_types import RosVersion, get_ros_version, rosapi_service, rosapi_type

pytestmark = [pytest.mark.integration]


class TestGetNodes:
    """Verify get_nodes tool returns the running node list."""

    def test_returns_nodes(self, ws):
        """get_nodes should return a non-empty list of nodes."""
        message = {
            "op": "call_service",
            "id": "test_get_nodes",
            "service": rosapi_service("nodes"),
            "type": rosapi_type("Nodes"),
            "args": {},
        }
        response = ws.request(message)
        assert response is not None
        assert isinstance(response, dict)
        assert response.get("result") is not False, f"Service call failed: {response}"
        assert "values" in response
        nodes = response["values"].get("nodes", [])
        assert len(nodes) > 0, "Should find at least one node"

    def test_includes_turtlesim(self, ws):
        """turtlesim node should be present (launched by Docker container)."""
        message = {
            "op": "call_service",
            "id": "test_nodes_turtlesim",
            "service": rosapi_service("nodes"),
            "type": rosapi_type("Nodes"),
            "args": {},
        }
        response = ws.request(message)
        nodes = response["values"].get("nodes", [])
        assert any("/turtlesim" in n for n in nodes), f"turtlesim not in {nodes}"

    def test_node_count(self, ws):
        """Should have at least 3 nodes: turtlesim, rosbridge, rosapi."""
        message = {
            "op": "call_service",
            "id": "test_node_count",
            "service": rosapi_service("nodes"),
            "type": rosapi_type("Nodes"),
            "args": {},
        }
        response = ws.request(message)
        nodes = response["values"].get("nodes", [])
        assert len(nodes) >= 3, f"Expected >= 3 nodes, got {len(nodes)}: {nodes}"


class TestGetNodeDetails:
    """Verify get_node_details tool returns publishers/subscribers/services.

    Only queries nodes that exist in the node list — calling node_details
    for nonexistent nodes crashes rosapi_node on ROS 2 (#273).
    """

    def test_turtlesim_details(self, ws):
        """get_node_details for /turtlesim should return publishers and subscribers."""
        # Verify turtlesim is in the node list before querying details
        list_msg = {
            "op": "call_service",
            "id": "test_details_list_first",
            "service": rosapi_service("nodes"),
            "type": rosapi_type("Nodes"),
            "args": {},
        }
        list_resp = ws.request(list_msg)
        nodes = list_resp["values"].get("nodes", [])
        assert any("/turtlesim" in n for n in nodes), f"turtlesim not in {nodes}"

        message = {
            "op": "call_service",
            "id": "test_node_details_turtlesim",
            "service": rosapi_service("node_details"),
            "type": rosapi_type("NodeDetails"),
            "args": {"node": "/turtlesim"},
        }
        response = ws.request(message)
        assert response is not None
        assert isinstance(response, dict)
        assert response.get("result") is not False, f"Service call failed: {response}"
        assert "values" in response
        values = response["values"]
        assert len(values.get("publishing", [])) > 0, "turtlesim should have publishers"
        assert len(values.get("subscribing", [])) > 0, "turtlesim should have subscribers"

    def test_rosbridge_details(self, ws):
        """get_node_details for rosbridge should return services."""
        # Find the rosbridge node name from the node list
        list_msg = {
            "op": "call_service",
            "id": "test_details_rosbridge_list",
            "service": rosapi_service("nodes"),
            "type": rosapi_type("Nodes"),
            "args": {},
        }
        list_resp = ws.request(list_msg)
        nodes = list_resp["values"].get("nodes", [])
        rosbridge = next((n for n in nodes if "rosbridge" in n), None)
        assert rosbridge is not None, f"rosbridge not in {nodes}"

        message = {
            "op": "call_service",
            "id": "test_node_details_rosbridge",
            "service": rosapi_service("node_details"),
            "type": rosapi_type("NodeDetails"),
            "args": {"node": rosbridge},
        }
        response = ws.request(message)
        assert response is not None
        assert isinstance(response, dict)
        assert response.get("result") is not False, f"Service call failed: {response}"
        assert "values" in response
        values = response["values"]
        assert len(values.get("services", [])) > 0, "rosbridge should have services"


class TestGetNodesNegative:
    """Negative tests for node tools — edge cases and unexpected input."""

    def test_nodes_are_strings(self, ws):
        """Every node name should be a string starting with /."""
        message = {
            "op": "call_service",
            "id": "test_nodes_strings",
            "service": rosapi_service("nodes"),
            "type": rosapi_type("Nodes"),
            "args": {},
        }
        response = ws.request(message)
        nodes = response["values"].get("nodes", [])
        for node in nodes:
            assert isinstance(node, str), f"Expected string, got {type(node)}: {node}"
            assert node.startswith("/"), f"Node name should start with /: {node}"

    def test_node_details_empty_name_ros1(self, ws):
        """node_details with empty node name should fail gracefully on ROS 1.

        On ROS 2 this crashes rosapi_node (#273), so only test on ROS 1.
        """
        if get_ros_version() == RosVersion.ROS2:
            pytest.skip("empty node name crashes rosapi_node on ROS 2 (#273)")
        message = {
            "op": "call_service",
            "id": "test_node_details_empty",
            "service": rosapi_service("node_details"),
            "type": rosapi_type("NodeDetails"),
            "args": {"node": ""},
        }
        response = ws.request(message)
        assert response is not None
        # Should either fail (result: false) or return empty details
        values = response.get("values", {})
        if response.get("result") is not False:
            assert not values.get("publishing", [])
            assert not values.get("subscribing", [])

    def test_turtlesim_has_expected_topics(self, ws):
        """turtlesim details should include well-known topic names."""
        # Find turtlesim in node list first
        list_msg = {
            "op": "call_service",
            "id": "test_neg_list",
            "service": rosapi_service("nodes"),
            "type": rosapi_type("Nodes"),
            "args": {},
        }
        list_resp = ws.request(list_msg)
        nodes = list_resp["values"].get("nodes", [])
        assert any("/turtlesim" in n for n in nodes)

        message = {
            "op": "call_service",
            "id": "test_neg_turtlesim_topics",
            "service": rosapi_service("node_details"),
            "type": rosapi_type("NodeDetails"),
            "args": {"node": "/turtlesim"},
        }
        response = ws.request(message)
        values = response["values"]
        publishers = values.get("publishing", [])
        subscribers = values.get("subscribing", [])
        # turtlesim should publish pose and subscribe to cmd_vel
        assert any("pose" in p for p in publishers), f"No pose topic in {publishers}"
        assert any("cmd_vel" in s for s in subscribers), f"No cmd_vel topic in {subscribers}"
