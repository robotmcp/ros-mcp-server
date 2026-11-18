"""Raw sensor_msgs/Image rows may contain padding, as specified by step."""

import base64
import json

import cv2
import numpy as np
import pytest

from ros_mcp.utils.websocket import parse_input


@pytest.mark.parametrize("encoding", ["rgb8", "bgr8", "mono8", "mono16", "16UC1"])
@pytest.mark.parametrize("padding", [0, 1, 4])
@pytest.mark.parametrize("hint", [None, True])
def test_raw_image_row_padding(tmp_path, monkeypatch, encoding, padding, hint):
    monkeypatch.setenv("ROS_MCP_IMAGE_DIR", str(tmp_path))
    channels = 3 if encoding in ("rgb8", "bgr8") else 1
    dtype = np.uint16 if encoding.lower() in ("mono16", "16uc1") else np.uint8
    shape = (3, 5, 3) if channels == 3 else (3, 5)
    pixels = (np.arange(np.prod(shape)).reshape(shape) * 13).astype(dtype)
    rows = [row.tobytes() for row in pixels]
    row_bytes = len(rows[0])
    msg = {
        "height": 3,
        "width": 5,
        "encoding": encoding,
        "is_bigendian": 0,
        "step": row_bytes + padding,
        "data": base64.b64encode(b"".join(row + b"\xee" * padding for row in rows)).decode(),
    }
    frame = {"op": "publish", "topic": "/camera/image", "msg": msg}
    expected = pixels
    if encoding == "rgb8":
        expected = cv2.cvtColor(pixels, cv2.COLOR_RGB2BGR)
    elif dtype == np.uint16:
        expected = cv2.normalize(pixels, None, 0, 255, cv2.NORM_MINMAX, dtype=cv2.CV_8U)
    ok, encoded = cv2.imencode(".jpeg", expected, [cv2.IMWRITE_JPEG_QUALITY, 95])
    assert ok
    parsed, is_image = parse_input(json.dumps(frame), expects_image=hint)
    assert parsed == frame
    assert is_image
    assert (tmp_path / "received_image.jpeg").read_bytes() == encoded.tobytes()


@pytest.mark.parametrize(
    "step,data", [(4, bytes(8)), (6, bytes(11)), (6, bytes(13)), (0, bytes(12)), ("6", bytes(12))]
)
@pytest.mark.parametrize("hint", [None, True])
def test_invalid_row_layout_falls_back_to_json(tmp_path, monkeypatch, step, data, hint):
    monkeypatch.setenv("ROS_MCP_IMAGE_DIR", str(tmp_path))
    frame = {
        "op": "publish",
        "topic": "/camera/image",
        "msg": {
            "height": 2,
            "width": 5,
            "encoding": "mono8",
            "step": step,
            "data": base64.b64encode(data).decode(),
        },
    }
    assert parse_input(json.dumps(frame), expects_image=hint) == (frame, False)
    assert not (tmp_path / "received_image.jpeg").exists()


def test_missing_step_preserves_packed_image(tmp_path, monkeypatch):
    monkeypatch.setenv("ROS_MCP_IMAGE_DIR", str(tmp_path))
    pixels = np.arange(15, dtype=np.uint8).reshape(3, 5)
    frame = {
        "op": "publish",
        "topic": "/camera/image",
        "msg": {
            "height": 3,
            "width": 5,
            "encoding": "mono8",
            "data": base64.b64encode(pixels.tobytes()).decode(),
        },
    }
    assert parse_input(json.dumps(frame)) == (frame, True)
    ok, encoded = cv2.imencode(".jpeg", pixels, [cv2.IMWRITE_JPEG_QUALITY, 95])
    assert ok
    assert (tmp_path / "received_image.jpeg").read_bytes() == encoded.tobytes()


def test_compressed_image_unchanged(tmp_path, monkeypatch):
    monkeypatch.setenv("ROS_MCP_IMAGE_DIR", str(tmp_path))
    pixels = np.arange(15, dtype=np.uint8).reshape(3, 5)
    ok, encoded = cv2.imencode(".jpeg", pixels)
    assert ok
    frame = {
        "op": "publish",
        "topic": "/camera/image/compressed",
        "msg": {
            "format": "jpeg",
            "data": base64.b64encode(encoded.tobytes()).decode(),
        },
    }
    assert parse_input(json.dumps(frame)) == (frame, True)
    assert (tmp_path / "received_image.jpeg").read_bytes() == encoded.tobytes()
