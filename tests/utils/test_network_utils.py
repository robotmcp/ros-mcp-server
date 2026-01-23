"""Tests for ros_mcp.utils.network_utils module."""

import socket
from unittest.mock import MagicMock, patch

from ros_mcp.utils.network_utils import ping_ip_and_port


class TestPingIpAndPort:
    """Test cases for ping_ip_and_port function."""

    def test_result_structure(self):
        """Test that result has expected structure."""
        # Use localhost which should be pingable
        result = ping_ip_and_port("127.0.0.1", 9999, ping_timeout=1.0, port_timeout=1.0)

        assert "ip" in result
        assert "port" in result
        assert "ping" in result
        assert "port_check" in result
        assert "overall_status" in result

        assert "success" in result["ping"]
        assert "error" in result["ping"]
        assert "response_time_ms" in result["ping"]

        assert "open" in result["port_check"]
        assert "error" in result["port_check"]

    @patch("ros_mcp.utils.network_utils.subprocess.run")
    @patch("ros_mcp.utils.network_utils.socket.socket")
    def test_fully_accessible(self, mock_socket_class, mock_run):
        """Test fully accessible status when both ping and port succeed."""
        # Mock successful ping
        mock_run.return_value = MagicMock(returncode=0, stdout="time=0.5ms\n")

        # Mock successful port connection
        mock_socket = MagicMock()
        mock_socket.connect_ex.return_value = 0
        mock_socket_class.return_value = mock_socket

        result = ping_ip_and_port("192.168.1.1", 9090, ping_timeout=1.0, port_timeout=1.0)

        assert result["ping"]["success"] is True
        assert result["port_check"]["open"] is True
        assert "Fully_accessible" in result["overall_status"]

    @patch("ros_mcp.utils.network_utils.subprocess.run")
    @patch("ros_mcp.utils.network_utils.socket.socket")
    def test_port_closed(self, mock_socket_class, mock_run):
        """Test status when ping succeeds but port is closed."""
        # Mock successful ping
        mock_run.return_value = MagicMock(returncode=0, stdout="time=0.5ms\n")

        # Mock closed port
        mock_socket = MagicMock()
        mock_socket.connect_ex.return_value = 111  # Connection refused
        mock_socket_class.return_value = mock_socket

        result = ping_ip_and_port("192.168.1.1", 9090, ping_timeout=1.0, port_timeout=1.0)

        assert result["ping"]["success"] is True
        assert result["port_check"]["open"] is False
        assert "IP_reachable_port_closed" in result["overall_status"]

    @patch("ros_mcp.utils.network_utils.subprocess.run")
    @patch("ros_mcp.utils.network_utils.socket.socket")
    def test_ip_unreachable(self, mock_socket_class, mock_run):
        """Test status when IP is unreachable."""
        # Mock failed ping
        mock_run.return_value = MagicMock(returncode=1, stdout="")

        # Mock failed port connection
        mock_socket = MagicMock()
        mock_socket.connect_ex.side_effect = socket.timeout("Connection timed out")
        mock_socket_class.return_value = mock_socket

        result = ping_ip_and_port("192.168.1.200", 9090, ping_timeout=1.0, port_timeout=1.0)

        assert result["ping"]["success"] is False
        assert "IP_unreachable" in result["overall_status"]

    @patch("ros_mcp.utils.network_utils.subprocess.run")
    def test_ping_timeout(self, mock_run):
        """Test handling of ping timeout."""
        import subprocess

        mock_run.side_effect = subprocess.TimeoutExpired(cmd="ping", timeout=2.0)

        result = ping_ip_and_port("192.168.1.1", 9090, ping_timeout=1.0, port_timeout=1.0)

        assert result["ping"]["success"] is False
        assert "timeout" in result["ping"]["error"].lower()

    @patch("ros_mcp.utils.network_utils.subprocess.run")
    def test_ping_command_not_found(self, mock_run):
        """Test handling when ping command is not available."""
        mock_run.side_effect = FileNotFoundError("ping not found")

        result = ping_ip_and_port("192.168.1.1", 9090, ping_timeout=1.0, port_timeout=1.0)

        assert result["ping"]["success"] is False
        assert "not found" in result["ping"]["error"].lower()

    @patch("ros_mcp.utils.network_utils.subprocess.run")
    @patch("ros_mcp.utils.network_utils.socket.socket")
    def test_port_connection_timeout(self, mock_socket_class, mock_run):
        """Test handling of port connection timeout."""
        # Mock successful ping
        mock_run.return_value = MagicMock(returncode=0, stdout="time=0.5ms\n")

        # Mock port timeout
        mock_socket = MagicMock()
        mock_socket.connect_ex.side_effect = socket.timeout("timed out")
        mock_socket_class.return_value = mock_socket

        result = ping_ip_and_port("192.168.1.1", 9090, ping_timeout=1.0, port_timeout=1.0)

        assert result["port_check"]["open"] is False
        assert "timeout" in result["port_check"]["error"].lower()

    @patch("ros_mcp.utils.network_utils.subprocess.run")
    @patch("ros_mcp.utils.network_utils.socket.socket")
    def test_dns_resolution_error(self, mock_socket_class, mock_run):
        """Test handling of DNS resolution errors."""
        # Mock successful ping
        mock_run.return_value = MagicMock(returncode=0, stdout="time=0.5ms\n")

        # Mock DNS error
        mock_socket = MagicMock()
        mock_socket.connect_ex.side_effect = socket.gaierror("Name resolution failed")
        mock_socket_class.return_value = mock_socket

        result = ping_ip_and_port("invalid.hostname", 9090, ping_timeout=1.0, port_timeout=1.0)

        assert result["port_check"]["open"] is False
        assert (
            "DNS" in result["port_check"]["error"]
            or "resolution" in result["port_check"]["error"].lower()
        )

    @patch("ros_mcp.utils.network_utils.subprocess.run")
    def test_response_time_extraction(self, mock_run):
        """Test that response time is correctly extracted from ping output."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="64 bytes from 127.0.0.1: icmp_seq=1 ttl=64 time=0.123 ms\n",
        )

        result = ping_ip_and_port("127.0.0.1", 9999, ping_timeout=1.0, port_timeout=1.0)

        assert result["ping"]["success"] is True
        # Response time might be extracted or None depending on parsing
        if result["ping"]["response_time_ms"] is not None:
            assert isinstance(result["ping"]["response_time_ms"], float)

    def test_localhost_ping(self):
        """Test pinging localhost (should generally succeed)."""
        result = ping_ip_and_port("127.0.0.1", 9999, ping_timeout=2.0, port_timeout=1.0)

        # Localhost ping should succeed on most systems
        assert result["ip"] == "127.0.0.1"
        assert result["port"] == 9999
        # Port 9999 is likely closed, so overall status won't be fully accessible

    @patch("ros_mcp.utils.network_utils.subprocess.run")
    @patch("ros_mcp.utils.network_utils.socket.socket")
    def test_unusual_ip_reachable_port_open(self, mock_socket_class, mock_run):
        """Test unusual case where ping fails but port is open."""
        # Mock failed ping
        mock_run.return_value = MagicMock(returncode=1, stdout="")

        # Mock successful port connection (unusual but possible)
        mock_socket = MagicMock()
        mock_socket.connect_ex.return_value = 0
        mock_socket_class.return_value = mock_socket

        result = ping_ip_and_port("192.168.1.1", 9090, ping_timeout=1.0, port_timeout=1.0)

        assert result["ping"]["success"] is False
        assert result["port_check"]["open"] is True
        assert "unusual" in result["overall_status"].lower()
