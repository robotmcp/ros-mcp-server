"""Unit tests for WebSocketManager close + context manager.

Complements request/send coverage without overlapping that module.
No real sockets.
"""

from __future__ import annotations

import importlib.util
import sys
import types
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

_ROOT = Path(__file__).resolve().parents[2]
_WS_PATH = _ROOT / "ros_mcp" / "utils" / "websocket.py"


def _stub_heavy_deps() -> None:
    if "cv2" not in sys.modules:
        sys.modules["cv2"] = types.ModuleType("cv2")
    if "numpy" not in sys.modules:
        sys.modules["numpy"] = types.ModuleType("numpy")
    if "websocket" not in sys.modules:
        ws_client = types.ModuleType("websocket")
        ws_client.create_connection = MagicMock()  # type: ignore[attr-defined]
        sys.modules["websocket"] = ws_client

    if "ros_mcp" not in sys.modules:
        pkg = types.ModuleType("ros_mcp")
        pkg.__path__ = [str(_ROOT / "ros_mcp")]  # type: ignore[attr-defined]
        sys.modules["ros_mcp"] = pkg
    if "ros_mcp.utils" not in sys.modules:
        utils = types.ModuleType("ros_mcp.utils")
        utils.__path__ = [str(_ROOT / "ros_mcp" / "utils")]  # type: ignore[attr-defined]
        sys.modules["ros_mcp.utils"] = utils

    if "ros_mcp.utils.config_utils" not in sys.modules:
        cfg = types.ModuleType("ros_mcp.utils.config_utils")
        cfg.get_image_dir = lambda: "/tmp"  # type: ignore[attr-defined]
        cfg.get_image_path = lambda filename="received_image.jpeg": f"/tmp/{filename}"  # type: ignore[attr-defined]
        sys.modules["ros_mcp.utils.config_utils"] = cfg


def _load_websocket_module():
    _stub_heavy_deps()
    name = "ros_mcp.utils.websocket_close_ctx_under_test"
    if name in sys.modules:
        del sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, _WS_PATH)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture
def ws_mod():
    return _load_websocket_module()


class TestClose:
    def test_close_when_ws_none(self, ws_mod):
        m = ws_mod.WebSocketManager("127.0.0.1", 9090)
        m.ws = None
        m.close()  # must not raise
        assert m.ws is None

    def test_close_connected_clears(self, ws_mod):
        m = ws_mod.WebSocketManager("127.0.0.1", 9090)
        fake = MagicMock()
        fake.connected = True
        m.ws = fake
        m.close()
        fake.close.assert_called_once()
        assert m.ws is None

    def test_close_when_not_connected_flag(self, ws_mod):
        m = ws_mod.WebSocketManager("127.0.0.1", 9090)
        fake = MagicMock()
        fake.connected = False
        m.ws = fake
        m.close()
        fake.close.assert_not_called()
        # still leaves ws as-is when not connected (matches implementation)
        assert m.ws is fake

    def test_close_exception_still_clears(self, ws_mod):
        m = ws_mod.WebSocketManager("127.0.0.1", 9090)
        fake = MagicMock()
        fake.connected = True
        fake.close.side_effect = RuntimeError("close boom")
        m.ws = fake
        m.close()
        assert m.ws is None


class TestContextManager:
    def test_enter_returns_self(self, ws_mod):
        m = ws_mod.WebSocketManager("127.0.0.1", 9090)
        assert m.__enter__() is m

    def test_with_block_closes(self, ws_mod):
        m = ws_mod.WebSocketManager("127.0.0.1", 9090)
        with patch.object(m, "close") as close_mock:
            with m:
                pass
        close_mock.assert_called_once()
