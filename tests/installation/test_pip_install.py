"""
Tests for pip-based installation methods.

These tests verify that pip install works both from PyPI and from source.
"""

import pytest
from pathlib import Path

from .conftest import build_docker_image, cleanup_docker_image


@pytest.mark.installation
@pytest.mark.slow
def test_pip_install_from_pypi(repo_root: Path, docker_dir: Path):
    """
    Test pip install ros-mcp from PyPI in a clean container.

    This verifies that the published package can be installed and runs correctly.
    """
    dockerfile = docker_dir / "Dockerfile.pip-pypi"
    tag = "ros-mcp-test:pip-pypi"

    try:
        result = build_docker_image(
            dockerfile_path=dockerfile,
            context_path=repo_root,
            tag=tag,
            timeout=300,  # 5 minutes for package downloads
        )

        assert result.returncode == 0, (
            f"pip install from PyPI failed:\n"
            f"STDOUT:\n{result.stdout}\n"
            f"STDERR:\n{result.stderr}"
        )

        # Verify success message is in output
        assert "SUCCESS" in result.stdout or "ros-mcp" in result.stdout.lower(), (
            f"Build succeeded but output unexpected:\n{result.stdout}"
        )

    finally:
        cleanup_docker_image(tag)


@pytest.mark.installation
@pytest.mark.slow
def test_pip_install_from_source(repo_root: Path, docker_dir: Path):
    """
    Test pip install . from cloned repository in a clean container.

    This verifies that developers can install the package from source.
    """
    dockerfile = docker_dir / "Dockerfile.pip-source"
    tag = "ros-mcp-test:pip-source"

    try:
        result = build_docker_image(
            dockerfile_path=dockerfile,
            context_path=repo_root,
            tag=tag,
            timeout=300,
        )

        assert result.returncode == 0, (
            f"pip install from source failed:\n"
            f"STDOUT:\n{result.stdout}\n"
            f"STDERR:\n{result.stderr}"
        )

    finally:
        cleanup_docker_image(tag)


@pytest.mark.installation
@pytest.mark.slow
@pytest.mark.parametrize("python_version", ["3.10", "3.11", "3.12"])
def test_pip_install_python_versions(repo_root: Path, docker_dir: Path, python_version: str):
    """
    Test pip install works on multiple Python versions.

    This ensures compatibility across supported Python versions.
    """
    # Read the Dockerfile and modify the base image
    dockerfile_content = (docker_dir / "Dockerfile.pip-source").read_text()
    dockerfile_content = dockerfile_content.replace(
        "FROM python:3.10-slim",
        f"FROM python:{python_version}-slim"
    )

    # Write temporary Dockerfile
    temp_dockerfile = docker_dir / f"Dockerfile.pip-source-{python_version}"
    temp_dockerfile.write_text(dockerfile_content)
    tag = f"ros-mcp-test:pip-py{python_version}"

    try:
        result = build_docker_image(
            dockerfile_path=temp_dockerfile,
            context_path=repo_root,
            tag=tag,
            timeout=300,
        )

        assert result.returncode == 0, (
            f"pip install failed on Python {python_version}:\n"
            f"STDOUT:\n{result.stdout}\n"
            f"STDERR:\n{result.stderr}"
        )

    finally:
        cleanup_docker_image(tag)
        # Clean up temporary Dockerfile
        if temp_dockerfile.exists():
            temp_dockerfile.unlink()
