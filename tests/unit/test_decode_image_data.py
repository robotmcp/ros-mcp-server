"""Unit tests for _decode_image_data encodings in ros_mcp/utils/websocket.py.

Uses lightweight ndarray stand-ins + mocked cv2 so OpenCV is not required offline.
Related to #308 / image path hygiene (#301/#345 line).
"""

from __future__ import annotations

import importlib.util
import sys
import types
from pathlib import Path
from unittest.mock import MagicMock

import pytest

_ROOT = Path(__file__).resolve().parents[2]
_WEBSOCKET_PATH = _ROOT / "ros_mcp" / "utils" / "websocket.py"
_CONFIG_UTILS_PATH = _ROOT / "ros_mcp" / "utils" / "config_utils.py"


class FakeArray:
    """Minimal numpy ndarray substitute for reshape / byteswap chains."""

    def __init__(self, data, shape=None):
        self._data = list(data) if not isinstance(data, FakeArray) else list(data._data)
        self.shape = shape
        self.dtype = "fake"

    def reshape(self, shape):
        # shape may be (h, w) or (h, w, c)
        return FakeArray(self._data, shape=shape)

    def byteswap(self):
        return self

    def newbyteorder(self):
        return FakeArray(list(reversed(self._data)), shape=self.shape)


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
    np.frombuffer = lambda *a, **k: FakeArray([0, 1, 2, 3, 4, 5])  # type: ignore[attr-defined]
    np.uint8 = "uint8"  # type: ignore[attr-defined]
    np.uint16 = "uint16"  # type: ignore[attr-defined]
    np.ndarray = FakeArray  # type: ignore[attr-defined]

    cv2 = sys.modules["cv2"]
    cv2.COLOR_RGB2BGR = 4  # type: ignore[attr-defined]
    cv2.NORM_MINMAX = 32  # type: ignore[attr-defined]
    cv2.CV_8U = 0  # type: ignore[attr-defined]
    cv2.IMWRITE_JPEG_QUALITY = 1  # type: ignore[attr-defined]
    cv2.imwrite = MagicMock(return_value=True)  # type: ignore[attr-defined]
    cv2.cvtColor = MagicMock(side_effect=lambda img, code: FakeArray(img._data, shape=("bgr",)))  # type: ignore[attr-defined]
    cv2.normalize = MagicMock(  # type: ignore[attr-defined]
        side_effect=lambda src, dst, a, b, norm, dtype: FakeArray([0, 255], shape=getattr(src, "shape", None))
    )

    ws_mod = sys.modules["websocket"]
    if not hasattr(ws_mod, "create_connection"):
        ws_mod.create_connection = lambda *a, **k: None  # type: ignore[attr-defined]

    _ensure_pkg("ros_mcp")
    _ensure_pkg("ros_mcp.utils")
    if "ros_mcp.utils.config_utils" not in sys.modules:
        spec_cfg = importlib.util.spec_from_file_location(
            "ros_mcp.utils.config_utils", _CONFIG_UTILS_PATH
        )
        assert spec_cfg and spec_cfg.loader
        cfg = importlib.util.module_from_spec(spec_cfg)
        sys.modules["ros_mcp.utils.config_utils"] = cfg
        _ensure_stub("yaml")
        try:
            spec_cfg.loader.exec_module(cfg)
        except Exception:
            cfg.get_image_dir = lambda: "/tmp"  # type: ignore[attr-defined]
            cfg.get_image_path = lambda filename="received_image.jpeg": f"/tmp/{filename}"  # type: ignore[attr-defined]

    mod_name = "ros_mcp_utils_websocket_decode_image_unit"
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


class TestDecodeImageData:
    def test_rgb8_calls_cvtcolor(self, ws):
        cv2 = sys.modules["cv2"]
        cv2.cvtColor.reset_mock()
        arr = FakeArray([1, 2, 3] * 4)
        out = ws._decode_image_data(arr, height=2, width=2, encoding="rgb8", msg={})
        assert out is not None
        assert out.shape == ("bgr",)
        cv2.cvtColor.assert_called_once()
        args, _ = cv2.cvtColor.call_args
        assert args[1] == cv2.COLOR_RGB2BGR

    def test_bgr8_reshape_only(self, ws):
        cv2 = sys.modules["cv2"]
        cv2.cvtColor.reset_mock()
        arr = FakeArray(list(range(12)))
        out = ws._decode_image_data(arr, height=2, width=2, encoding="bgr8", msg={})
        assert out is not None
        assert out.shape == (2, 2, 3)
        cv2.cvtColor.assert_not_called()

    def test_mono8(self, ws):
        arr = FakeArray(list(range(4)))
        out = ws._decode_image_data(arr, height=2, width=2, encoding="mono8", msg={})
        assert out is not None
        assert out.shape == (2, 2)

    def test_mono8_case_insensitive(self, ws):
        arr = FakeArray(list(range(4)))
        out = ws._decode_image_data(arr, height=2, width=2, encoding="MONO8", msg={})
        assert out is not None
        assert out.shape == (2, 2)

    def test_mono16_normalizes(self, ws):
        cv2 = sys.modules["cv2"]
        cv2.normalize.reset_mock()
        arr = FakeArray(list(range(4)))
        out = ws._decode_image_data(arr, height=2, width=2, encoding="mono16", msg={})
        assert out is not None
        cv2.normalize.assert_called_once()

    def test_16uc1_with_bigendian_flag(self, ws):
        cv2 = sys.modules["cv2"]
        cv2.normalize.reset_mock()
        arr = FakeArray([10, 20, 30, 40])
        out = ws._decode_image_data(
            arr, height=2, width=2, encoding="16UC1", msg={"is_bigendian": 1}
        )
        assert out is not None
        cv2.normalize.assert_called_once()

    def test_unsupported_encoding_returns_none(self, ws):
        arr = FakeArray([0, 1, 2])
        out = ws._decode_image_data(arr, height=1, width=1, encoding="yuv422_custom", msg={})
        assert out is None

    def test_bigendian_bad_field_still_normalizes(self, ws):
        """is_bigendian not int-like → swallow and normalize."""
        cv2 = sys.modules["cv2"]
        cv2.normalize.reset_mock()
        arr = FakeArray([1, 2, 3, 4])
        out = ws._decode_image_data(
            arr, height=2, width=2, encoding="mono16", msg={"is_bigendian": "nope"}
        )
        assert out is not None
        cv2.normalize.assert_called_once()
