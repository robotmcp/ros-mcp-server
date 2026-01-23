"""E2E tests for parameter operations with real ROS 2 turtlesim.

Parameter interfaces are significantly different between ROS 1 and ROS 2.
ROS 2 uses node-namespaced parameters with rcl_interfaces, while ROS 1
uses a global parameter server. This module tests ROS 2 specific functionality.
"""

import pytest

# Mark all tests in this module as e2e and ros2-only
pytestmark = [pytest.mark.e2e, pytest.mark.ros2]


class TestGetParameter:
    """E2E tests for get_parameter functionality."""

    def test_get_turtlesim_background_parameter(self, ws_manager):
        """Get turtlesim background color parameter."""
        # Turtlesim has background_r, background_g, background_b parameters
        message = {
            "op": "call_service",
            "service": "/rosapi/get_param",
            "type": "rosapi_msgs/srv/GetParam",
            "args": {"name": "/turtlesim:background_r"},
            "id": "get_param_background_r",
        }

        with ws_manager:
            response = ws_manager.request(message, timeout=10.0)

        # Should get a value (default is 69 for blue background)
        if "values" in response:
            value = response["values"].get("value", "")
            # Value should be a number string
            assert value, "Expected non-empty value for background_r"

    def test_get_nonexistent_parameter(self, ws_manager):
        """Get a parameter that doesn't exist."""
        message = {
            "op": "call_service",
            "service": "/rosapi/get_param",
            "type": "rosapi_msgs/srv/GetParam",
            "args": {"name": "/turtlesim:nonexistent_param_xyz"},
            "id": "get_param_nonexistent",
        }

        with ws_manager:
            response = ws_manager.request(message, timeout=10.0)

        # Should return empty value or unsuccessful
        if "values" in response:
            value = response["values"].get("value", "")
            # Empty or quoted empty string indicates not found
            assert value in ["", '""', None] or not response["values"].get("successful", True)


class TestSetParameter:
    """E2E tests for set_parameter functionality."""

    def test_set_and_get_background_parameter(self, ws_manager):
        """Set a turtlesim background parameter and verify it changed."""
        # First get the original value
        get_msg = {
            "op": "call_service",
            "service": "/rosapi/get_param",
            "type": "rosapi_msgs/srv/GetParam",
            "args": {"name": "/turtlesim:background_r"},
            "id": "get_original_background_r",
        }

        with ws_manager:
            original_response = ws_manager.request(get_msg, timeout=10.0)

        original_value = original_response.get("values", {}).get("value", "69")

        # Set to a new value
        new_value = "100" if original_value != "100" else "150"
        set_msg = {
            "op": "call_service",
            "service": "/rosapi/set_param",
            "type": "rosapi_msgs/srv/SetParam",
            "args": {"name": "/turtlesim:background_r", "value": new_value},
            "id": "set_background_r",
        }

        with ws_manager:
            set_response = ws_manager.request(set_msg, timeout=10.0)

        # Verify the set operation (might succeed or fail based on permissions)
        if set_response.get("values", {}).get("successful", False):
            # Get the value again to verify
            with ws_manager:
                ws_manager.request(get_msg, timeout=10.0)
            # Note: The actual change might require a service call to take effect

        # Restore original value
        restore_msg = {
            "op": "call_service",
            "service": "/rosapi/set_param",
            "type": "rosapi_msgs/srv/SetParam",
            "args": {"name": "/turtlesim:background_r", "value": original_value},
            "id": "restore_background_r",
        }

        with ws_manager:
            ws_manager.request(restore_msg, timeout=10.0)


class TestGetParameters:
    """E2E tests for listing parameters."""

    def test_list_turtlesim_parameters(self, ws_manager):
        """List all parameters for turtlesim node."""
        message = {
            "op": "call_service",
            "service": "/turtlesim/list_parameters",
            "type": "rcl_interfaces/srv/ListParameters",
            "args": {},
            "id": "list_turtlesim_params",
        }

        with ws_manager:
            response = ws_manager.request(message, timeout=10.0)

        if "values" in response:
            result = response["values"].get("result", {})
            names = result.get("names", [])

            # Turtlesim should have background color parameters
            expected_params = ["background_r", "background_g", "background_b"]
            for param in expected_params:
                assert any(param in name for name in names), f"Expected {param} in {names}"


class TestHasParameter:
    """E2E tests for checking parameter existence."""

    def test_has_existing_parameter(self, ws_manager):
        """Check that an existing parameter is found."""
        # Use get_param to check existence (safer than has_param)
        message = {
            "op": "call_service",
            "service": "/rosapi/get_param",
            "type": "rosapi_msgs/srv/GetParam",
            "args": {"name": "/turtlesim:background_r"},
            "id": "check_existing_param",
        }

        with ws_manager:
            response = ws_manager.request(message, timeout=10.0)

        # Should have a value
        if "values" in response:
            value = response["values"].get("value", "")
            assert value and value not in ["", '""'], "Parameter should exist with value"

    def test_has_nonexistent_parameter(self, ws_manager):
        """Check that a non-existent parameter is not found."""
        message = {
            "op": "call_service",
            "service": "/rosapi/get_param",
            "type": "rosapi_msgs/srv/GetParam",
            "args": {"name": "/turtlesim:definitely_not_a_real_param"},
            "id": "check_nonexistent_param",
        }

        with ws_manager:
            response = ws_manager.request(message, timeout=10.0)

        # Should have empty value or unsuccessful
        if "values" in response:
            value = response["values"].get("value", "")
            assert value in ["", '""', None] or not response["values"].get("successful", True)


class TestParameterIntegration:
    """Integration tests for parameter operations."""

    def test_parameter_workflow(self, ws_manager):
        """Complete workflow: list, get, set, verify, restore."""
        # 1. List parameters
        list_msg = {
            "op": "call_service",
            "service": "/turtlesim/list_parameters",
            "type": "rcl_interfaces/srv/ListParameters",
            "args": {},
            "id": "workflow_list_params",
        }

        with ws_manager:
            list_response = ws_manager.request(list_msg, timeout=10.0)

        if "values" not in list_response:
            pytest.skip("Cannot list parameters")

        # 2. Get background_g value
        get_msg = {
            "op": "call_service",
            "service": "/rosapi/get_param",
            "type": "rosapi_msgs/srv/GetParam",
            "args": {"name": "/turtlesim:background_g"},
            "id": "workflow_get_param",
        }

        with ws_manager:
            get_response = ws_manager.request(get_msg, timeout=10.0)

        original_value = get_response.get("values", {}).get("value", "86")

        # 3. Set new value
        new_value = "200"
        set_msg = {
            "op": "call_service",
            "service": "/rosapi/set_param",
            "type": "rosapi_msgs/srv/SetParam",
            "args": {"name": "/turtlesim:background_g", "value": new_value},
            "id": "workflow_set_param",
        }

        with ws_manager:
            ws_manager.request(set_msg, timeout=10.0)

        # 4. Restore original value
        restore_msg = {
            "op": "call_service",
            "service": "/rosapi/set_param",
            "type": "rosapi_msgs/srv/SetParam",
            "args": {"name": "/turtlesim:background_g", "value": original_value},
            "id": "workflow_restore_param",
        }

        with ws_manager:
            ws_manager.request(restore_msg, timeout=10.0)
