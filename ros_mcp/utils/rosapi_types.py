"""Version-aware rosapi service type and path resolver.

ROS 1 rosbridge registers services under ``/rosapi/`` with short types
like ``rosapi/Topics``.

ROS 2 rosbridge registers services under ``/rosapi_node/`` with
fully-qualified types like ``rosapi_msgs/srv/Topics``.

This module probes the running rosbridge *once* and caches the correct
format so every subsequent call gets the right type and path automatically.
"""

from __future__ import annotations

import logging
from typing import Optional

from ros_mcp.utils.websocket import WebSocketManager

logger = logging.getLogger(__name__)

# Mapping from short name → (ros1_type, ros2_type)
_TYPE_MAP: dict[str, tuple[str, str]] = {
    # --- nodes ---
    "Nodes": ("rosapi/Nodes", "rosapi_msgs/srv/Nodes"),
    "NodeDetails": ("rosapi/NodeDetails", "rosapi_msgs/srv/NodeDetails"),
    # --- topics ---
    "Topics": ("rosapi/Topics", "rosapi_msgs/srv/Topics"),
    "TopicType": ("rosapi/TopicType", "rosapi_msgs/srv/TopicType"),
    "Publishers": ("rosapi/Publishers", "rosapi_msgs/srv/Publishers"),
    "Subscribers": ("rosapi/Subscribers", "rosapi_msgs/srv/Subscribers"),
    "MessageDetails": ("rosapi/MessageDetails", "rosapi_msgs/srv/MessageDetails"),
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
    # --- actions (ROS 2 only) ---
    "ActionServers": ("rosapi/ActionServers", "rosapi_msgs/srv/ActionServers"),
    "Interfaces": ("rosapi/Interfaces", "rosapi_msgs/srv/Interfaces"),
    "ActionGoalDetails": ("rosapi/ActionGoalDetails", "rosapi_msgs/srv/ActionGoalDetails"),
    "ActionResultDetails": (
        "rosapi/ActionResultDetails",
        "rosapi_msgs/srv/ActionResultDetails",
    ),
    "ActionFeedbackDetails": (
        "rosapi/ActionFeedbackDetails",
        "rosapi_msgs/srv/ActionFeedbackDetails",
    ),
}

# Service path prefixes
_ROS1_PREFIX = "/rosapi"
_ROS2_PREFIX = "/rosapi_node"


class RosapiTypeResolver:
    """Resolves rosapi service type strings and paths based on ROS version."""

    def __init__(self) -> None:
        self._is_ros2: Optional[bool] = None
        self._distro: str = ""
        self._service_prefix: str = _ROS1_PREFIX

    def detect(self, ws_manager: WebSocketManager) -> None:
        """Probe rosbridge to determine the ROS version (1 vs 2).

        Tries ``get_ros_version`` under each known prefix:
        - ``/rosapi/`` (ROS 1)
        - ``/rosapi_node/`` (ROS 2)

        The prefix that responds successfully determines the ROS version.
        """
        for prefix, is_ros2 in ((_ROS1_PREFIX, False), (_ROS2_PREFIX, True)):
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
                    self._is_ros2 = is_ros2
                    self._service_prefix = prefix
                    logger.info(
                        "Detected ROS distro '%s' (ROS %s) → prefix=%s",
                        distro,
                        "2" if is_ros2 else "1",
                        prefix,
                    )
                    return
            except Exception as e:
                logger.debug("Detection with prefix %s failed: %s", prefix, e)

        # Default to ROS 1 format if detection fails
        self._is_ros2 = False
        self._service_prefix = _ROS1_PREFIX
        logger.info("Defaulting to ROS 1 format (prefix=%s)", self._service_prefix)

    def get_type(self, short_name: str) -> str:
        """Return the correct type string for the given short name."""
        if self._is_ros2 is None:
            self._is_ros2 = False

        entry = _TYPE_MAP.get(short_name)
        if entry is None:
            return f"rosapi/{short_name}"

        ros1_type, ros2_type = entry
        return ros2_type if self._is_ros2 else ros1_type

    def get_service(self, service_name: str) -> str:
        """Return the full service path for a rosapi service.

        Args:
            service_name: Short service name, e.g. ``"nodes"``, ``"topic_type"``.

        Returns:
            Full path like ``"/rosapi/nodes"`` (ROS 1) or ``"/rosapi_node/nodes"`` (ROS 2).
        """
        return f"{self._service_prefix}/{service_name}"


# Module-level singleton
_resolver = RosapiTypeResolver()


def detect_rosapi_types(ws_manager: WebSocketManager) -> None:
    """Probe rosbridge and cache the correct type format. Call once at startup."""
    _resolver.detect(ws_manager)


def is_ros1() -> bool:
    """Return True if the detected version is ROS 1 (or unknown)."""
    return not _resolver._is_ros2


def rosapi_type(short_name: str) -> str:
    """Get the version-appropriate rosapi type string.

    Example::

        rosapi_type("Services")  # → "rosapi/Services" on ROS 1
        # → "rosapi_msgs/srv/Services" on ROS 2
    """
    return _resolver.get_type(short_name)


def rosapi_service(service_name: str) -> str:
    """Get the version-appropriate rosapi service path.

    Example::

        rosapi_service("nodes")  # → "/rosapi/nodes" on ROS 1
        # → "/rosapi_node/nodes" on ROS 2
    """
    return _resolver.get_service(service_name)
