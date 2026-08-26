"""Unit tests for ros_mcp/utils/network_utils.py."""

from unittest.mock import MagicMock, patch

from ros_mcp.utils.network_utils import _parse_ping_time_ms, ping_ip_and_port

# ---------------------------------------------------------------------------
# Ping output captured verbatim from each platform, used as parser input.
# ---------------------------------------------------------------------------

WINDOWS_SUB_MILLISECOND = """
Pinging 127.0.0.1 with 32 bytes of data:
Reply from 127.0.0.1: bytes=32 time<1ms TTL=128

Ping statistics for 127.0.0.1:
    Packets: Sent = 1, Received = 1, Lost = 0 (0% loss),
Approximate round trip times in milli-seconds:
    Minimum = 0ms, Maximum = 0ms, Average = 0ms
"""

WINDOWS_INTEGER_MILLISECONDS = """
Pinging 8.8.8.8 with 32 bytes of data:
Reply from 8.8.8.8: bytes=32 time=9ms TTL=115

Ping statistics for 8.8.8.8:
    Packets: Sent = 1, Received = 1, Lost = 0 (0% loss),
Approximate round trip times in milli-seconds:
    Minimum = 9ms, Maximum = 9ms, Average = 9ms
"""

LINUX_FRACTIONAL_MILLISECONDS = """PING 127.0.0.1 (127.0.0.1) 56(84) bytes of data.
64 bytes from 127.0.0.1: icmp_seq=1 ttl=64 time=0.057 ms

--- 127.0.0.1 ping statistics ---
1 packets transmitted, 1 received, 0% packet loss, time 0ms
rtt min/avg/max/mdev = 0.057/0.057/0.057/0.000 ms
"""

WINDOWS_TIMED_OUT = """
Pinging 192.168.223.254 with 32 bytes of data:
Request timed out.

Ping statistics for 192.168.223.254:
    Packets: Sent = 1, Received = 0, Lost = 1 (100% loss),
"""


# ---------------------------------------------------------------------------
# _parse_ping_time_ms — pure parser, exercised against every output format
# ---------------------------------------------------------------------------


class TestParsePingTimeMs:
    def test_windows_sub_millisecond_reply(self):
        # Windows prints "time<1ms"; 1.0 is the tightest bound ping gives us.
        assert _parse_ping_time_ms(WINDOWS_SUB_MILLISECOND) == 1.0

    def test_windows_integer_milliseconds(self):
        # Windows prints no space before the unit ("time=9ms").
        assert _parse_ping_time_ms(WINDOWS_INTEGER_MILLISECONDS) == 9.0

    def test_linux_fractional_milliseconds(self):
        # Linux prints a space before the unit ("time=0.057 ms").
        assert _parse_ping_time_ms(LINUX_FRACTIONAL_MILLISECONDS) == 0.057

    def test_linux_summary_line_is_not_read_as_a_reply(self):
        # The Linux summary carries "time 0ms" (elapsed run time, not an RTT).
        summary = "1 packets transmitted, 1 received, 0% packet loss, time 0ms\n"
        assert _parse_ping_time_ms(summary) is None

    def test_timed_out_output_returns_none(self):
        assert _parse_ping_time_ms(WINDOWS_TIMED_OUT) is None

    def test_empty_output_returns_none(self):
        assert _parse_ping_time_ms("") is None


# ---------------------------------------------------------------------------
# ping_ip_and_port — response_time_ms is populated on every platform
# ---------------------------------------------------------------------------


class TestPingIpAndPortResponseTime:
    @staticmethod
    def _ping_with_stdout(stdout: str, returncode: int = 0) -> dict:
        """Run ping_ip_and_port with the ping command and socket both stubbed."""
        with (
            patch("ros_mcp.utils.network_utils.subprocess.run") as run_mock,
            patch("ros_mcp.utils.network_utils.socket.socket") as socket_mock,
        ):
            run_mock.return_value = MagicMock(returncode=returncode, stdout=stdout)
            socket_mock.return_value.connect_ex.return_value = 0
            return ping_ip_and_port("127.0.0.1", 9090)

    def test_windows_reply_reports_response_time(self):
        result = self._ping_with_stdout(WINDOWS_INTEGER_MILLISECONDS)
        assert result["ping"]["success"] is True
        assert result["ping"]["response_time_ms"] == 9.0

    def test_linux_reply_reports_response_time(self):
        result = self._ping_with_stdout(LINUX_FRACTIONAL_MILLISECONDS)
        assert result["ping"]["success"] is True
        assert result["ping"]["response_time_ms"] == 0.057

    def test_failed_ping_leaves_response_time_unset(self):
        result = self._ping_with_stdout(WINDOWS_TIMED_OUT, returncode=1)
        assert result["ping"]["success"] is False
        assert result["ping"]["response_time_ms"] is None
