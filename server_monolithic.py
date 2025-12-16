import argparse
import os
import sys
from typing import Union

from fastmcp import FastMCP

from resources import register_all_resources
from utils.config_utils import get_verified_robot_spec_util, get_verified_robots_list_util
from utils.network_utils import ping_ip_and_port
from utils.websocket_manager import WebSocketManager

# ROS bridge connection settings
ROSBRIDGE_IP = "127.0.0.1"  # Default is localhost. Replace with your local IPor set using the LLM.
ROSBRIDGE_PORT = (
    9090  # Rosbridge default is 9090. Replace with your rosbridge port or set using the LLM.
)

# MCP transport settings
MCP_TRANSPORT = os.getenv("MCP_TRANSPORT", "stdio").lower()  # Default is stdio.

# MCP connection settings (streamable-http)
MCP_HOST = os.getenv(
    "MCP_HOST", "127.0.0.1"
)  # Default is localhost. Replace with the address of your remote MCP server.

# MCP port settings (default=9000)
MCP_PORT = int(
    os.getenv("MCP_PORT", "9000")
)  # Default is 9000. Replace with the port of your remote MCP server.

# Initialize MCP server and WebSocket manager
mcp = FastMCP("ros-mcp-server")
ws_manager = WebSocketManager(
    ROSBRIDGE_IP, ROSBRIDGE_PORT, default_timeout=5.0
)  # Increased default timeout for ROS operations


register_all_resources(mcp, ws_manager)


@mcp.tool(
    description=(
        "Load specifications and usage context for a verified robot model. "
        "ONLY use if the robot model is in the verified list (use get_verified_robots_list first to check). "
        "Most robots won't have a spec - that's OK, connect directly using connect_to_robot instead."
    )
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
    )
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
    description=(
        "Connect to the robot by setting the IP/port. This tool also tests connectivity to confirm that the robot is reachable and the port is open."
    )
)
def connect_to_robot(
    ip: str = ROSBRIDGE_IP,
    port: Union[int, str] = ROSBRIDGE_PORT,
    ping_timeout: float = 2.0,
    port_timeout: float = 2.0,
) -> dict:
    """
    Connect to a robot by setting the IP and port for the WebSocket connection, then testing connectivity.

    Args:
        ip (str): The IP address of the rosbridge server. Defaults to "127.0.0.1" (localhost).
        port (int): The port number of the rosbridge server. Defaults to 9090.
        ping_timeout (float): Timeout for ping in seconds. Default = 2.0.
        port_timeout (float): Timeout for port check in seconds. Default = 2.0.

    Returns:
        dict: Connection status with ping and port check results.
    """
    # Set default values if None
    actual_ip = str(ip).strip() if ip else ROSBRIDGE_IP
    actual_port = int(port) if port else ROSBRIDGE_PORT

    # Set the IP and port
    ws_manager.set_ip(actual_ip, actual_port)

    # Test connectivity
    ping_result = ping_ip_and_port(actual_ip, actual_port, ping_timeout, port_timeout)

    # Combine the results
    return {
        "message": f"WebSocket IP set to {actual_ip}:{actual_port}",
        "connectivity_test": ping_result,
    }


## ############################################################################################## ##
##
##                       ROS ACTIONS (migrated to ros_mcp/tools/actions.py)
##
## ############################################################################################## ##


def parse_arguments():
    """Parse command line arguments for MCP server configuration."""
    parser = argparse.ArgumentParser(
        description="ROS MCP Server - Connect to ROS robots via MCP protocol",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python server.py                                    # Use stdio transport (default)
  python server.py --transport http --host 0.0.0.0 --port 9000
  python server.py --transport streamable-http --host 127.0.0.1 --port 8080
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

    # Update global variables with parsed arguments
    global MCP_TRANSPORT, MCP_HOST, MCP_PORT
    MCP_TRANSPORT = args.transport.lower()
    MCP_HOST = args.host
    MCP_PORT = args.port

    if MCP_TRANSPORT == "stdio":
        # stdio doesn't need host/port
        mcp.run(transport="stdio")

    elif MCP_TRANSPORT in {"http", "streamable-http"}:
        # http and streamable-http both require host/port
        print(f"Transport: {MCP_TRANSPORT} -> http://{MCP_HOST}:{MCP_PORT}", file=sys.stderr)
        mcp.run(transport=MCP_TRANSPORT, host=MCP_HOST, port=MCP_PORT)

    elif MCP_TRANSPORT == "sse":
        print(f"Transport: {MCP_TRANSPORT} -> http://{MCP_HOST}:{MCP_PORT}", file=sys.stderr)
        print("Currently unsupported. Use 'stdio', 'http', or 'streamable-http'.", file=sys.stderr)
        mcp.run(transport=MCP_TRANSPORT, host=MCP_HOST, port=MCP_PORT)

    else:
        raise ValueError(
            f"Unsupported MCP_TRANSPORT={MCP_TRANSPORT!r}. "
            "Use 'stdio', 'http', or 'streamable-http'."
        )


if __name__ == "__main__":
    main()
