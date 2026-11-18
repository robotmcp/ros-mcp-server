"""Offline action-result interpretation, using normal repository imports."""

import asyncio
import json

import pytest

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


class ResultSocket:
    def __init__(self, bridge_result, status, values):
        self.bridge_result = bridge_result
        self.status = status
        self.values = values
        self.connected = True
        self.sent = []
        self.received = []
        self.close_count = 0

    def send(self, message):
        self.sent.append(json.loads(message))

    def settimeout(self, _timeout):
        pass

    def recv(self):
        assert len(self.sent) == 1
        submitted = self.sent[0]
        frame = {
            "op": "action_result",
            "id": submitted["id"],
            "action": submitted["action"],
            "result": self.bridge_result,
            "status": self.status,
            "values": self.values,
        }
        self.received.append(frame)
        return json.dumps(frame)

    def close(self):
        self.close_count += 1
        self.connected = False


@pytest.mark.parametrize(
    "bridge_result,status,values,expected_success",
    [
        (False, 0, "synthetic action client failure", False),
        (True, 4, {"marker": "succeeded"}, True),
        (True, 6, {"marker": "aborted"}, True),
    ],
    ids=["bridge-failure", "succeeded-control", "aborted-status-control"],
)
def test_action_result_preserves_bridge_failure_and_ros_status(
    monkeypatch, bridge_result, status, values, expected_success
):
    socket = ResultSocket(bridge_result, status, values)
    monkeypatch.setattr(transport.websocket, "create_connection", lambda *_a, **_k: socket)
    manager = transport.WebSocketManager("127.0.0.1", 9090, default_timeout=10)
    collector = ToolCollector()
    actions.register_action_tools(collector, manager)
    result = asyncio.run(
        collector.tools["send_action_goal"](
            "/test_action", "example/action/Test", {"value": 1}, timeout=10
        )
    )
    # Both identifiers match: this probe is independent of response correlation.
    assert result["goal_id"] == socket.sent[0]["id"] == socket.received[0]["id"]
    assert result["action"] == socket.received[0]["action"]
    assert result["status"] == status
    assert result["result"] == values
    assert len(socket.sent) == 1
    assert socket.close_count == 1
    assert manager.ws is None
    # A bridge result=True does not establish STATUS_SUCCEEDED: status remains separate.
    assert result["success"] is expected_success
