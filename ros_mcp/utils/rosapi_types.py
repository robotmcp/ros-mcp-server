"""Version-aware rosapi service type and path resolver.

Humble (and earlier) rosbridge registers services under ``/rosapi/`` with
short types like ``rosapi/Topics``.
Jazzy (and later) registers under ``/rosapi_node/`` with fully-qualified
types like ``rosapi_msgs/srv/Topics``.

This module probes the running rosbridge *once* and caches the correct
format so every subsequent call gets the right type and path automatically.
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

# Distros that use the new rosapi_msgs/srv/ format and /rosapi_node/ prefix
_JAZZY_AND_LATER = {"jazzy", "kilted", "rolling"}

# Service path prefixes per distro
_HUMBLE_PREFIX = "/rosapi"
_JAZZY_PREFIX = "/rosapi_node"


class RosapiTypeResolver:
    """Resolves rosapi service type strings and paths based on the connected ROS distro."""

    def __init__(self) -> None:
        self._use_jazzy_format: Optional[bool] = None
        self._distro: str = ""
        self._service_prefix: str = _HUMBLE_PREFIX

    def detect(self, ws_manager: WebSocketManager) -> None:
        """Probe rosbridge to determine the correct service prefix and type format.

        Tries ``get_ros_version`` under each known prefix (/rosapi/ then /rosapi_node/).
        Checks that the response contains actual version data (not just an error dict).
        """
        for prefix, is_jazzy in ((_HUMBLE_PREFIX, False), (_JAZZY_PREFIX, True)):
            try:
                request = {
                    "op": "call_service",
                    "id": "rosapi_prefix_detect",
                    "service": f"{prefix}/get_ros_version",
                    "args": {},
                }
                with ws_manager:
                    response = ws_manager.request(request)

                if not response or not isinstance(response, dict):
                    continue

                # On failure rosbridge returns result=false
                if response.get("result") is False:
                    continue

                values = response.get("values")
                if isinstance(values, dict) and "distro" in values:
                    distro = str(values["distro"]).strip().lower()
                    self._distro = distro
                    self._use_jazzy_format = is_jazzy
                    self._service_prefix = prefix
                    logger.info(
                        "Detected ROS distro '%s' → prefix=%s, jazzy_types=%s",
                        distro, prefix, is_jazzy,
                    )
                    return
            except Exception as e:
                logger.debug("Detection with prefix %s failed: %s", prefix, e)

        # Default to humble format if detection fails
        self._use_jazzy_format = False
        self._service_prefix = _HUMBLE_PREFIX
        logger.info("Defaulting to humble format (prefix=%s)", self._service_prefix)

    def get_type(self, short_name: str) -> str:
        """Return the correct type string for the given short name."""
        if self._use_jazzy_format is None:
            self._use_jazzy_format = False

        entry = _TYPE_MAP.get(short_name)
        if entry is None:
            return f"rosapi/{short_name}"

        humble_type, jazzy_type = entry
        return jazzy_type if self._use_jazzy_format else humble_type

    def get_service(self, service_name: str) -> str:
        """Return the full service path for a rosapi service.

        Args:
            service_name: Short service name, e.g. ``"nodes"``, ``"topic_type"``.

        Returns:
            Full path like ``"/rosapi/nodes"`` or ``"/rosapi_node/nodes"``.
        """
        return f"{self._service_prefix}/{service_name}"


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
    return _resolver.get_type(short_name)


def rosapi_service(service_name: str) -> str:
    """Get the version-appropriate rosapi service path.

    Example::

        rosapi_service("nodes")  # → "/rosapi/nodes" on Humble
                                 # → "/rosapi_node/nodes" on Jazzy
    """
    return _resolver.get_service(service_name)
