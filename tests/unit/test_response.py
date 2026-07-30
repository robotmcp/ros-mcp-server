"""Unit tests for ros_mcp/utils/response.py — string-values regression (#251/#308)."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

_RESPONSE_PATH = Path(__file__).resolve().parents[2] / "ros_mcp" / "utils" / "response.py"


def _load_response():
    """Load response.py without importing ros_mcp package (avoids FastMCP side effects)."""
    spec = importlib.util.spec_from_file_location("ros_mcp_utils_response", _RESPONSE_PATH)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def response_mod():
    return _load_response()


class TestCheckResponse:
    def test_none_response(self, response_mod):
        assert response_mod._check_response(None) == {
            "error": "No response received from rosbridge"
        }

    def test_non_dict_response(self, response_mod):
        assert response_mod._check_response("nope") == {
            "error": "No response received from rosbridge"
        }
        assert response_mod._check_response([]) == {"error": "No response received from rosbridge"}

    def test_result_true_ok(self, response_mod):
        assert response_mod._check_response({"result": True, "values": {"a": 1}}) is None

    def test_missing_result_treated_as_ok(self, response_mod):
        assert response_mod._check_response({"values": {"ok": True}}) is None

    def test_result_false_with_dict_values_message(self, response_mod):
        err = response_mod._check_response({"result": False, "values": {"message": "service gone"}})
        assert err is not None
        assert "service gone" in err["error"]

    def test_result_false_with_string_values_no_crash(self, response_mod):
        # Regression for #251: values can be a str when service missing.
        err = response_mod._check_response({"result": False, "values": "Service does not exist"})
        assert err is not None
        assert "Service does not exist" in err["error"]


class TestSafeGetValues:
    def test_dict_values(self, response_mod):
        assert response_mod._safe_get_values({"values": {"topics": ["/chatter"]}}) == {
            "topics": ["/chatter"]
        }

    def test_string_values_returns_none(self, response_mod):
        assert response_mod._safe_get_values({"values": "Service does not exist"}) is None

    def test_missing_values(self, response_mod):
        assert response_mod._safe_get_values({}) is None

    def test_non_dict_response(self, response_mod):
        assert response_mod._safe_get_values(None) is None
        assert response_mod._safe_get_values("x") is None


class TestExtractError:
    def test_dict_message(self, response_mod):
        assert response_mod._extract_error({"values": {"message": "boom"}}) == "boom"

    def test_string_values(self, response_mod):
        assert response_mod._extract_error({"values": "not found"}) == "not found"

    def test_empty_dict_values_default(self, response_mod):
        assert response_mod._extract_error({"values": {}}) == "Service call failed"

    def test_none_response(self, response_mod):
        assert response_mod._extract_error(None) == "No response"
