"""Unit tests for subscribe_once validation paths (no rosbridge)."""

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
    def __init__(self) -> None:
        self.default_timeout = 2.0
        self.calls: list = []

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def send(self, message):
        self.calls.append(("send", message))
        return None

    def receive(self, timeout=None):
        self.calls.append(("receive", timeout))
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


def _wire_utils(utils):
    response = types.ModuleType("ros_mcp.utils.response")
    response._check_response = lambda _r: None  # type: ignore[attr-defined]
    response._safe_get_values = lambda _r: {}  # type: ignore[attr-defined]
    sys.modules["ros_mcp.utils.response"] = response
    utils.response = response  # type: ignore[attr-defined]

    rosapi = types.ModuleType("ros_mcp.utils.rosapi_types")
    rosapi.rosapi_service = lambda n: f"/rosapi/{n}"  # type: ignore[attr-defined]
    rosapi.rosapi_type = lambda n: f"rosapi/{n}"  # type: ignore[attr-defined]
    sys.modules["ros_mcp.utils.rosapi_types"] = rosapi
    utils.rosapi_types = rosapi  # type: ignore[attr-defined]

    websocket_mod = types.ModuleType("ros_mcp.utils.websocket")
    websocket_mod.WebSocketManager = object  # type: ignore[attr-defined]
    websocket_mod.parse_input = lambda *a, **k: (None, False)  # type: ignore[attr-defined]
    sys.modules["ros_mcp.utils.websocket"] = websocket_mod
    utils.websocket = websocket_mod  # type: ignore[attr-defined]

    images = types.ModuleType("ros_mcp.tools.images")
    images.convert_expects_image_hint = lambda x: None  # type: ignore[attr-defined]
    images._encode_image_to_imagecontent = lambda img: img  # type: ignore[attr-defined]
    sys.modules["ros_mcp.tools.images"] = images


def _load_topics_module(unique: str):
    utils = _bootstrap_common()
    _wire_utils(utils)
    name = f"ros_mcp_tools_topics_ut_{unique}"
    if name in sys.modules:
        del sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, _TOPICS_PATH)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def _get_tool(tool_name: str):
    mod = _load_topics_module(tool_name + str(id(object())))
    mcp = FakeMCP()
    ws = FakeWsManager()
    mod.register_topic_tools(mcp, ws)
    return mcp.tools[tool_name], ws


class TestSubscribeOnceValidation:
    def test_missing_topic_and_msg_type(self):
        tool, _ = _get_tool("subscribe_once")
        out = tool(topic="", msg_type="")
        assert out == {
            "error": "Missing required arguments: topic and msg_type must be provided."
        }

    def test_missing_topic_only(self):
        tool, _ = _get_tool("subscribe_once")
        out = tool(topic="", msg_type="std_msgs/String")
        assert "Missing required arguments" in out["error"]

    def test_timeout_non_number(self):
        tool, _ = _get_tool("subscribe_once")
        out = tool(topic="/chatter", msg_type="std_msgs/String", timeout="nope")  # type: ignore[arg-type]
        assert out == {"error": "timeout must be a number"}

    def test_timeout_negative(self):
        tool, _ = _get_tool("subscribe_once")
        out = tool(topic="/chatter", msg_type="std_msgs/String", timeout=-1.0)
        assert out == {"error": "timeout must be >= 0"}

    def test_queue_length_too_small(self):
        tool, _ = _get_tool("subscribe_once")
        out = tool(topic="/chatter", msg_type="std_msgs/String", queue_length=0)
        assert out == {"error": "queue_length must be an integer ≥ 1"}

    def test_queue_length_non_int(self):
        tool, _ = _get_tool("subscribe_once")
        out = tool(
            topic="/chatter", msg_type="std_msgs/String", queue_length="bad"  # type: ignore[arg-type]
        )
        assert out == {"error": "queue_length must be an integer"}

    def test_throttle_rate_negative(self):
        tool, _ = _get_tool("subscribe_once")
        out = tool(topic="/chatter", msg_type="std_msgs/String", throttle_rate_ms=-5)
        assert out == {"error": "throttle_rate_ms must be an integer ≥ 0"}

    def test_throttle_rate_non_int(self):
        tool, _ = _get_tool("subscribe_once")
        out = tool(
            topic="/chatter",
            msg_type="std_msgs/String",
            throttle_rate_ms="x",  # type: ignore[arg-type]
        )
        assert out == {"error": "throttle_rate_ms must be an integer"}
