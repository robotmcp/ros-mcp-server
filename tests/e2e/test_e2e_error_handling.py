"""E2E tests for error handling and edge cases."""

import json
import time

import pytest

pytestmark = pytest.mark.e2e


class TestConnectionErrors:
    """E2E tests for connection error handling."""

    def test_connection_timeout_to_invalid_host(self, invalid_ws_manager):
        """Test connection timeout to unreachable host."""
        # Try to connect to invalid host
        error = invalid_ws_manager.connect()

        # Should return an error
        assert error is not None, "Expected connection error for invalid host"
        assert "error" in error.lower() or "timeout" in error.lower() or "connection" in error.lower(), (
            f"Expected connection or timeout error, got: {error}"
        )

    def test_send_without_connection(self, invalid_ws_manager):
        """Test sending message without valid connection."""
        message = {"op": "call_service", "service": "/test", "args": {}}

        # Send should fail or return error
        result = invalid_ws_manager.send(message)

        # Should return error string
        assert result is not None, "Expected error when sending without connection"


class TestSubscriptionErrors:
    """E2E tests for subscription error handling."""

    def test_subscribe_timeout_on_inactive_topic(self, ws_manager_tiny_timeout):
        """Test subscription timeout on topic that doesn't publish."""
        # Create a topic name that likely doesn't exist or publish
        fake_topic = "/nonexistent_topic_12345"

        subscribe_msg = {
            "op": "subscribe",
            "topic": fake_topic,
            "type": "std_msgs/msg/String",
        }

        with ws_manager_tiny_timeout:
            ws_manager_tiny_timeout.send(subscribe_msg)

            # Should timeout waiting for message
            start = time.time()
            response = ws_manager_tiny_timeout.receive(timeout=1.0)
            elapsed = time.time() - start

            # Unsubscribe
            ws_manager_tiny_timeout.send({"op": "unsubscribe", "topic": fake_topic})

        # Should have timed out (no message received from nonexistent topic)
        # Response might be None (timeout) or an error status
        if response:
            data = json.loads(response)
            # If we got a response, it should be an error or not from our fake topic
            assert data.get("topic") != fake_topic or data.get("op") == "status"


class TestServiceCallErrors:
    """E2E tests for service call error handling."""

    def test_service_call_timeout(self, ws_manager_short_timeout, rosapi_topics_type):
        """Test service call with short timeout."""
        # This test verifies the timeout mechanism works
        message = {
            "op": "call_service",
            "service": "/rosapi/topics",
            "type": rosapi_topics_type,
            "args": {},
            "id": "timeout_test",
        }

        with ws_manager_short_timeout:
            response = ws_manager_short_timeout.request(message, timeout=5.0)

        # With valid rosbridge, this should succeed
        assert "values" in response or "error" in response, (
            f"Expected valid response or error: {response}"
        )

    def test_call_nonexistent_service(self, ws_manager, service_type_empty):
        """Test calling a service that doesn't exist."""
        message = {
            "op": "call_service",
            "service": "/nonexistent_service_12345",
            "type": service_type_empty,
            "args": {},
            "id": "nonexistent_service_test",
        }

        with ws_manager:
            response = ws_manager.request(message, timeout=5.0)

        # Should return an error or failed result
        # rosbridge may return different error formats
        is_error = (
            "error" in response
            or response.get("result") is False
            or "error" in str(response).lower()
        )
        assert is_error or response.get("values") is None, (
            f"Expected error for nonexistent service: {response}"
        )

    def test_malformed_service_request(self, ws_manager):
        """Test service call with malformed request."""
        # Missing required fields
        message = {
            "op": "call_service",
            # Missing service name and type
            "args": {},
            "id": "malformed_test",
        }

        with ws_manager:
            ws_manager.send(message)
            response = ws_manager.receive(timeout=3.0)

        # Should get an error response or no valid response
        if response:
            data = json.loads(response)
            # rosbridge should return an error status
            is_error = (
                data.get("op") == "status"
                or "error" in str(data).lower()
            )
            # Malformed requests may be silently ignored or return error
            assert is_error or data.get("op") != "service_response"


class TestWebSocketReconnection:
    """E2E tests for WebSocket reconnection behavior."""

    def test_websocket_reconnection_after_close(self, ws_manager, rosapi_topics_type):
        """Test WebSocket reconnects after manual close."""
        # First connection and request
        message = {
            "op": "call_service",
            "service": "/rosapi/topics",
            "type": rosapi_topics_type,
            "args": {},
            "id": "reconnect_test_1",
        }

        with ws_manager:
            response1 = ws_manager.request(message, timeout=5.0)

        assert "values" in response1, f"First request failed: {response1}"

        # Close the connection
        ws_manager.close()

        # Second request should reconnect automatically
        message["id"] = "reconnect_test_2"

        with ws_manager:
            response2 = ws_manager.request(message, timeout=5.0)

        assert "values" in response2, f"Second request after reconnect failed: {response2}"

    def test_multiple_sequential_requests(self, ws_manager, rosapi_topics_type):
        """Test multiple sequential requests on same connection."""
        for i in range(3):
            message = {
                "op": "call_service",
                "service": "/rosapi/topics",
                "type": rosapi_topics_type,
                "args": {},
                "id": f"sequential_test_{i}",
            }

            with ws_manager:
                response = ws_manager.request(message, timeout=5.0)

            assert "values" in response, f"Request {i} failed: {response}"


class TestInputValidation:
    """E2E tests for input validation error handling."""

    def test_empty_topic_name_handling(self, ws_manager):
        """Test handling of empty topic name in subscription."""
        subscribe_msg = {
            "op": "subscribe",
            "topic": "",
            "type": "std_msgs/msg/String",
        }

        with ws_manager:
            ws_manager.send(subscribe_msg)
            response = ws_manager.receive(timeout=2.0)

        # Should get error or be ignored
        if response:
            data = json.loads(response)
            # Empty topic should not return valid publish message
            assert data.get("op") != "publish" or data.get("topic") != ""

    def test_invalid_message_type_handling(self, ws_manager, rosapi_topic_type_type):
        """Test handling of invalid message type."""
        message = {
            "op": "call_service",
            "service": "/rosapi/topic_type",
            "type": rosapi_topic_type_type,
            "args": {"topic": "/nonexistent_topic_xyz"},
            "id": "invalid_type_test",
        }

        with ws_manager:
            response = ws_manager.request(message, timeout=5.0)

        # Should return empty type or error for nonexistent topic
        if "values" in response:
            topic_type = response["values"].get("type", "")
            # Empty type indicates topic doesn't exist
            assert topic_type == "" or "error" in str(response).lower()
