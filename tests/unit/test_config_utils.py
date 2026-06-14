"""Unit tests for ros_mcp/utils/config_utils.py."""

from pathlib import Path

import pytest

import ros_mcp.utils.config_utils as config_module
from ros_mcp.utils.config_utils import (
    get_verified_robot_spec_util,
    get_verified_robots_list_util,
    load_robot_config,
)

# ---------------------------------------------------------------------------
# load_robot_config — accepts specs_dir param, fully controllable
# ---------------------------------------------------------------------------


class TestLoadRobotConfig:
    def test_valid_yaml(self, valid_robot_yaml):
        specs_dir, robot_name = valid_robot_yaml
        config = load_robot_config(robot_name, specs_dir)
        assert config["name"] == "test_robot"
        assert config["type"] == "simulated"
        assert "test robot" in config["prompts"].lower()

    def test_missing_file_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError, match="Robot config file not found"):
            load_robot_config("nonexistent", str(tmp_path))

    def test_empty_yaml_returns_empty_dict(self, empty_robot_yaml):
        specs_dir, robot_name = empty_robot_yaml
        config = load_robot_config(robot_name, specs_dir)
        assert config == {}


# ---------------------------------------------------------------------------
# get_verified_robot_spec_util — uses Path(__file__) internally
# ---------------------------------------------------------------------------


def _patch_specs_dir(monkeypatch, tmp_path):
    """Redirect config_utils.__file__ so specs_dir resolves to tmp_path/robot_specifications.

    Note: this approach is tightly coupled to config_utils's internal path
    resolution (Path(__file__).parent.parent.parent / "robot_specifications").
    If config_utils is refactored to accept specs_dir via injection or
    configuration, these monkeypatches will need to be revisited.
    """
    # config_utils resolves: Path(__file__).parent.parent.parent / "robot_specifications"
    # So __file__ must be at: tmp_path / "a" / "b" / "config_utils.py"
    fake_file = tmp_path / "a" / "b" / "config_utils.py"
    fake_file.parent.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(config_module, "__file__", str(fake_file))


class TestGetVerifiedRobotSpecUtil:
    def test_valid_robot_with_fixture(self, monkeypatch, tmp_path):
        _patch_specs_dir(monkeypatch, tmp_path)
        specs_dir = tmp_path / "robot_specifications"
        specs_dir.mkdir()
        (specs_dir / "my_robot.yaml").write_text("type: simulated\nprompts: A test robot.\n")
        result = get_verified_robot_spec_util("my_robot")
        assert "my_robot" in result
        assert result["my_robot"]["type"] == "simulated"

    def test_spaces_in_name_replaced(self, monkeypatch, tmp_path):
        _patch_specs_dir(monkeypatch, tmp_path)
        specs_dir = tmp_path / "robot_specifications"
        specs_dir.mkdir()
        (specs_dir / "my_robot.yaml").write_text("type: real\nprompts: A real robot.\n")
        result = get_verified_robot_spec_util("my robot")
        assert "my_robot" in result

    def test_missing_robot_raises(self, monkeypatch, tmp_path):
        _patch_specs_dir(monkeypatch, tmp_path)
        (tmp_path / "robot_specifications").mkdir()
        with pytest.raises(FileNotFoundError):
            get_verified_robot_spec_util("nonexistent")

    def test_empty_config_raises_value_error(self, monkeypatch, tmp_path):
        _patch_specs_dir(monkeypatch, tmp_path)
        specs_dir = tmp_path / "robot_specifications"
        specs_dir.mkdir()
        (specs_dir / "empty.yaml").write_text("")
        with pytest.raises(ValueError, match="No configuration found"):
            get_verified_robot_spec_util("empty")

    def test_missing_required_field_raises(self, monkeypatch, tmp_path):
        _patch_specs_dir(monkeypatch, tmp_path)
        specs_dir = tmp_path / "robot_specifications"
        specs_dir.mkdir()
        (specs_dir / "incomplete.yaml").write_text("type: real\n")
        with pytest.raises(ValueError, match="missing required field"):
            get_verified_robot_spec_util("incomplete")

    def test_with_real_robot_specs(self):
        """Integration-style: test against actual robot_specifications/ in the repo."""
        specs_path = Path(__file__).parent.parent.parent / "robot_specifications"
        real_robots = [f.stem for f in specs_path.glob("*.yaml") if f.stem != "YOUR_ROBOT_NAME"]
        if not real_robots:
            pytest.skip("No real robot spec files found")
        result = get_verified_robot_spec_util(real_robots[0])
        assert real_robots[0] in result
        assert "type" in result[real_robots[0]]
        assert "prompts" in result[real_robots[0]]


# ---------------------------------------------------------------------------
# get_verified_robots_list_util — uses Path(__file__) internally
# ---------------------------------------------------------------------------


class TestGetVerifiedRobotsListUtil:
    def test_returns_sorted_list(self):
        """Test against the actual robot_specifications/ directory."""
        result = get_verified_robots_list_util()
        if "error" in result:
            pytest.skip(f"Skipping: {result['error']}")
        assert "robot_specifications" in result
        assert "count" in result
        assert result["count"] > 0
        names = result["robot_specifications"]
        assert names == sorted(names)

    def test_missing_directory(self, monkeypatch, tmp_path):
        _patch_specs_dir(monkeypatch, tmp_path)
        # Don't create robot_specifications/ → should return error
        result = get_verified_robots_list_util()
        assert "error" in result
        assert "not found" in result["error"]

    def test_empty_directory(self, monkeypatch, tmp_path):
        _patch_specs_dir(monkeypatch, tmp_path)
        (tmp_path / "robot_specifications").mkdir()
        result = get_verified_robots_list_util()
        assert "error" in result
        assert "No robot specification files found" in result["error"]
