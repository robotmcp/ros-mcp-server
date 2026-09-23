"""Unit tests for get_actions and call_service paths (no rosbridge)."""

from __future__ import annotations

import importlib.util
import sys
import types
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
_ACTIONS_PATH = _ROOT / "ros_mcp" / "tools" / "actions.py"
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
    def __init__(self, response=None) -> None:
        self._response = response
        self.calls: list = []
        self.default_timeout = 2.0

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def request(self, message, timeout=None):
        self.calls.append((message, timeout))
        return self._response

    def send(self, message):
        self.calls.append(("send", message))
        return None


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


def _bootstrap_common():
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

    class Context:
        pass

    fastmcp.Context = Context  # type: ignore[attr-defined]
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
    _ensure_pkg("ros_mcp.tools")
    return _ensure_pkg("ros_mcp.utils")


def _wire_utils(utils, safe_get_values, check_response=None):
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


def _load_actions_module(safe_get_values, check_response=None):
    utils = _bootstrap_common()
    _wire_utils(utils, safe_get_values, check_response)
    name = f"ros_mcp_tools_actions_ut_{id(safe_get_values)}_{id(check_response)}"
    if name in sys.modules:
        del sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, _ACTIONS_PATH)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def _load_services_module(safe_get_values, check_response=None):
    utils = _bootstrap_common()
    _wire_utils(utils, safe_get_values, check_response)
    name = f"ros_mcp_tools_services_cs_{id(safe_get_values)}_{id(check_response)}"
    if name in sys.modules:
        del sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, _SERVICES_PATH)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


class TestGetActions:
    def test_success_list(self):
        mod = _load_actions_module(
            lambda _r: {"action_servers": ["/a", "/b"]}
        )
        mcp = FakeMCP()
        ws = FakeWsManager(response={"ok": True})
        mod.register_action_tools(mcp, ws)
        out = mcp.tools["get_actions"]()
        assert out == {"actions": ["/a", "/b"], "action_count": 2}
        msg = ws.calls[0][0]
        assert msg["service"] == "/rosapi/action_servers"
        assert msg["type"] == "rosapi/ActionServers"

    def test_values_none_warning(self):
        mod = _load_actions_module(lambda _r: None)
        mcp = FakeMCP()
        ws = FakeWsManager(response={"ok": True})
        mod.register_action_tools(mcp, ws)
        assert mcp.tools["get_actions"]() == {"warning": "No actions found"}

    def test_check_response_error(self):
        mod = _load_actions_module(
            lambda _r: {"action_servers": []},
            check_response=lambda _r: {"error": "boom"},
        )
        mcp = FakeMCP()
        ws = FakeWsManager(response={"ok": True})
        mod.register_action_tools(mcp, ws)
        assert mcp.tools["get_actions"]() == {"error": "boom"}


class TestCallService:
    def test_service_response_success_and_default_timeout(self):
        mod = _load_services_module(lambda _r: None)
        mcp = FakeMCP()
        ws = FakeWsManager(
            response={"op": "service_response", "result": True, "values": {"ok": 1}}
        )
        ws.default_timeout = 7.5
        mod.register_service_tools(mcp, ws)
        out = mcp.tools["call_service"]("/s", "t/S", {"x": 1}, timeout=None)
        assert out["success"] is True
        assert out["result"] == {"ok": 1}
        assert out["service"] == "/s"
        assert out["service_type"] == "t/S"
        assert ws.calls[0][1] == 7.5

    def test_status_error(self):
        mod = _load_services_module(lambda _r: None)
        mcp = FakeMCP()
        ws = FakeWsManager(
            response={"op": "status", "level": "error", "msg": "bad"}
        )
        mod.register_service_tools(mcp, ws)
        out = mcp.tools["call_service"]("/s", "t/S", {})
        assert out["success"] is False
        assert out["error"] == "bad"

    def test_unexpected_format(self):
        mod = _load_services_module(lambda _r: None)
        mcp = FakeMCP()
        ws = FakeWsManager(response={"op": "other"})
        mod.register_service_tools(mcp, ws)
        out = mcp.tools["call_service"]("/s", "t/S", {})
        assert out["success"] is False
        assert "Unexpected" in out["error"]
        assert out["raw_response"] == {"op": "other"}

    def test_check_response_error(self):
        mod = _load_services_module(
            lambda _r: None,
            check_response=lambda _r: {"error": "ws failed"},
        )
        mcp = FakeMCP()
        ws = FakeWsManager(response={})
        mod.register_service_tools(mcp, ws)
        out = mcp.tools["call_service"]("/s", "t/S", {})
        assert out["success"] is False
        assert out["error"] == "ws failed"
        assert out["service"] == "/s"
