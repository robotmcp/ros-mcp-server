"""Prompts package for ROS MCP Server.

Functions to register prompts with the MCP server instance.
"""

from ros_mcp.prompts.test_actions_tools import register_test_actions_tools_prompts
from ros_mcp.prompts.test_connection_tools import register_test_connection_tools_prompts
from ros_mcp.prompts.test_nodes_tools import register_test_nodes_tools_prompts
from ros_mcp.prompts.test_parameters_tools import register_test_parameters_tools_prompts
from ros_mcp.prompts.test_server_tools import register_test_server_tools_prompts
from ros_mcp.prompts.test_services_tools import register_test_services_tools_prompts
from ros_mcp.prompts.test_topics_tools import register_test_topics_tools_prompts


def register_all_prompts(mcp):
    """Register all prompts with the MCP server instance."""
    register_test_server_tools_prompts(mcp)
    register_test_connection_tools_prompts(mcp)
    register_test_nodes_tools_prompts(mcp)
    register_test_services_tools_prompts(mcp)
    register_test_topics_tools_prompts(mcp)
    register_test_actions_tools_prompts(mcp)
    register_test_parameters_tools_prompts(mcp)
