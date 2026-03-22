"""Window capture tool for ROS MCP.

Captures X11 GUI windows (e.g., TurtleSim, RViz, Gazebo) and returns
them as ImageContent, allowing the AI to see what's displayed.
"""

import io
import sys

from fastmcp import FastMCP
from mcp.types import ImageContent, ToolAnnotations

try:
    import numpy as np
    from PIL import Image as PILImage
    from Xlib import X, display

    WINDOW_CAPTURE_AVAILABLE = True
except ImportError:
    WINDOW_CAPTURE_AVAILABLE = False


def _find_window_by_name(root, name):
    """Recursively find the largest window matching the name."""
    results = []

    def _search(win):
        try:
            wm_name = win.get_wm_name()
            if wm_name and name.lower() in wm_name.lower():
                geom = win.get_geometry()
                if geom.width > 10 and geom.height > 10:
                    results.append((win, wm_name, geom.width, geom.height))
        except Exception:
            pass
        for child in win.query_tree().children:
            _search(child)

    _search(root)
    if not results:
        return None
    return max(results, key=lambda x: x[2] * x[3])


def _list_windows(root):
    """List all named windows with size > 10x10."""
    results = []

    def _search(win):
        try:
            wm_name = win.get_wm_name()
            if wm_name:
                geom = win.get_geometry()
                if geom.width > 10 and geom.height > 10:
                    results.append(
                        {
                            "name": wm_name,
                            "width": geom.width,
                            "height": geom.height,
                        }
                    )
        except Exception:
            pass
        for child in win.query_tree().children:
            _search(child)

    _search(root)
    return results


def _capture_window(win, resize_width=0, resize_height=0):
    """Capture a window and return as JPEG ImageContent."""
    geom = win.get_geometry()
    raw = win.get_image(0, 0, geom.width, geom.height, X.ZPixmap, 0xFFFFFFFF)

    # BGRX -> RGB
    img_np = np.frombuffer(raw.data, dtype=np.uint8).reshape(
        geom.height, geom.width, 4
    )
    rgb = img_np[:, :, :3][:, :, ::-1].copy()

    pil_img = PILImage.fromarray(rgb)

    # Optionally resize
    if resize_width > 0 and resize_height > 0:
        pil_img = pil_img.resize((resize_width, resize_height), PILImage.LANCZOS)

    # Encode as JPEG
    buf = io.BytesIO()
    pil_img.save(buf, format="JPEG", quality=85)
    img_bytes = buf.getvalue()

    import base64

    b64_data = base64.b64encode(img_bytes).decode("utf-8")

    return ImageContent(type="image", data=b64_data, mimeType="image/jpeg")


def register_window_capture_tools(mcp: FastMCP) -> None:
    """Register window capture tools."""

    @mcp.tool(
        description=(
            "List all visible GUI windows that can be captured.\n"
            "Returns window names and sizes. Use the window name with capture_window.\n"
            "Example:\n"
            "list_windows()"
        ),
        annotations=ToolAnnotations(
            title="List Windows",
            readOnlyHint=True,
        ),
    )
    def list_windows() -> dict:
        """
        List all visible X11 GUI windows.

        Returns:
            dict: List of windows with names and dimensions,
                or an error if window capture is not available.
        """
        if not WINDOW_CAPTURE_AVAILABLE:
            return {
                "error": "Window capture not available. "
                "Install dependencies: sudo apt install python3-xlib && pip install pillow numpy"
            }

        try:
            d = display.Display()
            root = d.screen().root
            windows = _list_windows(root)
            return {"windows": windows, "window_count": len(windows)}
        except Exception as e:
            return {"error": f"Failed to list windows: {e}"}

    @mcp.tool(
        description=(
            "Capture a screenshot of a GUI window (e.g., TurtleSim, RViz, Gazebo).\n"
            "Returns the window contents as an image so the AI can see what's displayed.\n"
            "Example:\n"
            "capture_window(window_name='TurtleSim')\n"
            "capture_window(window_name='RViz', resize_width=640, resize_height=480)"
        ),
        annotations=ToolAnnotations(
            title="Capture Window",
            readOnlyHint=True,
        ),
    )
    def capture_window(
        window_name: str = "TurtleSim",
        resize_width: int = 0,
        resize_height: int = 0,
    ) -> ImageContent:  # type: ignore  # See issue #140
        """
        Capture a screenshot of a GUI window and return it as an image.

        This tool finds a window by name and captures its contents,
        allowing the AI to see ROS GUI applications like TurtleSim,
        RViz, Gazebo, or any other X11 window.

        Args:
            window_name (str): Name (or partial name) of the window to capture
                (default: "TurtleSim")
            resize_width (int): Resize width in pixels. 0 = no resize (default: 0)
            resize_height (int): Resize height in pixels. 0 = no resize (default: 0)

        Returns:
            ImageContent: JPEG screenshot of the window, or error dict if not found.
        """
        if not WINDOW_CAPTURE_AVAILABLE:
            return {  # type: ignore[return-value]
                "error": "Window capture not available. "
                "Install dependencies: sudo apt install python3-xlib && pip install pillow numpy"
            }

        try:
            d = display.Display()
            root = d.screen().root
            result = _find_window_by_name(root, window_name)

            if not result:
                available = _list_windows(root)
                names = [w["name"] for w in available]
                return {  # type: ignore[return-value]
                    "error": f"Window '{window_name}' not found. "
                    f"Available windows: {names}"
                }

            win, wm_name, w, h = result
            return _capture_window(
                win, resize_width=resize_width, resize_height=resize_height
            )

        except Exception as e:
            return {"error": f"Failed to capture window: {e}"}  # type: ignore[return-value]
