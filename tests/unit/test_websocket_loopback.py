"""Exercise WebSocketManager against a local rosbridge stand-in."""

import json
import socket

import pytest

from ros_mcp.utils.websocket import WebSocketManager

SERVICE_REQUEST = {"op": "call_service", "id": "test-1", "service": "/test"}
SERVICE_RESPONSE = {
    "op": "service_response",
    "id": "test-1",
    "service": "/test",
    "result": True,
    "values": {"answer": 42},
}


@pytest.mark.parametrize(
    ("mock_rosbridge", "expected"),
    [
        pytest.param(json.dumps(SERVICE_RESPONSE), SERVICE_RESPONSE, id="response"),
        pytest.param(
            "not JSON",
            {"error": "invalid_json", "raw": "not JSON"},
            id="malformed-response",
        ),
    ],
    indirect=["mock_rosbridge"],
)
def test_request_over_websocket(mock_rosbridge, expected):
    address, received = mock_rosbridge
    with WebSocketManager(*address) as manager:
        assert manager.request(SERVICE_REQUEST) == expected

    assert received.get(timeout=2) == SERVICE_REQUEST


@pytest.mark.parametrize("mock_rosbridge", [None], indirect=True)
def test_request_timeout_over_websocket(mock_rosbridge):
    address, received = mock_rosbridge
    with WebSocketManager(*address) as manager:
        response = manager.request(SERVICE_REQUEST, timeout=0.3)

        assert response == {"error": "no response or timeout from rosbridge"}
        assert manager.ws is None

    assert received.get(timeout=2) == SERVICE_REQUEST


def test_request_reports_connection_refused(loopback_host):
    # A bound socket without a listener keeps the test port reserved.
    with socket.socket() as bound_socket:
        bound_socket.bind((loopback_host, 0))
        with WebSocketManager(*bound_socket.getsockname()) as manager:
            response = manager.request(SERVICE_REQUEST)

            assert response["error"].startswith("[WebSocket] Connection error:")
            assert manager.ws is None
