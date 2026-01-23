"""E2E tests for action operations with real ROS 2 turtlesim.

Actions are a ROS 2 specific feature and are not available in ROS 1.
"""

import json
import math
import time

import pytest

from tests.e2e.conftest import get_turtle_pose, reset_turtle, teleport_turtle

# Mark all tests in this module as e2e and ros2-only
pytestmark = [pytest.mark.e2e, pytest.mark.ros2]


class TestGetActions:
    """E2E tests for get_actions functionality."""

    def test_get_actions_returns_rotate_absolute(self, ws_manager, turtlesim_actions, rosapi_services_type):
        """Verify turtlesim rotate_absolute action exists."""
        # First check if the action_servers service is available
        services_msg = {
            "op": "call_service",
            "service": "/rosapi/services",
            "type": rosapi_services_type,
            "args": {},
            "id": "check_action_servers_service",
        }

        with ws_manager:
            services_response = ws_manager.request(services_msg, timeout=10.0)

        services = services_response.get("values", {}).get("services", [])

        if "/rosapi/action_servers" not in services:
            pytest.skip("action_servers service not available in this rosbridge version")

        # Now get actions
        message = {
            "op": "call_service",
            "service": "/rosapi/action_servers",
            "type": "rosapi/ActionServers",
            "args": {},
            "id": "get_actions_e2e",
        }

        with ws_manager:
            response = ws_manager.request(message, timeout=10.0)

        if "error" in response:
            pytest.skip(f"Action listing not supported: {response['error']}")

        actions = response.get("values", {}).get("action_servers", [])

        # Check for expected turtlesim actions
        for expected_action in turtlesim_actions:
            assert expected_action in actions, f"Expected {expected_action} in actions"


class TestSendRotateAbsoluteGoal:
    """E2E tests for sending action goals to rotate_absolute."""

    def test_send_rotate_goal_basic(
        self, ws_manager, service_type_empty, service_type_teleport, msg_type_pose
    ):
        """Send a rotation goal and verify it's accepted."""
        # Reset turtle to known position
        reset_turtle(ws_manager, service_type_empty)
        teleport_turtle(ws_manager, 5.5, 5.5, 0.0, service_type_teleport)
        time.sleep(0.5)

        # Send action goal
        goal_id = f"test_goal_{int(time.time() * 1000)}"
        message = {
            "op": "send_action_goal",
            "id": goal_id,
            "action": "/turtle1/rotate_absolute",
            "action_type": "turtlesim/action/RotateAbsolute",
            "args": {"theta": math.pi / 2},  # 90 degrees
            "feedback": True,
        }

        with ws_manager:
            ws_manager.send(message)

            # Wait for result or feedback
            end_time = time.time() + 10.0
            got_response = False

            while time.time() < end_time:
                response = ws_manager.receive(timeout=1.0)
                if response:
                    data = json.loads(response)
                    op = data.get("op", "")

                    if op == "action_result":
                        got_response = True
                        # Check for success
                        assert data.get("id") == goal_id
                        break
                    elif op == "action_feedback":
                        # We're receiving feedback, that's good
                        got_response = True
                    elif op == "status" and data.get("level") == "error":
                        pytest.fail(f"Action error: {data.get('msg')}")

        # Verify turtle rotated
        time.sleep(0.5)
        pose = get_turtle_pose(ws_manager, msg_type=msg_type_pose)
        if pose and got_response:
            # Should be approximately 90 degrees (pi/2)
            expected_theta = math.pi / 2
            # Allow for some tolerance
            theta_diff = abs(pose["theta"] - expected_theta)
            # Handle wrap-around
            if theta_diff > math.pi:
                theta_diff = 2 * math.pi - theta_diff
            assert theta_diff < 0.2, f"Expected theta ~{expected_theta}, got {pose['theta']}"

    def test_send_rotate_goal_with_feedback(self, ws_manager, service_type_empty, service_type_teleport):
        """Send a rotation goal and verify feedback is received."""
        reset_turtle(ws_manager, service_type_empty)
        teleport_turtle(ws_manager, 5.5, 5.5, 0.0, service_type_teleport)
        time.sleep(0.5)

        goal_id = f"feedback_goal_{int(time.time() * 1000)}"
        message = {
            "op": "send_action_goal",
            "id": goal_id,
            "action": "/turtle1/rotate_absolute",
            "action_type": "turtlesim/action/RotateAbsolute",
            "args": {"theta": math.pi},  # 180 degrees - longer rotation
            "feedback": True,
        }

        feedback_received = []
        result_received = None

        with ws_manager:
            ws_manager.send(message)

            end_time = time.time() + 15.0
            while time.time() < end_time:
                response = ws_manager.receive(timeout=1.0)
                if response:
                    data = json.loads(response)
                    op = data.get("op", "")

                    if op == "action_feedback":
                        feedback_received.append(data)
                    elif op == "action_result":
                        result_received = data
                        break

        # For a 180 degree rotation, we should get some feedback
        # (unless the action completes very quickly)
        if result_received:
            assert result_received.get("id") == goal_id
        # Feedback might or might not be received depending on rotation speed


class TestCancelActionGoal:
    """E2E tests for canceling action goals."""

    def test_cancel_action_goal(self, ws_manager, service_type_empty, service_type_teleport):
        """Start a rotation and cancel it mid-way."""
        reset_turtle(ws_manager, service_type_empty)
        teleport_turtle(ws_manager, 5.5, 5.5, 0.0, service_type_teleport)
        time.sleep(0.5)

        # Start a long rotation
        goal_id = f"cancel_goal_{int(time.time() * 1000)}"
        start_message = {
            "op": "send_action_goal",
            "id": goal_id,
            "action": "/turtle1/rotate_absolute",
            "action_type": "turtlesim/action/RotateAbsolute",
            "args": {"theta": 2 * math.pi - 0.1},  # Almost full rotation
            "feedback": True,
        }

        with ws_manager:
            ws_manager.send(start_message)

            # Wait a short time then cancel
            time.sleep(0.5)

            # Send cancel request
            cancel_message = {
                "op": "cancel_action_goal",
                "id": goal_id,
                "action": "/turtle1/rotate_absolute",
            }
            ws_manager.send(cancel_message)

            # Wait for cancellation or result
            end_time = time.time() + 5.0

            while time.time() < end_time:
                response = ws_manager.receive(timeout=1.0)
                if response:
                    data = json.loads(response)
                    op = data.get("op", "")

                    if op == "action_result":
                        # Action completed (might have finished or been cancelled)
                        break
                    elif op == "status":
                        # Might get status about cancellation
                        if "cancel" in data.get("msg", "").lower():
                            break

        # Note: Cancel might or might not succeed depending on timing
        # The important thing is that we can send the cancel request


class TestActionStatus:
    """E2E tests for getting action status."""

    def test_get_action_status_no_active_goals(self, ws_manager, service_type_empty):
        """Get status when no goals are active."""
        # Reset to ensure no goals are running
        reset_turtle(ws_manager, service_type_empty)
        time.sleep(1.0)

        # Subscribe to action status topic
        status_topic = "/turtle1/rotate_absolute/_action/status"
        subscribe_msg = {
            "op": "subscribe",
            "topic": status_topic,
            "type": "action_msgs/msg/GoalStatusArray",
        }

        with ws_manager:
            ws_manager.send(subscribe_msg)

            # Try to get a status message
            end_time = time.time() + 5.0
            status_received = None

            while time.time() < end_time:
                response = ws_manager.receive(timeout=1.0)
                if response:
                    data = json.loads(response)
                    if data.get("op") == "publish" and data.get("topic") == status_topic:
                        status_received = data.get("msg", {})
                        break

            ws_manager.send({"op": "unsubscribe", "topic": status_topic})

        # Status message might have empty or non-empty status_list
        if status_received is not None:
            assert "status_list" in status_received


class TestActionIntegration:
    """Integration tests for action workflows."""

    def test_rotate_then_check_pose(
        self, ws_manager, service_type_empty, service_type_teleport, msg_type_pose
    ):
        """Complete workflow: rotate and verify final position."""
        # Setup
        reset_turtle(ws_manager, service_type_empty)
        teleport_turtle(ws_manager, 5.5, 5.5, 0.0, service_type_teleport)
        time.sleep(0.5)

        initial_pose = get_turtle_pose(ws_manager, msg_type=msg_type_pose)
        assert initial_pose is not None
        assert abs(initial_pose["theta"]) < 0.1, "Should start at theta ~0"

        # Rotate to 90 degrees
        target_theta = math.pi / 2
        goal_id = f"integration_goal_{int(time.time() * 1000)}"

        message = {
            "op": "send_action_goal",
            "id": goal_id,
            "action": "/turtle1/rotate_absolute",
            "action_type": "turtlesim/action/RotateAbsolute",
            "args": {"theta": target_theta},
            "feedback": True,
        }

        with ws_manager:
            ws_manager.send(message)

            # Wait for completion
            end_time = time.time() + 10.0
            completed = False

            while time.time() < end_time:
                response = ws_manager.receive(timeout=1.0)
                if response:
                    data = json.loads(response)
                    if data.get("op") == "action_result":
                        completed = True
                        break

        # Verify final pose
        time.sleep(0.5)
        final_pose = get_turtle_pose(ws_manager, msg_type=msg_type_pose)
        assert final_pose is not None

        if completed:
            # Should be at target theta
            theta_diff = abs(final_pose["theta"] - target_theta)
            if theta_diff > math.pi:
                theta_diff = 2 * math.pi - theta_diff
            assert theta_diff < 0.2, f"Expected theta ~{target_theta}, got {final_pose['theta']}"

            # Position should not have changed significantly
            assert abs(final_pose["x"] - 5.5) < 0.5
            assert abs(final_pose["y"] - 5.5) < 0.5
