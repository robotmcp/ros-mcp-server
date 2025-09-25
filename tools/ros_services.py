# tools/ros_services.py
from typing import Optional

# Note: This module provides ROS service tools that will be imported by server.py
# The MCP instance and WebSocket manager are managed by server.py
# ws_manager will be passed as a parameter or imported when needed


def get_services(ws_manager) -> dict:
    """
    Get list of all available ROS services.

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


def get_service_type(service: str, ws_manager) -> dict:
    """
    Get the service type for a specific service.

    Args:
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


def get_service_details(service_type: str, ws_manager) -> dict:
    """
    Get complete service details including request and response structures.

    Args:
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


def get_service_providers(service: str, ws_manager) -> dict:
    """
    Get list of nodes that provide a specific service.

    Args:
        service (str): The service name (e.g., '/rosapi/topics')

    Returns:
        dict: Contains list of nodes providing this service,
            or an error message if service doesn't exist.
    """
    # Validate input
    if not service or not service.strip():
        return {"error": "Service name cannot be empty"}

    # rosbridge service call to get service providers
    message = {
        "op": "call_service",
        "service": "/rosapi/service_providers",
        "type": "rosapi/ServiceProviders",
        "args": {"service": service},
        "id": f"get_service_providers_request_{service.replace('/', '_')}",
    }

    # Request service providers from rosbridge
    with ws_manager:
        response = ws_manager.request(message)

    # Return service providers if present
    if response and "values" in response:
        providers = response["values"].get("providers", [])
        return {"service": service, "providers": providers, "provider_count": len(providers)}
    else:
        return {"error": f"Failed to get providers for service {service}"}


def inspect_all_services(ws_manager) -> dict:
    """
    Get comprehensive information about all services including types and providers.

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
            if type_response and "values" in type_response:
                service_type = type_response["values"].get("type", "unknown")
            elif type_response and "error" in type_response:
                service_errors.append(f"Service {service}: {type_response['error']}")

            # Get service providers
            providers_message = {
                "op": "call_service",
                "service": "/rosapi/service_providers",
                "type": "rosapi/ServiceProviders",
                "args": {"service": service},
                "id": f"get_providers_{service.replace('/', '_')}",
            }

            providers_response = ws_manager.request(providers_message)
            providers = []
            if providers_response and "values" in providers_response:
                providers = providers_response["values"].get("providers", [])
            elif providers_response and "error" in providers_response:
                service_errors.append(f"Service {service} providers: {providers_response['error']}")

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


def call_service(
    service_name: str, service_type: str, request: dict, ws_manager, timeout: Optional[float] = None
) -> dict:
    """
    Call a ROS service with specified request data.

    Args:
        service_name (str): The service name (e.g., '/rosapi/topics')
        service_type (str): The service type (e.g., 'rosapi/Topics')
        request (dict): Service request data as a dictionary
        timeout (Optional[float]): Timeout in seconds. If None, uses the default timeout.

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


def register_service_tools(mcp_instance, ws_manager):
    """Register all ROS service tools with the MCP instance."""

    @mcp_instance.tool(
        description="Get list of all available ROS services.\nExample:\nget_services()"
    )
    def get_services_tool() -> dict:
        return get_services(ws_manager)

    @mcp_instance.tool(
        description="Get the service type for a specific service.\nExample:\nget_service_type('/rosapi/topics')"
    )
    def get_service_type_tool(service: str) -> dict:
        return get_service_type(service, ws_manager)

    @mcp_instance.tool(
        description="Get complete service details including request and response structures.\nExample:\nget_service_details('my_package/CustomService')"
    )
    def get_service_details_tool(service_type: str) -> dict:
        return get_service_details(service_type, ws_manager)

    @mcp_instance.tool(
        description="Get list of nodes that provide a specific service.\nExample:\nget_service_providers('/rosapi/topics')"
    )
    def get_service_providers_tool(service: str) -> dict:
        return get_service_providers(service, ws_manager)

    @mcp_instance.tool(
        description="Get comprehensive information about all services including types and providers.\nExample:\ninspect_all_services()"
    )
    def inspect_all_services_tool() -> dict:
        return inspect_all_services(ws_manager)

    @mcp_instance.tool(
        description="Call a ROS service with specified request data.\nExample:\ncall_service('/rosapi/topics', 'rosapi/Topics', {})\ncall_service('/slow_service', 'my_package/SlowService', {}, timeout=10.0)  # Specify timeout only for slow services"
    )
    def call_service_tool(
        service_name: str, service_type: str, request: dict, timeout: Optional[float] = None
    ) -> dict:
        return call_service(service_name, service_type, request, ws_manager, timeout)
