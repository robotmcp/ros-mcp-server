"""Service tools for ROS MCP."""

from fastmcp import FastMCP

from ros_mcp.utils.websocket import WebSocketManager


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

    @mcp.tool(
        description=(
            "Get complete service details including request/response structures and provider nodes.\n"
            "Example:\n"
            "get_service_details('/rosapi/topics')"
        )
    )
    def get_service_details(service: str) -> dict:
        """
        Get complete service details including request/response structures and provider nodes.

        Args:
            service (str): The service name (e.g., '/rosapi/topics')

        Returns:
            dict: Contains complete service definition with request and response structures,
                provider nodes, and provider count.
        """
        # Validate input
        if not service or not service.strip():
            return {"error": "Service name cannot be empty"}

        result = {
            "service": service,
            "type": "",
            "request": {},
            "response": {},
            "providers": [],
            "provider_count": 0,
        }

        with ws_manager:
            # First get the service type
            type_message = {
                "op": "call_service",
                "service": "/rosapi/service_type",
                "type": "rosapi_msgs/srv/ServiceType",
                "args": {"service": service},
                "id": f"get_service_type_{service.replace('/', '_')}",
            }

            type_response = ws_manager.request(type_message)
            if type_response and "values" in type_response:
                service_type = type_response["values"].get("type", "")
                if service_type:
                    result["type"] = service_type
                else:
                    return {"error": f"Service {service} does not exist or has no type"}
            else:
                return {"error": f"Failed to get type for service {service}"}

            # Get request details
            request_message = {
                "op": "call_service",
                "service": "/rosapi/service_request_details",
                "type": "rosapi_msgs/srv/ServiceRequestDetails",
                "args": {"type": result["type"]},
                "id": f"get_service_details_request_{result['type'].replace('/', '_')}",
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
                "args": {"type": result["type"]},
                "id": f"get_service_details_response_{result['type'].replace('/', '_')}",
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

            # Get service providers
            provider_message = {
                "op": "call_service",
                "service": "/rosapi/service_node",
                "type": "rosapi_msgs/srv/ServiceNode",
                "args": {"service": service},
                "id": f"get_service_providers_request_{service.replace('/', '_')}",
            }

            provider_response = ws_manager.request(provider_message)
            providers = []

            # Handle different response formats safely
            if provider_response and isinstance(provider_response, dict):
                if "values" in provider_response:
                    node = provider_response["values"].get("node", "")
                    if node:
                        providers = [node]
                elif "result" in provider_response:
                    node = provider_response["result"].get("node", "")
                    if node:
                        providers = [node]

            result["providers"] = providers
            result["provider_count"] = len(providers)

        # Check if we got any data
        if not result["request"] and not result["response"]:
            return {"error": f"Service {service} not found or has no definition"}

        # Add note about field name format
        result["note"] = (
            "Field names shown above are formatted for rosbridge (leading underscores removed). "
            "Use these exact field names when calling call_service()."
        )

        return result

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
        service_name: str, service_type: str, request: dict, timeout: float = None
    ) -> dict:
        """
        Call a ROS service with specified request data.

        Args:
            service_name (str): The service name (e.g., '/rosapi/topics')
            service_type (str): The service type (e.g., 'rosapi/Topics')
            request (dict): Service request data as a dictionary
            timeout (float): Timeout in seconds. If None, uses ws_manager.default_timeout.

        Returns:
            dict: Contains the service response or error information.
        """
        # Use ws_manager.default_timeout if timeout is None
        if timeout is None:
            timeout = ws_manager.default_timeout

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
