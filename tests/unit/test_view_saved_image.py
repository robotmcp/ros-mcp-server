"""Unit tests for view_saved_image tool."""

from __future__ import annotations

from unittest.mock import MagicMock

from PIL import Image as PILImage

import ros_mcp.tools.images as images_mod
from ros_mcp.tools.images import register_image_tools


class _FakeMCP:
    def __init__(self) -> None:
        self.tools = {}

    def tool(self, *args, **kwargs):
        def deco(fn):
            self.tools[fn.__name__] = fn
            return fn

        return deco


def test_view_saved_image_missing_path(tmp_path):
    mcp = _FakeMCP()
    register_image_tools(mcp)
    view = mcp.tools["view_saved_image"]
    missing = tmp_path / "nope.jpeg"
    result = view(image_path=str(missing))
    assert isinstance(result, dict)
    assert "error" in result
    assert str(missing) in result["error"]


def test_view_saved_image_encodes_existing_file(monkeypatch, tmp_path):
    mcp = _FakeMCP()
    register_image_tools(mcp)
    view = mcp.tools["view_saved_image"]

    img_path = tmp_path / "shot.jpeg"
    PILImage.new("RGB", (4, 4), color=(10, 20, 30)).save(img_path, format="JPEG")

    sentinel = object()
    encode = MagicMock(return_value=sentinel)
    monkeypatch.setattr(images_mod, "_encode_image_to_imagecontent", encode)

    result = view(image_path=str(img_path))
    assert result is sentinel
    encode.assert_called_once()
    arg = encode.call_args[0][0]
    assert arg.size == (4, 4)
