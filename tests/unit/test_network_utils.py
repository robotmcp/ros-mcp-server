"""Unit tests for ros_mcp/utils/network_utils.py."""

import subprocess

import pytest

import ros_mcp.utils.network_utils as network_utils


@pytest.mark.parametrize(
    ("system", "expected_timeout"),
    [
        ("Linux", "2"),
        ("Darwin", "2000"),
        ("Windows", "2000"),
    ],
)
def test_ping_uses_platform_specific_timeout(monkeypatch, system, expected_timeout):
    """Use seconds on Linux and milliseconds on macOS and Windows."""
    monkeypatch.setattr(network_utils.platform, "system", lambda: system)

    commands = []

    def fake_run(command, **kwargs):
        commands.append(command)
        return subprocess.CompletedProcess(
            args=command,
            returncode=0,
            stdout="64 bytes from 127.0.0.1: icmp_seq=0 ttl=64 time=1.23 ms\n",
            stderr="",
        )

    monkeypatch.setattr(network_utils.subprocess, "run", fake_run)

    class FakeSocket:
        def settimeout(self, timeout):
            pass

        def connect_ex(self, address):
            return 0

        def close(self):
            pass

    monkeypatch.setattr(network_utils.socket, "socket", lambda *args, **kwargs: FakeSocket())

    result = network_utils.ping_ip_and_port("127.0.0.1", 9090, ping_timeout=2.0)
    expected_flag = "-n" if system == "Windows" else "-c"
    timeout_flag = "-w" if system == "Windows" else "-W"

    assert commands == [["ping", expected_flag, "1", timeout_flag, expected_timeout, "127.0.0.1"]]
    assert result["ping"]["success"] is True
    assert result["ping"]["response_time_ms"] == 1.23
    assert result["port_check"]["open"] is True
