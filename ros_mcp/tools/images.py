"""Image tools for ROS MCP."""

import io
import os

from fastmcp import FastMCP
from fastmcp.utilities.types import Image
from mcp.types import ImageContent, ToolAnnotations
from PIL import Image as PILImage


def convert_expects_image_hint(expects_image: str) -> bool | None:
    """
    Convert string-based expects_image hint to boolean for internal use.

    Args:
        expects_image (str): String hint about whether to expect image data
            - "true": prioritize image parsing
            - "false": skip image detection for faster processing
            - "auto": auto-detect based on message fields (default)
            - any other value: treated as "auto"

    Returns:
        bool | None: Converted hint for parse_input function
            - True: prioritize image parsing
            - False: skip image detection
            - None: auto-detect
    """
    if expects_image == "true":
        return True
    elif expects_image == "false":
        return False
    else:  # "auto" or any other value
        return None


def _encode_image_to_imagecontent(image) -> ImageContent:
    """
    Encodes a PIL Image to a format compatible with ImageContent.

    Args:
        image (PIL.Image.Image): The image to encode.

    Returns:
        ImageContent: JPEG-encoded image wrapped in an ImageContent object.
    """
    buffer = io.BytesIO()
    image.save(buffer, format="JPEG")
    img_bytes = buffer.getvalue()
    img_obj = Image(data=img_bytes, format="jpeg")
    return img_obj.to_image_content()


def register_image_tools(
    mcp: FastMCP,
) -> None:
    """Register all image-related tools."""

    @mcp.tool(
        description=(
            "View a previously saved image from disk.\n"
            "Images are automatically saved when subscribing to image topics.\n"
            "Use this tool to re-view a saved image without re-subscribing.\n"
        ),
        annotations=ToolAnnotations(
            title="View Saved Image",
            readOnlyHint=True,
        ),
    )
    def view_saved_image(
        image_path: str = "./camera/received_image.jpeg",
    ) -> ImageContent:  # type: ignore  # See issue #140
        """
        View a previously saved image from the specified path.

        Images are automatically saved to disk when subscribing to image topics
        via subscribe_once() or subscribe_for_duration(). Use this tool to
        re-view a saved image without re-subscribing.

        Args:
            image_path (str): Path to the saved image file (default: "./camera/received_image.jpeg")

        Returns:
            ImageContent: JPEG-encoded image wrapped in an ImageContent object, or error dict if file not found.
        """
        if not os.path.exists(image_path):
            return {"error": f"No image found at {image_path}"}  # type: ignore[return-value]  # See issue #140
        img = PILImage.open(image_path)
        return _encode_image_to_imagecontent(img)
