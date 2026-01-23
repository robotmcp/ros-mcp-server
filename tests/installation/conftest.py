"""
Pytest configuration and fixtures for installation tests.

These tests use Docker to verify installation methods in clean environments.
"""

import subprocess
import pytest
from pathlib import Path


def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line(
        "markers", "installation: marks tests as installation tests (may be slow)"
    )


@pytest.fixture(scope="module")
def repo_root() -> Path:
    """Return path to repository root."""
    return Path(__file__).parent.parent.parent


@pytest.fixture(scope="module")
def docker_dir() -> Path:
    """Return path to docker directory containing Dockerfiles."""
    return Path(__file__).parent / "docker"


def docker_available() -> bool:
    """Check if Docker is available and functional on the system."""
    try:
        # First check if docker command exists
        result = subprocess.run(
            ["docker", "version"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode != 0:
            return False

        # Also verify we can actually use Docker (not just have the command)
        # This catches WSL2 cases where docker command exists but isn't connected
        result = subprocess.run(
            ["docker", "info"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        return result.returncode == 0
    except (subprocess.SubprocessError, FileNotFoundError):
        return False


@pytest.fixture(scope="module", autouse=True)
def require_docker():
    """Skip all tests if Docker is not available."""
    if not docker_available():
        pytest.skip("Docker is not available or not functional")


def build_docker_image(
    dockerfile_path: Path,
    context_path: Path,
    tag: str = None,
    build_args: dict = None,
    timeout: int = 300,
) -> subprocess.CompletedProcess:
    """
    Build a Docker image from a Dockerfile.

    Args:
        dockerfile_path: Path to the Dockerfile
        context_path: Path to the build context (usually repo root)
        tag: Optional tag for the image
        build_args: Optional dict of build arguments
        timeout: Build timeout in seconds (default 5 minutes)

    Returns:
        CompletedProcess with build output
    """
    cmd = ["docker", "build", "-f", str(dockerfile_path)]

    if tag:
        cmd.extend(["-t", tag])

    if build_args:
        for key, value in build_args.items():
            cmd.extend(["--build-arg", f"{key}={value}"])

    cmd.append(str(context_path))

    return subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=timeout,
    )


def run_docker_container(
    image: str,
    command: str = None,
    timeout: int = 60,
) -> subprocess.CompletedProcess:
    """
    Run a Docker container.

    Args:
        image: Image name or tag to run
        command: Optional command to run in container
        timeout: Run timeout in seconds

    Returns:
        CompletedProcess with run output
    """
    cmd = ["docker", "run", "--rm", image]

    if command:
        cmd.extend(["sh", "-c", command])

    return subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=timeout,
    )


def cleanup_docker_image(tag: str) -> None:
    """Remove a Docker image by tag."""
    subprocess.run(
        ["docker", "rmi", "-f", tag],
        capture_output=True,
        timeout=30,
    )
