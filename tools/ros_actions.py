# tools/ros_actions.py
import json
import time
import uuid
from typing import Optional

# Note: This module provides ROS actions tools that will be imported by server.py
# The MCP instance and WebSocket manager are managed by server.py
# ws_manager will be passed as a parameter or imported when needed


def get_actions(ws_manager) -> dict:
    """
    Get list of all available ROS actions.

    Returns:
        dict: Contains list of all active actions,
            or a message string if no actions are found.
    """
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


def get_action_type(action: str, ws_manager) -> dict:
    """
    Get the action type for a specific action.

    Args:
        action (str): The action name (e.g., '/turtle1/rotate_absolute')

    Returns:
        dict: Contains the action type,
            or an error message if action doesn't exist.
    """
    # Validate input
    if not action or not action.strip():
        return {"error": "Action name cannot be empty"}

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

    return {"error": f"Failed to get type for action {action}"}


def get_action_details(action_type: str, ws_manager) -> dict:
    """
    Get complete action details including goal, result, and feedback structures.

    Args:
        action_type (str): The action type (e.g., 'turtlesim/action/RotateAbsolute')

    Returns:
        dict: Contains complete action definition with goal, result, and feedback structures.
    """
    # Validate input
    if not action_type or not action_type.strip():
        return {"error": "Action type cannot be empty"}

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
        if goal_response and "values" in goal_response:
            typedefs = goal_response["values"].get("typedefs", [])
            if typedefs:
                for typedef in typedefs:
                    field_names = typedef.get("fieldnames", [])
                    field_types = typedef.get("fieldtypes", [])
                    fields = {}
                    for name, ftype in zip(field_names, field_types):
                        fields[name] = ftype
                    result["goal"] = {"fields": fields, "field_count": len(fields)}

        # Get result details using action-specific service
        result_message = {
            "op": "call_service",
            "service": "/rosapi/action_result_details",
            "type": "rosapi_msgs/srv/ActionResultDetails",
            "args": {"type": action_type},
            "id": f"get_action_result_details_{action_type.replace('/', '_')}",
        }

        result_response = ws_manager.request(result_message)
        if result_response and "values" in result_response:
            typedefs = result_response["values"].get("typedefs", [])
            if typedefs:
                for typedef in typedefs:
                    field_names = typedef.get("fieldnames", [])
                    field_types = typedef.get("fieldtypes", [])
                    fields = {}
                    for name, ftype in zip(field_names, field_types):
                        fields[name] = ftype
                    result["result"] = {"fields": fields, "field_count": len(fields)}

        # Get feedback details using action-specific service
        feedback_message = {
            "op": "call_service",
            "service": "/rosapi/action_feedback_details",
            "type": "rosapi_msgs/srv/ActionFeedbackDetails",
            "args": {"type": action_type},
            "id": f"get_action_feedback_details_{action_type.replace('/', '_')}",
        }

        feedback_response = ws_manager.request(feedback_message)
        if feedback_response and "values" in feedback_response:
            typedefs = feedback_response["values"].get("typedefs", [])
            if typedefs:
                for typedef in typedefs:
                    field_names = typedef.get("fieldnames", [])
                    field_types = typedef.get("fieldtypes", [])
                    fields = {}
                    for name, ftype in zip(field_names, field_types):
                        fields[name] = ftype
                    result["feedback"] = {"fields": fields, "field_count": len(fields)}

    # Check if we got any data
    if not result["goal"] and not result["result"] and not result["feedback"]:
        return {"error": f"Action type {action_type} not found or has no definition"}

    return result


def inspect_all_actions(ws_manager) -> dict:
    """
    Get comprehensive information about all actions including types and available actions.

    Returns:
        dict: Contains detailed information about all actions,
            including action names, types, and server information.
    """
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


def send_action_goal(
    action_name: str,
    action_type: str,
    goal: dict,
    ws_manager,
    timeout: Optional[float] = None,
    blocking: bool = True,
) -> dict:
    """
    Send a goal to a ROS action server.

    Args:
        action_name (str): The name of the action to call (e.g., '/turtle1/rotate_absolute')
        action_type (str): The type of the action (e.g., 'turtlesim/action/RotateAbsolute')
        goal (dict): The goal message to send
        timeout (float, optional): Timeout for action completion in seconds. Default is None (no timeout).
        blocking (bool): If True, wait for action completion. If False, return immediately after sending.

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
        "args": goal,  # rosbridge expects "args" not "goal" as in previous versions
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

        # Handle blocking vs non-blocking mode
        if not blocking:
            # Non-blocking mode: return immediately after sending
            return {
                "action": action_name,
                "action_type": action_type,
                "success": True,
                "goal_id": goal_id,
                "status": "sent",
                "note": "Goal sent successfully in non-blocking mode. Use get_action_result to check completion.",
            }

        # Blocking mode: wait for response with timeout
        actual_timeout = timeout if timeout is not None else 30.0  # Increased default timeout
        start_time = time.time()

        while time.time() - start_time < actual_timeout:
            response = ws_manager.receive(timeout=2.0)  # Check every 2 seconds

            if response:
                try:
                    msg_data = json.loads(response)

                    # Check for status errors
                    if msg_data.get("op") == "status" and msg_data.get("level") == "error":
                        return {
                            "action": action_name,
                            "action_type": action_type,
                            "success": False,
                            "error": f"Action goal failed: {msg_data.get('msg', 'Unknown error')}",
                        }

                    # Check for action response
                    if msg_data.get("op") == "action_result":
                        return {
                            "action": action_name,
                            "action_type": action_type,
                            "success": msg_data.get("result", False),
                            "goal_id": goal_id,
                            "status": msg_data.get("status", "unknown"),
                            "result": msg_data.get("values", {}),
                        }

                except json.JSONDecodeError:
                    continue

    return {
        "action": action_name,
        "action_type": action_type,
        "success": True,
        "goal_id": goal_id,
        "status": "sent",
        "note": "Goal sent successfully. Action may be executing asynchronously.",
    }


def cancel_action_goal(action_name: str, goal_id: str, ws_manager) -> dict:
    """
    Cancel a specific action goal.

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
    }

    # Send the cancel request through rosbridge
    with ws_manager:
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
        "status": "cancel_sent",
        "note": "Cancel request sent successfully. Action may still be executing.",
    }


def register_action_tools(mcp_instance, ws_manager):
    """Register all ROS action tools with the MCP instance."""

    @mcp_instance.tool(
        description="Get list of all available ROS actions.\nExample:\nget_actions()"
    )
    def get_actions_tool() -> dict:
        return get_actions(ws_manager)

    @mcp_instance.tool(
        description="Get the action type for a specific action.\nExample:\nget_action_type('/turtle1/rotate_absolute')"
    )
    def get_action_type_tool(action: str) -> dict:
        return get_action_type(action, ws_manager)

    @mcp_instance.tool(
        description="Get complete action details including goal, result, and feedback structures.\nExample:\nget_action_details('turtlesim/action/RotateAbsolute')"
    )
    def get_action_details_tool(action_type: str) -> dict:
        return get_action_details(action_type, ws_manager)

    @mcp_instance.tool(
        description="Get comprehensive information about all actions including types and available actions.\nExample:\ninspect_all_actions()"
    )
    def inspect_all_actions_tool() -> dict:
        return inspect_all_actions(ws_manager)

    @mcp_instance.tool(
        description="Send a goal to a ROS action server.\nExample:\nsend_action_goal('/turtle1/rotate_absolute', 'turtlesim/action/RotateAbsolute', {'theta': 1.57})\nsend_action_goal('/turtle1/rotate_absolute', 'turtlesim/action/RotateAbsolute', {'theta': 1.57}, blocking=False)  # Non-blocking"
    )
    def send_action_goal_tool(
        action_name: str,
        action_type: str,
        goal: dict,
        timeout: Optional[float] = None,
        blocking: bool = True,
    ) -> dict:
        return send_action_goal(action_name, action_type, goal, ws_manager, timeout, blocking)

    @mcp_instance.tool(
        description="Cancel a specific action goal.\nExample:\ncancel_action_goal('/turtle1/rotate_absolute', 'goal_1758653551839_21acd486')"
    )
    def cancel_action_goal_tool(action_name: str, goal_id: str) -> dict:
        return cancel_action_goal(action_name, goal_id, ws_manager)
