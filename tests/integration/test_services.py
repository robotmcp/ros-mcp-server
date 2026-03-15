"""Integration tests for service tools against a real ROS2 rosbridge."""

import pytest

pytestmark = [pytest.mark.integration, pytest.mark.slow]


class TestGetServices:
    def test_returns_services(self, tools):
        result = tools["get_services"]()
        assert "services" in result
        assert len(result["services"]) > 0

    def test_includes_turtlesim_services(self, tools):
        result = tools["get_services"]()
        services = result["services"]
        assert any("/spawn" in s for s in services)
        assert any("/kill" in s for s in services)

    def test_has_service_count(self, tools):
        result = tools["get_services"]()
        assert result["service_count"] == len(result["services"])


class TestGetServiceType:
    def test_set_pen_type(self, tools):
        result = tools["get_service_type"](service="/turtle1/set_pen")
        assert "type" in result
        assert "error" not in result

    def test_nonexistent_service(self, tools):
        result = tools["get_service_type"](service="/nonexistent_service_xyz")
        assert "error" in result


class TestGetServiceDetails:
    def test_set_pen_details(self, tools):
        result = tools["get_service_details"](service="/turtle1/set_pen")
        assert "error" not in result
        assert result.get("type") != ""
        assert "request" in result
        assert "response" in result


class TestCallService:
    def test_call_set_pen(self, tools):
        result = tools["call_service"](
            service_name="/turtle1/set_pen",
            service_type="turtlesim/srv/SetPen",
            request={"r": 255, "g": 0, "b": 0, "width": 2},
        )
        assert result.get("success") is True

    def test_call_nonexistent_service(self, tools):
        result = tools["call_service"](
            service_name="/nonexistent_service_xyz",
            service_type="std_srvs/srv/Empty",
            request={},
        )
        assert result.get("success") is False
