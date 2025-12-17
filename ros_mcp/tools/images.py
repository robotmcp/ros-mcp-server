"""Image tools for ROS MCP."""

import io
import os

from fastmcp import FastMCP
from fastmcp.utilities.types import Image
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


def _encode_image_to_imagecontent(image):
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
            "Analyze a previously received image that was saved by any ROS operation.\n"
            "Images can be received from:\n"
            "- Any topic containing image data (not just topics with 'Image' in the name)\n"
            "- Service responses containing image data\n"
            "- subscribe_once() or subscribe_for_duration() operations\n"
            "Use this tool to analyze the saved image after receiving it from any source.\n"
        )
    )
    def analyze_previously_received_image(
        image_path: str = "./camera/received_image.jpeg",
    ) -> dict:
        """
        Analyze the previously received image saved at the specified path.

        This tool loads the previously saved image from the specified path
        (which can be created by any ROS operation that receives image data), and converts
        it into an MCP-compatible ImageContent format so that the LLM can interpret it.

        Images can be received from:
        - Any Topic containing image data
        - Any Service responses containing image data
        - subscribe_once() or subscribe_for_duration() operations

        Args:
            image_path (str): Path to the saved image file (default: "./camera/received_image.jpeg")

        Returns:
            ImageContent: JPEG-encoded image wrapped in an ImageContent object, or error dict if file not found.
        """
        if not os.path.exists(image_path):
            return {"error": f"No image found at {image_path}"}
        img = PILImage.open(image_path)
        return _encode_image_to_imagecontent(img)
