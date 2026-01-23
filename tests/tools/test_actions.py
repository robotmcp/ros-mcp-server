"""Tests for ros_mcp.tools.actions module."""

import json
import pytest
from unittest.mock import MagicMock, patch, AsyncMock

# Import the registration function and test directly
from ros_mcp.tools.actions import register_action_tools


class MockFastMCP:
    """Mock FastMCP for capturing registered tools."""

    def __init__(self):
        self.tools = {}

    def tool(self, description=None):
        def decorator(func):
            self.tools[func.__name__] = func
            return func
        return decorator


@pytest.fixture
def mock_mcp():
    """Create a mock FastMCP instance."""
    return MockFastMCP()


@pytest.fixture
def action_tools(mock_mcp, mock_ws_manager):
    """Register action tools and return them."""
    register_action_tools(mock_mcp, mock_ws_manager)
    return mock_mcp.tools


class TestGetActions:
    """Test cases for get_actions tool."""

    def test_returns_action_list(self, action_tools, mock_ws_manager):
        """Test that get_actions returns list of actions."""
        # First response: services check
        # Second response: action servers
        mock_ws_manager.add_responses([
            {
                "result": True,
                "values": {
                    "services": ["/rosapi/action_servers", "/rosapi/services"]
                }
            },
            {
                "result": True,
                "values": {
                    "action_servers": ["/turtle1/rotate_absolute", "/fibonacci"]
                }
            }
        ])

        result = action_tools["get_actions"]()

        assert "actions" in result
        assert len(result["actions"]) == 2
        assert "/turtle1/rotate_absolute" in result["actions"]
        assert result["action_count"] == 2

    def test_missing_action_servers_service(self, action_tools, mock_ws_manager):
        """Test when /rosapi/action_servers service is not available."""
        mock_ws_manager.add_response({
            "result": True,
            "values": {
                "services": ["/rosapi/services", "/rosapi/topics"]
            }
        })

        result = action_tools["get_actions"]()

        assert "warning" in result
        assert "compatibility" in result
        assert "/rosapi/action_servers" in result["compatibility"]["missing_services"]

    def test_empty_response(self, action_tools, mock_ws_manager):
        """Test when no actions are found."""
        mock_ws_manager.add_responses([
            {
                "result": True,
                "values": {"services": ["/rosapi/action_servers"]}
            },
            {
                "result": True,
                "values": {"action_servers": []}
            }
        ])

        result = action_tools["get_actions"]()

        assert "actions" in result
        assert result["actions"] == []
        assert result["action_count"] == 0

    def test_service_call_failure(self, action_tools, mock_ws_manager):
        """Test when service call fails."""
        mock_ws_manager.add_responses([
            {
                "result": True,
                "values": {"services": ["/rosapi/action_servers"]}
            },
            {
                "result": False,
                "values": {"message": "Service unavailable"}
            }
        ])

        result = action_tools["get_actions"]()

        assert "error" in result

    def test_websocket_error(self, action_tools, mock_ws_manager):
        """Test when WebSocket returns error."""
        mock_ws_manager.add_responses([
            {
                "result": True,
                "values": {"services": ["/rosapi/action_servers"]}
            },
            {"error": "Connection lost"}
        ])

        result = action_tools["get_actions"]()

        assert "error" in result
        assert "WebSocket error" in result["error"]

    def test_no_response_from_services_check(self, action_tools, mock_ws_manager):
        """Test when services check returns no response."""
        mock_ws_manager.add_response(None)

        result = action_tools["get_actions"]()

        assert "warning" in result
        assert "Cannot check service availability" in result["warning"]


class TestGetActionDetails:
    """Test cases for get_action_details tool."""

    def test_empty_action_name(self, action_tools, mock_ws_manager):
        """Test with empty action name."""
        result = action_tools["get_action_details"]("")

        assert "error" in result
        assert "cannot be empty" in result["error"]

    def test_whitespace_action_name(self, action_tools, mock_ws_manager):
        """Test with whitespace-only action name."""
        result = action_tools["get_action_details"]("   ")

        assert "error" in result
        assert "cannot be empty" in result["error"]

    def test_known_action_with_details(self, action_tools, mock_ws_manager):
        """Test getting details for a known action like /turtle1/rotate_absolute."""
        # Services check response
        mock_ws_manager.add_responses([
            {
                "result": True,
                "values": {
                    "services": [
                        "/rosapi/interfaces",
                        "/rosapi/action_goal_details",
                        "/rosapi/action_result_details",
                        "/rosapi/action_feedback_details",
                        "/rosapi/services"
                    ]
                }
            },
            # Second services check
            {
                "result": True,
                "values": {
                    "services": [
                        "/rosapi/interfaces",
                        "/rosapi/action_goal_details",
                        "/rosapi/action_result_details",
                        "/rosapi/action_feedback_details",
                        "/rosapi/services"
                    ]
                }
            },
            # Goal details
            {
                "result": True,
                "values": {
                    "typedefs": [{
                        "type": "turtlesim/action/RotateAbsolute_Goal",
                        "fieldnames": ["theta"],
                        "fieldtypes": ["float32"],
                        "fieldarraylen": [-1],
                        "examples": ["0.0"],
                        "constnames": [],
                        "constvalues": []
                    }]
                }
            },
            # Result details
            {
                "result": True,
                "values": {
                    "typedefs": [{
                        "type": "turtlesim/action/RotateAbsolute_Result",
                        "fieldnames": ["delta"],
                        "fieldtypes": ["float32"],
                        "fieldarraylen": [-1],
                        "examples": ["0.0"],
                        "constnames": [],
                        "constvalues": []
                    }]
                }
            },
            # Feedback details
            {
                "result": True,
                "values": {
                    "typedefs": [{
                        "type": "turtlesim/action/RotateAbsolute_Feedback",
                        "fieldnames": ["remaining"],
                        "fieldtypes": ["float32"],
                        "fieldarraylen": [-1],
                        "examples": ["0.0"],
                        "constnames": [],
                        "constvalues": []
                    }]
                }
            }
        ])

        result = action_tools["get_action_details"]("/turtle1/rotate_absolute")

        assert "action" in result
        assert result["action"] == "/turtle1/rotate_absolute"
        assert "action_type" in result
        assert "goal" in result
        assert "result" in result
        assert "feedback" in result

    def test_missing_interfaces_service(self, action_tools, mock_ws_manager):
        """Test when /rosapi/interfaces is not available."""
        mock_ws_manager.add_response({
            "result": True,
            "values": {"services": ["/rosapi/services"]}
        })

        result = action_tools["get_action_details"]("/unknown_action")

        assert "warning" in result or "compatibility" in result

    def test_unknown_action_type(self, action_tools, mock_ws_manager):
        """Test with unknown action that can't be resolved."""
        mock_ws_manager.add_responses([
            {
                "result": True,
                "values": {"services": ["/rosapi/interfaces"]}
            },
            # Interfaces response with no matching action
            {
                "result": True,
                "values": {"interfaces": ["std_msgs/msg/String"]}
            }
        ])

        result = action_tools["get_action_details"]("/unknown_action")

        # Should return error since action type couldn't be found
        assert "error" in result or "warning" in result


class TestGetActionStatus:
    """Test cases for get_action_status tool."""

    def test_empty_action_name(self, action_tools, mock_ws_manager):
        """Test with empty action name."""
        result = action_tools["get_action_status"]("")

        assert "error" in result
        assert "cannot be empty" in result["error"]

    def test_adds_leading_slash(self, action_tools, mock_ws_manager):
        """Test that leading slash is added if missing."""
        mock_ws_manager.add_response(json.dumps({
            "op": "publish",
            "msg": {"status_list": []}
        }))

        result = action_tools["get_action_status"]("turtle1/rotate_absolute")

        # Check that request was made with leading slash
        assert result["action_name"] == "/turtle1/rotate_absolute"

    def test_successful_status_with_goals(self, action_tools, mock_ws_manager):
        """Test getting status with active goals."""
        mock_ws_manager._responses = []

        # Mock the receive to return status message
        def mock_receive(timeout=None):
            return json.dumps({
                "op": "publish",
                "msg": {
                    "status_list": [
                        {
                            "goal_info": {
                                "goal_id": {"uuid": "abc123"},
                                "stamp": {"sec": 1000, "nanosec": 500}
                            },
                            "status": 2  # EXECUTING
                        }
                    ]
                }
            })

        mock_ws_manager.receive = mock_receive

        result = action_tools["get_action_status"]("/turtle1/rotate_absolute")

        assert result["success"] is True
        assert result["goal_count"] == 1
        assert result["active_goals"][0]["status_text"] == "STATUS_EXECUTING"

    def test_no_active_goals(self, action_tools, mock_ws_manager):
        """Test when there are no active goals."""
        def mock_receive(timeout=None):
            return json.dumps({
                "op": "publish",
                "msg": {"status_list": []}
            })

        mock_ws_manager.receive = mock_receive

        result = action_tools["get_action_status"]("/turtle1/rotate_absolute")

        assert result["success"] is True
        assert result["goal_count"] == 0

    def test_status_topic_error(self, action_tools, mock_ws_manager):
        """Test when status topic returns error."""
        def mock_receive(timeout=None):
            return json.dumps({
                "op": "status",
                "level": "error",
                "msg": "Topic not found"
            })

        mock_ws_manager.receive = mock_receive

        result = action_tools["get_action_status"]("/turtle1/rotate_absolute")

        assert "error" in result

    def test_no_response_timeout(self, action_tools, mock_ws_manager):
        """Test when no response is received (timeout)."""
        def mock_receive(timeout=None):
            return None

        mock_ws_manager.receive = mock_receive

        result = action_tools["get_action_status"]("/turtle1/rotate_absolute")

        assert result["success"] is False
        assert "No response" in result["error"]


class TestSendActionGoal:
    """Test cases for send_action_goal tool."""

    @pytest.mark.asyncio
    async def test_empty_action_name(self, action_tools, mock_ws_manager):
        """Test with empty action name."""
        result = await action_tools["send_action_goal"]("", "type", {"theta": 1.0})

        assert "error" in result
        assert "Action name cannot be empty" in result["error"]

    @pytest.mark.asyncio
    async def test_empty_action_type(self, action_tools, mock_ws_manager):
        """Test with empty action type."""
        result = await action_tools["send_action_goal"]("/action", "", {"theta": 1.0})

        assert "error" in result
        assert "Action type cannot be empty" in result["error"]

    @pytest.mark.asyncio
    async def test_empty_goal(self, action_tools, mock_ws_manager):
        """Test with empty goal."""
        result = await action_tools["send_action_goal"]("/action", "type", {})

        assert "error" in result
        assert "Goal cannot be empty" in result["error"]

    @pytest.mark.asyncio
    async def test_successful_action_goal(self, action_tools, mock_ws_manager):
        """Test successful action goal completion."""
        call_count = [0]

        def mock_receive(timeout=None):
            call_count[0] += 1
            if call_count[0] == 1:
                return json.dumps({
                    "op": "action_result",
                    "status": "SUCCEEDED",
                    "values": {"delta": 0.5}
                })
            return None

        mock_ws_manager.receive = mock_receive

        result = await action_tools["send_action_goal"](
            "/turtle1/rotate_absolute",
            "turtlesim/action/RotateAbsolute",
            {"theta": 1.57},
            timeout=5.0
        )

        assert result["success"] is True
        assert result["status"] == "SUCCEEDED"
        assert "result" in result

    @pytest.mark.asyncio
    async def test_action_with_feedback(self, action_tools, mock_ws_manager):
        """Test action that sends feedback before result."""
        call_count = [0]

        def mock_receive(timeout=None):
            call_count[0] += 1
            if call_count[0] <= 2:
                return json.dumps({
                    "op": "action_feedback",
                    "values": {"remaining": 1.0 - (call_count[0] * 0.5)}
                })
            return json.dumps({
                "op": "action_result",
                "status": "SUCCEEDED",
                "values": {"delta": 0.1}
            })

        mock_ws_manager.receive = mock_receive

        result = await action_tools["send_action_goal"](
            "/turtle1/rotate_absolute",
            "turtlesim/action/RotateAbsolute",
            {"theta": 1.57},
            timeout=5.0
        )

        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_action_timeout_with_feedback(self, action_tools, mock_ws_manager):
        """Test action timeout but with partial feedback."""
        def mock_receive(timeout=None):
            return json.dumps({
                "op": "action_feedback",
                "values": {"remaining": 0.5}
            })

        mock_ws_manager.receive = mock_receive

        result = await action_tools["send_action_goal"](
            "/turtle1/rotate_absolute",
            "turtlesim/action/RotateAbsolute",
            {"theta": 1.57},
            timeout=0.5  # Short timeout
        )

        # Should succeed with feedback but note timeout
        assert "last_feedback" in result or "error" in result

    @pytest.mark.asyncio
    async def test_send_failure(self, action_tools, mock_ws_manager):
        """Test when send fails."""
        mock_ws_manager.send = lambda msg: "Connection error"

        result = await action_tools["send_action_goal"](
            "/turtle1/rotate_absolute",
            "turtlesim/action/RotateAbsolute",
            {"theta": 1.57}
        )

        assert result["success"] is False
        assert "Failed to send" in result["error"]


class TestCancelActionGoal:
    """Test cases for cancel_action_goal tool."""

    def test_empty_action_name(self, action_tools, mock_ws_manager):
        """Test with empty action name."""
        result = action_tools["cancel_action_goal"]("", "goal_123")

        assert "error" in result
        assert "Action name cannot be empty" in result["error"]

    def test_empty_goal_id(self, action_tools, mock_ws_manager):
        """Test with empty goal ID."""
        result = action_tools["cancel_action_goal"]("/action", "")

        assert "error" in result
        assert "Goal ID cannot be empty" in result["error"]

    def test_successful_cancel(self, action_tools, mock_ws_manager):
        """Test successful cancel request."""
        result = action_tools["cancel_action_goal"](
            "/turtle1/rotate_absolute",
            "goal_123"
        )

        assert result["success"] is True
        assert result["goal_id"] == "goal_123"
        assert "Cancel request sent" in result["note"]

    def test_cancel_send_failure(self, action_tools, mock_ws_manager):
        """Test when send fails."""
        mock_ws_manager.send = lambda msg: "Connection error"

        result = action_tools["cancel_action_goal"](
            "/turtle1/rotate_absolute",
            "goal_123"
        )

        assert result["success"] is False
        assert "Failed to send cancel" in result["error"]


class TestActionStatusCodes:
    """Test action status code mapping."""

    def test_all_status_codes(self, action_tools, mock_ws_manager):
        """Test that all status codes are properly mapped."""
        status_map = {
            0: "STATUS_UNKNOWN",
            1: "STATUS_ACCEPTED",
            2: "STATUS_EXECUTING",
            3: "STATUS_CANCELING",
            4: "STATUS_SUCCEEDED",
            5: "STATUS_CANCELED",
            6: "STATUS_ABORTED",
        }

        for code, expected_text in status_map.items():
            def mock_receive(timeout=None, status_code=code):
                return json.dumps({
                    "op": "publish",
                    "msg": {
                        "status_list": [{
                            "goal_info": {
                                "goal_id": {"uuid": "test"},
                                "stamp": {"sec": 0, "nanosec": 0}
                            },
                            "status": status_code
                        }]
                    }
                })

            mock_ws_manager.receive = lambda t=None, c=code: json.dumps({
                "op": "publish",
                "msg": {
                    "status_list": [{
                        "goal_info": {
                            "goal_id": {"uuid": "test"},
                            "stamp": {"sec": 0, "nanosec": 0}
                        },
                        "status": c
                    }]
                }
            })

            result = action_tools["get_action_status"]("/test_action")
            if result.get("active_goals"):
                assert result["active_goals"][0]["status_text"] == expected_text
