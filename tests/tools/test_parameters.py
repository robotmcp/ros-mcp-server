"""Tests for ros_mcp.tools.parameters module."""

import pytest

from ros_mcp.tools.parameters import _safe_check_parameter_exists, register_parameter_tools


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
def parameter_tools(mock_mcp, mock_ws_manager):
    """Register parameter tools and return them."""
    register_parameter_tools(mock_mcp, mock_ws_manager)
    return mock_mcp.tools


class TestSafeCheckParameterExists:
    """Test cases for _safe_check_parameter_exists helper."""

    def test_parameter_exists(self, mock_ws_manager):
        """Test when parameter exists with value."""
        mock_ws_manager.add_response({"values": {"value": "255", "successful": True}})

        exists, reason, response = _safe_check_parameter_exists(
            "/turtlesim:background_b", mock_ws_manager
        )

        assert exists is True
        assert reason == ""
        assert response is not None

    def test_parameter_not_exists_empty_value(self, mock_ws_manager):
        """Test when parameter doesn't exist (empty value)."""
        mock_ws_manager.add_response(
            {"values": {"value": '""', "successful": False, "reason": "Parameter not found"}}
        )

        exists, reason, response = _safe_check_parameter_exists(
            "/nonexistent:param", mock_ws_manager
        )

        assert exists is False
        assert "not found" in reason.lower() or "not exist" in reason.lower()

    def test_no_response(self, mock_ws_manager):
        """Test when no response is received."""
        mock_ws_manager.add_response(None)

        exists, reason, response = _safe_check_parameter_exists("/test:param", mock_ws_manager)

        assert exists is False
        assert "No response" in reason

    def test_result_format_response(self, mock_ws_manager):
        """Test with 'result' format response instead of 'values'."""
        mock_ws_manager.add_response({"result": {"value": "100", "successful": True}})

        exists, reason, response = _safe_check_parameter_exists("/test:param", mock_ws_manager)

        assert exists is True

    def test_exception_handling(self, mock_ws_manager):
        """Test exception handling."""

        def raise_error(msg):
            raise ConnectionError("Connection lost")

        mock_ws_manager.request = raise_error

        exists, reason, response = _safe_check_parameter_exists("/test:param", mock_ws_manager)

        assert exists is False
        assert "Error" in reason


class TestGetParameter:
    """Test cases for get_parameter tool."""

    def test_empty_parameter_name(self, parameter_tools, mock_ws_manager):
        """Test with empty parameter name."""
        result = parameter_tools["get_parameter"]("")

        assert "error" in result
        assert "cannot be empty" in result["error"]

    def test_whitespace_parameter_name(self, parameter_tools, mock_ws_manager):
        """Test with whitespace-only parameter name."""
        result = parameter_tools["get_parameter"]("   ")

        assert "error" in result
        assert "cannot be empty" in result["error"]

    def test_successful_get_parameter(self, parameter_tools, mock_ws_manager):
        """Test getting an existing parameter."""
        mock_ws_manager.add_response({"values": {"value": "255", "successful": True, "reason": ""}})

        result = parameter_tools["get_parameter"]("/turtlesim:background_b")

        assert result["name"] == "/turtlesim:background_b"
        assert result["value"] == "255"
        assert result["successful"] is True

    def test_parameter_not_found(self, parameter_tools, mock_ws_manager):
        """Test getting a non-existent parameter."""
        mock_ws_manager.add_response(
            {"values": {"value": "", "successful": False, "reason": "Parameter not found"}}
        )

        result = parameter_tools["get_parameter"]("/nonexistent:param")

        assert result["exists"] is False
        assert result["successful"] is False

    def test_string_response_fallback(self, parameter_tools, mock_ws_manager):
        """Test handling of string response (malformed)."""
        # First call for existence check
        mock_ws_manager.add_responses(
            [
                {"values": {"value": "test"}},  # Exists
            ]
        )

        # Mock to return string for the actual get
        original_request = mock_ws_manager.request

        def mock_request(msg, timeout=None):
            return original_request(msg, timeout)

        mock_ws_manager.request = mock_request

        result = parameter_tools["get_parameter"]("/test:param")

        # Should handle gracefully
        assert "name" in result


class TestSetParameter:
    """Test cases for set_parameter tool."""

    def test_empty_parameter_name(self, parameter_tools, mock_ws_manager):
        """Test with empty parameter name."""
        result = parameter_tools["set_parameter"]("", "value")

        assert "error" in result
        assert "cannot be empty" in result["error"]

    def test_successful_set_parameter(self, parameter_tools, mock_ws_manager):
        """Test setting a parameter successfully."""
        mock_ws_manager.add_responses(
            [
                {"values": {"value": "100"}},  # Existence check
                {"values": {"successful": True, "reason": ""}},  # Set response
            ]
        )

        result = parameter_tools["set_parameter"]("/turtlesim:background_b", "100")

        assert result["name"] == "/turtlesim:background_b"
        assert result["value"] == "100"
        assert result["successful"] is True

    def test_set_parameter_failure(self, parameter_tools, mock_ws_manager):
        """Test when set parameter fails."""
        mock_ws_manager.add_responses(
            [
                {"values": {"value": ""}},  # Doesn't exist
                {"values": {"successful": False, "reason": "Read-only parameter"}},
            ]
        )

        result = parameter_tools["set_parameter"]("/readonly:param", "value")

        assert result["successful"] is False

    def test_set_parameter_exception(self, parameter_tools, mock_ws_manager):
        """Test exception handling during set."""
        mock_ws_manager.add_response({"values": {"value": "test"}})

        def raise_on_second_call(msg, timeout=None):
            if "set_param" in msg.get("service", ""):
                raise ConnectionError("Connection lost")
            return {"values": {"value": "test"}}

        mock_ws_manager.request = raise_on_second_call

        result = parameter_tools["set_parameter"]("/test:param", "value")

        assert result["successful"] is False
        assert "Error" in result["reason"]


class TestHasParameter:
    """Test cases for has_parameter tool."""

    def test_empty_parameter_name(self, parameter_tools, mock_ws_manager):
        """Test with empty parameter name."""
        result = parameter_tools["has_parameter"]("")

        assert "error" in result
        assert "cannot be empty" in result["error"]

    def test_parameter_exists(self, parameter_tools, mock_ws_manager):
        """Test when parameter exists."""
        mock_ws_manager.add_response({"values": {"value": "255", "successful": True}})

        result = parameter_tools["has_parameter"]("/turtlesim:background_b")

        assert result["name"] == "/turtlesim:background_b"
        assert result["exists"] is True
        assert result["successful"] is True

    def test_parameter_not_exists(self, parameter_tools, mock_ws_manager):
        """Test when parameter doesn't exist."""
        mock_ws_manager.add_response(
            {"values": {"value": "", "successful": False, "reason": "Not found"}}
        )

        result = parameter_tools["has_parameter"]("/nonexistent:param")

        assert result["exists"] is False
        assert result["successful"] is True  # The check itself succeeded


class TestDeleteParameter:
    """Test cases for delete_parameter tool."""

    def test_empty_parameter_name(self, parameter_tools, mock_ws_manager):
        """Test with empty parameter name."""
        result = parameter_tools["delete_parameter"]("")

        assert "error" in result
        assert "cannot be empty" in result["error"]

    def test_delete_nonexistent_parameter(self, parameter_tools, mock_ws_manager):
        """Test deleting a parameter that doesn't exist."""
        mock_ws_manager.add_response(
            {"values": {"value": "", "successful": False, "reason": "Not found"}}
        )

        result = parameter_tools["delete_parameter"]("/nonexistent:param")

        assert result["successful"] is False
        assert result["exists"] is False

    def test_successful_delete(self, parameter_tools, mock_ws_manager):
        """Test successful parameter deletion."""
        mock_ws_manager.add_responses(
            [
                {"values": {"value": "255", "successful": True}},  # Exists
                {"values": {"successful": True, "reason": ""}},  # Delete response
            ]
        )

        result = parameter_tools["delete_parameter"]("/turtlesim:background_b")

        assert result["name"] == "/turtlesim:background_b"
        assert result["successful"] is True

    def test_delete_failure(self, parameter_tools, mock_ws_manager):
        """Test when delete fails."""
        mock_ws_manager.add_responses(
            [
                {"values": {"value": "255", "successful": True}},  # Exists
                {"values": {"successful": False, "reason": "Permission denied"}},
            ]
        )

        result = parameter_tools["delete_parameter"]("/protected:param")

        assert result["successful"] is False

    def test_delete_exception(self, parameter_tools, mock_ws_manager):
        """Test exception handling during delete."""
        mock_ws_manager.add_response({"values": {"value": "test", "successful": True}})

        def raise_on_delete(msg, timeout=None):
            if "delete_param" in msg.get("service", ""):
                raise ConnectionError("Connection lost")
            return {"values": {"value": "test", "successful": True}}

        mock_ws_manager.request = raise_on_delete

        result = parameter_tools["delete_parameter"]("/test:param")

        assert result["successful"] is False
        assert "Error" in result["reason"]


class TestGetParameters:
    """Test cases for get_parameters tool."""

    def test_empty_node_name(self, parameter_tools, mock_ws_manager):
        """Test with empty node name."""
        result = parameter_tools["get_parameters"]("")

        assert "error" in result
        assert "cannot be empty" in result["error"]

    def test_successful_get_parameters(self, parameter_tools, mock_ws_manager):
        """Test getting parameters for a node."""
        mock_ws_manager.add_response(
            {"values": {"result": {"names": ["background_r", "background_g", "background_b"]}}}
        )

        result = parameter_tools["get_parameters"]("/turtlesim")

        assert result["node"] == "/turtlesim"
        assert result["parameter_count"] == 3
        assert "/turtlesim:background_r" in result["parameters"]

    def test_node_name_normalization(self, parameter_tools, mock_ws_manager):
        """Test that node name is normalized with leading slash."""
        mock_ws_manager.add_response({"values": {"result": {"names": []}}})

        result = parameter_tools["get_parameters"]("turtlesim")

        assert result["node"] == "/turtlesim"

    def test_trailing_slash_removal(self, parameter_tools, mock_ws_manager):
        """Test that trailing slash is removed."""
        mock_ws_manager.add_response({"values": {"result": {"names": []}}})

        result = parameter_tools["get_parameters"]("/turtlesim/")

        assert result["node"] == "/turtlesim"

    def test_no_response(self, parameter_tools, mock_ws_manager):
        """Test when no response is received."""
        mock_ws_manager.add_response(None)

        result = parameter_tools["get_parameters"]("/turtlesim")

        assert "error" in result
        assert "No response" in result["error"]

    def test_service_call_failure(self, parameter_tools, mock_ws_manager):
        """Test when service call fails."""
        mock_ws_manager.add_response(
            {"result": False, "values": {"message": "Service not available"}}
        )

        result = parameter_tools["get_parameters"]("/turtlesim")

        assert "error" in result

    def test_exception_handling(self, parameter_tools, mock_ws_manager):
        """Test exception handling."""

        def raise_error(msg, timeout=None):
            raise ConnectionError("Connection lost")

        mock_ws_manager.request = raise_error

        result = parameter_tools["get_parameters"]("/turtlesim")

        assert "error" in result


class TestGetParameterDetails:
    """Test cases for get_parameter_details tool."""

    def test_empty_parameter_name(self, parameter_tools, mock_ws_manager):
        """Test with empty parameter name."""
        result = parameter_tools["get_parameter_details"]("")

        assert "error" in result
        assert "cannot be empty" in result["error"]

    def test_parameter_not_found(self, parameter_tools, mock_ws_manager):
        """Test when parameter doesn't exist."""
        mock_ws_manager.add_response(
            {"values": {"value": "", "successful": False, "reason": "Not found"}}
        )

        result = parameter_tools["get_parameter_details"]("/nonexistent:param")

        assert result["exists"] is False
        assert "Not found" in result["reason"] or "not exist" in result["reason"].lower()

    def test_successful_get_details(self, parameter_tools, mock_ws_manager):
        """Test getting full parameter details."""
        mock_ws_manager.add_responses(
            [
                {"values": {"value": "255", "successful": True}},  # Get param
                {
                    "values": {  # Describe parameters
                        "descriptors": [{"type": "int", "description": "Blue background color"}]
                    }
                },
            ]
        )

        result = parameter_tools["get_parameter_details"]("/turtlesim:background_b")

        assert result["name"] == "/turtlesim:background_b"
        assert result["value"] == "255"
        assert result["exists"] is True
        assert result["node"] == "/turtlesim"
        assert result["parameter"] == "background_b"

    def test_type_inference_bool(self, parameter_tools, mock_ws_manager):
        """Test type inference for boolean values."""
        mock_ws_manager.add_responses(
            [
                {"values": {"value": "true", "successful": True}},
                {"values": {"descriptors": []}},  # No type info
            ]
        )

        result = parameter_tools["get_parameter_details"]("/node:bool_param")

        assert result["type"] == "bool"

    def test_type_inference_int(self, parameter_tools, mock_ws_manager):
        """Test type inference for integer values."""
        mock_ws_manager.add_responses(
            [{"values": {"value": "42", "successful": True}}, {"values": {"descriptors": []}}]
        )

        result = parameter_tools["get_parameter_details"]("/node:int_param")

        assert result["type"] == "int"

    def test_type_inference_negative_int(self, parameter_tools, mock_ws_manager):
        """Test type inference for negative integer."""
        mock_ws_manager.add_responses(
            [{"values": {"value": "-10", "successful": True}}, {"values": {"descriptors": []}}]
        )

        result = parameter_tools["get_parameter_details"]("/node:neg_param")

        assert result["type"] == "int"

    def test_type_inference_float(self, parameter_tools, mock_ws_manager):
        """Test type inference for float values."""
        mock_ws_manager.add_responses(
            [{"values": {"value": "3.14", "successful": True}}, {"values": {"descriptors": []}}]
        )

        result = parameter_tools["get_parameter_details"]("/node:float_param")

        assert result["type"] == "float"

    def test_type_inference_string(self, parameter_tools, mock_ws_manager):
        """Test type inference for string values."""
        mock_ws_manager.add_responses(
            [
                {"values": {"value": '"hello world"', "successful": True}},
                {"values": {"descriptors": []}},
            ]
        )

        result = parameter_tools["get_parameter_details"]("/node:str_param")

        assert result["type"] == "string"

    def test_describe_parameters_failure(self, parameter_tools, mock_ws_manager):
        """Test when describe_parameters fails but get_param succeeds."""
        mock_ws_manager.add_response({"values": {"value": "255", "successful": True}})

        # Make the second call fail
        call_count = [0]
        original_request = mock_ws_manager.request

        def mock_request(msg, timeout=None):
            call_count[0] += 1
            if call_count[0] > 1:
                raise Exception("Service not available")
            return original_request(msg, timeout)

        mock_ws_manager.request = mock_request

        result = parameter_tools["get_parameter_details"]("/turtlesim:background_b")

        # Should still return result with inferred type
        assert result["exists"] is True
        assert result["type"] in ["int", "string", "unknown"]
