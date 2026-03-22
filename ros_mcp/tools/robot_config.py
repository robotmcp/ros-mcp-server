"""Robot configuration tools for ROS MCP."""

from fastmcp import FastMCP
from mcp.types import ToolAnnotations

from ros_mcp.utils.config_utils import get_verified_robot_spec_util, get_verified_robots_list_util
from ros_mcp.utils.rosapi_types import DetectionError, RosVersion, get_distro, get_ros_version
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
        ),
        annotations=ToolAnnotations(
            title="Get Verified Robots List",
            readOnlyHint=True,
        ),
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
        description="Detect the ROS version and distribution via rosbridge.",
        annotations=ToolAnnotations(
            title="Detect ROS Version",
            readOnlyHint=True,
        ),
    )
    def detect_ros_version() -> dict:
        """
        Detects the ROS version and distro via rosbridge WebSocket.

        Returns:
            dict: {'version': '1' or '2', 'distro': '<distro name>'} or error info.
        """
        try:
            version = get_ros_version()
            distro = get_distro()
            return {
                "version": "1" if version == RosVersion.ROS1 else "2",
                "distro": distro,
            }
        except DetectionError as e:
            return {"error": f"Could not detect ROS version: {e}"}
