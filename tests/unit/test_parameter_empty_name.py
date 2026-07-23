"""Unit tests for parameters.* empty-name validation (no rosbridge)."""

from __future__ import annotations

import importlib.util
import sys
import types
from pathlib import Path

import pytest

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
    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def request(self, message):
        raise AssertionError(f"ws.request should not be called for empty name; got {message!r}")


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

    spec = importlib.util.spec_from_file_location(
        "ros_mcp_tools_parameters_empty_ut", _PARAMETERS_PATH
    )
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    tools.parameters = mod  # type: ignore[attr-defined]
    return mod


@pytest.fixture(scope="module")
def parameter_tools():
    mod = _load_parameters_module()
    mcp = FakeMCP()
    mod.register_parameter_tools(mcp, FakeWsManager())
    for name in (
        "get_parameter",
        "set_parameter",
        "has_parameter",
        "delete_parameter",
        "get_parameters",
    ):
        assert name in mcp.tools
    return mcp.tools


class TestGetParameterEmptyName:
    def test_empty_string(self, parameter_tools):
        result = parameter_tools["get_parameter"]("")
        assert result == {"error": "Parameter name cannot be empty"}

    def test_whitespace_only(self, parameter_tools):
        result = parameter_tools["get_parameter"]("  ")
        assert result == {"error": "Parameter name cannot be empty"}


class TestSetParameterEmptyName:
    def test_empty_string(self, parameter_tools):
        result = parameter_tools["set_parameter"]("", "1")
        assert result == {"error": "Parameter name cannot be empty"}

    def test_whitespace_only(self, parameter_tools):
        result = parameter_tools["set_parameter"]("\t", "1")
        assert result == {"error": "Parameter name cannot be empty"}


class TestHasParameterEmptyName:
    def test_empty_string(self, parameter_tools):
        result = parameter_tools["has_parameter"]("")
        assert result == {"error": "Parameter name cannot be empty"}

    def test_tab_whitespace(self, parameter_tools):
        result = parameter_tools["has_parameter"]("\t")
        assert result == {"error": "Parameter name cannot be empty"}


class TestDeleteParameterEmptyName:
    def test_empty_string(self, parameter_tools):
        result = parameter_tools["delete_parameter"]("")
        assert result == {"error": "Parameter name cannot be empty"}


class TestGetParametersEmptyNodeName:
    def test_empty_string(self, parameter_tools):
        result = parameter_tools["get_parameters"]("")
        assert result == {"error": "Node name cannot be empty"}

    def test_whitespace_only(self, parameter_tools):
        result = parameter_tools["get_parameters"]("   ")
        assert result == {"error": "Node name cannot be empty"}
