"""Parameter tools for ROS MCP."""

from fastmcp import FastMCP

from ros_mcp.utils.websocket import WebSocketManager


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
        if not name or not name.strip():
            return {"error": "Parameter name cannot be empty"}

        message = {
            "op": "call_service",
            "service": "/rosapi/get_param",
            "type": "rosapi_msgs/srv/GetParam",
            "args": {"name": name},
            "id": f"get_param_{name.replace('/', '_').replace(':', '_')}",
        }

        with ws_manager:
            response = ws_manager.request(message)

        if response and "values" in response:
            result_data = response["values"]
            value = result_data.get("value", "")
            # If we have a value, consider it successful even if successful field says false
            successful = result_data.get("successful", False) or bool(value)
            return {
                "name": name,
                "value": value,
                "successful": successful,
                "reason": result_data.get("reason", ""),
            }
        elif response and "result" in response:
            result_data = response["result"]
            # Handle both dict and direct value cases
            if isinstance(result_data, dict):
                value = result_data.get("value", "")
                successful = result_data.get("successful", False) or bool(value)
                return {
                    "name": name,
                    "value": value,
                    "successful": successful,
                    "reason": result_data.get("reason", ""),
                }
            else:
                # Direct value in result
                return {
                    "name": name,
                    "value": str(result_data) if result_data is not None else "",
                    "successful": True,
                    "reason": "",
                }
        else:
            error_msg = (
                response.get("values", {}).get("message", "Service call failed")
                if response
                else "No response"
            )
            return {"error": f"Failed to get parameter {name}: {error_msg}"}

    @mcp.tool(
        description=(
            "Set a single ROS parameter value. Works only with ROS 2.\n"
            "Example:\nset_parameter('/turtlesim:background_b', '255')"
        )
    )
    def set_parameter(name: str, value: str) -> dict:
        """Set a single ROS parameter value. Works only with ROS 2."""
        if not name or not name.strip():
            return {"error": "Parameter name cannot be empty"}

        message = {
            "op": "call_service",
            "service": "/rosapi/set_param",
            "type": "rosapi_msgs/srv/SetParam",
            "args": {"name": name, "value": value},
            "id": f"set_param_{name.replace('/', '_').replace(':', '_')}",
        }

        with ws_manager:
            response = ws_manager.request(message)

        if response and "values" in response:
            result_data = response["values"]
            # If we have a response, consider it successful even if successful field says false
            successful = result_data.get("successful", False) or True
            return {
                "name": name,
                "value": value,
                "successful": successful,
                "reason": result_data.get("reason", ""),
            }
        elif response and "result" in response:
            result_data = response["result"]
            if isinstance(result_data, dict):
                successful = result_data.get("successful", False) or True
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
        else:
            error_msg = (
                response.get("values", {}).get("message", "Service call failed")
                if response
                else "No response"
            )
            return {"error": f"Failed to set parameter {name}: {error_msg}"}

    @mcp.tool(
        description=(
            "Check if a ROS parameter exists. Works only with ROS 2.\n"
            "Example:\nhas_parameter('/turtlesim:background_b')"
        )
    )
    def has_parameter(name: str) -> dict:
        """Check if a ROS parameter exists. Works only with ROS 2."""
        if not name or not name.strip():
            return {"error": "Parameter name cannot be empty"}

        message = {
            "op": "call_service",
            "service": "/rosapi/has_param",
            "type": "rosapi_msgs/srv/HasParam",
            "args": {"name": name},
            "id": f"has_param_{name.replace('/', '_').replace(':', '_')}",
        }

        with ws_manager:
            response = ws_manager.request(message)

        if response and "values" in response:
            result_data = response["values"]
            exists = result_data.get("exists", False)
            # If we got a response with exists field, consider it successful
            successful = result_data.get("successful", False) or True
            return {
                "name": name,
                "exists": exists,
                "successful": successful,
                "reason": result_data.get("reason", ""),
            }
        elif response and "result" in response:
            result_data = response["result"]
            if isinstance(result_data, dict):
                exists = result_data.get("exists", False)
                successful = result_data.get("successful", False) or True
                return {
                    "name": name,
                    "exists": exists,
                    "successful": successful,
                    "reason": result_data.get("reason", ""),
                }
            else:
                # Direct boolean result
                return {
                    "name": name,
                    "exists": bool(result_data) if result_data is not None else False,
                    "successful": True,
                    "reason": "",
                }
        else:
            error_msg = (
                response.get("values", {}).get("message", "Service call failed")
                if response
                else "No response"
            )
            return {"error": f"Failed to check parameter {name}: {error_msg}"}

    @mcp.tool(
        description=(
            "Delete a ROS parameter. Works only with ROS 2.\n"
            "Example:\ndelete_parameter('/turtlesim:background_b')"
        )
    )
    def delete_parameter(name: str) -> dict:
        """Delete a ROS parameter. Works only with ROS 2."""
        if not name or not name.strip():
            return {"error": "Parameter name cannot be empty"}

        message = {
            "op": "call_service",
            "service": "/rosapi/delete_param",
            "type": "rosapi_msgs/srv/DeleteParam",
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

    @mcp.tool(
        description=(
            "Get list of all ROS parameter names for a specific node. Works only with ROS 2.\n"
            "Example:\nget_parameters('cam2image')\nget_parameters('/cam2image')"
        )
    )
    def get_parameters(node_name: str) -> dict:
        """Get list of all ROS parameter names for a specific node. Works only with ROS 2."""
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

        message = {
            "op": "call_service",
            "service": service_name,
            "type": "rcl_interfaces/srv/ListParameters",
            "args": {},
            "id": f"get_parameters_{normalized_node.replace('/', '_')}",
        }

        with ws_manager:
            response = ws_manager.request(message)

        # Check for timeout or connection errors
        if not response:
            return {"error": f"Failed to get parameters for node {normalized_node}: No response or timeout from rosbridge"}

        # Check for explicit error in response
        if isinstance(response, dict) and "error" in response:
            error_msg = response.get("error", "Service call failed")
            return {"error": f"Failed to get parameters for node {normalized_node}: {error_msg}"}

        # Check for service response errors first
        if response and "result" in response and not response["result"]:
            # Service call failed - return error with details from values
            error_msg = response.get("values", {}).get("message", "Service call failed")
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

    # Commented out: inspect_all_parameters depends on get_parameters which doesn't always work reliably
    # @mcp.tool(
    #     description=(
    #         "Get comprehensive information about all ROS parameters including values and metadata. "
    #         "Works only with ROS 2.\n"
    #         "Example:\n"
    #         "inspect_all_parameters()"
    #     )
    # )
    # def inspect_all_parameters() -> dict:
    #     """Get comprehensive information about all ROS parameters including values and metadata. Works only with ROS 2."""
    #     # First get all parameters
    #     parameters_message = {
    #         "op": "call_service",
    #         "service": "/rosapi/get_param_names",
    #         "type": "rosapi_msgs/srv/GetParamNames",
    #         "args": {},
    #         "id": "inspect_all_parameters_request_1",
    #     }
    #
    #     with ws_manager:
    #         parameters_response = ws_manager.request(parameters_message)
    #
    #         if not parameters_response or "values" not in parameters_response:
    #             return {"error": "Failed to get parameters list"}
    #
    #         parameters = parameters_response["values"].get("names", [])
    #         parameter_details = {}
    #
    #         # Get details for each parameter
    #         parameter_errors = []
    #         for param_name in parameters:
    #             # Get parameter value
    #             value_message = {
    #                 "op": "call_service",
    #                 "service": "/rosapi/get_param",
    #                 "type": "rosapi_msgs/srv/GetParam",
    #                 "args": {"name": param_name},
    #                 "id": f"get_param_{param_name.replace('/', '_').replace(':', '_')}",
    #             }
    #
    #             value_response = ws_manager.request(value_message)
    #             param_value = ""
    #             param_successful = False
    #             if value_response and "values" in value_response:
    #                 value_data = value_response["values"]
    #                 param_value = value_data.get("value", "")
    #                 param_successful = value_data.get("successful", False)
    #             elif value_response and "result" in value_response and value_response["result"]:
    #                 value_data = value_response["result"]
    #                 param_value = value_data.get("value", "")
    #                 param_successful = value_data.get("successful", False)
    #             elif value_response and "error" in value_response:
    #                 parameter_errors.append(f"Parameter {param_name}: {value_response['error']}")
    #
    #             # Get parameter type (using describe_parameters service)
    #             type_message = {
    #                 "op": "call_service",
    #                 "service": "/rosapi/describe_parameters",
    #                 "type": "rcl_interfaces/DescribeParameters",
    #                 "args": {"names": [param_name]},
    #                 "id": f"describe_param_{param_name.replace('/', '_').replace(':', '_')}",
    #             }
    #
    #             type_response = ws_manager.request(type_message)
    #             param_type = "unknown"
    #
    #             # Handle different response formats for parameter type detection
    #             if type_response and isinstance(type_response, dict):
    #                 if "values" in type_response:
    #                     result_data = type_response["values"]
    #                     if isinstance(result_data, dict):
    #                         descriptors = result_data.get("descriptors", [])
    #                         if descriptors and len(descriptors) > 0:
    #                             param_type = descriptors[0].get("type", "unknown")
    #                 elif "result" in type_response and type_response["result"]:
    #                     result_data = type_response["result"]
    #                     if isinstance(result_data, dict):
    #                         descriptors = result_data.get("descriptors", [])
    #                         if descriptors and len(descriptors) > 0:
    #                             param_type = descriptors[0].get("type", "unknown")
    #                 elif "error" in type_response:
    #                     parameter_errors.append(
    #                         f"Parameter {param_name} type: {type_response['error']}"
    #                     )
    #
    #             # Fallback: Try to infer type from value
    #             if param_type == "unknown" and param_value:
    #                 try:
    #                     # Remove quotes for type checking
    #                     clean_value = param_value.strip('"')
    #
    #                     # Try to parse as different types
    #                     if clean_value.lower() in ["true", "false"]:
    #                         param_type = "bool"
    #                     elif clean_value.isdigit() or (
    #                         clean_value.startswith("-") and clean_value[1:].isdigit()
    #                     ):
    #                         param_type = "int"
    #                     elif (
    #                         "." in clean_value
    #                         and clean_value.replace(".", "").replace("-", "").isdigit()
    #                     ):
    #                         param_type = "float"
    #                     elif param_value.startswith('"') and param_value.endswith('"'):
    #                         param_type = "string"
    #                     elif clean_value == "":
    #                         param_type = "string"
    #                     else:
    #                         param_type = "string"
    #                 except Exception:
    #                     param_type = "string"
    #
    #             parameter_details[param_name] = {
    #                 "value": param_value,
    #                 "type": param_type,
    #                 "exists": param_successful,
    #             }
    #
    #         return {
    #             "total_parameters": len(parameters),
    #             "parameters": parameter_details,
    #             "parameter_errors": parameter_errors,  # Include any errors encountered during inspection
    #         }

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
        # Validate input
        if not name or not name.strip():
            return {"error": "Parameter name cannot be empty"}

        # Get parameter value
        value_message = {
            "op": "call_service",
            "service": "/rosapi/get_param",
            "type": "rosapi_msgs/srv/GetParam",
            "args": {"name": name},
            "id": f"get_param_details_{name.replace('/', '_').replace(':', '_')}",
        }

        with ws_manager:
            value_response = ws_manager.request(value_message)

        if not value_response:
            return {"error": f"Failed to get parameter {name}: No response"}

        # Handle different response formats
        value_data = None
        param_value = ""
        param_successful = False

        if "values" in value_response:
            value_data = value_response["values"]
            param_value = value_data.get("value", "")
            # If we have a value, consider it successful
            param_successful = value_data.get("successful", False) or bool(param_value)
        elif "result" in value_response:
            result_data = value_response["result"]
            if isinstance(result_data, dict):
                value_data = result_data
                param_value = result_data.get("value", "")
                param_successful = result_data.get("successful", False) or bool(param_value)
            else:
                # Direct value
                param_value = str(result_data) if result_data is not None else ""
                param_successful = bool(param_value)
        else:
            return {"error": f"Failed to get parameter {name}: Unexpected response format"}

        if not param_successful and not param_value:
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
