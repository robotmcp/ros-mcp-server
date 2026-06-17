"""Integration tests for topic tools.

These tests call the actual MCP tool functions (get_topics, get_topic_type,
get_topic_details, get_message_details, subscribe_once, subscribe_for_duration,
publish_once, publish_for_durations) against a live rosbridge container.
"""

import json
import time

import pytest

pytestmark = [pytest.mark.integration]


def _get_type(tools, topic):
    """Get the msg type for a topic, failing the test with a clear message if not found."""
    result = tools["get_topic_type"](topic=topic)
    assert "type" in result, f"get_topic_type failed for {topic}: {result}"
    return result["type"]


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
        assert any("cmd_vel" in t for t in result["topics"]), f"cmd_vel not in {result['topics']}"


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
        """get_topic_details for /turtle1/pose should have turtlesim as publisher."""
        result = tools["get_topic_details"](topic="/turtle1/pose")
        assert result["topic"] == "/turtle1/pose"
        assert "Pose" in result["type"]
        assert result["publisher_count"] > 0
        assert any("turtlesim" in p for p in result["publishers"]), result["publishers"]

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
        pose_type = _get_type(tools, "/turtle1/pose")
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


class TestSubscribeForDuration:
    """Verify subscribe_for_duration MCP tool collects messages over time."""

    def test_collect_pose_messages(self, tools):
        """subscribe_for_duration on /turtle1/pose should collect multiple messages."""
        pose_type = _get_type(tools, "/turtle1/pose")
        result = tools["subscribe_for_duration"](
            topic="/turtle1/pose",
            msg_type=pose_type,
            duration=2.0,
            max_messages=5,
        )
        # subscribe_for_duration returns a ToolResult; summary is in content[0].text
        assert hasattr(result, "content"), f"subscribe_for_duration failed: {result}"
        summary = json.loads(result.content[0].text)
        assert summary["collected_count"] > 0
        assert summary["topic"] == "/turtle1/pose"

    def test_missing_args_returns_error(self, tools):
        """subscribe_for_duration without topic/msg_type should return error."""
        result = tools["subscribe_for_duration"]()
        assert "error" in result


class TestPublishOnce:
    """Verify publish_once MCP tool sends a message."""

    def test_publish_cmd_vel(self, tools):
        """publish_once should successfully publish a Twist to /turtle1/cmd_vel."""
        cmd_vel_type = _get_type(tools, "/turtle1/cmd_vel")
        result = tools["publish_once"](
            topic="/turtle1/cmd_vel",
            msg_type=cmd_vel_type,
            msg={"linear": {"x": 0.1, "y": 0.0, "z": 0.0}},
        )
        assert result.get("success") is True, f"publish_once failed: {result}"

    def test_empty_msg_returns_error(self, tools):
        """publish_once with empty msg should return error."""
        result = tools["publish_once"](
            topic="/turtle1/cmd_vel",
            msg_type="geometry_msgs/Twist",
            msg={},
        )
        assert "error" in result

    def test_missing_topic_returns_error(self, tools):
        """publish_once without topic should return error."""
        result = tools["publish_once"]()
        assert "error" in result


class TestPublishForDurations:
    """Verify publish_for_durations MCP tool sends a sequence of messages."""

    def test_publish_sequence(self, tools):
        """publish_for_durations should publish a message sequence."""
        cmd_vel_type = _get_type(tools, "/turtle1/cmd_vel")
        messages = [{"linear": {"x": 0.1}}, {"linear": {"x": 0.0}}]
        result = tools["publish_for_durations"](
            topic="/turtle1/cmd_vel",
            msg_type=cmd_vel_type,
            messages=messages,
            durations=[0.5, 0.1],
            rate_hz=0,
        )
        assert result.get("success") is True, f"publish_for_durations failed: {result}"
        # published_count may be < total on some distros due to rosbridge response
        # timing in non-streaming mode (rate_hz=0), but it must never exceed the
        # number of messages requested.
        published = result["published_count"]
        assert 1 <= published <= len(messages), (
            f"expected 1..{len(messages)} published, got {published}: {result}"
        )

    def test_empty_sequence(self, tools):
        """publish_for_durations with empty lists should succeed with 0 published."""
        cmd_vel_type = _get_type(tools, "/turtle1/cmd_vel")
        result = tools["publish_for_durations"](
            topic="/turtle1/cmd_vel",
            msg_type=cmd_vel_type,
            messages=[],
            durations=[],
        )
        assert result.get("success") is True
        assert result["published_count"] == 0

    def test_missing_args_returns_error(self, tools):
        """publish_for_durations without topic/msg_type should return error."""
        result = tools["publish_for_durations"]()
        assert "error" in result


class TestPublishAndSubscribe:
    """End-to-end: publish cmd_vel and verify turtle moves via pose subscription."""

    def test_turtle_moves_after_publish(self, tools):
        """Publish a velocity, then check that the turtle's position changed."""
        pose_type = _get_type(tools, "/turtle1/pose")

        # Get initial pose
        before = tools["subscribe_once"](topic="/turtle1/pose", msg_type=pose_type, timeout=5.0)
        assert "msg" in before, f"Failed to get initial pose: {before}"
        x_before = before["msg"]["x"]

        # Publish forward velocity
        cmd_vel_type = _get_type(tools, "/turtle1/cmd_vel")
        pub_result = tools["publish_for_durations"](
            topic="/turtle1/cmd_vel",
            msg_type=cmd_vel_type,
            messages=[{"linear": {"x": 1.0, "y": 0.0, "z": 0.0}}],
            durations=[1.0],
            rate_hz=10,
        )
        assert pub_result.get("success") is True

        # Wait briefly for physics to update
        time.sleep(0.5)

        # Get new pose
        after = tools["subscribe_once"](topic="/turtle1/pose", msg_type=pose_type, timeout=5.0)
        assert "msg" in after, f"Failed to get new pose: {after}"
        x_after = after["msg"]["x"]

        # Forward velocity (linear.x > 0) should increase x specifically.
        assert x_after > x_before, (
            f"Turtle did not move forward: x_before={x_before}, x_after={x_after}"
        )
