"""Unit tests for response helpers and convert_expects_image_hint.

- ros_mcp/utils/response.py string-values regression (#251) + #308 coverage
- ros_mcp/tools/images.py convert_expects_image_hint pure mapping

Loads modules via importlib with package shells so FastMCP/OpenCV are not
required offline.
"""

from __future__ import annotations

import importlib.util
import sys
import types
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[2]
_RESPONSE_PATH = _ROOT / "ros_mcp" / "utils" / "response.py"
_IMAGES_PATH = _ROOT / "ros_mcp" / "tools" / "images.py"


def _ensure_pkg(name: str) -> types.ModuleType:
    if name in sys.modules:
        return sys.modules[name]
    mod = types.ModuleType(name)
    mod.__path__ = []  # type: ignore[attr-defined]
    sys.modules[name] = mod
    return mod


def _ensure_stub(name: str) -> types.ModuleType:
    if name in sys.modules:
        return sys.modules[name]
    try:
        return __import__(name)
    except ImportError:
        mod = types.ModuleType(name)
        sys.modules[name] = mod
        return mod


def _load_response():
    spec = importlib.util.spec_from_file_location("ros_mcp_utils_response_unit", _RESPONSE_PATH)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def _load_images_tool_module():
    """Load images.py enough to exercise convert_expects_image_hint only."""
    # ROS tools pull FastMCP, MCP types, PIL. Stub to keep unit path offline.
    for name in (
        "fastmcp",
        "fastmcp.utilities",
        "fastmcp.utilities.types",
        "mcp",
        "mcp.types",
        "PIL",
        "PIL.Image",
    ):
        _ensure_stub(name)

    # Minimal annotations / Image placeholders so decorator evaluation succeeds.
    mcp_types = sys.modules["mcp.types"]
    if not hasattr(mcp_types, "ToolAnnotations"):
        class ToolAnnotations:  # noqa: N801 — mirror external API name
            def __init__(self, **kwargs):
                self.kwargs = kwargs

        class ImageContent:  # noqa: N801
            pass

        mcp_types.ToolAnnotations = ToolAnnotations
        mcp_types.ImageContent = ImageContent

    fastmcp = sys.modules["fastmcp"]
    if not hasattr(fastmcp, "FastMCP"):
        class FastMCP:  # noqa: N801
            def tool(self, *args, **kwargs):
                def deco(fn):
                    return fn

                return deco

        fastmcp.FastMCP = FastMCP

    fm_util_types = sys.modules["fastmcp.utilities.types"]
    if not hasattr(fm_util_types, "Image"):
        class Image:  # noqa: N801
            def __init__(self, *args, **kwargs):
                pass

            def to_image_content(self):
                return object()

        fm_util_types.Image = Image

    pil_image = sys.modules["PIL.Image"]
    if not hasattr(pil_image, "open"):
        pil_image.open = lambda *a, **k: None  # type: ignore[attr-defined]

    _ensure_pkg("ros_mcp")
    _ensure_pkg("ros_mcp.utils")
    _ensure_pkg("ros_mcp.tools")

    # Provide get_image_path used at module import / default args without full config_utils load
    config_stub = types.ModuleType("ros_mcp.utils.config_utils")
    config_stub.get_image_path = lambda filename="received_image.jpeg": f"/tmp/{filename}"  # type: ignore[attr-defined]
    sys.modules["ros_mcp.utils.config_utils"] = config_stub

    spec = importlib.util.spec_from_file_location("ros_mcp_tools_images_unit", _IMAGES_PATH)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def response_mod():
    return _load_response()


@pytest.fixture(scope="module")
def images_mod():
    return _load_images_tool_module()


class TestCheckResponse:
    def test_none_response(self, response_mod):
        assert response_mod._check_response(None) == {
            "error": "No response received from rosbridge"
        }

    def test_non_dict_response(self, response_mod):
        assert response_mod._check_response("nope") == {
            "error": "No response received from rosbridge"
        }
        assert response_mod._check_response([]) == {
            "error": "No response received from rosbridge"
        }

    def test_result_true_ok(self, response_mod):
        assert response_mod._check_response({"result": True, "values": {"a": 1}}) is None

    def test_missing_result_treated_as_ok(self, response_mod):
        assert response_mod._check_response({"values": {"ok": True}}) is None

    def test_result_false_with_dict_values_message(self, response_mod):
        err = response_mod._check_response(
            {"result": False, "values": {"message": "service gone"}}
        )
        assert err is not None
        assert "service gone" in err["error"]

    def test_result_false_with_string_values_no_crash(self, response_mod):
        # Regression for #251: values can be a str when service missing.
        err = response_mod._check_response(
            {"result": False, "values": "Service does not exist"}
        )
        assert err is not None
        assert "Service does not exist" in err["error"]


class TestSafeGetValues:
    def test_dict_values(self, response_mod):
        assert response_mod._safe_get_values({"values": {"topics": ["/chatter"]}}) == {
            "topics": ["/chatter"]
        }

    def test_string_values_returns_none(self, response_mod):
        assert response_mod._safe_get_values({"values": "Service does not exist"}) is None

    def test_missing_values(self, response_mod):
        assert response_mod._safe_get_values({}) is None

    def test_non_dict_response(self, response_mod):
        assert response_mod._safe_get_values(None) is None
        assert response_mod._safe_get_values("x") is None


class TestExtractError:
    def test_dict_message(self, response_mod):
        assert response_mod._extract_error({"values": {"message": "boom"}}) == "boom"

    def test_string_values(self, response_mod):
        assert response_mod._extract_error({"values": "not found"}) == "not found"

    def test_empty_dict_values_default(self, response_mod):
        assert response_mod._extract_error({"values": {}}) == "Service call failed"

    def test_none_response(self, response_mod):
        assert response_mod._extract_error(None) == "No response"


class TestConvertExpectsImageHint:
    def test_true_string(self, images_mod):
        assert images_mod.convert_expects_image_hint("true") is True

    def test_false_string(self, images_mod):
        assert images_mod.convert_expects_image_hint("false") is False

    def test_auto_and_unknown_map_to_none(self, images_mod):
        assert images_mod.convert_expects_image_hint("auto") is None
        assert images_mod.convert_expects_image_hint("") is None
        assert images_mod.convert_expects_image_hint("maybe") is None
