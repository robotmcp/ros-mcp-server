"""Version-aware rosapi service type and path resolver.

Detection strategy:
- ``get_ros_version`` service exists → **ROS 2** (this service is ROS 2-only)
- ``get_ros_version`` absent, ``get_param /rosdistro`` responds → **ROS 1**
- Neither responds → ``DetectionError``

Version determines the type format:
- ROS 1: ``rosapi/Topics``
- ROS 2: ``rosapi_msgs/srv/Topics``

The service path prefix (``/rosapi/`` vs ``/rosapi_node/``) depends on the
rosapi node name in the launch file, not the ROS version. Both are probed
automatically.

This module probes the running rosbridge *once* and caches the result.
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


class DetectionError(RuntimeError):
    """Raised when ROS version detection fails due to infrastructure problems."""


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

        Strategy:
        1. Try ``get_ros_version`` at each prefix. This service only exists
           in ROS 2, so a successful response with ``version >= 2`` confirms ROS 2.
        2. If every prefix returned ``result: false`` (service not found), that
           confirms ROS 1 — the absence of ``get_ros_version`` is proof.
        3. If every prefix failed with an exception (network error, timeout),
           raise ``DetectionError`` — we cannot determine the version.
        4. On ROS 1, optionally get the distro name via ``get_param /rosdistro``.
        """
        got_service_not_found = False
        exceptions: list[str] = []

        # Phase 1: try get_ros_version (ROS 2 only service)
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
                        exceptions.append(f"{prefix}: empty or non-dict response")
                        continue

                    if response.get("result") is False:
                        # Service not found — this is a genuine signal
                        got_service_not_found = True
                        continue

                    values = response.get("values")
                    if not isinstance(values, dict):
                        exceptions.append(f"{prefix}: values is not a dict: {values}")
                        continue

                    # Determine ROS version from the response
                    raw_version = values.get("version")
                    if raw_version is not None and int(raw_version) >= 2:
                        self._version = RosVersion.ROS2
                        self._distro = str(values.get("distro", "")).strip().lower()
                        self._service_prefix = prefix
                        logger.info(
                            "Detected ROS 2 distro '%s' → prefix=%s",
                            self._distro,
                            prefix,
                        )
                        return

                    # version < 2 or missing — unexpected, treat as ROS 1
                    got_service_not_found = True

                except Exception as e:
                    exceptions.append(f"{prefix}: {e}")

        # Phase 1 complete — no ROS 2 found
        if not got_service_not_found and exceptions:
            # Every probe failed with exceptions — we never reached rosbridge
            raise DetectionError(
                "Could not detect ROS version — all probes failed with errors: "
                + "; ".join(exceptions)
            )

        # Phase 2: confirmed ROS 1 (get_ros_version not found = ROS 2 service absent)
        self._version = RosVersion.ROS1
        self._service_prefix = "/rosapi"
        logger.info("get_ros_version not available — confirmed ROS 1")

        # Optionally get distro name
        try:
            with ws_manager:
                request = {
                    "op": "call_service",
                    "id": "rosapi_detect_ros1_distro",
                    "service": "/rosapi/get_param",
                    "args": {"name": "/rosdistro"},
                }
                response = ws_manager.request(request)

                if response and isinstance(response, dict) and response.get("result") is not False:
                    values = response.get("values")
                    if values:
                        distro = values.get("value") if isinstance(values, dict) else values
                        self._distro = (
                            str(distro).strip('"').replace("\\n", "").replace("\n", "").lower()
                        )
                        logger.info("ROS 1 distro: '%s'", self._distro)
        except Exception as e:
            logger.warning("ROS 1 distro detection failed (non-fatal): %s", e)

    def _reset(self) -> None:
        """Reset detection state. For testing only."""
        self._version = None
        self._distro = ""
        self._service_prefix = "/rosapi"

    @property
    def version(self) -> RosVersion:
        if self._version is None:
            raise DetectionError("ROS version not detected — call detect_rosapi_types() first")
        return self._version

    @property
    def distro(self) -> str:
        return self._distro

    def get_type(self, short_name: str) -> str:
        """Return the version-appropriate type string.

        Falls back to ROS 2 format (rosapi_msgs/srv/) when version is unknown.
        """
        if self._version is None:
            logger.warning(
                "ROS version unknown — falling back to ROS 2 type format for '%s'",
                short_name,
            )
            type_prefix = _TYPE_PREFIX[RosVersion.ROS2]
        else:
            type_prefix = _TYPE_PREFIX[self._version]
        return f"{type_prefix}/{short_name}"

    def get_service(self, service_name: str) -> str:
        """Return the discovered service path."""
        return f"{self._service_prefix}/{service_name}"


# Module-level singleton
_resolver = RosapiTypeResolver()


def detect_rosapi_types(ws_manager: WebSocketManager) -> None:
    """Probe rosbridge and cache the correct type format. Call once at startup.

    Raises:
        DetectionError: If rosbridge is unreachable (all probes failed with exceptions).
    """
    _resolver.detect(ws_manager)


def _reset_resolver() -> None:
    """Reset global resolver state. For testing only."""
    _resolver._reset()


def get_ros_version() -> RosVersion:
    """Return the detected ROS version enum.

    Raises:
        DetectionError: If detect_rosapi_types() was never called.
    """
    return _resolver.version


def get_distro() -> str:
    """Return the detected ROS distro name (e.g. 'noetic', 'humble').

    May be empty on ROS 1 if distro detection failed.
    """
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
