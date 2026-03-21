"""Integration test: verify ROS version detection against a live rosbridge."""

import pytest

from ros_mcp.utils.rosapi_types import (
    RosVersion,
    get_distro,
    get_ros_version,
    rosapi_service,
    rosapi_type,
)

pytestmark = [pytest.mark.integration]

# Expected ROS version per distro
_DISTRO_TO_VERSION = {
    "noetic": RosVersion.ROS1,
    "humble": RosVersion.ROS2,
}

# Expected service prefix per distro (independent of ROS version)
_DISTRO_TO_PREFIX = {
    "noetic": "/rosapi",
    "humble": "/rosapi",
}


class TestDetectRosVersion:
    """Tests run after detect_rosapi_types() was called once in the ws fixture."""

    def test_detection_succeeds(self, ws):
        """detect_rosapi_types should have identified the connected rosbridge."""
        assert get_distro() != "", "Distro should be detected (not empty)"

    def test_version_matches_distro(self, ws, ros_distro):
        """get_ros_version() should return the correct enum for the launched distro."""
        expected = _DISTRO_TO_VERSION[ros_distro]
        assert get_ros_version() == expected

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

    def test_resolved_service_works(self, ws):
        """Call the resolved service path to verify it reaches rosbridge."""
        message = {
            "op": "call_service",
            "id": "test_resolved_svc",
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
        assert len(nodes) > 0, "Should find at least one node (turtlesim)"
