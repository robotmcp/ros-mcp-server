"""Shared fixtures for unit tests."""

import pytest

# ---------------------------------------------------------------------------
# rosbridge response fixtures (used by test_response.py)
# ---------------------------------------------------------------------------


@pytest.fixture
def success_response():
    """A rosbridge response indicating success with values."""
    return {"result": True, "values": {"message": "ok", "data": [1, 2, 3]}}


@pytest.fixture
def failure_response():
    """A rosbridge response indicating failure with an error message."""
    return {"result": False, "values": {"message": "Service not available"}}


@pytest.fixture
def failure_response_no_message():
    """A rosbridge response indicating failure without an error message."""
    return {"result": False, "values": {}}


# ---------------------------------------------------------------------------
# Robot config fixtures (used by test_config_utils.py)
# ---------------------------------------------------------------------------


@pytest.fixture
def valid_robot_yaml(tmp_path):
    """Create a temporary valid robot YAML file and return (specs_dir, robot_name)."""
    yaml_content = (
        "name: test_robot\ntype: simulated\nprompts: |\n  This is a test robot for unit testing.\n"
    )
    yaml_file = tmp_path / "test_robot.yaml"
    yaml_file.write_text(yaml_content)
    return str(tmp_path), "test_robot"


@pytest.fixture
def empty_robot_yaml(tmp_path):
    """Create a temporary empty YAML file and return (specs_dir, robot_name)."""
    yaml_file = tmp_path / "empty_robot.yaml"
    yaml_file.write_text("")
    return str(tmp_path), "empty_robot"
