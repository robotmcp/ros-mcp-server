"""Robot configuration tools for ROS1 MCP."""

from fastmcp import FastMCP
from mcp.types import ToolAnnotations

from ros_mcp.utils.config_utils import get_verified_robot_spec_util, get_verified_robots_list_util
from ros_mcp.utils.websocket import WebSocketManager


def register_robot_config_tools(mcp: FastMCP, ws_manager: WebSocketManager) -> None:
    """Register all robot configuration-related tools."""

    @mcp.tool(
        description=(
            "Load specifications and usage context for a verified robot model. "
            "ONLY use if the robot model is in the verified list (use get_verified_robots_list first to check). "
            "Most robots won't have a spec - that's OK, connect directly using connect_to_robot instead."
        ),
        annotations=ToolAnnotations(
            title="Get Verified Robot Spec",
            readOnlyHint=True,
        ),
    )
    def get_verified_robot_spec(name: str) -> dict:
        """Load pre-defined specifications and additional context for a verified robot model."""
        robot_config = get_verified_robot_spec_util(name)

        if len(robot_config) > 1:
            return {
                "error": f"Multiple configurations found for robot '{name}'. Please specify a more precise name."
            }
        if not robot_config:
            return {
                "error": f"No configuration found for robot '{name}'. Please check the name and try again. Or set IP/port manually using connect_to_robot."
            }
        return {"robot_config": robot_config}

    @mcp.tool(
        description=(
            "List pre-verified robot models that have specification files with usage guidance available. "
            "If your robot is not in this list, you can still connect to it directly using connect_to_robot."
        ),
        annotations=ToolAnnotations(
            title="Get Verified Robots List",
            readOnlyHint=True,
        ),
    )
    def get_verified_robots_list() -> dict:
        """List all pre-verified robot models that have specification files available."""
        return get_verified_robots_list_util()

    @mcp.tool(
        description="Detect ROS1 distribution via rosbridge (/rosapi/get_param name=/rosdistro).",
        annotations=ToolAnnotations(
            title="Detect ROS Version",
            readOnlyHint=True,
        ),
    )
    def detect_ros_version() -> dict:
        """Detect ROS1 distribution via rosbridge WebSocket."""
        ros1_request = {
            "op": "call_service",
            "id": "ros1_distro_check",
            "service": "/rosapi/get_param",
            "type": "rosapi/GetParam",
            "args": {"name": "/rosdistro"},
        }

        with ws_manager:
            response = ws_manager.request(ros1_request)

        if isinstance(response, dict):
            values = response.get("values", {})
            if isinstance(values, dict):
                distro = values.get("value")
                if distro is not None:
                    distro_clean = str(distro).strip('"').replace("\\n", "").replace("\n", "")
                    return {"version": "1", "distro": distro_clean}

        return {"error": "Could not detect ROS1 distribution via /rosapi/get_param /rosdistro"}
