"""Integration tests for node tools (step 2).

These tests verify get_nodes and get_node_details return correct
results using rosapi_service()/rosapi_type() resolved paths.

Note: get_node_details crashes rosapi_node on Humble and Jazzy (#273).
Those tests are skipped on ROS 2.
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

    Note: get_node_details crashes rosapi_node on Humble and Jazzy (#273).
    These tests only run on ROS 1.
    """

    @pytest.fixture(autouse=True)
    def _skip_ros2(self, ws):
        """Skip all tests in this class on ROS 2 due to #273."""
        # ws ensures detect_rosapi_types() has been called
        if get_ros_version() == RosVersion.ROS2:
            pytest.skip("get_node_details crashes rosapi_node on ROS 2 (#273)")

    def test_turtlesim_details(self, ws):
        """get_node_details for /turtlesim should return publishers and subscribers."""
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
        # turtlesim publishes to /turtle1/pose and subscribes to /turtle1/cmd_vel
        assert len(values.get("publishing", [])) > 0, "turtlesim should have publishers"
        assert len(values.get("subscribing", [])) > 0, "turtlesim should have subscribers"

    def test_nonexistent_node(self, ws):
        """get_node_details for a nonexistent node should return empty or error."""
        message = {
            "op": "call_service",
            "id": "test_node_details_missing",
            "service": rosapi_service("node_details"),
            "type": rosapi_type("NodeDetails"),
            "args": {"node": "/nonexistent_node_xyz"},
        }
        response = ws.request(message)
        assert response is not None
        # Either result is false or values are empty
        if response.get("result") is not False:
            values = response.get("values", {})
            publishing = values.get("publishing", [])
            subscribing = values.get("subscribing", [])
            services = values.get("services", [])
            assert not publishing and not subscribing and not services
