"""Integration test fixtures: Docker lifecycle and MCP tool access."""

import subprocess
import time
from pathlib import Path

import pytest
from fastmcp import FastMCP

from ros_mcp.tools import register_all_tools
from ros_mcp.utils.rosapi_types import detect_rosapi_types
from ros_mcp.utils.websocket import WebSocketManager

COMPOSE_DIR = Path(__file__).parent
ROSBRIDGE_PORT = 9090


def docker_available() -> bool:
    """Check if Docker is available and running."""
    try:
        result = subprocess.run(
            ["docker", "info"],
            capture_output=True,
            timeout=10,
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def _wait_for_rosbridge(ws: WebSocketManager, timeout: float = 30) -> None:
    """Poll rosbridge websocket until it accepts connections."""
    deadline = time.time() + timeout
    last_error = None
    while time.time() < deadline:
        try:
            ws.connect()
            ws.close()
            return
        except Exception as e:
            last_error = e
            time.sleep(1)
    raise TimeoutError(
        f"Rosbridge not ready after {timeout}s on port {ROSBRIDGE_PORT}: {last_error}"
    )


def pytest_configure(config):
    config.addinivalue_line("markers", "integration: integration tests requiring Docker + ROS")


@pytest.fixture(scope="session", autouse=True)
def require_docker():
    """Skip all integration tests if Docker is not available."""
    if not docker_available():
        pytest.skip("Docker is not available")


@pytest.fixture(scope="session")
def compose_up(require_docker):
    """Start docker-compose, wait for healthchecks, yield, then tear down."""
    compose_file = str(COMPOSE_DIR / "docker-compose.yml")
    try:
        subprocess.run(
            ["docker", "compose", "-f", compose_file, "up", "--build", "-d", "--wait"],
            check=True,
            timeout=300,
            capture_output=True,
        )
        yield
    finally:
        subprocess.run(
            ["docker", "compose", "-f", compose_file, "down", "--volumes", "--remove-orphans"],
            timeout=60,
            capture_output=True,
        )


@pytest.fixture(scope="session")
def ws(compose_up):
    """WebSocketManager connected to the ROS2 rosbridge container."""
    ws_manager = WebSocketManager("127.0.0.1", ROSBRIDGE_PORT, default_timeout=5.0)
    _wait_for_rosbridge(ws_manager, timeout=30)
    detect_rosapi_types(ws_manager)
    return ws_manager


@pytest.fixture(scope="session")
def tools(ws):
    """All MCP tools registered against the Docker rosbridge, as a name->callable dict."""
    mcp = FastMCP("integration-test")
    register_all_tools(mcp, ws, "127.0.0.1", ROSBRIDGE_PORT)
    return {name: tool.fn for name, tool in mcp._tool_manager._tools.items()}
