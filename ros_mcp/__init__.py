"""ROS MCP Package - Modularized ROS-MCP-Server.

This package provides ROS MCP tools that can be registered with any FastMCP instance.
"""

from ros_mcp.main import main, mcp
from ros_mcp.tools import register_ros_tools
from ros_mcp.utils.websocket_manager import WebSocketManager

__all__ = ["main", "mcp", "register_ros_tools", "WebSocketManager"]
