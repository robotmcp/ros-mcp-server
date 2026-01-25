"""
Tests for uvx-based installation method.

This tests the primary documented installation method using uvx.
All tests install from git to validate before publishing.
"""

from pathlib import Path

import pytest

from .conftest import build_docker_image, cleanup_docker_image


@pytest.mark.installation
@pytest.mark.slow
def test_uvx_install_from_git(repo_root: Path, docker_dir: Path, git_branch: str, repo_url: str):
    """
    Test uvx ros-mcp installation from git.

    This verifies that uvx can install and run ros-mcp from a git branch.
    Uses: uvx --from git+REPO_URL@BRANCH ros-mcp --help
    """
    dockerfile = docker_dir / "Dockerfile.uvx"
    tag = "ros-mcp-test:uvx-git"

    try:
        result = build_docker_image(
            dockerfile_path=dockerfile,
            context_path=repo_root,
            tag=tag,
            build_args={
                "REPO_URL": repo_url,
                "BRANCH": git_branch,
            },
            timeout=300,  # 5 minutes for uv and package downloads
        )

        assert result.returncode == 0, (
            f"uvx installation from git failed (branch: {git_branch}):\n"
            f"STDOUT:\n{result.stdout}\n"
            f"STDERR:\n{result.stderr}"
        )

        # Verify success message is in output (Docker outputs to stderr)
        combined_output = (result.stdout + result.stderr).lower()
        assert "success" in combined_output or "ros-mcp" in combined_output, (
            f"Build succeeded but output unexpected:\n{result.stdout}\n{result.stderr}"
        )

    finally:
        cleanup_docker_image(tag)


@pytest.mark.installation
@pytest.mark.slow
def test_uvx_install_with_transport_flag(
    repo_root: Path, docker_dir: Path, git_branch: str, repo_url: str
):
    """
    Test uvx ros-mcp with --transport=stdio flag as used in config examples.

    The documentation shows configuring Claude Desktop with:
    uvx ros-mcp --transport=stdio

    This verifies that flag works correctly when installed from git.
    """
    # Read and modify Dockerfile to test with transport flag
    dockerfile_content = (docker_dir / "Dockerfile.uvx").read_text()
    dockerfile_content = dockerfile_content.replace(
        'RUN uvx --from "git+${REPO_URL}@${BRANCH}" ros-mcp --help',
        'RUN uvx --from "git+${REPO_URL}@${BRANCH}" ros-mcp --transport=stdio --help',
    )

    temp_dockerfile = docker_dir / "Dockerfile.uvx-transport"
    temp_dockerfile.write_text(dockerfile_content)
    tag = "ros-mcp-test:uvx-transport"

    try:
        result = build_docker_image(
            dockerfile_path=temp_dockerfile,
            context_path=repo_root,
            tag=tag,
            build_args={
                "REPO_URL": repo_url,
                "BRANCH": git_branch,
            },
            timeout=300,
        )

        assert result.returncode == 0, (
            f"uvx installation with --transport=stdio failed (branch: {git_branch}):\n"
            f"STDOUT:\n{result.stdout}\n"
            f"STDERR:\n{result.stderr}"
        )

    finally:
        cleanup_docker_image(tag)
        if temp_dockerfile.exists():
            temp_dockerfile.unlink()
