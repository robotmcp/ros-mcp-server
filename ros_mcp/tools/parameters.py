"""Parameter tools for ROS MCP."""

from fastmcp import FastMCP

from ros_mcp.utils.websocket import WebSocketManager


def get_parameter_impl(ws_manager: WebSocketManager, name: str) -> dict:
    """
    Get a single ROS parameter value by name. Works only with ROS 2.

    Args:
        ws_manager: WebSocketManager instance to use for ROS connections
        name (str): The parameter name (e.g., '/turtlesim:background_b')

    Returns:
        dict: Contains parameter value and metadata, or error message if parameter not found.
    """
    if not name or not name.strip():
        return {"error": "Parameter name cannot be empty"}

    message = {
        "op": "call_service",
        "service": "/rosapi/get_param",
        "type": "rosapi/GetParam",
        "args": {"name": name},
        "id": f"get_param_{name.replace('/', '_').replace(':', '_')}",
    }

    with ws_manager:
        response = ws_manager.request(message)

    if response and "values" in response:
        result_data = response["values"]
        return {
            "name": name,
            "value": result_data.get("value", ""),
            "successful": result_data.get("successful", False),
            "reason": result_data.get("reason", ""),
        }
    elif response and "result" in response and response["result"]:
        result_data = response["result"]
        return {
            "name": name,
            "value": result_data.get("value", ""),
            "successful": result_data.get("successful", False),
            "reason": result_data.get("reason", ""),
        }
    else:
        error_msg = (
            response.get("values", {}).get("message", "Service call failed")
            if response
            else "No response"
        )
        return {"error": f"Failed to get parameter {name}: {error_msg}"}


def set_parameter_impl(ws_manager: WebSocketManager, name: str, value: str) -> dict:
    """
    Set a single ROS parameter value. Works only with ROS 2.

    Args:
        ws_manager: WebSocketManager instance to use for ROS connections
        name (str): The parameter name (e.g., '/turtlesim:background_b')
        value (str): The parameter value to set

    Returns:
        dict: Contains success status and metadata, or error message if failed.
    """
    if not name or not name.strip():
        return {"error": "Parameter name cannot be empty"}

    message = {
        "op": "call_service",
        "service": "/rosapi/set_param",
        "type": "rosapi/SetParam",
        "args": {"name": name, "value": value},
        "id": f"set_param_{name.replace('/', '_').replace(':', '_')}",
    }

    with ws_manager:
        response = ws_manager.request(message)

    if response and "values" in response:
        result_data = response["values"]
        return {
            "name": name,
            "value": value,
            "successful": result_data.get("successful", False),
            "reason": result_data.get("reason", ""),
        }
    elif response and "result" in response and response["result"]:
        result_data = response["result"]
        return {
            "name": name,
            "value": value,
            "successful": result_data.get("successful", False),
            "reason": result_data.get("reason", ""),
        }
    else:
        error_msg = (
            response.get("values", {}).get("message", "Service call failed")
            if response
            else "No response"
        )
        return {"error": f"Failed to set parameter {name}: {error_msg}"}


def has_parameter_impl(ws_manager: WebSocketManager, name: str) -> dict:
    """
    Check if a ROS parameter exists. Works only with ROS 2.

    Args:
        ws_manager: WebSocketManager instance to use for ROS connections
        name (str): The parameter name (e.g., '/turtlesim:background_b')

    Returns:
        dict: Contains existence status and metadata, or error message if failed.
    """
    if not name or not name.strip():
        return {"error": "Parameter name cannot be empty"}

    message = {
        "op": "call_service",
        "service": "/rosapi/has_param",
        "type": "rosapi/HasParam",
        "args": {"name": name},
        "id": f"has_param_{name.replace('/', '_').replace(':', '_')}",
    }

    with ws_manager:
        response = ws_manager.request(message)

    if response and "values" in response:
        result_data = response["values"]
        return {
            "name": name,
            "exists": result_data.get("exists", False),
            "successful": result_data.get("successful", False),
            "reason": result_data.get("reason", ""),
        }
    elif response and "result" in response and response["result"]:
        result_data = response["result"]
        return {
            "name": name,
            "exists": result_data.get("exists", False),
            "successful": result_data.get("successful", False),
            "reason": result_data.get("reason", ""),
        }
    else:
        error_msg = (
            response.get("values", {}).get("message", "Service call failed")
            if response
            else "No response"
        )
        return {"error": f"Failed to check parameter {name}: {error_msg}"}


def delete_parameter_impl(ws_manager: WebSocketManager, name: str) -> dict:
    """
    Delete a ROS parameter. Works only with ROS 2.

    Args:
        ws_manager: WebSocketManager instance to use for ROS connections
        name (str): The parameter name (e.g., '/turtlesim:background_b')

    Returns:
        dict: Contains success status and metadata, or error message if failed.
    """
    if not name or not name.strip():
        return {"error": "Parameter name cannot be empty"}

    message = {
        "op": "call_service",
        "service": "/rosapi/delete_param",
        "type": "rosapi/DeleteParam",
        "args": {"name": name},
        "id": f"delete_param_{name.replace('/', '_').replace(':', '_')}",
    }

    with ws_manager:
        response = ws_manager.request(message)

    if response and "values" in response:
        result_data = response["values"]
        return {
            "name": name,
            "successful": result_data.get("successful", False),
            "reason": result_data.get("reason", ""),
        }
    elif response and "result" in response and response["result"]:
        result_data = response["result"]
        return {
            "name": name,
            "successful": result_data.get("successful", False),
            "reason": result_data.get("reason", ""),
        }
    else:
        error_msg = (
            response.get("values", {}).get("message", "Service call failed")
            if response
            else "No response"
        )
        return {"error": f"Failed to delete parameter {name}: {error_msg}"}


def get_parameters_impl(ws_manager: WebSocketManager) -> dict:
    """
    Get list of all ROS parameter names. Works only with ROS 2.

    Args:
        ws_manager: WebSocketManager instance to use for ROS connections

    Returns:
        dict: Contains list of all parameter names, or error message if failed.
    """
    message = {
        "op": "call_service",
        "service": "/rosapi/get_param_names",
        "type": "rosapi/GetParamNames",
        "args": {},
        "id": "get_parameters_request_1",
    }

    with ws_manager:
        response = ws_manager.request(message)

    if response and "values" in response:
        names = response["values"].get("names", [])
        return {"parameters": names, "parameter_count": len(names)}
    elif response and "result" in response and response["result"]:
        result_data = response["result"]
        if isinstance(result_data, dict):
            names = result_data.get("names", [])
        else:
            names = []
        return {"parameters": names, "parameter_count": len(names)}
    else:
        error_msg = (
            response.get("values", {}).get("message", "Service call failed")
            if response
            else "No response"
        )
        return {"error": f"Failed to get parameter names: {error_msg}"}


def inspect_all_parameters_impl(ws_manager: WebSocketManager) -> dict:
    """
    Get comprehensive information about all ROS parameters including values and metadata.
    Works only with ROS 2.

    Args:
        ws_manager: WebSocketManager instance to use for ROS connections

    Returns:
        dict: Contains detailed information about all parameters,
            including parameter names, values, and metadata.
    """
    # First get all parameters
    parameters_message = {
        "op": "call_service",
        "service": "/rosapi/get_param_names",
        "type": "rosapi/GetParamNames",
        "args": {},
        "id": "inspect_all_parameters_request_1",
    }

    with ws_manager:
        parameters_response = ws_manager.request(parameters_message)

        if not parameters_response or "values" not in parameters_response:
            return {"error": "Failed to get parameters list"}

        parameters = parameters_response["values"].get("names", [])
        parameter_details = {}

        # Get details for each parameter
        parameter_errors = []
        for param_name in parameters:
            # Get parameter value
            value_message = {
                "op": "call_service",
                "service": "/rosapi/get_param",
                "type": "rosapi/GetParam",
                "args": {"name": param_name},
                "id": f"get_param_{param_name.replace('/', '_').replace(':', '_')}",
            }

            value_response = ws_manager.request(value_message)
            param_value = ""
            param_successful = False
            if value_response and "values" in value_response:
                value_data = value_response["values"]
                param_value = value_data.get("value", "")
                param_successful = value_data.get("successful", False)
            elif value_response and "result" in value_response and value_response["result"]:
                value_data = value_response["result"]
                param_value = value_data.get("value", "")
                param_successful = value_data.get("successful", False)
            elif value_response and "error" in value_response:
                parameter_errors.append(f"Parameter {param_name}: {value_response['error']}")

            # Get parameter type (using describe_parameters service)
            type_message = {
                "op": "call_service",
                "service": "/rosapi/describe_parameters",
                "type": "rcl_interfaces/DescribeParameters",
                "args": {"names": [param_name]},
                "id": f"describe_param_{param_name.replace('/', '_').replace(':', '_')}",
            }

            type_response = ws_manager.request(type_message)
            param_type = "unknown"

            # Handle different response formats for parameter type detection
            if type_response and isinstance(type_response, dict):
                if "values" in type_response:
                    result_data = type_response["values"]
                    if isinstance(result_data, dict):
                        descriptors = result_data.get("descriptors", [])
                        if descriptors and len(descriptors) > 0:
                            param_type = descriptors[0].get("type", "unknown")
                elif "result" in type_response and type_response["result"]:
                    result_data = type_response["result"]
                    if isinstance(result_data, dict):
                        descriptors = result_data.get("descriptors", [])
                        if descriptors and len(descriptors) > 0:
                            param_type = descriptors[0].get("type", "unknown")
                elif "error" in type_response:
                    parameter_errors.append(
                        f"Parameter {param_name} type: {type_response['error']}"
                    )

            # Fallback: Try to infer type from value
            if param_type == "unknown" and param_value:
                try:
                    # Remove quotes for type checking
                    clean_value = param_value.strip('"')

                    # Try to parse as different types
                    if clean_value.lower() in ["true", "false"]:
                        param_type = "bool"
                    elif clean_value.isdigit() or (
                        clean_value.startswith("-") and clean_value[1:].isdigit()
                    ):
                        param_type = "int"
                    elif (
                        "." in clean_value
                        and clean_value.replace(".", "").replace("-", "").isdigit()
                    ):
                        param_type = "float"
                    elif param_value.startswith('"') and param_value.endswith('"'):
                        param_type = "string"
                    elif clean_value == "":
                        param_type = "string"
                    else:
                        param_type = "string"
                except Exception:
                    param_type = "string"

            parameter_details[param_name] = {
                "value": param_value,
                "type": param_type,
                "exists": param_successful,
            }

        return {
            "total_parameters": len(parameters),
            "parameters": parameter_details,
            "parameter_errors": parameter_errors,  # Include any errors encountered during inspection
        }


def get_parameter_details_impl(ws_manager: WebSocketManager, name: str) -> dict:
    """
    Get comprehensive details about a specific ROS parameter including value, type, and metadata.
    Works only with ROS 2.

    Args:
        ws_manager: WebSocketManager instance to use for ROS connections
        name (str): The parameter name (e.g., '/turtlesim:background_r')

    Returns:
        dict: Contains detailed parameter information or error details.
    """
    # Validate input
    if not name or not name.strip():
        return {"error": "Parameter name cannot be empty"}

    # Get parameter value
    value_message = {
        "op": "call_service",
        "service": "/rosapi/get_param",
        "type": "rosapi/GetParam",
        "args": {"name": name},
        "id": f"get_param_details_{name.replace('/', '_').replace(':', '_')}",
    }

    with ws_manager:
        value_response = ws_manager.request(value_message)

    if not value_response or "values" not in value_response:
        return {"error": f"Failed to get parameter {name}"}

    value_data = value_response["values"]
    param_value = value_data.get("value", "")
    param_successful = value_data.get("successful", False)

    if not param_successful:
        return {"error": f"Parameter {name} does not exist"}

    # Get parameter type
    type_message = {
        "op": "call_service",
        "service": "/rosapi/describe_parameters",
        "type": "rcl_interfaces/DescribeParameters",
        "args": {"names": [name]},
        "id": f"describe_param_details_{name.replace('/', '_').replace(':', '_')}",
    }

    with ws_manager:
        type_response = ws_manager.request(type_message)

    param_type = "unknown"
    param_description = ""

    if type_response and isinstance(type_response, dict):
        if "values" in type_response:
            result_data = type_response["values"]
            if isinstance(result_data, dict):
                descriptors = result_data.get("descriptors", [])
                if descriptors and len(descriptors) > 0:
                    descriptor = descriptors[0]
                    param_type = descriptor.get("type", "unknown")
                    param_description = descriptor.get("description", "")
        elif "result" in type_response and type_response["result"]:
            result_data = type_response["result"]
            if isinstance(result_data, dict):
                descriptors = result_data.get("descriptors", [])
                if descriptors and len(descriptors) > 0:
                    descriptor = descriptors[0]
                    param_type = descriptor.get("type", "unknown")
                    param_description = descriptor.get("description", "")

    # Fallback: Try to infer type from value
    if param_type == "unknown" and param_value:
        try:
            clean_value = param_value.strip('"')
            if clean_value.lower() in ["true", "false"]:
                param_type = "bool"
            elif clean_value.isdigit() or (
                clean_value.startswith("-") and clean_value[1:].isdigit()
            ):
                param_type = "int"
            elif "." in clean_value and clean_value.replace(".", "").replace("-", "").isdigit():
                param_type = "float"
            elif param_value.startswith('"') and param_value.endswith('"'):
                param_type = "string"
            elif clean_value == "":
                param_type = "string"
            else:
                param_type = "string"
        except Exception:
            param_type = "string"

    return {
        "name": name,
        "value": param_value,
        "type": param_type,
        "exists": param_successful,
        "description": param_description,
        "node": name.split(":")[0] if ":" in name else "",
        "parameter": name.split(":")[1] if ":" in name else name,
    }


def register_parameter_tools(
    mcp: FastMCP,
    ws_manager: WebSocketManager,
) -> None:
    """Register all parameter-related tools."""

    @mcp.tool(
        description=(
            "Get a single ROS parameter value by name. Works only with ROS 2.\n"
            "Example:\nget_parameter('/turtlesim:background_b')"
        )
    )
    def get_parameter(name: str) -> dict:
        """Get a single ROS parameter value by name. Works only with ROS 2."""
        return get_parameter_impl(ws_manager, name)

    @mcp.tool(
        description=(
            "Set a single ROS parameter value. Works only with ROS 2.\n"
            "Example:\nset_parameter('/turtlesim:background_b', '255')"
        )
    )
    def set_parameter(name: str, value: str) -> dict:
        """Set a single ROS parameter value. Works only with ROS 2."""
        return set_parameter_impl(ws_manager, name, value)

    @mcp.tool(
        description=(
            "Check if a ROS parameter exists. Works only with ROS 2.\n"
            "Example:\nhas_parameter('/turtlesim:background_b')"
        )
    )
    def has_parameter(name: str) -> dict:
        """Check if a ROS parameter exists. Works only with ROS 2."""
        return has_parameter_impl(ws_manager, name)

    @mcp.tool(
        description=(
            "Delete a ROS parameter. Works only with ROS 2.\n"
            "Example:\ndelete_parameter('/turtlesim:background_b')"
        )
    )
    def delete_parameter(name: str) -> dict:
        """Delete a ROS parameter. Works only with ROS 2."""
        return delete_parameter_impl(ws_manager, name)

    @mcp.tool(
        description=(
            "Get list of all ROS parameter names. Works only with ROS 2.\n"
            "Example:\nget_parameters()"
        )
    )
    def get_parameters() -> dict:
        """Get list of all ROS parameter names. Works only with ROS 2."""
        return get_parameters_impl(ws_manager)

    @mcp.tool(
        description=(
            "Get comprehensive information about all ROS parameters including values and metadata. "
            "Works only with ROS 2.\n"
            "Example:\n"
            "inspect_all_parameters()"
        )
    )
    def inspect_all_parameters() -> dict:
        """Get comprehensive information about all ROS parameters including values and metadata. Works only with ROS 2."""
        return inspect_all_parameters_impl(ws_manager)

    @mcp.tool(
        description=(
            "Get comprehensive details about a specific ROS parameter including value, type, and metadata. "
            "Works only with ROS 2.\n"
            "Example:\n"
            "get_parameter_details('/turtlesim:background_r')"
        )
    )
    def get_parameter_details(name: str) -> dict:
        """Get comprehensive details about a specific ROS parameter including value, type, and metadata. Works only with ROS 2."""
        return get_parameter_details_impl(ws_manager, name)
