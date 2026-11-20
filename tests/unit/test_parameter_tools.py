"""Unit tests for parameter tools and compatibility handling."""

import pytest

from ros_mcp.tools.parameters import register_parameter_tools
from ros_mcp.utils.rosapi_types import _reset_resolver
from ros_mcp.utils.service_verifier import _reset_service_cache


class _FakeMcp:
    def __init__(self):
        self.tools = {}

    def tool(self, **_kwargs):
        def decorator(fn):
            self.tools[fn.__name__] = fn
            return fn

        return decorator


class _FakeWs:
    def __init__(self, responses=None):
        self._responses = responses or {}
        self.default_timeout = 2.0

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def request(self, message, timeout=None):
        service = message.get("service", "")
        if service in self._responses:
            resp = self._responses[service]
            if callable(resp):
                return resp(message)
            return resp
        return {"result": False, "error": f"service {service} does not exist"}


@pytest.fixture(autouse=True)
def reset_state():
    _reset_service_cache()
    _reset_resolver()
    yield
    _reset_service_cache()
    _reset_resolver()


def _get_parameter_tools(responses=None):
    mcp = _FakeMcp()
    ws = _FakeWs(responses)
    register_parameter_tools(mcp, ws)
    return mcp.tools


def test_get_parameter_missing_service_returns_compatibility():
    # When /rosapi/services does not include get_param
    tools = _get_parameter_tools({"/rosapi/services": {"values": {"services": ["/rosapi/topics"]}}})
    result = tools["get_parameter"](name="/turtlesim:background_r")
    assert "error" in result
    assert "compatibility" in result
    assert "/rosapi/get_param" in result["compatibility"]["missing_services"]
    assert result["successful"] is False
    assert result["exists"] is False


def test_get_parameter_success():
    tools = _get_parameter_tools(
        {
            "/rosapi/services": {"values": {"services": ["/rosapi/get_param"]}},
            "/rosapi/get_param": {"values": {"value": "255"}},
        }
    )
    result = tools["get_parameter"](name="/turtlesim:background_r")
    assert result["name"] == "/turtlesim:background_r"
    assert result["value"] == "255"
    assert result["successful"] is True


def test_get_parameter_nonexistent():
    tools = _get_parameter_tools(
        {
            "/rosapi/services": {"values": {"services": ["/rosapi/get_param"]}},
            "/rosapi/get_param": {"values": {"value": '""', "reason": "Parameter does not exist"}},
        }
    )
    result = tools["get_parameter"](name="/turtlesim:nonexistent")
    assert result["successful"] is False
    assert result["exists"] is False
    assert "error" not in result  # Normal non-existent param is not an infrastructure error


def test_set_parameter_missing_service_returns_compatibility():
    tools = _get_parameter_tools(
        {"/rosapi/services": {"values": {"services": ["/rosapi/get_param"]}}}
    )
    result = tools["set_parameter"](name="/turtlesim:background_r", value="200")
    assert "error" in result
    assert "compatibility" in result
    assert "/rosapi/set_param" in result["compatibility"]["missing_services"]
    assert result["successful"] is False


def test_set_parameter_success():
    tools = _get_parameter_tools(
        {
            "/rosapi/services": {
                "values": {"services": ["/rosapi/get_param", "/rosapi/set_param"]}
            },
            "/rosapi/get_param": {"values": {"value": "100"}},
            "/rosapi/set_param": {"values": {"successful": True}},
        }
    )
    result = tools["set_parameter"](name="/turtlesim:background_r", value="200")
    assert result["successful"] is True
    assert result["value"] == "200"


def test_has_parameter_missing_service_returns_compatibility():
    tools = _get_parameter_tools({"/rosapi/services": {"values": {"services": []}}})
    result = tools["has_parameter"](name="/turtlesim:background_r")
    assert "error" in result
    assert "compatibility" in result
    assert result["exists"] is False


def test_has_parameter_exists_and_not_exists():
    tools = _get_parameter_tools(
        {
            "/rosapi/services": {"values": {"services": ["/rosapi/get_param"]}},
            "/rosapi/get_param": lambda msg: (
                {"values": {"value": "123"}}
                if msg["args"]["name"] == "/exists"
                else {"values": {"value": '""'}}
            ),
        }
    )
    assert tools["has_parameter"](name="/exists")["exists"] is True
    assert tools["has_parameter"](name="/missing")["exists"] is False


def test_delete_parameter_missing_service_returns_compatibility():
    tools = _get_parameter_tools(
        {"/rosapi/services": {"values": {"services": ["/rosapi/get_param"]}}}
    )
    result = tools["delete_parameter"](name="/turtlesim:background_r")
    assert "error" in result
    assert "compatibility" in result
    assert "/rosapi/delete_param" in result["compatibility"]["missing_services"]
    assert result["successful"] is False


def test_delete_parameter_success():
    tools = _get_parameter_tools(
        {
            "/rosapi/services": {
                "values": {"services": ["/rosapi/get_param", "/rosapi/delete_param"]}
            },
            "/rosapi/get_param": {"values": {"value": "100"}},
            "/rosapi/delete_param": {"values": {"successful": True}},
        }
    )
    result = tools["delete_parameter"](name="/turtlesim:background_r")
    assert result["successful"] is True


def test_get_parameters_missing_service_returns_list_parameters_error_and_compatibility():
    tools = _get_parameter_tools(
        {"/rosapi/services": {"values": {"services": ["/rosapi/get_param"]}}}
    )
    result = tools["get_parameters"](node_name="turtlesim")
    # Must contain "list_parameters" to preserve compatibility with existing integration tests
    assert "error" in result
    assert "list_parameters" in result["error"]
    assert "compatibility" in result
    assert "/turtlesim/list_parameters" in result["compatibility"]["missing_services"]
    assert result["node"] == "/turtlesim"
    assert result["parameter_count"] == 0


def test_get_parameters_success():
    tools = _get_parameter_tools(
        {
            "/rosapi/services": {"values": {"services": ["/turtlesim/list_parameters"]}},
            "/turtlesim/list_parameters": {
                "values": {"result": {"names": ["background_r", "background_g"]}}
            },
        }
    )
    result = tools["get_parameters"](node_name="turtlesim")
    assert result["node"] == "/turtlesim"
    assert result["parameter_count"] == 2
    assert "/turtlesim:background_r" in result["parameters"]
    assert "/turtlesim:background_g" in result["parameters"]


def test_inspect_all_parameters_missing_service_returns_compatibility():
    tools = _get_parameter_tools(
        {"/rosapi/services": {"values": {"services": ["/rosapi/get_param"]}}}
    )
    result = tools["inspect_all_parameters"]()
    assert "error" in result
    assert "compatibility" in result
    assert "/rosapi/get_param_names" in result["compatibility"]["missing_services"]
    assert result["total_parameters"] == 0


def test_inspect_all_parameters_success_with_type_inference():
    tools = _get_parameter_tools(
        {
            "/rosapi/services": {
                "values": {"services": ["/rosapi/get_param_names", "/rosapi/get_param"]}
            },
            "/rosapi/get_param_names": {
                "values": {"names": ["/turtlesim:background_r", "/my_node:use_sim_time"]}
            },
            "/rosapi/get_param": lambda msg: (
                {"values": {"value": "255"}}
                if msg["args"]["name"] == "/turtlesim:background_r"
                else {"values": {"value": "true"}}
            ),
        }
    )
    result = tools["inspect_all_parameters"]()
    assert result["total_parameters"] == 2
    params = result["parameters"]
    assert "/turtlesim:background_r" in params
    assert params["/turtlesim:background_r"]["value"] == "255"
    assert params["/turtlesim:background_r"]["type"] == "int"
    assert params["/turtlesim:background_r"]["exists"] is True

    assert "/my_node:use_sim_time" in params
    assert params["/my_node:use_sim_time"]["value"] == "true"
    assert params["/my_node:use_sim_time"]["type"] == "bool"


def test_get_parameter_details_missing_service_returns_compatibility():
    tools = _get_parameter_tools({"/rosapi/services": {"values": {"services": []}}})
    result = tools["get_parameter_details"](name="/turtlesim:background_r")
    assert "error" in result
    assert "compatibility" in result
    assert "/rosapi/get_param" in result["compatibility"]["missing_services"]
    assert result["exists"] is False
