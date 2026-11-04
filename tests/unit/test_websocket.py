"""Unit tests for WebSocketManager."""

from unittest.mock import MagicMock

import websocket

from ros_mcp.utils.websocket import WebSocketManager


def test_receive_timeout_closes_connection_by_default():
    """By default (close_on_timeout=True), a receive timeout closes the WebSocket."""
    manager = WebSocketManager("127.0.0.1", 9090)
    connection = MagicMock()
    connection.connected = True
    connection.recv.side_effect = websocket.WebSocketTimeoutException("timed out")
    manager.ws = connection

    result = manager.receive(timeout=0.1)

    assert result is None
    assert manager.ws is None
    connection.close.assert_called_once()


def test_receive_timeout_keeps_connection_open_when_configured():
    """When close_on_timeout=False, an idle receive timeout does not close the WebSocket."""
    manager = WebSocketManager("127.0.0.1", 9090, close_on_timeout=False)
    connection = MagicMock()
    connection.connected = True
    connection.recv.side_effect = websocket.WebSocketTimeoutException("timed out")
    manager.ws = connection

    result = manager.receive(timeout=0.1)

    assert result is None
    assert manager.ws is connection
    connection.close.assert_not_called()


def test_receive_server_close_frame_closes_connection():
    """An empty string from recv() indicates a server close frame and closes the socket."""
    manager = WebSocketManager("127.0.0.1", 9090, close_on_timeout=False)
    connection = MagicMock()
    connection.connected = True
    connection.recv.return_value = ""
    manager.ws = connection

    result = manager.receive(timeout=0.1)

    assert result is None
    assert manager.ws is None
    connection.close.assert_called_once()


def test_receive_without_auto_connect_does_not_reconnect():
    """With auto_connect=False, receive does not reconnect if disconnected."""
    manager = WebSocketManager("127.0.0.1", 9090)
    manager.connect = MagicMock()

    result = manager.receive(timeout=0.1, auto_connect=False)

    assert result is None
    manager.connect.assert_not_called()


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


def test_request_timeout_closes_connection():
    """A timed-out request must close the socket to prevent stale replies."""
    manager = WebSocketManager("127.0.0.1", 9090)
    connection = MagicMock()
    connection.connected = True
    connection.recv.side_effect = websocket.WebSocketTimeoutException("timed out")
    manager.ws = connection

    response = manager.request({"op": "call_service", "service": "/test"}, timeout=0.1)

    assert "error" in response
    assert manager.ws is None
    connection.close.assert_called_once()
