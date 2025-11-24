from __future__ import annotations

import copy
import json
import time
import uuid
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
_BEHAVIOR_TREE_LIBRARY_PATH = BASE_DIR / "robot_specifications" / "bts" / "turtlesim_bt_library.json"

_behavior_tree_cache: dict[str, dict] = {}
_behavior_tree_library: dict[str, dict] = {}
_behavior_tree_library_errors: list[str] = []
_behavior_tree_library_loaded = False


def _generate_tree_id() -> str:
    """
    Generate unique tree ID using timestamp + short UUID.

    Returns:
        str: Unique tree identifier (e.g., "tree_1732147392_8a3f9c12")
    """
    timestamp = int(time.time() * 1000)
    short_uuid = str(uuid.uuid4())[:8]
    return f"tree_{timestamp}_{short_uuid}"


def _count_actions(node: dict) -> int:
    """
    Recursively count action nodes in tree.

    Args:
        node: Tree node (sequence or action)

    Returns:
        int: Total number of action nodes
    """
    if node.get("type") == "action":
        return 1
    elif node.get("type") == "sequence":
        return sum(_count_actions(child) for child in node.get("children", []))
    else:
        return 0


def validate_tree_definition(tree: dict) -> tuple[bool, str]:
    """
    Validate tree structure before execution.

    Checks:
    - Root node has "type" field
    - Sequence nodes have "children" list
    - Action nodes have required fields: action_name, action_type, goal
    - No unknown node types

    Args:
        tree: Tree definition dict

    Returns:
        tuple: (is_valid, error_message)
    """
    if not isinstance(tree, dict):
        return False, "Tree must be a dictionary"

    if "type" not in tree:
        return False, "Tree node missing 'type' field"

    node_type = tree["type"]

    if node_type == "sequence":
        if "children" not in tree:
            return False, "Sequence node missing 'children' field"

        children = tree["children"]
        if not isinstance(children, list):
            return False, "Sequence 'children' must be a list"

        if len(children) == 0:
            return True, ""  # Empty sequence is valid (no-op)

        # Validate each child recursively
        for i, child in enumerate(children):
            is_valid, error = validate_tree_definition(child)
            if not is_valid:
                return False, f"Child {i}: {error}"

        return True, ""

    elif node_type == "action":
        # Check required fields
        required_fields = ["action_name", "action_type", "goal"]
        for field in required_fields:
            if field not in tree:
                return False, f"Action node missing required field '{field}'"

        # Validate goal is a dict
        if not isinstance(tree["goal"], dict):
            return False, "Action 'goal' must be a dictionary"

        return True, ""

    else:
        return False, f"Unknown node type: '{node_type}'"


def _generate_ascii_tree(tree: dict, tree_name: str = "Main") -> str:
    """
    Generate ASCII tree visualization.

    Example output:
    : turtle_task :: tree
    └── seq_main :: sequence
        ├── goto_pose :: action[GoToPose] (x=5.0, y=5.0)
        └── drive_distance :: action[DriveDistance] (distance=2.0)

    Args:
        tree: Tree definition dict
        tree_name: Root name for the tree

    Returns:
        str: Formatted ASCII tree string
    """
    lines = [f": {tree_name} :: tree"]
    _add_node_lines(tree, lines, prefix="", is_last=True)
    return "\n".join(lines)


def _add_node_lines(node: dict, lines: list, prefix: str, is_last: bool):
    """
    Recursively add node lines with proper tree characters.

    Args:
        node: Tree node to visualize
        lines: List of output lines (modified in place)
        prefix: Prefix string for indentation
        is_last: Whether this is the last child of its parent
    """
    # Determine connector
    connector = "└── " if is_last else "├── "

    # Get node info
    node_type = node.get("type", "unknown")
    node_name = node.get("name", f"{node_type}_node")

    if node_type == "sequence":
        lines.append(f"{prefix}{connector}{node_name} :: sequence")

        # Add children
        children = node.get("children", [])
        child_prefix = prefix + ("    " if is_last else "│   ")

        for i, child in enumerate(children):
            is_last_child = (i == len(children) - 1)
            _add_node_lines(child, lines, child_prefix, is_last_child)

    elif node_type == "action":
        action_name = node.get("action_name", "unknown")
        action_type = node.get("action_type", "unknown/Unknown")

        # Extract just the action name (e.g., "GoToPose" from "pkg/action/GoToPose")
        action_short = action_type.split("/")[-1] if "/" in action_type else action_type

        # Format goal parameters (concise version - show first 3 params)
        goal = node.get("goal", {})
        if goal:
            params = ", ".join([f"{k}={v}" for k, v in list(goal.items())[:3]])
            if len(goal) > 3:
                params += ", ..."
            lines.append(f"{prefix}{connector}{node_name} :: action[{action_short}] ({params})")
        else:
            lines.append(f"{prefix}{connector}{node_name} :: action[{action_short}]")

    else:
        lines.append(f"{prefix}{connector}{node_name} :: {node_type}")


def _ensure_behavior_tree_library_loaded() -> None:
    """Load the behavior tree library from this repo if it hasn't been loaded yet."""
    global _behavior_tree_library_loaded
    if _behavior_tree_library_loaded:
        return

    _load_behavior_tree_library()
    _behavior_tree_library_loaded = True


def _load_behavior_tree_library() -> None:
    """Load predefined behavior trees from the bundled JSON file."""
    _behavior_tree_library.clear()
    _behavior_tree_library_errors.clear()

    if not _BEHAVIOR_TREE_LIBRARY_PATH.exists():
        return

    try:
        data = json.loads(_BEHAVIOR_TREE_LIBRARY_PATH.read_text())
    except Exception as exc:
        _behavior_tree_library_errors.append(
            f"Failed to load behavior_tree_library.json: {exc}"
        )
        return

    trees = data.get("trees", [])
    for entry in trees:
        entry_id = entry.get("id")
        if not entry_id:
            _behavior_tree_library_errors.append("Skipped entry without 'id'")
            continue

        entry_id = str(entry_id)
        name = entry.get("name", entry_id)
        description = entry.get("description", "")
        tags = entry.get("tags", [])
        tree_def_raw = entry.get("tree")

        if not isinstance(tree_def_raw, dict):
            _behavior_tree_library_errors.append(
                f"Behavior tree '{entry_id}' is missing a valid 'tree' definition"
            )
            continue

        tree_definition = copy.deepcopy(tree_def_raw)
        is_valid, validation_error = validate_tree_definition(tree_definition)
        visualization = _generate_ascii_tree(tree_definition, name)
        action_count = _count_actions(tree_definition)

        cached_tree_id = None
        if is_valid:
            cached_tree_id = f"library_{entry_id}"
            _behavior_tree_cache[cached_tree_id] = {
                "tree_definition": copy.deepcopy(tree_definition),
                "tree_name": name,
                "created_at": time.time(),
                "visualization": visualization,
                "valid": True,
            }

        _behavior_tree_library[entry_id] = {
            "library_id": entry_id,
            "name": name,
            "description": description,
            "tags": tags,
            "tree_definition": copy.deepcopy(tree_definition),
            "visualization": visualization,
            "action_count": action_count,
            "cached_tree_id": cached_tree_id,
            "valid": is_valid,
            "validation_errors": [] if is_valid else [validation_error],
        }


def get_behavior_tree_cache() -> dict[str, dict]:
    return _behavior_tree_cache


def get_behavior_tree_library() -> dict[str, dict]:
    return _behavior_tree_library


def get_behavior_tree_library_errors() -> list[str]:
    return _behavior_tree_library_errors
