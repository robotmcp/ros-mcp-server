"""Unit tests for WebSocketManager.set_ip and connect (mocked)."""

from unittest.mock import MagicMock, patch

from ros_mcp.utils.websocket import WebSocketManager


class TestWebSocketManagerSetIp:
    def test_set_ip_updates_fields(self):
        mgr = WebSocketManager("127.0.0.1", 9090)
        mgr.set_ip("10.0.0.5", 9191)
        assert mgr.ip == "10.0.0.5"
        assert mgr.port == 9191


class TestWebSocketManagerConnect:
    def test_connect_success(self):
        mgr = WebSocketManager("127.0.0.1", 9090, default_timeout=1.5)
        fake_ws = MagicMock()
        fake_ws.connected = True
        with patch("ros_mcp.utils.websocket.websocket.create_connection", return_value=fake_ws) as cc:
            err = mgr.connect()
        assert err is None
        assert mgr.ws is fake_ws
        cc.assert_called_once()
        args, kwargs = cc.call_args
        assert args[0] == "ws://127.0.0.1:9090"
        assert kwargs.get("timeout") == 1.5

    def test_connect_exception_returns_error(self):
        mgr = WebSocketManager("bad.host", 1)
        with patch(
            "ros_mcp.utils.websocket.websocket.create_connection",
            side_effect=OSError("boom"),
        ):
            err = mgr.connect()
        assert err is not None
        assert "boom" in err or "Connection error" in err
        assert mgr.ws is None

    def test_already_connected_skips_create(self):
        mgr = WebSocketManager("127.0.0.1", 9090)
        fake_ws = MagicMock()
        fake_ws.connected = True
        mgr.ws = fake_ws
        with patch("ros_mcp.utils.websocket.websocket.create_connection") as cc:
            err = mgr.connect()
        assert err is None
        cc.assert_not_called()
        assert mgr.ws is fake_ws
