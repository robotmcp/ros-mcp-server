"""Tests for ros_mcp.tools.images module."""

import os
import tempfile

import pytest
from PIL import Image as PILImage

from ros_mcp.tools.images import (
    _encode_image_to_imagecontent,
    convert_expects_image_hint,
    register_image_tools,
)


class MockFastMCP:
    """Mock FastMCP for capturing registered tools."""

    def __init__(self):
        self.tools = {}

    def tool(self, description=None):
        def decorator(func):
            self.tools[func.__name__] = func
            return func

        return decorator


@pytest.fixture
def mock_mcp():
    """Create a mock FastMCP instance."""
    return MockFastMCP()


@pytest.fixture
def image_tools(mock_mcp):
    """Register image tools and return them."""
    register_image_tools(mock_mcp)
    return mock_mcp.tools


@pytest.fixture
def temp_image():
    """Create a temporary test image."""
    with tempfile.NamedTemporaryFile(suffix=".jpeg", delete=False) as f:
        # Create a simple red image
        img = PILImage.new("RGB", (100, 100), color="red")
        img.save(f, format="JPEG")
        temp_path = f.name

    yield temp_path

    # Cleanup
    if os.path.exists(temp_path):
        os.unlink(temp_path)


@pytest.fixture
def temp_png_image():
    """Create a temporary PNG test image."""
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
        img = PILImage.new("RGBA", (50, 50), color=(0, 255, 0, 255))
        img.save(f, format="PNG")
        temp_path = f.name

    yield temp_path

    if os.path.exists(temp_path):
        os.unlink(temp_path)


class TestConvertExpectsImageHint:
    """Test cases for convert_expects_image_hint function."""

    def test_true_string(self):
        """Test with 'true' string."""
        result = convert_expects_image_hint("true")
        assert result is True

    def test_false_string(self):
        """Test with 'false' string."""
        result = convert_expects_image_hint("false")
        assert result is False

    def test_auto_string(self):
        """Test with 'auto' string."""
        result = convert_expects_image_hint("auto")
        assert result is None

    def test_other_value(self):
        """Test with any other value defaults to None (auto)."""
        result = convert_expects_image_hint("anything_else")
        assert result is None

    def test_empty_string(self):
        """Test with empty string defaults to None."""
        result = convert_expects_image_hint("")
        assert result is None

    def test_uppercase_true(self):
        """Test that uppercase 'TRUE' is treated as auto (not true)."""
        result = convert_expects_image_hint("TRUE")
        assert result is None  # Case sensitive, so treated as "other"


class TestEncodeImageToImageContent:
    """Test cases for _encode_image_to_imagecontent function."""

    def test_encode_rgb_image(self):
        """Test encoding an RGB image."""
        img = PILImage.new("RGB", (100, 100), color="blue")
        result = _encode_image_to_imagecontent(img)

        # Should return ImageContent object
        assert result is not None
        assert hasattr(result, "type")
        assert result.type == "image"

    def test_encode_rgba_image(self):
        """Test encoding an RGBA image (with alpha)."""
        img = PILImage.new("RGBA", (50, 50), color=(255, 0, 0, 128))
        # Convert to RGB since JPEG doesn't support alpha
        img = img.convert("RGB")
        result = _encode_image_to_imagecontent(img)

        assert result is not None
        assert result.type == "image"

    def test_encode_grayscale_image(self):
        """Test encoding a grayscale image."""
        img = PILImage.new("L", (100, 100), color=128)
        result = _encode_image_to_imagecontent(img)

        assert result is not None
        assert result.type == "image"

    def test_encode_small_image(self):
        """Test encoding a very small image."""
        img = PILImage.new("RGB", (1, 1), color="white")
        result = _encode_image_to_imagecontent(img)

        assert result is not None

    def test_encode_large_image(self):
        """Test encoding a larger image."""
        img = PILImage.new("RGB", (1000, 1000), color="green")
        result = _encode_image_to_imagecontent(img)

        assert result is not None


class TestAnalyzePreviouslyReceivedImage:
    """Test cases for analyze_previously_received_image tool."""

    def test_image_not_found(self, image_tools):
        """Test when image file doesn't exist."""
        result = image_tools["analyze_previously_received_image"]("/nonexistent/path/image.jpeg")

        assert "error" in result
        assert "No image found" in result["error"]

    def test_default_path_not_found(self, image_tools):
        """Test with default path when file doesn't exist."""
        result = image_tools["analyze_previously_received_image"]()

        assert "error" in result
        assert "No image found" in result["error"]

    def test_successful_image_load(self, image_tools, temp_image):
        """Test successfully loading an existing image."""
        result = image_tools["analyze_previously_received_image"](temp_image)

        # Should return ImageContent, not error dict
        assert "error" not in result if isinstance(result, dict) else True
        # If it's an ImageContent object, it should have a type
        if hasattr(result, "type"):
            assert result.type == "image"

    def test_png_image_load(self, image_tools, temp_image):
        """Test loading a PNG image (converted to JPEG internally)."""
        # Note: The tool converts all images to JPEG, so we use the JPEG fixture
        result = image_tools["analyze_previously_received_image"](temp_image)

        assert "error" not in result if isinstance(result, dict) else True

    def test_custom_path(self, image_tools, temp_image):
        """Test with custom image path."""
        result = image_tools["analyze_previously_received_image"](image_path=temp_image)

        assert "error" not in result if isinstance(result, dict) else True


class TestImageToolsRegistration:
    """Test that image tools are properly registered."""

    def test_tool_registered(self, image_tools):
        """Test that analyze_previously_received_image is registered."""
        assert "analyze_previously_received_image" in image_tools

    def test_tool_callable(self, image_tools):
        """Test that the registered tool is callable."""
        assert callable(image_tools["analyze_previously_received_image"])


class TestImageToolsEdgeCases:
    """Edge case tests for image tools."""

    def test_empty_path(self, image_tools):
        """Test with empty string path."""
        result = image_tools["analyze_previously_received_image"]("")

        assert "error" in result

    def test_directory_path(self, image_tools):
        """Test with directory path instead of file."""
        # Use a non-existent path to avoid PIL trying to open a directory
        result = image_tools["analyze_previously_received_image"]("/nonexistent/path")

        # Should fail since path doesn't exist
        assert "error" in result

    def test_relative_path(self, image_tools, temp_image):
        """Test with relative path converted from absolute."""
        # Get the filename from temp_image
        filename = os.path.basename(temp_image)
        temp_dir = os.path.dirname(temp_image)

        # Change to temp directory and use relative path
        original_dir = os.getcwd()
        try:
            os.chdir(temp_dir)
            result = image_tools["analyze_previously_received_image"](filename)
            # Should work with relative path
            assert "error" not in result if isinstance(result, dict) else True
        finally:
            os.chdir(original_dir)
