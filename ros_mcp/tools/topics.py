"""Topic tools for ROS MCP."""

from fastmcp import FastMCP

from ros_mcp.utils.websocket_manager import WebSocketManager


def get_topics_impl(ws_manager: WebSocketManager) -> dict:
    """
    Get list of all available ROS topics.

    Args:
        ws_manager: WebSocketManager instance to use for connections

    Returns:
        dict: Contains two lists - 'topics' and 'types',
            or a message string if no topics are found.
    """
    # rosbridge service call to get topic list
    message = {
        "op": "call_service",
        "service": "/rosapi/topics",
        "type": "rosapi/Topics",
        "args": {},
        "id": "get_topics_request_1",
    }

    # Request topic list from rosbridge
    with ws_manager:
        response = ws_manager.request(message)

    # Check for service response errors first
    if response and "result" in response and not response["result"]:
        # Service call failed - return error with details from values
        error_msg = response.get("values", {}).get("message", "Service call failed")
        return {"error": f"Service call failed: {error_msg}"}

    # Return topic info if present
    if response and "values" in response:
        values = response["values"]
        topics = values.get("topics", [])
        types = values.get("types", [])
        return {"topics": topics, "types": types, "topic_count": len(topics)}
    else:
        return {"warning": "No topics found"}


def get_topic_details_impl(ws_manager: WebSocketManager, topic: str) -> dict:
    """
    Get detailed information about a specific topic including its type, publishers, and subscribers.

    Args:
        ws_manager: WebSocketManager instance to use for connections
        topic (str): The topic name (e.g., '/cmd_vel')

    Returns:
        dict: Contains detailed topic information including type, publishers, and subscribers,
            or an error message if topic doesn't exist.
    """
    # Validate input
    if not topic or not topic.strip():
        return {"error": "Topic name cannot be empty"}

    result = {
        "topic": topic,
        "type": "unknown",
        "publishers": [],
        "subscribers": [],
        "publisher_count": 0,
        "subscriber_count": 0,
    }

    with ws_manager:
        # Get topic type
        type_message = {
            "op": "call_service",
            "service": "/rosapi/topic_type",
            "type": "rosapi/TopicType",
            "args": {"topic": topic},
            "id": f"get_topic_type_{topic.replace('/', '_')}",
        }

        type_response = ws_manager.request(type_message)
        if type_response and "values" in type_response:
            result["type"] = type_response["values"].get("type", "unknown")

        # Get publishers for this topic
        publishers_message = {
            "op": "call_service",
            "service": "/rosapi/publishers",
            "type": "rosapi/Publishers",
            "args": {"topic": topic},
            "id": f"get_publishers_{topic.replace('/', '_')}",
        }

        publishers_response = ws_manager.request(publishers_message)
        if publishers_response and "values" in publishers_response:
            result["publishers"] = publishers_response["values"].get("publishers", [])

        # Get subscribers for this topic
        subscribers_message = {
            "op": "call_service",
            "service": "/rosapi/subscribers",
            "type": "rosapi/Subscribers",
            "args": {"topic": topic},
            "id": f"get_subscribers_{topic.replace('/', '_')}",
        }

        subscribers_response = ws_manager.request(subscribers_message)
        if subscribers_response and "values" in subscribers_response:
            result["subscribers"] = subscribers_response["values"].get("subscribers", [])

    result["publisher_count"] = len(result["publishers"])
    result["subscriber_count"] = len(result["subscribers"])

    # Check if we got any data
    if result["type"] == "unknown" and not result["publishers"] and not result["subscribers"]:
        return {"error": f"Topic {topic} not found or has no details available"}

    return result


def inspect_all_topics_impl(ws_manager: WebSocketManager) -> dict:
    """
    Get comprehensive information about all ROS topics including publishers, subscribers, and message types.

    Args:
        ws_manager: WebSocketManager instance to use for connections

    Returns:
        dict: Contains detailed information about all topics including:
            - Topic names and message types
            - Publishers for each topic
            - Subscribers for each topic
            - Connection counts and statistics
    """
    # First get all topics
    topics_message = {
        "op": "call_service",
        "service": "/rosapi/topics",
        "type": "rosapi/Topics",
        "args": {},
        "id": "inspect_all_topics_request_1",
    }

    with ws_manager:
        topics_response = ws_manager.request(topics_message)

        if not topics_response or "values" not in topics_response:
            return {"error": "Failed to get topics list"}

        topics = topics_response["values"].get("topics", [])
        types = topics_response["values"].get("types", [])
        topic_details = {}

        # Get details for each topic
        topic_errors = []
        for i, topic in enumerate(topics):
            # Get topic type
            topic_type = types[i] if i < len(types) else "unknown"

            # Get publishers for this topic
            publishers_message = {
                "op": "call_service",
                "service": "/rosapi/publishers",
                "type": "rosapi/Publishers",
                "args": {"topic": topic},
                "id": f"get_publishers_{topic.replace('/', '_')}",
            }

            publishers_response = ws_manager.request(publishers_message)
            publishers = []
            if publishers_response and "values" in publishers_response:
                publishers = publishers_response["values"].get("publishers", [])
            elif publishers_response and "result" in publishers_response and not publishers_response["result"]:
                error_msg = publishers_response.get("values", {}).get("message", "Service call failed")
                topic_errors.append(f"Topic {topic} publishers: {error_msg}")

            # Get subscribers for this topic
            subscribers_message = {
                "op": "call_service",
                "service": "/rosapi/subscribers",
                "type": "rosapi/Subscribers",
                "args": {"topic": topic},
                "id": f"get_subscribers_{topic.replace('/', '_')}",
            }

            subscribers_response = ws_manager.request(subscribers_message)
            subscribers = []
            if subscribers_response and "values" in subscribers_response:
                subscribers = subscribers_response["values"].get("subscribers", [])
            elif subscribers_response and "result" in subscribers_response and not subscribers_response["result"]:
                error_msg = subscribers_response.get("values", {}).get("message", "Service call failed")
                topic_errors.append(f"Topic {topic} subscribers: {error_msg}")

            topic_details[topic] = {
                "type": topic_type,
                "publishers": publishers,
                "subscribers": subscribers,
                "publisher_count": len(publishers),
                "subscriber_count": len(subscribers),
            }

        return {
            "total_topics": len(topics),
            "topics": topic_details,
            "topic_errors": topic_errors,  # Include any errors encountered during inspection
        }


def register_topic_tools(
    mcp: FastMCP,
    ws_manager: WebSocketManager,
) -> None:
    """Register all topic-related tools."""

    @mcp.tool(
        description=("Get list of all available ROS topics.\nExample:\nget_topics()")
    )
    def get_topics() -> dict:
        """Get list of all available ROS topics."""
        return get_topics_impl(ws_manager)

    @mcp.tool(
        description=(
            "Get detailed information about a specific topic including its type, publishers, and subscribers.\n"
            "Example:\n"
            "get_topic_details('/cmd_vel')"
        )
    )
    def get_topic_details(topic: str) -> dict:
        """Get detailed information about a specific topic including its type, publishers, and subscribers."""
        return get_topic_details_impl(ws_manager, topic)

    @mcp.tool(
        description=(
            "Get comprehensive information about all ROS topics including publishers, subscribers, and message types. "
            "Note that this may take time to execute when there are a large number of topics since it queries each one by one.\n"
            "Example:\n"
            "inspect_all_topics()"
        )
    )
    def inspect_all_topics() -> dict:
        """Get comprehensive information about all ROS topics including publishers, subscribers, and message types."""
        return inspect_all_topics_impl(ws_manager)

