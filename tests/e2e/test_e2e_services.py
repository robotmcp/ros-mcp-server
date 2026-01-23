"""E2E tests for service operations with real ROS 2 turtlesim."""

import json
import math
import time

import pytest

from tests.e2e.conftest import get_turtle_pose, reset_turtle, teleport_turtle


pytestmark = pytest.mark.e2e


class TestGetServices:
    """E2E tests for get_services functionality."""

    def test_get_services_returns_turtlesim_services(self, ws_manager, turtlesim_services):
        """Verify turtlesim services exist in service list."""
        message = {
            "op": "call_service",
            "service": "/rosapi/services",
            "type": "rosapi_msgs/srv/Services",
            "args": {},
            "id": "get_services_e2e",
        }

        with ws_manager:
            response = ws_manager.request(message, timeout=10.0)

        assert "values" in response, f"Expected values in response: {response}"
        services = response["values"].get("services", [])

        # Check for expected turtlesim services
        for expected_service in turtlesim_services:
            assert expected_service in services, f"Expected {expected_service} in services"

    def test_get_services_includes_rosapi(self, ws_manager):
        """Verify rosapi services are also listed."""
        message = {
            "op": "call_service",
            "service": "/rosapi/services",
            "type": "rosapi_msgs/srv/Services",
            "args": {},
            "id": "get_services_rosapi_e2e",
        }

        with ws_manager:
            response = ws_manager.request(message, timeout=10.0)

        services = response.get("values", {}).get("services", [])

        # Check for some rosapi services
        rosapi_services = [s for s in services if "/rosapi/" in s]
        assert len(rosapi_services) > 0, "Should have rosapi services"


class TestCallTeleportAbsolute:
    """E2E tests for teleport_absolute service."""

    def test_teleport_to_center(self, ws_manager):
        """Teleport turtle to center of screen."""
        # First reset
        reset_turtle(ws_manager)

        # Teleport to center (5.5, 5.5)
        message = {
            "op": "call_service",
            "service": "/turtle1/teleport_absolute",
            "type": "turtlesim/srv/TeleportAbsolute",
            "args": {"x": 5.5, "y": 5.5, "theta": 0.0},
            "id": "teleport_center_e2e",
        }

        with ws_manager:
            response = ws_manager.request(message, timeout=10.0)

        # Service should succeed (empty response for TeleportAbsolute)
        assert "error" not in response, f"Service call should succeed: {response}"

        # Verify turtle is at the target position
        time.sleep(0.3)
        pose = get_turtle_pose(ws_manager)
        assert pose is not None, "Should get pose after teleport"
        assert abs(pose["x"] - 5.5) < 0.1, f"x should be ~5.5, got {pose['x']}"
        assert abs(pose["y"] - 5.5) < 0.1, f"y should be ~5.5, got {pose['y']}"

    def test_teleport_to_corner(self, ws_manager):
        """Teleport turtle to top-right corner."""
        message = {
            "op": "call_service",
            "service": "/turtle1/teleport_absolute",
            "type": "turtlesim/srv/TeleportAbsolute",
            "args": {"x": 10.0, "y": 10.0, "theta": math.pi / 2},
            "id": "teleport_corner_e2e",
        }

        with ws_manager:
            response = ws_manager.request(message, timeout=10.0)

        assert "error" not in response

        time.sleep(0.3)
        pose = get_turtle_pose(ws_manager)
        assert pose is not None
        assert abs(pose["x"] - 10.0) < 0.1, f"x should be ~10.0, got {pose['x']}"
        assert abs(pose["y"] - 10.0) < 0.1, f"y should be ~10.0, got {pose['y']}"

    def test_teleport_sets_orientation(self, ws_manager):
        """Verify teleport sets the correct orientation."""
        target_theta = math.pi / 4  # 45 degrees

        message = {
            "op": "call_service",
            "service": "/turtle1/teleport_absolute",
            "type": "turtlesim/srv/TeleportAbsolute",
            "args": {"x": 5.5, "y": 5.5, "theta": target_theta},
            "id": "teleport_orientation_e2e",
        }

        with ws_manager:
            response = ws_manager.request(message, timeout=10.0)

        assert "error" not in response

        time.sleep(0.3)
        pose = get_turtle_pose(ws_manager)
        assert pose is not None
        # Allow some tolerance for theta comparison
        assert abs(pose["theta"] - target_theta) < 0.1, f"theta should be ~{target_theta}, got {pose['theta']}"


class TestCallSpawnService:
    """E2E tests for spawn service."""

    def test_spawn_new_turtle(self, ws_manager):
        """Spawn a new turtle and verify new topics appear."""
        # First, get current topics
        topics_msg = {
            "op": "call_service",
            "service": "/rosapi/topics",
            "type": "rosapi/Topics",
            "args": {},
            "id": "get_topics_before_spawn",
        }

        with ws_manager:
            topics_response = ws_manager.request(topics_msg, timeout=10.0)

        initial_topics = topics_response.get("values", {}).get("topics", [])

        # Spawn a new turtle
        spawn_msg = {
            "op": "call_service",
            "service": "/spawn",
            "type": "turtlesim/srv/Spawn",
            "args": {"x": 2.0, "y": 2.0, "theta": 0.0, "name": "turtle2"},
            "id": "spawn_turtle2_e2e",
        }

        with ws_manager:
            spawn_response = ws_manager.request(spawn_msg, timeout=10.0)

        # Spawn should return the name
        if "values" in spawn_response:
            assert spawn_response["values"].get("name") == "turtle2"

        # Wait for new topics to register
        time.sleep(1.0)

        # Verify new topics exist
        with ws_manager:
            new_topics_response = ws_manager.request(topics_msg, timeout=10.0)

        new_topics = new_topics_response.get("values", {}).get("topics", [])

        assert "/turtle2/cmd_vel" in new_topics, "Should have turtle2 cmd_vel topic"
        assert "/turtle2/pose" in new_topics, "Should have turtle2 pose topic"

        # Clean up - kill the spawned turtle
        kill_msg = {
            "op": "call_service",
            "service": "/kill",
            "type": "turtlesim/srv/Kill",
            "args": {"name": "turtle2"},
            "id": "kill_turtle2_e2e",
        }

        with ws_manager:
            ws_manager.request(kill_msg, timeout=5.0)


class TestCallClearService:
    """E2E tests for clear service."""

    def test_call_clear_service(self, ws_manager):
        """Verify clear service can be called successfully."""
        message = {
            "op": "call_service",
            "service": "/clear",
            "type": "std_srvs/srv/Empty",
            "args": {},
            "id": "clear_e2e",
        }

        with ws_manager:
            response = ws_manager.request(message, timeout=10.0)

        # Clear service should succeed (empty response)
        assert "error" not in response, f"Clear service should succeed: {response}"


class TestCallResetService:
    """E2E tests for reset service."""

    def test_reset_returns_turtle_to_center(self, ws_manager):
        """Verify reset service returns turtle to initial position."""
        # First, move turtle away from center
        teleport_turtle(ws_manager, 2.0, 2.0, 0.0)
        time.sleep(0.3)

        # Call reset
        message = {
            "op": "call_service",
            "service": "/reset",
            "type": "std_srvs/srv/Empty",
            "args": {},
            "id": "reset_e2e",
        }

        with ws_manager:
            response = ws_manager.request(message, timeout=10.0)

        assert "error" not in response

        # Verify turtle is back at center
        time.sleep(0.5)
        pose = get_turtle_pose(ws_manager)
        assert pose is not None

        # Default turtlesim starting position is approximately (5.5, 5.5)
        assert 5.0 < pose["x"] < 6.0, f"x should be near center, got {pose['x']}"
        assert 5.0 < pose["y"] < 6.0, f"y should be near center, got {pose['y']}"


class TestCallSetPenService:
    """E2E tests for set_pen service."""

    def test_set_pen_color(self, ws_manager):
        """Verify set_pen service can be called to change pen settings."""
        message = {
            "op": "call_service",
            "service": "/turtle1/set_pen",
            "type": "turtlesim/srv/SetPen",
            "args": {
                "r": 255,
                "g": 0,
                "b": 0,
                "width": 3,
                "off": 0,
            },
            "id": "set_pen_e2e",
        }

        with ws_manager:
            response = ws_manager.request(message, timeout=10.0)

        # SetPen should succeed (empty response)
        assert "error" not in response, f"SetPen service should succeed: {response}"

    def test_set_pen_off(self, ws_manager):
        """Verify set_pen can disable drawing."""
        message = {
            "op": "call_service",
            "service": "/turtle1/set_pen",
            "type": "turtlesim/srv/SetPen",
            "args": {
                "r": 0,
                "g": 0,
                "b": 0,
                "width": 1,
                "off": 1,  # Disable pen
            },
            "id": "set_pen_off_e2e",
        }

        with ws_manager:
            response = ws_manager.request(message, timeout=10.0)

        assert "error" not in response


class TestServiceDetails:
    """E2E tests for getting service details."""

    def test_get_service_type(self, ws_manager):
        """Get service type for teleport_absolute."""
        message = {
            "op": "call_service",
            "service": "/rosapi/service_type",
            "type": "rosapi_msgs/srv/ServiceType",
            "args": {"service": "/turtle1/teleport_absolute"},
            "id": "get_service_type_e2e",
        }

        with ws_manager:
            response = ws_manager.request(message, timeout=10.0)

        assert "values" in response
        service_type = response["values"].get("type", "")
        assert "TeleportAbsolute" in service_type, f"Expected TeleportAbsolute, got {service_type}"
