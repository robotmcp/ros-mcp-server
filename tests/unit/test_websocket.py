"""Unit tests for WebSocketManager."""

from unittest.mock import MagicMock

import websocket

from ros_mcp.utils.websocket import WebSocketManager


def test_receive_timeout_keeps_connection_open():
    """An idle receive timeout should not close the WebSocket."""
    manager = WebSocketManager("127.0.0.1", 9090)
    connection = MagicMock()
    connection.connected = True
    connection.recv.side_effect = websocket.WebSocketTimeoutException("timed out")
    manager.ws = connection

    result = manager.receive(timeout=0.1)

    assert result is None
    assert manager.ws is connection
    connection.close.assert_not_called()


def test_receive_unexpected_error_closes_connection():
    """An unexpected receive error should still close the connection."""
    manager = WebSocketManager("127.0.0.1", 9090)
    connection = MagicMock()
    connection.connected = True
    connection.recv.side_effect = OSError("connection lost")
    manager.ws = connection

    result = manager.receive(timeout=0.1)

    assert result is None
    assert manager.ws is None
    connection.close.assert_called_once()
