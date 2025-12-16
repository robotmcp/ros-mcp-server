"""Entry point for ROS MCP Server (modular version).

This module provides a simple entry point that imports and runs the main() function
from ros_mcp.server. This is the recommended way to run the server.

Usage:
    python main.py
    python -m ros_mcp.server
    
The modular version uses ros_mcp/server.py and ros_mcp/tools.py.
"""
from ros_mcp.main import main

if __name__ == "__main__":
    main()

