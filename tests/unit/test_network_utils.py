"""Unit tests for ros_mcp/utils/network_utils.py."""

import subprocess

import pytest

import ros_mcp.utils.network_utils as network_utils


@pytest.mark.parametrize(
    ("system", "ping_timeout", "expected_timeout", "stdout", "expected_response_time"),
    [
        (
            "Linux",
            2.0,
            "2",
            "64 bytes from 127.0.0.1: icmp_seq=0 ttl=64 time=1.23 ms\n",
            1.23,
        ),
        (
            "Linux",
            0.5,
            "0.5",
            "64 bytes from 127.0.0.1: icmp_seq=0 ttl=64 time=0.50 ms\n",
            0.50,
        ),
        (
            "Darwin",
            2.0,
            "2000",
            "64 bytes from 127.0.0.1: icmp_seq=0 ttl=64 time=1.23 ms\n",
            1.23,
        ),
        (
            "Darwin",
            0.5,
            "500",
            "64 bytes from 127.0.0.1: icmp_seq=0 ttl=64 time=0.50 ms\n",
            0.50,
        ),
        (
            "FreeBSD",
            2.0,
            "2000",
            "64 bytes from 127.0.0.1: icmp_seq=0 ttl=64 time=1.23 ms\n",
            1.23,
        ),
        (
            "FreeBSD",
            0.5,
            "500",
            "64 bytes from 127.0.0.1: icmp_seq=0 ttl=64 time=0.50 ms\n",
            0.50,
        ),
        (
            "Windows",
            2.0,
            "2000",
            "Reply from 127.0.0.1: bytes=32 time=24ms TTL=128\n",
            24.0,
        ),
        (
            "Windows",
            0.5,
            "500",
            "Reply from 127.0.0.1: bytes=32 time<1ms TTL=128\n",
            1.0,
        ),
    ],
)
def test_ping_uses_platform_specific_timeout(
    monkeypatch, system, ping_timeout, expected_timeout, stdout, expected_response_time
):
    """Use seconds on Linux and milliseconds on macOS, BSD, and Windows."""
    monkeypatch.setattr(network_utils.platform, "system", lambda: system)

    commands = []

    def fake_run(command, **kwargs):
        commands.append(command)
        return subprocess.CompletedProcess(
            args=command,
            returncode=0,
            stdout=stdout,
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

    result = network_utils.ping_ip_and_port("127.0.0.1", 9090, ping_timeout=ping_timeout)
    expected_flag = "-n" if system == "Windows" else "-c"
    timeout_flag = "-w" if system == "Windows" else "-W"

    assert commands == [["ping", expected_flag, "1", timeout_flag, expected_timeout, "127.0.0.1"]]
    assert result["ping"]["success"] is True
    assert result["ping"]["response_time_ms"] == expected_response_time
    assert result["port_check"]["open"] is True


@pytest.mark.parametrize("invalid_timeout", [0, -1.0, -0.001])
def test_ping_rejects_non_positive_timeout(invalid_timeout):
    result = network_utils.ping_ip_and_port("127.0.0.1", 9090, ping_timeout=invalid_timeout)
    assert result["ping"]["success"] is False
    assert result["ping"]["error"] == "ping_timeout must be greater than 0"
    assert result["overall_status"] == "Invalid_parameters"


@pytest.mark.parametrize("invalid_timeout", [0, -1.0, -0.001])
def test_ping_rejects_non_positive_port_timeout(invalid_timeout):
    result = network_utils.ping_ip_and_port("127.0.0.1", 9090, port_timeout=invalid_timeout)
    assert result["port_check"]["open"] is False
    assert result["port_check"]["error"] == "port_timeout must be greater than 0"
    assert result["overall_status"] == "Invalid_parameters"
