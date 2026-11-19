"""Shared fixtures for unit tests."""

import asyncio
import json
from concurrent.futures import Future
from queue import Queue
from threading import Thread

import pytest
from websockets.asyncio.server import serve


@pytest.fixture
def loopback_host(monkeypatch):
    """Bypass HTTP proxies for the local WebSocket endpoint."""
    host = "127.0.0.1"
    monkeypatch.setenv("no_proxy", host)
    return host


@pytest.fixture
def mock_rosbridge(request, loopback_host):
    """Record incoming requests and send the configured text reply, if any."""
    received = Queue()
    reply = request.param
    started = Future()

    async def handle(connection):
        async for message in connection:
            received.put(json.loads(message))
            if reply is not None:
                await connection.send(reply)

    async def serve_until_closed():
        async with serve(handle, loopback_host, 0) as server:
            address = server.sockets[0].getsockname()
            started.set_result((address, asyncio.get_running_loop(), server))
            await server.wait_closed()

    def run():
        try:
            asyncio.run(serve_until_closed())
        except Exception as error:
            if started.done():
                raise
            started.set_exception(error)

    # WebSocketManager blocks while waiting for a reply, so serve on a separate thread.
    worker = Thread(target=run, daemon=True)
    worker.start()
    address, loop, server = started.result(timeout=3)
    try:
        yield address, received
    finally:
        loop.call_soon_threadsafe(server.close)
        worker.join(timeout=3)
        assert not worker.is_alive(), "The mock rosbridge server did not stop"


# ---------------------------------------------------------------------------
# Robot config fixtures (used by test_config_utils.py)
# ---------------------------------------------------------------------------


@pytest.fixture
def valid_robot_yaml(tmp_path):
    """Create a temporary valid robot YAML file and return (specs_dir, robot_name)."""
    yaml_content = (
        "name: test_robot\ntype: simulated\nprompts: |\n  This is a test robot for unit testing.\n"
    )
    yaml_file = tmp_path / "test_robot.yaml"
    yaml_file.write_text(yaml_content)
    return str(tmp_path), "test_robot"


@pytest.fixture
def empty_robot_yaml(tmp_path):
    """Create a temporary empty YAML file and return (specs_dir, robot_name)."""
    yaml_file = tmp_path / "empty_robot.yaml"
    yaml_file.write_text("")
    return str(tmp_path), "empty_robot"
