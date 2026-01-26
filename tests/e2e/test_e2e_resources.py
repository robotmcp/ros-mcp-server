"""E2E tests for MCP resources with real ROS environment."""

import pytest

pytestmark = pytest.mark.e2e


class TestRobotSpecsResources:
    """E2E tests for robot specification resources."""

    def test_robot_specs_list_available_robots(self, mcp_server):
        """Verify robot specs resource lists available robots."""
        # Access the resource manager
        resource_manager = mcp_server._resource_manager
        resources = resource_manager._resources

        # Check that robot specs resource exists
        robot_specs_uri = "ros-mcp://robot-specs/get_verified_robots_list"
        assert robot_specs_uri in resources, (
            f"Expected robot specs resource at {robot_specs_uri}"
        )


class TestRosMetadataResources:
    """E2E tests for ROS metadata resources."""

    def test_ros_metadata_all_returns_topics(self, ws_manager, rosapi_topics_type):
        """Verify ROS metadata returns topics from running ROS system."""
        message = {
            "op": "call_service",
            "service": "/rosapi/topics",
            "type": rosapi_topics_type,
            "args": {},
            "id": "metadata_topics_test",
        }

        with ws_manager:
            response = ws_manager.request(message, timeout=10.0)

        assert "values" in response, f"Expected values in response: {response}"
        topics = response["values"].get("topics", [])
        assert len(topics) > 0, "Expected at least one topic from ROS system"

    def test_ros_metadata_all_returns_services(self, ws_manager, rosapi_services_type):
        """Verify ROS metadata returns services from running ROS system."""
        message = {
            "op": "call_service",
            "service": "/rosapi/services",
            "type": rosapi_services_type,
            "args": {},
            "id": "metadata_services_test",
        }

        with ws_manager:
            response = ws_manager.request(message, timeout=10.0)

        assert "values" in response, f"Expected values in response: {response}"
        services = response["values"].get("services", [])
        assert len(services) > 0, "Expected at least one service from ROS system"

    def test_ros_metadata_all_returns_nodes(self, ws_manager, rosapi_nodes_type):
        """Verify ROS metadata returns nodes from running ROS system."""
        message = {
            "op": "call_service",
            "service": "/rosapi/nodes",
            "type": rosapi_nodes_type,
            "args": {},
            "id": "metadata_nodes_test",
        }

        with ws_manager:
            response = ws_manager.request(message, timeout=10.0)

        assert "values" in response, f"Expected values in response: {response}"
        nodes = response["values"].get("nodes", [])
        assert len(nodes) > 0, "Expected at least one node from ROS system"

    def test_ros_metadata_contains_turtlesim(self, ws_manager, rosapi_topics_type):
        """Verify ROS metadata contains turtlesim-related entries."""
        # Get topics
        topics_message = {
            "op": "call_service",
            "service": "/rosapi/topics",
            "type": rosapi_topics_type,
            "args": {},
            "id": "metadata_turtlesim_topics_test",
        }

        with ws_manager:
            response = ws_manager.request(topics_message, timeout=10.0)

        topics = response.get("values", {}).get("topics", [])

        # Check for turtlesim-related topics
        turtlesim_topics = [t for t in topics if "turtle" in t.lower()]
        assert len(turtlesim_topics) > 0, (
            f"Expected turtlesim topics, found: {topics[:10]}..."
        )

    def test_resources_registered_with_mcp(self, mcp_server):
        """Verify resources are registered with MCP server."""
        resource_manager = mcp_server._resource_manager
        resources = resource_manager._resources

        assert len(resources) > 0, "Expected at least one resource to be registered"

        # Check for expected resource URIs
        expected_resources = [
            "ros-mcp://robot-specs/get_verified_robots_list",
            "ros-mcp://ros-metadata/topics/all",
            "ros-mcp://ros-metadata/services/all",
            "ros-mcp://ros-metadata/nodes/all",
        ]

        for expected in expected_resources:
            assert expected in resources, (
                f"Expected resource '{expected}' to be registered. Found: {list(resources.keys())}"
            )
