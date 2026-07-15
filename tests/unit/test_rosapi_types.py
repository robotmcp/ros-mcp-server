"""Unit tests for ros_mcp/utils/rosapi_types.py (prefixes, fallbacks, no network)."""

from __future__ import annotations

import importlib.util
import sys
import types
from pathlib import Path
from unittest.mock import MagicMock

import pytest

_ROOT = Path(__file__).resolve().parents[2]
_ROSAPI_PATH = _ROOT / "ros_mcp" / "utils" / "rosapi_types.py"


def _load_rosapi_types():
    """Load rosapi_types without importing the ros_mcp package root (FastMCP)."""
    # Stub websocket dependency pulled only for type hint import of WebSocketManager
    if "websocket" not in sys.modules:
        sys.modules["websocket"] = types.ModuleType("websocket")

    # Minimal package shells
    if "ros_mcp" not in sys.modules:
        pkg = types.ModuleType("ros_mcp")
        pkg.__path__ = [str(_ROOT / "ros_mcp")]  # type: ignore[attr-defined]
        sys.modules["ros_mcp"] = pkg
    if "ros_mcp.utils" not in sys.modules:
        utils = types.ModuleType("ros_mcp.utils")
        utils.__path__ = [str(_ROOT / "ros_mcp" / "utils")]  # type: ignore[attr-defined]
        sys.modules["ros_mcp.utils"] = utils

    # Stub websocket module used by rosapi_types (`from ros_mcp.utils.websocket import WebSocketManager`)
    if "ros_mcp.utils.websocket" not in sys.modules:
        ws_mod = types.ModuleType("ros_mcp.utils.websocket")
        ws_mod.WebSocketManager = object  # type: ignore[attr-defined]
        sys.modules["ros_mcp.utils.websocket"] = ws_mod

    name = "ros_mcp.utils.rosapi_types"
    if name in sys.modules and getattr(sys.modules[name], "__file__", None) == str(_ROSAPI_PATH):
        return sys.modules[name]

    spec = importlib.util.spec_from_file_location(name, _ROSAPI_PATH)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def rt():
    return _load_rosapi_types()


@pytest.fixture(autouse=True)
def _clean_global_resolver(rt):
    rt._reset_resolver()
    yield
    rt._reset_resolver()


class TestRosapiTypeResolverPure:
    def test_get_type_fallback_ros2_when_unknown(self, rt):
        r = rt.RosapiTypeResolver()
        assert r.get_type("Topics") == "rosapi_msgs/srv/Topics"
        assert r.get_type("Nodes") == "rosapi_msgs/srv/Nodes"

    def test_get_type_ros1_and_ros2(self, rt):
        r = rt.RosapiTypeResolver()
        r._version = rt.RosVersion.ROS1
        assert r.get_type("Topics") == "rosapi/Topics"
        r._version = rt.RosVersion.ROS2
        assert r.get_type("Topics") == "rosapi_msgs/srv/Topics"

    def test_get_service_default_and_custom_prefix(self, rt):
        r = rt.RosapiTypeResolver()
        assert r.get_service("nodes") == "/rosapi/nodes"
        r._service_prefix = "/rosapi_node"
        assert r.get_service("nodes") == "/rosapi_node/nodes"
        assert r.get_service("topics") == "/rosapi_node/topics"

    def test_version_property_raises_before_detect(self, rt):
        r = rt.RosapiTypeResolver()
        with pytest.raises(rt.DetectionError, match="not detected"):
            _ = r.version

    def test_reset_clears_state(self, rt):
        r = rt.RosapiTypeResolver()
        r._version = rt.RosVersion.ROS2
        r._distro = "jazzy"
        r._service_prefix = "/rosapi_node"
        r._reset()
        assert r._version is None
        assert r._distro == ""
        assert r._service_prefix == "/rosapi"
        with pytest.raises(rt.DetectionError):
            _ = r.version


class TestModuleHelpers:
    def test_get_ros_version_raises_before_detect(self, rt):
        with pytest.raises(rt.DetectionError, match="not detected"):
            rt.get_ros_version()

    def test_rosapi_type_fallback_when_unknown(self, rt):
        assert rt.rosapi_type("Services") == "rosapi_msgs/srv/Services"

    def test_rosapi_type_and_service_after_inject(self, rt):
        rt._resolver._version = rt.RosVersion.ROS1
        rt._resolver._service_prefix = "/rosapi"
        assert rt.rosapi_type("Topics") == "rosapi/Topics"
        assert rt.rosapi_service("nodes") == "/rosapi/nodes"

        rt._resolver._version = rt.RosVersion.ROS2
        rt._resolver._service_prefix = "/rosapi_node"
        assert rt.rosapi_type("Topics") == "rosapi_msgs/srv/Topics"
        assert rt.rosapi_service("nodes") == "/rosapi_node/nodes"
        rt._resolver._distro = "humble"
        assert rt.get_distro() == "humble"
        assert rt.get_ros_version() is rt.RosVersion.ROS2

    def test_reset_resolver_restores_unknown(self, rt):
        rt._resolver._version = rt.RosVersion.ROS2
        rt._reset_resolver()
        with pytest.raises(rt.DetectionError):
            rt.get_ros_version()
        assert rt.rosapi_type("Topics") == "rosapi_msgs/srv/Topics"

    def test_detect_ros2_success_cache(self, rt):
        """Shallow FakeWs: get_ros_version returns ROS 2 at /rosapi."""

        class FakeWs:
            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

            def request(self, message, timeout=None):
                svc = message.get("service", "")
                if svc.endswith("/get_ros_version"):
                    return {
                        "result": True,
                        "values": {"version": 2, "distro": "humble"},
                    }
                return {"result": False}

        resolver = rt.RosapiTypeResolver()
        resolver.detect(FakeWs())
        assert resolver.version is rt.RosVersion.ROS2
        assert resolver.distro == "humble"
        assert resolver.get_service("nodes") == "/rosapi/nodes"
        assert resolver.get_type("Topics") == "rosapi_msgs/srv/Topics"


# Silence unused import lint if MagicMock kept for future
_ = MagicMock
