"""Integration tests for parameter tools.

These tests call the actual MCP tool functions (get_parameter, set_parameter,
has_parameter, delete_parameter, get_parameters, get_parameter_details)
against a live rosbridge container.

Parameter semantics differ across ROS versions:
- ROS 1 (melodic/noetic): global parameter server, slash-separated names
  (e.g. /turtlesim/background_r). The test seeds a known parameter via
  set_parameter before reading.
- ROS 2 (humble/jazzy): per-node parameters keyed "node:name" through
  rosbridge (e.g. /turtlesim:background_r). turtlesim populates background_r/g/b
  on launch.

get_parameters relies on rcl_interfaces/srv/ListParameters and is ROS 2-only;
on ROS 1 the tool returns a graceful "service does not exist" error, which the
test asserts directly.
"""

import time

import pytest

from ros_mcp.utils.rosapi_types import RosVersion, get_ros_version

pytestmark = [pytest.mark.integration]


_PARAMS = {
    RosVersion.ROS1: {
        "seed_name": "/ros_mcp_test_param",
        "seed_value": "42",
        # On ROS 1, the only param we know exists post-fixture is the one we seed.
        "existing_name": "/ros_mcp_test_param",
    },
    RosVersion.ROS2: {
        "seed_name": "/turtlesim:background_r",
        "seed_value": "100",
        # On ROS 2, turtlesim populates background_r on launch.
        "existing_name": "/turtlesim:background_r",
    },
}


def _params_for_current_version() -> dict:
    version = get_ros_version()
    return _PARAMS[version]


@pytest.fixture
def params():
    return _params_for_current_version()


@pytest.fixture
def ros1_seeded_param(tools, params):
    """On ROS 1, set a known parameter before the test and clean it up after."""
    if get_ros_version() != RosVersion.ROS1:
        yield params
        return
    tools["set_parameter"](name=params["seed_name"], value=params["seed_value"])
    yield params
    tools["delete_parameter"](name=params["seed_name"])


class TestGetParameter:
    def test_returns_value_for_known_parameter(self, tools, ros1_seeded_param):
        result = tools["get_parameter"](name=ros1_seeded_param["existing_name"])
        assert "value" in result
        assert result.get("successful") is True
        assert str(result["value"]).strip() != ""

    def test_empty_name_returns_error(self, tools):
        result = tools["get_parameter"](name="")
        assert "error" in result

    def test_whitespace_name_returns_error(self, tools):
        result = tools["get_parameter"](name="   ")
        assert "error" in result


class TestSetParameter:
    def test_set_succeeds(self, tools, params):
        version = get_ros_version()
        if version == RosVersion.ROS1:
            unique_name = f"/ros_mcp_test_set_{int(time.time_ns())}"
            result = tools["set_parameter"](name=unique_name, value="7")
            assert result.get("successful") is True
            tools["delete_parameter"](name=unique_name)
            return
        # ROS 2: mutating turtlesim's params, so capture and restore.
        target = params["seed_name"]
        original = tools["get_parameter"](name=target).get("value")
        try:
            result = tools["set_parameter"](name=target, value="7")
            assert result.get("successful") is True
        finally:
            if original is not None:
                tools["set_parameter"](name=target, value=str(original))

    def test_empty_name_returns_error(self, tools):
        result = tools["set_parameter"](name="", value="1")
        assert "error" in result


class TestHasParameter:
    def test_existing_parameter(self, tools, ros1_seeded_param):
        result = tools["has_parameter"](name=ros1_seeded_param["existing_name"])
        assert result["exists"] is True

    def test_nonexistent_parameter(self, tools):
        result = tools["has_parameter"](name="/ros_mcp_does_not_exist_xyz")
        assert result["exists"] is False

    def test_empty_name_returns_error(self, tools):
        result = tools["has_parameter"](name="")
        assert "error" in result


class TestDeleteParameter:
    def test_delete_round_trip(self, tools):
        if get_ros_version() == RosVersion.ROS2:
            pytest.skip(
                "ROS 2 delete-success is not exercisable against this setup: turtlesim "
                "silently drops undeclared params (set 'succeeds' but nothing persists "
                "to delete), and deleting a declared param crashes the rosapi node. The "
                "testable ROS 2 delete paths (nonexistent -> unsuccessful, empty name -> "
                "error) are covered by the other tests in this class."
            )
        name = f"/ros_mcp_test_delete_{int(time.time_ns())}"
        tools["set_parameter"](name=name, value="1")
        assert tools["has_parameter"](name=name)["exists"] is True
        result = tools["delete_parameter"](name=name)
        assert result.get("successful") is True
        assert tools["has_parameter"](name=name)["exists"] is False

    def test_nonexistent_returns_unsuccessful(self, tools):
        result = tools["delete_parameter"](name="/ros_mcp_does_not_exist_xyz")
        assert result.get("successful") is False

    def test_empty_name_returns_error(self, tools):
        result = tools["delete_parameter"](name="")
        assert "error" in result


class TestGetParameters:
    def test_returns_list_for_known_node(self, tools):
        result = tools["get_parameters"](node_name="turtlesim")
        if get_ros_version() == RosVersion.ROS1:
            # get_parameters relies on rcl_interfaces/srv/ListParameters which only
            # exists on ROS 2. The tool documents "Works only with ROS 2" and returns
            # a graceful error pointing at the missing per-node service.
            assert "error" in result
            assert "list_parameters" in result["error"]
            return
        assert "parameters" in result
        assert "parameter_count" in result
        assert isinstance(result["parameters"], list)

    def test_empty_node_returns_error(self, tools):
        result = tools["get_parameters"](node_name="")
        assert "error" in result


class TestGetParameterDetails:
    def test_returns_details_for_known_parameter(self, tools, ros1_seeded_param):
        # On ROS 1, the describe_parameters call fails internally but the tool
        # falls back to type inference from the value, so the test passes on both
        # versions. On ROS 2, describe_parameters supplies the type.
        result = tools["get_parameter_details"](name=ros1_seeded_param["existing_name"])
        assert result["exists"] is True
        assert "value" in result
        assert "type" in result

    def test_nonexistent_returns_error_response(self, tools):
        if get_ros_version() == RosVersion.ROS1:
            name = "/ros_mcp_definitely_does_not_exist"
        else:
            name = "/turtlesim:does_not_exist"
        result = tools["get_parameter_details"](name=name)
        assert result["exists"] is False

    def test_empty_name_returns_error(self, tools):
        result = tools["get_parameter_details"](name="")
        assert "error" in result
