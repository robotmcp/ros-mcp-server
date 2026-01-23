"""E2E test fixtures for ROS integration tests (ROS 1 and ROS 2)."""

import json
import os
import socket
import time

import pytest

from ros_mcp.utils.websocket import WebSocketManager


def pytest_addoption(parser):
    """Add command line options for ROS version selection."""
    parser.addoption(
        "--ros-version",
        action="store",
        default="2",
        choices=["1", "2"],
        help="ROS version to test against (1 or 2, default: 2)",
    )


def pytest_configure(config):
    """Configure custom markers."""
    config.addinivalue_line("markers", "e2e: End-to-end tests requiring ROS environment")
    config.addinivalue_line("markers", "ros1: Tests specific to ROS 1")
    config.addinivalue_line("markers", "ros2: Tests specific to ROS 2")


@pytest.fixture(scope="session")
def ros_version(request):
    """Return the ROS version being tested."""
    return request.config.getoption("--ros-version")


@pytest.fixture(scope="session")
def rosbridge_host():
    """Return rosbridge host."""
    return os.environ.get("ROSBRIDGE_HOST", "127.0.0.1")


@pytest.fixture(scope="session")
def rosbridge_port(ros_version):
    """Return rosbridge port based on ROS version."""
    if ros_version == "1":
        return int(os.environ.get("ROSBRIDGE_PORT", "9091"))
    return int(os.environ.get("ROSBRIDGE_PORT", "9090"))


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
def ws_manager_tiny_timeout(wait_for_rosbridge, rosbridge_host, rosbridge_port):
    """WebSocketManager with very short timeout for testing timeout behavior."""
    manager = WebSocketManager(rosbridge_host, rosbridge_port, default_timeout=0.5)
    yield manager
    manager.close()


@pytest.fixture
def invalid_ws_manager():
    """WebSocketManager with invalid host for error testing."""
    manager = WebSocketManager("192.0.2.1", 9090, default_timeout=1.0)  # TEST-NET-1 - guaranteed unreachable
    yield manager
    manager.close()


# ROS version-aware service types
@pytest.fixture
def service_type_empty(ros_version):
    """Return Empty service type based on ROS version."""
    if ros_version == "1":
        return "std_srvs/Empty"
    return "std_srvs/srv/Empty"


@pytest.fixture
def service_type_teleport(ros_version):
    """Return TeleportAbsolute service type based on ROS version."""
    if ros_version == "1":
        return "turtlesim/TeleportAbsolute"
    return "turtlesim/srv/TeleportAbsolute"


@pytest.fixture
def service_type_spawn(ros_version):
    """Return Spawn service type based on ROS version."""
    if ros_version == "1":
        return "turtlesim/Spawn"
    return "turtlesim/srv/Spawn"


@pytest.fixture
def service_type_kill(ros_version):
    """Return Kill service type based on ROS version."""
    if ros_version == "1":
        return "turtlesim/Kill"
    return "turtlesim/srv/Kill"


@pytest.fixture
def service_type_set_pen(ros_version):
    """Return SetPen service type based on ROS version."""
    if ros_version == "1":
        return "turtlesim/SetPen"
    return "turtlesim/srv/SetPen"


@pytest.fixture
def msg_type_twist(ros_version):
    """Return Twist message type based on ROS version."""
    if ros_version == "1":
        return "geometry_msgs/Twist"
    return "geometry_msgs/msg/Twist"


@pytest.fixture
def msg_type_pose(ros_version):
    """Return Pose message type based on ROS version."""
    if ros_version == "1":
        return "turtlesim/Pose"
    return "turtlesim/msg/Pose"


# rosapi service types
@pytest.fixture
def rosapi_services_type(ros_version):
    """Return rosapi Services type based on ROS version."""
    if ros_version == "1":
        return "rosapi/Services"
    return "rosapi_msgs/srv/Services"


@pytest.fixture
def rosapi_topics_type(ros_version):
    """Return rosapi Topics type based on ROS version."""
    # Same for both versions
    return "rosapi/Topics"


@pytest.fixture
def rosapi_nodes_type(ros_version):
    """Return rosapi Nodes type based on ROS version."""
    # Same for both versions
    return "rosapi/Nodes"


@pytest.fixture
def rosapi_node_details_type(ros_version):
    """Return rosapi NodeDetails type based on ROS version."""
    # Same for both versions
    return "rosapi/NodeDetails"


@pytest.fixture
def rosapi_topic_type_type(ros_version):
    """Return rosapi TopicType type based on ROS version."""
    # Same for both versions
    return "rosapi/TopicType"


@pytest.fixture
def rosapi_service_type_type(ros_version):
    """Return rosapi ServiceType type based on ROS version."""
    if ros_version == "1":
        return "rosapi/ServiceType"
    return "rosapi_msgs/srv/ServiceType"


@pytest.fixture
def rosapi_get_param_type(ros_version):
    """Return rosapi GetParam type based on ROS version."""
    if ros_version == "1":
        return "rosapi/GetParam"
    return "rosapi_msgs/srv/GetParam"


@pytest.fixture
def rosapi_set_param_type(ros_version):
    """Return rosapi SetParam type based on ROS version."""
    if ros_version == "1":
        return "rosapi/SetParam"
    return "rosapi_msgs/srv/SetParam"


@pytest.fixture
def rosapi_get_ros_version_type(ros_version):
    """Return rosapi GetROSVersion type based on ROS version."""
    if ros_version == "1":
        # ROS1 doesn't have this service, will skip tests that need it
        return None
    return "rosapi_msgs/srv/GetROSVersion"


@pytest.fixture
def turtlesim_topics():
    """Expected turtlesim topics (same for both ROS versions)."""
    return [
        "/turtle1/cmd_vel",
        "/turtle1/pose",
        "/turtle1/color_sensor",
    ]


@pytest.fixture
def turtlesim_services():
    """Expected turtlesim services (same for both ROS versions)."""
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
    """Expected turtlesim actions (ROS 2 only)."""
    return [
        "/turtle1/rotate_absolute",
    ]


def reset_turtle(ws_manager, service_type="std_srvs/srv/Empty"):
    """
    Helper function to reset turtle to center position.

    Args:
        ws_manager: WebSocketManager instance
        service_type: Service type string (ROS version dependent)
    """
    reset_msg = {
        "op": "call_service",
        "service": "/reset",
        "type": service_type,
        "args": {},
        "id": "reset_turtle",
    }

    with ws_manager:
        response = ws_manager.request(reset_msg, timeout=5.0)

    # Give time for reset to complete
    time.sleep(0.5)
    return response


def teleport_turtle(ws_manager, x: float, y: float, theta: float = 0.0,
                    service_type="turtlesim/srv/TeleportAbsolute"):
    """
    Helper function to teleport turtle to specific position.

    Args:
        ws_manager: WebSocketManager instance
        x: X coordinate (0.0 to 11.0)
        y: Y coordinate (0.0 to 11.0)
        theta: Orientation in radians
        service_type: Service type string (ROS version dependent)
    """
    teleport_msg = {
        "op": "call_service",
        "service": "/turtle1/teleport_absolute",
        "type": service_type,
        "args": {"x": x, "y": y, "theta": theta},
        "id": "teleport_turtle",
    }

    with ws_manager:
        response = ws_manager.request(teleport_msg, timeout=5.0)

    time.sleep(0.2)
    return response


def get_turtle_pose(ws_manager, timeout: float = 5.0, msg_type="turtlesim/msg/Pose"):
    """
    Helper function to get current turtle pose.

    Args:
        ws_manager: WebSocketManager instance
        timeout: Timeout in seconds
        msg_type: Message type string (ROS version dependent)

    Returns:
        dict with x, y, theta, linear_velocity, angular_velocity
    """
    subscribe_msg = {
        "op": "subscribe",
        "topic": "/turtle1/pose",
        "type": msg_type,
    }

    with ws_manager:
        ws_manager.send(subscribe_msg)

        end_time = time.time() + timeout
        while time.time() < end_time:
            response = ws_manager.receive(timeout=0.5)
            if response:
                data = json.loads(response)
                if data.get("op") == "publish" and data.get("topic") == "/turtle1/pose":
                    # Unsubscribe
                    ws_manager.send({"op": "unsubscribe", "topic": "/turtle1/pose"})
                    return data.get("msg", {})

    return None


@pytest.fixture
def reset_turtle_fixture(ws_manager, service_type_empty):
    """Fixture that resets turtle before each test."""
    reset_turtle(ws_manager, service_type_empty)
    yield
    # Optionally reset after test too
    reset_turtle(ws_manager, service_type_empty)


@pytest.fixture(scope="session")
def mcp_server(wait_for_rosbridge, rosbridge_host, rosbridge_port):
    """
    Full MCP server instance with all tools, resources, and prompts registered.

    This fixture provides access to the configured FastMCP server for testing
    registration of tools, resources, and prompts.
    """
    from fastmcp import FastMCP

    from ros_mcp.prompts import register_all_prompts
    from ros_mcp.resources import register_all_resources
    from ros_mcp.tools import register_all_tools
    from ros_mcp.utils.websocket import WebSocketManager as WsManager

    mcp = FastMCP("ros-mcp-server-test")
    ws = WsManager(rosbridge_host, rosbridge_port, default_timeout=10.0)

    register_all_tools(mcp, ws, rosbridge_ip=rosbridge_host, rosbridge_port=rosbridge_port)
    register_all_resources(mcp, ws)
    register_all_prompts(mcp)

    yield mcp
    ws.close()
