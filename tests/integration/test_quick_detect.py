"""Quick standalone test: detect ROS version against a running rosbridge.

Usage (assumes rosbridge may or may not be running on port 9090):

    uv run python tests/integration/test_quick_detect.py

Scenarios:
  - No rosbridge running    → DetectionError (expected)
  - ROS 1 Noetic running    → ROS1, prefix=/rosapi
  - ROS 2 Humble running    → ROS2, prefix=/rosapi
  - ROS 2 Jazzy running     → ROS2, prefix=/rosapi_node
"""

import json
import sys

sys.path.insert(0, ".")

from ros_mcp.utils.rosapi_types import (  # noqa: E402
    DetectionError,
    _reset_resolver,
    detect_rosapi_types,
    get_distro,
    get_ros_version,
    rosapi_service,
    rosapi_type,
)
from ros_mcp.utils.websocket import WebSocketManager  # noqa: E402

ws = WebSocketManager("127.0.0.1", 9090, default_timeout=3.0)
_reset_resolver()

try:
    detect_rosapi_types(ws)
except DetectionError as e:
    print(f"DETECTION FAILED: {e}")
    print("This is expected if no rosbridge is running.")
    sys.exit(1)

version = get_ros_version()
distro = get_distro()

print(f"version  = {version}")
print(f"distro   = {distro!r}")
print(f"prefix   = {rosapi_service('nodes')}")
print(f"type     = {rosapi_type('Topics')}")
print()

# Verify a real call works
ws.connect()
msg = {
    "op": "call_service",
    "service": rosapi_service("nodes"),
    "type": rosapi_type("Nodes"),
    "args": {},
}
ws.ws.send(json.dumps(msg))
resp = json.loads(ws.ws.recv())
ws.close()

if resp.get("result") is False:
    print(f"SERVICE CALL FAILED: {resp}")
    sys.exit(1)

nodes = resp.get("values", {}).get("nodes", [])
print(f"nodes    = {nodes}")
print(f"result   = OK ({len(nodes)} nodes found)")
