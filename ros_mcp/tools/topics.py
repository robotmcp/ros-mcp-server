"""Topic tools for ROS MCP."""

import json
import time
from typing import Any, Dict, List

from fastmcp import FastMCP

from ros_mcp.tools.utils import convert_expects_image_hint
from ros_mcp.utils.websocket_manager import WebSocketManager, parse_input


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


def get_topic_type_impl(ws_manager: WebSocketManager, topic: str) -> dict:
    """
    Get the message type for a specific topic.

    Args:
        ws_manager: WebSocketManager instance to use for ROS connections
        topic (str): The topic name (e.g., '/cmd_vel')

    Returns:
        dict: Contains the 'type' field with the message type,
            or an error message if topic doesn't exist.
    """
    # Validate input
    if not topic or not topic.strip():
        return {"error": "Topic name cannot be empty"}

    # rosbridge service call to get topic type
    message = {
        "op": "call_service",
        "service": "/rosapi/topic_type",
        "type": "rosapi/TopicType",
        "args": {"topic": topic},
        "id": f"get_topic_type_request_{topic.replace('/', '_')}",
    }

    # Request topic type from rosbridge
    with ws_manager:
        response = ws_manager.request(message)

    # Check for service response errors first
    if response and "result" in response and not response["result"]:
        # Service call failed - return error with details from values
        error_msg = response.get("values", {}).get("message", "Service call failed")
        return {"error": f"Service call failed: {error_msg}"}

    # Return topic type if present
    if response and "values" in response:
        topic_type = response["values"].get("type", "")
        if topic_type:
            return {"topic": topic, "type": topic_type}
        else:
            return {"error": f"Topic {topic} does not exist or has no type"}
    else:
        return {"error": f"Failed to get type for topic {topic}"}


def get_message_details_impl(ws_manager: WebSocketManager, message_type: str) -> dict:
    """
    Get the complete structure/definition of a message type.

    Args:
        ws_manager: WebSocketManager instance to use for ROS connections
        message_type (str): The message type (e.g., 'geometry_msgs/Twist')

    Returns:
        dict: Contains the message structure with field names and types,
            or an error message if the message type doesn't exist.
    """
    # Validate input
    if not message_type or not message_type.strip():
        return {"error": "Message type cannot be empty"}

    # rosbridge service call to get message details
    message = {
        "op": "call_service",
        "service": "/rosapi/message_details",
        "type": "rosapi/MessageDetails",
        "args": {"type": message_type},
        "id": f"get_message_details_request_{message_type.replace('/', '_')}",
    }

    # Request message details from rosbridge
    with ws_manager:
        response = ws_manager.request(message)

    # Check for service response errors first
    if response and "result" in response and not response["result"]:
        # Service call failed - return error with details from values
        error_msg = response.get("values", {}).get("message", "Service call failed")
        return {"error": f"Service call failed: {error_msg}"}

    # Return message structure if present
    if response and "values" in response:
        typedefs = response["values"].get("typedefs", [])
        if typedefs:
            # Parse the structure into a more readable format
            structure = {}
            for typedef in typedefs:
                type_name = typedef.get("type", message_type)
                field_names = typedef.get("fieldnames", [])
                field_types = typedef.get("fieldtypes", [])

                fields = {}
                for name, ftype in zip(field_names, field_types):
                    fields[name] = ftype

                structure[type_name] = {"fields": fields, "field_count": len(fields)}

            return {"message_type": message_type, "structure": structure}
        else:
            return {"error": f"Message type {message_type} not found or has no definition"}
    else:
        return {"error": f"Failed to get details for message type {message_type}"}


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
            elif (
                publishers_response
                and "result" in publishers_response
                and not publishers_response["result"]
            ):
                error_msg = publishers_response.get("values", {}).get(
                    "message", "Service call failed"
                )
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
            elif (
                subscribers_response
                and "result" in subscribers_response
                and not subscribers_response["result"]
            ):
                error_msg = subscribers_response.get("values", {}).get(
                    "message", "Service call failed"
                )
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


def subscribe_once_impl(
    ws_manager: WebSocketManager,
    topic: str,
    msg_type: str,
    expects_image: str = "auto",
    timeout: float | None = None,
    queue_length: int | None = None,
    throttle_rate_ms: int | None = None,
) -> dict:
    """
    Subscribe to a given ROS topic via rosbridge and return the first message received.

    Args:
        ws_manager: WebSocketManager instance to use for ROS connections
        topic (str): The ROS topic name (e.g., "/cmd_vel", "/joint_states").
        msg_type (str): The ROS message type (e.g., "geometry_msgs/Twist").
        timeout (float | None): Timeout in seconds. If None, uses the default timeout.
        queue_length (int | None): How many messages to buffer before dropping old ones. Must be ≥ 1.
        throttle_rate_ms (int | None): Minimum interval between messages in milliseconds. Must be ≥ 0.
        expects_image (str): Hint about whether to expect image data.
            - "true": prioritize image parsing (use for sensor_msgs/Image topics)
            - "false": skip image detection for faster processing (use for non-image topics)
            - "auto": auto-detect based on message fields (default)

    Returns:
        dict:
            - {"msg": <parsed ROS message>} if successful
            - {"error": "<error message>"} if subscription or timeout fails
    """
    # Validate critical args before attempting subscription
    if not topic or not msg_type:
        return {"error": "Missing required arguments: topic and msg_type must be provided."}

    # Validate optional parameters
    if queue_length is not None and (not isinstance(queue_length, int) or queue_length < 1):
        return {"error": "queue_length must be an integer ≥ 1"}

    if throttle_rate_ms is not None and (
        not isinstance(throttle_rate_ms, int) or throttle_rate_ms < 0
    ):
        return {"error": "throttle_rate_ms must be an integer ≥ 0"}

    # Construct the rosbridge subscribe message
    subscribe_msg: dict = {
        "op": "subscribe",
        "topic": topic,
        "type": msg_type,
    }

    # Add optional parameters if provided
    if queue_length is not None:
        subscribe_msg["queue_length"] = queue_length

    if throttle_rate_ms is not None:
        subscribe_msg["throttle_rate"] = throttle_rate_ms

    # Subscribe and wait for the first message
    with ws_manager:
        # Send subscription request
        send_error = ws_manager.send(subscribe_msg)
        if send_error:
            return {"error": f"Failed to subscribe: {send_error}"}

        # Use default timeout if none specified
        actual_timeout = timeout if timeout is not None else ws_manager.default_timeout

        # Loop until we receive the first message or timeout
        end_time = time.time() + actual_timeout
        while time.time() < end_time:
            response = ws_manager.receive(timeout=0.5)  # non-blocking small timeout
            if response is None:
                continue  # idle timeout: no frame this tick

            # Convert string hint to boolean for parse_input
            expects_image_bool = convert_expects_image_hint(expects_image)

            # Parse input with expects_image hint
            msg_data, was_parsed_as_image = parse_input(response, expects_image_bool)

            if not msg_data:
                continue  # parsing failed or empty

            # Check for status errors from rosbridge
            if msg_data.get("op") == "status" and msg_data.get("level") == "error":
                return {"error": f"Rosbridge error: {msg_data.get('msg', 'Unknown error')}"}

            # Check for the first published message
            if msg_data.get("op") == "publish" and msg_data.get("topic") == topic:
                # Unsubscribe before returning the message
                unsubscribe_msg = {"op": "unsubscribe", "topic": topic}
                ws_manager.send(unsubscribe_msg)
                # Return appropriate message based on whether image was actually parsed
                if was_parsed_as_image:
                    # Exclude the 'data' field from image messages as it's too large
                    msg_content = msg_data.get("msg", {})
                    filtered_msg = {k: v for k, v in msg_content.items() if k != "data"}
                    return {
                        "msg": filtered_msg,
                        "message": "Image received successfully and saved in the MCP server. Run the 'analyze_previously_received_image' tool to analyze it",
                    }
                else:
                    return {"msg": msg_data.get("msg", {})}

        # Timeout - unsubscribe and return error
        unsubscribe_msg = {"op": "unsubscribe", "topic": topic}
        ws_manager.send(unsubscribe_msg)
        return {"error": "Timeout waiting for message from topic"}


def publish_once_impl(
    ws_manager: WebSocketManager,
    topic: str,
    msg_type: str,
    msg: dict,
) -> dict:
    """
    Publish a single message to a ROS topic via rosbridge.

    Args:
        ws_manager: WebSocketManager instance to use for ROS connections
        topic (str): ROS topic name (e.g., "/cmd_vel")
        msg_type (str): ROS message type (e.g., "geometry_msgs/Twist")
        msg (dict): Message payload as a dictionary

    Returns:
        dict:
            - {"success": True} if sent without errors
            - {"error": "<error message>"} if connection/send failed
    """
    # Validate critical args before attempting publish
    if not topic or not msg_type or not msg:
        return {
            "error": "Missing required arguments: topic, msg_type, and msg must all be provided."
        }

    # Use proper advertise → publish → unadvertise pattern
    with ws_manager:
        # 1. Advertise the topic
        advertise_msg = {"op": "advertise", "topic": topic, "type": msg_type}
        send_error = ws_manager.send(advertise_msg)
        if send_error:
            return {"error": f"Failed to advertise topic: {send_error}"}

        # Check for advertise response/errors
        response = ws_manager.receive(timeout=1.0)
        if response:
            try:
                msg_data = json.loads(response)
                if msg_data.get("op") == "status" and msg_data.get("level") == "error":
                    return {"error": f"Advertise failed: {msg_data.get('msg', 'Unknown error')}"}
            except json.JSONDecodeError:
                pass  # Non-JSON response is usually fine for advertise

        # 2. Publish the message
        publish_msg = {"op": "publish", "topic": topic, "msg": msg}
        send_error = ws_manager.send(publish_msg)
        if send_error:
            # Try to unadvertise even if publish failed
            ws_manager.send({"op": "unadvertise", "topic": topic})
            return {"error": f"Failed to publish message: {send_error}"}

        # Check for publish response/errors
        response = ws_manager.receive(timeout=1.0)
        if response:
            try:
                msg_data = json.loads(response)
                if msg_data.get("op") == "status" and msg_data.get("level") == "error":
                    # Unadvertise before returning error
                    ws_manager.send({"op": "unadvertise", "topic": topic})
                    return {"error": f"Publish failed: {msg_data.get('msg', 'Unknown error')}"}
            except json.JSONDecodeError:
                pass  # Non-JSON response is usually fine for publish

        # 3. Unadvertise the topic
        unadvertise_msg = {"op": "unadvertise", "topic": topic}
        ws_manager.send(unadvertise_msg)

    return {
        "success": True,
        "note": "Message published using advertise → publish → unadvertise pattern",
    }


def subscribe_for_duration_impl(
    ws_manager: WebSocketManager,
    topic: str,
    msg_type: str,
    duration: float = 5.0,
    max_messages: int = 100,
    queue_length: int | None = None,
    throttle_rate_ms: int | None = None,
    expects_image: str = "auto",
) -> dict:
    """
    Subscribe to a ROS topic via rosbridge for a fixed duration and collect messages.

    Args:
        ws_manager: WebSocketManager instance to use for ROS connections
        topic (str): ROS topic name (e.g. "/cmd_vel", "/joint_states")
        msg_type (str): ROS message type (e.g. "geometry_msgs/Twist")
        duration (float): How long (seconds) to listen for messages
        max_messages (int): Maximum number of messages to collect before stopping
        queue_length (int | None): How many messages to buffer before dropping old ones. Must be ≥ 1.
        throttle_rate_ms (int | None): Minimum interval between messages in milliseconds. Must be ≥ 0.
        expects_image (str): Hint about whether to expect image data.
            - "true": prioritize image parsing (use for sensor_msgs/Image topics)
            - "false": skip image detection for faster processing (use for non-image topics)
            - "auto": auto-detect based on message fields (default)

    Returns:
        dict:
            {
                "topic": topic_name,
                "collected_count": N,
                "messages": [msg1, msg2, ...]
            }
    """
    # Validate critical args before subscribing
    if not topic or not msg_type:
        return {"error": "Missing required arguments: topic and msg_type must be provided."}

    # Validate optional parameters
    if queue_length is not None and (not isinstance(queue_length, int) or queue_length < 1):
        return {"error": "queue_length must be an integer ≥ 1"}

    if throttle_rate_ms is not None and (
        not isinstance(throttle_rate_ms, int) or throttle_rate_ms < 0
    ):
        return {"error": "throttle_rate_ms must be an integer ≥ 0"}

    # Send subscription request
    subscribe_msg: dict = {
        "op": "subscribe",
        "topic": topic,
        "type": msg_type,
    }

    # Add optional parameters if provided
    if queue_length is not None:
        subscribe_msg["queue_length"] = queue_length

    if throttle_rate_ms is not None:
        subscribe_msg["throttle_rate"] = throttle_rate_ms

    with ws_manager:
        send_error = ws_manager.send(subscribe_msg)
        if send_error:
            return {"error": f"Failed to subscribe: {send_error}"}

        collected_messages = []
        status_errors = []
        end_time = time.time() + duration

        # Loop until duration expires or we hit max_messages
        while time.time() < end_time and len(collected_messages) < max_messages:
            response = ws_manager.receive(timeout=0.5)  # non-blocking small timeout
            if response is None:
                continue  # idle timeout: no frame this tick

            # Convert string hint to boolean for parse_input
            expects_image_bool = convert_expects_image_hint(expects_image)

            # Parse input with expects_image hint
            msg_data, was_parsed_as_image = parse_input(response, expects_image_bool)

            if not msg_data:
                continue  # parsing failed or empty

            # Check for status errors from rosbridge
            if msg_data.get("op") == "status" and msg_data.get("level") == "error":
                status_errors.append(msg_data.get("msg", "Unknown error"))
                continue

            # Check for published messages matching our topic
            if msg_data.get("op") == "publish" and msg_data.get("topic") == topic:
                # Add message based on whether it was actually parsed as image
                if was_parsed_as_image:
                    # Exclude the 'data' field from image messages as it's too large
                    msg_content = msg_data.get("msg", {})
                    filtered_msg = {k: v for k, v in msg_content.items() if k != "data"}
                    collected_messages.append(
                        {
                            "image_message": "Image received and saved. Use 'analyze_previously_received_image' to analyze it.",
                            "msg": filtered_msg,
                        }
                    )
                else:
                    collected_messages.append(msg_data.get("msg", {}))

        # Unsubscribe when done
        unsubscribe_msg = {"op": "unsubscribe", "topic": topic}
        ws_manager.send(unsubscribe_msg)

    return {
        "topic": topic,
        "collected_count": len(collected_messages),
        "messages": collected_messages,
        "status_errors": status_errors,  # Include any errors encountered during collection
    }


def publish_for_durations_impl(
    ws_manager: WebSocketManager,
    topic: str,
    msg_type: str,
    messages: List[Dict[str, Any]],
    durations: List[float],
) -> dict:
    """
    Publish a sequence of messages to a given ROS topic with delays in between.

    Args:
        ws_manager: WebSocketManager instance to use for ROS connections
        topic (str): ROS topic name (e.g., "/cmd_vel")
        msg_type (str): ROS message type (e.g., "geometry_msgs/Twist")
        messages (List[Dict[str, Any]]): A list of message dictionaries (ROS-compatible payloads)
        durations (List[float]): A list of durations (seconds) to wait between messages

    Returns:
        dict:
            {
                "success": True,
                "published_count": <number of messages>,
                "topic": topic,
                "msg_type": msg_type
            }
            OR {"error": "<error message>"} if something failed
    """
    # Validate critical args before publishing
    if not topic or not msg_type or not messages or not durations:
        return {
            "error": "Missing required arguments: topic, msg_type, messages, and durations must all be provided."
        }

    # Ensure same length for messages and durations
    if len(messages) != len(durations):
        return {"error": "messages and durations must have the same length"}

    # Use proper advertise → publish → unadvertise pattern
    with ws_manager:
        # 1. Advertise the topic
        advertise_msg = {"op": "advertise", "topic": topic, "type": msg_type}
        send_error = ws_manager.send(advertise_msg)
        if send_error:
            return {"error": f"Failed to advertise topic: {send_error}"}

        # Check for advertise response/errors
        response = ws_manager.receive(timeout=1.0)
        if response:
            try:
                msg_data = json.loads(response)
                if msg_data.get("op") == "status" and msg_data.get("level") == "error":
                    return {"error": f"Advertise failed: {msg_data.get('msg', 'Unknown error')}"}
            except json.JSONDecodeError:
                pass  # Non-JSON response is usually fine for advertise

        published_count = 0
        errors = []

        # 2. Iterate and publish each message with a delay
        for i, (msg, delay) in enumerate(zip(messages, durations)):
            # Build the rosbridge publish message
            publish_msg = {"op": "publish", "topic": topic, "msg": msg}

            # Send it
            send_error = ws_manager.send(publish_msg)
            if send_error:
                errors.append(f"Message {i + 1}: {send_error}")
                continue  # Continue with next message instead of failing completely

            # Check for publish response/errors
            response = ws_manager.receive(timeout=1.0)
            if response:
                try:
                    msg_data = json.loads(response)
                    if msg_data.get("op") == "status" and msg_data.get("level") == "error":
                        errors.append(f"Message {i + 1}: {msg_data.get('msg', 'Unknown error')}")
                        continue
                except json.JSONDecodeError:
                    pass  # Non-JSON response is usually fine for publish

            published_count += 1

            # Wait before sending the next message
            time.sleep(delay)

        # 3. Unadvertise the topic
        unadvertise_msg = {"op": "unadvertise", "topic": topic}
        ws_manager.send(unadvertise_msg)

    return {
        "success": True,
        "published_count": published_count,
        "total_messages": len(messages),
        "topic": topic,
        "msg_type": msg_type,
        "errors": errors,  # Include any errors encountered during publishing
    }


def register_topic_tools(
    mcp: FastMCP,
    ws_manager: WebSocketManager,
) -> None:
    """Register all topic-related tools."""

    @mcp.tool(description=("Get list of all available ROS topics.\nExample:\nget_topics()"))
    def get_topics() -> dict:
        """Get list of all available ROS topics."""
        return get_topics_impl(ws_manager)

    @mcp.tool(
        description=(
            "Get the message type for a specific topic.\nExample:\nget_topic_type('/cmd_vel')"
        )
    )
    def get_topic_type(topic: str) -> dict:
        """Get the message type for a specific topic."""
        return get_topic_type_impl(ws_manager, topic)

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
            "Get the complete structure/definition of a message type.\n"
            "Example:\n"
            "get_message_details('geometry_msgs/Twist')"
        )
    )
    def get_message_details(message_type: str) -> dict:
        """Get the complete structure/definition of a message type."""
        return get_message_details_impl(ws_manager, message_type)

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

    @mcp.tool(
        description=(
            "Subscribe to a ROS topic and return the first message received.\n"
            "Example:\n"
            "subscribe_once(topic='/cmd_vel', msg_type='geometry_msgs/msg/TwistStamped')\n"
            "subscribe_once(topic='/slow_topic', msg_type='my_package/SlowMsg', timeout=None)  # Specify timeout only if topic publishes infrequently\n"
            "subscribe_once(topic='/high_rate_topic', msg_type='sensor_msgs/Image', timeout=None, queue_length=5, throttle_rate_ms=100)  # Control message buffering and rate\n"
            "subscribe_once(topic='/camera/image_raw', msg_type='sensor_msgs/Image', expects_image='true')  # Hint that this is an image for faster processing\n"
            "subscribe_once(topic='/point_cloud', msg_type='sensor_msgs/PointCloud2', expects_image='false')  # Skip image detection for non-image data"
        )
    )
    def subscribe_once(
        topic: str = "",
        msg_type: str = "",
        expects_image: str = "auto",
        timeout: float | None = None,
        queue_length: int | None = None,
        throttle_rate_ms: int | None = None,
    ) -> dict:
        """Subscribe to a ROS topic and return the first message received."""
        if timeout is None:
            timeout = ws_manager.default_timeout
        return subscribe_once_impl(
            ws_manager, topic, msg_type, expects_image, timeout, queue_length, throttle_rate_ms
        )

    @mcp.tool(
        description=(
            "Publish a single message to a ROS topic.\n"
            "Example:\n"
            "publish_once(topic='/cmd_vel', msg_type='geometry_msgs/msg/TwistStamped', msg={'linear': {'x': 1.0}})"
        )
    )
    def publish_once(topic: str = "", msg_type: str = "", msg: dict = None) -> dict:
        """Publish a single message to a ROS topic via rosbridge."""
        if msg is None:
            msg = {}
        return publish_once_impl(ws_manager, topic, msg_type, msg)

    @mcp.tool(
        description=(
            "Subscribe to a topic for a duration and collect messages.\n"
            "Example:\n"
            "subscribe_for_duration(topic='/cmd_vel', msg_type='geometry_msgs/msg/TwistStamped', duration=5, max_messages=10)\n"
            "subscribe_for_duration(topic='/high_rate_topic', msg_type='sensor_msgs/Image', duration=10, queue_length=5, throttle_rate_ms=100)  # Control message buffering and rate\n"
            "subscribe_for_duration(topic='/camera/image_raw', msg_type='sensor_msgs/Image', duration=5, expects_image='true')  # Hint that this is an image for faster processing\n"
            "subscribe_for_duration(topic='/point_cloud', msg_type='sensor_msgs/PointCloud2', duration=5, expects_image='false')  # Skip image detection for non-image data"
        )
    )
    def subscribe_for_duration(
        topic: str = "",
        msg_type: str = "",
        duration: float = 5.0,
        max_messages: int = 100,
        queue_length: int | None = None,
        throttle_rate_ms: int | None = None,
        expects_image: str = "auto",
    ) -> dict:
        """Subscribe to a ROS topic via rosbridge for a fixed duration and collect messages."""
        return subscribe_for_duration_impl(
            ws_manager,
            topic,
            msg_type,
            duration,
            max_messages,
            queue_length,
            throttle_rate_ms,
            expects_image,
        )

    @mcp.tool(
        description=(
            "Publish a sequence of messages with delays.\n"
            "Example:\n"
            "publish_for_durations(topic='/cmd_vel', msg_type='geometry_msgs/msg/TwistStamped', messages=[{'linear': {'x': 1.0}}, {'linear': {'x': 0.0}}], durations=[1, 2])"
        )
    )
    def publish_for_durations(
        topic: str = "",
        msg_type: str = "",
        messages: List[Dict[str, Any]] = None,
        durations: List[float] = None,
    ) -> dict:
        """Publish a sequence of messages to a given ROS topic with delays in between."""
        if messages is None:
            messages = []
        if durations is None:
            durations = []
        return publish_for_durations_impl(ws_manager, topic, msg_type, messages, durations)
