"""subscribe_once and subscribe_for_duration keep their subscription across idle read slices."""

import json
from unittest.mock import MagicMock

import websocket

import ros_mcp.tools.topics as topics
import ros_mcp.utils.websocket as ws_module
from ros_mcp.utils.websocket import WebSocketManager


class FakeMCP:
    def __init__(self):
        self.tools = {}

    def tool(self, **kwargs):
        def decorator(func):
            self.tools[func.__name__] = func
            return func

        return decorator


def slow_topic(monkeypatch, idle_slices):
    """A rosbridge socket whose topic publishes only after `idle_slices` read timeouts."""
    message = json.dumps({"op": "publish", "topic": "/slow", "msg": {"data": 7}})
    replies = [websocket.WebSocketTimeoutException("timed out")] * idle_slices + [message]
    connections = []

    def create_connection(url, timeout=None):
        connection = MagicMock()
        connection.connected = True
        connection.recv.side_effect = list(replies)
        connections.append(connection)
        return connection

    monkeypatch.setattr(ws_module.websocket, "create_connection", create_connection)
    manager = WebSocketManager("127.0.0.1", 9090)
    mcp = FakeMCP()
    topics.register_topic_tools(mcp, manager)
    return mcp.tools, connections


def subscribes(connection):
    sent = [json.loads(call.args[0]) for call in connection.send.call_args_list]
    return [m for m in sent if m.get("op") == "subscribe"]


def test_subscribe_once_hears_a_topic_slower_than_one_slice(monkeypatch):
    tools, connections = slow_topic(monkeypatch, idle_slices=3)

    result = tools["subscribe_once"](topic="/slow", msg_type="std_msgs/Int32", timeout=10)

    assert result.get("msg") == {"data": 7}, result
    assert len(connections) == 1, "an idle slice reconnected and dropped the subscription"
    assert len(subscribes(connections[0])) == 1


def test_subscribe_for_duration_hears_a_topic_slower_than_one_slice(monkeypatch):
    tools, connections = slow_topic(monkeypatch, idle_slices=3)

    result = tools["subscribe_for_duration"](
        topic="/slow", msg_type="std_msgs/Int32", duration=10, max_messages=1
    )

    summary = json.loads(result.content[0].text)
    assert summary["collected_count"] == 1, summary
    assert json.loads(result.content[1].text) == {"data": 7}
    assert len(connections) == 1, "an idle slice reconnected and dropped the subscription"


def test_receive_close_on_timeout_overrides_the_manager_default():
    manager = WebSocketManager("127.0.0.1", 9090)
    connection = MagicMock()
    connection.connected = True
    connection.recv.side_effect = websocket.WebSocketTimeoutException("timed out")
    manager.ws = connection

    assert manager.receive(timeout=0.1, close_on_timeout=False) is None
    assert manager.ws is connection
    connection.close.assert_not_called()
