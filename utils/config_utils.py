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


def load_map_config(map_name: str, specs_dir: str) -> dict:
    """
    Load the map configuration from a YAML file by map name.

    Args:
        map_name (str): The name of the map.
        specs_dir (str): Directory containing map information files.

    Returns:
        dict: The map configuration.

    Raises:
        FileNotFoundError: If the YAML file does not exist.
    """
    file_path = Path(specs_dir) / f"{map_name}.yaml"

    if not file_path.exists():
        raise FileNotFoundError(f"map config file not found: {file_path}")

    with file_path.open("r") as file:
        return yaml.safe_load(file) or {}


def get_map_info_util(name: str) -> dict:
    """
    Get the map information in a more accessible format.

    Args:
        name (str): The name of the map.

    Returns:
        dict: Get map information with map name as key.
    """
    # Resolve relative to the project root (one level up from utils)
    specs_dir = Path(__file__).parent.parent / "map_specifications"

    name = name.replace(" ", "_")
    config = load_map_config(name, str(specs_dir))
    parsed_config = {}

    # Check if the loaded config has the required fields
    if not config:
        raise ValueError(f"No configuration found for map '{name}'")

    # Check required fields
    for field in ("type", "locations"):
        if field not in config or config[field] in (None, ""):
            raise ValueError(f"Map '{name}' is missing required field: {field}")

    # Create configuration with robot name as key
    parsed_config[name] = {"type": config["type"], "locations": config["locations"]}

    return parsed_config


def get_map_info_list_util() -> dict:
    """
    Get a list of all available map specification files.

    Returns:
        dict: List of available map names that can be used with get_map_info_util.
    """
    # Resolve relative to the project root (one level up from utils)
    specs_path = Path(__file__).parent.parent / "map_specifications"

    if not specs_path.exists():
        return {"error": f"Map specifications directory not found: {specs_path}"}

    try:
        # Find all YAML files in the specifications directory
        yaml_files = list(specs_path.glob("*.yaml"))

        if not yaml_files:
            return {"error": "No map specification files found"}

        # Extract robot names (file names without .yaml extension)
        map_names = [file.stem for file in yaml_files]
        map_names.sort()  # Sort alphabetically for consistency

        return {"map_specifications": map_names, "count": len(map_names)}

    except Exception as e:
        return {"error": f"Failed to read map specifications directory: {str(e)}"}


def write_map_location_util(
    map_name: str,  # e.g. "hospital", "office"
    name: str,  # e.g. "AED"
    description: str,
    x: float,
    y: float,
    yaw: float,
) -> dict:
    """
    Add or update a location entry in map_specifications/{map_name}.yaml.

    Args:
        map_name (str): Map name without extension (e.g., 'hospital', 'office').
        name (str): Location name (e.g., 'AED').
        description (str): Description of the location.
        x (float): X coordinate.
        y (float): Y coordinate.
        yaw (float): Orientation in radians.

    Returns:
        dict: Status, which file was modified, and the added/updated location.
    """
    try:
        # Resolve specs directory (same as get_map_info_util)
        specs_dir = Path(__file__).parent.parent / "map_specifications"

        if not specs_dir.exists():
            return {"error": f"Map specifications directory not found: {specs_dir}"}

        # Build the YAML file path for the selected map
        safe_map_name = map_name.replace(" ", "_")
        map_file = specs_dir / f"{safe_map_name}.yaml"

        if not map_file.exists():
            return {"error": f"Map file not found: {map_file}"}

        # Load existing YAML
        with map_file.open("r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}

        # Ensure 'locations' exists
        if "locations" not in data or data["locations"] is None:
            data["locations"] = []

        locations = data["locations"]

        # Build the new/updated location entry
        new_location = {
            "name": name,
            "description": description,
            "pose": {
                "x": float(x),
                "y": float(y),
                "yaw": float(yaw),
            },
        }

        # If a location with the same name exists → update it, else append
        action = "added"
        for idx, loc in enumerate(locations):
            if loc.get("name") == name:
                locations[idx] = new_location
                action = "updated"
                break
        else:
            locations.append(new_location)

        data["locations"] = locations

        # Write back to the same YAML file
        with map_file.open("w", encoding="utf-8") as f:
            yaml.safe_dump(
                data,
                f,
                sort_keys=False,
                allow_unicode=True,
            )

        return {
            "status": "success",
            "action": action,
            "map_name": safe_map_name,
            "file": str(map_file),
            "location": new_location,
        }

    except Exception as e:
        return {"error": f"Failed to write semantic location: {str(e)}"}
