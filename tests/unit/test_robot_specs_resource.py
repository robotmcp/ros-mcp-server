"""Unit tests for ros_mcp/resources/robot_specs.py listing resource."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

_SRC = Path(__file__).resolve().parents[2] / "ros_mcp" / "resources" / "robot_specs.py"


class FakeMCP:
    """Capture @mcp.resource handlers."""

    def __init__(self) -> None:
        self.handlers: dict[str, object] = {}

    def resource(self, uri: str):
        def decorator(fn):
            self.handlers[uri] = fn
            return fn

        return decorator


def _load_with_project_root(project_root: Path):
    """Load robot_specs so specs_dir == project_root / robot_specifications.

    register_robot_spec_resources closes over Path(__file__).parent.parent.parent.
    Exec a copy whose __file__ sits at project_root/ros_mcp/resources/....
    """
    pkg_resources = project_root / "ros_mcp" / "resources"
    pkg_resources.mkdir(parents=True, exist_ok=True)
    target = pkg_resources / "robot_specs_ut_copy.py"
    target.write_text(_SRC.read_text(encoding="utf-8"), encoding="utf-8")

    name = f"robot_specs_ut_{id(project_root)}"
    spec = importlib.util.spec_from_file_location(name, target)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


URI = "ros-mcp://robot-specs/get_verified_robots_list"


class TestRobotSpecsResource:
    def test_lists_yaml_and_filters_template(self, tmp_path: Path):
        specs = tmp_path / "robot_specifications"
        specs.mkdir()
        (specs / "alpha.yaml").write_text("type: sim\nprompts: a\n")
        (specs / "beta.yaml").write_text("type: real\nprompts: b\n")
        (specs / "YOUR_ROBOT_NAME.yaml").write_text("type: x\nprompts: y\n")

        mod = _load_with_project_root(tmp_path)
        mcp = FakeMCP()
        mod.register_robot_spec_resources(mcp)
        assert URI in mcp.handlers
        payload = json.loads(mcp.handlers[URI]())
        assert payload["count"] == 2
        assert payload["robot_specifications"] == ["alpha", "beta"]
        assert "YOUR_ROBOT_NAME" not in payload["robot_specifications"]

    def test_missing_directory(self, tmp_path: Path):
        mod = _load_with_project_root(tmp_path)
        # no robot_specifications/
        mcp = FakeMCP()
        mod.register_robot_spec_resources(mcp)
        payload = json.loads(mcp.handlers[URI]())
        assert "error" in payload
        assert "not found" in payload["error"]
        assert payload["robot_specifications"] == []

    def test_empty_directory(self, tmp_path: Path):
        (tmp_path / "robot_specifications").mkdir()
        mod = _load_with_project_root(tmp_path)
        mcp = FakeMCP()
        mod.register_robot_spec_resources(mcp)
        payload = json.loads(mcp.handlers[URI]())
        assert payload["count"] == 0
        assert payload["robot_specifications"] == []
        assert "error" not in payload

    def test_template_only_directory(self, tmp_path: Path):
        specs = tmp_path / "robot_specifications"
        specs.mkdir()
        (specs / "YOUR_ROBOT_NAME.yaml").write_text("type: t\nprompts: p\n")
        mod = _load_with_project_root(tmp_path)
        mcp = FakeMCP()
        mod.register_robot_spec_resources(mcp)
        payload = json.loads(mcp.handlers[URI]())
        assert payload["count"] == 0
        assert payload["robot_specifications"] == []
