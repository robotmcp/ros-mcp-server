"""Node tools for ROS MCP."""

from fastmcp import FastMCP
from mcp.types import ToolAnnotations

from ros_mcp.utils.response import _check_response, _safe_get_values
from ros_mcp.utils.rosapi_types import rosapi_service, rosapi_type
from ros_mcp.utils.websocket import WebSocketManager


def register_node_tools(
    mcp: FastMCP,
    ws_manager: WebSocketManager,
) -> None:
    """Register all node-related tools."""

    @mcp.tool(
        description=("Get list of all currently running ROS nodes.\nExample:\nget_nodes()"),
        annotations=ToolAnnotations(
            title="Get Nodes",
            readOnlyHint=True,
        ),
    )
    def get_nodes() -> dict:
        """
        Get list of all currently running ROS nodes.

        Returns:
            dict: Contains list of all active nodes,
                or a message string if no nodes are found.
        """
        # rosbridge service call to get node list
        message = {
            "op": "call_service",
            "service": rosapi_service("nodes"),
            "type": rosapi_type("Nodes"),
            "args": {},
            "id": "get_nodes_request_1",
        }

        # Request node list from rosbridge
        with ws_manager:
            response = ws_manager.request(message)

        error = _check_response(response)
        if error:
            return error

        # Return node info if present
        values = _safe_get_values(response)
        if values is not None:
            nodes = values.get("nodes", [])
            return {"nodes": nodes, "node_count": len(nodes)}
        return {"warning": "No nodes found"}

    @mcp.tool(
        description=(
            "Get detailed information about a specific node including its publishers, subscribers, and services.\n"
            "Example:\n"
            "get_node_details('/turtlesim')"
        ),
        annotations=ToolAnnotations(
            title="Get Node Details",
            readOnlyHint=True,
        ),
    )
    def get_node_details(node: str) -> dict:
        """
        Get detailed information about a specific node including its publishers, subscribers, and services.

        Args:
            node (str): The node name (e.g., '/turtlesim')

        Returns:
            dict: Contains detailed node information including publishers, subscribers, and services,
                or an error message if node doesn't exist.
        """
        # Validate input
        if not node or not node.strip():
            return {"error": "Node name cannot be empty"}

        result = {
            "node": node,
            "publishers": [],
            "subscribers": [],
            "services": [],
            "publisher_count": 0,
            "subscriber_count": 0,
            "service_count": 0,
        }

        # rosbridge service call to get node details
        message = {
            "op": "call_service",
            "service": rosapi_service("node_details"),
            "type": rosapi_type("NodeDetails"),
            "args": {"node": node},
            "id": f"get_node_details_{node.replace('/', '_')}",
        }

        # Request node details from rosbridge
        with ws_manager:
            response = ws_manager.request(message)

        error = _check_response(response)
        if error:
            return error

        # Extract data from the response
        values = _safe_get_values(response)
        if values is not None:
            # Extract publishers, subscribers, and services from the response
            # Note: rosapi uses "publishing" and "subscribing" field names
            publishers = values.get("publishing", [])
            subscribers = values.get("subscribing", [])
            services = values.get("services", [])

            result["publishers"] = publishers
            result["subscribers"] = subscribers
            result["services"] = services
            result["publisher_count"] = len(publishers)
            result["subscriber_count"] = len(subscribers)
            result["service_count"] = len(services)

        # Check if we got any data
        if not result["publishers"] and not result["subscribers"] and not result["services"]:
            return {"error": f"Node {node} not found or has no details available"}

        return result
