"""Unit tests for topics.get_message_details paths (no rosbridge)."""

from __future__ import annotations

import importlib.util
import sys
import types
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
_TOPICS_PATH = _ROOT / "ros_mcp" / "tools" / "topics.py"


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

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def request(self, message):
        self.calls.append(message)
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


def _load_topics_module(safe_get_values, check_response=None):
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
    websocket_mod.parse_input = lambda x: x  # type: ignore[attr-defined]
    sys.modules["ros_mcp.utils.websocket"] = websocket_mod
    utils.websocket = websocket_mod  # type: ignore[attr-defined]

    config_utils = types.ModuleType("ros_mcp.utils.config_utils")
    config_utils.get_image_path = lambda f="received_image.jpeg": f"/tmp/{f}"  # type: ignore[attr-defined]
    sys.modules["ros_mcp.utils.config_utils"] = config_utils
    utils.config_utils = config_utils  # type: ignore[attr-defined]

    images = types.ModuleType("ros_mcp.tools.images")
    images.convert_expects_image_hint = lambda x: None  # type: ignore[attr-defined]
    images._encode_image_to_imagecontent = lambda x: None  # type: ignore[attr-defined]
    sys.modules["ros_mcp.tools.images"] = images
    tools.images = images  # type: ignore[attr-defined]

    name = f"ros_mcp_tools_message_details_ut_{id(safe_get_values)}"
    if name in sys.modules:
        del sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, _TOPICS_PATH)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    tools.topics = mod  # type: ignore[attr-defined]
    return mod


class TestGetMessageDetails:
    def test_empty_name(self):
        mod = _load_topics_module(lambda _r: None)
        mcp = FakeMCP()
        ws = FakeWsManager()
        mod.register_topic_tools(mcp, ws)
        assert mcp.tools["get_message_details"]("") == {
            "error": "Message type cannot be empty"
        }
        assert mcp.tools["get_message_details"]("   ") == {
            "error": "Message type cannot be empty"
        }
        assert ws.calls == []

    def test_empty_typedefs(self):
        mod = _load_topics_module(lambda _r: {"typedefs": []})
        mcp = FakeMCP()
        ws = FakeWsManager(response={"ok": True})
        mod.register_topic_tools(mcp, ws)
        out = mcp.tools["get_message_details"]("std_msgs/String")
        assert "not found" in out["error"]
        assert len(ws.calls) == 1

    def test_values_none(self):
        mod = _load_topics_module(lambda _r: None)
        mcp = FakeMCP()
        ws = FakeWsManager(response={"ok": True})
        mod.register_topic_tools(mcp, ws)
        out = mcp.tools["get_message_details"]("std_msgs/String")
        assert "Failed to get details" in out["error"]

    def test_success_structure(self):
        def values(_r):
            return {
                "typedefs": [
                    {
                        "type": "geometry_msgs/Twist",
                        "fieldnames": ["linear", "angular"],
                        "fieldtypes": ["geometry_msgs/Vector3", "geometry_msgs/Vector3"],
                    }
                ]
            }

        mod = _load_topics_module(values)
        mcp = FakeMCP()
        ws = FakeWsManager(response={"values": {}})
        mod.register_topic_tools(mcp, ws)
        out = mcp.tools["get_message_details"]("geometry_msgs/Twist")
        assert out["message_type"] == "geometry_msgs/Twist"
        assert "geometry_msgs/Twist" in out["structure"]
        struct = out["structure"]["geometry_msgs/Twist"]
        assert struct["field_count"] == 2
        assert struct["fields"]["linear"] == "geometry_msgs/Vector3"
        assert struct["fields"]["angular"] == "geometry_msgs/Vector3"
