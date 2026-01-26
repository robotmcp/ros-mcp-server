"""E2E tests for CLI argument parsing and server initialization."""

import argparse

import pytest

pytestmark = pytest.mark.e2e


class TestParseArguments:
    """E2E tests for command line argument parsing."""

    def test_parse_arguments_defaults(self):
        """Verify default argument values are correct."""
        from ros_mcp.main import parse_arguments

        # Mock sys.argv to test defaults
        import sys
        original_argv = sys.argv
        try:
            sys.argv = ["ros_mcp"]
            args = parse_arguments()

            assert args.transport == "stdio", "Default transport should be stdio"
            assert args.host == "127.0.0.1", "Default host should be 127.0.0.1"
            assert args.port == 9000, "Default port should be 9000"
        finally:
            sys.argv = original_argv

    def test_parse_arguments_http_transport(self):
        """Verify HTTP transport arguments are parsed correctly."""
        from ros_mcp.main import parse_arguments

        import sys
        original_argv = sys.argv
        try:
            sys.argv = [
                "ros_mcp",
                "--transport", "http",
                "--host", "0.0.0.0",
                "--port", "8080",
            ]
            args = parse_arguments()

            assert args.transport == "http", "Transport should be http"
            assert args.host == "0.0.0.0", "Host should be 0.0.0.0"
            assert args.port == 8080, "Port should be 8080"
        finally:
            sys.argv = original_argv

    def test_parse_arguments_streamable_http_transport(self):
        """Verify streamable-http transport arguments are parsed correctly."""
        from ros_mcp.main import parse_arguments

        import sys
        original_argv = sys.argv
        try:
            sys.argv = [
                "ros_mcp",
                "--transport", "streamable-http",
                "--host", "192.168.1.100",
                "--port", "9999",
            ]
            args = parse_arguments()

            assert args.transport == "streamable-http"
            assert args.host == "192.168.1.100"
            assert args.port == 9999
        finally:
            sys.argv = original_argv


class TestMCPServerRegistration:
    """E2E tests for MCP server component registration."""

    def test_mcp_server_has_all_tools_registered(self, mcp_server):
        """Verify all expected tools are registered with MCP server."""
        tool_manager = mcp_server._tool_manager
        tools = tool_manager._tools

        # Expected tool categories based on the project structure
        expected_tools = [
            # Connection tools
            "connect_to_robot",
            "detect_ros_version",
            # Topic tools
            "get_topics",
            "get_topic_type",
            "get_topic_details",
            "get_message_details",
            "subscribe_once",
            "subscribe_for_duration",
            "publish_once",
            "publish_for_durations",
            # Service tools
            "get_services",
            "get_service_type",
            "get_service_details",
            "call_service",
            # Node tools
            "get_nodes",
            "get_node_details",
            # Parameter tools
            "get_parameter",
            "set_parameter",
            "has_parameter",
            "delete_parameter",
            "get_parameters",
            "get_parameter_details",
            # Action tools
            "get_actions",
            "get_action_details",
            "get_action_status",
            "send_action_goal",
            "cancel_action_goal",
            # Image tools
            "analyze_previously_received_image",
        ]

        tool_names = list(tools.keys())
        for expected_tool in expected_tools:
            assert expected_tool in tool_names, (
                f"Expected tool '{expected_tool}' to be registered. Found: {tool_names}"
            )

    def test_mcp_server_has_all_resources_registered(self, mcp_server):
        """Verify all expected resources are registered with MCP server."""
        resource_manager = mcp_server._resource_manager
        resources = resource_manager._resources

        expected_resources = [
            "ros-mcp://robot-specs/get_verified_robots_list",
            "ros-mcp://ros-metadata/topics/all",
            "ros-mcp://ros-metadata/services/all",
            "ros-mcp://ros-metadata/nodes/all",
        ]

        for expected_resource in expected_resources:
            assert expected_resource in resources, (
                f"Expected resource '{expected_resource}' to be registered"
            )

    def test_mcp_server_has_all_prompts_registered(self, mcp_server):
        """Verify all expected prompts are registered with MCP server."""
        prompt_manager = mcp_server._prompt_manager
        prompts = prompt_manager._prompts

        expected_prompts = [
            "test-server-tools",
            "test-connection-tools",
            "test-nodes-tools",
            "test-services-tools",
            "test-topics-tools",
            "test-actions-tools",
            "test-parameters-tools",
        ]

        prompt_names = list(prompts.keys())
        for expected_prompt in expected_prompts:
            assert expected_prompt in prompt_names, (
                f"Expected prompt '{expected_prompt}' to be registered"
            )

    def test_mcp_server_name(self, mcp_server):
        """Verify MCP server has correct name."""
        # The test server is named differently for isolation
        assert "ros-mcp-server" in mcp_server.name, (
            f"Expected 'ros-mcp-server' in name, got: {mcp_server.name}"
        )
