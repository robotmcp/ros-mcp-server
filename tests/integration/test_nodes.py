"""Integration tests for node tools against a real ROS2 rosbridge."""

import pytest

pytestmark = [pytest.mark.integration, pytest.mark.slow]


class TestGetNodes:
    def test_returns_nodes(self, tools):
        result = tools["get_nodes"]()
        assert "nodes" in result
        assert len(result["nodes"]) > 0

    def test_includes_turtlesim_node(self, tools):
        result = tools["get_nodes"]()
        nodes = result["nodes"]
        assert any("turtlesim" in n for n in nodes)

    def test_has_node_count(self, tools):
        result = tools["get_nodes"]()
        assert result["node_count"] == len(result["nodes"])


class TestGetNodeDetails:
    @pytest.mark.skip(
        reason="rosapi_node on Humble crashes on node_details (TypeError: cannot unpack non-iterable NoneType)"
    )
    def test_turtlesim_details(self, tools):
        # Find the turtlesim node name
        nodes_result = tools["get_nodes"]()
        turtlesim_node = next(n for n in nodes_result["nodes"] if "turtlesim" in n)

        result = tools["get_node_details"](node=turtlesim_node)
        assert "error" not in result
        assert result["publisher_count"] > 0
        assert result["subscriber_count"] > 0
        assert result["service_count"] > 0

    @pytest.mark.skip(
        reason="rosapi_node on Humble crashes on node_details (TypeError: cannot unpack non-iterable NoneType)"
    )
    def test_nonexistent_node(self, tools):
        result = tools["get_node_details"](node="/nonexistent_node_xyz")
        assert "error" in result
