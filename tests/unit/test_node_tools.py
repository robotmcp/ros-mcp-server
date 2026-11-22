"""Unit tests for ROS node tools (get_nodes, get_node_details).

Exercises node tools directly with fake MCP and WebSocketManager stand-ins,
requiring no running ROS environment or live rosbridge connection.
"""

from typing import Any

import pytest

from ros_mcp.tools.nodes import register_node_tools


class _FakeMcp:
    """Captures functions registered via the ``@mcp.tool(...)`` decorator."""

    def __init__(self) -> None:
        self.tools: dict[str, Any] = {}

    def tool(self, *args: Any, **kwargs: Any) -> Any:
        def decorator(fn: Any) -> Any:
            self.tools[fn.__name__] = fn
            return fn

        return decorator


class _FakeWsManager:
    """Minimal stand-in for WebSocketManager with a mock service response map."""

    def __init__(self, responses: dict[str, Any] | None = None) -> None:
        self.responses = responses or {}
        self.recorded_requests: list[dict[str, Any]] = []

    def __enter__(self) -> "_FakeWsManager":
        return self

    def __exit__(self, *exc: Any) -> bool:
        return False

    def request(self, message: dict[str, Any], timeout: float | None = None) -> dict[str, Any]:
        self.recorded_requests.append(message)
        service = message.get("service", "")
        # Lookup response by service path
        for key, resp in self.responses.items():
            if key in service:
                return resp
        return {}


def _setup_node_tools(
    responses: dict[str, Any] | None = None,
) -> tuple[dict[str, Any], _FakeWsManager]:
    mcp = _FakeMcp()
    ws = _FakeWsManager(responses)
    register_node_tools(mcp, ws)  # type: ignore[arg-type]
    return mcp.tools, ws


class TestGetNodeDetails:
    """Unit tests for get_node_details tool (including #273 crash prevention)."""

    @pytest.mark.parametrize("node_input", ["", "   ", "\t\n"])
    def test_empty_or_whitespace_node_name_returns_error(self, node_input: str) -> None:
        """Empty or whitespace-only string returns error without making any websocket requests."""
        tools, ws = _setup_node_tools()
        result = tools["get_node_details"](node=node_input)
        assert "error" in result
        assert "cannot be empty" in result["error"]
        assert len(ws.recorded_requests) == 0

    def test_nonexistent_node_does_not_call_node_details(self) -> None:
        """Regression test for #273: querying nonexistent node must return error

        without calling /rosapi/node_details, preventing upstream rosapi_node crash.
        """
        tools, ws = _setup_node_tools(
            {"nodes": {"result": True, "values": {"nodes": ["/turtlesim", "/rosapi"]}}}
        )
        result = tools["get_node_details"](node="/nonexistent")
        assert "error" in result
        assert "Node '/nonexistent' not found or is not running" in result["error"]
        # Must only call nodes check, NOT node_details
        assert len(ws.recorded_requests) == 1
        assert "nodes" in ws.recorded_requests[0].get("service", "")
        assert not any("node_details" in req.get("service", "") for req in ws.recorded_requests)

    def test_get_node_details_success(self) -> None:
        """Passing 'turtlesim' when '/turtlesim' is active resolves correctly and returns details."""
        tools, ws = _setup_node_tools(
            {
                "nodes": {"result": True, "values": {"nodes": ["/turtlesim"]}},
                "node_details": {
                    "result": True,
                    "values": {
                        "publishing": ["/turtle1/pose", "/turtle1/color_sensor"],
                        "subscribing": ["/turtle1/cmd_vel"],
                        "services": ["/reset", "/spawn", "/kill"],
                    },
                },
            }
        )
        result = tools["get_node_details"](node="turtlesim")
        assert result["node"] == "/turtlesim"
        assert result["publisher_count"] == 2
        assert result["subscriber_count"] == 1
        assert result["service_count"] == 3
        assert result["publishers"] == ["/turtle1/pose", "/turtle1/color_sensor"]
        assert result["subscribers"] == ["/turtle1/cmd_vel"]
        assert result["services"] == ["/reset", "/spawn", "/kill"]
        assert len(ws.recorded_requests) == 2

    @pytest.mark.parametrize("node_input", ["/turtlesim/", "turtlesim/"])
    def test_trailing_slash_normalization(self, node_input: str) -> None:
        """Trailing slashes (/turtlesim/ and turtlesim/) resolve to /turtlesim."""
        tools, ws = _setup_node_tools(
            {
                "nodes": {"result": True, "values": {"nodes": ["/turtlesim"]}},
                "node_details": {
                    "result": True,
                    "values": {
                        "publishing": ["/turtle1/pose"],
                        "subscribing": ["/turtle1/cmd_vel"],
                        "services": ["/reset"],
                    },
                },
            }
        )
        result = tools["get_node_details"](node=node_input)
        assert result["node"] == "/turtlesim"
        assert result["publisher_count"] == 1
        assert len(ws.recorded_requests) == 2

    def test_node_details_nodes_check_failure(self) -> None:
        """If active nodes query fails, returns error cleanly."""
        tools, ws = _setup_node_tools(
            {"nodes": {"result": False, "values": {"message": "Service unavailable"}}}
        )
        result = tools["get_node_details"](node="/turtlesim")
        assert "error" in result
        assert "Service unavailable" in result["error"]
        assert len(ws.recorded_requests) == 1

    def test_node_details_service_failure(self) -> None:
        """If node_details call fails after node check, returns error cleanly."""
        tools, ws = _setup_node_tools(
            {
                "nodes": {"result": True, "values": {"nodes": ["/turtlesim"]}},
                "node_details": {"result": False, "values": {"message": "Node details failed"}},
            }
        )
        result = tools["get_node_details"](node="/turtlesim")
        assert "error" in result
        assert "Node details failed" in result["error"]

    def test_node_with_no_details_available(self) -> None:
        """If node has empty publishers, subscribers, and services, returns error."""
        tools, ws = _setup_node_tools(
            {
                "nodes": {"result": True, "values": {"nodes": ["/empty_node"]}},
                "node_details": {
                    "result": True,
                    "values": {"publishing": [], "subscribing": [], "services": []},
                },
            }
        )
        result = tools["get_node_details"](node="/empty_node")
        assert "error" in result
        assert result["error"] == "Node /empty_node has no details available"
