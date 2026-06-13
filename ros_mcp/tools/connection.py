"""Connection tools for ROS MCP."""

from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Union

from fastmcp import FastMCP
from mcp.types import ToolAnnotations

from ros_mcp.utils.network_utils import ping_ip_and_port
from ros_mcp.utils.rosapi_types import detect_rosapi_types
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
        ),
        annotations=ToolAnnotations(
            title="Connect to Robot",
            destructiveHint=False,
        ),
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

        # Detect ROS version and cache rosapi type resolver
        detection_warning = None
        if ping_result.get("port_check", {}).get("open"):
            try:
                detect_rosapi_types(ws_manager)
            except Exception as e:
                detection_warning = (
                    f"ROS version detection failed: {e}. "
                    "Tools will assume ROS 2 type format (rosapi_msgs/srv/*)."
                )

        # Combine the results
        result: dict[str, Any] = {
            "message": f"WebSocket IP set to {actual_ip}:{actual_port}",
            "connectivity_test": ping_result,
        }
        if detection_warning:
            result["warning"] = detection_warning
        return result

    @mcp.tool(
        description=(
            "Ping one or more robot IP addresses and check if specific ports are open.\n"
            "A successful ping to the IP but not the port can indicate that ROSbridge is not running.\n"
            "Example:\n"
            "ping_robots(targets=[{'ip': '192.168.1.100', 'port': 9090}, {'ip': '192.168.1.101', 'port': 9090}])"
        ),
        annotations=ToolAnnotations(
            title="Ping Robots",
            readOnlyHint=True,
        ),
    )
    def ping_robots(
        targets: list[dict] = None,  # type: ignore[assignment]  # See issue #140
        ping_timeout: float = 2.0,
        port_timeout: float = 2.0,
    ) -> dict:
        """
        Ping one or more IP addresses and check if specific ports are open.

        Args:
            targets (list[dict]): List of target dictionaries, each containing:
                - ip (str): The IP address to ping (e.g., '192.168.1.100')
                - port (int): The port number to check (e.g., 9090)
            ping_timeout (float): Timeout for ping in seconds. Default = 2.0.
            port_timeout (float): Timeout for port check in seconds. Default = 2.0.

        Returns:
            dict: Contains a 'results' list with ping and port check results for each target.
        """
        # Set default value if targets is None
        if targets is None:
            targets = [{"ip": "127.0.0.1", "port": 9090}]

        # Validate targets is a non-empty list
        if not isinstance(targets, list):
            return {"error": "targets must be a list of dictionaries", "results": []}

        if len(targets) == 0:
            return {"error": "targets list cannot be empty", "results": []}

        # Pre-allocate results list to preserve input order
        results: list[Any] = [None] * len(targets)

        # Phase 1: Validate all targets and collect valid ones with their indices
        valid_targets = []  # List of (index, ip, port) tuples

        for i, target in enumerate(targets):
            # Validate target is a dictionary
            if not isinstance(target, dict):
                results[i] = {
                    "ip": None,
                    "port": None,
                    "error": f"Target at index {i} is not a dictionary",
                    "ping": {"success": False, "error": "Invalid target format"},
                    "port_check": {"open": False, "error": "Invalid target format"},
                    "overall_status": "Invalid target format",
                }
                continue

            # Validate required keys exist
            if "ip" not in target or "port" not in target:
                results[i] = {
                    "ip": target.get("ip", None),
                    "port": target.get("port", None),
                    "error": f"Target at index {i} missing required keys 'ip' or 'port'",
                    "ping": {"success": False, "error": "Missing required keys"},
                    "port_check": {"open": False, "error": "Missing required keys"},
                    "overall_status": "Invalid target format",
                }
                continue

            # Validate ip is a string and port is an integer
            ip = target["ip"]
            port = target["port"]

            if not isinstance(ip, str):
                results[i] = {
                    "ip": str(ip),
                    "port": port,
                    "error": f"Target at index {i}: 'ip' must be a string",
                    "ping": {"success": False, "error": "Invalid IP type"},
                    "port_check": {"open": False, "error": "Invalid IP type"},
                    "overall_status": "Invalid target format",
                }
                continue

            if not isinstance(port, int):
                try:
                    port = int(port)
                except (ValueError, TypeError):
                    results[i] = {
                        "ip": ip,
                        "port": port,
                        "error": f"Target at index {i}: 'port' must be an integer",
                        "ping": {"success": False, "error": "Invalid port type"},
                        "port_check": {"open": False, "error": "Invalid port type"},
                        "overall_status": "Invalid target format",
                    }
                    continue

            # Target is valid, add to list for parallel execution
            valid_targets.append((i, ip, port))

        # Phase 2: Execute pings in parallel for valid targets
        if valid_targets:
            max_workers = min(len(valid_targets), 20)
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                # Submit all ping tasks and create mapping
                future_to_info = {}
                for idx, ip, port in valid_targets:
                    future = executor.submit(ping_ip_and_port, ip, port, ping_timeout, port_timeout)
                    future_to_info[future] = (idx, ip, port)

                # Collect results as they complete
                for future in as_completed(future_to_info):
                    idx, ip, port = future_to_info[future]
                    try:
                        results[idx] = future.result()
                    except Exception as e:
                        # Handle exceptions from individual ping operations
                        results[idx] = {
                            "ip": ip,
                            "port": port,
                            "error": f"Exception during ping: {str(e)}",
                            "ping": {"success": False, "error": f"Exception: {str(e)}"},
                            "port_check": {"open": False, "error": f"Exception: {str(e)}"},
                            "overall_status": "Error during ping operation",
                        }

        return {"results": results}
