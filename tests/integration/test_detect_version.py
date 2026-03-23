"""Integration tests for detection tools.

These tests verify the rosapi_types module (service prefix, type format,
version detection) and the detect_ros_version MCP tool.
"""

import pytest

from ros_mcp.utils.rosapi_types import (
    RosVersion,
    get_distro,
    get_ros_version,
    rosapi_service,
    rosapi_type,
)

pytestmark = [pytest.mark.integration]

_DISTRO_TO_VERSION = {
    "melodic": RosVersion.ROS1,
    "noetic": RosVersion.ROS1,
    "humble": RosVersion.ROS2,
    "jazzy": RosVersion.ROS2,
}

_DISTRO_TO_PREFIX = {
    "melodic": "/rosapi",
    "noetic": "/rosapi",
    "humble": "/rosapi",
    "jazzy": "/rosapi",
}


class TestDetectRosVersion:
    """Verify rosapi_types module: version detection, service prefixes, type format."""

    def test_version_is_detected(self, ws):
        """Version should always be determined (never falls through)."""
        version = get_ros_version()
        assert version in (RosVersion.ROS1, RosVersion.ROS2)

    def test_version_matches_distro(self, ws, ros_distro):
        """get_ros_version() should return the correct enum for the launched distro."""
        expected = _DISTRO_TO_VERSION[ros_distro]
        assert get_ros_version() == expected

    def test_distro_matches(self, ws, ros_distro):
        """Detected distro should match the distro we launched."""
        detected = get_distro()
        assert detected == ros_distro, f"Expected distro '{ros_distro}', got '{detected}'"

    def test_ros2_has_distro(self, ws):
        """On ROS 2, distro should always be detected."""
        if get_ros_version() == RosVersion.ROS2:
            assert get_distro() != "", "ROS 2 should always report a distro"

    def test_service_prefix(self, ws, ros_distro):
        """Service prefix should match the known prefix for this distro."""
        expected_prefix = _DISTRO_TO_PREFIX[ros_distro]
        assert rosapi_service("nodes") == f"{expected_prefix}/nodes"
        assert rosapi_service("topics") == f"{expected_prefix}/topics"

    def test_type_format(self, ws, ros_distro):
        """Type format should match the detected ROS version."""
        expected = _DISTRO_TO_VERSION[ros_distro]
        if expected == RosVersion.ROS2:
            assert rosapi_type("Services") == "rosapi_msgs/srv/Services"
            assert rosapi_type("Topics") == "rosapi_msgs/srv/Topics"
        else:
            assert rosapi_type("Services") == "rosapi/Services"
            assert rosapi_type("Topics") == "rosapi/Topics"

    def test_resolved_service_works(self, tools):
        """Resolved service paths should work end-to-end via get_nodes tool."""
        result = tools["get_nodes"]()
        assert "nodes" in result, f"get_nodes failed: {result}"
        assert len(result["nodes"]) > 0, "Should find at least one node (turtlesim)"


class TestDetectRosVersionTool:
    """Test the detect_ros_version MCP tool function directly."""

    def test_tool_returns_version_and_distro(self, tools, ros_distro):
        """detect_ros_version tool should return version and distro matching the container."""
        result = tools["detect_ros_version"]()
        assert "error" not in result, f"Tool returned error: {result}"
        assert "version" in result
        assert "distro" in result
        assert result["distro"] == ros_distro

    def test_tool_version_is_consistent_string(self, tools):
        """version should always be a string ('1' or '2')."""
        result = tools["detect_ros_version"]()
        assert isinstance(result["version"], str)
        assert result["version"] in ("1", "2")

    def test_tool_ros2_version(self, tools):
        """On ROS 2, version should be '2'."""
        result = tools["detect_ros_version"]()
        if get_ros_version() == RosVersion.ROS2:
            assert result["version"] == "2"

    def test_tool_ros1_version(self, tools):
        """On ROS 1, version should be '1'."""
        result = tools["detect_ros_version"]()
        if get_ros_version() == RosVersion.ROS1:
            assert result["version"] == "1"
