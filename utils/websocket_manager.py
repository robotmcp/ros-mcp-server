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
        if any(fmt in format_str for fmt in ["jpeg", "jpg", "png", "bmp", "compressed"]):
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
    # 1. Input validation
    if raw is None:
        return None

    # 2. Parse JSON and extract message
    try:
        result = json.loads(raw)
        msg = result["msg"]
    except (json.JSONDecodeError, KeyError):
        print("[Image] Invalid JSON or missing 'msg' field.", file=sys.stderr)
        return None

    # 3. Extract and validate required fields
    data_b64 = msg.get("data")
    if not data_b64:
        print("[Image] Missing 'data' field in message.", file=sys.stderr)
        return None

    # 4. Ensure output directory exists
    os.makedirs("./camera", exist_ok=True)

    # 5. Determine image type and process accordingly
    format = msg.get("format")
    print(f"[Image] Format: {format}", file=sys.stderr)

    # 5a. Handle CompressedImage (already JPEG/PNG encoded)
    if format and any(fmt in format.lower() for fmt in ["jpeg", "jpg", "png", "bmp", "compressed"]):
        return _handle_compressed_image(data_b64, result)

    # 5b. Handle Raw Image (rgb8, bgr8, mono8, mono16, 16uc1)
    height, width, encoding = msg.get("height"), msg.get("width"), msg.get("encoding")
    if not all([height, width, encoding]):
        print("[Image] Missing required fields for raw image.", file=sys.stderr)
        return None

    return _handle_raw_image(data_b64, height, width, encoding, msg, result)


def _handle_compressed_image(data_b64: str, result: dict) -> dict | None:
    """Handle compressed image data (JPEG/PNG already encoded)."""
    path = "./camera/received_image_compressed.jpeg"
    image_bytes = base64.b64decode(data_b64)

    with open(path, "wb") as f:
        f.write(image_bytes)

    print(f"[Image] Saved CompressedImage to {path}", file=sys.stderr)
    return result if isinstance(result, dict) else None


def _handle_raw_image(
    data_b64: str, height: int, width: int, encoding: str, msg: dict, result: dict
) -> dict | None:
    """Handle raw image data (needs decoding and conversion)."""
    # Decode base64 to numpy array
    image_bytes = base64.b64decode(data_b64)

    # Determine data type based on encoding
    if encoding.lower() in ["mono16", "16uc1"]:
        img_np = np.frombuffer(image_bytes, dtype=np.uint16)
    else:
        img_np = np.frombuffer(image_bytes, dtype=np.uint8)

    # Process based on encoding type
    try:
        img_cv = _decode_image_data(img_np, height, width, encoding, msg)
        if img_cv is None:
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


def _decode_image_data(
    img_np: np.ndarray, height: int, width: int, encoding: str, msg: dict
) -> np.ndarray | None:
    """Decode image data based on encoding type."""
    # 8-bit encodings
    if encoding == "rgb8":
        img_cv = img_np.reshape((height, width, 3))
        img_cv = cv2.cvtColor(img_cv, cv2.COLOR_RGB2BGR)
    elif encoding == "bgr8":
        img_cv = img_np.reshape((height, width, 3))
    elif encoding.lower() == "mono8":
        img_cv = img_np.reshape((height, width))
    # 16-bit encodings
    elif encoding.lower() in ["mono16", "16uc1"]:
        img16 = img_np.reshape((height, width))
        # Handle big-endian byte order if needed
        try:
            if int(msg.get("is_bigendian", 0)) == 1:
                img16 = img16.byteswap().newbyteorder()
        except Exception:
            # If field missing or not int-like, proceed without swapping
            pass

        # Normalize 16-bit depth to 8-bit [0,255] for saving/preview
        img_cv = cv2.normalize(img16, None, 0, 255, cv2.NORM_MINMAX, dtype=cv2.CV_8U)
    else:
        print(f"[Image] Unsupported encoding: {encoding}", file=sys.stderr)
        return None

    return img_cv


def parse_input(
    raw: Union[str, bytes] | None, expects_image: bool | None = None
) -> tuple[dict | None, bool]:
    """
    Parse input data with optional image hint for optimized handling.

    Logic:
    - expects_image=True: Try image parsing, fallback to JSON
    - expects_image=False: Parse as JSON only (fastest)
    - expects_image=None: Auto-detect using lightweight checks, then parse accordingly

    Args:
        raw: JSON string, bytes, or None
        expects_image: Optional hint about whether to expect image data

    Returns:
        tuple: (parsed_data, was_parsed_as_image)
            - parsed_data: Parsed dict if successful, None otherwise
            - was_parsed_as_image: True if data was successfully parsed as image
    """
    # 1. Input validation
    if raw is None:
        return None, False

    # 2. Parse as JSON first (always needed as fallback)
    parsed_data = parse_json(raw)
    if parsed_data is None:
        return None, False

    # 3. Handle explicit hints
    if expects_image is True:
        return _handle_image_hint(raw, parsed_data)
    elif expects_image is False:
        return _handle_json_hint(parsed_data)
    else:
        return _handle_auto_detection(raw, parsed_data)


def _handle_image_hint(raw: Union[str, bytes], parsed_data: dict) -> tuple[dict | None, bool]:
    """Handle explicit image hint - try image parsing first."""
    print("[Input] Hinted to parse as image", file=sys.stderr)
    result = parse_image(raw)
    if result is not None:
        return result, True
    return parsed_data, False


def _handle_json_hint(parsed_data: dict) -> tuple[dict | None, bool]:
    """Handle explicit JSON hint - skip image parsing."""
    print("[Input] Hinted to parse as JSON", file=sys.stderr)
    return parsed_data, False


def _handle_auto_detection(raw: Union[str, bytes], parsed_data: dict) -> tuple[dict | None, bool]:
    """Handle auto-detection - check if message looks like an image."""
    print("[Input] Auto-detecting image", file=sys.stderr)

    # Check if this is a publish message that might contain image data
    if parsed_data and isinstance(parsed_data, dict) and parsed_data.get("op") == "publish":
        msg_content = parsed_data.get("msg", {})
        if is_image_like(msg_content):
            # Try image parsing
            result = parse_image(raw)
            if result is not None:
                return result, True

    # Return the already parsed JSON
    return parsed_data, False


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
                    print(f"[WebSocket] Using timeout of {actual_timeout} seconds", file=sys.stderr)
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
