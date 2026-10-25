"""Unit tests for pure helper _parse_typedef in ros_mcp/tools/actions.py.

Does not require OpenCV, FastMCP, or a live rosbridge. Related action-detail helpers.
"""

from __future__ import annotations

import importlib.util
import sys
import types
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[2]
_ACTIONS_PATH = _ROOT / "ros_mcp" / "tools" / "actions.py"


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


def _load_actions_module():
    """Load actions.py with FastMCP/mcp stubbed and package tree pre-seeded."""
    _ensure_stub("cv2")
    _ensure_stub("numpy")
    _ensure_stub("websocket")
    _ensure_stub("yaml")
    _ensure_stub("PIL")
    _ensure_stub("PIL.Image")

    fastmcp = _ensure_stub("fastmcp")
    fastmcp.FastMCP = object  # type: ignore[attr-defined]
    fastmcp.Context = object  # type: ignore[attr-defined]
    mcp_types = _ensure_pkg("mcp")
    mcp_types_mod = _ensure_pkg("mcp.types")
    mcp_types_mod.ToolAnnotations = object  # type: ignore[attr-defined]
    mcp_types.types = mcp_types_mod  # type: ignore[attr-defined]

    ros = _ensure_pkg("ros_mcp")
    tools = _ensure_pkg("ros_mcp.tools")
    utils = _ensure_pkg("ros_mcp.utils")

    # Minimal response / rosapi / websocket shells used at import time
    response = types.ModuleType("ros_mcp.utils.response")

    def _check_response(response_dict):  # pragma: no cover - not under test here
        return None

    def _safe_get_values(response_dict):  # pragma: no cover
        return None

    response._check_response = _check_response  # type: ignore[attr-defined]
    response._safe_get_values = _safe_get_values  # type: ignore[attr-defined]
    sys.modules["ros_mcp.utils.response"] = response
    utils.response = response  # type: ignore[attr-defined]

    rosapi = types.ModuleType("ros_mcp.utils.rosapi_types")

    def rosapi_service(name: str) -> str:
        return name

    def rosapi_type(name: str) -> str:
        return name

    rosapi.rosapi_service = rosapi_service  # type: ignore[attr-defined]
    rosapi.rosapi_type = rosapi_type  # type: ignore[attr-defined]
    sys.modules["ros_mcp.utils.rosapi_types"] = rosapi
    utils.rosapi_types = rosapi  # type: ignore[attr-defined]

    websocket_mod = types.ModuleType("ros_mcp.utils.websocket")
    websocket_mod.WebSocketManager = object  # type: ignore[attr-defined]
    sys.modules["ros_mcp.utils.websocket"] = websocket_mod
    utils.websocket = websocket_mod  # type: ignore[attr-defined]

    spec = importlib.util.spec_from_file_location(
        "ros_mcp_tools_actions_parse_typedef", _ACTIONS_PATH
    )
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    tools.actions = mod  # type: ignore[attr-defined]
    return mod


@pytest.fixture(scope="module")
def actions():
    return _load_actions_module()


class TestParseTypedef:
    def test_basic_mapping(self, actions):
        typedef = {
            "fieldnames": ["x", "y", "theta"],
            "fieldtypes": ["float64", "float64", "float64"],
        }
        out = actions._parse_typedef(typedef)
        assert out["field_count"] == 3
        assert out["fields"] == {
            "x": "float64",
            "y": "float64",
            "theta": "float64",
        }

    def test_empty_typedef(self, actions):
        out = actions._parse_typedef({})
        assert out["fields"] == {}
        assert out["field_count"] == 0

    def test_missing_types_defaults_to_empty_zip(self, actions):
        out = actions._parse_typedef({"fieldnames": ["only"]})
        assert out["fields"] == {}
        assert out["field_count"] == 0

    def test_mismatched_lengths_zip_truncates(self, actions):
        typedef = {
            "fieldnames": ["a", "b", "c"],
            "fieldtypes": ["int32", "string"],
        }
        out = actions._parse_typedef(typedef)
        assert out["fields"] == {"a": "int32", "b": "string"}
        assert out["field_count"] == 2

    def test_empty_lists(self, actions):
        out = actions._parse_typedef({"fieldnames": [], "fieldtypes": []})
        assert out == {"fields": {}, "field_count": 0}

    def test_single_field(self, actions):
        out = actions._parse_typedef(
            {"fieldnames": ["ok"], "fieldtypes": ["bool"]}
        )
        assert out["fields"] == {"ok": "bool"}
        assert out["field_count"] == 1
