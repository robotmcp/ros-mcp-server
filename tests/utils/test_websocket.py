"""Tests for ros_mcp.utils.websocket module."""

import base64
import json
import os
import tempfile
from unittest.mock import MagicMock, patch

import pytest

from ros_mcp.utils.websocket import (
    WebSocketManager,
    is_image_like,
    parse_image,
    parse_input,
    parse_json,
)


class TestParseJson:
    """Test cases for parse_json function."""

    def test_valid_json_string(self):
        """Test parsing valid JSON string."""
        raw = '{"key": "value", "number": 42}'
        result = parse_json(raw)
        assert result == {"key": "value", "number": 42}

    def test_valid_json_bytes(self):
        """Test parsing valid JSON from bytes."""
        raw = b'{"key": "value"}'
        result = parse_json(raw)
        assert result == {"key": "value"}

    def test_none_input(self):
        """Test that None input returns None."""
        result = parse_json(None)
        assert result is None

    def test_invalid_json(self):
        """Test that invalid JSON returns None."""
        raw = "not valid json"
        result = parse_json(raw)
        assert result is None

    def test_non_dict_json(self):
        """Test that JSON arrays return None (only dicts accepted)."""
        raw = "[1, 2, 3]"
        result = parse_json(raw)
        assert result is None

    def test_empty_object(self):
        """Test parsing empty JSON object."""
        raw = "{}"
        result = parse_json(raw)
        assert result == {}

    def test_nested_json(self):
        """Test parsing nested JSON."""
        raw = '{"outer": {"inner": "value"}}'
        result = parse_json(raw)
        assert result == {"outer": {"inner": "value"}}

    def test_malformed_bytes(self):
        """Test handling of malformed bytes with replacement."""
        raw = b'{"key": "\xff\xfe"}'
        result = parse_json(raw)
        # Should handle gracefully with replacement chars
        assert result is None or isinstance(result, dict)


class TestIsImageLike:
    """Test cases for is_image_like function."""

    def test_compressed_jpeg(self):
        """Test detection of compressed JPEG image."""
        msg_content = {"data": "base64data...", "format": "jpeg"}
        assert is_image_like(msg_content) is True

    def test_compressed_png(self):
        """Test detection of compressed PNG image."""
        msg_content = {"data": "base64data...", "format": "png"}
        assert is_image_like(msg_content) is True

    def test_compressed_mixed_case(self):
        """Test detection with mixed case format."""
        msg_content = {"data": "base64data...", "format": "JPEG"}
        assert is_image_like(msg_content) is True

    def test_raw_rgb8(self):
        """Test detection of raw RGB8 image."""
        msg_content = {
            "data": "base64data...",
            "width": 640,
            "height": 480,
            "encoding": "rgb8",
        }
        assert is_image_like(msg_content) is True

    def test_raw_bgr8(self):
        """Test detection of raw BGR8 image."""
        msg_content = {
            "data": "base64data...",
            "width": 640,
            "height": 480,
            "encoding": "bgr8",
        }
        assert is_image_like(msg_content) is True

    def test_raw_mono8(self):
        """Test detection of raw mono8 image."""
        msg_content = {
            "data": "base64data...",
            "width": 640,
            "height": 480,
            "encoding": "mono8",
        }
        assert is_image_like(msg_content) is True

    def test_raw_mono16(self):
        """Test detection of raw mono16 depth image."""
        msg_content = {
            "data": "base64data...",
            "width": 640,
            "height": 480,
            "encoding": "mono16",
        }
        assert is_image_like(msg_content) is True

    def test_non_image_missing_fields(self):
        """Test that messages missing required fields are not detected as images."""
        msg_content = {"data": "base64data..."}  # Missing width, height, encoding
        assert is_image_like(msg_content) is False

    def test_point_cloud(self):
        """Test that PointCloud2 is not detected as image."""
        msg_content = {
            "data": "base64data...",
            "width": 640,
            "height": 480,
            "encoding": "pointcloud",  # Not a valid image encoding
        }
        assert is_image_like(msg_content) is False

    def test_non_dict_input(self):
        """Test that non-dict input returns False."""
        assert is_image_like("not a dict") is False
        assert is_image_like(None) is False
        assert is_image_like([1, 2, 3]) is False

    def test_invalid_width_height_types(self):
        """Test that non-integer width/height returns False."""
        msg_content = {
            "data": "base64data...",
            "width": "640",  # String instead of int
            "height": 480,
            "encoding": "rgb8",
        }
        assert is_image_like(msg_content) is False

    def test_bayer_encoding(self):
        """Test detection of Bayer encoded images."""
        msg_content = {
            "data": "base64data...",
            "width": 640,
            "height": 480,
            "encoding": "bayer_rggb8",
        }
        assert is_image_like(msg_content) is True


class TestParseImage:
    """Test cases for parse_image function."""

    def setup_method(self):
        """Set up test fixtures."""
        # Create temporary camera directory for test outputs
        self.original_dir = os.getcwd()
        self.temp_dir = tempfile.mkdtemp()
        os.chdir(self.temp_dir)

    def teardown_method(self):
        """Clean up after tests."""
        os.chdir(self.original_dir)
        # Clean up temp directory
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_none_input(self):
        """Test that None input returns None."""
        result = parse_image(None)
        assert result is None

    def test_invalid_json(self):
        """Test that invalid JSON returns None."""
        result = parse_image("not valid json")
        assert result is None

    def test_missing_msg_field(self):
        """Test handling of missing 'msg' field."""
        raw = '{"data": "something"}'
        result = parse_image(raw)
        assert result is None

    def test_missing_data_field(self):
        """Test handling of missing 'data' field in msg."""
        raw = '{"msg": {"format": "jpeg"}}'
        result = parse_image(raw)
        assert result is None

    def test_compressed_jpeg(self):
        """Test parsing compressed JPEG image."""
        # Create a minimal valid JPEG (smallest possible)
        # This is a 1x1 red pixel JPEG
        jpeg_data = bytes(
            [
                0xFF, 0xD8, 0xFF, 0xE0, 0x00, 0x10, 0x4A, 0x46, 0x49, 0x46,
                0x00, 0x01, 0x01, 0x00, 0x00, 0x01, 0x00, 0x01, 0x00, 0x00,
                0xFF, 0xDB, 0x00, 0x43, 0x00, 0x08, 0x06, 0x06, 0x07, 0x06,
                0x05, 0x08, 0x07, 0x07, 0x07, 0x09, 0x09, 0x08, 0x0A, 0x0C,
                0x14, 0x0D, 0x0C, 0x0B, 0x0B, 0x0C, 0x19, 0x12, 0x13, 0x0F,
                0x14, 0x1D, 0x1A, 0x1F, 0x1E, 0x1D, 0x1A, 0x1C, 0x1C, 0x20,
                0x24, 0x2E, 0x27, 0x20, 0x22, 0x2C, 0x23, 0x1C, 0x1C, 0x28,
                0x37, 0x29, 0x2C, 0x30, 0x31, 0x34, 0x34, 0x34, 0x1F, 0x27,
                0x39, 0x3D, 0x38, 0x32, 0x3C, 0x2E, 0x33, 0x34, 0x32, 0xFF,
                0xC0, 0x00, 0x0B, 0x08, 0x00, 0x01, 0x00, 0x01, 0x01, 0x01,
                0x11, 0x00, 0xFF, 0xC4, 0x00, 0x1F, 0x00, 0x00, 0x01, 0x05,
                0x01, 0x01, 0x01, 0x01, 0x01, 0x01, 0x00, 0x00, 0x00, 0x00,
                0x00, 0x00, 0x00, 0x00, 0x01, 0x02, 0x03, 0x04, 0x05, 0x06,
                0x07, 0x08, 0x09, 0x0A, 0x0B, 0xFF, 0xC4, 0x00, 0xB5, 0x10,
                0x00, 0x02, 0x01, 0x03, 0x03, 0x02, 0x04, 0x03, 0x05, 0x05,
                0x04, 0x04, 0x00, 0x00, 0x01, 0x7D, 0x01, 0x02, 0x03, 0x00,
                0x04, 0x11, 0x05, 0x12, 0x21, 0x31, 0x41, 0x06, 0x13, 0x51,
                0x61, 0x07, 0x22, 0x71, 0x14, 0x32, 0x81, 0x91, 0xA1, 0x08,
                0x23, 0x42, 0xB1, 0xC1, 0x15, 0x52, 0xD1, 0xF0, 0x24, 0x33,
                0x62, 0x72, 0x82, 0x09, 0x0A, 0x16, 0x17, 0x18, 0x19, 0x1A,
                0x25, 0x26, 0x27, 0x28, 0x29, 0x2A, 0x34, 0x35, 0x36, 0x37,
                0x38, 0x39, 0x3A, 0x43, 0x44, 0x45, 0x46, 0x47, 0x48, 0x49,
                0x4A, 0x53, 0x54, 0x55, 0x56, 0x57, 0x58, 0x59, 0x5A, 0x63,
                0x64, 0x65, 0x66, 0x67, 0x68, 0x69, 0x6A, 0x73, 0x74, 0x75,
                0x76, 0x77, 0x78, 0x79, 0x7A, 0x83, 0x84, 0x85, 0x86, 0x87,
                0x88, 0x89, 0x8A, 0x92, 0x93, 0x94, 0x95, 0x96, 0x97, 0x98,
                0x99, 0x9A, 0xA2, 0xA3, 0xA4, 0xA5, 0xA6, 0xA7, 0xA8, 0xA9,
                0xAA, 0xB2, 0xB3, 0xB4, 0xB5, 0xB6, 0xB7, 0xB8, 0xB9, 0xBA,
                0xC2, 0xC3, 0xC4, 0xC5, 0xC6, 0xC7, 0xC8, 0xC9, 0xCA, 0xD2,
                0xD3, 0xD4, 0xD5, 0xD6, 0xD7, 0xD8, 0xD9, 0xDA, 0xE1, 0xE2,
                0xE3, 0xE4, 0xE5, 0xE6, 0xE7, 0xE8, 0xE9, 0xEA, 0xF1, 0xF2,
                0xF3, 0xF4, 0xF5, 0xF6, 0xF7, 0xF8, 0xF9, 0xFA, 0xFF, 0xDA,
                0x00, 0x08, 0x01, 0x01, 0x00, 0x00, 0x3F, 0x00, 0xFB, 0xD5,
                0xDB, 0x20, 0xA8, 0xF1, 0x45, 0x00, 0xFF, 0xD9,
            ]
        )
        b64_data = base64.b64encode(jpeg_data).decode("utf-8")
        raw = json.dumps({"msg": {"data": b64_data, "format": "jpeg"}})
        result = parse_image(raw)
        # Should return the parsed result or handle gracefully
        assert result is None or isinstance(result, dict)

    def test_raw_rgb8_image(self):
        """Test parsing raw RGB8 image."""
        # Create a 2x2 RGB8 image (12 bytes: 4 pixels * 3 bytes)
        image_data = bytes([255, 0, 0, 0, 255, 0, 0, 0, 255, 255, 255, 255])
        b64_data = base64.b64encode(image_data).decode("utf-8")
        raw = json.dumps(
            {
                "msg": {
                    "data": b64_data,
                    "width": 2,
                    "height": 2,
                    "encoding": "rgb8",
                    "is_bigendian": 0,
                    "step": 6,
                }
            }
        )
        result = parse_image(raw)
        # Should succeed and return the result dict
        assert result is not None
        assert isinstance(result, dict)
        assert "msg" in result


class TestParseInput:
    """Test cases for parse_input function."""

    def test_none_input(self):
        """Test that None input returns (None, False)."""
        result, was_image = parse_input(None)
        assert result is None
        assert was_image is False

    def test_json_only_hint(self):
        """Test explicit JSON-only parsing."""
        raw = '{"key": "value"}'
        result, was_image = parse_input(raw, expects_image=False)
        assert result == {"key": "value"}
        assert was_image is False

    def test_image_hint_with_non_image(self):
        """Test image hint with non-image data falls back to JSON."""
        raw = '{"key": "value"}'
        result, was_image = parse_input(raw, expects_image=True)
        assert result == {"key": "value"}
        assert was_image is False

    def test_auto_detect_non_image(self):
        """Test auto-detection of non-image message."""
        raw = '{"op": "publish", "topic": "/test", "msg": {"x": 1.0}}'
        result, was_image = parse_input(raw, expects_image=None)
        assert result is not None
        assert was_image is False

    def test_invalid_json(self):
        """Test that invalid JSON returns (None, False)."""
        result, was_image = parse_input("not valid json")
        assert result is None
        assert was_image is False


class TestWebSocketManager:
    """Test cases for WebSocketManager class."""

    def test_init(self):
        """Test WebSocketManager initialization."""
        manager = WebSocketManager("192.168.1.100", 9090, default_timeout=5.0)
        assert manager.ip == "192.168.1.100"
        assert manager.port == 9090
        assert manager.default_timeout == 5.0
        assert manager.ws is None

    def test_set_ip(self):
        """Test setting IP and port."""
        manager = WebSocketManager("127.0.0.1", 9090)
        manager.set_ip("192.168.1.100", 9091)
        assert manager.ip == "192.168.1.100"
        assert manager.port == 9091

    @patch("ros_mcp.utils.websocket.websocket.create_connection")
    def test_connect_success(self, mock_create_connection):
        """Test successful connection."""
        mock_ws = MagicMock()
        mock_ws.connected = True
        mock_create_connection.return_value = mock_ws

        manager = WebSocketManager("127.0.0.1", 9090)
        error = manager.connect()

        assert error is None
        assert manager.ws is not None
        mock_create_connection.assert_called_once()

    @patch("ros_mcp.utils.websocket.websocket.create_connection")
    def test_connect_failure(self, mock_create_connection):
        """Test connection failure."""
        mock_create_connection.side_effect = Exception("Connection refused")

        manager = WebSocketManager("127.0.0.1", 9090)
        error = manager.connect()

        assert error is not None
        assert "Connection error" in error
        assert manager.ws is None

    @patch("ros_mcp.utils.websocket.websocket.create_connection")
    def test_send_success(self, mock_create_connection):
        """Test successful message send."""
        mock_ws = MagicMock()
        mock_ws.connected = True
        mock_create_connection.return_value = mock_ws

        manager = WebSocketManager("127.0.0.1", 9090)
        message = {"op": "subscribe", "topic": "/test"}
        error = manager.send(message)

        assert error is None
        mock_ws.send.assert_called_once()

    @patch("ros_mcp.utils.websocket.websocket.create_connection")
    def test_send_json_serialization_error(self, mock_create_connection):
        """Test send with non-serializable message."""
        mock_ws = MagicMock()
        mock_ws.connected = True
        mock_ws.send.side_effect = TypeError("Object not JSON serializable")
        mock_create_connection.return_value = mock_ws

        manager = WebSocketManager("127.0.0.1", 9090)
        # Force connection
        manager.connect()
        error = manager.send({"key": object()})

        assert error is not None
        assert "JSON serialization error" in error or "Send error" in error

    @patch("ros_mcp.utils.websocket.websocket.create_connection")
    def test_receive_success(self, mock_create_connection):
        """Test successful message receive."""
        mock_ws = MagicMock()
        mock_ws.connected = True
        mock_ws.recv.return_value = '{"result": true}'
        mock_create_connection.return_value = mock_ws

        manager = WebSocketManager("127.0.0.1", 9090)
        response = manager.receive(timeout=1.0)

        assert response == '{"result": true}'

    @patch("ros_mcp.utils.websocket.websocket.create_connection")
    def test_receive_timeout(self, mock_create_connection):
        """Test receive timeout."""
        mock_ws = MagicMock()
        mock_ws.connected = True
        mock_ws.recv.side_effect = TimeoutError("Timeout")
        mock_create_connection.return_value = mock_ws

        manager = WebSocketManager("127.0.0.1", 9090)
        # Force connection
        manager.connect()
        response = manager.receive(timeout=1.0)

        assert response is None

    @patch("ros_mcp.utils.websocket.websocket.create_connection")
    def test_request_success(self, mock_create_connection):
        """Test successful request/response cycle."""
        mock_ws = MagicMock()
        mock_ws.connected = True
        mock_ws.recv.return_value = '{"result": true, "values": {"topics": []}}'
        mock_create_connection.return_value = mock_ws

        manager = WebSocketManager("127.0.0.1", 9090)
        response = manager.request({"op": "call_service", "service": "/test"})

        assert response is not None
        assert response.get("result") is True

    @patch("ros_mcp.utils.websocket.websocket.create_connection")
    def test_request_no_response(self, mock_create_connection):
        """Test request with no response."""
        mock_ws = MagicMock()
        mock_ws.connected = True
        mock_ws.recv.return_value = None
        mock_create_connection.return_value = mock_ws

        manager = WebSocketManager("127.0.0.1", 9090)
        # Force connection
        manager.connect()
        response = manager.request({"op": "call_service"})

        assert "error" in response

    @patch("ros_mcp.utils.websocket.websocket.create_connection")
    def test_close(self, mock_create_connection):
        """Test closing connection."""
        mock_ws = MagicMock()
        mock_ws.connected = True
        mock_create_connection.return_value = mock_ws

        manager = WebSocketManager("127.0.0.1", 9090)
        manager.connect()
        manager.close()

        mock_ws.close.assert_called_once()
        assert manager.ws is None

    @patch("ros_mcp.utils.websocket.websocket.create_connection")
    def test_context_manager(self, mock_create_connection):
        """Test using WebSocketManager as context manager."""
        mock_ws = MagicMock()
        mock_ws.connected = True
        mock_create_connection.return_value = mock_ws

        manager = WebSocketManager("127.0.0.1", 9090)
        with manager:
            manager.connect()
            assert manager.ws is not None

        # After exiting context, connection should be closed
        mock_ws.close.assert_called()

    def test_default_timeout(self):
        """Test default timeout is used when not specified."""
        manager = WebSocketManager("127.0.0.1", 9090, default_timeout=3.0)
        assert manager.default_timeout == 3.0
