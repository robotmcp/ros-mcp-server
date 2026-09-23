"""Unit tests for ros_mcp/tools/robot_config.py tool handlers (no rosbridge)."""

from __future__ import annotations

import importlib.util
import sys
import types
from pathlib import Path
from unittest.mock import MagicMock

import pytest

_ROOT = Path(__file__).resolve().parents[2]
_RC_PATH = _ROOT / "ros_mcp" / "tools" / "robot_config.py"


class FakeMCP:
    def __init__(self) -> None:
        self.tools: dict[str, object] = {}

    def tool(self, *args, **kwargs):
        def decorator(fn):
            self.tools[fn.__name__] = fn
            return fn

        return decorator


class FakeWsManager:
    pass


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


class RosVersion:
    ROS1 = 1
    ROS2 = 2


class DetectionError(Exception):
    pass


def _load_robot_config_module():
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

    config_utils = types.ModuleType("ros_mcp.utils.config_utils")
    config_utils.get_verified_robot_spec_util = MagicMock(name="spec_util")  # type: ignore[attr-defined]
    config_utils.get_verified_robots_list_util = MagicMock(name="list_util")  # type: ignore[attr-defined]
    sys.modules["ros_mcp.utils.config_utils"] = config_utils
    utils.config_utils = config_utils  # type: ignore[attr-defined]

    rosapi = types.ModuleType("ros_mcp.utils.rosapi_types")
    rosapi.RosVersion = RosVersion  # type: ignore[attr-defined]
    rosapi.DetectionError = DetectionError  # type: ignore[attr-defined]
    rosapi.get_distro = MagicMock(return_value="humble")  # type: ignore[attr-defined]
    rosapi.get_ros_version = MagicMock(return_value=RosVersion.ROS2)  # type: ignore[attr-defined]
    sys.modules["ros_mcp.utils.rosapi_types"] = rosapi
    utils.rosapi_types = rosapi  # type: ignore[attr-defined]

    websocket_mod = types.ModuleType("ros_mcp.utils.websocket")
    websocket_mod.WebSocketManager = object  # type: ignore[attr-defined]
    sys.modules["ros_mcp.utils.websocket"] = websocket_mod
    utils.websocket = websocket_mod  # type: ignore[attr-defined]

    name = "ros_mcp_tools_robot_config_ut"
    if name in sys.modules:
        del sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, _RC_PATH)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    tools.robot_config = mod  # type: ignore[attr-defined]
    return mod


@pytest.fixture
def tools():
    mod = _load_robot_config_module()
    mcp = FakeMCP()
    mod.register_robot_config_tools(mcp, FakeWsManager())
    return mcp.tools, mod


class TestGetVerifiedRobotSpec:
    def test_multi_match_error(self, tools):
        tools_map, mod = tools
        mod.get_verified_robot_spec_util.return_value = {
            "a": {"type": "x"},
            "b": {"type": "y"},
        }
        result = tools_map["get_verified_robot_spec"]("ambiguous")
        assert "error" in result
        assert "Multiple configurations" in result["error"]

    def test_empty_config_error(self, tools):
        tools_map, mod = tools
        mod.get_verified_robot_spec_util.return_value = {}
        result = tools_map["get_verified_robot_spec"]("missing")
        assert "error" in result
        assert "No configuration found" in result["error"]

    def test_success_wraps_robot_config(self, tools):
        tools_map, mod = tools
        payload = {"so101": {"type": "sim", "prompts": "hi"}}
        mod.get_verified_robot_spec_util.return_value = payload
        result = tools_map["get_verified_robot_spec"]("so101")
        assert result == {"robot_config": payload}


class TestGetVerifiedRobotsList:
    def test_passthrough(self, tools):
        tools_map, mod = tools
        listing = {"robot_specifications": ["alpha", "beta"], "count": 2}
        mod.get_verified_robots_list_util.return_value = listing
        assert tools_map["get_verified_robots_list"]() == listing


class TestDetectRosVersion:
    def test_ros2_happy_path(self, tools):
        tools_map, mod = tools
        mod.get_ros_version.return_value = RosVersion.ROS2
        mod.get_distro.return_value = "jazzy"
        assert tools_map["detect_ros_version"]() == {"version": "2", "distro": "jazzy"}

    def test_ros1_happy_path(self, tools):
        tools_map, mod = tools
        mod.get_ros_version.return_value = RosVersion.ROS1
        mod.get_distro.return_value = "noetic"
        assert tools_map["detect_ros_version"]() == {"version": "1", "distro": "noetic"}

    def test_detection_error(self, tools):
        tools_map, mod = tools
        mod.get_ros_version.side_effect = DetectionError("no bridge")
        result = tools_map["detect_ros_version"]()
        assert "error" in result
        assert "Could not detect ROS version" in result["error"]
        assert "no bridge" in result["error"]
