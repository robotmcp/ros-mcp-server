"""Unit tests for parameters.get_parameters paths (no rosbridge)."""

from __future__ import annotations

import importlib.util
import sys
import types
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
_PARAMETERS_PATH = _ROOT / "ros_mcp" / "tools" / "parameters.py"


class FakeMCP:
    def __init__(self) -> None:
        self.tools: dict[str, object] = {}

    def tool(self, *args, **kwargs):
        def decorator(fn):
            self.tools[fn.__name__] = fn
            return fn

        return decorator


class FakeWsManager:
    def __init__(self, response=None, raise_exc: Exception | None = None) -> None:
        self._response = response
        self._raise = raise_exc
        self.calls: list = []

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def request(self, message):
        self.calls.append(message)
        if self._raise is not None:
            raise self._raise
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


def _load_parameters_module():
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
    response._extract_error = lambda r: "error"  # type: ignore[attr-defined]
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

    name = f"ros_mcp_tools_parameters_get_paths_ut_{id(object())}"
    if name in sys.modules:
        del sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, _PARAMETERS_PATH)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    tools.parameters = mod  # type: ignore[attr-defined]
    return mod


class TestGetParameters:
    def test_empty_name(self):
        mod = _load_parameters_module()
        mcp = FakeMCP()
        ws = FakeWsManager()
        mod.register_parameter_tools(mcp, ws)
        assert mcp.tools["get_parameters"]("") == {"error": "Node name cannot be empty"}
        assert mcp.tools["get_parameters"]("   ") == {"error": "Node name cannot be empty"}
        assert ws.calls == []

    def test_success_with_names(self):
        mod = _load_parameters_module()
        mcp = FakeMCP()
        ws = FakeWsManager(
            response={"values": {"result": {"names": ["background_r", "background_g"]}}}
        )
        mod.register_parameter_tools(mcp, ws)
        out = mcp.tools["get_parameters"]("/turtlesim")
        assert out["node"] == "/turtlesim"
        assert out["parameter_count"] == 2
        assert "/turtlesim:background_r" in out["parameters"]
        assert "/turtlesim:background_g" in out["parameters"]
        assert ws.calls[0]["service"] == "/turtlesim/list_parameters"

    def test_normalize_leading_slash(self):
        mod = _load_parameters_module()
        mcp = FakeMCP()
        ws = FakeWsManager(response={"values": {"result": {"names": []}}})
        mod.register_parameter_tools(mcp, ws)
        out = mcp.tools["get_parameters"]("turtlesim")
        assert out["node"] == "/turtlesim"
        assert ws.calls[0]["service"] == "/turtlesim/list_parameters"

    def test_trailing_slash_stripped(self):
        mod = _load_parameters_module()
        mcp = FakeMCP()
        ws = FakeWsManager(response={"values": {"result": {"names": ["p"]}}})
        mod.register_parameter_tools(mcp, ws)
        out = mcp.tools["get_parameters"]("/foo/")
        assert out["node"] == "/foo"
        assert out["parameters"] == ["/foo:p"]
        assert ws.calls[0]["service"] == "/foo/list_parameters"

    def test_timeout_none_response(self):
        mod = _load_parameters_module()
        mcp = FakeMCP()
        ws = FakeWsManager(response=None)
        mod.register_parameter_tools(mcp, ws)
        out = mcp.tools["get_parameters"]("/n")
        assert "No response or timeout" in out["error"]

    def test_exception_wrapped(self):
        mod = _load_parameters_module()
        mcp = FakeMCP()
        ws = FakeWsManager(raise_exc=RuntimeError("boom"))
        mod.register_parameter_tools(mcp, ws)
        out = mcp.tools["get_parameters"]("/n")
        assert "boom" in out["error"]
