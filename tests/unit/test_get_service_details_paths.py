"""Unit tests for services.get_service_details paths (no rosbridge)."""

from __future__ import annotations

import importlib.util
import sys
import types
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
_SERVICES_PATH = _ROOT / "ros_mcp" / "tools" / "services.py"


class FakeMCP:
    def __init__(self) -> None:
        self.tools: dict[str, object] = {}

    def tool(self, *args, **kwargs):
        def decorator(fn):
            self.tools[fn.__name__] = fn
            return fn

        return decorator


class FakeWsManager:
    def __init__(self, responses=None, response=None) -> None:
        if responses is not None:
            self._queue = list(responses)
        else:
            self._queue = [response]
        self.calls: list = []
        self.default_timeout = 2.0

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def request(self, message, timeout=None):
        self.calls.append((message, timeout))
        if not self._queue:
            return {}
        return self._queue.pop(0)


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


def _load_services_module(safe_get_values, check_response=None):
    _ensure_stub("cv2")
    _ensure_stub("numpy")
    _ensure_stub("websocket")
    _ensure_stub("yaml")
    _ensure_stub("PIL")
    pil_image = _ensure_pkg("PIL.Image")
    pil_image.Image = object  # type: ignore[attr-defined]
    _ensure_stub("PIL").Image = pil_image  # type: ignore[attr-defined]

    fastmcp = _ensure_stub("fastmcp")
    fastmcp.FastMCP = object  # type: ignore[attr-defined]
    tools_tool = _ensure_pkg("fastmcp.tools.tool")

    class ToolResult:
        def __init__(self, **kwargs):
            self.__dict__.update(kwargs)

    tools_tool.ToolResult = ToolResult  # type: ignore[attr-defined]
    tools_pkg = _ensure_pkg("fastmcp.tools")
    tools_pkg.tool = tools_tool  # type: ignore[attr-defined]
    fastmcp.tools = tools_pkg  # type: ignore[attr-defined]

    mcp_types = _ensure_pkg("mcp.types")

    class ToolAnnotations:
        def __init__(self, **kwargs):
            self.__dict__.update(kwargs)

    class TextContent:
        def __init__(self, **kwargs):
            self.__dict__.update(kwargs)

    class ImageContent:
        def __init__(self, **kwargs):
            self.__dict__.update(kwargs)

    mcp_types.ToolAnnotations = ToolAnnotations  # type: ignore[attr-defined]
    mcp_types.TextContent = TextContent  # type: ignore[attr-defined]
    mcp_types.ImageContent = ImageContent  # type: ignore[attr-defined]
    _ensure_pkg("mcp").types = mcp_types  # type: ignore[attr-defined]

    _ensure_pkg("ros_mcp")
    tools = _ensure_pkg("ros_mcp.tools")
    utils = _ensure_pkg("ros_mcp.utils")

    response = types.ModuleType("ros_mcp.utils.response")
    response._check_response = check_response or (lambda _r: None)  # type: ignore[attr-defined]
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

    name = f"ros_mcp_tools_services_gsd_{id(safe_get_values)}_{id(check_response)}"
    if name in sys.modules:
        del sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, _SERVICES_PATH)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    tools.services = mod  # type: ignore[attr-defined]
    return mod


def _sgv_from_response(response):
    if not response or not isinstance(response, dict):
        return None
    values = response.get("values")
    return values if isinstance(values, dict) else None


class TestGetServiceDetails:
    def test_empty_name(self):
        mod = _load_services_module(lambda _r: None)
        mcp = FakeMCP()
        ws = FakeWsManager()
        mod.register_service_tools(mcp, ws)
        assert mcp.tools["get_service_details"]("") == {
            "error": "Service name cannot be empty"
        }
        assert mcp.tools["get_service_details"]("   ") == {
            "error": "Service name cannot be empty"
        }
        assert ws.calls == []

    def test_type_check_error(self):
        mod = _load_services_module(
            _sgv_from_response,
            check_response=lambda _r: {"error": "ws down"},
        )
        mcp = FakeMCP()
        ws = FakeWsManager(response={"ok": True})
        mod.register_service_tools(mcp, ws)
        assert mcp.tools["get_service_details"]("/foo") == {"error": "ws down"}

    def test_empty_type_string(self):
        mod = _load_services_module(_sgv_from_response)
        mcp = FakeMCP()
        ws = FakeWsManager(response={"values": {"type": ""}})
        mod.register_service_tools(mcp, ws)
        out = mcp.tools["get_service_details"]("/missing")
        assert "does not exist" in out["error"]

    def test_type_values_none(self):
        mod = _load_services_module(lambda _r: None)
        mcp = FakeMCP()
        ws = FakeWsManager(response={"ok": True})
        mod.register_service_tools(mcp, ws)
        out = mcp.tools["get_service_details"]("/x")
        assert "Failed to get type" in out["error"]

    def test_success_full(self):
        mod = _load_services_module(_sgv_from_response)
        mcp = FakeMCP()
        ws = FakeWsManager(
            responses=[
                {"values": {"type": "pkg/Srv"}},
                {"values": {"typedefs": [{"fieldnames": ["a"], "fieldtypes": ["int32"]}]}},
                {"values": {"typedefs": [{"fieldnames": ["b"], "fieldtypes": ["string"]}]}},
                {"values": {"node": "/provider"}},
            ]
        )
        mod.register_service_tools(mcp, ws)
        out = mcp.tools["get_service_details"]("/rosapi/topics")
        assert out["service"] == "/rosapi/topics"
        assert out["type"] == "pkg/Srv"
        assert out["request"]["fields"] == {"a": "int32"}
        assert out["response"]["fields"] == {"b": "string"}
        assert out["providers"] == ["/provider"]
        assert out["provider_count"] == 1
        assert "note" in out
        assert len(ws.calls) == 4

    def test_no_definition(self):
        mod = _load_services_module(_sgv_from_response)
        mcp = FakeMCP()
        ws = FakeWsManager(
            responses=[
                {"values": {"type": "pkg/Srv"}},
                {"values": {"typedefs": []}},
                {"values": {"typedefs": []}},
                {"values": {"node": ""}},
            ]
        )
        mod.register_service_tools(mcp, ws)
        out = mcp.tools["get_service_details"]("/empty_def")
        assert "no definition" in out["error"]
