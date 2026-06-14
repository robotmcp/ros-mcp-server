"""Integration tests for action tools.

These tests call the actual MCP tool functions (get_actions, get_action_details,
get_action_status, send_action_goal, cancel_action_goal) against a live
rosbridge container.

Action servers per distro:
- ROS 1 (melodic/noetic): /shape_server (from turtle_actionlib)
- ROS 2 (humble/jazzy): /turtle1/rotate_absolute (from turtlesim)

get_action_details and get_action_status use ROS 2-only rosbridge features
(/rosapi/interfaces, send_action_goal op). See issue #320 for ROS 1 support
via the 5-topic actionlib pattern.
"""

import asyncio

import pytest

from ros_mcp.utils.rosapi_types import RosVersion, get_ros_version

pytestmark = [pytest.mark.integration]


_ACTIONS = {
    RosVersion.ROS1: {
        "name": "/turtle_shape",
        "type": "turtle_actionlib/ShapeAction",
    },
    RosVersion.ROS2: {
        "name": "/turtle1/rotate_absolute",
        "type": "turtlesim/action/RotateAbsolute",
    },
}


def _action():
    """Return the action dict (name, type) for the current distro."""
    return _ACTIONS[get_ros_version()]


class TestGetActions:
    """Verify get_actions MCP tool returns the action list."""

    def test_returns_actions(self, tools):
        """get_actions should return actions and action_count."""
        result = tools["get_actions"]()
        assert "actions" in result
        assert "action_count" in result
        assert result["action_count"] > 0
        assert result["action_count"] == len(result["actions"])

    def test_includes_expected_action(self, tools):
        """The expected action server should be present."""
        result = tools["get_actions"]()
        actions = result["actions"]
        expected = _action()["name"]
        assert any(expected in a for a in actions), f"{expected} not in {actions}"


class TestGetActionDetails:
    """Verify get_action_details MCP tool returns action structure.

    Detail inspection requires /rosapi/interfaces (ROS 2 only).
    """

    @pytest.mark.skipif(
        "get_ros_version() != RosVersion.ROS2",
        reason="Action detail inspection requires /rosapi/interfaces (ROS 2 only, see #320)",
    )
    def test_action_details(self, tools):
        """get_action_details should return goal/result/feedback structure."""
        action = _action()["name"]
        result = tools["get_action_details"](action=action, action_type=_action()["type"])
        assert result["action"] == action
        assert "goal" in result
        assert "result" in result
        assert "feedback" in result
        assert result["goal"]["field_count"] > 0

    def test_empty_action_returns_error(self, tools):
        """get_action_details with empty string should return error."""
        result = tools["get_action_details"](action="")
        assert "error" in result

    def test_missing_action_type_returns_error(self, tools):
        """Without action_type, the error must also list the available types."""
        result = tools["get_action_details"](action="/nonexistent_action_xyz")
        assert "error" in result
        assert "action_type is required" in result["error"]
        # The caller is told which types they could pass instead.
        assert isinstance(result["available_action_types"], list)

    @pytest.mark.skipif(
        "get_ros_version() != RosVersion.ROS2",
        reason="action_type validation/crash is ROS 2 rosapi-specific (see #320)",
    )
    def test_nonexistent_action_type_does_not_crash_rosapi(self, tools):
        """A bogus action_type must be rejected WITHOUT crashing rosapi.

        get_action_details validates action_type against /rosapi/interfaces
        before querying its details, because asking rosapi for the
        goal/result/feedback of a non-existent type crashes the ROS 2 rosapi
        node — taking down every rosapi service for the rest of the session.
        This test locks in that guard: it asserts the type is rejected AND that
        rosapi is still answering afterwards.
        """
        result = tools["get_action_details"](
            action="/nonexistent_action_xyz",
            action_type="nonexistent_pkg/action/DoesNotExist",
        )
        # An unknown type must be reported as an error, never silently accepted.
        assert "error" in result

        # The crash check — this is the assertion that catches the regression,
        # independent of how the error is worded. Querying detail services for a
        # non-existent type used to kill the ROS 2 rosapi node; a follow-up
        # rosapi-backed call then fails with "service does not exist". If the
        # guard is removed, this assertion fails here.
        nodes_result = tools["get_nodes"]()
        assert "nodes" in nodes_result, f"rosapi crashed after bogus action_type: {nodes_result}"

        # The rejection should come from the interfaces validation, not from
        # reaching (and crashing on) the detail services.
        assert "not found" in result["error"].lower()
        assert isinstance(result["available_action_types"], list)


class TestGetActionStatus:
    """Verify get_action_status MCP tool returns status info.

    Status subscription works on ROS 2. On ROS 1, the status topic
    format differs (see #320).
    """

    @pytest.mark.skipif(
        "get_ros_version() != RosVersion.ROS2",
        reason="Action status subscription uses ROS 2 topic format (see #320)",
    )
    def test_action_status(self, tools):
        """get_action_status should echo the action and report goal status.

        With no goal in flight the action is reported as idle (goal_count 0),
        not an error; goal_count must always match the active_goals list.
        """
        action_name = _action()["name"]
        result = tools["get_action_status"](action_name=action_name)
        assert result.get("action_name") == action_name
        assert "error" not in result, f"unexpected error: {result}"
        assert result["goal_count"] == len(result["active_goals"])

    def test_empty_action_returns_error(self, tools):
        """get_action_status with empty string should return error."""
        result = tools["get_action_status"](action_name="")
        assert "error" in result


class TestSendActionGoal:
    """Verify send_action_goal MCP tool.

    Sending a goal uses the ROS 2 rosbridge ``send_action_goal`` op; on ROS 1
    actions use a different transport (see #320). The async tool is driven with
    ``asyncio.run`` since the suite has no asyncio plugin.
    """

    def test_empty_action_returns_error(self, tools):
        result = asyncio.run(
            tools["send_action_goal"](action_name="", action_type="x", goal={"a": 1})
        )
        assert "error" in result

    def test_empty_type_returns_error(self, tools):
        result = asyncio.run(
            tools["send_action_goal"](action_name="/a", action_type="", goal={"a": 1})
        )
        assert "error" in result

    def test_empty_goal_returns_error(self, tools):
        result = asyncio.run(tools["send_action_goal"](action_name="/a", action_type="x", goal={}))
        assert "error" in result

    @pytest.mark.skipif(
        "get_ros_version() != RosVersion.ROS2",
        reason="send_action_goal uses the ROS 2 rosbridge action op (see #320)",
    )
    def test_send_goal_completes(self, tools):
        """A goal to rotate_absolute should run to completion and return a result."""
        action = _action()
        result = asyncio.run(
            tools["send_action_goal"](
                action_name=action["name"],
                action_type=action["type"],
                goal={"theta": 1.0},
                timeout=10.0,
            )
        )
        assert result["success"] is True, f"goal did not complete: {result}"
        assert result["goal_id"]
        assert "result" in result


class TestCancelActionGoal:
    """Verify cancel_action_goal MCP tool."""

    def test_empty_action_returns_error(self, tools):
        result = tools["cancel_action_goal"](action_name="", goal_id="g")
        assert "error" in result

    def test_empty_goal_id_returns_error(self, tools):
        result = tools["cancel_action_goal"](action_name="/a", goal_id="")
        assert "error" in result

    @pytest.mark.skipif(
        "get_ros_version() != RosVersion.ROS2",
        reason="cancel_action_goal uses the ROS 2 rosbridge action op (see #320)",
    )
    def test_cancel_request_sent(self, tools):
        """Cancelling reports success once the request is sent (not server-acked)."""
        action_name = _action()["name"]
        result = tools["cancel_action_goal"](action_name=action_name, goal_id="nonexistent_goal")
        assert result["success"] is True
        assert result["action"] == action_name
