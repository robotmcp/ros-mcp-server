"""Path utilities for ROS MCP.

This module provides centralized path management for the ROS MCP server,
including camera directory and image file paths.
"""

import os
import tempfile
from pathlib import Path

try:
    from platformdirs import user_cache_dir
except ImportError:
    user_cache_dir = None


def get_camera_dir() -> Path:
    """
    Get the camera directory path.

    The directory is determined in the following priority order:
    1. ROS_MCP_CAMERA_DIR environment variable (if set)
    2. Platform-specific cache directory (if platformdirs is available)
       - Linux: ~/.cache/ros-mcp/camera/
       - macOS: ~/Library/Caches/ros-mcp/camera/
       - Windows: %LOCALAPPDATA%\\ros-mcp\\camera\\
    3. System temp directory as fallback
       - /tmp/ros-mcp/camera/ (Linux/macOS)
       - %TEMP%\\ros-mcp\\camera\\ (Windows)

    Returns:
        Path: Absolute path to the camera directory

    Examples:
        >>> camera_dir = get_camera_dir()
        >>> print(camera_dir)
        PosixPath('/home/user/.cache/ros-mcp/camera')
    """
    override = os.environ.get("ROS_MCP_CAMERA_DIR")
    if override:
        return Path(override).expanduser().resolve()

    if user_cache_dir is not None:
        return Path(user_cache_dir("ros-mcp", appauthor=False)) / "camera"

    return Path(tempfile.gettempdir()) / "ros-mcp" / "camera"


def get_fixed_image_path(filename: str = "received_image.jpeg") -> Path:
    """
    Get the fixed image path in the camera directory.

    This function ensures the camera directory exists before returning the path.
    It will create the directory if it doesn't exist.

    Args:
        filename (str): Name of the image file (default: "received_image.jpeg")

    Returns:
        Path: Absolute path to the image file

    Raises:
        RuntimeError: If the camera path exists but is not a directory,
                     or if directory creation fails

    Examples:
        >>> image_path = get_fixed_image_path()
        >>> print(image_path)
        PosixPath('/home/user/.cache/ros-mcp/camera/received_image.jpeg')

        >>> custom_path = get_fixed_image_path("my_image.jpg")
        >>> print(custom_path)
        PosixPath('/home/user/.cache/ros-mcp/camera/my_image.jpg')
    """
    camera_dir = get_camera_dir()

    if camera_dir.exists() and not camera_dir.is_dir():
        raise RuntimeError(f"Camera path exists but is not a directory: {camera_dir}")

    try:
        camera_dir.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        raise RuntimeError(f"Failed to create camera directory: {camera_dir}") from e

    return camera_dir / filename
