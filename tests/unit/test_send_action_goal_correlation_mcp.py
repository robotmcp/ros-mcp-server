"""MCP in-memory overlap probe; only the rosbridge socket factory is replaced."""

import asyncio
import json
import threading
import time
from collections import deque
from unittest.mock import patch

import pytest
from fastmcp import Client, FastMCP

from ros_mcp.tools.actions import register_action_tools
from ros_mcp.utils import websocket as transport


class PeerSocket:
    def __init__(self, trace):
        self.connected = True
        self.trace = trace
        self.frames = deque()

    def send(self, raw):
        submitted = json.loads(raw)
        self.trace.append({"send": submitted})
        if submitted["args"]["value"] == "A":
            self.frames.append(
                {
                    "op": "action_feedback",
                    "id": submitted["id"],
                    "action": submitted["action"],
                    "values": {"origin": "A-feedback"},
                }
            )
        # A result for another goal must not complete this call.
        self.frames.append(
            {
                "op": "action_result",
                "id": f"{submitted['id']}_wrong",
                "action": submitted["action"],
                "result": True,
                "status": 4,
                "values": {"origin": "wrong-goal"},
            }
        )
        self.frames.append(
            {
                "op": "action_result",
                "id": submitted["id"],
                "action": submitted["action"],
                "result": True,
                "status": 4,
                "values": {"origin": submitted["args"]["value"]},
            }
        )

    def recv(self):
        frame = self.frames.popleft()
        self.trace.append({"receive": frame})
        return json.dumps(frame)

    def settimeout(self, _timeout):
        pass

    def close(self):
        self.connected = False
        self.trace.append({"close": True})


class PendingGoalSocket:
    def __init__(self, trace):
        self.connected = True
        self.trace = trace
        self.goal_sent = threading.Event()
        self.cancel_sent = threading.Event()
        self.goal_id = None

    def send(self, raw):
        submitted = json.loads(raw)
        self.trace.append({"send": submitted})
        if submitted["op"] == "send_action_goal":
            self.goal_id = submitted["id"]
            self.goal_sent.set()
        elif submitted["op"] == "cancel_action_goal":
            self.cancel_sent.set()

    def recv(self):
        self.cancel_sent.wait(timeout=10)
        frame = {
            "op": "action_result",
            "id": self.goal_id,
            "status": 5,
            "values": {"canceled": True},
        }
        self.trace.append({"receive": frame})
        return json.dumps(frame)

    def settimeout(self, _timeout):
        pass

    def close(self):
        self.connected = False
        self.trace.append({"close": True})


async def progress(_progress, _total, _message):
    pass


async def run(overlap, same_action=False):
    trace = []
    connections = []

    def factory(*_args, **_kwargs):
        socket = PeerSocket(trace)
        connections.append(socket)
        return socket

    manager = transport.WebSocketManager("127.0.0.1", 9090, default_timeout=1)
    server = FastMCP("mission-overlap-probe")
    register_action_tools(server, manager)
    with patch.object(transport.websocket, "create_connection", factory):
        async with Client(server, progress_handler=progress) as client:

            async def call(marker):
                response = await client.call_tool(
                    "send_action_goal",
                    {
                        "action_name": "/test" if same_action else f"/test_{marker.lower()}",
                        "action_type": "example/action/Test",
                        "goal": {"value": marker},
                        "timeout": 1,
                    },
                )
                return response.data

            if overlap:
                results = await asyncio.gather(call("A"), call("B"))
            else:
                results = [await call("A"), await call("B")]

    return {
        "overlap": overlap,
        "same_action": same_action,
        "connections": len(connections),
        "results": results,
        "trace": trace,
    }


@pytest.mark.parametrize("same_action", [False, True], ids=["distinct-actions", "same-action"])
@pytest.mark.parametrize("overlap", [False, True], ids=["serialized", "concurrent"])
def test_action_result_belongs_to_submitted_goal(overlap, same_action):
    observation = asyncio.run(run(overlap, same_action))
    sends = [item["send"] for item in observation["trace"] if "send" in item]
    received = [
        item["receive"]
        for item in observation["trace"]
        if "receive" in item and item["receive"]["op"] == "action_result"
    ]
    assert len(sends) == len(observation["results"]) == 2
    assert len(received) == 4  # One mismatched and one valid result per goal.
    assert len({message["id"] for message in sends}) == 2

    # Each goal must use its own socket, including overlapping calls.
    assert observation["connections"] == 2

    submitted_by_id = {message["id"]: message for message in sends}
    assert len(submitted_by_id) == 2

    for result in observation["results"]:
        assert result["success"] is True
        assert result["goal_id"] in submitted_by_id

        submitted = submitted_by_id[result["goal_id"]]
        assert result["action"] == submitted["action"]
        assert result["result"]["origin"] == submitted["args"]["value"]

    # The received results must also belong to the goals that were submitted.
    received_ids = {frame["id"] for frame in received}
    expected_ids = set(submitted_by_id)
    assert received_ids == expected_ids | {f"{goal_id}_wrong" for goal_id in expected_ids}


class DroppingSocket:
    def __init__(self, trace):
        self.connected = True
        self.trace = trace

    def send(self, raw):
        submitted = json.loads(raw)
        self.trace.append({"send": submitted})

    def recv(self):
        # Simulate abrupt connection drop
        self.connected = False
        raise transport.websocket.WebSocketConnectionClosedException(
            "Connection to remote host was lost"
        )

    def settimeout(self, _timeout):
        pass

    def close(self):
        self.connected = False
        self.trace.append({"close": True})


def test_cancel_action_goal_uses_pending_goal_connection():
    trace = []
    connections = []
    goal_submitted_event = asyncio.Event()
    captured_goal_id = []

    def factory(*_args, **_kwargs):
        socket = PendingGoalSocket(trace)
        connections.append(socket)
        return socket

    async def progress_handler(_progress, _total, message):
        if message and message.startswith("Goal submitted: "):
            gid = message.replace("Goal submitted: ", "").strip()
            captured_goal_id.append(gid)
            goal_submitted_event.set()

    manager = transport.WebSocketManager("127.0.0.1", 9090, default_timeout=1)
    server = FastMCP("cancel-action-probe")
    register_action_tools(server, manager)

    async def exercise():
        async with Client(server, progress_handler=progress_handler) as client:
            goal_task = asyncio.create_task(
                client.call_tool(
                    "send_action_goal",
                    {
                        "action_name": "/test",
                        "action_type": "example/action/Test",
                        "goal": {"value": "pending"},
                        "timeout": 10,
                    },
                )
            )

            await asyncio.wait_for(goal_submitted_event.wait(), timeout=2.0)
            goal_id = captured_goal_id[0]

            # Cancel through the same Client on the single server event loop
            cancel_response = await client.call_tool(
                "cancel_action_goal",
                {"action_name": "/test", "goal_id": goal_id},
            )
            cancel_result = cancel_response.data

            goal_response = await asyncio.wait_for(goal_task, timeout=2.0)
            goal_result = goal_response.data

            # Cancel for finished goal through the same client falls back to default manager
            finished_cancel_response = await client.call_tool(
                "cancel_action_goal",
                {"action_name": "/test", "goal_id": goal_id},
            )
            finished_cancel_result = finished_cancel_response.data

            return cancel_result, goal_result, finished_cancel_result

    with patch.object(transport.websocket, "create_connection", factory):
        cancel_result, goal_result, finished_cancel_result = asyncio.run(exercise())

    sends = [item["send"] for item in trace if "send" in item]
    assert len(connections) == 2
    assert [message["op"] for message in sends] == [
        "send_action_goal",
        "cancel_action_goal",
        "cancel_action_goal",
    ]
    assert sends[1]["id"] == sends[0]["id"]
    assert sends[2]["id"] == sends[0]["id"]
    assert connections[0].cancel_sent.is_set()
    assert connections[1].cancel_sent.is_set()
    assert cancel_result["success"] is True
    assert goal_result["success"] is True
    assert goal_result["status"] == 5
    assert finished_cancel_result["success"] is True


def test_cancel_action_goal_untracked_falls_back_to_default_manager():
    trace = []
    connections = []

    def factory(*_args, **_kwargs):
        socket = PendingGoalSocket(trace)
        connections.append(socket)
        return socket

    manager = transport.WebSocketManager("127.0.0.1", 9090, default_timeout=1)
    server = FastMCP("cancel-untracked-probe")
    register_action_tools(server, manager)

    async def exercise():
        async with Client(server) as client:
            response = await client.call_tool(
                "cancel_action_goal",
                {"action_name": "/test_action", "goal_id": "nonexistent_goal"},
            )
            return response.data

    with patch.object(transport.websocket, "create_connection", factory):
        result = asyncio.run(exercise())

    assert result["success"] is True
    assert result["action"] == "/test_action"
    assert result["goal_id"] == "nonexistent_goal"
    assert len(connections) == 1
    sends = [item["send"] for item in trace if "send" in item]
    assert len(sends) == 1
    assert sends[0] == {
        "op": "cancel_action_goal",
        "id": "nonexistent_goal",
        "action": "/test_action",
    }


def test_send_action_goal_connection_loss_reports_error_immediately():
    trace = []
    connections = []

    def factory(*_args, **_kwargs):
        socket = DroppingSocket(trace)
        connections.append(socket)
        return socket

    manager = transport.WebSocketManager("127.0.0.1", 9090, default_timeout=1)
    server = FastMCP("drop-probe")
    register_action_tools(server, manager)

    async def exercise():
        async with Client(server) as client:
            start = time.time()
            response = await client.call_tool(
                "send_action_goal",
                {
                    "action_name": "/test",
                    "action_type": "example/action/Test",
                    "goal": {"value": "drop"},
                    "timeout": 10,  # 10s timeout, but connection drops immediately
                },
            )
            elapsed = time.time() - start
            return response.data, elapsed

    with patch.object(transport.websocket, "create_connection", factory):
        result, elapsed = asyncio.run(exercise())

    assert "Connection to rosbridge lost" in result["error"]
    assert elapsed < 2.0  # Must not wait out the 10s timeout
    # Did not spin-reconnect
    assert len(connections) == 1


def test_other_tools_can_run_concurrently_with_action_goal():
    trace = []
    connections = []

    class SlowSocket:
        def __init__(self, trace):
            self.connected = True
            self.trace = trace
            self.release_goal = threading.Event()

        def send(self, raw):
            self.trace.append({"send": json.loads(raw)})

        def recv(self):
            # Block until released by the test
            self.release_goal.wait(timeout=5)
            frame = {
                "op": "action_result",
                "id": "slow_goal",
                "status": 4,
                "values": {"done": True},
            }
            return json.dumps(frame)

        def settimeout(self, _timeout):
            pass

        def close(self):
            self.connected = False

    slow_socket = SlowSocket(trace)

    def factory(*_args, **_kwargs):
        connections.append(slow_socket)
        return slow_socket

    manager = transport.WebSocketManager("127.0.0.1", 9090, default_timeout=1)
    server = FastMCP("concurrency-probe")
    register_action_tools(server, manager)

    @server.tool()
    def ping() -> str:
        return "pong"

    async def exercise():
        async with Client(server) as client:
            goal_task = asyncio.create_task(
                client.call_tool(
                    "send_action_goal",
                    {
                        "action_name": "/test",
                        "action_type": "example/action/Test",
                        "goal": {"value": "slow"},
                        "goal_id": "slow_goal",
                        "timeout": 5,
                    },
                )
            )
            # Give goal a moment to enter receive worker thread
            await asyncio.sleep(0.05)

            # Concurrent call to another tool while goal is in receive
            ping_start = time.time()
            ping_response = await client.call_tool("ping", {})
            ping_duration = time.time() - ping_start

            slow_socket.release_goal.set()
            goal_response = await goal_task
            return ping_response.data, ping_duration, goal_response.data

    with patch.object(transport.websocket, "create_connection", factory):
        ping_data, ping_duration, goal_data = asyncio.run(exercise())

    assert ping_data == "pong"
    assert ping_duration < 0.5  # Not blocked by the goal's socket receive
    assert goal_data["success"] is True


async def main():
    print(json.dumps({"serialized": await run(False), "concurrent": await run(True)}, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
