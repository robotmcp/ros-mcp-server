"""Parameter tools for ROS1 MCP."""

import json

from fastmcp import FastMCP
from mcp.types import ToolAnnotations

from ros_mcp.utils.websocket import WebSocketManager


def _infer_param_type(raw_value: str) -> str:
    """Infer ROS parameter type from rosapi string payload."""
    if raw_value is None:
        return "unknown"

    value = str(raw_value).strip()
    if value == "":
        return "string"

    # rosapi/get_param often returns JSON-encoded strings
    try:
        parsed = json.loads(value)
        if isinstance(parsed, bool):
            return "bool"
        if isinstance(parsed, int):
            return "int"
        if isinstance(parsed, float):
            return "float"
        if isinstance(parsed, list):
            return "list"
        if isinstance(parsed, dict):
            return "dict"
        return "string"
    except Exception:
        pass

    lower = value.lower()
    if lower in {"true", "false"}:
        return "bool"

    try:
        int(value)
        return "int"
    except Exception:
        pass

    try:
        float(value)
        return "float"
    except Exception:
        pass

    return "string"


def _safe_check_parameter_exists(
    name: str, ws_manager: WebSocketManager
) -> tuple[bool, str, dict | None]:
    """Check parameter existence via /rosapi/get_param (safe fallback)."""

    message = {
        "op": "call_service",
        "service": "/rosapi/get_param",
        "type": "rosapi/GetParam",
        "args": {"name": name},
        "id": f"check_param_exists_{name.replace('/', '_').replace(':', '_')}",
    }

    try:
        with ws_manager:
            response = ws_manager.request(message)

        if not response:
            return False, "No response from service", None

        values = response.get("values") if isinstance(response, dict) else None
        if isinstance(values, dict):
            value = values.get("value", "")
            successful = bool(values.get("successful", False))
            if successful or str(value).strip() not in {"", '""', "''"}:
                return True, "", response
            reason = values.get("reason", "Parameter does not exist")
            return False, reason, None

        result = response.get("result") if isinstance(response, dict) else None
        if isinstance(result, dict):
            value = result.get("value", "")
            successful = bool(result.get("successful", False))
            if successful or str(value).strip() not in {"", '""', "''"}:
                return True, "", response
            reason = result.get("reason", "Parameter does not exist")
            return False, reason, None

        return False, "Unexpected response format", None
    except Exception as e:
        return False, f"Error checking parameter: {str(e)}", None


def register_parameter_tools(
    mcp: FastMCP,
    ws_manager: WebSocketManager,
) -> None:
    """Register all ROS1 parameter-related tools."""

    @mcp.tool(
        description=(
            "Get a single ROS parameter value by name.\n"
            "Example:\nget_parameter('/turtlesim/background_b')"
        ),
        annotations=ToolAnnotations(
            title="Get Parameter",
            readOnlyHint=True,
        ),
    )
    def get_parameter(name: str) -> dict:
        """Get a ROS parameter value by name."""
        if not name or not name.strip():
            return {"error": "Parameter name cannot be empty"}

        exists, reason, response = _safe_check_parameter_exists(name, ws_manager)
        if not exists:
            return {
                "name": name,
                "value": "",
                "successful": False,
                "reason": reason or f"Parameter {name} does not exist",
                "exists": False,
            }

        values = response.get("values") if isinstance(response, dict) else None
        result = response.get("result") if isinstance(response, dict) else None
        payload = values if isinstance(values, dict) else result if isinstance(result, dict) else {}
        value = payload.get("value", "") if isinstance(payload, dict) else ""

        return {
            "name": name,
            "value": value,
            "successful": True,
            "reason": payload.get("reason", "") if isinstance(payload, dict) else "",
            "type": _infer_param_type(value),
            "exists": True,
        }

    @mcp.tool(
        description=(
            "Set a single ROS parameter value.\n"
            "Example:\nset_parameter('/turtlesim/background_b', '255')"
        ),
        annotations=ToolAnnotations(
            title="Set Parameter",
            destructiveHint=True,
        ),
    )
    def set_parameter(name: str, value: str) -> dict:
        """Set a ROS parameter value."""
        if not name or not name.strip():
            return {"error": "Parameter name cannot be empty"}

        message = {
            "op": "call_service",
            "service": "/rosapi/set_param",
            "type": "rosapi/SetParam",
            "args": {"name": name, "value": value},
            "id": f"set_param_{name.replace('/', '_').replace(':', '_')}",
        }

        try:
            with ws_manager:
                response = ws_manager.request(message)
        except Exception as e:
            return {
                "name": name,
                "value": value,
                "successful": False,
                "reason": f"Error setting parameter: {str(e)}",
            }

        values = response.get("values") if isinstance(response, dict) else None
        result = response.get("result") if isinstance(response, dict) else None
        payload = values if isinstance(values, dict) else result if isinstance(result, dict) else {}

        successful = bool(payload.get("successful", True)) if isinstance(payload, dict) else True
        reason = payload.get("reason", "") if isinstance(payload, dict) else ""

        return {
            "name": name,
            "value": value,
            "successful": successful,
            "reason": reason,
        }

    @mcp.tool(
        description=(
            "Check if a ROS parameter exists.\n"
            "Example:\nhas_parameter('/turtlesim/background_b')"
        ),
        annotations=ToolAnnotations(
            title="Has Parameter",
            readOnlyHint=True,
        ),
    )
    def has_parameter(name: str) -> dict:
        """Check if a ROS parameter exists."""
        if not name or not name.strip():
            return {"error": "Parameter name cannot be empty"}

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
            "Example:\ndelete_parameter('/turtlesim/background_b')"
        ),
        annotations=ToolAnnotations(
            title="Delete Parameter",
            destructiveHint=True,
        ),
    )
    def delete_parameter(name: str) -> dict:
        """Delete a ROS parameter."""
        if not name or not name.strip():
            return {"error": "Parameter name cannot be empty"}

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
            "service": "/rosapi/delete_param",
            "type": "rosapi/DeleteParam",
            "args": {"name": name},
            "id": f"delete_param_{name.replace('/', '_').replace(':', '_')}",
        }

        try:
            with ws_manager:
                response = ws_manager.request(message)
        except Exception as e:
            return {
                "name": name,
                "successful": False,
                "reason": f"Error deleting parameter: {str(e)}",
            }

        values = response.get("values") if isinstance(response, dict) else None
        result = response.get("result") if isinstance(response, dict) else None
        payload = values if isinstance(values, dict) else result if isinstance(result, dict) else {}

        successful = bool(payload.get("successful", False)) if isinstance(payload, dict) else False
        reason = payload.get("reason", "") if isinstance(payload, dict) else ""

        return {
            "name": name,
            "successful": successful,
            "reason": reason,
        }

    @mcp.tool(
        description=(
            "Get all ROS parameter names from the parameter server.\n"
            "Example:\nget_parameters()"
        ),
        annotations=ToolAnnotations(
            title="Get Parameters",
            readOnlyHint=True,
        ),
    )
    def get_parameters() -> dict:
        """Get all ROS parameter names from the parameter server."""
        message = {
            "op": "call_service",
            "service": "/rosapi/get_param_names",
            "type": "rosapi/GetParamNames",
            "args": {},
            "id": "get_param_names",
        }

        try:
            with ws_manager:
                response = ws_manager.request(message)
        except Exception as e:
            return {"error": f"Failed to list parameters: {str(e)}"}

        if not isinstance(response, dict):
            return {"error": "Unexpected response format from /rosapi/get_param_names"}

        values = response.get("values", {})
        names = values.get("names", []) if isinstance(values, dict) else []

        return {"parameters": names, "parameter_count": len(names)}

    @mcp.tool(
        description=(
            "Get detailed metadata about a single ROS parameter.\n"
            "Example:\nget_parameter_details('/turtlesim/background_r')"
        ),
        annotations=ToolAnnotations(
            title="Get Parameter Details",
            readOnlyHint=True,
        ),
    )
    def get_parameter_details(name: str) -> dict:
        """Get detailed metadata about a single ROS parameter."""
        if not name or not name.strip():
            return {"error": "Parameter name cannot be empty"}

        basic = get_parameter(name)
        if basic.get("exists") is False:
            return {
                "name": name,
                "value": "",
                "type": "unknown",
                "exists": False,
                "description": "",
                "reason": basic.get("reason", "Parameter does not exist"),
            }

        value = basic.get("value", "")
        return {
            "name": name,
            "value": value,
            "type": _infer_param_type(value),
            "exists": True,
            "description": "",
        }
