"""Unit tests for ros_mcp/utils/response.py."""

from ros_mcp.utils.response import _check_response, _extract_error, _safe_get_values

# ---------------------------------------------------------------------------
# _check_response
# ---------------------------------------------------------------------------


class TestCheckResponse:
    def test_success_returns_none(self, success_response):
        assert _check_response(success_response) is None

    def test_failure_returns_error_dict(self, failure_response):
        result = _check_response(failure_response)
        assert result is not None
        assert "error" in result
        assert "Service not available" in result["error"]

    def test_failure_no_message_uses_fallback(self, failure_response_no_message):
        result = _check_response(failure_response_no_message)
        assert result is not None
        assert "Service call failed" in result["error"]

    def test_none_response(self):
        result = _check_response(None)
        assert result is not None
        assert "No response" in result["error"]

    def test_empty_dict_treated_as_no_response(self):
        """Empty dict is falsy in Python, so it's treated as no response."""
        result = _check_response({})
        assert result is not None
        assert "No response" in result["error"]

    def test_non_dict_response(self):
        result = _check_response("not a dict")
        assert result is not None
        assert "No response" in result["error"]

    def test_result_true_returns_none(self):
        assert _check_response({"result": True}) is None


# ---------------------------------------------------------------------------
# _safe_get_values
# ---------------------------------------------------------------------------


class TestSafeGetValues:
    def test_extracts_values_dict(self, success_response):
        values = _safe_get_values(success_response)
        assert values == {"message": "ok", "data": [1, 2, 3]}

    def test_missing_values_key(self):
        assert _safe_get_values({"result": True}) is None

    def test_non_dict_values(self):
        assert _safe_get_values({"values": "not a dict"}) is None

    def test_values_is_list(self):
        assert _safe_get_values({"values": [1, 2, 3]}) is None

    def test_none_response(self):
        assert _safe_get_values(None) is None

    def test_empty_dict_response(self):
        assert _safe_get_values({}) is None


# ---------------------------------------------------------------------------
# _extract_error
# ---------------------------------------------------------------------------


class TestExtractError:
    def test_extracts_message_field(self):
        response = {"values": {"message": "topic not found"}}
        assert _extract_error(response) == "topic not found"

    def test_missing_message_returns_fallback(self):
        response = {"values": {}}
        assert _extract_error(response) == "Service call failed"

    def test_non_dict_values_returns_str(self):
        response = {"values": "raw error text"}
        assert _extract_error(response) == "raw error text"

    def test_none_values_returns_fallback(self):
        response = {"values": None}
        assert _extract_error(response) == "Service call failed"

    def test_none_response(self):
        assert _extract_error(None) == "No response"

    def test_empty_dict_treated_as_no_response(self):
        """Empty dict is falsy, treated same as None."""
        assert _extract_error({}) == "No response"

    def test_non_dict_response(self):
        assert _extract_error([1, 2]) == "No response"
