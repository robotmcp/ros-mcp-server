"""Shared safety helpers for rosbridge response handling."""


def _extract_error(response, default: str = "Service call failed") -> str:
    """Safely extract an error message from a rosbridge response.

    Handles cases where response["values"] is a string instead of a dict.
    """
    if not response or not isinstance(response, dict):
        return str(response) if response else default
    values = response.get("values", {})
    if isinstance(values, dict):
        return values.get("message", default)
    return str(values) if values else default


def _check_response(response) -> dict | None:
    """Check for common response errors. Returns error dict or None if OK."""
    if not response:
        return {"error": "No response received from rosbridge"}
    if not isinstance(response, dict):
        return {"error": f"Unexpected response: {response}"}
    if "error" in response and "op" not in response:
        return {"error": f"Service call failed: {response['error']}"}
    if "result" in response and not response["result"]:
        return {"error": f"Service call failed: {_extract_error(response)}"}
    return None


def _safe_get_values(response) -> dict | None:
    """Safely extract the 'values' dict from a rosbridge response.

    Returns None if response is missing, not a dict, has no 'values' key,
    or if 'values' is not a dict (e.g. when rosbridge returns a string error).
    """
    if not response or not isinstance(response, dict):
        return None
    values = response.get("values")
    if isinstance(values, dict):
        return values
    return None
