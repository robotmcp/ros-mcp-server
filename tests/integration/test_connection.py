"""Integration tests for connection tools (step 1).

Detection logic is tested in test_detect_version.py (step 0).
This test verifies connectivity to the rosbridge container.
"""

import pytest

from ros_mcp.utils.network_utils import ping_ip_and_port

pytestmark = [pytest.mark.integration]


class TestPingLocalhost:
    def test_rosbridge_port_open(self, ws):
        """Port 9090 should be open (rosbridge is running)."""
        result = ping_ip_and_port("127.0.0.1", 9090)
        assert result["port_open"] is True
