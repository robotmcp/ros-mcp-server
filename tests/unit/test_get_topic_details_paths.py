"""Unit tests for topics.get_topic_details paths (no rosbridge)."""

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
    """Sequenced request responses for multi-call get_topic_details."""

    def __init__(self, responses=None) -> None:
        self._responses = list(responses or [])
        self.calls = []

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def request(self, message):
        self.calls.append(message)
        if not self._responses:
            return None
        return self._responses.pop(0)


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


def _load_topics_module(safe_get_values):
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
    response._check_response = lambda _r: None  # type: ignore[attr-defined]
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

    name = f"ros_mcp_tools_topics_details_ut_{id(safe_get_values)}"
    if name in sys.modules:
        del sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, _TOPICS_PATH)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    tools.topics = mod  # type: ignore[attr-defined]
    return mod


class TestGetTopicDetails:
    def test_empty_name(self):
        mod = _load_topics_module(lambda _r: None)
        mcp = FakeMCP()
        ws = FakeWsManager()
        mod.register_topic_tools(mcp, ws)
        assert mcp.tools["get_topic_details"]("") == {"error": "Topic name cannot be empty"}
        assert mcp.tools["get_topic_details"]("  ") == {"error": "Topic name cannot be empty"}

    def test_not_found_when_all_empty(self):
        mod = _load_topics_module(lambda _r: None)
        mcp = FakeMCP()
        ws = FakeWsManager(responses=[{}, {}, {}])
        mod.register_topic_tools(mcp, ws)
        out = mcp.tools["get_topic_details"]("/ghost")
        assert "not found" in out["error"]
        assert len(ws.calls) == 3

    def test_success_shape(self):
        payloads = [
            {"type": "std_msgs/String"},
            {"publishers": ["/talker"]},
            {"subscribers": ["/listener"]},
        ]

        def values(resp):
            return resp if resp else None

        mod = _load_topics_module(values)
        mcp = FakeMCP()
        ws = FakeWsManager(responses=list(payloads))
        mod.register_topic_tools(mcp, ws)
        out = mcp.tools["get_topic_details"]("/chatter")
        assert out["topic"] == "/chatter"
        assert out["type"] == "std_msgs/String"
        assert out["publishers"] == ["/talker"]
        assert out["subscribers"] == ["/listener"]
        assert out["publisher_count"] == 1
        assert out["subscriber_count"] == 1
        assert len(ws.calls) == 3
