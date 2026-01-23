"""E2E test fixtures for ROS 2 integration tests."""

import socket
import time

import pytest

from ros_mcp.utils.websocket import WebSocketManager


@pytest.fixture(scope="session")
def rosbridge_host():
    """Return rosbridge host."""
    return "127.0.0.1"


@pytest.fixture(scope="session")
def rosbridge_port():
    """Return rosbridge port."""
    return 9090


@pytest.fixture(scope="session")
def rosbridge_url(rosbridge_host, rosbridge_port):
    """Return rosbridge WebSocket URL."""
    return f"ws://{rosbridge_host}:{rosbridge_port}"


@pytest.fixture(scope="session")
def wait_for_rosbridge(rosbridge_host, rosbridge_port):
    """
    Wait for rosbridge to be ready (max 60s).

    This fixture blocks until rosbridge is accepting connections.
    """
    max_wait = 60
    for i in range(max_wait):
        try:
            sock = socket.create_connection((rosbridge_host, rosbridge_port), timeout=1)
            sock.close()
            # Extra buffer for ROS to fully initialize
            time.sleep(3)
            return True
        except (socket.error, ConnectionRefusedError, OSError):
            time.sleep(1)

    pytest.fail(f"rosbridge not available at {rosbridge_host}:{rosbridge_port} after {max_wait}s")


@pytest.fixture
def ws_manager(wait_for_rosbridge, rosbridge_host, rosbridge_port):
    """
    Real WebSocketManager connected to Docker rosbridge.

    This fixture provides a fresh WebSocketManager for each test.
    The connection is automatically closed after the test.
    """
    manager = WebSocketManager(rosbridge_host, rosbridge_port, default_timeout=10.0)
    yield manager
    manager.close()


@pytest.fixture
def ws_manager_short_timeout(wait_for_rosbridge, rosbridge_host, rosbridge_port):
    """WebSocketManager with shorter timeout for faster test failures."""
    manager = WebSocketManager(rosbridge_host, rosbridge_port, default_timeout=5.0)
    yield manager
    manager.close()


@pytest.fixture
def turtlesim_topics():
    """Expected turtlesim topics."""
    return [
        "/turtle1/cmd_vel",
        "/turtle1/pose",
        "/turtle1/color_sensor",
    ]


@pytest.fixture
def turtlesim_services():
    """Expected turtlesim services."""
    return [
        "/turtle1/teleport_absolute",
        "/turtle1/teleport_relative",
        "/turtle1/set_pen",
        "/spawn",
        "/kill",
        "/clear",
        "/reset",
    ]


@pytest.fixture
def turtlesim_actions():
    """Expected turtlesim actions."""
    return [
        "/turtle1/rotate_absolute",
    ]


def reset_turtle(ws_manager):
    """
    Helper function to reset turtle to center position.

    Call this at the start of tests that modify turtle state.
    """
    reset_msg = {
        "op": "call_service",
        "service": "/reset",
        "type": "std_srvs/srv/Empty",
        "args": {},
        "id": "reset_turtle",
    }

    with ws_manager:
        response = ws_manager.request(reset_msg, timeout=5.0)

    # Give time for reset to complete
    time.sleep(0.5)
    return response


def teleport_turtle(ws_manager, x: float, y: float, theta: float = 0.0):
    """
    Helper function to teleport turtle to specific position.

    Args:
        ws_manager: WebSocketManager instance
        x: X coordinate (0.0 to 11.0)
        y: Y coordinate (0.0 to 11.0)
        theta: Orientation in radians
    """
    teleport_msg = {
        "op": "call_service",
        "service": "/turtle1/teleport_absolute",
        "type": "turtlesim/srv/TeleportAbsolute",
        "args": {"x": x, "y": y, "theta": theta},
        "id": "teleport_turtle",
    }

    with ws_manager:
        response = ws_manager.request(teleport_msg, timeout=5.0)

    time.sleep(0.2)
    return response


def get_turtle_pose(ws_manager, timeout: float = 5.0):
    """
    Helper function to get current turtle pose.

    Returns:
        dict with x, y, theta, linear_velocity, angular_velocity
    """
    subscribe_msg = {
        "op": "subscribe",
        "topic": "/turtle1/pose",
        "type": "turtlesim/msg/Pose",
    }

    with ws_manager:
        ws_manager.send(subscribe_msg)

        end_time = time.time() + timeout
        while time.time() < end_time:
            response = ws_manager.receive(timeout=0.5)
            if response:
                import json
                data = json.loads(response)
                if data.get("op") == "publish" and data.get("topic") == "/turtle1/pose":
                    # Unsubscribe
                    ws_manager.send({"op": "unsubscribe", "topic": "/turtle1/pose"})
                    return data.get("msg", {})

    return None


@pytest.fixture
def reset_turtle_fixture(ws_manager):
    """Fixture that resets turtle before each test."""
    reset_turtle(ws_manager)
    yield
    # Optionally reset after test too
    reset_turtle(ws_manager)
