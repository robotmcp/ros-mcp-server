"""Unit tests for ros_mcp/utils/network_utils.py (pure DNS / mocked ping+port)."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

_PATH = Path(__file__).resolve().parents[2] / "ros_mcp" / "utils" / "network_utils.py"


def _load():
    spec = importlib.util.spec_from_file_location("ros_mcp_utils_network", _PATH)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def net():
    return _load()


class TestResolveDns:
    def test_already_ipv4(self, net):
        ok, ip, err = net._resolve_dns("127.0.0.1")
        assert ok is True
        assert ip == "127.0.0.1"
        assert err is None

    def test_dns_success(self, net):
        # getaddrinfo returns list of 5-tuples
        fake_info = [(2, 1, 6, "", ("93.184.216.34", 0))]
        with patch.object(net.socket, "getaddrinfo", return_value=fake_info):
            # force non-IP path: hostname that fails inet_aton
            ok, ip, err = net._resolve_dns("example.invalid.test")
            assert ok is True
            assert ip == "93.184.216.34"
            assert err is None

    def test_dns_failure(self, net):
        with patch.object(
            net.socket, "getaddrinfo", side_effect=net.socket.gaierror("boom")
        ):
            ok, ip, err = net._resolve_dns("does-not-resolve.example")
            assert ok is False
            assert ip is None
            assert err is not None
            assert "DNS resolution error" in err


class TestPingIpAndPort:
    def test_dns_fail_fast(self, net):
        with patch.object(net, "_resolve_dns", return_value=(False, None, "bad host")):
            result = net.ping_ip_and_port("badhost", 9090)
            assert result["ping"]["error"] == "bad host"
            assert result["port_check"]["error"] == "bad host"
            assert "DNS_resolution_failed" in result["overall_status"]

    def test_fully_accessible(self, net):
        with (
            patch.object(net, "_resolve_dns", return_value=(True, "10.0.0.5", None)),
            patch.object(net.subprocess, "run") as run_mock,
            patch.object(net.socket, "socket") as sock_cls,
        ):
            run_mock.return_value = MagicMock(
                returncode=0, stdout="64 bytes from 10.0.0.5: icmp_seq=0 time=1.2 ms\n"
            )
            sock = MagicMock()
            sock.connect_ex.return_value = 0
            sock_cls.return_value = sock

            result = net.ping_ip_and_port("robot", 9090)
            assert result["ping"]["success"] is True
            assert result["ping"]["response_time_ms"] == 1.2
            assert result["port_check"]["open"] is True
            assert result["overall_status"].startswith("Fully_accessible")

    def test_port_closed(self, net):
        with (
            patch.object(net, "_resolve_dns", return_value=(True, "10.0.0.5", None)),
            patch.object(net.subprocess, "run") as run_mock,
            patch.object(net.socket, "socket") as sock_cls,
        ):
            run_mock.return_value = MagicMock(returncode=0, stdout="time=2 ms")
            sock = MagicMock()
            sock.connect_ex.return_value = 111
            sock_cls.return_value = sock
            result = net.ping_ip_and_port("robot", 9090)
            assert result["ping"]["success"] is True
            assert result["port_check"]["open"] is False
            assert "IP_reachable_port_closed" in result["overall_status"]
