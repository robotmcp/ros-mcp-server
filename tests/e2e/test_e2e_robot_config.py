"""E2E tests for robot config operations with real ROS turtlesim."""

import pytest

pytestmark = pytest.mark.e2e


class TestDetectRosVersion:
    """E2E tests for ROS version detection."""

    def test_detect_ros_version(self, ws_manager, ros_version, rosapi_get_ros_version_type):
        """Detect ROS version via rosapi."""
        if rosapi_get_ros_version_type is None:
            pytest.skip("get_ros_version service not available in ROS 1")

        message = {
            "op": "call_service",
            "service": "/rosapi/get_ros_version",
            "type": rosapi_get_ros_version_type,
            "args": {},
            "id": "detect_ros_version_e2e",
        }

        with ws_manager:
            response = ws_manager.request(message, timeout=10.0)

        if "values" in response:
            values = response["values"]
            version = values.get("version")
            distro = values.get("distro")

            # Should detect the expected ROS version (may be int or string)
            assert str(version) == ros_version, f"Expected ROS {ros_version}, got version {version}"
            # Should have a valid distro name
            assert distro, "Expected distro name"

            if ros_version == "2":
                # Common ROS 2 distros
                valid_distros = [
                    "humble",
                    "iron",
                    "jazzy",
                    "rolling",
                    "foxy",
                    "galactic",
                ]
                assert any(d in distro.lower() for d in valid_distros), f"Unexpected distro: {distro}"
            else:
                # ROS 1 distros
                valid_distros = ["noetic", "melodic"]
                assert any(d in distro.lower() for d in valid_distros), f"Unexpected distro: {distro}"

    @pytest.mark.ros2
    def test_ros_version_response_format(self, ws_manager, rosapi_get_ros_version_type):
        """Verify ROS version response has expected format (ROS 2 only)."""
        if rosapi_get_ros_version_type is None:
            pytest.skip("get_ros_version service not available in ROS 1")

        message = {
            "op": "call_service",
            "service": "/rosapi/get_ros_version",
            "type": rosapi_get_ros_version_type,
            "args": {},
            "id": "ros_version_format_e2e",
        }

        with ws_manager:
            response = ws_manager.request(message, timeout=10.0)

        # Should have values or result
        assert "values" in response or "result" in response

        if "values" in response:
            values = response["values"]
            # Should have version and distro fields
            assert "version" in values or "distro" in values


class TestRosbridgeConnection:
    """E2E tests for verifying rosbridge is working."""

    def test_rosbridge_services_available(self, ws_manager, rosapi_services_type):
        """Verify essential rosbridge services are available."""
        message = {
            "op": "call_service",
            "service": "/rosapi/services",
            "type": rosapi_services_type,
            "args": {},
            "id": "check_rosbridge_services",
        }

        with ws_manager:
            response = ws_manager.request(message, timeout=10.0)

        assert "values" in response
        services = response["values"].get("services", [])

        # Essential rosapi services should be available
        essential_services = [
            "/rosapi/topics",
            "/rosapi/services",
            "/rosapi/nodes",
        ]

        for service in essential_services:
            assert service in services, f"Missing essential service: {service}"

    def test_rosbridge_topics_available(self, ws_manager, rosapi_topics_type):
        """Verify topics can be listed."""
        message = {
            "op": "call_service",
            "service": "/rosapi/topics",
            "type": rosapi_topics_type,
            "args": {},
            "id": "check_rosbridge_topics",
        }

        with ws_manager:
            response = ws_manager.request(message, timeout=10.0)

        assert "values" in response
        topics = response["values"].get("topics", [])

        # Should have turtlesim topics
        assert len(topics) > 0, "Should have at least one topic"
        turtlesim_topics = [t for t in topics if "turtle" in t.lower()]
        assert len(turtlesim_topics) > 0, f"Expected turtlesim topics in {topics}"


class TestRobotConfigIntegration:
    """Integration tests for robot configuration."""

    @pytest.mark.ros2
    def test_detect_version_and_list_capabilities(
        self, ws_manager, rosapi_get_ros_version_type, rosapi_services_type
    ):
        """Detect ROS version and list available capabilities (ROS 2 only)."""
        if rosapi_get_ros_version_type is None:
            pytest.skip("get_ros_version service not available in ROS 1")

        # 1. Get ROS version
        version_msg = {
            "op": "call_service",
            "service": "/rosapi/get_ros_version",
            "type": rosapi_get_ros_version_type,
            "args": {},
            "id": "integration_get_version",
        }

        with ws_manager:
            version_response = ws_manager.request(version_msg, timeout=10.0)

        version = version_response.get("values", {}).get("version", "unknown")

        # 2. Based on version, check for ROS 2 specific services
        if str(version) == "2":
            # Check for ROS 2 specific services like action_servers
            services_msg = {
                "op": "call_service",
                "service": "/rosapi/services",
                "type": rosapi_services_type,
                "args": {},
                "id": "integration_get_services",
            }

            with ws_manager:
                services_response = ws_manager.request(services_msg, timeout=10.0)

            services = services_response.get("values", {}).get("services", [])

            # ROS 2 should have parameter services
            param_services = [s for s in services if "param" in s.lower()]
            assert len(param_services) > 0, "ROS 2 should have parameter services"

    def test_full_system_check(
        self, ws_manager, ros_version, rosapi_nodes_type, rosapi_topics_type, rosapi_services_type
    ):
        """Comprehensive system check: nodes, topics, services."""
        results = {}
        results["version"] = ros_version

        # Check nodes
        nodes_msg = {
            "op": "call_service",
            "service": "/rosapi/nodes",
            "type": rosapi_nodes_type,
            "args": {},
            "id": "system_check_nodes",
        }

        with ws_manager:
            nodes_response = ws_manager.request(nodes_msg, timeout=10.0)

        results["node_count"] = len(nodes_response.get("values", {}).get("nodes", []))

        # Check topics
        topics_msg = {
            "op": "call_service",
            "service": "/rosapi/topics",
            "type": rosapi_topics_type,
            "args": {},
            "id": "system_check_topics",
        }

        with ws_manager:
            topics_response = ws_manager.request(topics_msg, timeout=10.0)

        results["topic_count"] = len(topics_response.get("values", {}).get("topics", []))

        # Check services
        services_msg = {
            "op": "call_service",
            "service": "/rosapi/services",
            "type": rosapi_services_type,
            "args": {},
            "id": "system_check_services",
        }

        with ws_manager:
            services_response = ws_manager.request(services_msg, timeout=10.0)

        results["service_count"] = len(services_response.get("values", {}).get("services", []))

        # Verify we got valid data
        assert str(results["version"]) == ros_version, f"Should be ROS {ros_version}"
        assert results["node_count"] > 0, "Should have nodes running"
        assert results["topic_count"] > 0, "Should have topics available"
        assert results["service_count"] > 0, "Should have services available"
