"""Tests for background ROS topic subscriptions."""

import json
import queue
import threading
import time
from types import SimpleNamespace

import pytest

import ros_mcp.tools.topics as topics


class FakeMCP:
    """Capture registered tool functions without running an MCP server."""

    def __init__(self):
        self.tools = {}

    def tool(self, **kwargs):
        def decorator(func):
            self.tools[func.__name__] = func
            return func

        return decorator


class FakeConnection:
    def __init__(self):
        self.connected = True


class FakeWebSocketManager:
    """In-memory WebSocket manager for deterministic unit tests."""

    def __init__(self, ip, port, default_timeout=2.0, disconnect_on_idle=False):
        self.ip = ip
        self.port = port
        self.default_timeout = default_timeout
        self.ws = FakeConnection()
        self.incoming = queue.Queue()
        self.sent = []
        self.disconnect_on_idle = disconnect_on_idle
        self.send_error = None
        self.connect_error = None
        self._lock = threading.RLock()
        self.lock = self._lock

    def connect(self):
        if self.connect_error:
            return self.connect_error
        if self.ws is None or not self.ws.connected:
            if self.disconnect_on_idle:
                return "simulated connection loss"
            self.ws = FakeConnection()
        return None

    def send(self, message):
        self.sent.append(message)
        return self.send_error

    def receive(self, timeout=None):
        try:
            return self.incoming.get(timeout=min(timeout or 0.05, 0.05))
        except queue.Empty:
            if self.disconnect_on_idle:
                self.ws = None
            return None

    def close(self):
        if self.ws is not None:
            self.ws.connected = False
        self.ws = None


@pytest.fixture
def harness(monkeypatch):
    managers = []
    disconnect_next = {"value": False}
    connect_error_next = {"value": None}
    send_error_next = {"value": None}

    def manager_factory(ip, port, default_timeout=2.0):
        manager = FakeWebSocketManager(
            ip,
            port,
            default_timeout,
            disconnect_on_idle=disconnect_next["value"],
        )
        manager.connect_error = connect_error_next["value"]
        manager.send_error = send_error_next["value"]
        disconnect_next["value"] = False
        connect_error_next["value"] = None
        send_error_next["value"] = None
        managers.append(manager)
        return manager

    monkeypatch.setattr(topics, "WebSocketManager", manager_factory)

    mcp = FakeMCP()
    base_manager = SimpleNamespace(
        ip="127.0.0.1",
        port=9090,
        default_timeout=2.0,
    )
    topics.register_topic_tools(mcp, base_manager)

    obj = SimpleNamespace(
        tools=mcp.tools,
        managers=managers,
        disconnect_next=disconnect_next,
        connect_error_next=connect_error_next,
        send_error_next=send_error_next,
    )
    try:
        yield obj
    finally:
        for m in managers:
            m.close()
        topics.cleanup_background_subscriptions()


def wait_for(predicate, timeout=2.0):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return True
        time.sleep(0.01)
    return bool(predicate())


def publish(topic, message):
    return json.dumps({"op": "publish", "topic": topic, "msg": message})


def test_subscribe_validates_required_arguments(harness):
    subscribe = harness.tools["subscribe_background"]

    assert "topic" in subscribe()["error"]
    assert "msg_type" in subscribe(topic="/scan")["error"]
    assert (
        "queue_length"
        in subscribe(topic="/scan", msg_type="sensor_msgs/LaserScan", queue_length=0)["error"]
    )
    assert (
        "max_buffer"
        in subscribe(topic="/scan", msg_type="sensor_msgs/LaserScan", max_buffer=0)["error"]
    )
    assert harness.managers == []


def test_subscribe_and_retrieve_messages(harness):
    subscribe = harness.tools["subscribe_background"]
    get_messages = harness.tools["get_subscription_messages"]
    stop = harness.tools["stop_background_subscription"]

    result = subscribe(
        topic="/chatter",
        msg_type="std_msgs/String",
        max_buffer=5,
    )

    assert result["success"] is True
    assert result["status"] == "active"
    assert result["topic"] == "/chatter"
    assert len(harness.managers) == 1

    manager = harness.managers[0]
    assert manager.sent[0] == {
        "op": "subscribe",
        "topic": "/chatter",
        "type": "std_msgs/String",
        "queue_length": 10,
        "throttle_rate": 0,
    }

    manager.incoming.put(publish("/chatter", {"data": "hello"}))
    manager.incoming.put(publish("/other", {"data": "ignore"}))

    assert wait_for(lambda: get_messages(result["subscription_id"])["total_messages_received"] == 1)

    received = get_messages(result["subscription_id"])
    assert received["messages"] == [{"data": "hello"}]
    assert received["buffered_count"] == 1
    assert received["dropped_messages"] == 0

    stopped = stop(result["subscription_id"])
    assert stopped["success"] is True
    assert stopped["status"] == "stopped"
    assert manager.sent[-1] == {"op": "unsubscribe", "topic": "/chatter"}

    # Messages remain available after stopping.
    after_stop = get_messages(result["subscription_id"])
    assert after_stop["messages"] == [{"data": "hello"}]


def test_get_messages_clear_removes_only_returned_messages(harness):
    result = harness.tools["subscribe_background"](
        topic="/numbers",
        msg_type="std_msgs/Int32",
        max_buffer=5,
    )
    get_messages = harness.tools["get_subscription_messages"]
    manager = harness.managers[0]

    for number in (1, 2, 3):
        manager.incoming.put(publish("/numbers", {"data": number}))

    subscription_id = result["subscription_id"]
    assert wait_for(lambda: get_messages(subscription_id)["total_messages_received"] == 3)

    first = get_messages(subscription_id, max_messages=2, clear=True)
    assert first["messages"] == [{"data": 1}, {"data": 2}]
    assert first["buffered_count"] == 1

    remaining = get_messages(subscription_id)
    assert remaining["messages"] == [{"data": 3}]
    assert remaining["total_messages_received"] == 3

    harness.tools["stop_background_subscription"](subscription_id)


def test_buffer_limit_counts_dropped_messages(harness):
    result = harness.tools["subscribe_background"](
        topic="/numbers",
        msg_type="std_msgs/Int32",
        max_buffer=2,
    )
    get_messages = harness.tools["get_subscription_messages"]
    manager = harness.managers[0]
    subscription_id = result["subscription_id"]

    for number in (1, 2, 3):
        manager.incoming.put(publish("/numbers", {"data": number}))

    assert wait_for(lambda: get_messages(subscription_id)["total_messages_received"] == 3)

    received = get_messages(subscription_id)
    assert received["messages"] == [{"data": 2}, {"data": 3}]
    assert received["buffered_count"] == 2
    assert received["dropped_messages"] == 1

    harness.tools["stop_background_subscription"](subscription_id)


def test_unknown_subscription_ids_return_errors(harness):
    assert (
        "Unknown subscription_id" in harness.tools["get_subscription_messages"]("missing")["error"]
    )
    assert (
        "Unknown subscription_id"
        in harness.tools["stop_background_subscription"]("missing")["error"]
    )


def test_connection_loss_marks_subscription_as_error(harness):
    harness.disconnect_next["value"] = True

    result = harness.tools["subscribe_background"](
        topic="/chatter",
        msg_type="std_msgs/String",
    )
    assert result["success"] is True

    subscription_id = result["subscription_id"]
    get_messages = harness.tools["get_subscription_messages"]

    assert wait_for(lambda: get_messages(subscription_id)["status"] == "error")

    state = get_messages(subscription_id)
    assert any("connection lost" in error.lower() for error in state["errors"])
    assert wait_for(lambda: harness.managers[0].ws is None)


def test_subscribe_validates_types_and_rejects_booleans(harness):
    subscribe = harness.tools["subscribe_background"]
    get_messages = harness.tools["get_subscription_messages"]

    assert (
        "queue_length must be an integer"
        in subscribe(topic="/scan", msg_type="LaserScan", queue_length=True)["error"]
    )
    assert (
        "throttle_rate_ms must be an integer"
        in subscribe(topic="/scan", msg_type="LaserScan", throttle_rate_ms=True)["error"]
    )
    assert (
        "max_buffer must be an integer"
        in subscribe(topic="/scan", msg_type="LaserScan", max_buffer=True)["error"]
    )
    assert "topic is required" in subscribe(topic=123, msg_type="LaserScan")["error"]
    assert "topic is required" in subscribe(topic="   ", msg_type="LaserScan")["error"]
    assert "msg_type is required" in subscribe(topic="/scan", msg_type="")["error"]

    sub = subscribe(topic="/chatter", msg_type="std_msgs/String")
    assert sub["success"] is True
    sid = sub["subscription_id"]

    assert "max_messages must be an integer" in get_messages(sid, max_messages=True)["error"]
    assert "clear must be a boolean" in get_messages(sid, clear="not_a_bool")["error"]
    assert "clear must be a boolean" in get_messages(sid, clear=1)["error"]
    assert "max_messages must be an integer" in get_messages(sid, max_messages="invalid")["error"]

    harness.tools["stop_background_subscription"](sid)


def test_subscribe_startup_failures_and_cleanup(harness):
    subscribe = harness.tools["subscribe_background"]
    get_messages = harness.tools["get_subscription_messages"]

    # 1. Connection error during startup
    harness.connect_error_next["value"] = "Simulated connection refused"
    res1 = subscribe(topic="/test1", msg_type="std_msgs/String")
    assert "Could not connect to rosbridge" in res1["error"]
    assert len(harness.managers) == 1
    assert harness.managers[0].ws is None

    # 2. Send error during startup
    harness.send_error_next["value"] = "Simulated send error"
    res2 = subscribe(topic="/test2", msg_type="std_msgs/String")
    assert "Failed to subscribe" in res2["error"]
    assert len(harness.managers) == 2
    assert harness.managers[1].ws is None

    # Verify no invalid entries exist in registry
    assert "Unknown subscription_id" in get_messages("nonexistent")["error"]


def test_active_subscription_concurrency_limit(harness):
    subscribe = harness.tools["subscribe_background"]
    stop = harness.tools["stop_background_subscription"]

    subscription_ids = []
    # Start up to the maximum 20 active subscriptions
    for i in range(20):
        res = subscribe(topic=f"/topic_{i}", msg_type="std_msgs/Int32")
        assert res["success"] is True, f"Failed at subscription {i}: {res}"
        subscription_ids.append(res["subscription_id"])

    # Attempting the 21st should fail atomically
    overflow = subscribe(topic="/topic_overflow", msg_type="std_msgs/Int32")
    assert "Maximum active background subscriptions (20) reached" in overflow["error"]

    # Stop one subscription to free a slot
    stop_res = stop(subscription_ids[0])
    assert stop_res["success"] is True
    assert stop_res["status"] == "stopped"

    # Now the 21st subscription should succeed
    retry = subscribe(topic="/topic_20", msg_type="std_msgs/Int32")
    assert retry["success"] is True
    subscription_ids.append(retry["subscription_id"])

    # Clean up
    for sid in subscription_ids[1:]:
        stop(sid)


def test_concurrent_threads_cannot_exceed_limit(harness):
    subscribe = harness.tools["subscribe_background"]
    stop = harness.tools["stop_background_subscription"]

    results = []
    barrier = threading.Barrier(25)

    def worker(i):
        barrier.wait()
        res = subscribe(topic=f"/thread_topic_{i}", msg_type="std_msgs/Int32")
        results.append(res)

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(25)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=5.0)

    successes = [r for r in results if r.get("success") is True]
    failures = [
        r for r in results if "Maximum active background subscriptions" in r.get("error", "")
    ]

    assert len(successes) == 20
    assert len(failures) == 5

    for s in successes:
        stop(s["subscription_id"])


def test_stop_already_failed_and_repeated_stop(harness):
    harness.disconnect_next["value"] = True
    subscribe = harness.tools["subscribe_background"]
    get_messages = harness.tools["get_subscription_messages"]
    stop = harness.tools["stop_background_subscription"]

    res = subscribe(topic="/failing", msg_type="std_msgs/String")
    assert res["success"] is True
    sid = res["subscription_id"]

    # Wait for listener to detect disconnect and mark status as error
    assert wait_for(lambda: get_messages(sid)["status"] == "error")
    msg_state = get_messages(sid)
    assert any("connection lost" in err.lower() for err in msg_state["errors"])

    # Stopping an already-failed subscription should succeed and transition to stopped
    stop1 = stop(sid)
    assert stop1["success"] is True
    assert stop1["status"] == "stopped"

    # Repeated stop call on already-stopped subscription is idempotent
    stop2 = stop(sid)
    assert stop2["success"] is True
    assert stop2["status"] == "stopped"

    # Buffered messages and recorded errors remain accessible
    after_stop = get_messages(sid)
    assert after_stop["status"] == "stopped"
    assert any("connection lost" in err.lower() for err in after_stop["errors"])


def test_stopping_healthy_subscription_records_no_errors(harness):
    subscribe = harness.tools["subscribe_background"]
    get_messages = harness.tools["get_subscription_messages"]
    stop = harness.tools["stop_background_subscription"]

    res = subscribe(topic="/clean_stop", msg_type="std_msgs/String")
    sid = res["subscription_id"]

    stopped = stop(sid)
    assert stopped["success"] is True
    assert stopped["status"] == "stopped"

    state = get_messages(sid)
    assert state["status"] == "stopped"
    assert state["errors"] == []


def test_registry_pruning_preserves_active_records(harness):
    subscribe = harness.tools["subscribe_background"]
    stop = harness.tools["stop_background_subscription"]
    get_messages = harness.tools["get_subscription_messages"]

    # Start and stop 5 subscriptions to create stopped records
    stopped_ids = []
    for i in range(5):
        res = subscribe(topic=f"/temp_{i}", msg_type="std_msgs/String")
        sid = res["subscription_id"]
        stop(sid)
        stopped_ids.append(sid)

    # Start 1 active subscription
    active_res = subscribe(topic="/active_stay", msg_type="std_msgs/String")
    active_id = active_res["subscription_id"]

    # Verify active subscription is intact
    active_state = get_messages(active_id)
    assert active_state["status"] == "active"

    # Stop active subscription
    stop(active_id)


def test_concurrent_messages_and_clear(harness):
    subscribe = harness.tools["subscribe_background"]
    get_messages = harness.tools["get_subscription_messages"]
    stop = harness.tools["stop_background_subscription"]

    res = subscribe(topic="/stream", msg_type="std_msgs/Int32", max_buffer=200)
    sid = res["subscription_id"]
    manager = harness.managers[-1]

    # Stream messages in background while retrieving with clear=True
    received_total = []

    def producer():
        for i in range(50):
            manager.incoming.put(publish("/stream", {"data": i}))
            time.sleep(0.005)

    prod_thread = threading.Thread(target=producer)
    prod_thread.start()

    deadline = time.monotonic() + 3.0
    while time.monotonic() < deadline and len(received_total) < 50:
        chunk = get_messages(sid, max_messages=10, clear=True)
        for m in chunk["messages"]:
            received_total.append(m["data"])
        time.sleep(0.01)

    prod_thread.join(timeout=2.0)

    # Fetch remaining
    remaining = get_messages(sid, max_messages=100, clear=True)
    for m in remaining["messages"]:
        received_total.append(m["data"])

    assert received_total == list(range(50))
    stop(sid)


def test_lifecycle_cleanup_function(harness):
    subscribe = harness.tools["subscribe_background"]
    get_messages = harness.tools["get_subscription_messages"]

    res1 = subscribe(topic="/life1", msg_type="std_msgs/String")
    res2 = subscribe(topic="/life2", msg_type="std_msgs/String")

    assert res1["success"] is True
    assert res2["success"] is True

    # Call cleanup
    topics.cleanup_background_subscriptions()

    assert get_messages(res1["subscription_id"])["status"] == "stopped"
    assert get_messages(res2["subscription_id"])["status"] == "stopped"
    assert harness.managers[0].ws is None
    assert harness.managers[1].ws is None


def test_subscribe_validates_ws_manager_none():
    mcp = FakeMCP()
    topics.register_topic_tools(mcp, None)
    result = mcp.tools["subscribe_background"](topic="/test", msg_type="std_msgs/String")
    assert result == {"error": "WebSocket manager is not initialized"}


def test_subscription_ids_are_normalized(harness):
    subscribe = harness.tools["subscribe_background"]
    get_messages = harness.tools["get_subscription_messages"]
    stop = harness.tools["stop_background_subscription"]

    result = subscribe(topic="/whitespace", msg_type="std_msgs/String")
    assert result["success"] is True
    subscription_id = result["subscription_id"]

    # Surrounding whitespace should not change the subscription ID.
    messages = get_messages(f"  {subscription_id}  ")
    assert messages["status"] == "active"

    stopped = stop(f"  {subscription_id}  ")
    assert stopped["success"] is True
    assert stopped["status"] == "stopped"

    # The original ID remains valid after stopping.
    assert get_messages(subscription_id)["status"] == "stopped"


def test_cleanup_keeps_status_stopping_while_listener_is_alive(harness, monkeypatch):
    entered_receive = threading.Event()
    release_receive = threading.Event()

    def blocking_receive(self, timeout=None):
        entered_receive.set()
        release_receive.wait(timeout=5.0)
        return None

    monkeypatch.setattr(FakeWebSocketManager, "receive", blocking_receive)

    result = harness.tools["subscribe_background"](
        topic="/blocked_listener", msg_type="std_msgs/String"
    )
    assert result["success"] is True
    subscription_id = result["subscription_id"]

    try:
        assert entered_receive.wait(timeout=2.0), "Listener never entered receive()"

        # Cleanup waits for one second, but the listener is deliberately blocked.
        topics.cleanup_background_subscriptions()

        state = harness.tools["get_subscription_messages"](subscription_id)
        assert state["status"] == "stopping"
    finally:
        # Always release the listener so the test cannot leak a thread.
        release_receive.set()
