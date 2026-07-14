"""Unit tests for pure parse helpers in ros_mcp/utils/websocket.py.

Covers parse_json and is_image_like without requiring OpenCV, numpy, FastMCP, or
a live websocket client. Related to #308.
"""

from __future__ import annotations

import importlib.util
import sys
import types
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[2]
_WEBSOCKET_PATH = _ROOT / "ros_mcp" / "utils" / "websocket.py"
_CONFIG_UTILS_PATH = _ROOT / "ros_mcp" / "utils" / "config_utils.py"


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
    """Ensure a package-style module exists in sys.modules."""
    if name in sys.modules:
        return sys.modules[name]
    mod = types.ModuleType(name)
    mod.__path__ = []  # type: ignore[attr-defined]
    sys.modules[name] = mod
    return mod


def _load_websocket_module():
    """Load websocket.py with heavy deps stubbed and package imports short-circuited."""
    _ensure_stub("cv2")
    _ensure_stub("numpy")
    _ensure_stub("websocket")
    _ensure_stub("yaml")

    # Prevent `from ros_mcp.utils.config_utils import …` from loading ros_mcp/__init__.py
    # (which imports FastMCP via main). Install lightweight package shells + real config_utils.
    _ensure_pkg("ros_mcp")
    utils_pkg = _ensure_pkg("ros_mcp.utils")

    config_spec = importlib.util.spec_from_file_location(
        "ros_mcp.utils.config_utils", _CONFIG_UTILS_PATH
    )
    assert config_spec and config_spec.loader
    config_mod = importlib.util.module_from_spec(config_spec)
    sys.modules["ros_mcp.utils.config_utils"] = config_mod
    config_spec.loader.exec_module(config_mod)
    utils_pkg.config_utils = config_mod  # type: ignore[attr-defined]

    spec = importlib.util.spec_from_file_location(
        "ros_mcp_utils_websocket_parse", _WEBSOCKET_PATH
    )
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    # Spot-check: race-free module name separate from package path
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def ws_mod():
    return _load_websocket_module()


class TestParseJson:
    def test_none_returns_none(self, ws_mod):
        assert ws_mod.parse_json(None) is None

    def test_empty_string_returns_none(self, ws_mod):
        assert ws_mod.parse_json("") is None

    def test_invalid_json_returns_none(self, ws_mod):
        assert ws_mod.parse_json("{not-json") is None
        assert ws_mod.parse_json("undefined") is None

    def test_non_dict_json_returns_none(self, ws_mod):
        assert ws_mod.parse_json("[]") is None
        assert ws_mod.parse_json("1") is None
        assert ws_mod.parse_json('"hello"') is None
        assert ws_mod.parse_json("true") is None

    def test_valid_dict_string(self, ws_mod):
        assert ws_mod.parse_json('{"op": "publish", "topic": "/chatter"}') == {
            "op": "publish",
            "topic": "/chatter",
        }

    def test_valid_dict_bytes_utf8(self, ws_mod):
        raw = b'{"result": true, "values": {"a": 1}}'
        assert ws_mod.parse_json(raw) == {"result": True, "values": {"a": 1}}

    def test_bytes_with_invalid_utf8_still_parses_after_replace(self, ws_mod):
        # Pure invalid utf-8 alone is not valid JSON → None.
        assert ws_mod.parse_json(b"\xff\xfe") is None


class TestIsImageLike:
    def test_non_dict(self, ws_mod):
        assert ws_mod.is_image_like(None) is False  # type: ignore[arg-type]
        assert ws_mod.is_image_like("x") is False  # type: ignore[arg-type]
        assert ws_mod.is_image_like([]) is False  # type: ignore[arg-type]

    def test_compressed_image_format(self, ws_mod):
        assert ws_mod.is_image_like({"data": "AAAA", "format": "jpeg"}) is True
        assert ws_mod.is_image_like({"data": "AAAA", "format": "png"}) is True
        assert (
            ws_mod.is_image_like({"data": "AAAA", "format": "image/jpeg compressed"}) is True
        )

    def test_compressed_with_non_image_format_falls_through(self, ws_mod):
        # Has data+format but format is not image-like, and lacks raw Image fields.
        assert ws_mod.is_image_like({"data": "AAAA", "format": "octet-stream"}) is False

    def test_raw_image_happy_path(self, ws_mod):
        msg = {
            "data": "AAAA",
            "width": 640,
            "height": 480,
            "encoding": "rgb8",
        }
        assert ws_mod.is_image_like(msg) is True

    def test_pointcloud_decoy_not_image(self, ws_mod):
        # Messages can carry binary data without being cameras (PointCloud2-like).
        assert (
            ws_mod.is_image_like({"data": "AAAA", "fields": [], "point_step": 32}) is False
        )

    def test_missing_required_raw_fields(self, ws_mod):
        assert ws_mod.is_image_like({"data": "x", "width": 1, "height": 1}) is False
        assert ws_mod.is_image_like({"width": 1, "height": 1, "encoding": "rgb8"}) is False

    def test_non_int_dimensions(self, ws_mod):
        assert (
            ws_mod.is_image_like(
                {"data": "x", "width": "640", "height": 480, "encoding": "bgr8"}
            )
            is False
        )
        assert (
            ws_mod.is_image_like(
                {"data": "x", "width": 640, "height": "480", "encoding": "bgr8"}
            )
            is False
        )

    def test_unknown_encoding_rejected(self, ws_mod):
        assert (
            ws_mod.is_image_like(
                {
                    "data": "x",
                    "width": 1,
                    "height": 1,
                    "encoding": "not_a_real_encoding",
                }
            )
            is False
        )

    def test_mono8_and_bayer_accepted(self, ws_mod):
        assert (
            ws_mod.is_image_like({"data": "x", "width": 2, "height": 2, "encoding": "mono8"})
            is True
        )
        assert (
            ws_mod.is_image_like(
                {"data": "x", "width": 2, "height": 2, "encoding": "bayer_rggb8"}
            )
            is True
        )
