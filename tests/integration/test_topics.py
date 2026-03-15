"""Integration tests for topic tools against a real ROS2 rosbridge."""

import pytest

pytestmark = [pytest.mark.integration, pytest.mark.slow]


class TestGetTopics:
    def test_returns_topics(self, tools):
        result = tools["get_topics"]()
        assert "topics" in result
        assert len(result["topics"]) > 0

    def test_includes_turtlesim_topics(self, tools):
        result = tools["get_topics"]()
        topics = result["topics"]
        assert any("/turtle1/cmd_vel" in t for t in topics)
        assert any("/turtle1/pose" in t for t in topics)

    def test_has_topic_count(self, tools):
        result = tools["get_topics"]()
        assert result["topic_count"] == len(result["topics"])


class TestGetTopicType:
    def test_cmd_vel_is_twist(self, tools):
        result = tools["get_topic_type"](topic="/turtle1/cmd_vel")
        assert "type" in result
        assert "Twist" in result["type"]

    def test_pose_type(self, tools):
        result = tools["get_topic_type"](topic="/turtle1/pose")
        assert "type" in result
        assert "Pose" in result["type"]

    def test_nonexistent_topic(self, tools):
        result = tools["get_topic_type"](topic="/nonexistent_topic_xyz")
        assert "error" in result


class TestGetTopicDetails:
    def test_cmd_vel_details(self, tools):
        result = tools["get_topic_details"](topic="/turtle1/cmd_vel")
        assert result.get("type") != "unknown"
        assert "publisher_count" in result
        assert "subscriber_count" in result


class TestGetMessageDetails:
    def test_twist_structure(self, tools):
        result = tools["get_message_details"](message_type="geometry_msgs/Twist")
        assert "structure" in result
        assert "error" not in result


class TestSubscribeOnce:
    def test_subscribe_to_pose(self, tools):
        result = tools["subscribe_once"](
            topic="/turtle1/pose",
            msg_type="turtlesim/msg/Pose",
            timeout=5.0,
        )
        assert "msg" in result
        msg = result["msg"]
        assert "x" in msg
        assert "y" in msg
        assert "theta" in msg
