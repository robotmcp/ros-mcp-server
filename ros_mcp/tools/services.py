"""Service tools for ROS MCP."""

from fastmcp import FastMCP

from ros_mcp.utils.websocket_manager import WebSocketManager


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
        "type": "rosapi/Services",
        "args": {},
        "id": "get_services_request_1",
    }

    # Request service list from rosbridge
    with ws_manager:
        response = ws_manager.request(message)

    # Ensure response is a dict
    if not isinstance(response, dict):
        return {"error": f"Unexpected response type: {type(response).__name__}"}

    # Check for websocket manager errors (connection/send/receive failures)
    if "error" in response:
        return {"error": response["error"]}

    # Check for rosbridge status error messages (timeouts, etc.)
    if response.get("op") == "status" and response.get("level") == "error":
        return {"error": response.get("msg", "Unknown rosbridge error")}

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
        "type": "rosapi/ServiceType",
        "args": {"service": service},
        "id": f"get_service_type_request_{service.replace('/', '_')}",
    }

    # Request service type from rosbridge
    with ws_manager:
        response = ws_manager.request(message)

    # Check for websocket manager errors (connection/send/receive failures)
    if not isinstance(response, dict) or "error" in response:
        error_msg = (
            response.get("error", "Unknown error")
            if isinstance(response, dict)
            else "Invalid response"
        )
        return {"error": f"Failed to get service type: {error_msg}"}

    # Check for rosbridge status error messages (timeouts, etc.)
    if response.get("op") == "status" and response.get("level") == "error":
        return {"error": response.get("msg", "Unknown rosbridge error")}

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
            "type": "rosapi/ServiceRequestDetails",
            "args": {"type": service_type},
            "id": f"get_service_details_request_{service_type.replace('/', '_')}",
        }

        request_response = ws_manager.request(request_message)
        # Check for errors
        if isinstance(request_response, dict):
            if "error" in request_response:
                return {"error": f"Failed to get request details: {request_response['error']}"}
            if request_response.get("op") == "status" and request_response.get("level") == "error":
                return {"error": f"Rosbridge error: {request_response.get('msg', 'Unknown error')}"}
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
            "type": "rosapi/ServiceResponseDetails",
            "args": {"type": service_type},
            "id": f"get_service_details_response_{service_type.replace('/', '_')}",
        }

        response_response = ws_manager.request(response_message)
        # Check for errors
        if isinstance(response_response, dict):
            if "error" in response_response:
                return {"error": f"Failed to get response details: {response_response['error']}"}
            if (
                response_response.get("op") == "status"
                and response_response.get("level") == "error"
            ):
                return {
                    "error": f"Rosbridge error: {response_response.get('msg', 'Unknown error')}"
                }
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
        "type": "rosapi/ServiceNode",
        "args": {"service": service},
        "id": f"get_service_providers_request_{service.replace('/', '_')}",
    }

    # Request service providers from rosbridge
    with ws_manager:
        response = ws_manager.request(message)

    # Check for websocket manager errors (connection/send/receive failures)
    if not isinstance(response, dict):
        return {"error": f"Invalid response type for service {service}"}

    if "error" in response:
        return {"error": f"Service call failed: {response['error']}"}

    # Check for rosbridge status error messages (timeouts, etc.)
    if response.get("op") == "status" and response.get("level") == "error":
        return {"error": response.get("msg", "Unknown rosbridge error")}

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
    elif response is False:
        return {"error": f"No response received for service {service}"}
    elif response is True:
        return {"error": f"Unexpected boolean response for service {service}"}
    else:
        return {"error": f"Failed to get providers for service {service}"}

    return {"service": service, "providers": providers, "provider_count": len(providers)}


def inspect_all_services_impl(ws_manager: WebSocketManager) -> dict:
    """
    Get comprehensive information about all services including types and providers.

    Args:
        ws_manager: WebSocketManager instance to use for ROS connections

    Returns:
        dict: Contains detailed information about all services,
            including service names, types, and provider nodes.
    """
    # First get all services
    services_message = {
        "op": "call_service",
        "service": "/rosapi/services",
        "type": "rosapi/Services",
        "args": {},
        "id": "inspect_all_services_request_1",
    }

    with ws_manager:
        services_response = ws_manager.request(services_message)

        # Check for errors
        if not isinstance(services_response, dict):
            return {"error": "Failed to get services list: invalid response"}
        if "error" in services_response:
            return {"error": f"Failed to get services list: {services_response['error']}"}
        if services_response.get("op") == "status" and services_response.get("level") == "error":
            return {"error": f"Rosbridge error: {services_response.get('msg', 'Unknown error')}"}
        if not services_response or "values" not in services_response:
            return {"error": "Failed to get services list"}

        services = services_response["values"].get("services", [])
        service_details = {}

        # Get details for each service
        service_errors = []
        for service in services:
            # Get service type
            type_message = {
                "op": "call_service",
                "service": "/rosapi/service_type",
                "type": "rosapi/ServiceType",
                "args": {"service": service},
                "id": f"get_type_{service.replace('/', '_')}",
            }

            type_response = ws_manager.request(type_message)
            service_type = ""
            if isinstance(type_response, dict):
                if type_response.get("op") == "status" and type_response.get("level") == "error":
                    service_errors.append(
                        f"Service {service}: {type_response.get('msg', 'Unknown error')}"
                    )
                elif "values" in type_response:
                    service_type = type_response["values"].get("type", "unknown")
                elif "error" in type_response:
                    service_errors.append(f"Service {service}: {type_response['error']}")

            # Get service provider (using service_node instead of service_providers)
            provider_message = {
                "op": "call_service",
                "service": "/rosapi/service_node",
                "type": "rosapi/ServiceNode",
                "args": {"service": service},
                "id": f"get_provider_{service.replace('/', '_')}",
            }

            provider_response = ws_manager.request(provider_message)
            providers = []

            # Handle different response formats safely
            if isinstance(provider_response, dict):
                if (
                    provider_response.get("op") == "status"
                    and provider_response.get("level") == "error"
                ):
                    service_errors.append(
                        f"Service {service} provider: {provider_response.get('msg', 'Unknown error')}"
                    )
                elif "values" in provider_response:
                    node = provider_response["values"].get("node", "")
                    if node:
                        providers = [node]
                elif "result" in provider_response:
                    node = provider_response["result"].get("node", "")
                    if node:
                        providers = [node]
                elif "error" in provider_response:
                    service_errors.append(
                        f"Service {service} provider: {provider_response['error']}"
                    )
            elif provider_response is False:
                service_errors.append(f"Service {service} provider: No response received")
            elif provider_response is True:
                service_errors.append(f"Service {service} provider: Unexpected boolean response")

            service_details[service] = {
                "type": service_type,
                "providers": providers,
                "provider_count": len(providers),
            }

        return {
            "total_services": len(services),
            "services": service_details,
            "service_errors": service_errors,  # Include any errors encountered during inspection
        }


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

    # Check for websocket manager errors (connection/send/receive failures)
    if not isinstance(response, dict):
        return {
            "service": service_name,
            "service_type": service_type,
            "success": False,
            "error": f"Invalid response type: {type(response).__name__}",
        }

    if "error" in response:
        return {
            "service": service_name,
            "service_type": service_type,
            "success": False,
            "error": response["error"],
        }

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
        """
        Get list of all available ROS services.

        Returns:
            dict: Contains list of all active services,
                or a message string if no services are found.
        """
        return get_services_impl(ws_manager)

    @mcp.tool(
        description=(
            "Get the service type for a specific service.\nExample:\nget_service_type('/rosapi/topics')"
        )
    )
    def get_service_type(service: str) -> dict:
        """
        Get the service type for a specific service.

        Args:
            service (str): The service name (e.g., '/rosapi/topics')

        Returns:
            dict: Contains the service type,
                or an error message if service doesn't exist.
        """
        return get_service_type_impl(ws_manager, service)

    @mcp.tool(
        description=(
            "Get complete service details including request and response structures.\n"
            "Example:\n"
            "get_service_details('my_package/CustomService')"
        )
    )
    def get_service_details(service_type: str) -> dict:
        """
        Get complete service details including request and response structures.

        Args:
            service_type (str): The service type (e.g., 'my_package/CustomService')

        Returns:
            dict: Contains complete service definition with request and response structures.
        """
        return get_service_details_impl(ws_manager, service_type)

    @mcp.tool(
        description=(
            "Get list of nodes that provide a specific service.\n"
            "Example:\n"
            "get_service_providers('/rosapi/topics')"
        )
    )
    def get_service_providers(service: str) -> dict:
        """
        Get list of nodes that provide a specific service.

        Args:
            service (str): The service name (e.g., '/rosapi/topics')

        Returns:
            dict: Contains list of nodes providing this service,
                or an error message if service doesn't exist.
        """
        return get_service_providers_impl(ws_manager, service)

    @mcp.tool(
        description=(
            "Get comprehensive information about all services including types and providers. Note that this may take time to execute when three are a large number of services since it queries each one by one under the hood. \n"
            "Example:\n"
            "inspect_all_services()"
        )
    )
    def inspect_all_services() -> dict:
        """
        Get comprehensive information about all services including types and providers.

        Returns:
            dict: Contains detailed information about all services,
                including service names, types, and provider nodes.
        """
        return inspect_all_services_impl(ws_manager)

    @mcp.tool(
        description=(
            "Call a ROS service with specified request data.\n"
            "Example:\n"
            "call_service('/rosapi/topics', 'rosapi/Topics', {})\n"
            "call_service('/slow_service', 'my_package/SlowService', {}, timeout=10.0)  # Specify timeout only for slow services"
        )
    )
    def call_service(
        service_name: str, service_type: str, request: dict, timeout: float | None = None
    ) -> dict:
        """
        Call a ROS service with specified request data.

        Args:
            service_name (str): The service name (e.g., '/rosapi/topics')
            service_type (str): The service type (e.g., 'rosapi/Topics')
            request (dict): Service request data as a dictionary
            timeout (float | None): Timeout in seconds. If None, uses the default timeout.

        Returns:
            dict: Contains the service response or error information.
        """
        return call_service_impl(ws_manager, service_name, service_type, request, timeout)
