"""Unit tests for the ros-metadata MCP resources.

These exercise the resource callables directly with a fake ``mcp`` and a fake
``ws_manager``, so they need no running rosbridge.
"""

import json

from ros_mcp.resources.ros_metadata import register_ros_metadata_resources


class _FakeMcp:
    """Captures functions registered via the ``@mcp.resource(uri)`` decorator."""

    def __init__(self):
        self.resources = {}

    def resource(self, uri):
        def decorator(fn):
            self.resources[uri] = fn
            return fn

        return decorator


class _FakeWs:
    """Minimal stand-in for WebSocketManager: a context manager with ``request``."""

    def __init__(self, responses):
        self._responses = responses
        self.default_timeout = 2.0

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def request(self, message, timeout=None):
        return self._responses.get(message.get("service", ""), {})


def _get_all_resource(ws):
    mcp = _FakeMcp()
    register_ros_metadata_resources(mcp, ws)
    return mcp.resources["ros-mcp://ros-metadata/all"]


def test_get_all_metadata_handles_string_values_for_topics():
    """Regression for #251.

    rosbridge can return a *string* in ``values`` (e.g. when a service does not
    exist). The topics block used ``response["values"].get(...)``, which raised
    "'str' object has no attribute 'get'". It must instead degrade gracefully to
    an empty topics list with no error recorded.
    """
    ws = _FakeWs({"/rosapi/topics": {"values": "service /rosapi/topics does not exist"}})
    get_all = _get_all_resource(ws)

    data = json.loads(get_all())  # must not raise

    assert data["topics"] == []
    assert not any("has no attribute" in err for err in data.get("errors", []))


def test_get_all_metadata_parses_topics_with_types():
    """Well-formed topics responses are paired with their types."""
    ws = _FakeWs(
        {
            "/rosapi/topics": {
                "values": {"topics": ["/a", "/b"], "types": ["std_msgs/String", "std_msgs/Int32"]}
            }
        }
    )
    get_all = _get_all_resource(ws)

    data = json.loads(get_all())

    assert data["topics"] == [
        {"name": "/a", "type": "std_msgs/String"},
        {"name": "/b", "type": "std_msgs/Int32"},
    ]
