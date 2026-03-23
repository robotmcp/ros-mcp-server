"""Integration tests for topic tools (step 3).

These tests call the actual MCP tool functions (get_topics, get_topic_type,
get_topic_details, get_message_details, subscribe_once) against a live
rosbridge container.
"""

import pytest

pytestmark = [pytest.mark.integration]


class TestGetTopics:
    """Verify get_topics MCP tool returns the topic list."""

    def test_returns_topics(self, tools):
        """get_topics should return topics, types, and topic_count."""
        result = tools["get_topics"]()
        assert "topics" in result
        assert "types" in result
        assert "topic_count" in result
        assert result["topic_count"] > 0
        assert result["topic_count"] == len(result["topics"])
        assert len(result["types"]) == len(result["topics"])

    def test_includes_turtle_pose(self, tools):
        """turtlesim publishes /turtle1/pose — it should appear in topics."""
        result = tools["get_topics"]()
        assert any("/turtle1/pose" in t for t in result["topics"]), (
            f"/turtle1/pose not in {result['topics']}"
        )

    def test_includes_cmd_vel(self, tools):
        """turtlesim subscribes to /turtle1/cmd_vel — it should appear in topics."""
        result = tools["get_topics"]()
        assert any("cmd_vel" in t for t in result["topics"]), (
            f"cmd_vel not in {result['topics']}"
        )


class TestGetTopicType:
    """Verify get_topic_type MCP tool returns the message type."""

    def test_turtle_pose_type(self, tools):
        """get_topic_type for /turtle1/pose should return turtlesim/Pose."""
        result = tools["get_topic_type"](topic="/turtle1/pose")
        assert "type" in result
        assert "Pose" in result["type"]

    def test_empty_topic_returns_error(self, tools):
        """get_topic_type with empty string should return error."""
        result = tools["get_topic_type"](topic="")
        assert "error" in result


class TestGetTopicDetails:
    """Verify get_topic_details MCP tool returns type + publishers + subscribers."""

    def test_pose_details(self, tools):
        """get_topic_details for /turtle1/pose should have a publisher (turtlesim)."""
        result = tools["get_topic_details"](topic="/turtle1/pose")
        assert result["topic"] == "/turtle1/pose"
        assert "Pose" in result["type"]
        assert result["publisher_count"] > 0

    def test_empty_topic_returns_error(self, tools):
        """get_topic_details with empty string should return error."""
        result = tools["get_topic_details"](topic="")
        assert "error" in result


class TestGetMessageDetails:
    """Verify get_message_details MCP tool returns message structure."""

    def test_twist_structure(self, tools):
        """get_message_details for geometry_msgs/Twist should return fields."""
        result = tools["get_message_details"](message_type="geometry_msgs/Twist")
        assert "structure" in result, f"Unexpected result: {result}"
        assert len(result["structure"]) > 0

    def test_empty_type_returns_error(self, tools):
        """get_message_details with empty string should return error."""
        result = tools["get_message_details"](message_type="")
        assert "error" in result


class TestSubscribeOnce:
    """Verify subscribe_once MCP tool receives a message from a live topic."""

    def test_subscribe_to_pose(self, tools):
        """subscribe_once on /turtle1/pose should receive a Pose message."""
        # Get the actual type from get_topic_type (differs between ROS 1 and 2)
        type_result = tools["get_topic_type"](topic="/turtle1/pose")
        pose_type = type_result["type"]
        result = tools["subscribe_once"](
            topic="/turtle1/pose",
            msg_type=pose_type,
            timeout=5.0,
        )
        assert "msg" in result, f"subscribe_once failed: {result}"
        msg = result["msg"]
        assert "x" in msg
        assert "y" in msg

    def test_missing_args_returns_error(self, tools):
        """subscribe_once without topic/msg_type should return error."""
        result = tools["subscribe_once"]()
        assert "error" in result
