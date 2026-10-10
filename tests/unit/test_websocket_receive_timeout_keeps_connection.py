"""WebSocketManager.receive must not close the socket on read timeout (#318)."""

from __future__ import annotations

from unittest.mock import MagicMock

from ros_mcp.utils.websocket import WebSocketManager, _is_websocket_timeout


def test_is_websocket_timeout_helpers():
    assert _is_websocket_timeout(TimeoutError("timed out"))
    assert _is_websocket_timeout(TimeoutError())
    assert not _is_websocket_timeout(RuntimeError("boom"))
    assert _is_websocket_timeout(OSError("timed out"))


def test_receive_timeout_returns_none_without_close():
    mgr = WebSocketManager("127.0.0.1", 9090, default_timeout=0.1)
    fake = MagicMock()
    fake.connected = True
    fake.recv.side_effect = TimeoutError("timed out")
    mgr.ws = fake

    # spy close
    closed = {"n": 0}
    orig_close = mgr.close

    def _close():
        closed["n"] += 1
        return orig_close()

    mgr.close = _close  # type: ignore[method-assign]

    out = mgr.receive(timeout=0.05)
    assert out is None
    assert closed["n"] == 0
    fake.recv.assert_called()
    # connection still held
    assert mgr.ws is fake


def test_receive_hard_error_still_closes():
    mgr = WebSocketManager("127.0.0.1", 9090, default_timeout=0.1)
    fake = MagicMock()
    fake.connected = True
    fake.recv.side_effect = RuntimeError("connection reset")
    mgr.ws = fake

    out = mgr.receive(timeout=0.05)
    assert out is None
    assert mgr.ws is None
