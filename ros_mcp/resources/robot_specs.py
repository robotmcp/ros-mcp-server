"""Resources for robot specifications."""

import json
from pathlib import Path


def register_robot_spec_resources(mcp):
    """Register robot specification resources with the MCP server."""

    # Get the robot_specifications directory path
    # From ros_mcp/resources/robot_specs.py, go up to project root
    specs_dir = Path(__file__).parent.parent.parent / "robot_specifications"

    @mcp.resource("ros-mcp://robot-specs/get_verified_robots_list")
    def get_verified_robots_list() -> str:
        """
        Get all available robot specifications.

        Returns:
            str: JSON string with list of available robot names
        """
        try:
            if not specs_dir.exists():
                return json.dumps(
                    {
                        "error": f"Robot specifications directory not found: {specs_dir}",
                        "robot_specifications": [],
                    }
                )

            # Find all YAML files
            yaml_files = list(specs_dir.glob("*.yaml"))

            # Filter out template files only
            robot_names = [file.stem for file in yaml_files if not file.stem.startswith("YOUR_")]
            robot_names.sort()

            return json.dumps({"robot_specifications": robot_names, "count": len(robot_names)})

        except Exception as e:
            return json.dumps(
                {
                    "error": f"Failed to list robot specifications: {str(e)}",
                    "robot_specifications": [],
                }
            )
