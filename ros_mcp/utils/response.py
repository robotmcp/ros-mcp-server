"""Helpers for safely handling rosbridge service responses."""

from typing import Optional


def _check_response(response: dict) -> Optional[dict]:
    """Return an error dict if the response indicates failure, else None."""
    if not response or not isinstance(response, dict):
        return {"error": "No response received from rosbridge"}
    if "result" in response and not response["result"]:
        error_msg = _extract_error(response)
        return {"error": f"Service call failed: {error_msg}"}
    return None


def _safe_get_values(response: dict) -> Optional[dict]:
    """Extract the 'values' field from a response, returning None if absent or not a dict."""
    if not response or not isinstance(response, dict):
        return None
    values = response.get("values")
    if isinstance(values, dict):
        return values
    return None


def _extract_error(response: dict) -> str:
    """Extract a human-readable error message from a failed rosbridge response."""
    if not response or not isinstance(response, dict):
        return "No response"
    values = response.get("values", {})
    if isinstance(values, dict):
        return values.get("message", "Service call failed")
    return str(values) if values else "Service call failed"
