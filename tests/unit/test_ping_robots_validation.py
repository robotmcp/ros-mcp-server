"""Unit tests for connection.ping_robots target validation (no real network)."""

from __future__ import annotations

import importlib.util
import sys
import types
from pathlib import Path
from typing import Any

import pytest

_ROOT = Path(__file__).resolve().parents[2]
_CONNECTION_PATH = _ROOT / "ros_mcp" / "tools" / "connection.py"


class FakeMCP:
    def __init__(self) -> None:
        self.tools: dict[str, object] = {}

    def tool(self, *args, **kwargs):
        def decorator(fn):
            self.tools[fn.__name__] = fn
            return fn

        return decorator


class FakeWsManager:
    """Connection tools accept ws_manager but ping_robots does not use it."""

    def set_ip(self, *args, **kwargs):
        raise AssertionError("set_ip should not run in ping_robots validation tests")


def _ensure_stub(name: str) -> types.ModuleType:
    if name in sys.modules:
        return sys.modules[name]
    try:
        return __import__(name)
    except ImportError:
        mod = types.ModuleType(name)
        sys.modules[name] = mod
        return mod


def _ensure_pkg(name: str) -> types.ModuleType:
    if name in sys.modules:
        return sys.modules[name]
    mod = types.ModuleType(name)
    mod.__path__ = []  # type: ignore[attr-defined]
    sys.modules[name] = mod
    return mod


def _load_connection_module(ping_impl):
    """Load connection.py with stubs; inject ping_impl for ping_ip_and_port."""
    _ensure_stub("cv2")
    _ensure_stub("numpy")
    _ensure_stub("websocket")
    _ensure_stub("yaml")

    fastmcp = _ensure_stub("fastmcp")
    fastmcp.FastMCP = object  # type: ignore[attr-defined]

    mcp_types = _ensure_pkg("mcp.types")

    class ToolAnnotations:
        def __init__(self, **kwargs):
            self.__dict__.update(kwargs)

    mcp_types.ToolAnnotations = ToolAnnotations  # type: ignore[attr-defined]
    _ensure_pkg("mcp").types = mcp_types  # type: ignore[attr-defined]

    _ensure_pkg("ros_mcp")
    tools = _ensure_pkg("ros_mcp.tools")
    utils = _ensure_pkg("ros_mcp.utils")

    network = types.ModuleType("ros_mcp.utils.network_utils")
    network.ping_ip_and_port = ping_impl  # type: ignore[attr-defined]
    sys.modules["ros_mcp.utils.network_utils"] = network
    utils.network_utils = network  # type: ignore[attr-defined]

    rosapi = types.ModuleType("ros_mcp.utils.rosapi_types")
    rosapi.detect_rosapi_types = lambda ws: None  # type: ignore[attr-defined]
    sys.modules["ros_mcp.utils.rosapi_types"] = rosapi
    utils.rosapi_types = rosapi  # type: ignore[attr-defined]

    websocket_mod = types.ModuleType("ros_mcp.utils.websocket")
    websocket_mod.WebSocketManager = object  # type: ignore[attr-defined]
    sys.modules["ros_mcp.utils.websocket"] = websocket_mod
    utils.websocket = websocket_mod  # type: ignore[attr-defined]

    # Unique module name so injects differ between tests if needed
    name = f"ros_mcp_tools_connection_ping_ut_{id(ping_impl)}"
    spec = importlib.util.spec_from_file_location(name, _CONNECTION_PATH)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    tools.connection = mod  # type: ignore[attr-defined]
    return mod


def _canned_ping(ip: str, port: int, ping_timeout: float = 2.0, port_timeout: float = 2.0) -> dict:
    return {
        "ip": ip,
        "port": port,
        "ping": {"success": True, "latency_ms": 1.0},
        "port_check": {"open": True},
        "overall_status": "reachable",
    }


@pytest.fixture
def ping_robots():
    calls: list[tuple[Any, ...]] = []

    def _tracked_ping(ip, port, ping_timeout=2.0, port_timeout=2.0):
        calls.append((ip, port, ping_timeout, port_timeout))
        return _canned_ping(ip, port, ping_timeout, port_timeout)

    mod = _load_connection_module(_tracked_ping)
    mcp = FakeMCP()
    mod.register_connection_tools(mcp, FakeWsManager(), default_ip="127.0.0.1", default_port=9090)
    assert "ping_robots" in mcp.tools
    tool = mcp.tools["ping_robots"]
    tool._calls = calls  # type: ignore[attr-defined]
    return tool


class TestPingRobotsValidation:
    def test_targets_not_list(self, ping_robots):
        result = ping_robots(targets={"ip": "1.2.3.4", "port": 9090})  # type: ignore[arg-type]
        assert result["error"] == "targets must be a list of dictionaries"
        assert result["results"] == []
        assert ping_robots._calls == []  # type: ignore[attr-defined]

    def test_targets_empty_list(self, ping_robots):
        result = ping_robots(targets=[])
        assert result["error"] == "targets list cannot be empty"
        assert result["results"] == []
        assert ping_robots._calls == []  # type: ignore[attr-defined]

    def test_non_dict_element(self, ping_robots):
        result = ping_robots(targets=["not-a-dict"])  # type: ignore[list-item]
        assert "error" not in result or result.get("error") is None
        assert len(result["results"]) == 1
        row = result["results"][0]
        assert row["error"] == "Target at index 0 is not a dictionary"
        assert row["overall_status"] == "Invalid target format"
        assert ping_robots._calls == []  # type: ignore[attr-defined]

    def test_missing_required_keys(self, ping_robots):
        result = ping_robots(targets=[{"ip": "10.0.0.1"}])
        row = result["results"][0]
        assert "missing required keys" in row["error"]
        assert row["ip"] == "10.0.0.1"
        assert row["port"] is None
        assert ping_robots._calls == []  # type: ignore[attr-defined]

    def test_ip_must_be_string(self, ping_robots):
        result = ping_robots(targets=[{"ip": 1921680101, "port": 9090}])  # type: ignore[list-item]
        row = result["results"][0]
        assert "'ip' must be a string" in row["error"]
        assert row["overall_status"] == "Invalid target format"
        assert ping_robots._calls == []  # type: ignore[attr-defined]

    def test_port_unconvertible(self, ping_robots):
        result = ping_robots(targets=[{"ip": "192.168.1.1", "port": "not-a-port"}])
        row = result["results"][0]
        assert "'port' must be an integer" in row["error"]
        assert ping_robots._calls == []  # type: ignore[attr-defined]

    def test_default_targets_none_calls_ping(self, ping_robots):
        result = ping_robots()
        assert "results" in result
        assert len(result["results"]) == 1
        assert result["results"][0]["ip"] == "127.0.0.1"
        assert result["results"][0]["port"] == 9090
        assert ping_robots._calls == [("127.0.0.1", 9090, 2.0, 2.0)]  # type: ignore[attr-defined]

    def test_string_port_converted(self, ping_robots):
        result = ping_robots(targets=[{"ip": "10.0.0.5", "port": "9091"}])
        assert len(result["results"]) == 1
        assert result["results"][0]["port"] == 9091
        assert ping_robots._calls == [("10.0.0.5", 9091, 2.0, 2.0)]  # type: ignore[attr-defined]

    def test_mixed_valid_and_invalid_preserves_order(self, ping_robots):
        result = ping_robots(
            targets=[
                {"ip": "1.1.1.1", "port": 1},
                "bad",  # type: ignore[list-item]
                {"ip": "2.2.2.2", "port": 2},
            ]
        )
        rows = result["results"]
        assert len(rows) == 3
        assert rows[0]["ip"] == "1.1.1.1"
        assert rows[1]["overall_status"] == "Invalid target format"
        assert rows[2]["ip"] == "2.2.2.2"
        assert ping_robots._calls == [  # type: ignore[attr-defined]
            ("1.1.1.1", 1, 2.0, 2.0),
            ("2.2.2.2", 2, 2.0, 2.0),
        ]
