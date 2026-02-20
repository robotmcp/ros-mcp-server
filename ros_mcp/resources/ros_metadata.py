"""Resources for ROS1 metadata and discovery information."""

import json
from typing import Any

from ros_mcp.utils.websocket import WebSocketManager


def _call_service(
    ws_manager: WebSocketManager,
    service: str,
    service_type: str,
    args: dict[str, Any],
    request_id: str,
) -> dict[str, Any]:
    """Convenience helper for rosbridge service calls."""
    request = {
        "op": "call_service",
        "service": service,
        "type": service_type,
        "args": args,
        "id": request_id,
    }
    with ws_manager:
        response = ws_manager.request(request)
    return response if isinstance(response, dict) else {}


def register_ros_metadata_resources(mcp, ws_manager: WebSocketManager):
    """Register ROS metadata resources with the MCP server."""

    @mcp.resource("ros-mcp://ros-metadata/all")
    def get_all_ros_metadata() -> str:
        """Get all ROS1 metadata including topics, services, nodes, and parameters."""
        metadata: dict[str, Any] = {
            "topics": [],
            "services": [],
            "nodes": [],
            "parameters": [],
            "ros_version": None,
            "errors": [],
        }

        try:
            # ROS1 distro
            distro_resp = _call_service(
                ws_manager,
                "/rosapi/get_param",
                "rosapi/GetParam",
                {"name": "/rosdistro"},
                "ros1_distro_check",
            )
            distro = distro_resp.get("values", {}).get("value")
            if distro is not None:
                distro_clean = str(distro).strip('"').replace("\\n", "").replace("\n", "")
                metadata["ros_version"] = {"version": "1", "distro": distro_clean}
            else:
                metadata["errors"].append("Failed to detect ROS distro via /rosdistro")

            # Topics
            topics_resp = _call_service(
                ws_manager,
                "/rosapi/topics",
                "rosapi/Topics",
                {},
                "get_topics_request",
            )
            topics = topics_resp.get("values", {}).get("topics", [])
            topic_types = topics_resp.get("values", {}).get("types", [])
            metadata["topics"] = [
                {"name": topic, "type": topic_type}
                for topic, topic_type in zip(topics, topic_types)
            ]

            # Services
            services_resp = _call_service(
                ws_manager,
                "/rosapi/services",
                "rosapi/Services",
                {},
                "get_services_request",
            )
            services = services_resp.get("values", {}).get("services", [])
            service_types = services_resp.get("values", {}).get("types", [])
            metadata["services"] = [
                {"name": service, "type": service_type}
                for service, service_type in zip(services, service_types)
            ]

            # Nodes
            nodes_resp = _call_service(
                ws_manager,
                "/rosapi/nodes",
                "rosapi/Nodes",
                {},
                "get_nodes_request",
            )
            metadata["nodes"] = nodes_resp.get("values", {}).get("nodes", [])

            # Parameters
            params_resp = _call_service(
                ws_manager,
                "/rosapi/get_param_names",
                "rosapi/GetParamNames",
                {},
                "get_parameters_request",
            )
            metadata["parameters"] = params_resp.get("values", {}).get("names", [])

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
                },
                indent=2,
            )

    @mcp.resource("ros-mcp://ros-metadata/nodes/all")
    def get_nodes_details() -> str:
        """Get details about all ROS nodes (pub/sub/services)."""
        try:
            nodes_resp = _call_service(
                ws_manager,
                "/rosapi/nodes",
                "rosapi/Nodes",
                {},
                "nodes_all",
            )
            nodes = nodes_resp.get("values", {}).get("nodes", [])

            node_details: dict[str, Any] = {}
            node_errors: list[str] = []

            with ws_manager:
                for node in nodes:
                    details_req = {
                        "op": "call_service",
                        "service": "/rosapi/node_details",
                        "type": "rosapi/NodeDetails",
                        "args": {"node": node},
                        "id": f"node_details_{node.replace('/', '_')}",
                    }
                    response = ws_manager.request(details_req)
                    if isinstance(response, dict) and "values" in response:
                        values = response.get("values", {})
                        publishing = values.get("publishing", [])
                        subscribing = values.get("subscribing", [])
                        services = values.get("services", [])
                        node_details[node] = {
                            "publishers": publishing,
                            "subscribers": subscribing,
                            "services": services,
                            "publisher_count": len(publishing),
                            "subscriber_count": len(subscribing),
                            "service_count": len(services),
                        }
                    else:
                        node_errors.append(f"Failed to inspect node: {node}")

            return json.dumps(
                {
                    "total_nodes": len(nodes),
                    "nodes": node_details,
                    "node_errors": node_errors,
                },
                indent=2,
            )
        except Exception as e:
            return json.dumps(
                {
                    "error": f"Failed to inspect all nodes: {str(e)}",
                    "total_nodes": 0,
                    "nodes": {},
                    "node_errors": [],
                },
                indent=2,
            )

    @mcp.resource("ros-mcp://ros-metadata/services/all")
    def get_services_details() -> str:
        """Get details about all ROS services (type/provider node)."""
        try:
            services_resp = _call_service(
                ws_manager,
                "/rosapi/services",
                "rosapi/Services",
                {},
                "services_all",
            )
            services = services_resp.get("values", {}).get("services", [])

            service_details: dict[str, Any] = {}
            service_errors: list[str] = []

            with ws_manager:
                for service in services:
                    type_req = {
                        "op": "call_service",
                        "service": "/rosapi/service_type",
                        "type": "rosapi/ServiceType",
                        "args": {"service": service},
                        "id": f"service_type_{service.replace('/', '_')}",
                    }
                    type_resp = ws_manager.request(type_req)
                    service_type = "unknown"
                    if isinstance(type_resp, dict):
                        service_type = type_resp.get("values", {}).get("type", "unknown")

                    provider_req = {
                        "op": "call_service",
                        "service": "/rosapi/service_node",
                        "type": "rosapi/ServiceNode",
                        "args": {"service": service},
                        "id": f"service_provider_{service.replace('/', '_')}",
                    }
                    provider_resp = ws_manager.request(provider_req)
                    providers: list[str] = []
                    if isinstance(provider_resp, dict):
                        node = provider_resp.get("values", {}).get("node", "")
                        if node:
                            providers = [node]
                        elif provider_resp.get("error"):
                            service_errors.append(f"Service {service}: {provider_resp['error']}")

                    service_details[service] = {
                        "type": service_type,
                        "providers": providers,
                        "provider_count": len(providers),
                    }

            return json.dumps(
                {
                    "total_services": len(services),
                    "services": service_details,
                    "service_errors": service_errors,
                },
                indent=2,
            )
        except Exception as e:
            return json.dumps(
                {
                    "error": f"Failed to inspect all services: {str(e)}",
                    "total_services": 0,
                    "services": {},
                    "service_errors": [],
                },
                indent=2,
            )

    @mcp.resource("ros-mcp://ros-metadata/topics/all")
    def get_topics_details() -> str:
        """Get details about all ROS topics (type/pubs/subs)."""
        try:
            topics_resp = _call_service(
                ws_manager,
                "/rosapi/topics",
                "rosapi/Topics",
                {},
                "topics_all",
            )
            topics = topics_resp.get("values", {}).get("topics", [])
            types = topics_resp.get("values", {}).get("types", [])

            topic_details: dict[str, Any] = {}
            topic_errors: list[str] = []

            with ws_manager:
                for idx, topic in enumerate(topics):
                    topic_type = types[idx] if idx < len(types) else "unknown"

                    pubs_req = {
                        "op": "call_service",
                        "service": "/rosapi/publishers",
                        "type": "rosapi/Publishers",
                        "args": {"topic": topic},
                        "id": f"topic_publishers_{topic.replace('/', '_')}",
                    }
                    pubs_resp = ws_manager.request(pubs_req)
                    publishers = []
                    if isinstance(pubs_resp, dict):
                        publishers = pubs_resp.get("values", {}).get("publishers", [])

                    subs_req = {
                        "op": "call_service",
                        "service": "/rosapi/subscribers",
                        "type": "rosapi/Subscribers",
                        "args": {"topic": topic},
                        "id": f"topic_subscribers_{topic.replace('/', '_')}",
                    }
                    subs_resp = ws_manager.request(subs_req)
                    subscribers = []
                    if isinstance(subs_resp, dict):
                        subscribers = subs_resp.get("values", {}).get("subscribers", [])

                    if not isinstance(pubs_resp, dict) or not isinstance(subs_resp, dict):
                        topic_errors.append(f"Failed to inspect topic edges for {topic}")

                    topic_details[topic] = {
                        "type": topic_type,
                        "publishers": publishers,
                        "subscribers": subscribers,
                        "publisher_count": len(publishers),
                        "subscriber_count": len(subscribers),
                    }

            return json.dumps(
                {
                    "total_topics": len(topics),
                    "topics": topic_details,
                    "topic_errors": topic_errors,
                },
                indent=2,
            )
        except Exception as e:
            return json.dumps(
                {
                    "error": f"Failed to inspect all topics: {str(e)}",
                    "total_topics": 0,
                    "topics": {},
                    "topic_errors": [],
                },
                indent=2,
            )

    @mcp.resource("ros-mcp://ros-metadata/parameters/all")
    def get_parameters_details() -> str:
        """Get all parameter names from ROS1 parameter server."""
        try:
            params_resp = _call_service(
                ws_manager,
                "/rosapi/get_param_names",
                "rosapi/GetParamNames",
                {},
                "params_all",
            )
            names = params_resp.get("values", {}).get("names", [])
            return json.dumps(
                {
                    "total_parameters": len(names),
                    "parameters": names,
                },
                indent=2,
            )
        except Exception as e:
            return json.dumps(
                {
                    "error": f"Failed to inspect all parameters: {str(e)}",
                    "total_parameters": 0,
                    "parameters": [],
                },
                indent=2,
            )
