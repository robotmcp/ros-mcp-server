"""Unit tests for action tools compatibility handling across ROS versions."""

import asyncio

import pytest

from ros_mcp.tools.actions import register_action_tools
from ros_mcp.utils.rosapi_types import RosVersion, _reset_resolver, _resolver
from ros_mcp.utils.service_verifier import _reset_service_cache


class _FakeMcp:
    def __init__(self):
        self.tools = {}

    def tool(self, **_kwargs):
        def decorator(fn):
            self.tools[fn.__name__] = fn
            return fn

        return decorator


class _FakeWs:
    def __init__(self, responses=None):
        self._responses = responses or {}
        self.default_timeout = 2.0

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def request(self, message, timeout=None):
        service = message.get("service", "")
        if service in self._responses:
            resp = self._responses[service]
            if callable(resp):
                return resp(message)
            return resp
        return {"result": False, "error": f"service {service} does not exist"}

    def send(self, message):
        return None

    def receive(self, timeout=None):
        return None


@pytest.fixture(autouse=True)
def reset_state():
    _reset_service_cache()
    _reset_resolver()
    yield
    _reset_service_cache()
    _reset_resolver()


def _get_action_tools(responses=None):
    mcp = _FakeMcp()
    ws = _FakeWs(responses)
    register_action_tools(mcp, ws)
    return mcp.tools


def test_get_actions_missing_service_returns_compatibility():
    tools = _get_action_tools({"/rosapi/services": {"values": {"services": ["/rosapi/topics"]}}})
    result = tools["get_actions"]()
    assert "error" in result
    assert "compatibility" in result
    assert "/rosapi/action_servers" in result["compatibility"]["missing_services"]
    assert result["action_count"] == 0
    assert result["actions"] == []


def test_get_actions_success():
    tools = _get_action_tools(
        {
            "/rosapi/services": {"values": {"services": ["/rosapi/action_servers"]}},
            "/rosapi/action_servers": {"values": {"action_servers": ["/turtle1/rotate_absolute"]}},
        }
    )
    result = tools["get_actions"]()
    assert result["action_count"] == 1
    assert result["actions"] == ["/turtle1/rotate_absolute"]


def test_get_action_details_missing_interfaces_returns_compatibility():
    tools = _get_action_tools(
        {
            "/rosapi/services": {"values": {"services": ["/rosapi/action_servers"]}},
            "/rosapi/interfaces": {
                "result": False,
                "error": "service /rosapi/interfaces does not exist",
            },
        }
    )
    result = tools["get_action_details"](
        action="/turtle1/rotate_absolute", action_type="turtlesim/action/RotateAbsolute"
    )
    assert "error" in result
    assert "compatibility" in result
    assert "/rosapi/interfaces" in result["compatibility"]["missing_services"]


def test_get_action_status_on_ros1_returns_clean_warning():
    _resolver._version = RosVersion.ROS1
    tools = _get_action_tools()
    result = tools["get_action_status"](action_name="/turtle_shape")
    assert "warning" in result
    assert "compatibility" in result
    assert result["action_name"] == "/turtle_shape"
    assert result["active_goals"] == []
    assert result["goal_count"] == 0


def test_send_action_goal_on_ros1_returns_clean_error():
    _resolver._version = RosVersion.ROS1
    tools = _get_action_tools()
    result = asyncio.run(
        tools["send_action_goal"](
            action_name="/turtle_shape",
            action_type="turtle_actionlib/ShapeAction",
            goal={"edges": 4, "radius": 2.0},
        )
    )
    assert result["success"] is False
    assert "error" in result
    assert "send_action_goal is not available on ROS 1" in result["error"]
    assert "compatibility" in result


def test_cancel_action_goal_on_ros1_returns_clean_error():
    _resolver._version = RosVersion.ROS1
    tools = _get_action_tools()
    result = tools["cancel_action_goal"](
        action_name="/turtle_shape",
        goal_id="goal_123",
    )
    assert result["success"] is False
    assert "error" in result
    assert "cancel_action_goal is not available on ROS 1" in result["error"]
    assert "compatibility" in result
