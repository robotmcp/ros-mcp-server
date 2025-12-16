"""Connection tools for ROS MCP."""

from typing import Union

from fastmcp import FastMCP

from ros_mcp.utils.network_utils import ping_ip_and_port
from ros_mcp.utils.websocket_manager import WebSocketManager


def connect_to_robot_impl(
    ws_manager: WebSocketManager,
    ip: str,
    port: Union[int, str],
    ping_timeout: float = 2.0,
    port_timeout: float = 2.0,
    default_ip: str = "127.0.0.1",
    default_port: int = 9090,
) -> dict:
    """
    Connect to a robot by setting the IP and port for the WebSocket connection, then testing connectivity.

    Args:
        ws_manager: WebSocketManager instance to use for connections
        ip (str): The IP address of the rosbridge server.
        port (int): The port number of the rosbridge server.
        ping_timeout (float): Timeout for ping in seconds. Default = 2.0.
        port_timeout (float): Timeout for port check in seconds. Default = 2.0.
        default_ip (str): Default IP address if ip is None or empty.
        default_port (int): Default port if port is None or empty.

    Returns:
        dict: Connection status with ping and port check results.
    """
    # Set default values if None
    actual_ip = str(ip).strip() if ip else default_ip
    actual_port = int(port) if port else default_port

    # Set the IP and port
    ws_manager.set_ip(actual_ip, actual_port)

    # Test connectivity
    ping_result = ping_ip_and_port(actual_ip, actual_port, ping_timeout, port_timeout)

    # Combine the results
    return {
        "message": f"WebSocket IP set to {actual_ip}:{actual_port}",
        "connectivity_test": ping_result,
    }


def ping_robot_impl(
    ip: str,
    port: int,
    ping_timeout: float = 2.0,
    port_timeout: float = 2.0,
) -> dict:
    """
    Ping an IP address and check if a specific port is open.

    Args:
        ip (str): The IP address to ping (e.g., '192.168.1.100')
        port (int): The port number to check (e.g., 9090)
        ping_timeout (float): Timeout for ping in seconds. Default = 2.0.
        port_timeout (float): Timeout for port check in seconds. Default = 2.0.

    Returns:
        dict: Contains ping and port check results with detailed status information.
    """
    return ping_ip_and_port(ip, port, ping_timeout, port_timeout)


def register_connection_tools(
    mcp: FastMCP,
    ws_manager: WebSocketManager,
    default_ip: str,
    default_port: int,
) -> None:
    """Register all connection-related tools."""

    @mcp.tool(
        description=(
            "Connect to the robot by setting the IP/port. This tool also tests connectivity to confirm that the robot is reachable and the port is open."
        )
    )
    def connect_to_robot(
        ip: str = default_ip,
        port: Union[int, str] = default_port,
        ping_timeout: float = 2.0,
        port_timeout: float = 2.0,
    ) -> dict:
        """Connect to a robot by setting the IP and port for the WebSocket connection, then testing connectivity."""
        return connect_to_robot_impl(
            ws_manager, ip, port, ping_timeout, port_timeout, default_ip, default_port
        )

    @mcp.tool(
        description=(
            "Ping a robot's IP address and check if a specific port is open.\n"
            "A successful ping to the IP but not the port can indicate that ROSbridge is not running.\n"
            "Example:\n"
            "ping_robot(ip='192.168.1.100', port=9090)"
        )
    )
    def ping_robot(
        ip: str,
        port: int,
        ping_timeout: float = 2.0,
        port_timeout: float = 2.0,
    ) -> dict:
        """Ping an IP address and check if a specific port is open."""
        return ping_robot_impl(ip, port, ping_timeout, port_timeout)


