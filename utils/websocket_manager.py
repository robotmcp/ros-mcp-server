import base64
import json
import os
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
        print("[Image] Invalid JSON or missing 'msg' field.")
        return None

    data_b64 = msg.get("data")
    if not data_b64:
        print("[Image] Missing 'data' field in message.")
        return None

    # ✅ Ensure output directory exists
    os.makedirs("./camera", exist_ok=True)

    # Case 1: CompressedImage (already JPEG/PNG encoded)
    if "format" in msg and msg["format"].lower() in ["jpeg", "jpg", "png"]:
        image_bytes = base64.b64decode(data_b64)
        path = "./camera/received_image.jpeg"
        with open(path, "wb") as f:
            f.write(image_bytes)
        print(f"[Image] Saved CompressedImage to {path}")
        return result if isinstance(result, dict) else None

    # Case 2: Raw Image (rgb8, bgr8, mono8)
    height, width, encoding = msg.get("height"), msg.get("width"), msg.get("encoding")
    if not all([height, width, encoding]):
        print("[Image] Missing required fields for raw image.")
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
            print(f"[Image] Unsupported encoding: {encoding}")
            return None
    except ValueError as e:
        print(f"[Image] Reshape error: {e}")
        return None

    # Save as JPEG with quality 95
    success = cv2.imwrite("./camera/received_image.jpeg", img_cv, [cv2.IMWRITE_JPEG_QUALITY, 95])
    if success:
        print("[Image] Saved raw Image to ./camera/received_image.jpeg")
        return result if isinstance(result, dict) else None
    else:
        return None


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
        print(f"[WebSocket] IP set to {self.ip}:{self.port}")

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
                    print(f"[WebSocket] Connected ({self.default_timeout}s timeout)")
                    return None  # no error
                except Exception as e:
                    error_msg = f"[WebSocket] Connection error: {e}"
                    print(error_msg)
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
                    print(error_msg)
                    self.close()
                    return error_msg
                except Exception as e:
                    error_msg = f"[WebSocket] Send error: {e}"
                    print(error_msg)
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
                    print(f"[WebSocket] Receive error or timeout: {e}")
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

        # Attempt to parse JSON
        parsed_response = parse_json(response)
        if parsed_response is None:
            print(f"[WebSocket] JSON decode error for response: {response}")
            return {"error": "invalid_json", "raw": response}
        return parsed_response

    def close(self):
        with self.lock:
            if self.ws and self.ws.connected:
                try:
                    self.ws.close()
                    print("[WebSocket] Closed")
                except Exception as e:
                    print(f"[WebSocket] Close error: {e}")
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
