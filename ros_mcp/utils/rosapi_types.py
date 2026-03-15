"""Version-aware rosapi service type resolver.

Humble (and earlier) rosbridge registers services with short types like ``rosapi/Topics``.
Jazzy (and later) uses fully-qualified types like ``rosapi_msgs/srv/Topics``.

This module probes the running rosbridge *once* and caches the correct format so
every subsequent call gets the right type string automatically.
"""

from __future__ import annotations

import logging
from typing import Optional

from ros_mcp.utils.websocket import WebSocketManager

logger = logging.getLogger(__name__)

# Mapping from short name → (humble_type, jazzy_type)
_TYPE_MAP: dict[str, tuple[str, str]] = {
    # --- nodes ---
    "Nodes": ("rosapi/Nodes", "rosapi/Nodes"),
    "NodeDetails": ("rosapi/NodeDetails", "rosapi/NodeDetails"),
    # --- topics ---
    "Topics": ("rosapi/Topics", "rosapi/Topics"),
    "TopicType": ("rosapi/TopicType", "rosapi/TopicType"),
    "Publishers": ("rosapi/Publishers", "rosapi/Publishers"),
    "Subscribers": ("rosapi/Subscribers", "rosapi/Subscribers"),
    "MessageDetails": ("rosapi/MessageDetails", "rosapi/MessageDetails"),
    # --- services ---
    "Services": ("rosapi/Services", "rosapi_msgs/srv/Services"),
    "ServiceType": ("rosapi/ServiceType", "rosapi_msgs/srv/ServiceType"),
    "ServiceRequestDetails": (
        "rosapi/ServiceRequestDetails",
        "rosapi_msgs/srv/ServiceRequestDetails",
    ),
    "ServiceResponseDetails": (
        "rosapi/ServiceResponseDetails",
        "rosapi_msgs/srv/ServiceResponseDetails",
    ),
    "ServiceNode": ("rosapi/ServiceNode", "rosapi_msgs/srv/ServiceNode"),
    # --- parameters ---
    "GetParam": ("rosapi/GetParam", "rosapi_msgs/srv/GetParam"),
    "SetParam": ("rosapi/SetParam", "rosapi_msgs/srv/SetParam"),
    "DeleteParam": ("rosapi/DeleteParam", "rosapi_msgs/srv/DeleteParam"),
    "GetParamNames": ("rosapi/GetParamNames", "rosapi_msgs/srv/GetParamNames"),
    # --- actions ---
    "ActionServers": ("rosapi/ActionServers", "rosapi/ActionServers"),
    "Interfaces": ("rosapi/Interfaces", "rosapi/Interfaces"),
    "ActionGoalDetails": ("rosapi/ActionGoalDetails", "rosapi_msgs/srv/ActionGoalDetails"),
    "ActionResultDetails": ("rosapi/ActionResultDetails", "rosapi_msgs/srv/ActionResultDetails"),
    "ActionFeedbackDetails": (
        "rosapi/ActionFeedbackDetails",
        "rosapi_msgs/srv/ActionFeedbackDetails",
    ),
}

# Distros that use the new rosapi_msgs/srv/ format
_JAZZY_AND_LATER = {"jazzy", "kilted", "rolling"}


class RosapiTypeResolver:
    """Resolves rosapi service type strings based on the connected ROS distro."""

    def __init__(self) -> None:
        self._use_jazzy_format: Optional[bool] = None
        self._distro: str = ""

    def detect(self, ws_manager: WebSocketManager) -> None:
        """Probe rosbridge to determine the ROS distro and set the type format."""
        try:
            request = {
                "op": "call_service",
                "id": "rosapi_type_detect",
                "service": "/rosapi/get_ros_version",
                "args": {},
            }
            with ws_manager:
                response = ws_manager.request(request)

            values = response.get("values") if response else None
            if isinstance(values, dict):
                distro = str(values.get("distro", "")).strip().lower()
                self._distro = distro
                self._use_jazzy_format = distro in _JAZZY_AND_LATER
                logger.info(
                    "Detected ROS distro '%s' → %s type format",
                    distro,
                    "jazzy" if self._use_jazzy_format else "humble",
                )
                return
        except Exception as e:
            logger.warning("Failed to detect ROS distro: %s", e)

        # Default to humble (short) format if detection fails
        self._use_jazzy_format = False
        logger.info("Defaulting to humble type format")

    def get(self, short_name: str) -> str:
        """Return the correct type string for the given short name.

        Args:
            short_name: The short type name, e.g. ``"Services"``, ``"TopicType"``.

        Returns:
            The full type string appropriate for the detected ROS distro.
        """
        if self._use_jazzy_format is None:
            # Not yet detected — default to humble format
            self._use_jazzy_format = False

        entry = _TYPE_MAP.get(short_name)
        if entry is None:
            # Unknown type — return as-is with rosapi/ prefix
            return f"rosapi/{short_name}"

        humble_type, jazzy_type = entry
        return jazzy_type if self._use_jazzy_format else humble_type


# Module-level singleton
_resolver = RosapiTypeResolver()


def detect_rosapi_types(ws_manager: WebSocketManager) -> None:
    """Probe rosbridge and cache the correct type format. Call once at startup."""
    _resolver.detect(ws_manager)


def is_humble() -> bool:
    """Return True if the detected distro is Humble (or older / unknown)."""
    return not _resolver._use_jazzy_format


def rosapi_type(short_name: str) -> str:
    """Get the version-appropriate rosapi type string.

    Example::

        rosapi_type("Services")  # → "rosapi/Services" on Humble
        # → "rosapi_msgs/srv/Services" on Jazzy
    """
    return _resolver.get(short_name)
