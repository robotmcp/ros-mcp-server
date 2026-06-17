"""Integration tests for the ros-metadata MCP resources (step 7).

These exercise the five ``ros-mcp://ros-metadata/*`` resources registered by
``register_ros_metadata_resources`` against a live rosbridge container. Each
resource returns a JSON string; tests parse it and assert the payload shape plus
known turtlesim entities.

Resource URIs:
- ``ros-mcp://ros-metadata/all``          → topics/services/nodes/params/version
- ``ros-mcp://ros-metadata/nodes/all``    → per-node publishers/subscribers/services
- ``ros-mcp://ros-metadata/services/all`` → per-service type/providers
- ``ros-mcp://ros-metadata/topics/all``   → per-topic type/publishers/subscribers
- ``ros-mcp://ros-metadata/actions/all``  → per-action type/status

Action inspection uses the rosapi ``action_servers`` service, which is a ROS 2
rosbridge feature. On ROS 1 the resource returns a structured
"not supported" payload instead of an action list (see #320), so content
assertions for actions are gated to ROS 2.
"""

import json

import pytest
from fastmcp import FastMCP

from ros_mcp.resources import register_all_resources
from ros_mcp.utils.rosapi_types import RosVersion, get_ros_version
from ros_mcp.utils.websocket import WebSocketManager

pytestmark = [pytest.mark.integration]

ALL = "ros-mcp://ros-metadata/all"
NODES = "ros-mcp://ros-metadata/nodes/all"
SERVICES = "ros-mcp://ros-metadata/services/all"
TOPICS = "ros-mcp://ros-metadata/topics/all"
ACTIONS = "ros-mcp://ros-metadata/actions/all"


def _read(resources, uri):
    """Read a resource by URI and parse its JSON payload into a dict."""
    payload = resources[uri]()
    assert isinstance(payload, str), f"resource {uri} should return a JSON string"
    return json.loads(payload)


def _assert_counts_match(name, detail, kinds):
    """Assert each ``<kind>_count`` equals the length of its ``<kind>s`` list."""
    for kind in kinds:
        assert detail[f"{kind}_count"] == len(detail[f"{kind}s"]), (name, kind, detail)


class TestAllMetadata:
    """Verify ros-mcp://ros-metadata/all aggregates the system snapshot."""

    def test_returns_core_sections(self, resources):
        """The snapshot exposes topics/services/nodes/parameters as lists."""
        data = _read(resources, ALL)
        for key in ("topics", "services", "nodes", "parameters"):
            assert isinstance(data[key], list), f"{key} should be a list"
        assert isinstance(data["summary"], dict)

    def test_reports_detected_version(self, resources):
        """ros_version reflects the resolver detected at connect time."""
        data = _read(resources, ALL)
        expected = "2" if get_ros_version() == RosVersion.ROS2 else "1"
        assert data["ros_version"]["version"] == expected
        assert isinstance(data["ros_version"]["distro"], str)

    def test_summary_counts_match_lists(self, resources):
        """summary totals match the lengths of their corresponding lists."""
        data = _read(resources, ALL)
        summary = data["summary"]
        assert summary["total_topics"] == len(data["topics"])
        assert summary["total_services"] == len(data["services"])
        assert summary["total_nodes"] == len(data["nodes"])
        assert summary["total_parameters"] == len(data["parameters"])

    def test_includes_turtlesim_node(self, resources):
        """The turtlesim node launched by the container is present."""
        data = _read(resources, ALL)
        assert any("/turtlesim" in n for n in data["nodes"]), f"turtlesim not in {data['nodes']}"

    def test_topics_carry_names_and_types(self, resources):
        """Each topic entry is a {name, type} dict with a leading-slash name."""
        data = _read(resources, ALL)
        assert data["topics"], "expected at least one topic"
        for entry in data["topics"]:
            assert entry["name"].startswith("/"), f"topic name should start with /: {entry}"
            assert entry["type"], f"topic type should be non-empty: {entry}"

    def test_no_errors_on_healthy_container(self, resources):
        """A healthy turtlesim snapshot reports no collection errors."""
        data = _read(resources, ALL)
        assert data["errors"] == [], f"unexpected errors: {data['errors']}"
        assert data["summary"]["has_errors"] is False


class TestNodesDetails:
    """Verify ros-mcp://ros-metadata/nodes/all returns per-node connections."""

    def test_shape(self, resources):
        """Payload has total_nodes, a nodes map, and a node_errors list."""
        data = _read(resources, NODES)
        assert data["total_nodes"] > 0
        assert isinstance(data["nodes"], dict)
        assert data["total_nodes"] == len(data["nodes"])
        assert isinstance(data["node_errors"], list)

    def test_turtlesim_has_pubs_and_subs(self, resources):
        """turtlesim publishes (pose) and subscribes (cmd_vel)."""
        data = _read(resources, NODES)
        turtlesim = next((n for n in data["nodes"] if "/turtlesim" in n), None)
        assert turtlesim is not None, f"turtlesim not in {list(data['nodes'])}"
        detail = data["nodes"][turtlesim]
        assert detail["publisher_count"] > 0, "turtlesim should publish"
        assert detail["subscriber_count"] > 0, "turtlesim should subscribe"

    def test_counts_match_lists(self, resources):
        """Each node's *_count fields match the lengths of their lists."""
        data = _read(resources, NODES)
        for name, detail in data["nodes"].items():
            _assert_counts_match(name, detail, ("publisher", "subscriber", "service"))


class TestServicesDetails:
    """Verify ros-mcp://ros-metadata/services/all returns per-service info."""

    def test_shape(self, resources):
        """Payload has total_services, a services map, and a service_errors list."""
        data = _read(resources, SERVICES)
        assert data["total_services"] > 0
        assert isinstance(data["services"], dict)
        assert data["total_services"] == len(data["services"])
        assert isinstance(data["service_errors"], list)

    def test_provider_count_matches_list(self, resources):
        """Each service's provider_count matches its providers list length."""
        data = _read(resources, SERVICES)
        for name, detail in data["services"].items():
            assert detail["provider_count"] == len(detail["providers"]), name

    def test_includes_rosapi_service(self, resources):
        """The rosapi services that back this resource are themselves listed."""
        data = _read(resources, SERVICES)
        assert any("rosapi" in s for s in data["services"]), (
            f"no rosapi service in {list(data['services'])[:10]}..."
        )


class TestTopicsDetails:
    """Verify ros-mcp://ros-metadata/topics/all returns per-topic connections."""

    def test_shape(self, resources):
        """Payload has total_topics, a topics map, and a topic_errors list."""
        data = _read(resources, TOPICS)
        assert data["total_topics"] > 0
        assert isinstance(data["topics"], dict)
        assert data["total_topics"] == len(data["topics"])
        assert isinstance(data["topic_errors"], list)

    def test_turtle_pose_published(self, resources):
        """/turtle1/pose exists, is typed, and has turtlesim as a publisher."""
        data = _read(resources, TOPICS)
        assert "/turtle1/pose" in data["topics"], f"pose not in {list(data['topics'])}"
        pose = data["topics"]["/turtle1/pose"]
        assert pose["type"], "pose topic should carry a type"
        assert pose["publisher_count"] > 0, "turtlesim should publish /turtle1/pose"

    def test_counts_match_lists(self, resources):
        """Each topic's *_count fields match the lengths of their lists."""
        data = _read(resources, TOPICS)
        for name, detail in data["topics"].items():
            _assert_counts_match(name, detail, ("publisher", "subscriber"))


class TestActionsDetails:
    """Verify ros-mcp://ros-metadata/actions/all.

    Action inspection requires the rosapi ``action_servers`` service (ROS 2).
    On ROS 1 the resource returns a structured "not supported" payload, so the
    content assertion is gated to ROS 2.
    """

    def test_payload_is_structured(self, resources):
        """On any distro the payload is a dict that parses cleanly.

        Either an action listing (total_actions/actions/action_errors) or, when
        rosapi lacks action_servers, an error payload carrying a compatibility
        explanation — never a crash.
        """
        data = _read(resources, ACTIONS)
        assert isinstance(data, dict)
        if "error" in data:
            assert "compatibility" in data, f"error payload missing compatibility: {data}"
        else:
            assert isinstance(data["total_actions"], int)
            assert isinstance(data["actions"], dict)
            assert isinstance(data["action_errors"], list)

    @pytest.mark.skipif(
        "get_ros_version() != RosVersion.ROS2",
        reason="rosapi action_servers inspection is a ROS 2 feature (see #320)",
    )
    def test_rotate_absolute_listed(self, resources):
        """turtlesim's /turtle1/rotate_absolute action is discovered on ROS 2."""
        data = _read(resources, ACTIONS)
        assert "error" not in data, f"unexpected error payload: {data}"
        assert "/turtle1/rotate_absolute" in data["actions"], (
            f"rotate_absolute not in {list(data['actions'])}"
        )
        assert "status" in data["actions"]["/turtle1/rotate_absolute"]


@pytest.fixture
def offline_resources():
    """Resources bound to an unreachable rosbridge (an unused local port).

    Exercises the graceful-degradation paths: with no rosbridge to talk to,
    every resource must still return a structured JSON payload rather than
    raise. Does not use the shared ``ws`` fixture, so it needs no container.
    """
    ws = WebSocketManager("127.0.0.1", 1, default_timeout=1.0)
    mcp = FastMCP("offline-ros-mcp")
    register_all_resources(mcp, ws)
    return {uri: res.fn for uri, res in mcp._resource_manager._resources.items()}


class TestOfflineDegradation:
    """Every resource degrades gracefully when rosbridge is unreachable."""

    @pytest.mark.parametrize("uri", [NODES, SERVICES, TOPICS, ACTIONS])
    def test_detail_resource_reports_structured_error(self, offline_resources, uri):
        """Detail resources return a top-level error payload, never a crash."""
        data = json.loads(offline_resources[uri]())
        assert isinstance(data, dict)
        assert "error" in data, f"{uri} should report a structured error offline: {data}"

    def test_all_metadata_returns_empty_snapshot(self, offline_resources):
        """The aggregate snapshot still parses, with empty sections."""
        data = json.loads(offline_resources[ALL]())
        assert isinstance(data["summary"], dict)
        assert data["topics"] == []
        assert data["services"] == []
        assert data["nodes"] == []
