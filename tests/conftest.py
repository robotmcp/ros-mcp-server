"""Shared test fixtures for ROS MCP Server tests.

IMPORTANT: These tests must be run using the project's virtual environment
to ensure all dependencies are available:

    source .venv/bin/activate
    pytest tests/utils tests/tools -v

Or directly:

    .venv/bin/pytest tests/utils tests/tools -v
"""

import json
from unittest.mock import patch

import pytest


class MockWebSocket:
    """Mock WebSocket connection for testing."""

    def __init__(self):
        self.connected = False
        self.sent_messages = []
        self.receive_queue = []
        self._timeout = 2.0

    def send(self, message: str):
        """Record sent messages."""
        self.sent_messages.append(message)

    def recv(self) -> str:
        """Return next message from receive queue."""
        if self.receive_queue:
            return self.receive_queue.pop(0)
        raise TimeoutError("No message available")

    def settimeout(self, timeout: float):
        """Set receive timeout."""
        self._timeout = timeout

    def close(self):
        """Close the connection."""
        self.connected = False


class MockWebSocketManager:
    """Mock WebSocketManager for testing tools without real WebSocket connection."""

    def __init__(self, ip: str = "127.0.0.1", port: int = 9090, default_timeout: float = 2.0):
        self.ip = ip
        self.port = port
        self.default_timeout = default_timeout
        self.ws = None
        self._responses = []
        self._request_history = []
        self._connected = False

    def set_ip(self, ip: str, port: int):
        """Set the IP and port for the WebSocket connection."""
        self.ip = ip
        self.port = port

    def connect(self) -> str | None:
        """Mock connection - always succeeds unless configured otherwise."""
        self._connected = True
        return None

    def send(self, message: dict) -> str | None:
        """Record sent message and return success."""
        self._request_history.append(message)
        return None

    def receive(self, timeout: float | None = None) -> str | None:
        """Return next configured response."""
        if self._responses:
            response = self._responses.pop(0)
            if isinstance(response, dict):
                return json.dumps(response)
            return response
        return None

    def request(self, message: dict, timeout: float | None = None) -> dict:
        """Send request and return configured response."""
        self._request_history.append(message)
        if self._responses:
            response = self._responses.pop(0)
            if isinstance(response, str):
                try:
                    return json.loads(response)
                except json.JSONDecodeError:
                    return {"error": "invalid_json", "raw": response}
            return response
        return {"error": "no response configured"}

    def close(self):
        """Close mock connection."""
        self._connected = False

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()

    # Test helper methods
    def add_response(self, response: dict | str):
        """Add a response to be returned by receive() or request()."""
        self._responses.append(response)

    def add_responses(self, responses: list):
        """Add multiple responses."""
        self._responses.extend(responses)

    def get_request_history(self) -> list:
        """Get all requests that were sent."""
        return self._request_history

    def clear(self):
        """Clear responses and request history."""
        self._responses = []
        self._request_history = []


@pytest.fixture
def mock_ws_manager():
    """Create a MockWebSocketManager instance."""
    return MockWebSocketManager()


@pytest.fixture
def mock_ws_with_response():
    """Factory fixture to create MockWebSocketManager with pre-configured responses."""

    def _create(responses: list[dict | str] | None = None):
        manager = MockWebSocketManager()
        if responses:
            manager.add_responses(responses)
        return manager

    return _create


@pytest.fixture
def sample_topics_response():
    """Sample response from /rosapi/topics service."""
    return {
        "result": True,
        "values": {
            "topics": [
                "/turtle1/cmd_vel",
                "/turtle1/pose",
                "/rosout",
                "/parameter_events",
                "/turtle1/color_sensor",
            ],
            "types": [
                "geometry_msgs/msg/Twist",
                "turtlesim/msg/Pose",
                "rcl_interfaces/msg/Log",
                "rcl_interfaces/msg/ParameterEvent",
                "turtlesim/msg/Color",
            ],
        },
    }


@pytest.fixture
def sample_services_response():
    """Sample response from /rosapi/services service."""
    return {
        "result": True,
        "values": {
            "services": [
                "/turtle1/teleport_absolute",
                "/turtle1/teleport_relative",
                "/turtle1/set_pen",
                "/spawn",
                "/kill",
                "/clear",
                "/reset",
                "/rosapi/topics",
                "/rosapi/services",
            ]
        },
    }


@pytest.fixture
def sample_actions_response():
    """Sample response from /rosapi/action_servers service."""
    return {
        "result": True,
        "values": {"action_servers": ["/turtle1/rotate_absolute"]},
    }


@pytest.fixture
def sample_nodes_response():
    """Sample response from /rosapi/nodes service."""
    return {
        "result": True,
        "values": {"nodes": ["/turtlesim", "/rosbridge_websocket", "/rosapi"]},
    }


@pytest.fixture
def sample_pose_message():
    """Sample turtlesim pose message."""
    return {
        "op": "publish",
        "topic": "/turtle1/pose",
        "msg": {
            "x": 5.544444561004639,
            "y": 5.544444561004639,
            "theta": 0.0,
            "linear_velocity": 0.0,
            "angular_velocity": 0.0,
        },
    }


@pytest.fixture
def sample_twist_message():
    """Sample Twist message for cmd_vel."""
    return {
        "linear": {"x": 1.0, "y": 0.0, "z": 0.0},
        "angular": {"x": 0.0, "y": 0.0, "z": 0.5},
    }


@pytest.fixture
def sample_image_message():
    """Sample compressed image message."""
    return {
        "op": "publish",
        "topic": "/camera/image_compressed",
        "msg": {
            "format": "jpeg",
            "data": "/9j/4AAQSkZJRg==",  # Truncated base64 for testing
        },
    }


@pytest.fixture
def sample_raw_image_message():
    """Sample raw image message with RGB8 encoding."""
    # 2x2 RGB8 image (12 bytes)
    import base64

    image_data = bytes([255, 0, 0, 0, 255, 0, 0, 0, 255, 255, 255, 255])
    return {
        "op": "publish",
        "topic": "/camera/image_raw",
        "msg": {
            "width": 2,
            "height": 2,
            "encoding": "rgb8",
            "is_bigendian": 0,
            "step": 6,
            "data": base64.b64encode(image_data).decode("utf-8"),
        },
    }


@pytest.fixture
def sample_service_response():
    """Sample successful service call response."""
    return {
        "op": "service_response",
        "result": True,
        "service": "/turtle1/teleport_absolute",
        "values": {},
    }


@pytest.fixture
def sample_error_response():
    """Sample error response from rosbridge."""
    return {
        "op": "status",
        "level": "error",
        "msg": "Service call failed: service not available",
    }


@pytest.fixture
def temp_robot_specs(tmp_path):
    """Create temporary robot specification files for testing."""
    specs_dir = tmp_path / "robot_specifications"
    specs_dir.mkdir()

    # Create a valid robot spec
    valid_spec = specs_dir / "test_robot.yaml"
    valid_spec.write_text(
        """type: quadruped
prompts: |
  This is a test robot.
  It has 4 legs.
"""
    )

    # Create an empty spec
    empty_spec = specs_dir / "empty_robot.yaml"
    empty_spec.write_text("")

    # Create a spec with missing fields
    incomplete_spec = specs_dir / "incomplete_robot.yaml"
    incomplete_spec.write_text("type: mobile_robot\n")

    return specs_dir


@pytest.fixture
def mock_ping_success():
    """Mock successful ping result."""
    return {
        "ip": "127.0.0.1",
        "port": 9090,
        "ping": {"success": True, "error": None, "response_time_ms": 0.5},
        "port_check": {"open": True, "error": None},
        "overall_status": "Fully_accessible. The robot is reachable and the port is open, indicating that we are likely able to connect to ROS",
    }


@pytest.fixture
def mock_ping_port_closed():
    """Mock ping result with closed port."""
    return {
        "ip": "127.0.0.1",
        "port": 9090,
        "ping": {"success": True, "error": None, "response_time_ms": 0.5},
        "port_check": {
            "open": False,
            "error": "Port 9090 is closed or unreachable (error code: 111)",
        },
        "overall_status": "IP_reachable_port_closed. The robot is reachable but ROS_bridge is unreachable. Check if ROS_bridge is running as well as firewall settings.",
    }


@pytest.fixture
def mock_ping_unreachable():
    """Mock ping result for unreachable IP."""
    return {
        "ip": "192.168.1.200",
        "port": 9090,
        "ping": {
            "success": False,
            "error": "Ping failed with return code 1",
            "response_time_ms": None,
        },
        "port_check": {"open": False, "error": "Port 9090 connection timeout after 2.0 seconds"},
        "overall_status": "IP_unreachable. Check if the IP address is correct, the robot is powered on & connected to the network. Also check network and firewall settings.",
    }


# Patch helpers for tools that use the actual WebSocketManager
@pytest.fixture
def patch_websocket_manager():
    """Fixture to patch WebSocketManager in tools."""

    def _patch(module_path: str, mock_manager: MockWebSocketManager):
        return patch(f"{module_path}.WebSocketManager", return_value=mock_manager)

    return _patch
