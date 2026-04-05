"""Integration tests for service tools.

These tests call the actual MCP tool functions (get_services, get_service_type,
get_service_details, call_service) against a live rosbridge container.
"""

import time

import pytest

pytestmark = [pytest.mark.integration]


class TestGetServices:
    """Verify get_services MCP tool returns the service list."""

    def test_returns_services(self, tools):
        """get_services should return services and service_count."""
        result = tools["get_services"]()
        assert "services" in result
        assert "service_count" in result
        assert result["service_count"] > 0
        assert result["service_count"] == len(result["services"])

    def test_includes_rosapi_services(self, tools):
        """rosapi services should be present (rosapi node is running)."""
        result = tools["get_services"]()
        services = result["services"]
        assert any("nodes" in s for s in services), f"nodes service not in {services}"

    def test_includes_turtlesim_services(self, tools):
        """turtlesim services like /clear or /spawn should be present."""
        result = tools["get_services"]()
        services = result["services"]
        assert any("spawn" in s for s in services), f"spawn not in {services}"


class TestGetServiceType:
    """Verify get_service_type MCP tool returns the service type."""

    def test_known_service_type(self, tools):
        """get_service_type for a turtlesim service should return a type string."""
        result = tools["get_service_type"](service="/kill")
        assert "type" in result
        assert len(result["type"]) > 0

    def test_empty_service_returns_error(self, tools):
        """get_service_type with empty string should return error."""
        result = tools["get_service_type"](service="")
        assert "error" in result

    def test_whitespace_service_returns_error(self, tools):
        """get_service_type with whitespace should return error."""
        result = tools["get_service_type"](service="   ")
        assert "error" in result


class TestGetServiceDetails:
    """Verify get_service_details MCP tool returns full service definition."""

    def test_spawn_details(self, tools):
        """get_service_details for /spawn should return request/response fields."""
        result = tools["get_service_details"](service="/spawn")
        assert result["service"] == "/spawn"
        assert len(result["type"]) > 0
        assert "request" in result
        assert "response" in result

    def test_empty_service_returns_error(self, tools):
        """get_service_details with empty string should return error."""
        result = tools["get_service_details"](service="")
        assert "error" in result

    def test_whitespace_service_returns_error(self, tools):
        """get_service_details with whitespace should return error."""
        result = tools["get_service_details"](service="   ")
        assert "error" in result


class TestCallService:
    """Verify call_service MCP tool can call a live service."""

    def test_call_spawn_turtle(self, tools):
        """call_service for /spawn should create a new turtle."""
        # Use a unique name to avoid conflicts across test runs
        turtle_name = f"test_turtle_{int(time.time_ns())}"
        type_result = tools["get_service_type"](service="/spawn")
        spawn_type = type_result["type"]
        result = tools["call_service"](
            service_name="/spawn",
            service_type=spawn_type,
            request={"x": 3.0, "y": 3.0, "theta": 0.0, "name": turtle_name},
        )
        assert result["success"] is True
