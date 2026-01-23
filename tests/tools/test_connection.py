"""Tests for ros_mcp.tools.connection module."""

from unittest.mock import MagicMock, patch

import pytest

from tests.conftest import MockWebSocketManager


class TestConnectToRobot:
    """Test cases for connect_to_robot tool."""

    def test_connect_with_defaults(self, mock_ping_success):
        """Test connecting with default IP and port."""
        from fastmcp import FastMCP

        from ros_mcp.tools.connection import register_connection_tools

        mcp = FastMCP("test")
        ws_manager = MockWebSocketManager()

        with patch(
            "ros_mcp.tools.connection.ping_ip_and_port", return_value=mock_ping_success
        ):
            register_connection_tools(mcp, ws_manager, "127.0.0.1", 9090)

            # Find the registered tool
            tools = mcp._tool_manager._tools
            connect_tool = tools.get("connect_to_robot")
            assert connect_tool is not None

            # Call the tool function directly
            result = connect_tool.fn()

            assert "message" in result
            assert "connectivity_test" in result
            assert "127.0.0.1:9090" in result["message"]

    def test_connect_with_custom_ip_port(self, mock_ping_success):
        """Test connecting with custom IP and port."""
        from fastmcp import FastMCP

        from ros_mcp.tools.connection import register_connection_tools

        mcp = FastMCP("test")
        ws_manager = MockWebSocketManager()

        with patch(
            "ros_mcp.tools.connection.ping_ip_and_port", return_value=mock_ping_success
        ):
            register_connection_tools(mcp, ws_manager, "127.0.0.1", 9090)

            tools = mcp._tool_manager._tools
            connect_tool = tools.get("connect_to_robot")

            result = connect_tool.fn(ip="192.168.1.100", port=9091)

            assert "192.168.1.100:9091" in result["message"]
            assert ws_manager.ip == "192.168.1.100"
            assert ws_manager.port == 9091

    def test_connect_sets_ws_manager_ip(self, mock_ping_success):
        """Test that connect_to_robot sets the ws_manager IP and port."""
        from fastmcp import FastMCP

        from ros_mcp.tools.connection import register_connection_tools

        mcp = FastMCP("test")
        ws_manager = MockWebSocketManager("127.0.0.1", 9090)

        with patch(
            "ros_mcp.tools.connection.ping_ip_and_port", return_value=mock_ping_success
        ):
            register_connection_tools(mcp, ws_manager, "127.0.0.1", 9090)

            tools = mcp._tool_manager._tools
            connect_tool = tools.get("connect_to_robot")

            connect_tool.fn(ip="10.0.0.1", port=8080)

            assert ws_manager.ip == "10.0.0.1"
            assert ws_manager.port == 8080

    def test_connect_returns_connectivity_test(self, mock_ping_port_closed):
        """Test that connectivity test results are returned."""
        from fastmcp import FastMCP

        from ros_mcp.tools.connection import register_connection_tools

        mcp = FastMCP("test")
        ws_manager = MockWebSocketManager()

        with patch(
            "ros_mcp.tools.connection.ping_ip_and_port", return_value=mock_ping_port_closed
        ):
            register_connection_tools(mcp, ws_manager, "127.0.0.1", 9090)

            tools = mcp._tool_manager._tools
            connect_tool = tools.get("connect_to_robot")

            result = connect_tool.fn()

            assert result["connectivity_test"]["port_check"]["open"] is False


class TestPingRobot:
    """Test cases for ping_robot tool."""

    def test_ping_reachable(self, mock_ping_success):
        """Test pinging a reachable robot."""
        from fastmcp import FastMCP

        from ros_mcp.tools.connection import register_connection_tools

        mcp = FastMCP("test")
        ws_manager = MockWebSocketManager()

        with patch(
            "ros_mcp.tools.connection.ping_ip_and_port", return_value=mock_ping_success
        ):
            register_connection_tools(mcp, ws_manager, "127.0.0.1", 9090)

            tools = mcp._tool_manager._tools
            ping_tool = tools.get("ping_robot")
            assert ping_tool is not None

            result = ping_tool.fn(ip="127.0.0.1", port=9090)

            assert result["ping"]["success"] is True
            assert result["port_check"]["open"] is True
            assert "Fully_accessible" in result["overall_status"]

    def test_ping_unreachable(self, mock_ping_unreachable):
        """Test pinging an unreachable robot."""
        from fastmcp import FastMCP

        from ros_mcp.tools.connection import register_connection_tools

        mcp = FastMCP("test")
        ws_manager = MockWebSocketManager()

        with patch(
            "ros_mcp.tools.connection.ping_ip_and_port", return_value=mock_ping_unreachable
        ):
            register_connection_tools(mcp, ws_manager, "127.0.0.1", 9090)

            tools = mcp._tool_manager._tools
            ping_tool = tools.get("ping_robot")

            result = ping_tool.fn(ip="192.168.1.200", port=9090)

            assert result["ping"]["success"] is False
            assert "IP_unreachable" in result["overall_status"]

    def test_ping_with_custom_timeouts(self, mock_ping_success):
        """Test pinging with custom timeout values."""
        from fastmcp import FastMCP

        from ros_mcp.tools.connection import register_connection_tools

        mcp = FastMCP("test")
        ws_manager = MockWebSocketManager()

        with patch(
            "ros_mcp.tools.connection.ping_ip_and_port", return_value=mock_ping_success
        ) as mock_ping:
            register_connection_tools(mcp, ws_manager, "127.0.0.1", 9090)

            tools = mcp._tool_manager._tools
            ping_tool = tools.get("ping_robot")

            ping_tool.fn(
                ip="127.0.0.1", port=9090, ping_timeout=5.0, port_timeout=3.0
            )

            mock_ping.assert_called_with("127.0.0.1", 9090, 5.0, 3.0)

    def test_ping_port_closed(self, mock_ping_port_closed):
        """Test pinging when port is closed."""
        from fastmcp import FastMCP

        from ros_mcp.tools.connection import register_connection_tools

        mcp = FastMCP("test")
        ws_manager = MockWebSocketManager()

        with patch(
            "ros_mcp.tools.connection.ping_ip_and_port", return_value=mock_ping_port_closed
        ):
            register_connection_tools(mcp, ws_manager, "127.0.0.1", 9090)

            tools = mcp._tool_manager._tools
            ping_tool = tools.get("ping_robot")

            result = ping_tool.fn(ip="127.0.0.1", port=9090)

            assert result["ping"]["success"] is True
            assert result["port_check"]["open"] is False
            assert "IP_reachable_port_closed" in result["overall_status"]
