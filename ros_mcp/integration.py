"""Integration module for ros-mcp-server with robotmcp_server.

This module provides the register() function called by submodule_integration.py.
It reads its own configuration from environment variables, keeping ROS-specific
configuration encapsulated within this submodule.
"""

import logging
import os

from fastmcp import FastMCP

from ros_mcp.prompts import register_all_prompts
from ros_mcp.resources import register_all_resources
from ros_mcp.tools import register_all_tools
from ros_mcp.utils.websocket import WebSocketManager

logger = logging.getLogger(__name__)

# ROS Bridge defaults (can be overridden via environment variables)
DEFAULT_ROSBRIDGE_IP = "127.0.0.1"
DEFAULT_ROSBRIDGE_PORT = 9090
DEFAULT_TIMEOUT = 5.0


def register(mcp: FastMCP, **kwargs) -> None:
    """Register all ROS MCP tools, resources, and prompts.

    This is the main entry point called by submodule_integration.py.
    Configuration is read from environment variables, not passed as parameters.

    Environment variables:
        ROSBRIDGE_IP: IP address of rosbridge server (default: 127.0.0.1)
        ROSBRIDGE_PORT: Port of rosbridge server (default: 9090)
        ROS_DEFAULT_TIMEOUT: Default timeout for ROS operations (default: 5.0)

    Args:
        mcp: FastMCP instance to register with
        **kwargs: Ignored (for forward compatibility)
    """
    rosbridge_ip = os.getenv("ROSBRIDGE_IP", DEFAULT_ROSBRIDGE_IP)
    rosbridge_port = int(os.getenv("ROSBRIDGE_PORT", str(DEFAULT_ROSBRIDGE_PORT)))
    default_timeout = float(os.getenv("ROS_DEFAULT_TIMEOUT", str(DEFAULT_TIMEOUT)))

    logger.info(f"[ROS_MCP] Initializing with rosbridge at {rosbridge_ip}:{rosbridge_port}")

    # Create WebSocketManager with configuration
    ws_manager = WebSocketManager(rosbridge_ip, rosbridge_port, default_timeout=default_timeout)

    # Register all components
    register_all_tools(mcp, ws_manager, rosbridge_ip=rosbridge_ip, rosbridge_port=rosbridge_port)
    register_all_resources(mcp, ws_manager)
    register_all_prompts(mcp)

    logger.info("[ROS_MCP] Registration complete")
