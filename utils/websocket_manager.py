import base64
import json
import os
import sys
import threading
from typing import Union

import cv2
import numpy as np
import websocket


def parse_json(raw: Union[str, bytes] | None) -> dict | None:
    """
    Safely parse JSON from string or bytes.

    Args:
        raw: JSON string, bytes, or None

    Returns:
        Parsed dict if successful, None if raw is None, parsing fails, or result is not a dict
    """
    if raw is None:
        return None
    if isinstance(raw, bytes):
        raw = raw.decode("utf-8", errors="replace")
    try:
        result = json.loads(raw)
        return result if isinstance(result, dict) else None
    except (json.JSONDecodeError, TypeError):
        return None


def is_image_like(msg_content: dict) -> bool:
    """
    Check if a message looks like an image message by examining its fields.

    This checks for image-specific fields (width, height, encoding) in addition
    to the data field to distinguish images from other messages that may contain
    binary data (e.g., PointCloud2, ByteMultiArray).

    Args:
        msg_content: The message content dictionary

    Returns:
        bool: True if the message appears to be an image, False otherwise
    """
    if not isinstance(msg_content, dict):
        return False

    # Check for CompressedImage format (has 'data' and 'format' fields)
    if "data" in msg_content and "format" in msg_content:
        format_str = msg_content.get("format", "").lower()
        if any(fmt in format_str for fmt in ["jpeg", "jpg", "png"]):
            return True

    # Check for raw Image format (has 'data', 'width', 'height', 'encoding')
    required_fields = {"data", "width", "height", "encoding"}
    if not required_fields.issubset(msg_content.keys()):
        return False

    # Validate field types
    if not isinstance(msg_content.get("width"), int) or not isinstance(
        msg_content.get("height"), int
    ):
        return False

    # Check for valid image encodings (sensor_msgs/Image standard encodings)
    encoding = msg_content.get("encoding", "").lower()
    valid_encodings = [
        "rgb8",
        "rgba8",
        "bgr8",
        "bgra8",
        "mono8",
        "mono16",
        "8uc1",
        "8uc3",
        "8uc4",
        "16uc1",
        "bayer",
        "yuv",
    ]
    if not any(enc in encoding for enc in valid_encodings):
        return False

    return True


def parse_image(raw: Union[str, bytes] | None) -> dict | None:
    """
    Decode an image message (json with base64 data) and save it as JPEG.

    Args:
        raw: JSON string, bytes, or None

    Returns:
        Parsed dict if successful, None if raw is None, parsing fails, or result is not a dict
    """

    if raw is None:
        return None

    try:
        result = json.loads(raw)
        msg = result["msg"]
    except (json.JSONDecodeError, KeyError):
        print("[Image] Invalid JSON or missing 'msg' field.", file=sys.stderr)
        return None

    data_b64 = msg.get("data")
    if not data_b64:
        print("[Image] Missing 'data' field in message.", file=sys.stderr)
        return None

    # ✅ Ensure output directory exists
    os.makedirs("./camera", exist_ok=True)

    # Case 1: CompressedImage (already JPEG/PNG encoded)
    if "format" in msg and msg["format"].lower() in ["jpeg", "jpg", "png"]:
        image_bytes = base64.b64decode(data_b64)
        path = "./camera/received_image.jpeg"
        with open(path, "wb") as f:
            f.write(image_bytes)
        print(f"[Image] Saved CompressedImage to {path}", file=sys.stderr)
        return result if isinstance(result, dict) else None

    # Case 2: Raw Image (rgb8, bgr8, mono8)
    height, width, encoding = msg.get("height"), msg.get("width"), msg.get("encoding")
    if not all([height, width, encoding]):
        print("[Image] Missing required fields for raw image.", file=sys.stderr)
        return None

    # Decode base64 to numpy array
    image_bytes = base64.b64decode(data_b64)
    img_np = np.frombuffer(image_bytes, dtype=np.uint8)

    # Encoding handlers
    try:
        if encoding == "rgb8":
            img_cv = img_np.reshape((height, width, 3))
            img_cv = cv2.cvtColor(img_cv, cv2.COLOR_RGB2BGR)
        elif encoding == "bgr8":
            img_cv = img_np.reshape((height, width, 3))
        elif encoding == "mono8":
            img_cv = img_np.reshape((height, width))
        else:
            print(f"[Image] Unsupported encoding: {encoding}", file=sys.stderr)
            return None
    except ValueError as e:
        print(f"[Image] Reshape error: {e}", file=sys.stderr)
        return None

    # Save as JPEG with quality 95
    success = cv2.imwrite("./camera/received_image.jpeg", img_cv, [cv2.IMWRITE_JPEG_QUALITY, 95])
    if success:
        print("[Image] Saved raw Image to ./camera/received_image.jpeg", file=sys.stderr)
        return result if isinstance(result, dict) else None
    else:
        return None


def parse_input(
    raw: Union[str, bytes] | None, expects_image: bool | None = None
) -> tuple[dict | None, bool]:
    """
    Parse input data with optional image hint for optimized handling.

    This function determines the parsing strategy based on the expects_image hint:
    - If expects_image=True: prioritize image parsing, fall back to JSON
    - If expects_image=False: parse as JSON only (faster for non-image data)
    - If expects_image=None: auto-detect based on message structure

    Args:
        raw: JSON string, bytes, or None
        expects_image: Optional hint about whether to expect image data

    Returns:
        tuple: (parsed_data, was_parsed_as_image)
            - parsed_data: Parsed dict if successful, None otherwise
            - was_parsed_as_image: True if data was successfully parsed as image
    """
    if raw is None:
        return None, False

    # Step 1: Auto-detect mode if not explicitly specified
    if expects_image is None:
        # Try to parse as JSON first to check structure
        temp_parsed = parse_json(raw)
        if temp_parsed and isinstance(temp_parsed, dict) and temp_parsed.get("op") == "publish":
            msg_content = temp_parsed.get("msg", {})
            expects_image = is_image_like(msg_content)
        else:
            expects_image = False

    # Step 2: Parse based on expected type with graceful fallback
    if expects_image:
        # Try image parsing first
        result = parse_image(raw)
        if result is not None:
            return result, True
        else:
            # Fallback to JSON if image parsing failed
            result = parse_json(raw)
            return result, False
    else:
        # Parse as JSON (faster for non-image data)
        result = parse_json(raw)
        return result, False


class WebSocketManager:
    def __init__(self, ip: str, port: int, default_timeout: float = 2.0):
        self.ip = ip
        self.port = port
        self.default_timeout = default_timeout
        self.ws = None
        self.lock = threading.RLock()

    def set_ip(self, ip: str, port: int):
        """
        Set the IP and port for the WebSocket connection.
        """
        self.ip = ip
        self.port = port
        print(f"[WebSocket] IP set to {self.ip}:{self.port}", file=sys.stderr)

    def connect(self) -> str | None:
        """
        Attempt to establish a WebSocket connection.

        Returns:
            None if successful,
            or an error message string if connection failed.
        """
        with self.lock:
            if self.ws is None or not self.ws.connected:
                try:
                    url = f"ws://{self.ip}:{self.port}"
                    self.ws = websocket.create_connection(url, timeout=self.default_timeout)
                    print(
                        f"[WebSocket] Connected ({self.default_timeout}s timeout)", file=sys.stderr
                    )
                    return None  # no error
                except Exception as e:
                    error_msg = f"[WebSocket] Connection error: {e}"
                    print(error_msg, file=sys.stderr)
                    self.ws = None
                    return error_msg
            return None  # already connected, no error

    def send(self, message: dict) -> str | None:
        """
        Send a JSON-serializable message over WebSocket.

        Returns:
            None if successful,
            or an error message string if send failed.
        """
        with self.lock:
            conn_error = self.connect()
            if conn_error:
                return conn_error  # failed to connect

            if self.ws:
                try:
                    json_msg = json.dumps(message)  # ensure it's JSON-serializable
                    self.ws.send(json_msg)
                    return None  # no error
                except TypeError as e:
                    error_msg = f"[WebSocket] JSON serialization error: {e}"
                    print(error_msg, file=sys.stderr)
                    self.close()
                    return error_msg
                except Exception as e:
                    error_msg = f"[WebSocket] Send error: {e}"
                    print(error_msg, file=sys.stderr)
                    self.close()
                    return error_msg

            return "[WebSocket] Not connected, send aborted."

    def receive(self, timeout: float | None = None) -> Union[str, bytes] | None:
        """
        Receive a single message from rosbridge within the given timeout.

        Args:
            timeout (float | None): Seconds to wait before timing out.
                                     If None, uses the default timeout.

        Returns:
            str | None: JSON string received from rosbridge, or None if timeout/error.
        """
        with self.lock:
            self.connect()
            if self.ws:
                try:
                    # Use default timeout if none specified
                    actual_timeout = timeout if timeout is not None else self.default_timeout
                    # Temporarily set the receive timeout
                    self.ws.settimeout(actual_timeout)
                    raw = self.ws.recv()  # rosbridge sends JSON as a string
                    return raw
                except Exception as e:
                    print(f"[WebSocket] Receive error or timeout: {e}", file=sys.stderr)
                    self.close()
                    return None
            return None

    def request(self, message: dict, timeout: float | None = None) -> dict:
        """
        Send a request to Rosbridge and return the response.

        Args:
            message (dict): The Rosbridge message dictionary to send.
            timeout (float | None): Seconds to wait for a response.
                                     If None, uses the default timeout.

        Returns:
            dict:
                - Parsed JSON response if successful.
                - {"error": "<error message>"} if connection/send/receive fails.
                - {"error": "invalid_json", "raw": <response>} if decoding fails.
        """
        # Attempt to send the message (connect() is called internally in send())
        send_error = self.send(message)
        if send_error:
            return {"error": send_error}

        # Attempt to receive a response (connect() is called internally in receive())
        response = self.receive(timeout=timeout)
        if response is None:
            return {"error": "no response or timeout from rosbridge"}

        # Attempt to parse response (auto-detect images, but services rarely return images)
        parsed_response, _ = parse_input(response, expects_image=None)
        if parsed_response is None:
            print(f"[WebSocket] JSON decode error for response: {response}", file=sys.stderr)
            return {"error": "invalid_json", "raw": response}
        return parsed_response

    def close(self):
        with self.lock:
            if self.ws and self.ws.connected:
                try:
                    self.ws.close()
                    print("[WebSocket] Closed", file=sys.stderr)
                except Exception as e:
                    print(f"[WebSocket] Close error: {e}", file=sys.stderr)
                finally:
                    self.ws = None

    def __enter__(self):
        """Context manager entry - automatically connects."""
        # Don't connect here since we want to maintain the existing pattern
        # where request() handles connection automatically
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - automatically closes the connection."""
        self.close()
