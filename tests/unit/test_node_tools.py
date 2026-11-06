"""Unit tests for ROS node tools (get_nodes, get_node_details).

Exercises node tools directly with fake MCP and WebSocketManager stand-ins,
requiring no running ROS environment or live rosbridge connection.
"""

from typing import Any

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


class TestGetNodes:
    """Unit tests for get_nodes tool."""

    def test_get_nodes_success(self) -> None:
        """Verify get_nodes returns node list and correct count."""
        tools, _ = _setup_node_tools(
            {"nodes": {"result": True, "values": {"nodes": ["/turtlesim", "/rosbridge_websocket"]}}}
        )
        result = tools["get_nodes"]()
        assert "nodes" in result
        assert result["nodes"] == ["/turtlesim", "/rosbridge_websocket"]
        assert result["node_count"] == 2

    def test_get_nodes_service_error(self) -> None:
        """Verify get_nodes returns error when service returns failure."""
        tools, _ = _setup_node_tools(
            {"nodes": {"result": False, "values": {"message": "Service unavailable"}}}
        )
        result = tools["get_nodes"]()
        assert "error" in result
        assert "Service unavailable" in result["error"]

    def test_get_nodes_empty_list(self) -> None:
        """Verify get_nodes returns empty list and 0 count when nodes list is empty."""
        tools, _ = _setup_node_tools({"nodes": {"result": True, "values": {"nodes": []}}})
        result = tools["get_nodes"]()
        assert result["nodes"] == []
        assert result["node_count"] == 0

    def test_get_nodes_no_values_warning(self) -> None:
        """Verify warning returned when response has no values dict."""
        tools, _ = _setup_node_tools({"nodes": {"result": True}})
        result = tools["get_nodes"]()
        assert "warning" in result


class TestGetNodeDetails:
    """Unit tests for get_node_details tool (including #273 crash prevention)."""

    def test_empty_node_name_returns_error(self) -> None:
        """Empty string returns error without making any websocket requests."""
        tools, ws = _setup_node_tools()
        result = tools["get_node_details"](node="")
        assert "error" in result
        assert "cannot be empty" in result["error"]
        assert len(ws.recorded_requests) == 0

    def test_whitespace_node_name_returns_error(self) -> None:
        """Whitespace-only string returns error without making any requests."""
        tools, ws = _setup_node_tools()
        result = tools["get_node_details"](node="   ")
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

    def test_node_name_auto_prefixes_slash(self) -> None:
        """Passing 'turtlesim' when '/turtlesim' is active resolves correctly."""
        tools, ws = _setup_node_tools(
            {
                "nodes": {"result": True, "values": {"nodes": ["/turtlesim"]}},
                "node_details": {
                    "result": True,
                    "values": {
                        "publishing": ["/turtle1/pose"],
                        "subscribing": ["/turtle1/cmd_vel"],
                        "services": ["/turtle1/teleport_absolute"],
                    },
                },
            }
        )
        result = tools["get_node_details"](node="turtlesim")
        assert result["node"] == "/turtlesim"
        assert result["publisher_count"] == 1
        assert result["subscriber_count"] == 1
        assert result["service_count"] == 1
        assert result["publishers"] == ["/turtle1/pose"]
        assert result["subscribers"] == ["/turtle1/cmd_vel"]
        assert result["services"] == ["/turtle1/teleport_absolute"]

    def test_get_node_details_success(self) -> None:
        """Successfully returns publishers, subscribers, services for valid node."""
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
        result = tools["get_node_details"](node="/turtlesim")
        assert result["node"] == "/turtlesim"
        assert result["publisher_count"] == 2
        assert result["subscriber_count"] == 1
        assert result["service_count"] == 3
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
        assert "has no details available" in result["error"]
