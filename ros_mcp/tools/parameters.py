"""Parameter tools for ROS MCP."""

from fastmcp import FastMCP
from mcp.types import ToolAnnotations

from ros_mcp.utils.response import _extract_error, _safe_get_values
from ros_mcp.utils.rosapi_types import rosapi_service, rosapi_type
from ros_mcp.utils.service_verifier import is_service_available, make_compatibility_response
from ros_mcp.utils.websocket import WebSocketManager


def _safe_check_parameter_exists(
    name: str, ws_manager: WebSocketManager
) -> tuple[bool, str, dict | None]:
    """
    Safely check if a parameter exists using get_param (which doesn't crash rosapi_node).
    Also returns the full response if the parameter exists, to avoid redundant calls.

    Returns:
        tuple: (exists: bool, reason: str, response: dict | None)
    """

    def _is_empty_value(value: str) -> bool:
        """Check if a parameter value indicates the parameter does not exist."""
        if not value:
            return True
        # Strip quotes (handles '""' which represents empty string)
        stripped = value.strip('"').strip("'")
        if not stripped:
            return True
        # ROS 1 rosbridge get_param returns the literal JSON value `null` (string "null")
        # for missing parameters, with result=true. Treat as nonexistent.
        return stripped == "null"

    get_param_svc = rosapi_service("get_param")
    if not is_service_available(get_param_svc, ws_manager):
        return False, f"Service '{get_param_svc}' is not available", None

    message = {
        "op": "call_service",
        "service": get_param_svc,
        "type": rosapi_type("GetParam"),
        "args": {"name": name},
        "id": f"check_param_exists_{name.replace('/', '_').replace(':', '_')}",
    }

    try:
        with ws_manager:
            response = ws_manager.request(message)

        if not response:
            return False, "No response from service", None

        # Check if parameter exists based on response
        if response and "values" in response:
            result_data = response["values"]
            if isinstance(result_data, dict):
                value = result_data.get("value", "")
                # Check if value is effectively empty (handles '""' case for non-existent params)
                if _is_empty_value(value):
                    reason = result_data.get("reason", "Parameter does not exist")
                    return False, reason, None
                # Parameter exists and has a value
                return True, "", response
        elif response and "result" in response:
            result_data = response["result"]
            if isinstance(result_data, dict):
                value = result_data.get("value", "")
                # Check if value is effectively empty
                if _is_empty_value(value):
                    reason = result_data.get("reason", "Parameter does not exist")
                    return False, reason, None
                # Parameter exists and has a value
                return True, "", response
            elif result_data:
                # Direct result (non-dict) - assume it exists
                return True, "", response

        return False, "Unexpected response format", None
    except Exception as e:
        return False, f"Error checking parameter: {str(e)}", None


def register_parameter_tools(
    mcp: FastMCP,
    ws_manager: WebSocketManager,
) -> None:
    """Register all parameter-related tools."""

    @mcp.tool(
        description=(
            "Get a single ROS parameter value by name.\n"
            "Example:\nget_parameter('/turtlesim:background_b') (ROS 2) or get_parameter('/turtlesim/background_b') (ROS 1)"
        ),
        annotations=ToolAnnotations(
            title="Get Parameter",
            readOnlyHint=True,
        ),
    )
    def get_parameter(name: str) -> dict:
        """
        Get a single ROS parameter value by name.

        Args:
            name (str): The parameter name (e.g., '/turtlesim:background_b' on ROS 2 or '/turtlesim/background_b' on ROS 1)

        Returns:
            dict: Contains parameter value and metadata, or error message if parameter not found.
        """
        if not name or not name.strip():
            return {"error": "Parameter name cannot be empty"}

        # Check if parameter exists first to avoid unnecessary calls
        # (This uses get_param which is safe, unlike has_param which crashes)
        # The response is returned if parameter exists, so we can reuse it
        exists, reason, response = _safe_check_parameter_exists(name, ws_manager)
        if not exists:
            get_param_svc = rosapi_service("get_param")
            if not is_service_available(get_param_svc, ws_manager):
                return make_compatibility_response(
                    tool_name="get_parameter",
                    issue=f"Failed to get parameter '{name}': service '{get_param_svc}' is not available",
                    missing_services=[get_param_svc],
                    required_services=[get_param_svc],
                    suggestions=[
                        "Ensure rosbridge and rosapi are running",
                        "Check if parameter service is available using get_services()",
                    ],
                    note=f"Parameter retrieval requires {get_param_svc} service",
                    extra_fields={
                        "name": name,
                        "value": "",
                        "successful": False,
                        "reason": reason or f"Service {get_param_svc} is not available",
                        "exists": False,
                    },
                )
            return {
                "name": name,
                "value": "",
                "successful": False,
                "reason": reason or f"Parameter {name} does not exist",
                "exists": False,
            }

        # We already have the response from the existence check, so process it
        # Handle string responses (fallback for malformed responses)
        if isinstance(response, str):
            return {
                "name": name,
                "value": "",
                "successful": False,
                "reason": f"Unexpected response format: {response}",
            }

        # Process the response - parameter exists, so extract the value
        if response and "values" in response:
            result_data = response["values"]
            if isinstance(result_data, dict):
                value = result_data.get("value", "")
                successful = result_data.get("successful", False) or bool(value)
                reason = result_data.get("reason", "")
                return {
                    "name": name,
                    "value": value,
                    "successful": successful,
                    "reason": reason,
                }
        elif response and "result" in response:
            result_data = response["result"]
            if isinstance(result_data, dict):
                value = result_data.get("value", "")
                successful = result_data.get("successful", False) or bool(value)
                reason = result_data.get("reason", "")
                return {
                    "name": name,
                    "value": value,
                    "successful": successful,
                    "reason": reason,
                }
            else:
                # Direct value in result
                return {
                    "name": name,
                    "value": str(result_data) if result_data is not None else "",
                    "successful": True,
                    "reason": "",
                }

        # Fallback for unexpected response format
        error_msg = (
            _extract_error(response) if response and isinstance(response, dict) else "No response"
        )
        return {"error": f"Failed to get parameter {name}: {error_msg}"}

    @mcp.tool(
        description=(
            "Set a single ROS parameter value.\n"
            "Example:\nset_parameter('/turtlesim:background_b', '255') (ROS 2) or set_parameter('/turtlesim/background_b', '255') (ROS 1)"
        ),
        annotations=ToolAnnotations(
            title="Set Parameter",
            destructiveHint=True,
        ),
    )
    def set_parameter(name: str, value: str) -> dict:
        """
        Set a single ROS parameter value.

        Args:
            name (str): The parameter name (e.g., '/turtlesim:background_b' on ROS 2 or '/turtlesim/background_b' on ROS 1)
            value (str): The parameter value to set

        Returns:
            dict: Contains success status and metadata, or error message if failed.
        """
        if not name or not name.strip():
            return {"error": "Parameter name cannot be empty"}

        set_param_svc = rosapi_service("set_param")
        if not is_service_available(set_param_svc, ws_manager):
            return make_compatibility_response(
                tool_name="set_parameter",
                issue=f"Failed to set parameter '{name}': service '{set_param_svc}' is not available",
                missing_services=[set_param_svc],
                required_services=[set_param_svc],
                suggestions=[
                    "Ensure rosbridge and rosapi are running",
                    "Check if parameter service is available using get_services()",
                ],
                note=f"Setting parameters requires {set_param_svc} service",
                extra_fields={"name": name, "value": value, "successful": False},
            )

        # Check if parameter exists first (set_param can create parameters, but checking
        # helps avoid issues and provides better error messages)
        exists, reason, _ = _safe_check_parameter_exists(name, ws_manager)
        # Note: We continue even if parameter doesn't exist, as set_param can create it

        message = {
            "op": "call_service",
            "service": set_param_svc,
            "type": rosapi_type("SetParam"),
            "args": {"name": name, "value": value},
            "id": f"set_param_{name.replace('/', '_').replace(':', '_')}",
        }

        try:
            with ws_manager:
                response = ws_manager.request(message)
        except Exception as e:
            # Catch any exceptions to prevent crashes
            return {
                "name": name,
                "value": value,
                "successful": False,
                "reason": f"Error setting parameter: {str(e)}",
            }

        # Handle string responses (fallback for malformed responses)
        if isinstance(response, str):
            return {
                "name": name,
                "value": value,
                "successful": False,
                "reason": f"Unexpected response format: {response}",
            }

        if response and "values" in response:
            result_data = response["values"]
            if isinstance(result_data, dict):
                successful = result_data.get("successful", True)  # Default to True if not specified
                return {
                    "name": name,
                    "value": value,
                    "successful": successful,
                    "reason": result_data.get("reason", ""),
                }
        elif response and "result" in response:
            result_data = response["result"]
            if isinstance(result_data, dict):
                successful = result_data.get("successful", True)  # Default to True if not specified
                return {
                    "name": name,
                    "value": value,
                    "successful": successful,
                    "reason": result_data.get("reason", ""),
                }
            else:
                # Direct result (boolean or other)
                return {
                    "name": name,
                    "value": value,
                    "successful": bool(result_data) if result_data is not None else True,
                    "reason": "",
                }

        # Fallback for unexpected response format
        error_msg = (
            _extract_error(response) if response and isinstance(response, dict) else "No response"
        )
        return {"error": f"Failed to set parameter {name}: {error_msg}"}

    @mcp.tool(
        description=(
            "Check if a ROS parameter exists.\n"
            "Example:\nhas_parameter('/turtlesim:background_b') (ROS 2) or has_parameter('/turtlesim/background_b') (ROS 1)"
        ),
        annotations=ToolAnnotations(
            title="Has Parameter",
            readOnlyHint=True,
        ),
    )
    def has_parameter(name: str) -> dict:
        """
        Check if a ROS parameter exists.

        Args:
            name (str): The parameter name (e.g., '/turtlesim:background_b' on ROS 2 or '/turtlesim/background_b' on ROS 1)

        Returns:
            dict: Contains existence status and metadata, or error message if failed.

        Note: This uses get_param internally (via _safe_check_parameter_exists) to avoid
        crashes in rosapi_node when checking for non-existent parameters.

        Limitation: existence is inferred from the parameter's value because the
        rosbridge ROS 1 get_param API has no separate "exists" signal. A parameter
        whose value is an empty string or the literal string "null" is therefore
        reported as not existing (false negative).
        """
        if not name or not name.strip():
            return {"error": "Parameter name cannot be empty"}

        get_param_svc = rosapi_service("get_param")
        if not is_service_available(get_param_svc, ws_manager):
            return make_compatibility_response(
                tool_name="has_parameter",
                issue=f"Failed to check parameter '{name}': service '{get_param_svc}' is not available",
                missing_services=[get_param_svc],
                required_services=[get_param_svc],
                suggestions=[
                    "Ensure rosbridge and rosapi are running",
                    "Check if parameter service is available using get_services()",
                ],
                note=f"Checking parameter existence requires {get_param_svc} service",
                extra_fields={"name": name, "exists": False, "successful": False},
            )

        # Use safe check function directly to avoid rosapi_node crashes
        # The /rosapi/has_param service crashes when the parameter doesn't exist
        exists, reason, _ = _safe_check_parameter_exists(name, ws_manager)

        return {
            "name": name,
            "exists": exists,
            "successful": True,
            "reason": reason if not exists else "",
        }

    @mcp.tool(
        description=(
            "Delete a ROS parameter.\n"
            "Example:\ndelete_parameter('/turtlesim:background_b') (ROS 2) or delete_parameter('/turtlesim/background_b') (ROS 1)"
        ),
        annotations=ToolAnnotations(
            title="Delete Parameter",
            destructiveHint=True,
        ),
    )
    def delete_parameter(name: str) -> dict:
        """
        Delete a ROS parameter.

        Args:
            name (str): The parameter name (e.g., '/turtlesim:background_b' on ROS 2 or '/turtlesim/background_b' on ROS 1)

        Returns:
            dict: Contains success status and metadata, or error message if failed.
        """
        if not name or not name.strip():
            return {"error": "Parameter name cannot be empty"}

        delete_param_svc = rosapi_service("delete_param")
        if not is_service_available(delete_param_svc, ws_manager):
            return make_compatibility_response(
                tool_name="delete_parameter",
                issue=f"Failed to delete parameter '{name}': service '{delete_param_svc}' is not available",
                missing_services=[delete_param_svc],
                required_services=[delete_param_svc],
                suggestions=[
                    "Ensure rosbridge and rosapi are running",
                    "Check if parameter service is available using get_services()",
                ],
                note=f"Deleting parameters requires {delete_param_svc} service",
                extra_fields={"name": name, "successful": False, "exists": False},
            )

        # Check if parameter exists first to avoid unnecessary calls
        exists, reason, _ = _safe_check_parameter_exists(name, ws_manager)
        if not exists:
            return {
                "name": name,
                "successful": False,
                "reason": reason or f"Parameter {name} does not exist",
                "exists": False,
            }

        message = {
            "op": "call_service",
            "service": delete_param_svc,
            "type": rosapi_type("DeleteParam"),
            "args": {"name": name},
            "id": f"delete_param_{name.replace('/', '_').replace(':', '_')}",
        }

        try:
            with ws_manager:
                response = ws_manager.request(message)
        except Exception as e:
            # Catch any exceptions to prevent crashes
            return {
                "name": name,
                "successful": False,
                "reason": f"Error deleting parameter: {str(e)}",
            }

        # Handle string responses (fallback for malformed responses)
        if isinstance(response, str):
            return {
                "name": name,
                "successful": False,
                "reason": f"Unexpected response format: {response}",
            }

        if response and "values" in response:
            result_data = response["values"]
            if isinstance(result_data, dict):
                # ROS 1 rosapi delete_param returns {"values": {}, "result": true} on
                # success, so when "successful" is absent inside values, fall back to
                # the top-level "result" field.
                if "successful" in result_data:
                    successful = bool(result_data["successful"])
                else:
                    successful = bool(response.get("result"))
                reason = result_data.get("reason", "")
                return {
                    "name": name,
                    "successful": successful,
                    "reason": reason,
                }
        elif response and "result" in response:
            result_data = response["result"]
            if isinstance(result_data, dict):
                successful = result_data.get("successful", False)
                reason = result_data.get("reason", "")
                return {
                    "name": name,
                    "successful": successful,
                    "reason": reason,
                }
            elif result_data:
                # Direct boolean result
                return {
                    "name": name,
                    "successful": bool(result_data),
                    "reason": "",
                }

        # Fallback for unexpected response format
        error_msg = (
            _extract_error(response) if response and isinstance(response, dict) else "No response"
        )
        return {"error": f"Failed to delete parameter {name}: {error_msg}"}

    @mcp.tool(
        description=(
            "Get list of all ROS parameter names for a specific node. Works only with ROS 2.\n"
            "Example:\nget_parameters('cam2image')\nget_parameters('/cam2image')"
        ),
        annotations=ToolAnnotations(
            title="Get Parameters",
            readOnlyHint=True,
        ),
    )
    def get_parameters(node_name: str) -> dict:
        """
        Get list of all ROS parameter names for a specific node. Works only with ROS 2.

        Args:
            node_name (str): The node name (e.g., '/turtlesim')

        Returns:
            dict: Contains list of all parameter names for the node, or error message if failed.
        """
        if not node_name or not node_name.strip():
            return {"error": "Node name cannot be empty"}

        # Normalize node name (ensure it starts with /)
        normalized_node = node_name.strip()
        if not normalized_node.startswith("/"):
            normalized_node = f"/{normalized_node}"

        # Remove trailing slash if present
        if normalized_node.endswith("/") and len(normalized_node) > 1:
            normalized_node = normalized_node[:-1]

        service_name = f"{normalized_node}/list_parameters"

        if not is_service_available(service_name, ws_manager):
            return make_compatibility_response(
                tool_name="get_parameters",
                issue=f"Failed to get parameters for node {normalized_node}: service '{service_name}' is not available",
                missing_services=[service_name],
                required_services=[service_name],
                suggestions=[
                    "Node parameter listing via list_parameters is only available on ROS 2 nodes.",
                    "On ROS 1, parameters are managed globally; use inspect_all_parameters or get_parameter.",
                    f"Ensure node '{normalized_node}' is running and exposes parameter services.",
                ],
                note=f"Requires {service_name} (rcl_interfaces/srv/ListParameters)",
                extra_fields={"node": normalized_node, "parameters": [], "parameter_count": 0},
            )

        message = {
            "op": "call_service",
            "service": service_name,
            "type": "rcl_interfaces/srv/ListParameters",
            "args": {},
            "id": f"get_parameters_{normalized_node.replace('/', '_')}",
        }

        try:
            with ws_manager:
                response = ws_manager.request(message)
        except Exception as e:
            # Catch any exceptions to prevent crashes
            return {"error": f"Failed to get parameters for node {normalized_node}: {str(e)}"}

        # Handle string responses (fallback for malformed responses)
        if isinstance(response, str):
            return {
                "error": f"Failed to get parameters for node {normalized_node}: Unexpected response format: {response}"
            }

        # Check for timeout or connection errors
        if not response:
            return {
                "error": f"Failed to get parameters for node {normalized_node}: No response or timeout from rosbridge"
            }

        # Check for explicit error in response
        if isinstance(response, dict) and "error" in response:
            error_msg = response.get("error", "Service call failed")
            return {"error": f"Failed to get parameters for node {normalized_node}: {error_msg}"}

        # Check for service response errors first
        if response and "result" in response and not response["result"]:
            # Service call failed - return error with details from values
            error_msg = _extract_error(response)
            if "does not exist" in error_msg.lower():
                return make_compatibility_response(
                    tool_name="get_parameters",
                    issue=f"Failed to get parameters for node {normalized_node}: {error_msg}",
                    missing_services=[service_name],
                    required_services=[service_name],
                    suggestions=[
                        "Node parameter listing via list_parameters is only available on ROS 2 nodes.",
                        "On ROS 1, parameters are managed globally; use inspect_all_parameters or get_parameter.",
                    ],
                    note=f"Requires {service_name} (rcl_interfaces/srv/ListParameters)",
                    extra_fields={"node": normalized_node, "parameters": [], "parameter_count": 0},
                )
            return {"error": f"Failed to get parameters for node {normalized_node}: {error_msg}"}

        # Extract parameter names from response
        names = []
        if response and "values" in response:
            result_data = response["values"]
            if isinstance(result_data, dict):
                # Check for result.names structure
                result_obj = result_data.get("result", {})
                if isinstance(result_obj, dict):
                    names = result_obj.get("names", [])
                else:
                    # Try direct names field
                    names = result_data.get("names", [])
        elif response and "result" in response:
            result_data = response["result"]
            if isinstance(result_data, dict):
                # Check for result.names structure
                result_obj = result_data.get("result", {})
                if isinstance(result_obj, dict):
                    names = result_obj.get("names", [])
                else:
                    names = result_data.get("names", [])

        # Format parameter names with node prefix
        formatted_names = [f"{normalized_node}:{name}" for name in names]

        return {
            "node": normalized_node,
            "parameters": formatted_names,
            "parameter_count": len(formatted_names),
        }

    @mcp.tool(
        description=(
            "Get comprehensive information about all ROS parameters including values and metadata.\n"
            "Example:\ninspect_all_parameters()"
        ),
        annotations=ToolAnnotations(
            title="Inspect All Parameters",
            readOnlyHint=True,
        ),
    )
    def inspect_all_parameters() -> dict:
        """Get comprehensive information about all ROS parameters including values and metadata.

        Returns:
            dict: Contains total_parameters, parameters dict with values and types,
                and any parameter_errors encountered during inspection.
        """
        get_param_names_svc = rosapi_service("get_param_names")
        if not is_service_available(get_param_names_svc, ws_manager):
            return make_compatibility_response(
                tool_name="inspect_all_parameters",
                issue="Parameter inspection not supported by this rosbridge/rosapi version",
                missing_services=[get_param_names_svc],
                required_services=[get_param_names_svc],
                suggestions=[
                    "This rosbridge version doesn't support get_param_names service",
                    "Use get_parameter(name) to read known parameters individually",
                ],
                note=f"Parameter inspection requires {get_param_names_svc} service",
                extra_fields={"total_parameters": 0, "parameters": {}, "parameter_errors": []},
            )

        parameters_message = {
            "op": "call_service",
            "service": get_param_names_svc,
            "type": rosapi_type("GetParamNames"),
            "args": {},
            "id": "inspect_all_parameters_request_1",
        }

        try:
            with ws_manager:
                parameters_response = ws_manager.request(parameters_message)
        except Exception as e:
            return {
                "error": f"Failed to get parameters list: {e}",
                "total_parameters": 0,
                "parameters": {},
                "parameter_errors": [str(e)],
            }

        if not parameters_response:
            return {
                "error": "Failed to get parameters list: no response from service",
                "total_parameters": 0,
                "parameters": {},
                "parameter_errors": [],
            }

        param_values = _safe_get_values(parameters_response)
        if param_values is None or not isinstance(param_values, dict):
            if isinstance(parameters_response.get("result"), dict):
                names = parameters_response["result"].get("names", [])
            elif isinstance(parameters_response.get("result"), list):
                names = parameters_response["result"]
            else:
                return {
                    "error": "Failed to get parameters list: invalid response format",
                    "total_parameters": 0,
                    "parameters": {},
                    "parameter_errors": [],
                }
        else:
            names = param_values.get("names", [])

        parameter_details = {}
        parameter_errors = []

        # Check if describe_parameters is available
        describe_svc = rosapi_service("describe_parameters")
        has_describe = is_service_available(describe_svc, ws_manager)

        for param_name in names:
            exists, reason, val_resp = _safe_check_parameter_exists(param_name, ws_manager)
            param_value = ""
            param_successful = exists

            if val_resp and isinstance(val_resp, dict):
                val_data = val_resp.get("values") or val_resp.get("result")
                if isinstance(val_data, dict):
                    param_value = val_data.get("value", "")
                elif val_data is not None:
                    param_value = str(val_data)

            param_type = "unknown"
            if has_describe:
                try:
                    type_message = {
                        "op": "call_service",
                        "service": describe_svc,
                        "type": "rcl_interfaces/DescribeParameters",
                        "args": {"names": [param_name]},
                        "id": f"describe_param_{param_name.replace('/', '_').replace(':', '_')}",
                    }
                    with ws_manager:
                        type_response = ws_manager.request(type_message)
                    if type_response and isinstance(type_response, dict):
                        t_vals = _safe_get_values(type_response)
                        if isinstance(t_vals, dict):
                            descriptors = t_vals.get("descriptors", [])
                            if descriptors:
                                param_type = descriptors[0].get("type", "unknown")
                except Exception:
                    pass

            # Fallback to type inference from value
            if param_type == "unknown" and param_value:
                try:
                    clean_value = param_value.strip('"')
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
            "total_parameters": len(names),
            "parameters": parameter_details,
            "parameter_errors": parameter_errors,
        }

    @mcp.tool(
        description=(
            "Get comprehensive details about a specific ROS parameter including value, type, and metadata.\n"
            "Example:\nget_parameter_details('/turtlesim:background_r') (ROS 2) or get_parameter_details('/turtlesim/background_r') (ROS 1)"
        ),
        annotations=ToolAnnotations(
            title="Get Parameter Details",
            readOnlyHint=True,
        ),
    )
    def get_parameter_details(name: str) -> dict:
        """
        Get comprehensive details about a specific ROS parameter including value, type, and metadata.

        Args:
            name (str): The parameter name (e.g., '/turtlesim:background_r' on ROS 2 or '/turtlesim/background_r' on ROS 1)

        Returns:
            dict: Contains detailed parameter information or error details.
        """
        # Validate input
        if not name or not name.strip():
            return {"error": "Parameter name cannot be empty"}

        # Helper to create error response
        def _error_response(reason: str) -> dict:
            return {
                "name": name,
                "value": "",
                "type": "unknown",
                "exists": False,
                "description": "",
                "node": name.split(":")[0] if ":" in name else "",
                "parameter": name.split(":")[1] if ":" in name else name,
                "reason": reason,
            }

        get_param_svc = rosapi_service("get_param")
        if not is_service_available(get_param_svc, ws_manager):
            return make_compatibility_response(
                tool_name="get_parameter_details",
                issue=f"Failed to get parameter details for '{name}': service '{get_param_svc}' is not available",
                missing_services=[get_param_svc],
                required_services=[get_param_svc],
                suggestions=["Ensure rosbridge and rosapi are running"],
                note=f"Parameter inspection requires {get_param_svc} service",
                extra_fields=_error_response(f"Service {get_param_svc} is not available"),
            )

        # Check if parameter exists first
        exists, reason, value_response = _safe_check_parameter_exists(name, ws_manager)
        if not exists:
            return _error_response(reason or f"Parameter {name} does not exist")

        # If we got a response from the existence check, use it directly
        # Otherwise, make a new call (shouldn't happen, but safety check)
        if value_response is None:
            value_message = {
                "op": "call_service",
                "service": rosapi_service("get_param"),
                "type": rosapi_type("GetParam"),
                "args": {"name": name},
                "id": f"get_param_details_{name.replace('/', '_').replace(':', '_')}",
            }

            try:
                with ws_manager:
                    value_response = ws_manager.request(value_message)
            except Exception as e:
                return _error_response(f"Error getting parameter details: {str(e)}")

        # Handle string responses (fallback for malformed responses)
        if isinstance(value_response, str):
            return _error_response(f"Unexpected response format: {value_response}")

        if not value_response:
            return _error_response("No response from service")

        # Handle different response formats
        value_data = None
        param_value = ""
        param_successful = False
        reason = ""

        if "values" in value_response:
            value_data = value_response["values"]
            if isinstance(value_data, dict):
                param_value = value_data.get("value", "")
                param_successful = value_data.get("successful", False) or bool(param_value)
                reason = value_data.get("reason", "")
        elif "result" in value_response:
            result_data = value_response["result"]
            if isinstance(result_data, dict):
                value_data = result_data
                param_value = result_data.get("value", "")
                param_successful = result_data.get("successful", False) or bool(param_value)
                reason = result_data.get("reason", "")
            else:
                # Direct value
                param_value = str(result_data) if result_data is not None else ""
                param_successful = bool(param_value)

        # Parameter should exist at this point (we checked earlier), but handle edge cases
        if not param_successful and not param_value:
            return _error_response(reason or f"Parameter {name} does not exist")

        # Get parameter type
        type_message = {
            "op": "call_service",
            "service": rosapi_service("describe_parameters"),
            "type": "rcl_interfaces/DescribeParameters",
            "args": {"names": [name]},
            "id": f"describe_param_details_{name.replace('/', '_').replace(':', '_')}",
        }

        try:
            with ws_manager:
                type_response = ws_manager.request(type_message)
        except Exception:
            # If describe_parameters fails, continue with type inference from value
            type_response = None

        param_type = "unknown"
        param_description = ""

        # Handle string responses (fallback for malformed responses)
        if isinstance(type_response, str):
            # Continue with type inference from value
            pass
        elif type_response is None:
            # Service call failed, continue with type inference from value
            pass
        elif type_response and isinstance(type_response, dict):
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
