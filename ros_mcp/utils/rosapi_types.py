"""Version-aware rosapi service type and path resolver.

ROS 1 rosbridge registers services under ``/rosapi/`` with short types
like ``rosapi/Topics``.

ROS 2 rosbridge registers services under ``/rosapi_node/`` with
fully-qualified types like ``rosapi_msgs/srv/Topics``.

This module probes the running rosbridge *once* and caches the correct
format so every subsequent call gets the right type and path automatically.
"""

from __future__ import annotations

import enum
import logging
from typing import Any

from ros_mcp.utils.websocket import WebSocketManager

logger = logging.getLogger(__name__)


class RosVersion(enum.Enum):
    """Detected ROS version.

    Enum order defines probe order: ROS2 is tried first because some ROS 2
    systems also expose a legacy /rosapi/ path for backward compatibility.
    Probing ROS2 first avoids false positives.
    """

    ROS2 = "ros2"
    ROS1 = "ros1"


# Per-version config
_VERSION_CONFIG: dict[RosVersion, dict[str, str]] = {
    RosVersion.ROS1: {"prefix": "/rosapi", "type_prefix": "rosapi"},
    RosVersion.ROS2: {"prefix": "/rosapi_node", "type_prefix": "rosapi_msgs/srv"},
}


class RosapiTypeResolver:
    """Resolves rosapi service type strings and paths based on ROS version."""

    def __init__(self) -> None:
        self._version: RosVersion | None = None
        self._distro: str = ""

    def detect(self, ws_manager: WebSocketManager) -> None:
        """Probe rosbridge to determine the ROS version (1 vs 2).

        Tries ``get_ros_version`` under each known prefix.
        Both probes share a single WebSocket connection.
        """
        with ws_manager:
            for version in RosVersion:
                config = _VERSION_CONFIG[version]
                prefix = config["prefix"]
                try:
                    request: dict[str, Any] = {
                        "op": "call_service",
                        "id": f"rosapi_detect_{version.value}",
                        "service": f"{prefix}/get_ros_version",
                        "args": {},
                    }
                    response = ws_manager.request(request)

                    if not response or not isinstance(response, dict):
                        continue
                    if response.get("result") is False:
                        continue

                    values = response.get("values")
                    if isinstance(values, dict) and "distro" in values:
                        self._distro = str(values["distro"]).strip().lower()
                        self._version = version
                        logger.info(
                            "Detected ROS distro '%s' (%s) → prefix=%s",
                            self._distro,
                            version.value,
                            prefix,
                        )
                        return
                except Exception as e:
                    logger.debug("Detection with %s prefix %s failed: %s", version.value, prefix, e)

        # Default to ROS 1 if detection fails
        self._version = RosVersion.ROS1
        logger.info("Defaulting to %s", self._version.value)

    def _reset(self) -> None:
        """Reset detection state. For testing only."""
        self._version = None
        self._distro = ""

    @property
    def version(self) -> RosVersion:
        if self._version is None:
            logger.warning("Accessed version before detect() — defaulting to ROS1")
            self._version = RosVersion.ROS1
        return self._version

    @property
    def distro(self) -> str:
        return self._distro

    def get_type(self, short_name: str) -> str:
        """Return the version-appropriate type string."""
        type_prefix = _VERSION_CONFIG[self.version]["type_prefix"]
        return f"{type_prefix}/{short_name}"

    def get_service(self, service_name: str) -> str:
        """Return the version-appropriate service path."""
        prefix = _VERSION_CONFIG[self.version]["prefix"]
        return f"{prefix}/{service_name}"


# Module-level singleton
_resolver = RosapiTypeResolver()


def detect_rosapi_types(ws_manager: WebSocketManager) -> None:
    """Probe rosbridge and cache the correct type format. Call once at startup."""
    _resolver.detect(ws_manager)


def _reset_resolver() -> None:
    """Reset global resolver state. For testing only."""
    _resolver._reset()


def get_ros_version() -> RosVersion:
    """Return the detected ROS version enum."""
    return _resolver.version


def get_distro() -> str:
    """Return the detected ROS distro name (e.g. 'noetic', 'humble')."""
    return _resolver.distro


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
