"""Action tools for ROS MCP."""

import asyncio
import json
import time
import uuid

from fastmcp import Context, FastMCP

from ros_mcp.utils.websocket import WebSocketManager


def register_action_tools(
    mcp: FastMCP,
    ws_manager: WebSocketManager,
) -> None:
    """Register all action-related tools."""

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
            "Get complete action details including type, goal, result, and feedback structures. Works only with ROS 2.\n"
            "Example:\nget_action_details('/turtle1/rotate_absolute')"
        )
    )
    def get_action_details(action: str) -> dict:
        """
        Get complete action details including type, goal, result, and feedback structures. Works only with ROS 2.

        Args:
            action (str): The action name (e.g., '/turtle1/rotate_absolute')

        Returns:
            dict: Contains complete action definition with type, goal, result, and feedback structures.
        """
        # Validate input
        if not action or not action.strip():
            return {"error": "Action name cannot be empty"}

        # First, get the action type
        action_type = "unknown"

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

        # Known action type mappings
        action_type_map = {
            "/turtle1/rotate_absolute": "turtlesim/action/RotateAbsolute",
            # Add more mappings as needed
        }

        # Check if it's a known action
        if action in action_type_map:
            action_type = action_type_map[action]
        else:
            # For unknown actions, try to derive the type from interfaces list
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
                        action_type = iface
                        break

        if action_type == "unknown":
            return {
                "error": f"Action type for {action} not found",
                "action": action,
                "available_action_types": action_interfaces
                if "action_interfaces" in locals()
                else [],
                "suggestion": "This action might not be available or use a different naming pattern",
            }

        # Now get action details using the action type
        result = {
            "action": action,
            "action_type": action_type,
            "goal": {},
            "result": {},
            "feedback": {},
        }

        # Check if required action detail services are available
        required_detail_services = [
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
                    "action": action,
                    "action_type": action_type,
                    "compatibility": {
                        "issue": "Cannot determine available services",
                        "required_services": required_detail_services,
                        "suggestion": "Ensure rosbridge is running and rosapi is available",
                    },
                }

            available_services = services_response.get("values", {}).get("services", [])
            missing_services = [
                svc for svc in required_detail_services if svc not in available_services
            ]

            if missing_services:
                # Return what we have (action type) even if details aren't available
                return {
                    "action": action,
                    "action_type": action_type,
                    "goal": {},
                    "result": {},
                    "feedback": {},
                    "compatibility": {
                        "issue": "Required action detail services are not available",
                        "missing_services": missing_services,
                        "required_services": required_detail_services,
                        "available_services": [s for s in available_services if "action" in s],
                        "note": "Action type found, but detailed structures are not available",
                    },
                }

            # Get goal, result, and feedback details
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
            return {
                "action": action,
                "action_type": action_type,
                "error": f"Action type {action_type} found but has no definition",
            }

        return result

    @mcp.tool(
        description=(
            "Get action status for a specific action name. Works only with ROS 2.\n"
            "Example:\nget_action_status('/fibonacci')"
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

                # Unsubscribe
                ws_manager.send({"op": "unsubscribe", "topic": status_topic})

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
            "Send a goal to a ROS action server. Works only with ROS 2.\n"
            "Example:\nsend_action_goal('/turtle1/rotate_absolute', 'turtlesim/action/RotateAbsolute', {'theta': 1.57})"
        )
    )
    async def send_action_goal(
        action_name: str,
        action_type: str,
        goal: dict,
        timeout: float = None,
        ctx: Context = None,
    ) -> dict:
        """
        Send a goal to a ROS action server. Works only with ROS 2.

        Args:
            action_name (str): The name of the action to call (e.g., '/turtle1/rotate_absolute')
            action_type (str): The type of the action (e.g., 'turtlesim/action/RotateAbsolute')
            goal (dict): The goal message to send
            timeout (float): Timeout for action completion in seconds. If None, uses ws_manager.default_timeout.

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

        # Use ws_manager.default_timeout if timeout is None
        if timeout is None:
            timeout = ws_manager.default_timeout

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
            start_time = time.time()
            last_feedback = None  # Store the last feedback message
            feedback_count = 0  # Count feedback messages received

            while time.time() - start_time < timeout:
                elapsed_time = time.time() - start_time

                response = ws_manager.receive(timeout - elapsed_time)

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
                        message=f"Action timed out after {timeout} seconds (received {feedback_count} feedback messages)",
                    )
                except Exception:
                    pass

            result = {
                "action": action_name,
                "action_type": action_type,
                "success": False,
                "goal_id": goal_id,
                "error": f"Action timed out after {timeout} seconds",
            }

            if last_feedback:
                result["success"] = True
                result["last_feedback"] = last_feedback.get("values", {})
                result["note"] = "Action timed out, but partial progress was made"

            return result

    @mcp.tool(
        description=(
            "Cancel a specific action goal. Works only with ROS 2.\n"
            "Example:\ncancel_action_goal('/turtle1/rotate_absolute', 'goal_1758653551839_21acd486')"
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
