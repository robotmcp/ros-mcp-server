"""Tests for ros_mcp.tools.topics module."""

import json
from unittest.mock import MagicMock, patch

import pytest

from tests.conftest import MockWebSocketManager


class TestGetTopics:
    """Test cases for get_topics tool."""

    def test_returns_topic_list(self, sample_topics_response):
        """Test that get_topics returns list of topics."""
        from fastmcp import FastMCP

        from ros_mcp.tools.topics import register_topic_tools

        mcp = FastMCP("test")
        ws_manager = MockWebSocketManager()
        ws_manager.add_response(sample_topics_response)

        register_topic_tools(mcp, ws_manager)

        tools = mcp._tool_manager._tools
        get_topics_tool = tools.get("get_topics")
        assert get_topics_tool is not None

        result = get_topics_tool.fn()

        assert "topics" in result
        assert "types" in result
        assert "topic_count" in result
        assert len(result["topics"]) == 5
        assert "/turtle1/cmd_vel" in result["topics"]

    def test_empty_response(self):
        """Test handling of empty topics response."""
        from fastmcp import FastMCP

        from ros_mcp.tools.topics import register_topic_tools

        mcp = FastMCP("test")
        ws_manager = MockWebSocketManager()
        ws_manager.add_response({"result": True, "values": {"topics": [], "types": []}})

        register_topic_tools(mcp, ws_manager)

        tools = mcp._tool_manager._tools
        get_topics_tool = tools.get("get_topics")

        result = get_topics_tool.fn()

        assert result["topic_count"] == 0

    def test_service_error(self):
        """Test handling of service call error."""
        from fastmcp import FastMCP

        from ros_mcp.tools.topics import register_topic_tools

        mcp = FastMCP("test")
        ws_manager = MockWebSocketManager()
        ws_manager.add_response(
            {"result": False, "values": {"message": "Service not available"}}
        )

        register_topic_tools(mcp, ws_manager)

        tools = mcp._tool_manager._tools
        get_topics_tool = tools.get("get_topics")

        result = get_topics_tool.fn()

        assert "error" in result

    def test_no_response(self):
        """Test handling when no response received."""
        from fastmcp import FastMCP

        from ros_mcp.tools.topics import register_topic_tools

        mcp = FastMCP("test")
        ws_manager = MockWebSocketManager()
        # No response added

        register_topic_tools(mcp, ws_manager)

        tools = mcp._tool_manager._tools
        get_topics_tool = tools.get("get_topics")

        result = get_topics_tool.fn()

        assert "warning" in result or "error" in result


class TestGetTopicType:
    """Test cases for get_topic_type tool."""

    def test_returns_topic_type(self):
        """Test that get_topic_type returns the correct type."""
        from fastmcp import FastMCP

        from ros_mcp.tools.topics import register_topic_tools

        mcp = FastMCP("test")
        ws_manager = MockWebSocketManager()
        ws_manager.add_response(
            {"result": True, "values": {"type": "geometry_msgs/msg/Twist"}}
        )

        register_topic_tools(mcp, ws_manager)

        tools = mcp._tool_manager._tools
        get_topic_type_tool = tools.get("get_topic_type")

        result = get_topic_type_tool.fn(topic="/turtle1/cmd_vel")

        assert result["topic"] == "/turtle1/cmd_vel"
        assert result["type"] == "geometry_msgs/msg/Twist"

    def test_empty_topic_name(self):
        """Test error when topic name is empty."""
        from fastmcp import FastMCP

        from ros_mcp.tools.topics import register_topic_tools

        mcp = FastMCP("test")
        ws_manager = MockWebSocketManager()

        register_topic_tools(mcp, ws_manager)

        tools = mcp._tool_manager._tools
        get_topic_type_tool = tools.get("get_topic_type")

        result = get_topic_type_tool.fn(topic="")

        assert "error" in result
        assert "empty" in result["error"].lower()

    def test_nonexistent_topic(self):
        """Test handling of non-existent topic."""
        from fastmcp import FastMCP

        from ros_mcp.tools.topics import register_topic_tools

        mcp = FastMCP("test")
        ws_manager = MockWebSocketManager()
        ws_manager.add_response({"result": True, "values": {"type": ""}})

        register_topic_tools(mcp, ws_manager)

        tools = mcp._tool_manager._tools
        get_topic_type_tool = tools.get("get_topic_type")

        result = get_topic_type_tool.fn(topic="/nonexistent")

        assert "error" in result


class TestSubscribeOnce:
    """Test cases for subscribe_once tool."""

    def test_receives_first_message(self, sample_pose_message):
        """Test that subscribe_once returns the first message."""
        from fastmcp import FastMCP

        from ros_mcp.tools.topics import register_topic_tools

        mcp = FastMCP("test")
        ws_manager = MockWebSocketManager()
        ws_manager.add_response(sample_pose_message)

        register_topic_tools(mcp, ws_manager)

        tools = mcp._tool_manager._tools
        subscribe_once_tool = tools.get("subscribe_once")

        result = subscribe_once_tool.fn(
            topic="/turtle1/pose", msg_type="turtlesim/msg/Pose"
        )

        assert "msg" in result
        assert result["msg"]["x"] == 5.544444561004639

    def test_missing_topic(self):
        """Test error when topic is missing."""
        from fastmcp import FastMCP

        from ros_mcp.tools.topics import register_topic_tools

        mcp = FastMCP("test")
        ws_manager = MockWebSocketManager()

        register_topic_tools(mcp, ws_manager)

        tools = mcp._tool_manager._tools
        subscribe_once_tool = tools.get("subscribe_once")

        result = subscribe_once_tool.fn(topic="", msg_type="std_msgs/String")

        assert "error" in result

    def test_missing_msg_type(self):
        """Test error when msg_type is missing."""
        from fastmcp import FastMCP

        from ros_mcp.tools.topics import register_topic_tools

        mcp = FastMCP("test")
        ws_manager = MockWebSocketManager()

        register_topic_tools(mcp, ws_manager)

        tools = mcp._tool_manager._tools
        subscribe_once_tool = tools.get("subscribe_once")

        result = subscribe_once_tool.fn(topic="/test", msg_type="")

        assert "error" in result

    def test_timeout_returns_error(self):
        """Test that timeout returns error."""
        from fastmcp import FastMCP

        from ros_mcp.tools.topics import register_topic_tools

        mcp = FastMCP("test")
        ws_manager = MockWebSocketManager()
        # No responses - will timeout

        register_topic_tools(mcp, ws_manager)

        tools = mcp._tool_manager._tools
        subscribe_once_tool = tools.get("subscribe_once")

        result = subscribe_once_tool.fn(
            topic="/test", msg_type="std_msgs/String", timeout=0.1
        )

        assert "error" in result
        assert "timeout" in result["error"].lower()

    def test_invalid_timeout(self):
        """Test error for invalid timeout value."""
        from fastmcp import FastMCP

        from ros_mcp.tools.topics import register_topic_tools

        mcp = FastMCP("test")
        ws_manager = MockWebSocketManager()

        register_topic_tools(mcp, ws_manager)

        tools = mcp._tool_manager._tools
        subscribe_once_tool = tools.get("subscribe_once")

        result = subscribe_once_tool.fn(
            topic="/test", msg_type="std_msgs/String", timeout=-1.0
        )

        assert "error" in result

    def test_invalid_queue_length(self):
        """Test error for invalid queue_length value."""
        from fastmcp import FastMCP

        from ros_mcp.tools.topics import register_topic_tools

        mcp = FastMCP("test")
        ws_manager = MockWebSocketManager()

        register_topic_tools(mcp, ws_manager)

        tools = mcp._tool_manager._tools
        subscribe_once_tool = tools.get("subscribe_once")

        result = subscribe_once_tool.fn(
            topic="/test", msg_type="std_msgs/String", queue_length=0
        )

        assert "error" in result

    def test_rosbridge_error_handling(self):
        """Test handling of rosbridge error status."""
        from fastmcp import FastMCP

        from ros_mcp.tools.topics import register_topic_tools

        mcp = FastMCP("test")
        ws_manager = MockWebSocketManager()
        ws_manager.add_response(
            {"op": "status", "level": "error", "msg": "Topic not found"}
        )

        register_topic_tools(mcp, ws_manager)

        tools = mcp._tool_manager._tools
        subscribe_once_tool = tools.get("subscribe_once")

        result = subscribe_once_tool.fn(
            topic="/test", msg_type="std_msgs/String", timeout=0.5
        )

        assert "error" in result


class TestPublishOnce:
    """Test cases for publish_once tool."""

    def test_publish_success(self):
        """Test successful message publish."""
        from fastmcp import FastMCP

        from ros_mcp.tools.topics import register_topic_tools

        mcp = FastMCP("test")
        ws_manager = MockWebSocketManager()
        # Add responses for advertise and publish
        ws_manager.add_response(None)  # advertise response
        ws_manager.add_response(None)  # publish response

        register_topic_tools(mcp, ws_manager)

        tools = mcp._tool_manager._tools
        publish_once_tool = tools.get("publish_once")

        result = publish_once_tool.fn(
            topic="/turtle1/cmd_vel",
            msg_type="geometry_msgs/msg/Twist",
            msg={"linear": {"x": 1.0}},
        )

        assert result["success"] is True

    def test_empty_topic(self):
        """Test error when topic is empty."""
        from fastmcp import FastMCP

        from ros_mcp.tools.topics import register_topic_tools

        mcp = FastMCP("test")
        ws_manager = MockWebSocketManager()

        register_topic_tools(mcp, ws_manager)

        tools = mcp._tool_manager._tools
        publish_once_tool = tools.get("publish_once")

        result = publish_once_tool.fn(
            topic="", msg_type="geometry_msgs/msg/Twist", msg={"linear": {"x": 1.0}}
        )

        assert "error" in result

    def test_empty_msg_type(self):
        """Test error when msg_type is empty."""
        from fastmcp import FastMCP

        from ros_mcp.tools.topics import register_topic_tools

        mcp = FastMCP("test")
        ws_manager = MockWebSocketManager()

        register_topic_tools(mcp, ws_manager)

        tools = mcp._tool_manager._tools
        publish_once_tool = tools.get("publish_once")

        result = publish_once_tool.fn(
            topic="/test", msg_type="", msg={"data": "test"}
        )

        assert "error" in result

    def test_empty_message(self):
        """Test error when message is empty."""
        from fastmcp import FastMCP

        from ros_mcp.tools.topics import register_topic_tools

        mcp = FastMCP("test")
        ws_manager = MockWebSocketManager()

        register_topic_tools(mcp, ws_manager)

        tools = mcp._tool_manager._tools
        publish_once_tool = tools.get("publish_once")

        result = publish_once_tool.fn(
            topic="/test", msg_type="std_msgs/String", msg={}
        )

        assert "error" in result

    def test_invalid_message_type(self):
        """Test error when message is not a dict."""
        from fastmcp import FastMCP

        from ros_mcp.tools.topics import register_topic_tools

        mcp = FastMCP("test")
        ws_manager = MockWebSocketManager()

        register_topic_tools(mcp, ws_manager)

        tools = mcp._tool_manager._tools
        publish_once_tool = tools.get("publish_once")

        # Passing a non-dict that can't be converted will raise ValueError
        # The function uses dict(msg) which fails on strings
        try:
            result = publish_once_tool.fn(
                topic="/test", msg_type="std_msgs/String", msg="not a dict"
            )
            # If it returns without error, check for error in result
            assert "error" in result
        except (ValueError, TypeError):
            # Expected - dict() can't convert a simple string
            pass


class TestPublishForDurations:
    """Test cases for publish_for_durations tool."""

    def test_publish_sequence(self):
        """Test publishing a sequence of messages."""
        from fastmcp import FastMCP

        from ros_mcp.tools.topics import register_topic_tools

        mcp = FastMCP("test")
        ws_manager = MockWebSocketManager()
        # Add responses for advertise and each publish
        ws_manager.add_responses([None, None, None, None])

        register_topic_tools(mcp, ws_manager)

        tools = mcp._tool_manager._tools
        publish_tool = tools.get("publish_for_durations")

        result = publish_tool.fn(
            topic="/test",
            msg_type="std_msgs/String",
            messages=[{"data": "msg1"}, {"data": "msg2"}],
            durations=[0.0, 0.0],
        )

        assert result["success"] is True
        assert result["total_messages"] == 2

    def test_empty_messages(self):
        """Test with empty message list."""
        from fastmcp import FastMCP

        from ros_mcp.tools.topics import register_topic_tools

        mcp = FastMCP("test")
        ws_manager = MockWebSocketManager()

        register_topic_tools(mcp, ws_manager)

        tools = mcp._tool_manager._tools
        publish_tool = tools.get("publish_for_durations")

        result = publish_tool.fn(
            topic="/test", msg_type="std_msgs/String", messages=[], durations=[]
        )

        assert result["success"] is True
        assert result["published_count"] == 0

    def test_mismatched_lengths(self):
        """Test error when messages and durations have different lengths."""
        from fastmcp import FastMCP

        from ros_mcp.tools.topics import register_topic_tools

        mcp = FastMCP("test")
        ws_manager = MockWebSocketManager()

        register_topic_tools(mcp, ws_manager)

        tools = mcp._tool_manager._tools
        publish_tool = tools.get("publish_for_durations")

        result = publish_tool.fn(
            topic="/test",
            msg_type="std_msgs/String",
            messages=[{"data": "msg1"}],
            durations=[0.0, 1.0],
        )

        assert "error" in result

    def test_negative_duration(self):
        """Test error for negative duration values."""
        from fastmcp import FastMCP

        from ros_mcp.tools.topics import register_topic_tools

        mcp = FastMCP("test")
        ws_manager = MockWebSocketManager()

        register_topic_tools(mcp, ws_manager)

        tools = mcp._tool_manager._tools
        publish_tool = tools.get("publish_for_durations")

        result = publish_tool.fn(
            topic="/test",
            msg_type="std_msgs/String",
            messages=[{"data": "msg1"}],
            durations=[-1.0],
        )

        assert "error" in result


class TestSubscribeForDuration:
    """Test cases for subscribe_for_duration tool."""

    def test_collects_messages(self, sample_pose_message):
        """Test collecting multiple messages over duration."""
        from fastmcp import FastMCP

        from ros_mcp.tools.topics import register_topic_tools

        mcp = FastMCP("test")
        ws_manager = MockWebSocketManager()
        # Add multiple pose messages
        ws_manager.add_responses([sample_pose_message, sample_pose_message])

        register_topic_tools(mcp, ws_manager)

        tools = mcp._tool_manager._tools
        subscribe_tool = tools.get("subscribe_for_duration")

        result = subscribe_tool.fn(
            topic="/turtle1/pose",
            msg_type="turtlesim/msg/Pose",
            duration=0.2,
            max_messages=10,
        )

        assert "messages" in result
        assert "collected_count" in result

    def test_max_messages_limit(self, sample_pose_message):
        """Test that max_messages limits collection."""
        from fastmcp import FastMCP

        from ros_mcp.tools.topics import register_topic_tools

        mcp = FastMCP("test")
        ws_manager = MockWebSocketManager()
        # Add many responses
        for _ in range(10):
            ws_manager.add_response(sample_pose_message)

        register_topic_tools(mcp, ws_manager)

        tools = mcp._tool_manager._tools
        subscribe_tool = tools.get("subscribe_for_duration")

        result = subscribe_tool.fn(
            topic="/turtle1/pose",
            msg_type="turtlesim/msg/Pose",
            duration=5.0,  # Long duration
            max_messages=2,  # But limited messages
        )

        assert result["collected_count"] <= 2

    def test_missing_required_args(self):
        """Test error when required arguments are missing."""
        from fastmcp import FastMCP

        from ros_mcp.tools.topics import register_topic_tools

        mcp = FastMCP("test")
        ws_manager = MockWebSocketManager()

        register_topic_tools(mcp, ws_manager)

        tools = mcp._tool_manager._tools
        subscribe_tool = tools.get("subscribe_for_duration")

        result = subscribe_tool.fn(topic="", msg_type="")

        assert "error" in result
