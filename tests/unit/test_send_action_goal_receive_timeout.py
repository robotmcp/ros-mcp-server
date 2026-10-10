"""Action-level coverage of receive timeouts, with no live ROS connection."""

import asyncio
import json
from types import SimpleNamespace

import pytest
import websocket

from ros_mcp.tools import actions
from ros_mcp.utils import websocket as transport


class ToolCollector:
    def __init__(self):
        self.tools = {}

    def tool(self, **_kwargs):
        def register(function):
            self.tools[function.__name__] = function
            return function

        return register


class Clock:
    now = 1000.0

    def time(self):
        return self.now


class Socket:
    def __init__(self, clock, events):
        self.clock = clock
        self.events = list(events)
        self.connected = True
        self.sent = []
        self.close_count = 0
        self.timeouts = []
        self.observations = []

    def send(self, message):
        self.sent.append(json.loads(message))

    def settimeout(self, timeout):
        self.timeouts.append(timeout)

    def recv(self):
        event = self.events.pop(0) if self.events else "deadline"
        self.observations.append((event, self.connected, self.close_count))
        if event == "deadline":
            self.clock.now += 20
            raise websocket.WebSocketTimeoutException("deadline elapsed")
        self.clock.now += 0.1
        if isinstance(event, Exception):
            raise event
        message = {
            "op": event,
            "id": self.sent[0]["id"],
            "action": "/test_action",
            "values": {"marker": event},
        }
        if event == "action_result":
            message.update(status=4, result=True)
        return json.dumps(message)

    def close(self):
        self.close_count += 1
        self.connected = False


def run_goal(monkeypatch, events):
    clock = Clock()
    primary = Socket(clock, events)
    sockets = []

    def connect(*_args, **_kwargs):
        # Reconnection cannot recover frames queued on the original socket.
        socket = primary if not sockets else Socket(clock, [])
        sockets.append(socket)
        return socket

    monkeypatch.setattr(transport.websocket, "create_connection", connect)
    # Replace only this module's clock; never patch the global time module.
    monkeypatch.setattr(actions, "time", SimpleNamespace(time=clock.time))
    manager = transport.WebSocketManager("127.0.0.1", 9090, default_timeout=10)
    collector = ToolCollector()
    actions.register_action_tools(collector, manager)
    result = asyncio.run(
        collector.tools["send_action_goal"](
            "/test_action", "example/action/Test", {"value": 1}, timeout=10
        )
    )
    return result, primary, sockets, manager


@pytest.mark.parametrize(
    "early_timeout",
    [TimeoutError("timed out"), websocket.WebSocketTimeoutException("read timed out")],
    ids=["builtin-timeout", "websocket-timeout"],
)
def test_feedback_early_timeout_then_result_keeps_one_dispatch(monkeypatch, early_timeout):
    result, primary, sockets, manager = run_goal(
        monkeypatch, ["action_feedback", early_timeout, "action_result"]
    )
    assert result["success"] is True
    assert result["status"] == 4
    assert result["result"] == {"marker": "action_result"}
    assert result["goal_id"] == primary.sent[0]["id"]
    assert len(sockets) == 1
    assert sum(len(socket.sent) for socket in sockets) == 1
    assert all(connected and closed == 0 for _, connected, closed in primary.observations)
    assert primary.close_count == 1  # normal context cleanup, after result
    assert manager.ws is None


def test_overall_deadline_still_returns_timeout_without_resending(monkeypatch):
    result, primary, sockets, manager = run_goal(monkeypatch, ["action_feedback", "deadline"])
    assert result["success"] is False
    assert "timed out" in result["error"]
    assert result["goal_id"] == primary.sent[0]["id"]
    assert result["feedback_count"] == 1
    assert len(sockets) == 1
    assert sum(len(socket.sent) for socket in sockets) == 1
    assert primary.close_count == 1
    assert manager.ws is None
