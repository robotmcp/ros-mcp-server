"""Tests for window capture MCP tools."""

from unittest.mock import MagicMock, patch

import pytest

from ros_mcp.tools.window_capture import (
    WINDOW_CAPTURE_AVAILABLE,
    _capture_window,
    _find_window_by_name,
    _list_windows,
    register_window_capture_tools,
)


class TestWindowCaptureAvailability:
    """Test that the module handles missing dependencies gracefully."""

    def test_module_imports_without_error(self):
        """Module should import even if X11 dependencies are missing."""
        from ros_mcp.tools import window_capture

        assert hasattr(window_capture, "WINDOW_CAPTURE_AVAILABLE")
        assert hasattr(window_capture, "register_window_capture_tools")


class TestFindWindowByName:
    """Test _find_window_by_name helper function."""

    @pytest.mark.skipif(not WINDOW_CAPTURE_AVAILABLE, reason="X11 dependencies not available")
    def test_find_nonexistent_window(self):
        """Should return None for a window name that doesn't exist."""
        from Xlib import display

        d = display.Display()
        root = d.screen().root
        result = _find_window_by_name(root, "NonExistentWindow12345")
        assert result is None

    @pytest.mark.skipif(not WINDOW_CAPTURE_AVAILABLE, reason="X11 dependencies not available")
    def test_find_window_returns_tuple(self):
        """If a window is found, should return (win, name, width, height) tuple."""
        from Xlib import display

        d = display.Display()
        root = d.screen().root
        # Try to find any window - there should be at least the WM
        result = _find_window_by_name(root, "Weston")
        if result is not None:
            win, name, w, h = result
            assert isinstance(name, str)
            assert w > 0
            assert h > 0


class TestListWindows:
    """Test _list_windows helper function."""

    @pytest.mark.skipif(not WINDOW_CAPTURE_AVAILABLE, reason="X11 dependencies not available")
    def test_list_windows_returns_list(self):
        """Should return a list of window dicts."""
        from Xlib import display

        d = display.Display()
        root = d.screen().root
        windows = _list_windows(root)
        assert isinstance(windows, list)
        for win in windows:
            assert "name" in win
            assert "width" in win
            assert "height" in win
            assert win["width"] > 10
            assert win["height"] > 10


class TestCaptureWindow:
    """Test _capture_window function."""

    @pytest.mark.skipif(not WINDOW_CAPTURE_AVAILABLE, reason="X11 dependencies not available")
    def test_capture_returns_image_content(self):
        """Should return ImageContent when given a valid window."""
        from mcp.types import ImageContent
        from Xlib import display

        d = display.Display()
        root = d.screen().root
        windows = _list_windows(root)
        if not windows:
            pytest.skip("No windows available to capture")

        # Find the actual window object
        result = _find_window_by_name(root, windows[0]["name"])
        if result is None:
            pytest.skip("Could not find window to capture")

        win, _, _, _ = result
        content = _capture_window(win)
        assert isinstance(content, ImageContent)
        assert content.type == "image"
        assert content.mimeType == "image/jpeg"
        assert len(content.data) > 0

    @pytest.mark.skipif(not WINDOW_CAPTURE_AVAILABLE, reason="X11 dependencies not available")
    def test_capture_with_resize(self):
        """Should return a resized ImageContent."""
        from mcp.types import ImageContent
        from Xlib import display

        d = display.Display()
        root = d.screen().root
        windows = _list_windows(root)
        if not windows:
            pytest.skip("No windows available to capture")

        result = _find_window_by_name(root, windows[0]["name"])
        if result is None:
            pytest.skip("Could not find window to capture")

        win, _, _, _ = result
        content = _capture_window(win, resize_width=160, resize_height=120)
        assert isinstance(content, ImageContent)
        assert content.type == "image"
        assert len(content.data) > 0


class TestRegisterWindowCaptureTools:
    """Test tool registration."""

    def test_register_tools(self):
        """Should register list_windows and capture_window tools."""
        mcp = MagicMock()
        # Make mcp.tool() return a decorator that passes through the function
        mcp.tool.return_value = lambda fn: fn

        register_window_capture_tools(mcp)

        # Should have been called twice (list_windows, capture_window)
        assert mcp.tool.call_count == 2


class TestToolsWithoutDependencies:
    """Test that tools return helpful errors when dependencies are missing."""

    def test_list_windows_without_deps(self):
        """list_windows should return error dict when deps missing."""
        mcp = MagicMock()
        registered_fns = {}

        def mock_tool(**kwargs):
            def decorator(fn):
                registered_fns[fn.__name__] = fn
                return fn

            return decorator

        mcp.tool = mock_tool

        with patch("ros_mcp.tools.window_capture.WINDOW_CAPTURE_AVAILABLE", False):
            register_window_capture_tools(mcp)

        result = registered_fns["list_windows"]()
        assert "error" in result
        assert "not available" in result["error"].lower()

    def test_capture_window_without_deps(self):
        """capture_window should return error dict when deps missing."""
        mcp = MagicMock()
        registered_fns = {}

        def mock_tool(**kwargs):
            def decorator(fn):
                registered_fns[fn.__name__] = fn
                return fn

            return decorator

        mcp.tool = mock_tool

        with patch("ros_mcp.tools.window_capture.WINDOW_CAPTURE_AVAILABLE", False):
            register_window_capture_tools(mcp)

        result = registered_fns["capture_window"]()
        assert "error" in result
        assert "not available" in result["error"].lower()
