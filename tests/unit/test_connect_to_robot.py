"""Unit tests for connect_to_robot registration."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

import ros_mcp.tools.connection as connection_mod
from ros_mcp.tools.connection import register_connection_tools


class _FakeMCP:
    def __init__(self) -> None:
        self.tools = {}

    def tool(self, *args, **kwargs):
        def deco(fn):
            self.tools[fn.__name__] = fn
            return fn

        return deco


def test_connect_to_robot_sets_ip_and_returns_ping(monkeypatch):
    mcp = _FakeMCP()
    ws = MagicMock()
    register_connection_tools(mcp, ws, default_ip="10.0.0.1", default_port=9090)
    connect = mcp.tools["connect_to_robot"]

    ping = {
        "ip": "192.168.1.5",
        "port": 9091,
        "ping": {"success": True},
        "port_check": {"open": True},
        "overall_status": "ok",
    }
    monkeypatch.setattr(connection_mod, "ping_ip_and_port", lambda *a, **k: ping)
    detect = MagicMock(return_value=SimpleNamespace())
    monkeypatch.setattr(connection_mod, "detect_rosapi_types", detect)

    result = connect(ip=" 192.168.1.5 ", port="9091", ping_timeout=1.0, port_timeout=1.0)

    ws.set_ip.assert_called_once_with("192.168.1.5", 9091)
    detect.assert_called_once_with(ws)
    assert result["message"] == "WebSocket IP set to 192.168.1.5:9091"
    assert result["connectivity_test"] is ping
    assert "warning" not in result


def test_connect_to_robot_detection_failure_sets_warning(monkeypatch):
    mcp = _FakeMCP()
    ws = MagicMock()
    register_connection_tools(mcp, ws, default_ip="127.0.0.1", default_port=9090)
    connect = mcp.tools["connect_to_robot"]

    monkeypatch.setattr(
        connection_mod,
        "ping_ip_and_port",
        lambda *a, **k: {"port_check": {"open": True}},
    )
    monkeypatch.setattr(
        connection_mod,
        "detect_rosapi_types",
        MagicMock(side_effect=RuntimeError("boom")),
    )

    result = connect()

    assert "warning" in result
    assert "ROS version detection failed" in result["warning"]
    assert "boom" in result["warning"]


def test_connect_to_robot_skips_detect_when_port_closed(monkeypatch):
    mcp = _FakeMCP()
    ws = MagicMock()
    register_connection_tools(mcp, ws, default_ip="127.0.0.1", default_port=9090)
    connect = mcp.tools["connect_to_robot"]

    monkeypatch.setattr(
        connection_mod,
        "ping_ip_and_port",
        lambda *a, **k: {"port_check": {"open": False}},
    )
    detect = MagicMock()
    monkeypatch.setattr(connection_mod, "detect_rosapi_types", detect)

    result = connect(ip=None, port=None)
    detect.assert_not_called()
    ws.set_ip.assert_called_once_with("127.0.0.1", 9090)
    assert "warning" not in result
