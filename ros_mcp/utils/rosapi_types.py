"""Version-aware rosapi service type and path resolver.

ROS 1 uses short type strings like ``rosapi/Topics``.
ROS 2 uses fully-qualified types like ``rosapi_msgs/srv/Topics``.

The service path prefix varies independently of ROS version:
- ``/rosapi/`` — ROS 1 Noetic, ROS 2 Humble
- ``/rosapi_node/`` — ROS 2 Jazzy and later

This module probes the running rosbridge *once* to discover both the
working prefix and the ROS version, then caches the result.
"""

from __future__ import annotations

import enum
import logging
from typing import Any

from ros_mcp.utils.websocket import WebSocketManager

logger = logging.getLogger(__name__)


class RosVersion(enum.Enum):
    """Detected ROS version."""

    ROS1 = "ros1"
    ROS2 = "ros2"


# Type prefix per ROS version
_TYPE_PREFIX: dict[RosVersion, str] = {
    RosVersion.ROS1: "rosapi",
    RosVersion.ROS2: "rosapi_msgs/srv",
}

# Known service path prefixes to probe (order matters: most common first)
_PREFIXES_TO_PROBE = ["/rosapi", "/rosapi_node"]


class RosapiTypeResolver:
    """Resolves rosapi service type strings and paths based on ROS version."""

    def __init__(self) -> None:
        self._version: RosVersion | None = None
        self._distro: str = ""
        self._service_prefix: str = "/rosapi"

    def detect(self, ws_manager: WebSocketManager) -> None:
        """Probe rosbridge to discover the ROS version and service prefix.

        Tries ``get_ros_version`` under each known prefix (``/rosapi/``,
        ``/rosapi_node/``). The first successful response determines the
        prefix. The ``version`` field in the response determines ROS 1 vs 2.
        """
        with ws_manager:
            for prefix in _PREFIXES_TO_PROBE:
                try:
                    request: dict[str, Any] = {
                        "op": "call_service",
                        "id": f"rosapi_detect_{prefix.strip('/')}",
                        "service": f"{prefix}/get_ros_version",
                        "args": {},
                    }
                    response = ws_manager.request(request)

                    if not response or not isinstance(response, dict):
                        continue
                    if response.get("result") is False:
                        continue

                    values = response.get("values")
                    if not isinstance(values, dict):
                        continue

                    # Determine ROS version from the response
                    raw_version = values.get("version")
                    if raw_version is not None and int(raw_version) >= 2:
                        self._version = RosVersion.ROS2
                    else:
                        self._version = RosVersion.ROS1

                    self._distro = str(values.get("distro", "")).strip().lower()
                    self._service_prefix = prefix

                    logger.info(
                        "Detected ROS distro '%s' (%s) → prefix=%s",
                        self._distro,
                        self._version.value,
                        prefix,
                    )
                    return
                except Exception as e:
                    logger.debug("Detection with prefix %s failed: %s", prefix, e)

        # Default to ROS 1 if detection fails
        self._version = RosVersion.ROS1
        self._service_prefix = "/rosapi"
        logger.info("Defaulting to %s", self._version.value)

    def _reset(self) -> None:
        """Reset detection state. For testing only."""
        self._version = None
        self._distro = ""
        self._service_prefix = "/rosapi"

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
        type_prefix = _TYPE_PREFIX[self.version]
        return f"{type_prefix}/{short_name}"

    def get_service(self, service_name: str) -> str:
        """Return the discovered service path."""
        return f"{self._service_prefix}/{service_name}"


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

        rosapi_service("nodes")  # → "/rosapi/nodes" on Humble
        # → "/rosapi_node/nodes" on Jazzy
    """
    return _resolver.get_service(service_name)
