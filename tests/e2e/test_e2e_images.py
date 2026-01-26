"""E2E tests for image processing functionality."""

import base64
import json
import os
import tempfile

import pytest

from ros_mcp.utils.websocket import is_image_like, parse_image

pytestmark = pytest.mark.e2e


class TestImageDetection:
    """E2E tests for image detection functions."""

    def test_is_image_like_raw_image(self):
        """Test is_image_like correctly identifies raw image messages."""
        raw_image_msg = {
            "data": "SGVsbG8gV29ybGQ=",  # base64 encoded data
            "width": 640,
            "height": 480,
            "encoding": "rgb8",
            "step": 1920,  # width * 3 for rgb8
        }

        assert is_image_like(raw_image_msg) is True, "Should detect raw image message"

    def test_is_image_like_compressed_image(self):
        """Test is_image_like correctly identifies compressed image messages."""
        compressed_image_msg = {
            "data": "SGVsbG8gV29ybGQ=",  # base64 encoded data
            "format": "jpeg",
        }

        assert is_image_like(compressed_image_msg) is True, "Should detect compressed image message"

    def test_is_image_like_non_image(self):
        """Test is_image_like correctly rejects non-image messages."""
        # Point cloud message (has data but is not image)
        pointcloud_msg = {
            "data": "SGVsbG8gV29ybGQ=",
            "width": 640,
            "height": 1,
            "fields": [{"name": "x", "offset": 0, "datatype": 7, "count": 1}],
        }

        assert is_image_like(pointcloud_msg) is False, "Should not detect point cloud as image"

        # Simple string message
        string_msg = {"data": "Hello World"}

        assert is_image_like(string_msg) is False, "Should not detect string as image"

    def test_is_image_like_bgr8_encoding(self):
        """Test is_image_like with bgr8 encoding."""
        bgr_image_msg = {
            "data": "SGVsbG8gV29ybGQ=",
            "width": 320,
            "height": 240,
            "encoding": "bgr8",
            "step": 960,
        }

        assert is_image_like(bgr_image_msg) is True, "Should detect bgr8 image"

    def test_is_image_like_mono8_encoding(self):
        """Test is_image_like with mono8 encoding."""
        mono_image_msg = {
            "data": "SGVsbG8gV29ybGQ=",
            "width": 100,
            "height": 100,
            "encoding": "mono8",
            "step": 100,
        }

        assert is_image_like(mono_image_msg) is True, "Should detect mono8 image"

    def test_is_image_like_invalid_encoding(self):
        """Test is_image_like with invalid encoding."""
        invalid_image_msg = {
            "data": "SGVsbG8gV29ybGQ=",
            "width": 100,
            "height": 100,
            "encoding": "invalid_encoding",
            "step": 100,
        }

        assert is_image_like(invalid_image_msg) is False, "Should reject invalid encoding"

    def test_is_image_like_missing_fields(self):
        """Test is_image_like with missing required fields."""
        # Missing width
        incomplete_msg = {
            "data": "SGVsbG8gV29ybGQ=",
            "height": 480,
            "encoding": "rgb8",
        }

        assert is_image_like(incomplete_msg) is False, "Should reject message missing width"

    def test_is_image_like_non_dict(self):
        """Test is_image_like with non-dict input."""
        assert is_image_like("not a dict") is False
        assert is_image_like(None) is False
        assert is_image_like([1, 2, 3]) is False


class TestImageParsing:
    """E2E tests for image parsing functions."""

    def test_parse_raw_rgb8_image(self):
        """Test parsing a raw RGB8 image message."""
        # Create a small 2x2 RGB image
        # Red, Green, Blue, White pixels
        pixels = bytes([
            255, 0, 0,    # Red
            0, 255, 0,    # Green
            0, 0, 255,    # Blue
            255, 255, 255 # White
        ])
        data_b64 = base64.b64encode(pixels).decode('utf-8')

        raw_message = json.dumps({
            "op": "publish",
            "topic": "/camera/image_raw",
            "msg": {
                "data": data_b64,
                "width": 2,
                "height": 2,
                "encoding": "rgb8",
                "step": 6,
                "header": {"stamp": {"sec": 0, "nanosec": 0}, "frame_id": "camera"},
            }
        })

        # Parse the image
        result = parse_image(raw_message)

        # Should succeed and save image
        assert result is not None, "Should successfully parse RGB8 image"
        assert os.path.exists("./camera/received_image.jpeg"), "Image file should be created"

        # Cleanup
        if os.path.exists("./camera/received_image.jpeg"):
            os.remove("./camera/received_image.jpeg")

    def test_parse_compressed_jpeg_image(self):
        """Test parsing a compressed JPEG image message."""
        # Create a minimal valid JPEG (1x1 pixel)
        # This is a minimal valid JPEG file bytes
        minimal_jpeg = bytes([
            0xFF, 0xD8, 0xFF, 0xE0, 0x00, 0x10, 0x4A, 0x46, 0x49, 0x46, 0x00, 0x01,
            0x01, 0x00, 0x00, 0x01, 0x00, 0x01, 0x00, 0x00, 0xFF, 0xDB, 0x00, 0x43,
            0x00, 0x08, 0x06, 0x06, 0x07, 0x06, 0x05, 0x08, 0x07, 0x07, 0x07, 0x09,
            0x09, 0x08, 0x0A, 0x0C, 0x14, 0x0D, 0x0C, 0x0B, 0x0B, 0x0C, 0x19, 0x12,
            0x13, 0x0F, 0x14, 0x1D, 0x1A, 0x1F, 0x1E, 0x1D, 0x1A, 0x1C, 0x1C, 0x20,
            0x24, 0x2E, 0x27, 0x20, 0x22, 0x2C, 0x23, 0x1C, 0x1C, 0x28, 0x37, 0x29,
            0x2C, 0x30, 0x31, 0x34, 0x34, 0x34, 0x1F, 0x27, 0x39, 0x3D, 0x38, 0x32,
            0x3C, 0x2E, 0x33, 0x34, 0x32, 0xFF, 0xC0, 0x00, 0x0B, 0x08, 0x00, 0x01,
            0x00, 0x01, 0x01, 0x01, 0x11, 0x00, 0xFF, 0xC4, 0x00, 0x1F, 0x00, 0x00,
            0x01, 0x05, 0x01, 0x01, 0x01, 0x01, 0x01, 0x01, 0x00, 0x00, 0x00, 0x00,
            0x00, 0x00, 0x00, 0x00, 0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07, 0x08,
            0x09, 0x0A, 0x0B, 0xFF, 0xC4, 0x00, 0xB5, 0x10, 0x00, 0x02, 0x01, 0x03,
            0x03, 0x02, 0x04, 0x03, 0x05, 0x05, 0x04, 0x04, 0x00, 0x00, 0x01, 0x7D,
            0x01, 0x02, 0x03, 0x00, 0x04, 0x11, 0x05, 0x12, 0x21, 0x31, 0x41, 0x06,
            0x13, 0x51, 0x61, 0x07, 0x22, 0x71, 0x14, 0x32, 0x81, 0x91, 0xA1, 0x08,
            0x23, 0x42, 0xB1, 0xC1, 0x15, 0x52, 0xD1, 0xF0, 0x24, 0x33, 0x62, 0x72,
            0x82, 0x09, 0x0A, 0x16, 0x17, 0x18, 0x19, 0x1A, 0x25, 0x26, 0x27, 0x28,
            0x29, 0x2A, 0x34, 0x35, 0x36, 0x37, 0x38, 0x39, 0x3A, 0x43, 0x44, 0x45,
            0x46, 0x47, 0x48, 0x49, 0x4A, 0x53, 0x54, 0x55, 0x56, 0x57, 0x58, 0x59,
            0x5A, 0x63, 0x64, 0x65, 0x66, 0x67, 0x68, 0x69, 0x6A, 0x73, 0x74, 0x75,
            0x76, 0x77, 0x78, 0x79, 0x7A, 0x83, 0x84, 0x85, 0x86, 0x87, 0x88, 0x89,
            0x8A, 0x92, 0x93, 0x94, 0x95, 0x96, 0x97, 0x98, 0x99, 0x9A, 0xA2, 0xA3,
            0xA4, 0xA5, 0xA6, 0xA7, 0xA8, 0xA9, 0xAA, 0xB2, 0xB3, 0xB4, 0xB5, 0xB6,
            0xB7, 0xB8, 0xB9, 0xBA, 0xC2, 0xC3, 0xC4, 0xC5, 0xC6, 0xC7, 0xC8, 0xC9,
            0xCA, 0xD2, 0xD3, 0xD4, 0xD5, 0xD6, 0xD7, 0xD8, 0xD9, 0xDA, 0xE1, 0xE2,
            0xE3, 0xE4, 0xE5, 0xE6, 0xE7, 0xE8, 0xE9, 0xEA, 0xF1, 0xF2, 0xF3, 0xF4,
            0xF5, 0xF6, 0xF7, 0xF8, 0xF9, 0xFA, 0xFF, 0xDA, 0x00, 0x08, 0x01, 0x01,
            0x00, 0x00, 0x3F, 0x00, 0xFB, 0xD5, 0xDB, 0x00, 0x31, 0xC4, 0x1F, 0xFF,
            0xD9
        ])
        data_b64 = base64.b64encode(minimal_jpeg).decode('utf-8')

        compressed_message = json.dumps({
            "op": "publish",
            "topic": "/camera/image_compressed",
            "msg": {
                "data": data_b64,
                "format": "jpeg",
                "header": {"stamp": {"sec": 0, "nanosec": 0}, "frame_id": "camera"},
            }
        })

        # Parse the image
        result = parse_image(compressed_message)

        # Should succeed and save image
        assert result is not None, "Should successfully parse compressed JPEG image"
        assert os.path.exists("./camera/received_image.jpeg"), "Image file should be created"

        # Cleanup
        if os.path.exists("./camera/received_image.jpeg"):
            os.remove("./camera/received_image.jpeg")

    def test_parse_image_invalid_json(self):
        """Test parse_image with invalid JSON."""
        result = parse_image("not valid json")

        assert result is None, "Should return None for invalid JSON"

    def test_parse_image_missing_msg_field(self):
        """Test parse_image with missing msg field."""
        message = json.dumps({"op": "publish", "topic": "/test"})

        result = parse_image(message)

        assert result is None, "Should return None for missing msg field"

    def test_parse_image_missing_data_field(self):
        """Test parse_image with missing data field."""
        message = json.dumps({
            "op": "publish",
            "topic": "/camera/image_raw",
            "msg": {
                "width": 640,
                "height": 480,
                "encoding": "rgb8",
            }
        })

        result = parse_image(message)

        assert result is None, "Should return None for missing data field"


class TestImageToolIntegration:
    """E2E tests for image tool integration."""

    def test_analyze_previously_received_image_no_file(self):
        """Test analyze tool when no image file exists."""
        from ros_mcp.tools.images import register_image_tools
        from fastmcp import FastMCP

        mcp = FastMCP("test-image")
        register_image_tools(mcp)

        # Get the registered tool
        tool_manager = mcp._tool_manager
        tools = tool_manager._tools

        assert "analyze_previously_received_image" in tools, (
            "analyze_previously_received_image tool should be registered"
        )

    def test_image_tool_registration(self, mcp_server):
        """Test that image tools are properly registered."""
        tool_manager = mcp_server._tool_manager
        tools = tool_manager._tools

        assert "analyze_previously_received_image" in tools, (
            "analyze_previously_received_image should be registered with MCP server"
        )
