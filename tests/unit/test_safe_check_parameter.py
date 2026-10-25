"""Unit tests for parameters._safe_check_parameter_exists edge paths.

Offline FakeWs — no live rosapi. Covers empty/null/quoted-empty YAML-ish values
and exception paths that previously lacked unit coverage.
"""

from __future__ import annotations

import importlib.util
import sys
import types
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[2]
_PARAMETERS_PATH = _ROOT / "ros_mcp" / "tools" / "parameters.py"


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


class FakeWsManager:
    def __init__(self, response=None, error: Exception | None = None):
        self._response = response
        self._error = error
        self.messages = []

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def request(self, message):
        self.messages.append(message)
        if self._error is not None:
            raise self._error
        return self._response


def _load_parameters_module():
    _ensure_stub("cv2")
    _ensure_stub("numpy")
    _ensure_stub("websocket")
    _ensure_stub("yaml")

    fastmcp = _ensure_stub("fastmcp")
    fastmcp.FastMCP = object  # type: ignore[attr-defined]
    mcp_types = _ensure_pkg("mcp.types")
    mcp_types.ToolAnnotations = object  # type: ignore[attr-defined]
    _ensure_pkg("mcp").types = mcp_types  # type: ignore[attr-defined]

    _ensure_pkg("ros_mcp")
    tools = _ensure_pkg("ros_mcp.tools")
    utils = _ensure_pkg("ros_mcp.utils")

    response = types.ModuleType("ros_mcp.utils.response")

    def _extract_error(r):
        if not r:
            return "No response"
        values = r.get("values", {}) if isinstance(r, dict) else {}
        if isinstance(values, dict):
            return values.get("message", "Service call failed")
        return str(values) if values else "Service call failed"

    response._extract_error = _extract_error  # type: ignore[attr-defined]
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
        "ros_mcp_tools_parameters_safe_check", _PARAMETERS_PATH
    )
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    tools.parameters = mod  # type: ignore[attr-defined]
    return mod


@pytest.fixture(scope="module")
def parameters():
    return _load_parameters_module()


class TestSafeCheckParameterExists:
    def test_no_response(self, parameters):
        ws = FakeWsManager(response=None)
        exists, reason, resp = parameters._safe_check_parameter_exists("/foo", ws)
        assert exists is False
        assert resp is None
        assert "No response" in reason

    def test_empty_string_value(self, parameters):
        payload = {"values": {"value": "", "reason": "missing"}}
        ws = FakeWsManager(response=payload)
        exists, reason, resp = parameters._safe_check_parameter_exists("/foo", ws)
        assert exists is False
        assert resp is None
        assert reason == "missing"

    def test_quoted_empty_string(self, parameters):
        payload = {"values": {"value": '""'}}
        ws = FakeWsManager(response=payload)
        exists, reason, resp = parameters._safe_check_parameter_exists("/foo", ws)
        assert exists is False
        assert resp is None

    def test_literal_null_string(self, parameters):
        # ROS1 rosbridge pattern for missing param
        payload = {"values": {"value": "null"}}
        ws = FakeWsManager(response=payload)
        exists, reason, resp = parameters._safe_check_parameter_exists("/foo", ws)
        assert exists is False
        assert resp is None

    def test_existing_value_in_values(self, parameters):
        payload = {"values": {"value": "42"}}
        ws = FakeWsManager(response=payload)
        exists, reason, resp = parameters._safe_check_parameter_exists("/bar", ws)
        assert exists is True
        assert reason == ""
        assert resp is payload

    def test_result_dict_empty(self, parameters):
        payload = {"result": {"value": "null", "reason": "gone"}}
        ws = FakeWsManager(response=payload)
        exists, reason, resp = parameters._safe_check_parameter_exists("/baz", ws)
        assert exists is False
        assert reason == "gone"

    def test_result_dict_value(self, parameters):
        payload = {"result": {"value": "true"}}
        ws = FakeWsManager(response=payload)
        exists, reason, resp = parameters._safe_check_parameter_exists("/baz", ws)
        assert exists is True
        assert resp is payload

    def test_request_raises(self, parameters):
        ws = FakeWsManager(error=RuntimeError("ws boom"))
        exists, reason, resp = parameters._safe_check_parameter_exists("/err", ws)
        assert exists is False
        assert resp is None
        assert "ws boom" in reason

    def test_unexpected_format(self, parameters):
        payload = {"op": "service_response"}  # no values/result
        ws = FakeWsManager(response=payload)
        exists, reason, resp = parameters._safe_check_parameter_exists("/x", ws)
        assert exists is False
        assert "Unexpected" in reason
