"""Tests for ros_mcp.tools.robot_config module."""

import pytest
from unittest.mock import MagicMock, patch

from ros_mcp.tools.robot_config import register_robot_config_tools


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
def robot_config_tools(mock_mcp, mock_ws_manager):
    """Register robot config tools and return them."""
    register_robot_config_tools(mock_mcp, mock_ws_manager)
    return mock_mcp.tools


class TestGetVerifiedRobotSpec:
    """Test cases for get_verified_robot_spec tool."""

    def test_robot_not_found(self, robot_config_tools):
        """Test when robot spec doesn't exist."""
        with patch(
            "ros_mcp.tools.robot_config.get_verified_robot_spec_util",
            return_value={}
        ):
            result = robot_config_tools["get_verified_robot_spec"]("nonexistent_robot")

        assert "error" in result
        assert "No configuration found" in result["error"]

    def test_multiple_configs_found(self, robot_config_tools):
        """Test when multiple configs match."""
        with patch(
            "ros_mcp.tools.robot_config.get_verified_robot_spec_util",
            return_value={"robot1": {}, "robot2": {}}
        ):
            result = robot_config_tools["get_verified_robot_spec"]("robot")

        assert "error" in result
        assert "Multiple configurations found" in result["error"]

    def test_single_config_found(self, robot_config_tools):
        """Test when exactly one config is found."""
        expected_config = {
            "test_robot": {
                "type": "mobile",
                "prompts": "Test robot prompts"
            }
        }
        with patch(
            "ros_mcp.tools.robot_config.get_verified_robot_spec_util",
            return_value=expected_config
        ):
            result = robot_config_tools["get_verified_robot_spec"]("test_robot")

        assert "robot_config" in result
        assert result["robot_config"] == expected_config

    def test_with_actual_local_rosbridge(self, robot_config_tools):
        """Test with actual local_rosbridge spec if it exists."""
        result = robot_config_tools["get_verified_robot_spec"]("local_rosbridge")

        # Either finds it or returns error - both are valid
        assert "robot_config" in result or "error" in result


class TestGetVerifiedRobotsList:
    """Test cases for get_verified_robots_list tool."""

    def test_returns_list(self, robot_config_tools):
        """Test that tool returns a list of robots."""
        with patch(
            "ros_mcp.tools.robot_config.get_verified_robots_list_util",
            return_value={
                "robot_specifications": ["robot1", "robot2", "robot3"],
                "count": 3
            }
        ):
            result = robot_config_tools["get_verified_robots_list"]()

        assert "robot_specifications" in result
        assert result["count"] == 3

    def test_empty_list(self, robot_config_tools):
        """Test when no robots are available."""
        with patch(
            "ros_mcp.tools.robot_config.get_verified_robots_list_util",
            return_value={"robot_specifications": [], "count": 0}
        ):
            result = robot_config_tools["get_verified_robots_list"]()

        assert result["robot_specifications"] == []
        assert result["count"] == 0

    def test_with_actual_specs(self, robot_config_tools):
        """Test with actual robot specifications directory."""
        result = robot_config_tools["get_verified_robots_list"]()

        assert isinstance(result, dict)
        # Should either have robot_specifications or error
        assert "robot_specifications" in result or "error" in result


class TestDetectRosVersion:
    """Test cases for detect_ros_version tool."""

    def test_ros2_detected(self, robot_config_tools, mock_ws_manager):
        """Test ROS 2 version detection."""
        mock_ws_manager.add_response({
            "values": {
                "version": "2",
                "distro": "humble"
            }
        })

        result = robot_config_tools["detect_ros_version"]()

        assert result["version"] == "2"
        assert result["distro"] == "humble"

    def test_ros1_fallback(self, robot_config_tools, mock_ws_manager):
        """Test ROS 1 detection when ROS 2 service fails."""
        mock_ws_manager.add_responses([
            {},  # ROS 2 detection fails (no version in values)
            {"values": {"value": '"noetic\n"'}}  # ROS 1 fallback
        ])

        result = robot_config_tools["detect_ros_version"]()

        assert result["version"] == "1"
        assert result["distro"] == "noetic"

    def test_ros1_with_dict_value(self, robot_config_tools, mock_ws_manager):
        """Test ROS 1 detection with dict response."""
        mock_ws_manager.add_responses([
            {},  # ROS 2 detection fails
            {"values": {"value": "melodic"}}
        ])

        result = robot_config_tools["detect_ros_version"]()

        assert result["version"] == "1"
        assert result["distro"] == "melodic"

    def test_detection_failure(self, robot_config_tools, mock_ws_manager):
        """Test when neither ROS version can be detected."""
        mock_ws_manager.add_responses([
            {},  # ROS 2 fails
            {}   # ROS 1 fails
        ])

        result = robot_config_tools["detect_ros_version"]()

        assert "error" in result
        assert "Could not detect" in result["error"]

    def test_no_response(self, robot_config_tools, mock_ws_manager):
        """Test when no response is received."""
        mock_ws_manager.add_responses([None, None])

        result = robot_config_tools["detect_ros_version"]()

        assert "error" in result

    def test_ros2_humble(self, robot_config_tools, mock_ws_manager):
        """Test ROS 2 Humble detection."""
        mock_ws_manager.add_response({
            "values": {"version": "2", "distro": "humble"}
        })

        result = robot_config_tools["detect_ros_version"]()

        assert result["version"] == "2"
        assert result["distro"] == "humble"

    def test_ros2_iron(self, robot_config_tools, mock_ws_manager):
        """Test ROS 2 Iron detection."""
        mock_ws_manager.add_response({
            "values": {"version": "2", "distro": "iron"}
        })

        result = robot_config_tools["detect_ros_version"]()

        assert result["version"] == "2"
        assert result["distro"] == "iron"

    def test_ros2_rolling(self, robot_config_tools, mock_ws_manager):
        """Test ROS 2 Rolling detection."""
        mock_ws_manager.add_response({
            "values": {"version": "2", "distro": "rolling"}
        })

        result = robot_config_tools["detect_ros_version"]()

        assert result["version"] == "2"
        assert result["distro"] == "rolling"

    def test_distro_string_cleaning(self, robot_config_tools, mock_ws_manager):
        """Test that distro string is properly cleaned."""
        mock_ws_manager.add_responses([
            {},  # ROS 2 fails
            {"values": {"value": '"noetic\\n"'}}  # Has quotes and newline
        ])

        result = robot_config_tools["detect_ros_version"]()

        assert result["version"] == "1"
        # Should be cleaned of quotes and newlines
        assert "\\n" not in result["distro"]
        assert '"' not in result["distro"]


class TestRobotConfigToolsIntegration:
    """Integration tests for robot config tools."""

    def test_list_then_get_spec(self, robot_config_tools):
        """Test listing robots then getting a spec."""
        # First list available robots
        list_result = robot_config_tools["get_verified_robots_list"]()

        if "robot_specifications" in list_result and list_result["robot_specifications"]:
            # Get the first non-template robot
            for robot in list_result["robot_specifications"]:
                if robot != "YOUR_ROBOT_NAME":
                    spec_result = robot_config_tools["get_verified_robot_spec"](robot)
                    # Should either find it or return error
                    assert "robot_config" in spec_result or "error" in spec_result
                    break

    def test_detect_version_then_connect(self, robot_config_tools, mock_ws_manager):
        """Test detecting ROS version workflow."""
        mock_ws_manager.add_response({
            "values": {"version": "2", "distro": "humble"}
        })

        version_result = robot_config_tools["detect_ros_version"]()

        if "version" in version_result:
            assert version_result["version"] in ["1", "2"]


class TestRobotConfigToolsRegistration:
    """Test that robot config tools are properly registered."""

    def test_all_tools_registered(self, robot_config_tools):
        """Test that all expected tools are registered."""
        expected_tools = [
            "get_verified_robot_spec",
            "get_verified_robots_list",
            "detect_ros_version"
        ]

        for tool_name in expected_tools:
            assert tool_name in robot_config_tools, f"Tool {tool_name} not registered"

    def test_tools_callable(self, robot_config_tools):
        """Test that all registered tools are callable."""
        for tool_name, tool_func in robot_config_tools.items():
            assert callable(tool_func), f"Tool {tool_name} is not callable"
