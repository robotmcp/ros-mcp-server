"""ROS MCP Server - MCP instance and main entry point.

This module provides the FastMCP server instance and main() function.
"""

import argparse
import sys

from fastmcp import FastMCP

from ros_mcp.prompts import register_all_prompts
from ros_mcp.resources import register_all_resources
from ros_mcp.tools import register_all_tools
from ros_mcp.utils.websocket import WebSocketManager

# ROS bridge connection settings
ROSBRIDGE_IP = "127.0.0.1"  # Default is localhost. Replace with your local IP or set using the LLM.
ROSBRIDGE_PORT = (
    9090  # Rosbridge default is 9090. Replace with your rosbridge port or set using the LLM.
)

# Initialize MCP server
mcp = FastMCP("ros-mcp-server")

# Initialize WebSocket manager
ws_manager = WebSocketManager(ROSBRIDGE_IP, ROSBRIDGE_PORT, default_timeout=5.0)

# Register all tools
register_all_tools(mcp, ws_manager, rosbridge_ip=ROSBRIDGE_IP, rosbridge_port=ROSBRIDGE_PORT)

# Register all resources
register_all_resources(mcp, ws_manager)

# Register all prompts
register_all_prompts(mcp)


def parse_arguments():
    """Parse command line arguments for MCP server configuration."""
    parser = argparse.ArgumentParser(
        description="ROS MCP Server - Connect to ROS robots via MCP protocol",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m ros_mcp.main                                    # Use stdio transport (default)
  python -m ros_mcp.main --transport http --host 0.0.0.0 --port 9000
  python -m ros_mcp.main --transport streamable-http --host 127.0.0.1 --port 8080
  python server.py                                           # Or use the top-level entry point
        """,
    )

    parser.add_argument(
        "--transport",
        choices=["stdio", "http", "streamable-http", "sse"],
        default="stdio",
        help="MCP transport protocol to use (default: stdio)",
    )

    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="Host address for HTTP-based transports (default: 127.0.0.1)",
    )

    parser.add_argument(
        "--port",
        type=int,
        default=9000,
        help="Port number for HTTP-based transports (default: 9000)",
    )

    return parser.parse_args()


def main():
    """Main entry point for the MCP server console script."""
    # Parse command line arguments
    args = parse_arguments()

    # Get transport settings
    mcp_transport = args.transport.lower()
    mcp_host = args.host
    mcp_port = args.port

    if mcp_transport == "stdio":
        # stdio doesn't need host/port
        mcp.run(transport="stdio")

    elif mcp_transport in {"http", "streamable-http"}:
        # http and streamable-http both require host/port
        print(f"Transport: {mcp_transport} -> http://{mcp_host}:{mcp_port}", file=sys.stderr)
        mcp.run(transport=mcp_transport, host=mcp_host, port=mcp_port)

    elif mcp_transport == "sse":
        print(f"Transport: {mcp_transport} -> http://{mcp_host}:{mcp_port}", file=sys.stderr)
        print("Currently unsupported. Use 'stdio', 'http', or 'streamable-http'.", file=sys.stderr)
        mcp.run(transport=mcp_transport, host=mcp_host, port=mcp_port)

    else:
        raise ValueError(
            f"Unsupported MCP_TRANSPORT={mcp_transport!r}. "
            "Use 'stdio', 'http', or 'streamable-http'."
        )


if __name__ == "__main__":
    main()
