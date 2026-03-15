"""Integration tests for connection and config tools against a real ROS2 rosbridge."""

import pytest

pytestmark = [pytest.mark.integration, pytest.mark.slow]


class TestDetectRosVersion:
    def test_detects_ros2(self, tools):
        result = tools["detect_ros_version"]()
        assert "error" not in result
        assert result.get("version") is not None
        assert "distro" in result


class TestPingRobot:
    def test_ping_localhost(self, tools):
        result = tools["connect_to_robot"](ip="127.0.0.1", port=9090)
        assert "connectivity_test" in result
