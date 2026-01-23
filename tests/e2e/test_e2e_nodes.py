"""E2E tests for node operations with real ROS turtlesim."""

import pytest

pytestmark = pytest.mark.e2e


class TestGetNodes:
    """E2E tests for get_nodes functionality."""

    def test_get_nodes_returns_list(self, ws_manager, rosapi_nodes_type):
        """Verify get_nodes returns a list of running nodes."""
        message = {
            "op": "call_service",
            "service": "/rosapi/nodes",
            "type": rosapi_nodes_type,
            "args": {},
            "id": "get_nodes_e2e",
        }

        with ws_manager:
            response = ws_manager.request(message, timeout=10.0)

        assert "error" not in response
        assert "values" in response

        nodes = response["values"].get("nodes", [])
        assert isinstance(nodes, list)
        assert len(nodes) > 0, "Should have at least one node running"

    def test_get_nodes_contains_turtlesim(self, ws_manager, rosapi_nodes_type):
        """Verify turtlesim node is in the list."""
        message = {
            "op": "call_service",
            "service": "/rosapi/nodes",
            "type": rosapi_nodes_type,
            "args": {},
            "id": "get_nodes_turtlesim_e2e",
        }

        with ws_manager:
            response = ws_manager.request(message, timeout=10.0)

        nodes = response.get("values", {}).get("nodes", [])

        # Look for turtlesim node (might be named /turtlesim or similar)
        turtlesim_nodes = [n for n in nodes if "turtlesim" in n.lower()]
        assert len(turtlesim_nodes) > 0, f"Expected turtlesim node in {nodes}"

    def test_get_nodes_contains_rosbridge(self, ws_manager, rosapi_nodes_type):
        """Verify rosbridge node is in the list."""
        message = {
            "op": "call_service",
            "service": "/rosapi/nodes",
            "type": rosapi_nodes_type,
            "args": {},
            "id": "get_nodes_rosbridge_e2e",
        }

        with ws_manager:
            response = ws_manager.request(message, timeout=10.0)

        nodes = response.get("values", {}).get("nodes", [])

        # Look for rosbridge node
        rosbridge_nodes = [n for n in nodes if "rosbridge" in n.lower()]
        assert len(rosbridge_nodes) > 0, f"Expected rosbridge node in {nodes}"


class TestGetNodeDetails:
    """E2E tests for get_node_details functionality."""

    def test_get_turtlesim_node_details(self, ws_manager, rosapi_nodes_type, rosapi_node_details_type):
        """Get details for turtlesim node."""
        # First get the turtlesim node name
        nodes_msg = {
            "op": "call_service",
            "service": "/rosapi/nodes",
            "type": rosapi_nodes_type,
            "args": {},
            "id": "get_nodes_for_details",
        }

        with ws_manager:
            nodes_response = ws_manager.request(nodes_msg, timeout=10.0)

        nodes = nodes_response.get("values", {}).get("nodes", [])
        turtlesim_node = next((n for n in nodes if "turtlesim" in n.lower()), None)

        if not turtlesim_node:
            pytest.skip("Turtlesim node not found")

        # Get node details
        details_msg = {
            "op": "call_service",
            "service": "/rosapi/node_details",
            "type": rosapi_node_details_type,
            "args": {"node": turtlesim_node},
            "id": "get_node_details_e2e",
        }

        with ws_manager:
            response = ws_manager.request(details_msg, timeout=10.0)

        assert "error" not in response
        assert "values" in response

        values = response["values"]

        # Turtlesim should have publishers, subscribers, and services
        publishers = values.get("publishing", [])
        subscribers = values.get("subscribing", [])

        # Check for expected turtlesim topics
        assert any("pose" in p for p in publishers), f"Expected pose publisher in {publishers}"
        assert any("cmd_vel" in s for s in subscribers), (
            f"Expected cmd_vel subscriber in {subscribers}"
        )

    def test_get_node_details_has_services(self, ws_manager, rosapi_nodes_type, rosapi_node_details_type):
        """Verify node details include services."""
        # Get turtlesim node
        nodes_msg = {
            "op": "call_service",
            "service": "/rosapi/nodes",
            "type": rosapi_nodes_type,
            "args": {},
            "id": "get_nodes_for_services",
        }

        with ws_manager:
            nodes_response = ws_manager.request(nodes_msg, timeout=10.0)

        nodes = nodes_response.get("values", {}).get("nodes", [])
        turtlesim_node = next((n for n in nodes if "turtlesim" in n.lower()), None)

        if not turtlesim_node:
            pytest.skip("Turtlesim node not found")

        details_msg = {
            "op": "call_service",
            "service": "/rosapi/node_details",
            "type": rosapi_node_details_type,
            "args": {"node": turtlesim_node},
            "id": "get_node_services_e2e",
        }

        with ws_manager:
            response = ws_manager.request(details_msg, timeout=10.0)

        services = response.get("values", {}).get("services", [])

        # Turtlesim has several services
        expected_services = ["teleport", "set_pen"]
        for expected in expected_services:
            assert any(expected in s for s in services), (
                f"Expected service containing '{expected}' in {services}"
            )


class TestNodeIntegration:
    """Integration tests for node operations."""

    def test_list_nodes_then_get_details(self, ws_manager, rosapi_nodes_type, rosapi_node_details_type):
        """Workflow: list nodes then get details for each."""
        # Get all nodes
        nodes_msg = {
            "op": "call_service",
            "service": "/rosapi/nodes",
            "type": rosapi_nodes_type,
            "args": {},
            "id": "integration_get_nodes",
        }

        with ws_manager:
            nodes_response = ws_manager.request(nodes_msg, timeout=10.0)

        nodes = nodes_response.get("values", {}).get("nodes", [])
        assert len(nodes) > 0

        # Get details for first node
        first_node = nodes[0]
        details_msg = {
            "op": "call_service",
            "service": "/rosapi/node_details",
            "type": rosapi_node_details_type,
            "args": {"node": first_node},
            "id": "integration_get_details",
        }

        with ws_manager:
            details_response = ws_manager.request(details_msg, timeout=10.0)

        # Should get valid response
        assert "values" in details_response
        values = details_response["values"]

        # Note: Some internal nodes might have no visible publishers/subscribers
        # so we just check we got a valid response structure
        assert isinstance(values.get("publishing", []), list)
        assert isinstance(values.get("subscribing", []), list)
        assert isinstance(values.get("services", []), list)
