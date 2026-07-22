"""Unit tests for nodes.get_nodes success / warning / error paths (no rosbridge)."""

from __future__ import annotations

import importlib.util
import sys
import types
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
_NODES_PATH = _ROOT / "ros_mcp" / "tools" / "nodes.py"


class FakeMCP:
    def __init__(self) -> None:
        self.tools: dict[str, object] = {}

    def tool(self, *args, **kwargs):
        def decorator(fn):
            self.tools[fn.__name__] = fn
            return fn

        return decorator


class FakeWsManager:
    def __init__(self) -> None:
        self._response = None
        self.last_message = None

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def request(self, message):
        self.last_message = message
        return self._response


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


def _load_nodes_module(check_response, safe_get_values):
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

    response = types.ModuleType("ros_mcp.utils.response")
    response._check_response = check_response  # type: ignore[attr-defined]
    response._safe_get_values = safe_get_values  # type: ignore[attr-defined]
    sys.modules["ros_mcp.utils.response"] = response
    utils.response = response  # type: ignore[attr-defined]

    rosapi = types.ModuleType("ros_mcp.utils.rosapi_types")
    rosapi.rosapi_service = lambda n: f"/rosapi/{n}"  # type: ignore[attr-defined]
    rosapi.rosapi_type = lambda n: f"rosapi/{n}"  # type: ignore[attr-defined]
    sys.modules["ros_mcp.utils.rosapi_types"] = rosapi
    utils.rosapi_types = rosapi  # type: ignore[attr-defined]

    websocket_mod = types.ModuleType("ros_mcp.utils.websocket")
    websocket_mod.WebSocketManager = object  # type: ignore[attr-defined]
    sys.modules["ros_mcp.utils.websocket"] = websocket_mod
    utils.websocket = websocket_mod  # type: ignore[attr-defined]

    name = f"ros_mcp_tools_nodes_get_nodes_ut_{id(check_response)}"
    if name in sys.modules:
        del sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, _NODES_PATH)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    tools.nodes = mod  # type: ignore[attr-defined]
    return mod


class TestGetNodes:
    def test_success_with_nodes(self):
        def check(_r):
            return None

        def values(_r):
            return {"nodes": ["/a", "/b"]}

        mod = _load_nodes_module(check, values)
        ws = FakeWsManager()
        ws._response = {"ok": True}
        mcp = FakeMCP()
        mod.register_node_tools(mcp, ws)
        result = mcp.tools["get_nodes"]()
        assert result == {"nodes": ["/a", "/b"], "node_count": 2}
        assert ws.last_message is not None
        assert ws.last_message["op"] == "call_service"
        assert "nodes" in ws.last_message["service"]

    def test_warning_when_values_missing(self):
        def check(_r):
            return None

        def values(_r):
            return None

        mod = _load_nodes_module(check, values)
        ws = FakeWsManager()
        ws._response = {"values": None}
        mcp = FakeMCP()
        mod.register_node_tools(mcp, ws)
        assert mcp.tools["get_nodes"]() == {"warning": "No nodes found"}

    def test_error_from_check_response(self):
        def check(_r):
            return {"error": "rosbridge down"}

        def values(_r):
            raise AssertionError("values should not be called after check error")

        mod = _load_nodes_module(check, values)
        ws = FakeWsManager()
        ws._response = {"status": "error"}
        mcp = FakeMCP()
        mod.register_node_tools(mcp, ws)
        assert mcp.tools["get_nodes"]() == {"error": "rosbridge down"}

    def test_empty_nodes_list_still_success(self):
        def check(_r):
            return None

        def values(_r):
            return {"nodes": []}

        mod = _load_nodes_module(check, values)
        ws = FakeWsManager()
        mcp = FakeMCP()
        mod.register_node_tools(mcp, ws)
        assert mcp.tools["get_nodes"]() == {"nodes": [], "node_count": 0}
