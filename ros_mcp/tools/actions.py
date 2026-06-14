"""Action tools for ROS MCP."""

import json
import time
import uuid

from fastmcp import Context, FastMCP
from mcp.types import ToolAnnotations

from ros_mcp.utils.response import _check_response, _safe_get_values
from ros_mcp.utils.rosapi_types import rosapi_service, rosapi_type
from ros_mcp.utils.websocket import WebSocketManager

# Action detail parts: result key → (rosapi service name, rosapi type name)
_ACTION_PARTS = {
    "goal": ("action_goal_details", "ActionGoalDetails"),
    "result": ("action_result_details", "ActionResultDetails"),
    "feedback": ("action_feedback_details", "ActionFeedbackDetails"),
}


def _parse_typedef(typedef: dict) -> dict:
    """Parse a rosapi typedef into a field-name -> type mapping.

    Mirrors the shape produced by get_message_details (topics) and
    get_service_details (services): a ``fields`` dict plus ``field_count``.
    """
    field_names = typedef.get("fieldnames", [])
    field_types = typedef.get("fieldtypes", [])

    fields = {}
    for name, ftype in zip(field_names, field_types):
        fields[name] = ftype

    return {"fields": fields, "field_count": len(fields)}


def _fetch_action_part(ws_manager: WebSocketManager, action_type: str, part: str) -> dict:
    """Fetch one part (goal/result/feedback) of an action definition."""
    service, type_name = _ACTION_PARTS[part]
    message = {
        "op": "call_service",
        "service": rosapi_service(service),
        "type": rosapi_type(type_name),
        "args": {"type": action_type},
        "id": f"get_action_{part}_{action_type.replace('/', '_')}",
    }
    response = ws_manager.request(message)

    error = _check_response(response)
    if error:
        return {}

    values = _safe_get_values(response)
    if values is not None:
        typedefs = values.get("typedefs", [])
        if typedefs:
            return _parse_typedef(typedefs[0])
    return {}


def register_action_tools(
    mcp: FastMCP,
    ws_manager: WebSocketManager,
) -> None:
    """Register all action-related tools."""

    @mcp.tool(
        description=("Get list of all available ROS actions.\nExample:\nget_actions()"),
        annotations=ToolAnnotations(
            title="Get Actions",
            readOnlyHint=True,
        ),
    )
    def get_actions() -> dict:
        """
        Get list of all available ROS actions.

        Returns:
            dict: Contains list of all active actions,
                or a message string if no actions are found.
        """
        message = {
            "op": "call_service",
            "service": rosapi_service("action_servers"),
            "type": rosapi_type("ActionServers"),
            "args": {},
            "id": "get_actions_request_1",
        }

        with ws_manager:
            response = ws_manager.request(message)

        error = _check_response(response)
        if error:
            return error

        values = _safe_get_values(response)
        if values is not None:
            actions = values.get("action_servers", [])
            return {"actions": actions, "action_count": len(actions)}
        return {"warning": "No actions found"}

    @mcp.tool(
        description=(
            "Get complete action details including goal, result, and feedback structures. "
            "Requires the action type; if you don't know it, call without action_type to get "
            "the list of available types back in the error.\n"
            "Example:\n"
            "get_action_details('/turtle1/rotate_absolute', 'turtlesim/action/RotateAbsolute')"
        ),
        annotations=ToolAnnotations(
            title="Get Action Details",
            readOnlyHint=True,
        ),
    )
    def get_action_details(action: str, action_type: str = "") -> dict:
        """
        Get complete action details including goal, result, and feedback structures.

        Args:
            action (str): The action name (e.g., '/turtle1/rotate_absolute')
            action_type (str): The action type (e.g., 'turtlesim/action/RotateAbsolute').
                Required. Call without action_type to get the available types back
                in the error (they are also listed by the interfaces service, not
                by get_actions(), which returns action *names*).

        Returns:
            dict: Contains complete action definition with goal, result, and feedback structures.
        """
        if not action or not action.strip():
            return {"error": "Action name cannot be empty"}

        with ws_manager:
            # Fetch the available action interfaces. We need them to suggest a
            # type when none was given, and to validate a supplied type before
            # querying its details: asking rosapi for the goal/result/feedback
            # of a non-existent type crashes the ROS 2 rosapi node, taking down
            # all rosapi services.
            interfaces_response = ws_manager.request(
                {
                    "op": "call_service",
                    "service": rosapi_service("interfaces"),
                    "type": rosapi_type("Interfaces"),
                    "args": {},
                    "id": f"get_interfaces_for_{action.replace('/', '_')}",
                }
            )
            interfaces_error = _check_response(interfaces_response)
            iface_values = _safe_get_values(interfaces_response)
            available = (
                [i for i in iface_values.get("interfaces", []) if "/action/" in i]
                if iface_values is not None
                else []
            )

            if not action_type or not action_type.strip():
                return {
                    "error": f"action_type is required for {action}",
                    "action": action,
                    "available_action_types": available,
                }

            # If the interfaces list is unavailable we cannot validate the type,
            # and we must not fall through to the detail services (a bad type
            # crashes rosapi). Report that distinctly from a genuine "not found".
            if interfaces_error:
                return {
                    "error": (
                        f"Cannot validate action_type for {action}: "
                        "the action interfaces service is unavailable"
                    ),
                    "action": action,
                    "action_type": action_type,
                }

            if action_type not in available:
                return {
                    "error": f"Action type '{action_type}' not found",
                    "action": action,
                    "action_type": action_type,
                    "available_action_types": available,
                }

            # Fetch goal, result, and feedback structures
            parts = {
                part: _fetch_action_part(ws_manager, action_type, part) for part in _ACTION_PARTS
            }

        if not any(parts.values()):
            return {
                "error": f"Action type {action_type} found but has no definition",
                "action": action,
                "action_type": action_type,
            }

        return {"action": action, "action_type": action_type, **parts}

    @mcp.tool(
        description=(
            "Get action status for a specific action name. Works only with ROS 2.\n"
            "Example:\nget_action_status('/turtle1/rotate_absolute')"
        ),
        annotations=ToolAnnotations(
            title="Get Action Status",
            readOnlyHint=True,
        ),
    )
    def get_action_status(action_name: str) -> dict:
        """
        Get action status for a specific action name. Works only with ROS 2.

        Args:
            action_name (str): The action name (e.g., '/turtle1/rotate_absolute')

        Returns:
            dict: Contains action status information including active goals and their status.
        """
        if not action_name or not action_name.strip():
            return {"error": "Action name cannot be empty"}

        if not action_name.startswith("/"):
            action_name = f"/{action_name}"

        status_topic = f"{action_name}/_action/status"
        status_msg_type = "action_msgs/msg/GoalStatusArray"

        status_map = {
            0: "STATUS_UNKNOWN",
            1: "STATUS_ACCEPTED",
            2: "STATUS_EXECUTING",
            3: "STATUS_CANCELING",
            4: "STATUS_SUCCEEDED",
            5: "STATUS_CANCELED",
            6: "STATUS_ABORTED",
        }

        try:
            with ws_manager:
                send_error = ws_manager.send(
                    {
                        "op": "subscribe",
                        "topic": status_topic,
                        "type": status_msg_type,
                        "id": f"get_action_status_{action_name.replace('/', '_')}",
                    }
                )
                if send_error:
                    return {
                        "error": f"Failed to subscribe to status topic: {send_error}",
                        "action_name": action_name,
                    }

                response = ws_manager.receive(timeout=3.0)

                # Unsubscribe regardless of result
                ws_manager.send({"op": "unsubscribe", "topic": status_topic})

                if not response:
                    # An idle action server may not publish status; that is not
                    # an error, just no goals in flight.
                    return {
                        "action_name": action_name,
                        "active_goals": [],
                        "goal_count": 0,
                        "note": "No status published; the action is idle or not running",
                    }

                response_data = json.loads(response)

                if response_data.get("op") == "status" and response_data.get("level") == "error":
                    return {
                        "error": f"Action status error: {response_data.get('msg', 'Unknown error')}",
                        "action_name": action_name,
                    }

                if "msg" not in response_data or "status_list" not in response_data.get("msg", {}):
                    return {
                        "action_name": action_name,
                        "active_goals": [],
                        "goal_count": 0,
                    }

                active_goals = []
                for item in response_data["msg"]["status_list"]:
                    goal_info = item.get("goal_info", {})
                    status = item.get("status", -1)
                    stamp = goal_info.get("stamp", {})
                    active_goals.append(
                        {
                            "goal_id": goal_info.get("goal_id", {}).get("uuid", "unknown"),
                            "status": status,
                            "status_text": status_map.get(status, "UNKNOWN"),
                            "timestamp": f"{stamp.get('sec', 0)}.{stamp.get('nanosec', 0)}",
                        }
                    )

                return {
                    "action_name": action_name,
                    "active_goals": active_goals,
                    "goal_count": len(active_goals),
                }

        except json.JSONDecodeError as e:
            return {"error": f"Failed to parse status response: {e}"}
        except Exception as e:
            return {"error": f"Failed to get action status: {e}", "action_name": action_name}

    @mcp.tool(
        description=(
            "Send a goal to a ROS action server. Works only with ROS 2.\n"
            "Example:\nsend_action_goal('/turtle1/rotate_absolute', 'turtlesim/action/RotateAbsolute', {'theta': 1.57})"
        ),
        annotations=ToolAnnotations(
            title="Send Action Goal",
            destructiveHint=True,
        ),
    )
    async def send_action_goal(
        action_name: str,
        action_type: str,
        goal: dict,
        timeout: float = None,  # type: ignore[assignment]  # See issue #140
        ctx: Context = None,  # type: ignore[assignment]  # See issue #140
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
        if not action_name or not action_name.strip():
            return {"error": "Action name cannot be empty"}
        if not action_type or not action_type.strip():
            return {"error": "Action type cannot be empty"}
        if not goal:
            return {"error": "Goal cannot be empty"}

        if not action_name.startswith("/"):
            action_name = f"/{action_name}"

        if timeout is None:
            timeout = ws_manager.default_timeout

        goal_id = f"goal_{int(time.time() * 1000)}_{uuid.uuid4().hex[:8]}"

        message = {
            "op": "send_action_goal",
            "id": goal_id,
            "action": action_name,
            "action_type": action_type,
            "args": goal,
            "feedback": True,
        }

        with ws_manager:
            send_error = ws_manager.send(message)
            if send_error:
                return {
                    "error": f"Failed to send action goal: {send_error}",
                    "action": action_name,
                    "success": False,
                }

            start_time = time.time()
            last_feedback = None
            feedback_count = 0

            while time.time() - start_time < timeout:
                remaining = timeout - (time.time() - start_time)
                response = ws_manager.receive(remaining)

                if not response:
                    continue

                try:
                    msg_data = json.loads(response)
                except json.JSONDecodeError:
                    continue

                if msg_data.get("op") == "action_result":
                    if ctx:
                        try:
                            await ctx.report_progress(
                                progress=feedback_count, total=None, message="Action completed"
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

                if msg_data.get("op") == "action_feedback":
                    feedback_count += 1
                    last_feedback = msg_data
                    if ctx:
                        try:
                            await ctx.report_progress(
                                progress=feedback_count,
                                total=None,
                                message=f"Feedback #{feedback_count}: {str(msg_data.get('values', {}))[:100]}",
                            )
                        except Exception:
                            pass

        # Timeout
        result = {
            "action": action_name,
            "action_type": action_type,
            "success": False,
            "goal_id": goal_id,
            "error": f"Action timed out after {timeout} seconds",
        }
        if last_feedback:
            result["last_feedback"] = last_feedback.get("values", {})
            result["feedback_count"] = feedback_count
        return result

    @mcp.tool(
        description=(
            "Cancel a specific action goal. Works only with ROS 2.\n"
            "Example:\ncancel_action_goal('/turtle1/rotate_absolute', 'goal_1758653551839_21acd486')"
        ),
        annotations=ToolAnnotations(
            title="Cancel Action Goal",
            destructiveHint=True,
        ),
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
        if not action_name or not action_name.strip():
            return {"error": "Action name cannot be empty"}
        if not goal_id or not goal_id.strip():
            return {"error": "Goal ID cannot be empty"}

        if not action_name.startswith("/"):
            action_name = f"/{action_name}"

        with ws_manager:
            send_error = ws_manager.send(
                {
                    "op": "cancel_action_goal",
                    "id": goal_id,
                    "action": action_name,
                }
            )
            if send_error:
                return {
                    "error": f"Failed to send cancel request: {send_error}",
                    "action": action_name,
                    "goal_id": goal_id,
                }

        # success here confirms the request was sent, not that the server
        # accepted it — the action may still be executing.
        return {
            "action": action_name,
            "goal_id": goal_id,
            "success": True,
            "note": "Cancel request sent; the action may still be executing",
        }
