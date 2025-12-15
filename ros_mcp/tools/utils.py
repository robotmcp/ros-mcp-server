"""Utility functions for ROS MCP tools."""

import io
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
