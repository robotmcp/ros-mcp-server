"""Unit tests for WebSocketManager.receive paths."""

from unittest.mock import MagicMock, patch

from ros_mcp.utils.websocket import WebSocketManager


class TestWebSocketManagerReceive:
    def test_receive_returns_raw_on_success(self):
        mgr = WebSocketManager("127.0.0.1", 9090, default_timeout=1.5)
        mock_ws = MagicMock()
        mock_ws.connected = True
        mock_ws.recv.return_value = '{"op": "service_response"}'
        mgr.ws = mock_ws

        with patch.object(mgr, "connect", return_value=None) as connect:
            raw = mgr.receive()
            connect.assert_called_once()
        assert raw == '{"op": "service_response"}'
        mock_ws.settimeout.assert_called_once_with(1.5)
        mock_ws.recv.assert_called_once()

    def test_receive_uses_explicit_timeout(self):
        mgr = WebSocketManager("127.0.0.1", 9090, default_timeout=2.0)
        mock_ws = MagicMock()
        mock_ws.connected = True
        mock_ws.recv.return_value = "ok"
        mgr.ws = mock_ws

        with patch.object(mgr, "connect", return_value=None):
            assert mgr.receive(timeout=0.25) == "ok"
        mock_ws.settimeout.assert_called_once_with(0.25)

    def test_receive_returns_none_on_exception_and_closes(self):
        mgr = WebSocketManager("127.0.0.1", 9090)
        mock_ws = MagicMock()
        mock_ws.connected = True
        mock_ws.recv.side_effect = TimeoutError("timed out")
        mgr.ws = mock_ws

        with patch.object(mgr, "connect", return_value=None):
            assert mgr.receive() is None
        assert mgr.ws is None
        mock_ws.close.assert_called()

    def test_receive_returns_none_when_no_ws(self):
        mgr = WebSocketManager("127.0.0.1", 9090)
        mgr.ws = None

        def _fake_connect():
            mgr.ws = None
            return "connect failed"

        with patch.object(mgr, "connect", side_effect=_fake_connect):
            assert mgr.receive() is None
