"""Unit tests for parse_input dispatch helpers in ros_mcp/utils/websocket.py.

Covers expects_image=True/False/None and private _handle_* helpers without
OpenCV, websocket client, or a live rosbridge. Related to #308.
"""

from __future__ import annotations

import importlib.util
import json
import sys
import types
from pathlib import Path
from unittest.mock import patch

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
    if name in sys.modules:
        return sys.modules[name]
    mod = types.ModuleType(name)
    mod.__path__ = []  # type: ignore[attr-defined]
    sys.modules[name] = mod
    return mod


def _load_websocket_module():
    """Load websocket.py with lightweight stubs for heavy deps."""
    for name in ("cv2", "numpy", "websocket"):
        _ensure_stub(name)

    # numpy should expose enough surface that accidental attribute access is meek
    np = sys.modules["numpy"]
    if not hasattr(np, "frombuffer"):
        np.frombuffer = lambda *a, **k: None  # type: ignore[attr-defined]
        np.uint8 = "uint8"  # type: ignore[attr-defined]
        np.uint16 = "uint16"  # type: ignore[attr-defined]
        np.ndarray = object  # type: ignore[attr-defined]

    cv2 = sys.modules["cv2"]
    if not hasattr(cv2, "imwrite"):
        cv2.imwrite = lambda *a, **k: False  # type: ignore[attr-defined]
        cv2.cvtColor = lambda *a, **k: a[0] if a else None  # type: ignore[attr-defined]
        cv2.COLOR_RGB2BGR = 4  # type: ignore[attr-defined]
        cv2.normalize = lambda *a, **k: None  # type: ignore[attr-defined]
        cv2.NORM_MINMAX = 32  # type: ignore[attr-defined]
        cv2.CV_8U = 0  # type: ignore[attr-defined]
        cv2.IMWRITE_JPEG_QUALITY = 1  # type: ignore[attr-defined]

    ws_mod = sys.modules["websocket"]
    if not hasattr(ws_mod, "create_connection"):
        ws_mod.create_connection = lambda *a, **k: None  # type: ignore[attr-defined]

    # Ensure ros_mcp.utils.config_utils is importable (websocket imports it)
    _ensure_pkg("ros_mcp")
    _ensure_pkg("ros_mcp.utils")
    if "ros_mcp.utils.config_utils" not in sys.modules:
        spec_cfg = importlib.util.spec_from_file_location(
            "ros_mcp.utils.config_utils", _CONFIG_UTILS_PATH
        )
        assert spec_cfg and spec_cfg.loader
        cfg = importlib.util.module_from_spec(spec_cfg)
        sys.modules["ros_mcp.utils.config_utils"] = cfg
        # yaml may be missing offline; stub if needed for config_utils only
        _ensure_stub("yaml")
        try:
            spec_cfg.loader.exec_module(cfg)
        except Exception:
            # Minimal surface used by websocket module at import time
            cfg.get_image_dir = lambda: "/tmp"  # type: ignore[attr-defined]
            cfg.get_image_path = lambda filename="received_image.jpeg": f"/tmp/{filename}"  # type: ignore[attr-defined]

    mod_name = "ros_mcp_utils_websocket_parse_input_unit"
    # Drop stale loads so patches attach to the live module under test
    sys.modules.pop(mod_name, None)
    spec = importlib.util.spec_from_file_location(mod_name, _WEBSOCKET_PATH)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules[mod_name] = mod
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def ws():
    return _load_websocket_module()


class TestParseInputNoneAndBadJson:
    def test_none_raw(self, ws):
        assert ws.parse_input(None) == (None, False)

    def test_invalid_json(self, ws):
        assert ws.parse_input("{not-json") == (None, False)

    def test_json_array_not_dict(self, ws):
        assert ws.parse_input("[1, 2]") == (None, False)


class TestParseInputJsonHint:
    def test_expects_false_skips_image(self, ws):
        payload = {"op": "publish", "msg": {"data": "x", "format": "jpeg"}}
        raw = json.dumps(payload)
        with patch.object(ws, "parse_image") as mock_img:
            data, was_img = ws.parse_input(raw, expects_image=False)
        assert was_img is False
        assert data == payload
        mock_img.assert_not_called()


class TestParseInputImageHint:
    def test_expects_true_success(self, ws):
        payload = {"op": "publish", "msg": {"data": "x"}}
        raw = json.dumps(payload)
        fake = {"saved": True}
        with patch.object(ws, "parse_image", return_value=fake) as mock_img:
            data, was_img = ws.parse_input(raw, expects_image=True)
        assert was_img is True
        assert data is fake
        mock_img.assert_called_once()

    def test_expects_true_fallback_to_json(self, ws):
        payload = {"op": "service_response", "values": {"ok": True}}
        raw = json.dumps(payload)
        with patch.object(ws, "parse_image", return_value=None):
            data, was_img = ws.parse_input(raw, expects_image=True)
        assert was_img is False
        assert data == payload


class TestParseInputAuto:
    def test_non_publish_no_image(self, ws):
        payload = {"op": "service_response", "values": {"a": 1}}
        raw = json.dumps(payload)
        with patch.object(ws, "parse_image") as mock_img, patch.object(
            ws, "is_image_like"
        ) as mock_like:
            data, was_img = ws.parse_input(raw, expects_image=None)
        assert data == payload
        assert was_img is False
        mock_img.assert_not_called()
        mock_like.assert_not_called()

    def test_publish_not_image_like(self, ws):
        payload = {"op": "publish", "msg": {"data": [1, 2, 3]}}
        raw = json.dumps(payload)
        with patch.object(ws, "is_image_like", return_value=False) as mock_like, patch.object(
            ws, "parse_image"
        ) as mock_img:
            data, was_img = ws.parse_input(raw, expects_image=None)
        assert data == payload
        assert was_img is False
        mock_like.assert_called_once()
        mock_img.assert_not_called()

    def test_publish_image_like_success(self, ws):
        payload = {"op": "publish", "msg": {"data": "x", "format": "jpeg"}}
        raw = json.dumps(payload)
        fake = {"img": True}
        with patch.object(ws, "is_image_like", return_value=True), patch.object(
            ws, "parse_image", return_value=fake
        ):
            data, was_img = ws.parse_input(raw, expects_image=None)
        assert was_img is True
        assert data is fake

    def test_publish_image_like_parse_fails(self, ws):
        payload = {"op": "publish", "msg": {"data": "x", "format": "jpeg"}}
        raw = json.dumps(payload)
        with patch.object(ws, "is_image_like", return_value=True), patch.object(
            ws, "parse_image", return_value=None
        ):
            data, was_img = ws.parse_input(raw, expects_image=None)
        assert was_img is False
        assert data == payload
