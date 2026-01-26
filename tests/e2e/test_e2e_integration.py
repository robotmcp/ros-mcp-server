"""E2E integration tests for multi-tool workflows."""

import json
import time

import pytest

from tests.e2e.conftest import get_turtle_pose, reset_turtle, teleport_turtle

pytestmark = pytest.mark.e2e


class TestDiscoverAndSubscribe:
    """E2E tests for discover-then-subscribe workflows."""

    def test_discover_topics_then_subscribe(self, ws_manager, rosapi_topics_type, msg_type_pose):
        """Test workflow: discover topics, then subscribe to one."""
        # Step 1: Discover topics
        topics_message = {
            "op": "call_service",
            "service": "/rosapi/topics",
            "type": rosapi_topics_type,
            "args": {},
            "id": "discover_topics",
        }

        with ws_manager:
            topics_response = ws_manager.request(topics_message, timeout=10.0)

        assert "values" in topics_response
        topics = topics_response["values"].get("topics", [])
        assert "/turtle1/pose" in topics, "Expected /turtle1/pose topic"

        # Step 2: Subscribe to the discovered topic
        subscribe_message = {
            "op": "subscribe",
            "topic": "/turtle1/pose",
            "type": msg_type_pose,
        }

        with ws_manager:
            ws_manager.send(subscribe_message)

            # Wait for message
            end_time = time.time() + 5.0
            received = False
            while time.time() < end_time:
                response = ws_manager.receive(timeout=0.5)
                if response:
                    data = json.loads(response)
                    if data.get("op") == "publish" and data.get("topic") == "/turtle1/pose":
                        received = True
                        msg = data.get("msg", {})
                        assert "x" in msg, "Expected x in pose message"
                        assert "y" in msg, "Expected y in pose message"
                        break

            # Unsubscribe
            ws_manager.send({"op": "unsubscribe", "topic": "/turtle1/pose"})

        assert received, "Did not receive message from subscribed topic"

    def test_discover_services_then_call(self, ws_manager, rosapi_services_type, service_type_empty):
        """Test workflow: discover services, then call one."""
        # Step 1: Discover services
        services_message = {
            "op": "call_service",
            "service": "/rosapi/services",
            "type": rosapi_services_type,
            "args": {},
            "id": "discover_services",
        }

        with ws_manager:
            services_response = ws_manager.request(services_message, timeout=10.0)

        assert "values" in services_response
        services = services_response["values"].get("services", [])
        assert "/reset" in services, "Expected /reset service"

        # Step 2: Call the discovered service
        call_message = {
            "op": "call_service",
            "service": "/reset",
            "type": service_type_empty,
            "args": {},
            "id": "call_reset",
        }

        with ws_manager:
            call_response = ws_manager.request(call_message, timeout=10.0)

        # Reset service should succeed (result may be empty for Empty srv)
        assert "error" not in call_response or call_response.get("result") is not None


class TestTurtleControlWorkflow:
    """E2E tests for turtle control workflows."""

    def test_spawn_turtle_control_kill(
        self, ws_manager, service_type_spawn, service_type_kill, msg_type_twist
    ):
        """Test workflow: spawn turtle, control it, then kill it."""
        # Step 1: Spawn a new turtle
        spawn_message = {
            "op": "call_service",
            "service": "/spawn",
            "type": service_type_spawn,
            "args": {"x": 5.0, "y": 5.0, "theta": 0.0, "name": "test_turtle"},
            "id": "spawn_turtle",
        }

        with ws_manager:
            spawn_response = ws_manager.request(spawn_message, timeout=10.0)

        # Note: Spawn might fail if turtle already exists, which is okay
        spawned = "values" in spawn_response or "error" not in spawn_response

        # Step 2: Try to move the turtle (publish velocity)
        if spawned:
            advertise_msg = {
                "op": "advertise",
                "topic": "/test_turtle/cmd_vel",
                "type": msg_type_twist,
            }

            publish_msg = {
                "op": "publish",
                "topic": "/test_turtle/cmd_vel",
                "msg": {"linear": {"x": 1.0, "y": 0.0, "z": 0.0}, "angular": {"x": 0.0, "y": 0.0, "z": 0.5}},
            }

            with ws_manager:
                ws_manager.send(advertise_msg)
                time.sleep(0.1)
                ws_manager.send(publish_msg)
                time.sleep(0.5)
                ws_manager.send({"op": "unadvertise", "topic": "/test_turtle/cmd_vel"})

        # Step 3: Kill the turtle
        kill_message = {
            "op": "call_service",
            "service": "/kill",
            "type": service_type_kill,
            "args": {"name": "test_turtle"},
            "id": "kill_turtle",
        }

        with ws_manager:
            ws_manager.request(kill_message, timeout=10.0)

        # Kill should succeed (or turtle didn't exist)
        # Both are acceptable outcomes for this test


class TestRapidOperations:
    """E2E tests for rapid sequential operations."""

    def test_rapid_sequential_topic_subscriptions(self, ws_manager, msg_type_pose):
        """Test rapid subscribe/unsubscribe cycles."""
        topic = "/turtle1/pose"

        for i in range(5):
            subscribe_msg = {
                "op": "subscribe",
                "topic": topic,
                "type": msg_type_pose,
                "id": f"rapid_sub_{i}",
            }

            with ws_manager:
                ws_manager.send(subscribe_msg)

                # Wait briefly for a message
                response = ws_manager.receive(timeout=1.0)
                if response:
                    data = json.loads(response)
                    if data.get("op") == "publish":
                        assert data.get("topic") == topic

                # Unsubscribe
                ws_manager.send({"op": "unsubscribe", "topic": topic})

            time.sleep(0.1)  # Brief pause between cycles

    def test_rapid_service_calls(self, ws_manager, rosapi_topics_type):
        """Test rapid service call sequences."""
        for i in range(5):
            message = {
                "op": "call_service",
                "service": "/rosapi/topics",
                "type": rosapi_topics_type,
                "args": {},
                "id": f"rapid_call_{i}",
            }

            with ws_manager:
                response = ws_manager.request(message, timeout=5.0)

            assert "values" in response, f"Call {i} failed: {response}"
            time.sleep(0.1)  # Brief pause between calls


class TestPublishSubscribeRoundtrip:
    """E2E tests for publish-subscribe roundtrip."""

    def test_publish_subscribe_roundtrip(
        self, ws_manager, reset_turtle_fixture, msg_type_twist, msg_type_pose
    ):
        """Test publishing to cmd_vel and observing pose change."""
        # Get initial pose
        initial_pose = get_turtle_pose(ws_manager, msg_type=msg_type_pose)
        assert initial_pose is not None, "Could not get initial pose"
        initial_x = initial_pose.get("x", 0)

        # Publish velocity command to move forward
        with ws_manager:
            ws_manager.send({
                "op": "advertise",
                "topic": "/turtle1/cmd_vel",
                "type": msg_type_twist,
            })
            time.sleep(0.1)

            # Publish forward movement
            ws_manager.send({
                "op": "publish",
                "topic": "/turtle1/cmd_vel",
                "msg": {"linear": {"x": 2.0, "y": 0.0, "z": 0.0}, "angular": {"x": 0.0, "y": 0.0, "z": 0.0}},
            })
            time.sleep(0.5)  # Let turtle move

            ws_manager.send({"op": "unadvertise", "topic": "/turtle1/cmd_vel"})

        # Get new pose
        new_pose = get_turtle_pose(ws_manager, msg_type=msg_type_pose)
        assert new_pose is not None, "Could not get new pose"
        new_x = new_pose.get("x", 0)

        # Turtle should have moved forward (x increased)
        assert new_x > initial_x, f"Turtle should have moved: initial_x={initial_x}, new_x={new_x}"


class TestFullDiscoveryWorkflow:
    """E2E tests for full robot discovery workflow."""

    def test_full_robot_discovery_workflow(
        self, ws_manager, rosapi_nodes_type, rosapi_topics_type, rosapi_services_type
    ):
        """Test complete discovery workflow: nodes -> topics -> services."""
        # Step 1: Discover nodes
        nodes_message = {
            "op": "call_service",
            "service": "/rosapi/nodes",
            "type": rosapi_nodes_type,
            "args": {},
            "id": "discover_nodes",
        }

        with ws_manager:
            nodes_response = ws_manager.request(nodes_message, timeout=10.0)

        assert "values" in nodes_response, f"Failed to get nodes: {nodes_response}"
        nodes = nodes_response["values"].get("nodes", [])
        assert len(nodes) > 0, "Expected at least one node"

        # Step 2: Discover topics
        topics_message = {
            "op": "call_service",
            "service": "/rosapi/topics",
            "type": rosapi_topics_type,
            "args": {},
            "id": "discover_topics",
        }

        with ws_manager:
            topics_response = ws_manager.request(topics_message, timeout=10.0)

        assert "values" in topics_response
        topics = topics_response["values"].get("topics", [])
        types = topics_response["values"].get("types", [])
        assert len(topics) > 0, "Expected at least one topic"
        assert len(topics) == len(types), "Topics and types should have same length"

        # Step 3: Discover services
        services_message = {
            "op": "call_service",
            "service": "/rosapi/services",
            "type": rosapi_services_type,
            "args": {},
            "id": "discover_services",
        }

        with ws_manager:
            services_response = ws_manager.request(services_message, timeout=10.0)

        assert "values" in services_response
        services = services_response["values"].get("services", [])
        assert len(services) > 0, "Expected at least one service"

        # Step 4: Verify turtlesim presence
        turtlesim_nodes = [n for n in nodes if "turtle" in n.lower()]
        turtlesim_topics = [t for t in topics if "turtle" in t.lower()]
        turtlesim_services = [s for s in services if "turtle" in s.lower()]

        assert len(turtlesim_nodes) > 0 or len(turtlesim_topics) > 0 or len(turtlesim_services) > 0, (
            "Expected turtlesim to be present in the ROS system"
        )
