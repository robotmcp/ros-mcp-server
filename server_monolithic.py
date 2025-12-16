import argparse
import asyncio
import io
import json
import os
import sys
import time
import uuid
from typing import Union

from fastmcp import Context, FastMCP
from fastmcp.utilities.types import Image
from PIL import Image as PILImage

from resources import register_all_resources
from utils.config_utils import get_verified_robot_spec_util, get_verified_robots_list_util
from utils.network_utils import ping_ip_and_port
from utils.websocket_manager import WebSocketManager

# ROS bridge connection settings
ROSBRIDGE_IP = "127.0.0.1"  # Default is localhost. Replace with your local IPor set using the LLM.
ROSBRIDGE_PORT = (
    9090  # Rosbridge default is 9090. Replace with your rosbridge port or set using the LLM.
)

# MCP transport settings
MCP_TRANSPORT = os.getenv("MCP_TRANSPORT", "stdio").lower()  # Default is stdio.

# MCP connection settings (streamable-http)
MCP_HOST = os.getenv(
    "MCP_HOST", "127.0.0.1"
)  # Default is localhost. Replace with the address of your remote MCP server.

# MCP port settings (default=9000)
MCP_PORT = int(
    os.getenv("MCP_PORT", "9000")
)  # Default is 9000. Replace with the port of your remote MCP server.

# Initialize MCP server and WebSocket manager
mcp = FastMCP("ros-mcp-server")
ws_manager = WebSocketManager(
    ROSBRIDGE_IP, ROSBRIDGE_PORT, default_timeout=5.0
)  # Increased default timeout for ROS operations


register_all_resources(mcp, ws_manager)


@mcp.tool(
    description=(
        "Load specifications and usage context for a verified robot model. "
        "ONLY use if the robot model is in the verified list (use get_verified_robots_list first to check). "
        "Most robots won't have a spec - that's OK, connect directly using connect_to_robot instead."
    )
)
def get_verified_robot_spec(name: str) -> dict:
    """
    Load pre-defined specifications and additional context for a verified robot model.

    This is OPTIONAL - only for a small set of pre-verified robot models stored in the repository.
    Use get_verified_robots_list() first to check if a spec exists.
    If no spec exists for your robot, simply use connect_to_robot() directly.

    Args:
        name (str): The exact robot model name from the verified list.

    Returns:
        dict: The robot specification with type, prompts, and additional context.
    """
    robot_config = get_verified_robot_spec_util(name)

    if len(robot_config) > 1:
        return {
            "error": f"Multiple configurations found for robot '{name}'. Please specify a more precise name."
        }
    elif not robot_config:
        return {
            "error": f"No configuration found for robot '{name}'. Please check the name and try again. Or you can set the IP/port manually using the 'connect_to_robot' tool."
        }
    return {"robot_config": robot_config}


@mcp.tool(
    description=(
        "List pre-verified robot models that have specification files with usage guidance available. "
        "Use this to check if a robot model has additional context available before calling get_verified_robot_spec. "
        "If your robot is not in this list, you can still connect to it directly using connect_to_robot."
    )
)
def get_verified_robots_list() -> dict:
    """
    List all pre-verified robot models that have specification files available in the repository.

    This is a small curated list of robot models with pre-defined specifications.
    If your robot model is not in this list, you can still connect to any ROS robot
    using the connect_to_robot() tool directly.

    Returns:
        dict: List of available verified robot model names and count.
    """
    return get_verified_robots_list_util()


@mcp.tool(
    description=(
        "Connect to the robot by setting the IP/port. This tool also tests connectivity to confirm that the robot is reachable and the port is open."
    )
)
def connect_to_robot(
    ip: str = ROSBRIDGE_IP,
    port: Union[int, str] = ROSBRIDGE_PORT,
    ping_timeout: float = 2.0,
    port_timeout: float = 2.0,
) -> dict:
    """
    Connect to a robot by setting the IP and port for the WebSocket connection, then testing connectivity.

    Args:
        ip (str): The IP address of the rosbridge server. Defaults to "127.0.0.1" (localhost).
        port (int): The port number of the rosbridge server. Defaults to 9090.
        ping_timeout (float): Timeout for ping in seconds. Default = 2.0.
        port_timeout (float): Timeout for port check in seconds. Default = 2.0.

    Returns:
        dict: Connection status with ping and port check results.
    """
    # Set default values if None
    actual_ip = str(ip).strip() if ip else ROSBRIDGE_IP
    actual_port = int(port) if port else ROSBRIDGE_PORT

    # Set the IP and port
    ws_manager.set_ip(actual_ip, actual_port)

    # Test connectivity
    ping_result = ping_ip_and_port(actual_ip, actual_port, ping_timeout, port_timeout)

    # Combine the results
    return {
        "message": f"WebSocket IP set to {actual_ip}:{actual_port}",
        "connectivity_test": ping_result,
    }


## ############################################################################################## ##
##
##                       ROS SERVICES
##
## ############################################################################################## ##


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
            if provider_response and isinstance(provider_response, dict):
                if "values" in provider_response:
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


## ############################################################################################## ##
##
##                       ROS ACTIONS
##
## ############################################################################################## ##


@mcp.tool(
    description=(
        "Get list of all available ROS actions. Works only with ROS 2.\nExample:\nget_actions()"
    )
)
def get_actions() -> dict:
    """
    Get list of all available ROS actions. Works only with ROS 2.

    Returns:
        dict: Contains list of all active actions,
            or a message string if no actions are found.
    """
    # Check if required service is available
    required_services = ["/rosapi/action_servers"]

    with ws_manager:
        # Get available services to check compatibility
        services_message = {
            "op": "call_service",
            "service": "/rosapi/services",
            "type": "rosapi/Services",
            "args": {},
            "id": "check_services_for_get_actions",
        }

        services_response = ws_manager.request(services_message)
        if not services_response or not isinstance(services_response, dict):
            return {
                "warning": "Cannot check service availability",
                "compatibility": {
                    "issue": "Cannot determine available services",
                    "required_services": required_services,
                    "suggestion": "Ensure rosbridge is running and rosapi is available",
                },
            }

        available_services = services_response.get("values", {}).get("services", [])
        missing_services = [svc for svc in required_services if svc not in available_services]

        if missing_services:
            return {
                "warning": "Action listing not supported by this rosbridge/rosapi version",
                "compatibility": {
                    "issue": "Required action services are not available",
                    "missing_services": missing_services,
                    "required_services": required_services,
                    "available_services": [s for s in available_services if "action" in s],
                    "suggestion": "This rosbridge version doesn't support action listing services",
                },
            }

    # rosbridge service call to get action list
    message = {
        "op": "call_service",
        "service": "/rosapi/action_servers",
        "type": "rosapi/ActionServers",
        "args": {},
        "id": "get_actions_request_1",
    }

    # Request action list from rosbridge
    with ws_manager:
        response = ws_manager.request(message)

    # Handle error responses from ws_manager
    if response and "error" in response:
        return {"error": f"WebSocket error: {response['error']}"}

    # Check for service response errors first
    if response and "result" in response and not response["result"]:
        # Service call failed - return error with details from values
        if "values" in response and isinstance(response["values"], dict):
            error_msg = response["values"].get("message", "Service call failed")
        else:
            error_msg = "Service call failed"
        return {"error": f"Service call failed: {error_msg}"}

    # Return action info if present
    if response and "values" in response:
        actions = response["values"].get("action_servers", [])
        return {"actions": actions, "action_count": len(actions)}
    else:
        return {"warning": "No actions found or /rosapi/action_servers service not available"}


@mcp.tool(
    description=(
        "Get the action type for a specific action. Works only with ROS 2.\nExample:\nget_action_type('/turtle1/rotate_absolute')"
    )
)
def get_action_type(action: str) -> dict:
    """
    Get the action type for a specific action. Works only with ROS 2.

    Args:
        action (str): The action name (e.g., '/turtle1/rotate_absolute')

    Returns:
        dict: Contains the action type,
            or an error message if action doesn't exist.
    """
    # Validate input
    if not action or not action.strip():
        return {"error": "Action name cannot be empty"}

    # Check if required service is available
    required_services = ["/rosapi/interfaces"]

    with ws_manager:
        # Get available services to check compatibility
        services_message = {
            "op": "call_service",
            "service": "/rosapi/services",
            "type": "rosapi/Services",
            "args": {},
            "id": "check_services_for_get_action_type",
        }

        services_response = ws_manager.request(services_message)
        if not services_response or not isinstance(services_response, dict):
            return {
                "warning": "Cannot check service availability",
                "action": action,
                "compatibility": {
                    "issue": "Cannot determine available services",
                    "required_services": required_services,
                    "suggestion": "Ensure rosbridge is running and rosapi is available",
                },
            }

        available_services = services_response.get("values", {}).get("services", [])
        missing_services = [svc for svc in required_services if svc not in available_services]

        if missing_services:
            return {
                "warning": "Action type resolution not supported by this rosbridge/rosapi version",
                "action": action,
                "compatibility": {
                    "issue": "Required services are not available",
                    "missing_services": missing_services,
                    "required_services": required_services,
                    "available_services": [s for s in available_services if "interface" in s],
                    "suggestion": "This rosbridge version doesn't support interface listing services",
                },
            }

    # Since there's no direct action_type service, we'll derive it from known patterns
    # or use a mapping approach for common actions

    # Known action type mappings
    action_type_map = {
        "/turtle1/rotate_absolute": "turtlesim/action/RotateAbsolute",
        # Add more mappings as needed
    }

    # Check if it's a known action
    if action in action_type_map:
        return {"action": action, "type": action_type_map[action]}

    # For unknown actions, try to derive the type from interfaces list
    # First get all interfaces to see if we can find a matching action type
    interfaces_message = {
        "op": "call_service",
        "service": "/rosapi/interfaces",
        "type": "rosapi/Interfaces",
        "args": {},
        "id": f"get_interfaces_for_action_{action.replace('/', '_')}",
    }

    with ws_manager:
        interfaces_response = ws_manager.request(interfaces_message)

    if interfaces_response and "values" in interfaces_response:
        interfaces = interfaces_response["values"].get("interfaces", [])

        # Look for action interfaces that might match
        action_interfaces = [iface for iface in interfaces if "/action/" in iface]

        # Try to match based on action name patterns
        action_name_part = action.split("/")[-1]  # Get last part (e.g., "rotate_absolute")

        for iface in action_interfaces:
            if action_name_part.lower() in iface.lower():
                return {"action": action, "type": iface}

        # If no exact match, return the list of available action interfaces
        return {
            "error": f"Action type for {action} not found",
            "available_action_types": action_interfaces,
            "suggestion": "This action might not be available or use a different naming pattern",
        }

    return {
        "error": f"Failed to get type for action {action}",
        "action": action,
        "compatibility": {
            "issue": "Failed to retrieve interfaces from rosapi",
            "required_services": ["/rosapi/interfaces"],
            "suggestion": "Ensure rosbridge is running and rosapi is available",
            "note": "Action type resolution requires /rosapi/interfaces service",
        },
    }


@mcp.tool(
    description=(
        "Get complete action details including goal, result, and feedback structures. Works only with ROS 2.\n"
        "Example:\n"
        "get_action_details('turtlesim/action/RotateAbsolute')."
    )
)
def get_action_details(action_type: str) -> dict:
    """
    Get complete action details including goal, result, and feedback structures. Works only with ROS 2.

    Args:
        action_type (str): The action type (e.g., 'turtlesim/action/RotateAbsolute')

    Returns:
        dict: Contains complete action definition with goal, result, and feedback structures.
    """
    # Validate input
    if not action_type or not action_type.strip():
        return {"error": "Action type cannot be empty"}

    # Check if required action detail services are available
    required_services = [
        "/rosapi/action_goal_details",
        "/rosapi/action_result_details",
        "/rosapi/action_feedback_details",
    ]

    with ws_manager:
        # Get available services to check compatibility
        services_message = {
            "op": "call_service",
            "service": "/rosapi/services",
            "type": "rosapi/Services",
            "args": {},
            "id": "check_services_for_action_details",
        }

        services_response = ws_manager.request(services_message)
        if not services_response or not isinstance(services_response, dict):
            return {
                "error": "Failed to check service availability",
                "action_type": action_type,
                "compatibility": {
                    "issue": "Cannot determine available services",
                    "required_services": required_services,
                    "suggestion": "Ensure rosbridge is running and rosapi is available",
                },
            }

        available_services = services_response.get("values", {}).get("services", [])
        missing_services = [svc for svc in required_services if svc not in available_services]

        if missing_services:
            return {
                "error": f"Action details for {action_type} not found",
                "action_type": action_type,
                "compatibility": {
                    "issue": "Required action detail services are not available",
                    "missing_services": missing_services,
                    "required_services": required_services,
                    "available_services": [s for s in available_services if "action" in s],
                    "suggestions": [
                        "Use get_actions() to list available actions",
                        "Use get_action_type() to get action type from action name",
                        "Action details may not be exposed by this rosbridge/rosapi version",
                        "Consider subscribing to action topics directly for live message inspection",
                    ],
                    "note": "Action detail services (/rosapi/action_*_details) are not part of standard rosapi",
                },
            }

    result = {"action_type": action_type, "goal": {}, "result": {}, "feedback": {}}

    # Get goal, result, and feedback details in a single WebSocket context
    with ws_manager:
        # Get goal details using action-specific service
        goal_message = {
            "op": "call_service",
            "service": "/rosapi/action_goal_details",
            "type": "rosapi_msgs/srv/ActionGoalDetails",
            "args": {"type": action_type},
            "id": f"get_action_goal_details_{action_type.replace('/', '_')}",
        }

        goal_response = ws_manager.request(goal_message)
        if (
            goal_response
            and isinstance(goal_response, dict)
            and "values" in goal_response
            and "error" not in goal_response
        ):
            typedefs = goal_response["values"].get("typedefs", [])
            if typedefs:
                for typedef in typedefs:
                    field_names = typedef.get("fieldnames", [])
                    field_types = typedef.get("fieldtypes", [])
                    field_array_len = typedef.get("fieldarraylen", [])
                    examples = typedef.get("examples", [])
                    const_names = typedef.get("constnames", [])
                    const_values = typedef.get("constvalues", [])

                    fields = {}
                    field_details = {}
                    for i, (name, ftype) in enumerate(zip(field_names, field_types)):
                        fields[name] = ftype
                        field_details[name] = {
                            "type": ftype,
                            "array_length": field_array_len[i] if i < len(field_array_len) else -1,
                            "example": examples[i] if i < len(examples) else None,
                        }

                    result["goal"] = {
                        "fields": fields,
                        "field_count": len(fields),
                        "field_details": field_details,
                        "message_type": typedef.get("type", ""),
                        "examples": examples,
                        "constants": dict(zip(const_names, const_values)) if const_names else {},
                    }

        # Get result details using action-specific service
        result_message = {
            "op": "call_service",
            "service": "/rosapi/action_result_details",
            "type": "rosapi_msgs/srv/ActionResultDetails",
            "args": {"type": action_type},
            "id": f"get_action_result_details_{action_type.replace('/', '_')}",
        }

        result_response = ws_manager.request(result_message)
        if (
            result_response
            and isinstance(result_response, dict)
            and "values" in result_response
            and "error" not in result_response
        ):
            typedefs = result_response["values"].get("typedefs", [])
            if typedefs:
                for typedef in typedefs:
                    field_names = typedef.get("fieldnames", [])
                    field_types = typedef.get("fieldtypes", [])
                    field_array_len = typedef.get("fieldarraylen", [])
                    examples = typedef.get("examples", [])
                    const_names = typedef.get("constnames", [])
                    const_values = typedef.get("constvalues", [])

                    fields = {}
                    field_details = {}
                    for i, (name, ftype) in enumerate(zip(field_names, field_types)):
                        fields[name] = ftype
                        field_details[name] = {
                            "type": ftype,
                            "array_length": field_array_len[i] if i < len(field_array_len) else -1,
                            "example": examples[i] if i < len(examples) else None,
                        }

                    result["result"] = {
                        "fields": fields,
                        "field_count": len(fields),
                        "field_details": field_details,
                        "message_type": typedef.get("type", ""),
                        "examples": examples,
                        "constants": dict(zip(const_names, const_values)) if const_names else {},
                    }

        # Get feedback details using action-specific service
        feedback_message = {
            "op": "call_service",
            "service": "/rosapi/action_feedback_details",
            "type": "rosapi_msgs/srv/ActionFeedbackDetails",
            "args": {"type": action_type},
            "id": f"get_action_feedback_details_{action_type.replace('/', '_')}",
        }

        feedback_response = ws_manager.request(feedback_message)
        if (
            feedback_response
            and isinstance(feedback_response, dict)
            and "values" in feedback_response
            and "error" not in feedback_response
        ):
            typedefs = feedback_response["values"].get("typedefs", [])
            if typedefs:
                for typedef in typedefs:
                    field_names = typedef.get("fieldnames", [])
                    field_types = typedef.get("fieldtypes", [])
                    field_array_len = typedef.get("fieldarraylen", [])
                    examples = typedef.get("examples", [])
                    const_names = typedef.get("constnames", [])
                    const_values = typedef.get("constvalues", [])

                    fields = {}
                    field_details = {}
                    for i, (name, ftype) in enumerate(zip(field_names, field_types)):
                        fields[name] = ftype
                        field_details[name] = {
                            "type": ftype,
                            "array_length": field_array_len[i] if i < len(field_array_len) else -1,
                            "example": examples[i] if i < len(examples) else None,
                        }

                    result["feedback"] = {
                        "fields": fields,
                        "field_count": len(fields),
                        "field_details": field_details,
                        "message_type": typedef.get("type", ""),
                        "examples": examples,
                        "constants": dict(zip(const_names, const_values)) if const_names else {},
                    }

    # Check if we got any data
    if not result["goal"] and not result["result"] and not result["feedback"]:
        return {"error": f"Action type {action_type} not found or has no definition"}

    return result


@mcp.tool(
    description=(
        "Get action status for a specific action name. Works only with ROS 2.\n"
        "Example:\n"
        "get_action_status('/fibonacci')"
    )
)
def get_action_status(action_name: str) -> dict:
    """
    Get action status for a specific action name. Works only with ROS 2.

    Args:
        action_name (str): The action name (e.g., '/fibonacci')

    Returns:
        dict: Contains action status information including active goals and their status.
    """
    # Validate input
    if not action_name or not action_name.strip():
        return {"error": "Action name cannot be empty"}

    # Ensure action name starts with /
    if not action_name.startswith("/"):
        action_name = f"/{action_name}"

    # Try to get action status by subscribing to the status topic
    status_topic = f"{action_name}/_action/status"
    status_msg_type = "action_msgs/msg/GoalStatusArray"

    try:
        # Subscribe to action status topic
        with ws_manager:
            message = {
                "op": "subscribe",
                "topic": status_topic,
                "type": status_msg_type,
                "id": f"get_action_status_{action_name.replace('/', '_')}",
            }

            send_error = ws_manager.send(message)
            if send_error:
                return {
                    "action_name": action_name,
                    "success": False,
                    "error": f"Failed to subscribe to status topic: {send_error}",
                }

            # Wait for status message
            response = ws_manager.receive(timeout=3.0)
            if not response:
                return {
                    "action_name": action_name,
                    "success": False,
                    "error": "No response from action status topic",
                }

            response_data = json.loads(response)

            if response_data.get("op") == "status" and response_data.get("level") == "error":
                return {
                    "error": f"Action status error: {response_data.get('msg', 'Unknown error')}"
                }

            if "msg" not in response_data or "status_list" not in response_data["msg"]:
                return {
                    "action_name": action_name,
                    "success": True,
                    "active_goals": [],
                    "goal_count": 0,
                    "note": f"No active goals found for action {action_name}",
                }

            status_list = response_data["msg"]["status_list"]
            status_map = {
                0: "STATUS_UNKNOWN",
                1: "STATUS_ACCEPTED",
                2: "STATUS_EXECUTING",
                3: "STATUS_CANCELING",
                4: "STATUS_SUCCEEDED",
                5: "STATUS_CANCELED",
                6: "STATUS_ABORTED",
            }

            active_goals = []
            for status_item in status_list:
                goal_info = status_item.get("goal_info", {})
                goal_id = goal_info.get("goal_id", {}).get("uuid", "unknown")
                status = status_item.get("status", -1)
                stamp = goal_info.get("stamp", {})

                active_goals.append(
                    {
                        "goal_id": goal_id,
                        "status": status,
                        "status_text": status_map.get(status, "UNKNOWN"),
                        "timestamp": f"{stamp.get('sec', 0)}.{stamp.get('nanosec', 0)}",
                    }
                )

            return {
                "action_name": action_name,
                "success": True,
                "active_goals": active_goals,
                "goal_count": len(active_goals),
                "note": f"Found {len(active_goals)} active goal(s) for action {action_name}",
            }

    except json.JSONDecodeError as e:
        return {"error": f"Failed to parse status response: {str(e)}"}
    except Exception as e:
        return {
            "action_name": action_name,
            "success": False,
            "error": f"Failed to get action status: {str(e)}",
        }


@mcp.tool(
    description=(
        "Get comprehensive information about all actions including types and available actions. Works only with ROS 2.\n"
        "Example:\n"
        "inspect_all_actions()."
    )
)
def inspect_all_actions() -> dict:
    """
    Get comprehensive information about all actions including types and available actions. Works only with ROS 2.

    Returns:
        dict: Contains detailed information about all actions,
            including action names, types, and server information.
    """
    # Check if required action services are available
    required_services = ["/rosapi/action_servers"]

    with ws_manager:
        # Get available services to check compatibility
        services_message = {
            "op": "call_service",
            "service": "/rosapi/services",
            "type": "rosapi/Services",
            "args": {},
            "id": "check_services_for_inspect_actions",
        }

        services_response = ws_manager.request(services_message)
        if not services_response or not isinstance(services_response, dict):
            return {
                "error": "Failed to check service availability",
                "compatibility": {
                    "issue": "Cannot determine available services",
                    "required_services": required_services,
                    "suggestion": "Ensure rosbridge is running and rosapi is available",
                },
            }

        available_services = services_response.get("values", {}).get("services", [])
        missing_services = [svc for svc in required_services if svc not in available_services]

        if missing_services:
            return {
                "error": "Action inspection not supported by this rosbridge/rosapi version",
                "compatibility": {
                    "issue": "Required action services are not available",
                    "missing_services": missing_services,
                    "required_services": required_services,
                    "available_services": [s for s in available_services if "action" in s],
                    "suggestions": [
                        "This rosbridge version doesn't support action inspection services",
                        "Use get_actions() to list available actions",
                        "Consider upgrading rosbridge or using a different implementation",
                    ],
                    "note": "Action inspection requires /rosapi/action_servers service",
                },
            }

    # First get all actions
    actions_message = {
        "op": "call_service",
        "service": "/rosapi/action_servers",
        "type": "rosapi/ActionServers",
        "args": {},
        "id": "inspect_all_actions_request_1",
    }

    with ws_manager:
        actions_response = ws_manager.request(actions_message)

        if not actions_response or "values" not in actions_response:
            return {"error": "Failed to get actions list"}

        actions = actions_response["values"].get("action_servers", [])
        action_details = {}

        # Get details for each action
        action_errors = []
        for action in actions:
            # Try to get action type (this may not always work due to rosapi limitations)
            action_type = "unknown"

            # Known action type mappings for common actions
            action_type_map = {
                "/turtle1/rotate_absolute": "turtlesim/action/RotateAbsolute",
                # Add more mappings as needed based on common ROS actions
            }

            if action in action_type_map:
                action_type = action_type_map[action]
            else:
                # Try to derive from interfaces
                interfaces_message = {
                    "op": "call_service",
                    "service": "/rosapi/interfaces",
                    "type": "rosapi/Interfaces",
                    "args": {},
                    "id": f"get_interfaces_{action.replace('/', '_')}",
                }

                interfaces_response = ws_manager.request(interfaces_message)
                if interfaces_response and "values" in interfaces_response:
                    interfaces = interfaces_response["values"].get("interfaces", [])
                    action_interfaces = [iface for iface in interfaces if "/action/" in iface]

                    # Try to match based on action name patterns
                    action_name_part = action.split("/")[-1]
                    for iface in action_interfaces:
                        if action_name_part.lower() in iface.lower():
                            action_type = iface
                            break

            action_details[action] = {
                "type": action_type,
                "status": "available" if action_type != "unknown" else "type_unknown",
            }

        return {
            "total_actions": len(actions),
            "actions": action_details,
            "action_errors": action_errors,
        }


@mcp.tool(
    description=(
        "Send a goal to a ROS action server. Works only with ROS 2.\n"
        "Example:\n"
        "send_action_goal('/turtle1/rotate_absolute', 'turtlesim/action/RotateAbsolute', {'theta': 1.57})"
    )
)
async def send_action_goal(
    action_name: str,
    action_type: str,
    goal: dict,
    timeout: float | None = None,
    ctx: Context | None = None,
) -> dict:
    """
    Send a goal to a ROS action server. Works only with ROS 2.

    Args:
        action_name (str): The name of the action to call (e.g., '/turtle1/rotate_absolute')
        action_type (str): The type of the action (e.g., 'turtlesim/action/RotateAbsolute')
        goal (dict): The goal message to send
        timeout (float, optional): Timeout for action completion in seconds. Default is None (uses default timeout).

    Returns:
        dict: Contains action response including goal_id, status, and result.
    """
    # Validate inputs
    if not action_name or not action_name.strip():
        return {"error": "Action name cannot be empty"}

    if not action_type or not action_type.strip():
        return {"error": "Action type cannot be empty"}

    if not goal:
        return {"error": "Goal cannot be empty"}

    # Generate unique goal ID
    goal_id = f"goal_{int(time.time() * 1000)}_{uuid.uuid4().hex[:8]}"

    # rosbridge action goal message
    # Based on rosbridge source code, it expects "args" instead of "goal"
    message = {
        "op": "send_action_goal",
        "id": goal_id,
        "action": action_name,
        "action_type": action_type,
        "args": goal,  # rosbridge expects "args" not "goal"
        "feedback": True,  # Enable feedback messages
    }

    # Send the action goal through rosbridge
    with ws_manager:
        send_error = ws_manager.send(message)
        if send_error:
            return {
                "action": action_name,
                "action_type": action_type,
                "success": False,
                "error": f"Failed to send action goal: {send_error}",
            }

        # Wait for action completion - handle both action_result and action_feedback
        actual_timeout = timeout if timeout is not None else 10.0  # Default 10 seconds
        start_time = time.time()
        last_feedback = None  # Store the last feedback message
        feedback_count = 0  # Count feedback messages received

        while time.time() - start_time < actual_timeout:
            elapsed_time = time.time() - start_time

            response = ws_manager.receive(timeout=actual_timeout - elapsed_time)

            if response:
                try:
                    msg_data = json.loads(response)

                    # Handle action_result messages (final completion)
                    if msg_data.get("op") == "action_result":
                        # Report completion
                        if ctx:
                            try:
                                completion_msg = f"Action completed successfully (received {feedback_count} feedback messages)"
                                await ctx.report_progress(
                                    progress=feedback_count, total=None, message=completion_msg
                                )
                            except Exception:
                                pass

                        return {
                            "action": action_name,
                            "action_type": action_type,
                            "success": True,
                            "goal_id": goal_id,
                            "status": msg_data.get("status", "unknown"),
                            "result": msg_data.get("values", {}),
                        }

                    # Store action_feedback messages and report progress
                    if msg_data.get("op") == "action_feedback":
                        feedback_count += 1
                        last_feedback = msg_data

                        # Report feedback progress
                        if ctx:
                            try:
                                feedback_values = msg_data.get("values", {})
                                feedback_msg = f"Action feedback #{feedback_count}: {str(feedback_values)[:100]}..."
                                await ctx.report_progress(
                                    progress=feedback_count, total=None, message=feedback_msg
                                )
                            except Exception:
                                pass

                except json.JSONDecodeError:
                    continue
            else:
                # No response received, continue waiting
                pass

            await asyncio.sleep(0.1)

        # Timeout - return last feedback if available
        if ctx and feedback_count > 0:
            try:
                await ctx.report_progress(
                    progress=feedback_count,
                    total=None,
                    message=f"Action timed out after {actual_timeout} seconds (received {feedback_count} feedback messages)",
                )
            except Exception:
                pass

        result = {
            "action": action_name,
            "action_type": action_type,
            "success": False,
            "goal_id": goal_id,
            "error": f"Action timed out after {actual_timeout} seconds",
        }

        if last_feedback:
            result["success"] = True
            result["last_feedback"] = last_feedback.get("values", {})
            result["note"] = "Action timed out, but partial progress was made"

        return result


@mcp.tool(
    description=(
        "Cancel a specific action goal. Works only with ROS 2.\n"
        "Example:\n"
        "cancel_action_goal('/turtle1/rotate_absolute', 'goal_1758653551839_21acd486')"
    )
)
def cancel_action_goal(action_name: str, goal_id: str) -> dict:
    """
    Cancel a specific action goal. Works only with ROS 2.

    Args:
        action_name (str): The name of the action (e.g., '/turtle1/rotate_absolute')
        goal_id (str): The goal ID to cancel

    Returns:
        dict: Contains cancellation status and result.
    """
    # Validate inputs
    if not action_name or not action_name.strip():
        return {"error": "Action name cannot be empty"}

    if not goal_id or not goal_id.strip():
        return {"error": "Goal ID cannot be empty"}

    # Create cancel message for rosbridge (based on rosbridge source code)
    cancel_message = {
        "op": "cancel_action_goal",
        "id": goal_id,  # Use the actual goal ID, not a new one
        "action": action_name,
        "feedback": True,  # Enable feedback messages
    }

    # Send the cancel request through rosbridge
    with ws_manager:
        # Send cancel request
        send_error = ws_manager.send(cancel_message)
        if send_error:
            return {
                "action": action_name,
                "goal_id": goal_id,
                "success": False,
                "error": f"Failed to send cancel request: {send_error}",
            }

    return {
        "action": action_name,
        "goal_id": goal_id,
        "success": True,
        "note": "Cancel request sent successfully. Action may still be executing.",
    }


## ############################################################################################## ##
##
##                       NETWORK DIAGNOSTICS
##
## ############################################################################################## ##


@mcp.tool(
    description=(
        "Ping a robot's IP address and check if a specific port is open.\n"
        "A successful ping to the IP but not the port can indicate that ROSbridge is not running.\n"
        "Example:\n"
        "ping_robot(ip='192.168.1.100', port=9090)"
    )
)
def ping_robot(ip: str, port: int, ping_timeout: float = 2.0, port_timeout: float = 2.0) -> dict:
    """
    Ping an IP address and check if a specific port is open.

    Args:
        ip (str): The IP address to ping (e.g., '192.168.1.100')
        port (int): The port number to check (e.g., 9090)
        ping_timeout (float): Timeout for ping in seconds. Default = 2.0.
        port_timeout (float): Timeout for port check in seconds. Default = 2.0.

    Returns:
        dict: Contains ping and port check results with detailed status information.
    """
    return ping_ip_and_port(ip, port, ping_timeout, port_timeout)


def parse_arguments():
    """Parse command line arguments for MCP server configuration."""
    parser = argparse.ArgumentParser(
        description="ROS MCP Server - Connect to ROS robots via MCP protocol",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python server.py                                    # Use stdio transport (default)
  python server.py --transport http --host 0.0.0.0 --port 9000
  python server.py --transport streamable-http --host 127.0.0.1 --port 8080
        """,
    )

    parser.add_argument(
        "--transport",
        choices=["stdio", "http", "streamable-http", "sse"],
        default="stdio",
        help="MCP transport protocol to use (default: stdio)",
    )

    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="Host address for HTTP-based transports (default: 127.0.0.1)",
    )

    parser.add_argument(
        "--port",
        type=int,
        default=9000,
        help="Port number for HTTP-based transports (default: 9000)",
    )

    return parser.parse_args()


def main():
    """Main entry point for the MCP server console script."""
    # Parse command line arguments
    args = parse_arguments()

    # Update global variables with parsed arguments
    global MCP_TRANSPORT, MCP_HOST, MCP_PORT
    MCP_TRANSPORT = args.transport.lower()
    MCP_HOST = args.host
    MCP_PORT = args.port

    if MCP_TRANSPORT == "stdio":
        # stdio doesn't need host/port
        mcp.run(transport="stdio")

    elif MCP_TRANSPORT in {"http", "streamable-http"}:
        # http and streamable-http both require host/port
        print(f"Transport: {MCP_TRANSPORT} -> http://{MCP_HOST}:{MCP_PORT}", file=sys.stderr)
        mcp.run(transport=MCP_TRANSPORT, host=MCP_HOST, port=MCP_PORT)

    elif MCP_TRANSPORT == "sse":
        print(f"Transport: {MCP_TRANSPORT} -> http://{MCP_HOST}:{MCP_PORT}", file=sys.stderr)
        print("Currently unsupported. Use 'stdio', 'http', or 'streamable-http'.", file=sys.stderr)
        mcp.run(transport=MCP_TRANSPORT, host=MCP_HOST, port=MCP_PORT)

    else:
        raise ValueError(
            f"Unsupported MCP_TRANSPORT={MCP_TRANSPORT!r}. "
            "Use 'stdio', 'http', or 'streamable-http'."
        )


if __name__ == "__main__":
    main()
