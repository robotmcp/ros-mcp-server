"""Resources for ROS metadata and discovery information."""

import json

from ros_mcp.utils.websocket import WebSocketManager


def register_ros_metadata_resources(mcp, ws_manager: WebSocketManager):
    """Register ROS metadata resources with the MCP server."""

    @mcp.resource("ros-mcp://ros-metadata/all")
    def get_all_ros_metadata() -> str:
        """
        Get all ROS metadata including topics, services, nodes, and parameters.

        Returns:
            str: JSON string with comprehensive ROS system information
        """
        try:
            metadata = {
                "topics": [],
                "services": [],
                "nodes": [],
                "parameters": [],
                "ros_version": None,
                "errors": [],
            }

            # Get ROS version
            try:
                ros2_request = {
                    "op": "call_service",
                    "id": "ros2_version_check",
                    "service": "/rosapi/get_ros_version",
                    "args": {},
                }
                with ws_manager:
                    response = ws_manager.request(ros2_request)
                    values = response.get("values") if response else None
                    if isinstance(values, dict) and "version" in values:
                        metadata["ros_version"] = {
                            "version": values.get("version"),
                            "distro": values.get("distro"),
                        }
                    else:
                        # Try ROS1
                        ros1_request = {
                            "op": "call_service",
                            "id": "ros1_distro_check",
                            "service": "/rosapi/get_param",
                            "args": {"name": "/rosdistro"},
                        }
                        response = ws_manager.request(ros1_request)
                        value = response.get("values") if response else None
                        if value:
                            distro = value.get("value") if isinstance(value, dict) else value
                            distro_clean = (
                                str(distro).strip('"').replace("\\n", "").replace("\n", "")
                            )
                            metadata["ros_version"] = {"version": "1", "distro": distro_clean}
            except Exception as e:
                metadata["errors"].append(f"Failed to get ROS version: {str(e)}")

            # Get topics
            try:
                topics_message = {
                    "op": "call_service",
                    "service": "/rosapi/topics",
                    "type": "rosapi/Topics",
                    "args": {},
                    "id": "get_topics_request",
                }
                with ws_manager:
                    response = ws_manager.request(topics_message)
                    if response and "values" in response:
                        topics = response["values"].get("topics", [])
                        types = response["values"].get("types", [])
                        metadata["topics"] = [
                            {"name": topic, "type": topic_type}
                            for topic, topic_type in zip(topics, types)
                        ]
            except Exception as e:
                metadata["errors"].append(f"Failed to get topics: {str(e)}")

            # Get services
            try:
                services_message = {
                    "op": "call_service",
                    "service": "/rosapi/services",
                    "type": "rosapi/Services",
                    "args": {},
                    "id": "get_services_request",
                }
                with ws_manager:
                    response = ws_manager.request(services_message)
                    if response and "values" in response:
                        services = response["values"].get("services", [])
                        types = response["values"].get("types", [])
                        metadata["services"] = [
                            {"name": service, "type": service_type}
                            for service, service_type in zip(services, types)
                        ]
            except Exception as e:
                metadata["errors"].append(f"Failed to get services: {str(e)}")

            # Get nodes
            try:
                nodes_message = {
                    "op": "call_service",
                    "service": "/rosapi/nodes",
                    "type": "rosapi/Nodes",
                    "args": {},
                    "id": "get_nodes_request",
                }
                with ws_manager:
                    response = ws_manager.request(nodes_message)
                    if response and "values" in response:
                        metadata["nodes"] = response["values"].get("nodes", [])
            except Exception as e:
                metadata["errors"].append(f"Failed to get nodes: {str(e)}")

            # Get parameters (ROS 2 only)
            try:
                params_message = {
                    "op": "call_service",
                    "service": "/rosapi/get_param_names",
                    "type": "rosapi/GetParamNames",
                    "args": {},
                    "id": "get_parameters_request",
                }
                with ws_manager:
                    response = ws_manager.request(params_message)
                    if response and "values" in response:
                        metadata["parameters"] = response["values"].get("names", [])
            except Exception:
                # Parameters might not be available in ROS1 or if service doesn't exist
                pass

            # Add summary counts
            metadata["summary"] = {
                "total_topics": len(metadata["topics"]),
                "total_services": len(metadata["services"]),
                "total_nodes": len(metadata["nodes"]),
                "total_parameters": len(metadata["parameters"]),
                "has_errors": len(metadata["errors"]) > 0,
            }

            return json.dumps(metadata, indent=2)

        except Exception as e:
            return json.dumps(
                {
                    "error": f"Failed to get ROS metadata: {str(e)}",
                    "topics": [],
                    "services": [],
                    "nodes": [],
                    "parameters": [],
                }
            )

    @mcp.resource("ros-mcp://ros-metadata/nodes/all")
    def get_nodes_details() -> str:
        """
        Get comprehensive information about all ROS nodes including their publishers, subscribers, and services.

        Returns:
            str: JSON string with detailed information about all nodes including:
                - Node names and details
                - Publishers for each node
                - Subscribers for each node
                - Services provided by each node
                - Connection counts and statistics
        """
        try:
            # First get all nodes
            nodes_message = {
                "op": "call_service",
                "service": "/rosapi/nodes",
                "type": "rosapi/Nodes",
                "args": {},
                "id": "get_nodes_request",
            }

            with ws_manager:
                nodes_response = ws_manager.request(nodes_message)

                if not nodes_response or "values" not in nodes_response:
                    return json.dumps(
                        {
                            "error": "Failed to get nodes list",
                            "total_nodes": 0,
                            "nodes": {},
                            "node_errors": [],
                        }
                    )

                nodes = nodes_response["values"].get("nodes", [])
                node_details = {}

                # Get details for each node
                node_errors = []
                for node in nodes:
                    # Get node details (publishers, subscribers, services)
                    node_details_message = {
                        "op": "call_service",
                        "service": "/rosapi/node_details",
                        "type": "rosapi/NodeDetails",
                        "args": {"node": node},
                        "id": f"get_node_details_{node.replace('/', '_')}",
                    }

                    node_details_response = ws_manager.request(node_details_message)

                    if node_details_response and "values" in node_details_response:
                        values = node_details_response["values"]
                        # Extract publishers, subscribers, and services from the response
                        # Note: rosapi uses "publishing" and "subscribing" field names
                        publishers = values.get("publishing", [])
                        subscribers = values.get("subscribing", [])
                        services = values.get("services", [])

                        node_details[node] = {
                            "publishers": publishers,
                            "subscribers": subscribers,
                            "services": services,
                            "publisher_count": len(publishers),
                            "subscriber_count": len(subscribers),
                            "service_count": len(services),
                        }
                    elif (
                        node_details_response
                        and "result" in node_details_response
                        and not node_details_response["result"]
                    ):
                        error_msg = node_details_response.get("values", {}).get(
                            "message", "Service call failed"
                        )
                        node_errors.append(f"Node {node}: {error_msg}")
                    else:
                        node_errors.append(f"Node {node}: Failed to get node details")

                result = {
                    "total_nodes": len(nodes),
                    "nodes": node_details,
                    "node_errors": node_errors,  # Include any errors encountered during inspection
                }

            return json.dumps(result, indent=2)
        except Exception as e:
            return json.dumps(
                {
                    "error": f"Failed to inspect all nodes: {str(e)}",
                    "total_nodes": 0,
                    "nodes": {},
                    "node_errors": [],
                }
            )
