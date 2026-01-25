"""
Tests for source-based installation using uv sync.

These tests verify the development installation workflow.
Source tests use the local repository (current branch).
"""

from pathlib import Path

import pytest

from .conftest import build_docker_image, cleanup_docker_image


@pytest.mark.installation
@pytest.mark.slow
def test_uv_source_install(repo_root: Path, docker_dir: Path):
    """
    Test uv sync from cloned repository.

    This verifies the development workflow:
    1. git clone the repository
    2. uv sync
    3. uv run ros-mcp --help
    """
    dockerfile = docker_dir / "Dockerfile.uv-source"
    tag = "ros-mcp-test:uv-source"

    try:
        result = build_docker_image(
            dockerfile_path=dockerfile,
            context_path=repo_root,
            tag=tag,
            timeout=300,
        )

        assert result.returncode == 0, (
            f"uv sync from source failed:\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
        )

    finally:
        cleanup_docker_image(tag)


@pytest.mark.installation
@pytest.mark.slow
def test_uv_source_with_dev_dependencies(repo_root: Path, docker_dir: Path):
    """
    Test uv sync with dev dependencies for development workflow.

    This verifies that developers can install with test dependencies.
    """
    # Modify Dockerfile to include dev dependencies
    dockerfile_content = (docker_dir / "Dockerfile.uv-source").read_text()
    dockerfile_content = dockerfile_content.replace("RUN uv sync", "RUN uv sync --extra dev")
    # Also verify pytest is available
    dockerfile_content = dockerfile_content.replace(
        'RUN echo "SUCCESS: uv sync from source works correctly"',
        'RUN uv run pytest --version && echo "SUCCESS: uv sync with dev dependencies works correctly"',
    )

    temp_dockerfile = docker_dir / "Dockerfile.uv-source-dev"
    temp_dockerfile.write_text(dockerfile_content)
    tag = "ros-mcp-test:uv-source-dev"

    try:
        result = build_docker_image(
            dockerfile_path=temp_dockerfile,
            context_path=repo_root,
            tag=tag,
            timeout=300,
        )

        assert result.returncode == 0, (
            f"uv sync with dev dependencies failed:\n"
            f"STDOUT:\n{result.stdout}\n"
            f"STDERR:\n{result.stderr}"
        )

    finally:
        cleanup_docker_image(tag)
        if temp_dockerfile.exists():
            temp_dockerfile.unlink()


@pytest.mark.installation
@pytest.mark.slow
@pytest.mark.parametrize("python_version", ["3.10", "3.11", "3.12"])
def test_uv_source_python_versions(repo_root: Path, docker_dir: Path, python_version: str):
    """
    Test uv sync works on multiple Python versions.

    This ensures the development workflow works across supported Python versions.
    """
    dockerfile_content = (docker_dir / "Dockerfile.uv-source").read_text()
    dockerfile_content = dockerfile_content.replace(
        "FROM python:3.10-slim", f"FROM python:{python_version}-slim"
    )

    temp_dockerfile = docker_dir / f"Dockerfile.uv-source-{python_version}"
    temp_dockerfile.write_text(dockerfile_content)
    tag = f"ros-mcp-test:uv-py{python_version}"

    try:
        result = build_docker_image(
            dockerfile_path=temp_dockerfile,
            context_path=repo_root,
            tag=tag,
            timeout=300,
        )

        assert result.returncode == 0, (
            f"uv sync failed on Python {python_version}:\n"
            f"STDOUT:\n{result.stdout}\n"
            f"STDERR:\n{result.stderr}"
        )

    finally:
        cleanup_docker_image(tag)
        if temp_dockerfile.exists():
            temp_dockerfile.unlink()
