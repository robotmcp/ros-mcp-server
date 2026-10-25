"""Unit tests for WebSocketManager.send paths."""

from unittest.mock import MagicMock, patch

from ros_mcp.utils.websocket import WebSocketManager


class TestWebSocketManagerSend:
    def test_send_returns_none_on_success(self):
        mgr = WebSocketManager("127.0.0.1", 9090)
        mock_ws = MagicMock()
        mock_ws.connected = True
        mgr.ws = mock_ws

        with patch.object(mgr, "connect", return_value=None) as connect:
            err = mgr.send({"op": "call_service", "id": "1"})
            connect.assert_called_once()
        assert err is None
        mock_ws.send.assert_called_once()
        payload = mock_ws.send.call_args[0][0]
        assert '"op": "call_service"' in payload or '"op":"call_service"' in payload.replace(
            " ", ""
        )

    def test_send_returns_connect_error(self):
        mgr = WebSocketManager("127.0.0.1", 9090)
        with patch.object(mgr, "connect", return_value="[WebSocket] Connection error: boom"):
            err = mgr.send({"op": "advertise"})
        assert err == "[WebSocket] Connection error: boom"

    def test_send_serialization_error_closes(self):
        mgr = WebSocketManager("127.0.0.1", 9090)
        mock_ws = MagicMock()
        mock_ws.connected = True
        mgr.ws = mock_ws

        with patch.object(mgr, "connect", return_value=None):
            with patch("ros_mcp.utils.websocket.json.dumps", side_effect=TypeError("not serializable")):
                err = mgr.send({"bad": object()})
        assert err is not None
        assert "serialization" in err.lower() or "JSON" in err
        assert mgr.ws is None
        mock_ws.close.assert_called()

    def test_send_generic_exception_closes(self):
        mgr = WebSocketManager("127.0.0.1", 9090)
        mock_ws = MagicMock()
        mock_ws.connected = True
        mock_ws.send.side_effect = OSError("broken pipe")
        mgr.ws = mock_ws

        with patch.object(mgr, "connect", return_value=None):
            err = mgr.send({"op": "ping"})
        assert err is not None
        assert "Send error" in err
        assert mgr.ws is None

    def test_send_aborts_when_ws_missing_after_connect(self):
        mgr = WebSocketManager("127.0.0.1", 9090)

        def _connect_ok_but_clear():
            mgr.ws = None
            return None

        with patch.object(mgr, "connect", side_effect=_connect_ok_but_clear):
            err = mgr.send({"op": "x"})
        assert err == "[WebSocket] Not connected, send aborted."
