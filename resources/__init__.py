# Resources package for ROS MCP Server
# Functions to register resources with the MCP server instance
from resources.robot_specs import register_robot_spec_resources
from resources.ros_metadata import register_ros_metadata_resources


def register_all_resources(mcp, ws_manager):
    """Register all resources with the MCP server instance."""
    register_robot_spec_resources(mcp)
    register_ros_metadata_resources(mcp, ws_manager)
