"""Entry point for ROS MCP Server (modular version).

This module provides a simple entry point that imports and runs the main() function
from ros_mcp.main. This is the recommended way to run the server.

Usage:
    python server.py
    python -m ros_mcp.main

The modular version uses ros_mcp/main.py and ros_mcp/tools/.
"""

from ros_mcp.main import main

if __name__ == "__main__":
    main()
