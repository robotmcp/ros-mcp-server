"""Unit tests for convert_expects_image_hint (pure mapping)."""

from ros_mcp.tools.images import convert_expects_image_hint


class TestConvertExpectsImageHint:
    def test_true_string(self):
        assert convert_expects_image_hint("true") is True

    def test_false_string(self):
        assert convert_expects_image_hint("false") is False

    def test_auto_string(self):
        assert convert_expects_image_hint("auto") is None

    def test_empty_string_is_auto(self):
        assert convert_expects_image_hint("") is None

    def test_unknown_is_auto(self):
        assert convert_expects_image_hint("maybe") is None
        assert convert_expects_image_hint("TRUE") is None
        assert convert_expects_image_hint("False") is None

    def test_whitespace_not_true(self):
        # Only exact "true"/"false" match; surrounding space is auto
        assert convert_expects_image_hint(" true") is None
        assert convert_expects_image_hint("false ") is None
