"""Unit tests for ros-metadata MCP resources (no live rosbridge)."""

import json

from ros_mcp.resources.ros_metadata import register_ros_metadata_resources


class _FakeMcp:
    def __init__(self):
        self.resources = {}

    def resource(self, uri):
        def decorator(fn):
            self.resources[uri] = fn
            return fn

        return decorator


class _FakeWs:
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
    """Regression for #251 / salvage of #343."""

    # Service path is version-dependent; cover both common keys by emptying responses
    # except one string-values topics entry via side_effect-like map on full service names.
    # Map by scanning keys in request: our Fake uses service field as key.
    # Use both rosapi and rosapi_namespaced possibilities by monkeypatching responses for any.
    class WS(_FakeWs):
        def request(self, message, timeout=None):
            if "topics" in message.get("service", ""):
                return {"values": "service /rosapi/topics does not exist"}
            return {}

    data = json.loads(_get_all_resource(WS({}))())
    assert data["topics"] == []
    assert not any("has no attribute" in err for err in data.get("errors", []))


def test_get_all_metadata_parses_topics_with_types():
    class WS(_FakeWs):
        def request(self, message, timeout=None):
            if "topics" in message.get("service", ""):
                return {
                    "values": {
                        "topics": ["/a", "/b"],
                        "types": ["std_msgs/String", "std_msgs/Int32"],
                    }
                }
            return {}

    data = json.loads(_get_all_resource(WS({}))())
    assert data["topics"] == [
        {"name": "/a", "type": "std_msgs/String"},
        {"name": "/b", "type": "std_msgs/Int32"},
    ]
