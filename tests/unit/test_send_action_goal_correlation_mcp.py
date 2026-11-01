"""MCP in-memory overlap probe; only the rosbridge socket factory is replaced."""

import asyncio
import json
import threading
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


def test_cancel_action_goal_uses_pending_goal_connection():
    trace = []
    connections = []
    connection_created = threading.Event()

    def factory(*_args, **_kwargs):
        socket = PendingGoalSocket(trace)
        connections.append(socket)
        connection_created.set()
        return socket

    manager = transport.WebSocketManager("127.0.0.1", 9090, default_timeout=1)
    server = FastMCP("cancel-action-probe")
    register_action_tools(server, manager)

    async def exercise():
        send_goal = server._tool_manager._tools["send_action_goal"].fn
        cancel_goal = server._tool_manager._tools["cancel_action_goal"].fn
        goal_task = asyncio.create_task(
            asyncio.to_thread(
                asyncio.run,
                send_goal(
                    action_name="/test",
                    action_type="example/action/Test",
                    goal={"value": "pending"},
                    timeout=10,
                ),
            )
        )
        await asyncio.to_thread(connection_created.wait, 2)
        await asyncio.to_thread(connections[0].goal_sent.wait, 2)
        goal_id = connections[0].goal_id
        cancel_result = await asyncio.to_thread(cancel_goal, "/test", goal_id)
        goal_result = await goal_task
        finished_cancel_result = cancel_goal("/test", goal_id)
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

    cancel_goal = server._tool_manager._tools["cancel_action_goal"].fn
    with patch.object(transport.websocket, "create_connection", factory):
        result = cancel_goal("/test_action", "nonexistent_goal")

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


async def main():
    print(json.dumps({"serialized": await run(False), "concurrent": await run(True)}, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
