"""ROS MCP Package - Modularized ROS-MCP-Server.

This package provides ROS MCP tools that can be registered with any FastMCP instance.
"""


def __getattr__(name):
    """Lazy import to avoid requiring fastmcp for utility imports."""
    if name == "main":
        from ros_mcp.main import main

        return main
    if name == "mcp":
        from ros_mcp.main import mcp

        return mcp
    if name == "register_all_tools":
        from ros_mcp.tools import register_all_tools

        return register_all_tools
    if name == "WebSocketManager":
        from ros_mcp.utils.websocket import WebSocketManager

        return WebSocketManager
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = ["main", "mcp", "register_all_tools", "WebSocketManager"]
