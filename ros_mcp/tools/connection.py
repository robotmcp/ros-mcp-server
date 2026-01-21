"""Connection tools for ROS MCP."""

import asyncio
from datetime import datetime, timezone
from typing import Union

from fastmcp import FastMCP, Context

from ros_mcp.utils.network_utils import ping_ip_and_port
from ros_mcp.utils.websocket import WebSocketManager


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
        """
        Connect to a robot by setting the IP and port for the WebSocket connection, then testing connectivity.

        Args:
            ip (str): The IP address of the rosbridge server.
            port (int): The port number of the rosbridge server.
            ping_timeout (float): Timeout for ping in seconds. Default = 2.0.
            port_timeout (float): Timeout for port check in seconds. Default = 2.0.

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

    @mcp.tool(
        description=(
            "Get the current server time in HH:MM:SS format (UTC).\n"
            "Compare with time.is to measure latency.\n"
            "If use_progress=True, sends time updates every second for 10 seconds.\n"
            "If use_progress=False, returns time once."
        )
    )
    async def get_time(ctx: Context, use_progress: bool = False) -> dict:
        """
        Get current server time for latency measurement.

        Args:
            ctx: MCP context for progress reporting.
            use_progress: If True, send 10 seconds of progress updates.

        Returns:
            dict: Contains current UTC time in HH:MM:SS format.
        """
        def get_current_time() -> str:
            return datetime.now(timezone.utc).strftime("%H:%M:%S")

        if use_progress:
            for i in range(10):
                current_time = get_current_time()
                await ctx.report_progress(
                    progress=i + 1,
                    total=10,
                    message=f"UTC: {current_time}"
                )
                if i < 9:
                    await asyncio.sleep(1)

        return {
            "utc_time": get_current_time(),
            "compare_with": "https://time.is/UTC",
        }
