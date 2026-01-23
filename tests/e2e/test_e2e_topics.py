"""E2E tests for topic operations with real ROS 2 turtlesim."""

import json
import math
import time

import pytest

from tests.e2e.conftest import get_turtle_pose, reset_turtle, teleport_turtle


pytestmark = pytest.mark.e2e


class TestGetTopics:
    """E2E tests for get_topics functionality."""

    def test_get_topics_returns_turtlesim_topics(self, ws_manager, turtlesim_topics):
        """Verify turtlesim topics exist in topic list."""
        message = {
            "op": "call_service",
            "service": "/rosapi/topics",
            "type": "rosapi/Topics",
            "args": {},
            "id": "get_topics_e2e",
        }

        with ws_manager:
            response = ws_manager.request(message, timeout=10.0)

        assert "values" in response, f"Expected values in response: {response}"
        topics = response["values"].get("topics", [])

        # Check for expected turtlesim topics
        for expected_topic in turtlesim_topics:
            assert expected_topic in topics, f"Expected {expected_topic} in topics"

    def test_get_topics_returns_types(self, ws_manager):
        """Verify topic types are returned correctly."""
        message = {
            "op": "call_service",
            "service": "/rosapi/topics",
            "type": "rosapi/Topics",
            "args": {},
            "id": "get_topics_types_e2e",
        }

        with ws_manager:
            response = ws_manager.request(message, timeout=10.0)

        assert "values" in response
        topics = response["values"].get("topics", [])
        types = response["values"].get("types", [])

        assert len(topics) == len(types), "Topics and types lists should have same length"

        # Find cmd_vel and verify its type
        if "/turtle1/cmd_vel" in topics:
            idx = topics.index("/turtle1/cmd_vel")
            assert "Twist" in types[idx], f"Expected Twist type, got {types[idx]}"


class TestGetTopicType:
    """E2E tests for get_topic_type functionality."""

    def test_get_topic_type_cmd_vel(self, ws_manager):
        """Verify type of cmd_vel topic."""
        message = {
            "op": "call_service",
            "service": "/rosapi/topic_type",
            "type": "rosapi/TopicType",
            "args": {"topic": "/turtle1/cmd_vel"},
            "id": "get_topic_type_e2e",
        }

        with ws_manager:
            response = ws_manager.request(message, timeout=10.0)

        assert "values" in response
        topic_type = response["values"].get("type", "")
        assert "Twist" in topic_type, f"Expected Twist type, got {topic_type}"

    def test_get_topic_type_pose(self, ws_manager):
        """Verify type of pose topic."""
        message = {
            "op": "call_service",
            "service": "/rosapi/topic_type",
            "type": "rosapi/TopicType",
            "args": {"topic": "/turtle1/pose"},
            "id": "get_topic_type_pose_e2e",
        }

        with ws_manager:
            response = ws_manager.request(message, timeout=10.0)

        assert "values" in response
        topic_type = response["values"].get("type", "")
        assert "Pose" in topic_type, f"Expected Pose type, got {topic_type}"


class TestSubscribeOnce:
    """E2E tests for subscribe_once functionality."""

    def test_subscribe_once_pose(self, ws_manager):
        """Subscribe to pose topic and verify message structure."""
        subscribe_msg = {
            "op": "subscribe",
            "topic": "/turtle1/pose",
            "type": "turtlesim/msg/Pose",
        }

        with ws_manager:
            ws_manager.send(subscribe_msg)

            # Wait for a pose message
            end_time = time.time() + 10.0
            received_msg = None

            while time.time() < end_time:
                response = ws_manager.receive(timeout=1.0)
                if response:
                    data = json.loads(response)
                    if data.get("op") == "publish" and data.get("topic") == "/turtle1/pose":
                        received_msg = data.get("msg", {})
                        break

            # Unsubscribe
            ws_manager.send({"op": "unsubscribe", "topic": "/turtle1/pose"})

        assert received_msg is not None, "Should receive pose message"
        assert "x" in received_msg, "Pose should have x coordinate"
        assert "y" in received_msg, "Pose should have y coordinate"
        assert "theta" in received_msg, "Pose should have theta"
        assert "linear_velocity" in received_msg, "Pose should have linear_velocity"
        assert "angular_velocity" in received_msg, "Pose should have angular_velocity"

    def test_subscribe_once_pose_values_reasonable(self, ws_manager):
        """Verify pose values are within expected bounds."""
        pose = get_turtle_pose(ws_manager)

        assert pose is not None, "Should receive pose"
        # Turtlesim window is 11x11
        assert 0.0 <= pose["x"] <= 11.0, f"x should be in [0, 11], got {pose['x']}"
        assert 0.0 <= pose["y"] <= 11.0, f"y should be in [0, 11], got {pose['y']}"
        # theta is in radians, typically -pi to pi
        assert -math.pi <= pose["theta"] <= math.pi or -2 * math.pi <= pose["theta"] <= 2 * math.pi


class TestPublishCmdVel:
    """E2E tests for publishing to cmd_vel topic."""

    def test_publish_cmd_vel_moves_turtle(self, ws_manager):
        """Verify publishing to cmd_vel moves the turtle."""
        # First, reset turtle and get initial pose
        reset_turtle(ws_manager)
        time.sleep(0.5)
        initial_pose = get_turtle_pose(ws_manager)
        assert initial_pose is not None, "Should get initial pose"

        # Teleport to known position
        teleport_turtle(ws_manager, 5.5, 5.5, 0.0)
        time.sleep(0.3)

        # Now publish a movement command
        with ws_manager:
            # Advertise
            advertise_msg = {
                "op": "advertise",
                "topic": "/turtle1/cmd_vel",
                "type": "geometry_msgs/msg/Twist",
            }
            ws_manager.send(advertise_msg)
            time.sleep(0.2)

            # Publish forward movement
            publish_msg = {
                "op": "publish",
                "topic": "/turtle1/cmd_vel",
                "msg": {
                    "linear": {"x": 2.0, "y": 0.0, "z": 0.0},
                    "angular": {"x": 0.0, "y": 0.0, "z": 0.0},
                },
            }
            ws_manager.send(publish_msg)
            time.sleep(0.5)  # Let the turtle move

            # Stop the turtle
            stop_msg = {
                "op": "publish",
                "topic": "/turtle1/cmd_vel",
                "msg": {
                    "linear": {"x": 0.0, "y": 0.0, "z": 0.0},
                    "angular": {"x": 0.0, "y": 0.0, "z": 0.0},
                },
            }
            ws_manager.send(stop_msg)

            # Unadvertise
            ws_manager.send({"op": "unadvertise", "topic": "/turtle1/cmd_vel"})

        # Get new pose and verify movement
        time.sleep(0.3)
        new_pose = get_turtle_pose(ws_manager)
        assert new_pose is not None, "Should get new pose"

        # Turtle should have moved forward (x increased since facing right at theta=0)
        assert new_pose["x"] > 5.5, f"Turtle should have moved right, x was 5.5, now {new_pose['x']}"

    def test_publish_angular_rotates_turtle(self, ws_manager):
        """Verify publishing angular velocity rotates the turtle."""
        # Reset and teleport to known position/orientation
        reset_turtle(ws_manager)
        teleport_turtle(ws_manager, 5.5, 5.5, 0.0)
        time.sleep(0.3)

        initial_pose = get_turtle_pose(ws_manager)
        initial_theta = initial_pose["theta"]

        # Publish rotation command
        with ws_manager:
            advertise_msg = {
                "op": "advertise",
                "topic": "/turtle1/cmd_vel",
                "type": "geometry_msgs/msg/Twist",
            }
            ws_manager.send(advertise_msg)
            time.sleep(0.2)

            # Rotate counter-clockwise
            publish_msg = {
                "op": "publish",
                "topic": "/turtle1/cmd_vel",
                "msg": {
                    "linear": {"x": 0.0, "y": 0.0, "z": 0.0},
                    "angular": {"x": 0.0, "y": 0.0, "z": 2.0},
                },
            }
            ws_manager.send(publish_msg)
            time.sleep(0.5)

            # Stop
            stop_msg = {
                "op": "publish",
                "topic": "/turtle1/cmd_vel",
                "msg": {
                    "linear": {"x": 0.0, "y": 0.0, "z": 0.0},
                    "angular": {"x": 0.0, "y": 0.0, "z": 0.0},
                },
            }
            ws_manager.send(stop_msg)
            ws_manager.send({"op": "unadvertise", "topic": "/turtle1/cmd_vel"})

        time.sleep(0.3)
        new_pose = get_turtle_pose(ws_manager)
        assert new_pose is not None, "Should get new pose"

        # Theta should have changed
        assert new_pose["theta"] != initial_theta, f"Turtle should have rotated"


class TestSubscribeForDuration:
    """E2E tests for subscribing for a duration."""

    def test_collect_multiple_pose_messages(self, ws_manager):
        """Verify collecting multiple messages over time."""
        subscribe_msg = {
            "op": "subscribe",
            "topic": "/turtle1/pose",
            "type": "turtlesim/msg/Pose",
        }

        messages = []

        with ws_manager:
            ws_manager.send(subscribe_msg)

            end_time = time.time() + 2.0  # Collect for 2 seconds
            while time.time() < end_time and len(messages) < 10:
                response = ws_manager.receive(timeout=0.5)
                if response:
                    data = json.loads(response)
                    if data.get("op") == "publish" and data.get("topic") == "/turtle1/pose":
                        messages.append(data.get("msg", {}))

            ws_manager.send({"op": "unsubscribe", "topic": "/turtle1/pose"})

        # Pose topic publishes at ~60Hz, so we should get multiple messages
        assert len(messages) > 1, f"Should collect multiple messages, got {len(messages)}"
