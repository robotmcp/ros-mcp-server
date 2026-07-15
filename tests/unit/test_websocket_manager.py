"""Unit tests for WebSocketManager error/control paths (no real sockets/OpenCV)."""

from __future__ import annotations

import importlib.util
import json
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
        np = types.ModuleType("numpy")
        sys.modules["numpy"] = np
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

    # config_utils is imported by websocket.py
    if "ros_mcp.utils.config_utils" not in sys.modules:
        cfg = types.ModuleType("ros_mcp.utils.config_utils")
        cfg.get_image_dir = lambda: "/tmp"  # type: ignore[attr-defined]
        cfg.get_image_path = lambda filename="received_image.jpeg": f"/tmp/{filename}"  # type: ignore[attr-defined]
        sys.modules["ros_mcp.utils.config_utils"] = cfg


def _load_websocket_module():
    _stub_heavy_deps()
    name = "ros_mcp.utils.websocket_under_test"
    # Always reload from disk for isolation of class methods under patch
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


class TestWebSocketManagerBasics:
    def test_set_ip(self, ws_mod):
        m = ws_mod.WebSocketManager("127.0.0.1", 9090)
        m.set_ip("10.0.0.2", 9091)
        assert m.ip == "10.0.0.2"
        assert m.port == 9091

    def test_send_connect_failure(self, ws_mod):
        m = ws_mod.WebSocketManager("127.0.0.1", 9090)
        with patch.object(m, "connect", return_value="[WebSocket] Connection error: boom"):
            err = m.send({"op": "call_service"})
        assert err is not None
        assert "Connection error" in err

    def test_send_json_serialization_error(self, ws_mod):
        m = ws_mod.WebSocketManager("127.0.0.1", 9090)
        fake_ws = MagicMock()
        fake_ws.connected = True
        m.ws = fake_ws
        with (
            patch.object(m, "connect", return_value=None),
            patch.object(ws_mod.json, "dumps", side_effect=TypeError("not serializable")),
            patch.object(m, "close") as close_mock,
        ):
            err = m.send({"op": "call_service"})
        assert err is not None
        assert "JSON serialization" in err
        close_mock.assert_called()


class TestWebSocketManagerRequest:
    def test_request_propagates_send_error(self, ws_mod):
        m = ws_mod.WebSocketManager("127.0.0.1", 9090)
        with patch.object(m, "send", return_value="send failed"):
            out = m.request({"op": "call_service", "service": "/x"})
        assert out == {"error": "send failed"}

    def test_request_timeout_no_response(self, ws_mod):
        m = ws_mod.WebSocketManager("127.0.0.1", 9090)
        with (
            patch.object(m, "send", return_value=None),
            patch.object(m, "receive", return_value=None),
        ):
            out = m.request({"op": "call_service"})
        assert out == {"error": "no response or timeout from rosbridge"}

    def test_request_invalid_json(self, ws_mod):
        m = ws_mod.WebSocketManager("127.0.0.1", 9090)
        raw = "not-json{"
        with (
            patch.object(m, "send", return_value=None),
            patch.object(m, "receive", return_value=raw),
        ):
            out = m.request({"op": "call_service"})
        assert out.get("error") == "invalid_json"
        assert out.get("raw") == raw

    def test_request_happy_json_dict(self, ws_mod):
        m = ws_mod.WebSocketManager("127.0.0.1", 9090)
        payload = {"op": "service_response", "result": True, "values": {"ok": 1}}
        with (
            patch.object(m, "send", return_value=None),
            patch.object(m, "receive", return_value=json.dumps(payload)),
        ):
            out = m.request({"op": "call_service"})
        assert out == payload

    def test_receive_without_ws_returns_none(self, ws_mod):
        m = ws_mod.WebSocketManager("127.0.0.1", 9090)
        with patch.object(m, "connect", return_value="fail"):
            assert m.receive() is None
