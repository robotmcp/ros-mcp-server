"""Integration tests for action tools.

These tests call the actual MCP tool functions (get_actions, get_action_details,
get_action_status) against a live rosbridge container.

Action servers per distro:
- ROS 1 (melodic/noetic): /shape_server (from turtle_actionlib)
- ROS 2 (humble/jazzy): /turtle1/rotate_absolute (from turtlesim)

get_action_details and get_action_status use ROS 2-only rosbridge features
(/rosapi/interfaces, send_action_goal op). See issue #320 for ROS 1 support
via the 5-topic actionlib pattern.
"""

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
        """get_action_details without action_type should error (action_type is required)."""
        result = tools["get_action_details"](action="/nonexistent_action_xyz")
        assert "error" in result

    def test_nonexistent_action_type_returns_error(self, tools):
        """get_action_details with a bogus action_type should return a no-definition error."""
        result = tools["get_action_details"](
            action="/nonexistent_action_xyz",
            action_type="nonexistent_pkg/action/DoesNotExist",
        )
        assert "error" in result


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
        """get_action_status should return status structure."""
        result = tools["get_action_status"](action_name=_action()["name"])
        assert "action_name" in result

    def test_empty_action_returns_error(self, tools):
        """get_action_status with empty string should return error."""
        result = tools["get_action_status"](action_name="")
        assert "error" in result
