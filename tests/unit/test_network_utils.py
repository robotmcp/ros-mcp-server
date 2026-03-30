"""Unit tests for ros_mcp/utils/network_utils.py.

All network operations (socket, subprocess) are mocked — no real connections needed.
"""

import socket
from unittest.mock import MagicMock, patch

from ros_mcp.utils.network_utils import _resolve_dns, ping_ip_and_port

# ---------------------------------------------------------------------------
# _resolve_dns
# ---------------------------------------------------------------------------


class TestResolveDns:
    def test_ip_address_returns_immediately(self):
        """An IP address should be returned as-is without DNS lookup."""
        success, ip, error = _resolve_dns("127.0.0.1")
        assert success is True
        assert ip == "127.0.0.1"
        assert error is None

    def test_another_ip_address(self):
        success, ip, error = _resolve_dns("192.168.1.100")
        assert success is True
        assert ip == "192.168.1.100"
        assert error is None

    @patch("ros_mcp.utils.network_utils.socket.getaddrinfo")
    def test_hostname_resolves_successfully(self, mock_getaddrinfo):
        mock_getaddrinfo.return_value = [
            (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("10.0.0.1", 0))
        ]
        success, ip, error = _resolve_dns("my-robot.local")
        assert success is True
        assert ip == "10.0.0.1"
        assert error is None

    @patch("ros_mcp.utils.network_utils.socket.getaddrinfo")
    def test_hostname_resolution_fails(self, mock_getaddrinfo):
        mock_getaddrinfo.side_effect = socket.gaierror("Name resolution failed")
        success, ip, error = _resolve_dns("unknown-host")
        assert success is False
        assert ip is None
        assert "DNS resolution error" in error

    @patch("ros_mcp.utils.network_utils.socket.getaddrinfo")
    def test_empty_resolution_result(self, mock_getaddrinfo):
        mock_getaddrinfo.return_value = []
        success, ip, error = _resolve_dns("empty-result.local")
        assert success is False
        assert ip is None
        assert "no results" in error


# ---------------------------------------------------------------------------
# ping_ip_and_port
# ---------------------------------------------------------------------------


class TestPingIpAndPort:
    @patch("ros_mcp.utils.network_utils.socket.socket")
    @patch("ros_mcp.utils.network_utils.subprocess.run")
    @patch("ros_mcp.utils.network_utils._resolve_dns")
    def test_fully_accessible(self, mock_dns, mock_subprocess, mock_socket_cls):
        mock_dns.return_value = (True, "192.168.1.10", None)
        mock_subprocess.return_value = MagicMock(
            returncode=0, stdout="64 bytes from 192.168.1.10: time=1.23 ms"
        )
        mock_sock = MagicMock()
        mock_sock.connect_ex.return_value = 0
        mock_socket_cls.return_value = mock_sock

        result = ping_ip_and_port("192.168.1.10", 9090)
        assert result["ping"]["success"] is True
        assert result["port_check"]["open"] is True
        assert "Fully_accessible" in result["overall_status"]

    @patch("ros_mcp.utils.network_utils.socket.socket")
    @patch("ros_mcp.utils.network_utils.subprocess.run")
    @patch("ros_mcp.utils.network_utils._resolve_dns")
    def test_ip_reachable_port_closed(self, mock_dns, mock_subprocess, mock_socket_cls):
        mock_dns.return_value = (True, "192.168.1.10", None)
        mock_subprocess.return_value = MagicMock(
            returncode=0, stdout="64 bytes from 192.168.1.10: time=0.5 ms"
        )
        mock_sock = MagicMock()
        mock_sock.connect_ex.return_value = 111  # Connection refused
        mock_socket_cls.return_value = mock_sock

        result = ping_ip_and_port("192.168.1.10", 9090)
        assert result["ping"]["success"] is True
        assert result["port_check"]["open"] is False
        assert "port_closed" in result["overall_status"]

    @patch("ros_mcp.utils.network_utils._resolve_dns")
    def test_dns_failure_returns_early(self, mock_dns):
        mock_dns.return_value = (False, None, "DNS resolution error: Name not found")

        result = ping_ip_and_port("bad-hostname", 9090)
        assert result["ping"]["success"] is False
        assert result["port_check"]["open"] is False
        assert "DNS_resolution_failed" in result["overall_status"]

    @patch("ros_mcp.utils.network_utils.socket.socket")
    @patch("ros_mcp.utils.network_utils.subprocess.run")
    @patch("ros_mcp.utils.network_utils._resolve_dns")
    def test_both_unreachable(self, mock_dns, mock_subprocess, mock_socket_cls):
        mock_dns.return_value = (True, "10.0.0.99", None)
        mock_subprocess.return_value = MagicMock(returncode=1, stdout="")
        mock_sock = MagicMock()
        mock_sock.connect_ex.return_value = 111
        mock_socket_cls.return_value = mock_sock

        result = ping_ip_and_port("10.0.0.99", 9090)
        assert result["ping"]["success"] is False
        assert result["port_check"]["open"] is False
        assert "IP_unreachable" in result["overall_status"]

    @patch("ros_mcp.utils.network_utils.socket.socket")
    @patch("ros_mcp.utils.network_utils.subprocess.run")
    @patch("ros_mcp.utils.network_utils._resolve_dns")
    def test_ping_timeout(self, mock_dns, mock_subprocess, mock_socket_cls):
        import subprocess

        mock_dns.return_value = (True, "10.0.0.1", None)
        mock_subprocess.side_effect = subprocess.TimeoutExpired(cmd="ping", timeout=2.0)
        mock_sock = MagicMock()
        mock_sock.connect_ex.return_value = 0
        mock_socket_cls.return_value = mock_sock

        result = ping_ip_and_port("10.0.0.1", 9090, ping_timeout=2.0)
        assert result["ping"]["success"] is False
        assert "timeout" in result["ping"]["error"].lower()
        assert result["port_check"]["open"] is True

    @patch("ros_mcp.utils.network_utils.socket.socket")
    @patch("ros_mcp.utils.network_utils.subprocess.run")
    @patch("ros_mcp.utils.network_utils._resolve_dns")
    def test_response_time_extracted(self, mock_dns, mock_subprocess, mock_socket_cls):
        mock_dns.return_value = (True, "127.0.0.1", None)
        mock_subprocess.return_value = MagicMock(
            returncode=0,
            stdout="PING 127.0.0.1: 56 data bytes\n64 bytes from 127.0.0.1: time=0.045 ms\n",
        )
        mock_sock = MagicMock()
        mock_sock.connect_ex.return_value = 0
        mock_socket_cls.return_value = mock_sock

        result = ping_ip_and_port("127.0.0.1", 9090)
        assert result["ping"]["response_time_ms"] == 0.045

    @patch("ros_mcp.utils.network_utils.socket.socket")
    @patch("ros_mcp.utils.network_utils.subprocess.run")
    @patch("ros_mcp.utils.network_utils._resolve_dns")
    def test_ip_unreachable_port_open(self, mock_dns, mock_subprocess, mock_socket_cls):
        """Unusual case: ping fails but port is open."""
        mock_dns.return_value = (True, "10.0.0.1", None)
        mock_subprocess.return_value = MagicMock(returncode=1, stdout="")
        mock_sock = MagicMock()
        mock_sock.connect_ex.return_value = 0
        mock_socket_cls.return_value = mock_sock

        result = ping_ip_and_port("10.0.0.1", 9090)
        assert result["ping"]["success"] is False
        assert result["port_check"]["open"] is True
        assert "IP_unreachable_port_open" in result["overall_status"]

    @patch("ros_mcp.utils.network_utils.socket.socket")
    @patch("ros_mcp.utils.network_utils.subprocess.run")
    @patch("ros_mcp.utils.network_utils._resolve_dns")
    def test_port_timeout(self, mock_dns, mock_subprocess, mock_socket_cls):
        mock_dns.return_value = (True, "10.0.0.1", None)
        mock_subprocess.return_value = MagicMock(returncode=0, stdout="time=1.0 ms")
        mock_sock = MagicMock()
        mock_sock.connect_ex.side_effect = socket.timeout("timed out")
        mock_socket_cls.return_value = mock_sock

        result = ping_ip_and_port("10.0.0.1", 9090)
        assert result["ping"]["success"] is True
        assert result["port_check"]["open"] is False
        assert "timeout" in result["port_check"]["error"].lower()

    @patch("ros_mcp.utils.network_utils.socket.socket")
    @patch("ros_mcp.utils.network_utils.subprocess.run")
    @patch("ros_mcp.utils.network_utils._resolve_dns")
    def test_ping_command_not_found(self, mock_dns, mock_subprocess, mock_socket_cls):
        mock_dns.return_value = (True, "10.0.0.1", None)
        mock_subprocess.side_effect = FileNotFoundError("ping not found")
        mock_sock = MagicMock()
        mock_sock.connect_ex.return_value = 0
        mock_socket_cls.return_value = mock_sock

        result = ping_ip_and_port("10.0.0.1", 9090)
        assert result["ping"]["success"] is False
        assert "not found" in result["ping"]["error"].lower()
        assert result["port_check"]["open"] is True

    def test_result_structure(self):
        """Verify the returned dict always has the expected shape."""
        with patch("ros_mcp.utils.network_utils._resolve_dns") as mock_dns:
            mock_dns.return_value = (False, None, "DNS error")
            result = ping_ip_and_port("x", 80)

        assert "ip" in result
        assert "port" in result
        assert "ping" in result
        assert "port_check" in result
        assert "overall_status" in result
        assert "success" in result["ping"]
        assert "open" in result["port_check"]
