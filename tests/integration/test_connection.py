"""Integration tests for connection tools (step 1).

These tests call the actual MCP tool functions (connect_to_robot,
ping_robots) against a live rosbridge container.
"""

import pytest

pytestmark = [pytest.mark.integration]


class TestConnectToRobot:
    """Verify connect_to_robot tool sets IP/port and tests connectivity."""

    def test_connect_localhost(self, tools):
        """connect_to_robot with default args should succeed against rosbridge."""
        result = tools["connect_to_robot"]()
        assert "message" in result
        assert "connectivity_test" in result
        assert result["connectivity_test"]["port_check"]["open"] is True

    def test_connect_explicit_ip_port(self, tools):
        """connect_to_robot with explicit IP/port should succeed."""
        result = tools["connect_to_robot"](ip="127.0.0.1", port=9090)
        assert "connectivity_test" in result
        assert result["connectivity_test"]["port_check"]["open"] is True

    def test_connect_wrong_port(self, tools):
        """connect_to_robot to a closed port should report port closed."""
        result = tools["connect_to_robot"](ip="127.0.0.1", port=19999, port_timeout=1.0)
        assert result["connectivity_test"]["port_check"]["open"] is False
        # Restore ws_manager to the correct port for subsequent tests
        tools["connect_to_robot"](ip="127.0.0.1", port=9090)


class TestPingRobots:
    """Verify ping_robots tool checks connectivity for multiple targets."""

    def test_ping_rosbridge(self, tools):
        """ping_robots with rosbridge target should report port open."""
        result = tools["ping_robots"](
            targets=[{"ip": "127.0.0.1", "port": 9090}],
        )
        assert "results" in result
        assert len(result["results"]) == 1
        assert result["results"][0]["port_check"]["open"] is True

    def test_ping_closed_port(self, tools):
        """ping_robots with a closed port should report port closed."""
        result = tools["ping_robots"](
            targets=[{"ip": "127.0.0.1", "port": 19999}],
            port_timeout=1.0,
        )
        assert result["results"][0]["port_check"]["open"] is False

    def test_ping_multiple_targets(self, tools):
        """ping_robots with mixed targets should return results for each."""
        result = tools["ping_robots"](
            targets=[
                {"ip": "127.0.0.1", "port": 9090},
                {"ip": "127.0.0.1", "port": 19999},
            ],
            port_timeout=1.0,
        )
        assert len(result["results"]) == 2
        assert result["results"][0]["port_check"]["open"] is True
        assert result["results"][1]["port_check"]["open"] is False

    def test_ping_default_target(self, tools):
        """ping_robots with no args should use default localhost:9090."""
        result = tools["ping_robots"]()
        assert "results" in result
        assert len(result["results"]) == 1

    def test_ping_empty_list(self, tools):
        """ping_robots with empty list should return error."""
        result = tools["ping_robots"](targets=[])
        assert "error" in result
