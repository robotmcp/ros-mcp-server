"""Service tools for ROS MCP."""

from fastmcp import FastMCP

from ros_mcp.utils.websocket import WebSocketManager


def get_services_impl(ws_manager: WebSocketManager) -> dict:
    """
    Get list of all available ROS services.

    Args:
        ws_manager: WebSocketManager instance to use for ROS connections

    Returns:
        dict: Contains list of all active services,
            or a message string if no services are found.
    """
    # rosbridge service call to get service list
    message = {
        "op": "call_service",
        "service": "/rosapi/services",
        "type": "rosapi_msgs/srv/Services",
        "args": {},
        "id": "get_services_request_1",
    }

    # Request service list from rosbridge
    with ws_manager:
        response = ws_manager.request(message)

    # Check for service response errors first
    if response and "result" in response and not response["result"]:
        # Service call failed - return error with details from values
        error_msg = response.get("values", {}).get("message", "Service call failed")
        return {"error": f"Service call failed: {error_msg}"}

    # Return service info if present
    if response and "values" in response:
        services = response["values"].get("services", [])
        return {"services": services, "service_count": len(services)}
    else:
        return {"warning": "No services found"}


def get_service_type_impl(ws_manager: WebSocketManager, service: str) -> dict:
    """
    Get the service type for a specific service.

    Args:
        ws_manager: WebSocketManager instance to use for ROS connections
        service (str): The service name (e.g., '/rosapi/topics')

    Returns:
        dict: Contains the service type,
            or an error message if service doesn't exist.
    """
    # Validate input
    if not service or not service.strip():
        return {"error": "Service name cannot be empty"}

    # rosbridge service call to get service type
    message = {
        "op": "call_service",
        "service": "/rosapi/service_type",
        "type": "rosapi_msgs/srv/ServiceType",
        "args": {"service": service},
        "id": f"get_service_type_request_{service.replace('/', '_')}",
    }

    # Request service type from rosbridge
    with ws_manager:
        response = ws_manager.request(message)

    # Check for service response errors first
    if response and "result" in response and not response["result"]:
        # Service call failed - return error with details from values
        error_msg = response.get("values", {}).get("message", "Service call failed")
        return {"error": f"Service call failed: {error_msg}"}

    # Return service type if present
    if response and "values" in response:
        service_type = response["values"].get("type", "")
        if service_type:
            return {"service": service, "type": service_type}
        else:
            return {"error": f"Service {service} does not exist or has no type"}
    else:
        return {"error": f"Failed to get type for service {service}"}


def get_service_details_impl(ws_manager: WebSocketManager, service_type: str) -> dict:
    """
    Get complete service details including request and response structures.

    Args:
        ws_manager: WebSocketManager instance to use for ROS connections
        service_type (str): The service type (e.g., 'my_package/CustomService')

    Returns:
        dict: Contains complete service definition with request and response structures.
    """
    # Validate input
    if not service_type or not service_type.strip():
        return {"error": "Service type cannot be empty"}

    result = {"service_type": service_type, "request": {}, "response": {}}

    # Get both request and response details in a single WebSocket context
    with ws_manager:
        # Get request details
        request_message = {
            "op": "call_service",
            "service": "/rosapi/service_request_details",
            "type": "rosapi_msgs/srv/ServiceRequestDetails",
            "args": {"type": service_type},
            "id": f"get_service_details_request_{service_type.replace('/', '_')}",
        }

        request_response = ws_manager.request(request_message)
        if request_response and "values" in request_response:
            typedefs = request_response["values"].get("typedefs", [])
            if typedefs:
                for typedef in typedefs:
                    field_names = typedef.get("fieldnames", [])
                    field_types = typedef.get("fieldtypes", [])
                    fields = {}
                    for name, ftype in zip(field_names, field_types):
                        fields[name] = ftype
                    result["request"] = {"fields": fields, "field_count": len(fields)}

        # Get response details
        response_message = {
            "op": "call_service",
            "service": "/rosapi/service_response_details",
            "type": "rosapi_msgs/srv/ServiceResponseDetails",
            "args": {"type": service_type},
            "id": f"get_service_details_response_{service_type.replace('/', '_')}",
        }

        response_response = ws_manager.request(response_message)
        if response_response and "values" in response_response:
            typedefs = response_response["values"].get("typedefs", [])
            if typedefs:
                for typedef in typedefs:
                    field_names = typedef.get("fieldnames", [])
                    field_types = typedef.get("fieldtypes", [])
                    fields = {}
                    for name, ftype in zip(field_names, field_types):
                        fields[name] = ftype
                    result["response"] = {"fields": fields, "field_count": len(fields)}

    # Check if we got any data
    if not result["request"] and not result["response"]:
        return {"error": f"Service type {service_type} not found or has no definition"}

    # Add note about field name format
    result["note"] = (
        "Field names shown above are formatted for rosbridge (leading underscores removed). "
        "Use these exact field names when calling call_service()."
    )

    return result


def get_service_providers_impl(ws_manager: WebSocketManager, service: str) -> dict:
    """
    Get list of nodes that provide a specific service.

    Args:
        ws_manager: WebSocketManager instance to use for ROS connections
        service (str): The service name (e.g., '/rosapi/topics')

    Returns:
        dict: Contains list of nodes providing this service,
            or an error message if service doesn't exist.
    """
    # Validate input
    if not service or not service.strip():
        return {"error": "Service name cannot be empty"}

    # rosbridge service call to get service providers (using service_node like inspect_all_services)
    message = {
        "op": "call_service",
        "service": "/rosapi/service_node",
        "type": "rosapi_msgs/srv/ServiceNode",
        "args": {"service": service},
        "id": f"get_service_providers_request_{service.replace('/', '_')}",
    }

    # Request service providers from rosbridge
    with ws_manager:
        response = ws_manager.request(message)

    # Return service providers if present (using same logic as inspect_all_services)
    providers = []

    # Handle different response formats safely
    if response and isinstance(response, dict):
        if "values" in response:
            node = response["values"].get("node", "")
            if node:
                providers = [node]
        elif "result" in response:
            node = response["result"].get("node", "")
            if node:
                providers = [node]
        elif "error" in response:
            return {"error": f"Service call failed: {response['error']}"}
    elif response is False:
        return {"error": f"No response received for service {service}"}
    elif response is True:
        return {"error": f"Unexpected boolean response for service {service}"}
    else:
        return {"error": f"Failed to get providers for service {service}"}

    return {"service": service, "providers": providers, "provider_count": len(providers)}


def call_service_impl(
    ws_manager: WebSocketManager,
    service_name: str,
    service_type: str,
    request: dict,
    timeout: float | None = None,
) -> dict:
    """
    Call a ROS service with specified request data.

    Args:
        ws_manager: WebSocketManager instance to use for ROS connections
        service_name (str): The service name (e.g., '/rosapi/topics')
        service_type (str): The service type (e.g., 'rosapi/Topics')
        request (dict): Service request data as a dictionary
        timeout (float | None): Timeout in seconds. If None, uses the default timeout.

    Returns:
        dict: Contains the service response or error information.
    """
    # rosbridge service call
    message = {
        "op": "call_service",
        "service": service_name,
        "type": service_type,
        "args": request,
        "id": f"call_service_request_{service_name.replace('/', '_')}",
    }

    # Call the service through rosbridge
    with ws_manager:
        response = ws_manager.request(message, timeout=timeout)

    # Check for service response errors first
    if response and "result" in response and not response["result"]:
        # Service call failed - return error with details from values
        error_msg = response.get("values", {}).get("message", "Service call failed")
        return {
            "service": service_name,
            "service_type": service_type,
            "success": False,
            "error": f"Service call failed: {error_msg}",
        }

    # Return service response if present
    if response:
        if response.get("op") == "service_response":
            # Alternative response format
            return {
                "service": service_name,
                "service_type": service_type,
                "success": response.get("result", True),
                "result": response.get("values", {}),
            }
        elif response.get("op") == "status" and response.get("level") == "error":
            # Error response
            return {
                "service": service_name,
                "service_type": service_type,
                "success": False,
                "error": response.get("msg", "Unknown error"),
            }
        else:
            # Unexpected response format
            return {
                "service": service_name,
                "service_type": service_type,
                "success": False,
                "error": "Unexpected response format",
                "raw_response": response,
            }
    else:
        return {
            "service": service_name,
            "service_type": service_type,
            "success": False,
            "error": "No response received from service call",
        }


def register_service_tools(
    mcp: FastMCP,
    ws_manager: WebSocketManager,
) -> None:
    """Register all service-related tools."""

    @mcp.tool(description=("Get list of all available ROS services.\nExample:\nget_services()"))
    def get_services() -> dict:
        """Get list of all available ROS services."""
        return get_services_impl(ws_manager)

    @mcp.tool(
        description=(
            "Get the service type for a specific service.\nExample:\nget_service_type('/rosapi/topics')"
        )
    )
    def get_service_type(service: str) -> dict:
        """Get the service type for a specific service."""
        return get_service_type_impl(ws_manager, service)

    @mcp.tool(
        description=(
            "Get complete service details including request and response structures.\n"
            "Example:\n"
            "get_service_details('my_package/CustomService')"
        )
    )
    def get_service_details(service_type: str) -> dict:
        """Get complete service details including request and response structures."""
        return get_service_details_impl(ws_manager, service_type)

    @mcp.tool(
        description=(
            "Get list of nodes that provide a specific service.\n"
            "Example:\n"
            "get_service_providers('/rosapi/topics')"
        )
    )
    def get_service_providers(service: str) -> dict:
        """Get list of nodes that provide a specific service."""
        return get_service_providers_impl(ws_manager, service)

    @mcp.tool(
        description=(
            "Call a ROS service with specified request data.\n"
            "Example:\n"
            "call_service('/rosapi/topics', 'rosapi/Topics', {})\n"
            "call_service('/slow_service', 'my_package/SlowService', {}, timeout=10.0)  # Specify timeout only for slow services\n"
            "\n"
            "IMPORTANT: Field names in the request dict should match the field names shown by get_service_details(), "
            "which are already formatted for rosbridge (without leading underscores). "
            "For example, use {'topic': '/image'} not {'_topic': '/image'}."
        )
    )
    def call_service(
        service_name: str, service_type: str, request: dict, timeout: float | None = None
    ) -> dict:
        """Call a ROS service with specified request data."""
        return call_service_impl(ws_manager, service_name, service_type, request, timeout)
