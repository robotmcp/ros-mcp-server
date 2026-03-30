import platform
import socket
import subprocess
from typing import Dict, Tuple


def _resolve_dns(hostname: str) -> Tuple[bool, str | None, str | None]:
    """
    Resolve hostname to IP address.

    Args:
        hostname: The hostname or IP address to resolve

    Returns:
        Tuple of (success: bool, resolved_ip: str | None, error: str | None)
        - If hostname is already an IP address, returns immediately with success=True
        - If DNS resolution succeeds, returns (True, resolved_ip, None)
        - If DNS resolution fails, returns (False, None, error_message)
    """
    # Check if already an IP address
    try:
        socket.inet_aton(hostname)
        return (True, hostname, None)  # Already an IP, no DNS needed
    except (socket.error, OSError):
        pass  # Not an IP, need DNS resolution

    # Try to resolve DNS
    try:
        addr_info = socket.getaddrinfo(hostname, None, socket.AF_INET, socket.SOCK_STREAM)
        if addr_info:
            # Extract IP address from the first result and ensure it's a string
            resolved_ip = str(addr_info[0][4][0])
            return (True, resolved_ip, None)
        else:
            return (False, None, "DNS resolution returned no results")
    except socket.gaierror as e:
        return (False, None, f"DNS resolution error: {str(e)}")
    except Exception as e:
        return (False, None, f"DNS resolution error: {str(e)}")


def ping_ip_and_port(
    ip: str, port: int, ping_timeout: float = 2.0, port_timeout: float = 2.0
) -> Dict:
    """
    Ping an IP address and check if a specific port is open.

    Args:
        ip (str): The IP address or hostname to ping (e.g., '192.168.1.100' or 'duck7')
        port (int): The port number to check (e.g., 9090)
        ping_timeout (float): Timeout for ping in seconds. Default = 2.0.
        port_timeout (float): Timeout for port check in seconds. Default = 2.0.

    Returns:
        dict: Contains ping and port check results with detailed status information.
    """
    result = {
        "ip": ip,
        "port": port,
        "ping": {"success": False, "error": None, "response_time_ms": None},
        "port_check": {"open": False, "error": None},
        "overall_status": "unknown",
    }

    # Step 0: DNS Resolution (do this FIRST)
    dns_success, resolved_ip, dns_error = _resolve_dns(ip)
    if not dns_success:
        # Fail fast - return early with DNS error
        result["ping"]["error"] = dns_error
        result["port_check"]["error"] = dns_error
        result["overall_status"] = (
            "DNS_resolution_failed. Check if the hostname is correct and DNS is configured properly."
        )
        return result

    # Use resolved IP for subsequent operations
    actual_ip = resolved_ip

    # Step 1: Ping the IP address
    try:
        # Use platform-specific ping command
        if platform.system().lower() == "windows":
            ping_cmd = ["ping", "-n", "1", "-w", str(int(ping_timeout * 1000)), actual_ip]
        else:  # Linux, macOS, etc.
            ping_cmd = ["ping", "-c", "1", "-W", str(int(ping_timeout)), actual_ip]

        ping_result = subprocess.run(
            ping_cmd, capture_output=True, text=True, timeout=ping_timeout + 1.0
        )

        if ping_result.returncode == 0:
            # Extract response time from ping output
            output_lines = ping_result.stdout.split("\n")
            for line in output_lines:
                if "time=" in line or "time<" in line:
                    # Extract time value (format varies by OS)
                    if "time=" in line:
                        time_part = line.split("time=")[1].split()[0]
                        try:
                            result["ping"]["response_time_ms"] = float(time_part)
                        except ValueError:
                            result["ping"]["response_time_ms"] = None
                    break

            result["ping"]["success"] = True
        else:
            result["ping"]["error"] = f"Ping failed with return code {ping_result.returncode}"

    except subprocess.TimeoutExpired:
        result["ping"]["error"] = f"Ping timeout after {ping_timeout} seconds"
    except FileNotFoundError:
        result["ping"]["error"] = "Ping command not found on this system"
    except Exception as e:
        result["ping"]["error"] = f"Ping error: {str(e)}"

    # Step 2: Check if port is open
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(port_timeout)

        port_result = sock.connect_ex((actual_ip, port))
        sock.close()

        if port_result == 0:
            result["port_check"]["open"] = True
        else:
            result["port_check"]["error"] = (
                f"Port {port} is closed or unreachable (error code: {port_result})"
            )

    except socket.timeout:
        result["port_check"]["error"] = (
            f"Port {port} connection timeout after {port_timeout} seconds"
        )
    except socket.gaierror as e:
        result["port_check"]["error"] = f"DNS resolution error: {str(e)}"
    except Exception as e:
        result["port_check"]["error"] = f"Port check error: {str(e)}"

    # Step 3: Determine overall status
    ping_success = result["ping"]["success"]
    port_open = result["port_check"]["open"]

    if ping_success and port_open:
        result["overall_status"] = (
            "Fully_accessible. The robot is reachable and the port is open, indicating that we are likely able to connect to ROS"
        )
    elif ping_success and not port_open:
        result["overall_status"] = (
            "IP_reachable_port_closed. The robot is reachable but ROS_bridge is unreachable. Check if ROS_bridge is running as well as firewall settings."
        )
    elif not ping_success and port_open:
        result["overall_status"] = (
            "IP_unreachable_port_open. This is unusual."  # Unusual but possible
        )
    else:
        result["overall_status"] = (
            "IP_unreachable. Check if the IP address is correct, the robot is powered on & connected to the network. Also check network and firewall settings."
        )

    return result
