"""Tests for ros_mcp.tools.services module."""

import json
from unittest.mock import MagicMock, patch

import pytest

from tests.conftest import MockWebSocketManager


class TestGetServices:
    """Test cases for get_services tool."""

    def test_returns_service_list(self, sample_services_response):
        """Test that get_services returns list of services."""
        from fastmcp import FastMCP

        from ros_mcp.tools.services import register_service_tools

        mcp = FastMCP("test")
        ws_manager = MockWebSocketManager()
        ws_manager.add_response(sample_services_response)

        register_service_tools(mcp, ws_manager)

        tools = mcp._tool_manager._tools
        get_services_tool = tools.get("get_services")
        assert get_services_tool is not None

        result = get_services_tool.fn()

        assert "services" in result
        assert "service_count" in result
        assert "/turtle1/teleport_absolute" in result["services"]

    def test_empty_response(self):
        """Test handling of empty services response."""
        from fastmcp import FastMCP

        from ros_mcp.tools.services import register_service_tools

        mcp = FastMCP("test")
        ws_manager = MockWebSocketManager()
        ws_manager.add_response({"result": True, "values": {"services": []}})

        register_service_tools(mcp, ws_manager)

        tools = mcp._tool_manager._tools
        get_services_tool = tools.get("get_services")

        result = get_services_tool.fn()

        assert result["service_count"] == 0

    def test_service_error(self):
        """Test handling of service call error."""
        from fastmcp import FastMCP

        from ros_mcp.tools.services import register_service_tools

        mcp = FastMCP("test")
        ws_manager = MockWebSocketManager()
        ws_manager.add_response(
            {"result": False, "values": {"message": "Service not available"}}
        )

        register_service_tools(mcp, ws_manager)

        tools = mcp._tool_manager._tools
        get_services_tool = tools.get("get_services")

        result = get_services_tool.fn()

        assert "error" in result


class TestGetServiceType:
    """Test cases for get_service_type tool."""

    def test_returns_service_type(self):
        """Test that get_service_type returns the correct type."""
        from fastmcp import FastMCP

        from ros_mcp.tools.services import register_service_tools

        mcp = FastMCP("test")
        ws_manager = MockWebSocketManager()
        ws_manager.add_response(
            {"result": True, "values": {"type": "turtlesim/srv/TeleportAbsolute"}}
        )

        register_service_tools(mcp, ws_manager)

        tools = mcp._tool_manager._tools
        get_service_type_tool = tools.get("get_service_type")

        result = get_service_type_tool.fn(service="/turtle1/teleport_absolute")

        assert result["service"] == "/turtle1/teleport_absolute"
        assert result["type"] == "turtlesim/srv/TeleportAbsolute"

    def test_empty_service_name(self):
        """Test error when service name is empty."""
        from fastmcp import FastMCP

        from ros_mcp.tools.services import register_service_tools

        mcp = FastMCP("test")
        ws_manager = MockWebSocketManager()

        register_service_tools(mcp, ws_manager)

        tools = mcp._tool_manager._tools
        get_service_type_tool = tools.get("get_service_type")

        result = get_service_type_tool.fn(service="")

        assert "error" in result
        assert "empty" in result["error"].lower()

    def test_nonexistent_service(self):
        """Test handling of non-existent service."""
        from fastmcp import FastMCP

        from ros_mcp.tools.services import register_service_tools

        mcp = FastMCP("test")
        ws_manager = MockWebSocketManager()
        ws_manager.add_response({"result": True, "values": {"type": ""}})

        register_service_tools(mcp, ws_manager)

        tools = mcp._tool_manager._tools
        get_service_type_tool = tools.get("get_service_type")

        result = get_service_type_tool.fn(service="/nonexistent")

        assert "error" in result


class TestGetServiceDetails:
    """Test cases for get_service_details tool."""

    def test_returns_full_details(self):
        """Test that get_service_details returns complete information."""
        from fastmcp import FastMCP

        from ros_mcp.tools.services import register_service_tools

        mcp = FastMCP("test")
        ws_manager = MockWebSocketManager()

        # Add responses for each service call
        ws_manager.add_responses(
            [
                # Service type response
                {"result": True, "values": {"type": "turtlesim/srv/TeleportAbsolute"}},
                # Request details response
                {
                    "result": True,
                    "values": {
                        "typedefs": [
                            {
                                "type": "turtlesim/srv/TeleportAbsolute_Request",
                                "fieldnames": ["x", "y", "theta"],
                                "fieldtypes": ["float32", "float32", "float32"],
                            }
                        ]
                    },
                },
                # Response details response
                {
                    "result": True,
                    "values": {
                        "typedefs": [
                            {
                                "type": "turtlesim/srv/TeleportAbsolute_Response",
                                "fieldnames": [],
                                "fieldtypes": [],
                            }
                        ]
                    },
                },
                # Provider response
                {"result": True, "values": {"node": "/turtlesim"}},
            ]
        )

        register_service_tools(mcp, ws_manager)

        tools = mcp._tool_manager._tools
        get_service_details_tool = tools.get("get_service_details")

        result = get_service_details_tool.fn(service="/turtle1/teleport_absolute")

        assert result["service"] == "/turtle1/teleport_absolute"
        assert result["type"] == "turtlesim/srv/TeleportAbsolute"
        assert "request" in result
        assert "response" in result
        assert "providers" in result

    def test_empty_service_name(self):
        """Test error when service name is empty."""
        from fastmcp import FastMCP

        from ros_mcp.tools.services import register_service_tools

        mcp = FastMCP("test")
        ws_manager = MockWebSocketManager()

        register_service_tools(mcp, ws_manager)

        tools = mcp._tool_manager._tools
        get_service_details_tool = tools.get("get_service_details")

        result = get_service_details_tool.fn(service="")

        assert "error" in result


class TestCallService:
    """Test cases for call_service tool."""

    def test_successful_call(self):
        """Test successful service call."""
        from fastmcp import FastMCP

        from ros_mcp.tools.services import register_service_tools

        mcp = FastMCP("test")
        ws_manager = MockWebSocketManager()
        ws_manager.add_response(
            {"op": "service_response", "result": True, "values": {}}
        )

        register_service_tools(mcp, ws_manager)

        tools = mcp._tool_manager._tools
        call_service_tool = tools.get("call_service")

        result = call_service_tool.fn(
            service_name="/turtle1/teleport_absolute",
            service_type="turtlesim/srv/TeleportAbsolute",
            request={"x": 5.0, "y": 5.0, "theta": 0.0},
        )

        assert result["success"] is True

    def test_call_with_timeout(self):
        """Test service call with custom timeout."""
        from fastmcp import FastMCP

        from ros_mcp.tools.services import register_service_tools

        mcp = FastMCP("test")
        ws_manager = MockWebSocketManager()
        ws_manager.add_response(
            {"op": "service_response", "result": True, "values": {"data": "response"}}
        )

        register_service_tools(mcp, ws_manager)

        tools = mcp._tool_manager._tools
        call_service_tool = tools.get("call_service")

        result = call_service_tool.fn(
            service_name="/slow_service",
            service_type="my_pkg/srv/SlowService",
            request={},
            timeout=10.0,
        )

        assert result["success"] is True

    def test_service_call_failure(self):
        """Test handling of failed service call."""
        from fastmcp import FastMCP

        from ros_mcp.tools.services import register_service_tools

        mcp = FastMCP("test")
        ws_manager = MockWebSocketManager()
        ws_manager.add_response(
            {"result": False, "values": {"message": "Service execution failed"}}
        )

        register_service_tools(mcp, ws_manager)

        tools = mcp._tool_manager._tools
        call_service_tool = tools.get("call_service")

        result = call_service_tool.fn(
            service_name="/failing_service",
            service_type="std_srvs/srv/Empty",
            request={},
        )

        assert result["success"] is False
        assert "error" in result

    def test_error_status_response(self):
        """Test handling of error status response."""
        from fastmcp import FastMCP

        from ros_mcp.tools.services import register_service_tools

        mcp = FastMCP("test")
        ws_manager = MockWebSocketManager()
        ws_manager.add_response(
            {"op": "status", "level": "error", "msg": "Service not found"}
        )

        register_service_tools(mcp, ws_manager)

        tools = mcp._tool_manager._tools
        call_service_tool = tools.get("call_service")

        result = call_service_tool.fn(
            service_name="/nonexistent_service",
            service_type="std_srvs/srv/Empty",
            request={},
        )

        assert result["success"] is False
        assert "error" in result

    def test_no_response(self):
        """Test handling when no response received."""
        from fastmcp import FastMCP

        from ros_mcp.tools.services import register_service_tools

        mcp = FastMCP("test")
        ws_manager = MockWebSocketManager()
        # No response added - will return error

        register_service_tools(mcp, ws_manager)

        tools = mcp._tool_manager._tools
        call_service_tool = tools.get("call_service")

        result = call_service_tool.fn(
            service_name="/timeout_service",
            service_type="std_srvs/srv/Empty",
            request={},
        )

        assert result["success"] is False

    def test_unexpected_response_format(self):
        """Test handling of unexpected response format."""
        from fastmcp import FastMCP

        from ros_mcp.tools.services import register_service_tools

        mcp = FastMCP("test")
        ws_manager = MockWebSocketManager()
        ws_manager.add_response({"op": "unknown", "data": "unexpected"})

        register_service_tools(mcp, ws_manager)

        tools = mcp._tool_manager._tools
        call_service_tool = tools.get("call_service")

        result = call_service_tool.fn(
            service_name="/service",
            service_type="std_srvs/srv/Empty",
            request={},
        )

        assert result["success"] is False
        assert "raw_response" in result


class TestServiceIntegration:
    """Integration-style tests for service tools."""

    def test_get_and_call_service_workflow(self):
        """Test typical workflow of getting service details then calling it."""
        from fastmcp import FastMCP

        from ros_mcp.tools.services import register_service_tools

        mcp = FastMCP("test")
        ws_manager = MockWebSocketManager()

        # First: get_services response
        ws_manager.add_response(
            {
                "result": True,
                "values": {"services": ["/turtle1/teleport_absolute", "/clear"]},
            }
        )
        # Second: get_service_type response
        ws_manager.add_response(
            {"result": True, "values": {"type": "turtlesim/srv/TeleportAbsolute"}}
        )
        # Third: call_service response
        ws_manager.add_response(
            {"op": "service_response", "result": True, "values": {}}
        )

        register_service_tools(mcp, ws_manager)

        tools = mcp._tool_manager._tools

        # Step 1: Get available services
        services_result = tools.get("get_services").fn()
        assert "/turtle1/teleport_absolute" in services_result["services"]

        # Step 2: Get service type
        type_result = tools.get("get_service_type").fn(
            service="/turtle1/teleport_absolute"
        )
        assert type_result["type"] == "turtlesim/srv/TeleportAbsolute"

        # Step 3: Call the service
        call_result = tools.get("call_service").fn(
            service_name="/turtle1/teleport_absolute",
            service_type="turtlesim/srv/TeleportAbsolute",
            request={"x": 5.0, "y": 5.0, "theta": 0.0},
        )
        assert call_result["success"] is True
