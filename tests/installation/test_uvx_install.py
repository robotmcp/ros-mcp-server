"""
Tests for uvx-based installation method.

This tests the primary documented installation method using uvx.
"""

import pytest
from pathlib import Path

from .conftest import build_docker_image, cleanup_docker_image


@pytest.mark.installation
@pytest.mark.slow
def test_uvx_install(repo_root: Path, docker_dir: Path):
    """
    Test uvx ros-mcp installation as documented.

    This is the primary installation method documented in installation.md:
    1. curl -LsSf https://astral.sh/uv/install.sh | sh
    2. uvx ros-mcp --help

    This test verifies that a user following the documentation will succeed.
    """
    dockerfile = docker_dir / "Dockerfile.uvx"
    tag = "ros-mcp-test:uvx"

    try:
        result = build_docker_image(
            dockerfile_path=dockerfile,
            context_path=repo_root,
            tag=tag,
            timeout=300,  # 5 minutes for uv and package downloads
        )

        assert result.returncode == 0, (
            f"uvx installation failed:\n"
            f"STDOUT:\n{result.stdout}\n"
            f"STDERR:\n{result.stderr}"
        )

        # Verify uv was installed and ros-mcp ran
        output = result.stdout.lower()
        assert "success" in output or "ros-mcp" in output, (
            f"Build succeeded but output unexpected:\n{result.stdout}"
        )

    finally:
        cleanup_docker_image(tag)


@pytest.mark.installation
@pytest.mark.slow
def test_uvx_install_with_transport_flag(repo_root: Path, docker_dir: Path):
    """
    Test uvx ros-mcp with --transport=stdio flag as used in config examples.

    The documentation shows configuring Claude Desktop with:
    uvx ros-mcp --transport=stdio

    This verifies that flag works correctly.
    """
    # Modify Dockerfile to test with transport flag
    dockerfile_content = (docker_dir / "Dockerfile.uvx").read_text()
    dockerfile_content = dockerfile_content.replace(
        "RUN uvx ros-mcp --help",
        "RUN uvx ros-mcp --transport=stdio --help"
    )

    temp_dockerfile = docker_dir / "Dockerfile.uvx-transport"
    temp_dockerfile.write_text(dockerfile_content)
    tag = "ros-mcp-test:uvx-transport"

    try:
        result = build_docker_image(
            dockerfile_path=temp_dockerfile,
            context_path=repo_root,
            tag=tag,
            timeout=300,
        )

        assert result.returncode == 0, (
            f"uvx installation with --transport=stdio failed:\n"
            f"STDOUT:\n{result.stdout}\n"
            f"STDERR:\n{result.stderr}"
        )

    finally:
        cleanup_docker_image(tag)
        if temp_dockerfile.exists():
            temp_dockerfile.unlink()
