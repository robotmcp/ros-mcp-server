from pathlib import Path

import yaml


def load_robot_config(robot_name: str, specs_dir: str) -> dict:
    """
    Load the robot configuration from a YAML file by robot name.

    Args:
        robot_name (str): The name of the robot.
        specs_dir (str): Directory containing robot specification files.

    Returns:
        dict: The robot configuration.

    Raises:
        FileNotFoundError: If the YAML file does not exist.
    """
    file_path = Path(specs_dir) / f"{robot_name}.yaml"

    if not file_path.exists():
        raise FileNotFoundError(f"Robot config file not found: {file_path}")

    with file_path.open("r") as file:
        return yaml.safe_load(file) or {}


def get_verified_robot_spec_util(name: str) -> dict:
    """
    Get the verified robot specification in a more accessible format.

    Args:
        name (str): The name of the robot.

    Returns:
        dict: Parsed robot configuration with robot name as key.
    """
    # Resolve relative to the project root (one level up from utils)
    specs_dir = Path(__file__).parent.parent / "robot_specifications"

    name = name.replace(" ", "_")
    config = load_robot_config(name, str(specs_dir))
    parsed_config = {}

    # Check if the loaded config has the required fields
    if not config:
        raise ValueError(f"No configuration found for robot '{name}'")

    # Check required fields
    for field in ("type", "prompts"):
        if field not in config or config[field] in (None, ""):
            raise ValueError(f"Robot '{name}' is missing required field: {field}")

    # Create configuration with robot name as key
    parsed_config[name] = {"type": config["type"], "prompts": config["prompts"]}

    return parsed_config


def get_verified_robots_list_util() -> dict:
    """
    Get a list of all available robot specification files.

    Returns:
        dict: List of available robot names that can be used with get_verified_robot_spec_util.
    """
    # Resolve relative to the project root (one level up from utils)
    specs_path = Path(__file__).parent.parent / "robot_specifications"

    if not specs_path.exists():
        return {"error": f"Robot specifications directory not found: {specs_path}"}

    try:
        # Find all YAML files in the specifications directory
        yaml_files = list(specs_path.glob("*.yaml"))

        if not yaml_files:
            return {"error": "No robot specification files found"}

        # Extract robot names (file names without .yaml extension)
        robot_names = [file.stem for file in yaml_files]
        robot_names.sort()  # Sort alphabetically for consistency

        return {"robot_specifications": robot_names, "count": len(robot_names)}

    except Exception as e:
        return {"error": f"Failed to read robot specifications directory: {str(e)}"}
