"""Integration tests for connection tools (step 1).

Detection logic is tested in test_detect_version.py (step 0).
These tests verify connectivity to the rosbridge container and
negative cases when no rosbridge is running.
"""

import pytest

from ros_mcp.utils.network_utils import ping_ip_and_port

pytestmark = [pytest.mark.integration]


class TestPingLocalhost:
    """Verify ping_ip_and_port against a live rosbridge and a closed port."""

    def test_rosbridge_port_open(self, ws):
        """Port 9090 should be open (rosbridge is running)."""
        result = ping_ip_and_port("127.0.0.1", 9090)
        assert result["port_check"]["open"] is True

    def test_closed_port(self, ws):
        """An unused port should report closed."""
        result = ping_ip_and_port("127.0.0.1", 19999, port_timeout=1.0)
        assert result["port_check"]["open"] is False

    def test_unreachable_host(self, ws):
        """A non-routable IP should fail both ping and port check."""
        result = ping_ip_and_port("192.0.2.1", 9090, ping_timeout=1.0, port_timeout=1.0)
        assert result["port_check"]["open"] is False
        assert result["ping"]["success"] is False
