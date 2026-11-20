"""Service availability and compatibility verification utility."""

from __future__ import annotations

import time
from typing import Any

from ros_mcp.utils.response import _safe_get_values
from ros_mcp.utils.rosapi_types import rosapi_service, rosapi_type
from ros_mcp.utils.websocket import WebSocketManager

_cached_services: list[str] = []
_last_fetch_time: float = 0.0


def _reset_service_cache() -> None:
    """Reset the service cache. Used primarily for unit tests."""
    global _cached_services, _last_fetch_time
    _cached_services = []
    _last_fetch_time = 0.0


def get_available_services(
    ws_manager: WebSocketManager, max_age_seconds: float = 2.0, force_refresh: bool = False
) -> list[str]:
    """Get list of all available ROS services, with caching.

    Args:
        ws_manager: WebSocketManager instance.
        max_age_seconds: Cache validity duration in seconds.
        force_refresh: If True, bypass the cache and fetch anew.

    Returns:
        List of available service names (strings).
    """
    global _cached_services, _last_fetch_time
    now = time.time()
    if not force_refresh and _cached_services and (now - _last_fetch_time < max_age_seconds):
        return _cached_services

    message = {
        "op": "call_service",
        "service": rosapi_service("services"),
        "type": rosapi_type("Services"),
        "args": {},
        "id": "service_verifier_get_services",
    }

    try:
        with ws_manager:
            response = ws_manager.request(message)
        values = _safe_get_values(response)
        if values is not None and isinstance(values, dict):
            _cached_services = values.get("services", [])
            _last_fetch_time = now
            return _cached_services
    except Exception:
        pass

    return _cached_services


def is_service_available(
    service_name: str, ws_manager: WebSocketManager, max_age_seconds: float = 2.0
) -> bool:
    """Check if a specific service is available in the ROS graph.

    Args:
        service_name: Name of the service to check (e.g. '/rosapi/get_param').
        ws_manager: WebSocketManager instance.
        max_age_seconds: Cache validity duration in seconds.

    Returns:
        True if the service is available, False otherwise.
    """
    services = get_available_services(ws_manager, max_age_seconds=max_age_seconds)
    if service_name in services:
        return True

    # If not found in cache, force refresh once to avoid false negatives
    refreshed = get_available_services(ws_manager, force_refresh=True)
    return service_name in refreshed


def verify_services(
    required_services: list[str], ws_manager: WebSocketManager
) -> tuple[bool, list[str]]:
    """Verify that all required services are available.

    Args:
        required_services: List of service names required for an operation.
        ws_manager: WebSocketManager instance.

    Returns:
        Tuple of (all_available: bool, missing_services: list[str]).
    """
    available = set(get_available_services(ws_manager))
    missing = [svc for svc in required_services if svc not in available]
    if missing:
        # Refresh once to re-check missing services
        available = set(get_available_services(ws_manager, force_refresh=True))
        missing = [svc for svc in required_services if svc not in available]
    return len(missing) == 0, missing


def make_compatibility_response(
    tool_name: str,
    issue: str,
    missing_services: list[str] | None = None,
    required_services: list[str] | None = None,
    suggestions: list[str] | None = None,
    note: str | None = None,
    warning: bool = False,
    extra_fields: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Construct a standardized compatibility issue response.

    Args:
        tool_name: Name of the tool or operation.
        issue: Descriptive issue explanation.
        missing_services: List of services that were missing.
        required_services: List of required services.
        suggestions: Suggested alternatives or troubleshooting steps.
        note: Additional context or notes.
        warning: If True, uses 'warning' key instead of 'error'.
        extra_fields: Additional top-level fields to merge into the response.

    Returns:
        Dictionary containing error/warning and compatibility details.
    """
    key = "warning" if warning else "error"
    res: dict[str, Any] = {
        key: issue,
        "compatibility": {
            "issue": issue,
            "missing_services": missing_services or [],
            "required_services": required_services or [],
            "suggestions": suggestions or [],
        },
    }
    if note:
        res["compatibility"]["note"] = note
    if extra_fields:
        res.update(extra_fields)
    return res
