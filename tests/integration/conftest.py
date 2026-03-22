"""Integration test fixtures: Docker lifecycle and WebSocket access."""

import os
import socket
import subprocess
import time
import warnings
from pathlib import Path

import pytest
from fastmcp import FastMCP

from ros_mcp.tools import register_all_tools
from ros_mcp.utils.rosapi_types import detect_rosapi_types
from ros_mcp.utils.websocket import WebSocketManager

COMPOSE_DIR = Path(__file__).parent
ROSBRIDGE_PORT = 9090

_DOCKERFILE_MAP = {
    "melodic": "Dockerfile.ros1-melodic",
    "noetic": "Dockerfile.ros1-noetic",
    "humble": "Dockerfile.ros2-humble",
    "jazzy": "Dockerfile.ros2-jazzy",
}

_CONTAINER_NAME_MAP = {
    "melodic": "integration-ros-melodic",
    "noetic": "integration-ros-noetic",
    "humble": "integration-ros2-humble",
    "jazzy": "integration-ros2-jazzy",
}


def docker_available() -> bool:
    try:
        result = subprocess.run(["docker", "info"], capture_output=True, timeout=10)
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def _wait_for_rosbridge(port: int = ROSBRIDGE_PORT, timeout: float = 30) -> None:
    """Poll rosbridge TCP port with a raw socket probe."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=2):
                return
        except OSError:
            time.sleep(1)
    raise TimeoutError(f"Rosbridge not ready after {timeout}s on port {port}")


def pytest_addoption(parser):
    parser.addoption(
        "--ros-distro",
        default="humble",
        choices=list(_DOCKERFILE_MAP.keys()),
        help="ROS distro to test against (default: humble)",
    )
    parser.addoption(
        "--skip-compose",
        action="store_true",
        default=False,
        help="Skip Docker compose up/down — assume container is already running",
    )


def pytest_configure(config):
    config.addinivalue_line("markers", "integration: integration tests requiring Docker + ROS")


@pytest.fixture(scope="session", autouse=True)
def require_docker():
    if not docker_available():
        pytest.skip("Docker is not available")


@pytest.fixture(scope="session")
def ros_distro(request):
    """The selected ROS distro name."""
    return request.config.getoption("--ros-distro")


@pytest.fixture(scope="session")
def compose_up(require_docker, ros_distro, request):
    """Start docker-compose with the selected ROS distro, yield, then tear down.

    If --skip-compose is set, assume the container is already running externally.
    """
    if request.config.getoption("--skip-compose"):
        yield
        return

    dockerfile = _DOCKERFILE_MAP[ros_distro]
    container_name = _CONTAINER_NAME_MAP[ros_distro]
    compose_file = str(COMPOSE_DIR / "docker-compose.yml")
    env = {**os.environ, "ROS_DOCKERFILE": dockerfile, "ROS_CONTAINER_NAME": container_name}
    try:
        result = subprocess.run(
            ["docker", "compose", "-f", compose_file, "up", "--build", "-d", "--wait"],
            timeout=300,
            capture_output=True,
            env=env,
        )
        if result.returncode != 0:
            stderr = result.stderr.decode() if result.stderr else "(no output)"
            pytest.fail(f"docker compose up failed (exit {result.returncode}):\n{stderr}")
        yield
    finally:
        down = subprocess.run(
            ["docker", "compose", "-f", compose_file, "down", "--volumes", "--remove-orphans"],
            timeout=60,
            capture_output=True,
            env=env,
        )
        if down.returncode != 0:
            warnings.warn(f"docker compose down failed (exit {down.returncode})")


@pytest.fixture(scope="session")
def ws(compose_up):
    """WebSocketManager connected to the rosbridge container, with version detected."""
    ws_manager = WebSocketManager("127.0.0.1", ROSBRIDGE_PORT, default_timeout=5.0)
    _wait_for_rosbridge(ROSBRIDGE_PORT, timeout=30)
    detect_rosapi_types(ws_manager)
    return ws_manager


@pytest.fixture(scope="session")
def tools(ws):
    """MCP tool functions registered against the live ws_manager.

    Returns a dict mapping tool name to its callable, e.g.:
        tools["connect_to_robot"]() → dict
        tools["get_nodes"]() → dict
    """
    mcp = FastMCP("test-ros-mcp")
    register_all_tools(mcp, ws, rosbridge_ip="127.0.0.1", rosbridge_port=ROSBRIDGE_PORT)
    return {name: tool.fn for name, tool in mcp._tool_manager._tools.items()}
