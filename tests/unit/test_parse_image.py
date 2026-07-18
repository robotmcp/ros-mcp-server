"""Unit tests for parse_image validation and compressed-image paths.

Offline: mocks open/base64/cv2 so OpenCV and real disks are not required.
Covers gaps not in #353–#360 open aerial unit PRs.
"""

from __future__ import annotations

import base64
import importlib.util
import json
import sys
import types
from pathlib import Path
from unittest.mock import MagicMock, mock_open, patch

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
    for name in ("cv2", "numpy", "websocket"):
        _ensure_stub(name)

    np = sys.modules["numpy"]
    if not hasattr(np, "frombuffer"):
        np.frombuffer = lambda *a, **k: None  # type: ignore[attr-defined]
        np.uint8 = "uint8"  # type: ignore[attr-defined]
        np.uint16 = "uint16"  # type: ignore[attr-defined]
        np.ndarray = object  # type: ignore[attr-defined]

    cv2 = sys.modules["cv2"]
    if not hasattr(cv2, "imwrite"):
        cv2.imwrite = MagicMock(return_value=True)  # type: ignore[attr-defined]
        cv2.cvtColor = MagicMock(side_effect=lambda img, code: img)  # type: ignore[attr-defined]
        cv2.COLOR_RGB2BGR = 4  # type: ignore[attr-defined]
        cv2.normalize = MagicMock(return_value=None)  # type: ignore[attr-defined]
        cv2.NORM_MINMAX = 32  # type: ignore[attr-defined]
        cv2.CV_8U = 0  # type: ignore[attr-defined]
        cv2.IMWRITE_JPEG_QUALITY = 1  # type: ignore[attr-defined]

    _ensure_pkg("ros_mcp")
    utils_pkg = _ensure_pkg("ros_mcp.utils")
    if "ros_mcp.utils.config_utils" not in sys.modules:
        config_spec = importlib.util.spec_from_file_location(
            "ros_mcp.utils.config_utils", _CONFIG_UTILS_PATH
        )
        assert config_spec and config_spec.loader
        config_mod = importlib.util.module_from_spec(config_spec)
        sys.modules["ros_mcp.utils.config_utils"] = config_mod
        _ensure_stub("yaml")
        try:
            config_spec.loader.exec_module(config_mod)
        except Exception:
            config_mod.get_image_dir = lambda: "/tmp"  # type: ignore[attr-defined]
            config_mod.get_image_path = lambda filename="received_image.jpeg": f"/tmp/{filename}"  # type: ignore[attr-defined]
        utils_pkg.config_utils = config_mod  # type: ignore[attr-defined]

    mod_name = "ros_mcp_utils_websocket_parse_image_unit"
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


class TestParseImageValidation:
    def test_none_raw(self, ws):
        assert ws.parse_image(None) is None

    def test_invalid_json(self, ws):
        assert ws.parse_image("{not-json") is None

    def test_missing_msg(self, ws):
        assert ws.parse_image(json.dumps({"op": "publish"})) is None

    def test_missing_data(self, ws):
        payload = {"msg": {"format": "jpeg"}}
        assert ws.parse_image(json.dumps(payload)) is None

    def test_raw_missing_dims(self, ws):
        # No format → raw path; height/width/encoding incomplete
        payload = {"msg": {"data": base64.b64encode(b"xx").decode("ascii"), "encoding": "rgb8"}}
        assert ws.parse_image(json.dumps(payload)) is None


class TestParseImageCompressed:
    def test_compressed_jpeg_writes_and_returns_dict(self, ws):
        blob = b"\xff\xd8fakejpeg"
        data_b64 = base64.b64encode(blob).decode("ascii")
        result_envelope = {"op": "publish", "msg": {"data": data_b64, "format": "jpeg"}}
        raw = json.dumps(result_envelope)

        m = mock_open()
        with (
            patch.object(ws, "get_image_dir", return_value="/tmp/imgs"),
            patch.object(ws, "get_image_path", return_value="/tmp/imgs/received_image.jpeg"),
            patch.object(ws.os, "makedirs") as mk,
            patch("builtins.open", m),
        ):
            out = ws.parse_image(raw)

        assert out == result_envelope
        mk.assert_called()
        handle = m()
        handle.write.assert_called()
        written = b"".join(c.args[0] for c in handle.write.call_args_list)
        assert written == blob

    def test_compressed_png_format_substring(self, ws):
        data_b64 = base64.b64encode(b"pngbytes").decode("ascii")
        result_envelope = {"op": "publish", "msg": {"data": data_b64, "format": "sensor_msgs/CompressedImage; png compressed"}}
        raw = json.dumps(result_envelope)
        with (
            patch.object(ws, "get_image_dir", return_value="/tmp"),
            patch.object(ws, "get_image_path", return_value="/tmp/received_image.jpeg"),
            patch.object(ws.os, "makedirs"),
            patch("builtins.open", mock_open()),
        ):
            out = ws.parse_image(raw)
        assert out == result_envelope
