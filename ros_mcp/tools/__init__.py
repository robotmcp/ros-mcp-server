"""ROS MCP Tools - Tool implementations organized by category.

This module provides the main registration function to register all ROS MCP tools
with a FastMCP instance.
"""
from fastmcp import FastMCP

from ros_mcp.tools.connection import register_connection_tools
from ros_mcp.tools.robot_config import register_robot_config_tools
from ros_mcp.tools.nodes import register_node_tools
from ros_mcp.tools.services import register_service_tools
from ros_mcp.utils.websocket_manager import WebSocketManager

# TODO: Import additional tool categories as they are created:
# from ros_mcp.tools.topics import register_topic_tools
# from ros_mcp.tools.parameters import register_parameter_tools
# from ros_mcp.tools.actions import register_action_tools
# from ros_mcp.tools.images import register_image_tools


def register_ros_tools(
    mcp: FastMCP,
    ws_manager: WebSocketManager,
    rosbridge_ip: str = "127.0.0.1",
    rosbridge_port: int = 9090,
) -> None:
    """Register all ROS MCP tools with the provided FastMCP instance.
    
    This function registers all available tools with the provided WebSocketManager.
    
    Args:
        mcp: FastMCP instance to register tools with
        ws_manager: WebSocketManager instance to use for ROS connections
        rosbridge_ip: IP address of the rosbridge server (default: "127.0.0.1")
        rosbridge_port: Port of the rosbridge server (default: 9090)
    """
    default_ip = rosbridge_ip
    default_port = rosbridge_port
    
    # Register all tool categories
    register_connection_tools(mcp, ws_manager, default_ip, default_port)
    register_robot_config_tools(mcp, ws_manager)
    register_node_tools(mcp, ws_manager)
    register_service_tools(mcp, ws_manager)
    
    # TODO: Register additional tool categories as they are created:
    # register_topic_tools(mcp, ws_manager)
    # register_parameter_tools(mcp, ws_manager)
    # register_action_tools(mcp, ws_manager)
    # register_image_tools(mcp, ws_manager)
