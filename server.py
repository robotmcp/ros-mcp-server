import argparse
import io
import json
import os
import time
from typing import Any, Dict, List, Union

from fastmcp import FastMCP
from fastmcp.utilities.types import Image
from PIL import Image as PILImage

from utils.config_utils import get_robot_specifications, parse_robot_config
from utils.network_utils import ping_ip_and_port
from utils.websocket_manager import WebSocketManager, parse_image, parse_json

# ROS bridge connection settings
ROSBRIDGE_IP = "127.0.0.1"  # Default is localhost. Replace with your local IPor set using the LLM.
ROSBRIDGE_PORT = (
    9090  # Rosbridge default is 9090. Replace with your rosbridge port or set using the LLM.
)

# MCP transport settings
MCP_TRANSPORT = os.getenv("MCP_TRANSPORT", "stdio").lower()  # Default is stdio.

# MCP connection settings (streamable-http)
MCP_HOST = os.getenv(
    "MCP_HOST", "127.0.0.1"
)  # Default is localhost. Replace with the address of your remote MCP server.

# MCP port settings (default=9000)
MCP_PORT = int(
    os.getenv("MCP_PORT", "9000")
)  # Default is 9000. Replace with the port of your remote MCP server.

# Initialize MCP server and WebSocket manager
mcp = FastMCP("ros-mcp-server")
ws_manager = WebSocketManager(
    ROSBRIDGE_IP, ROSBRIDGE_PORT, default_timeout=5.0
)  # Increased default timeout for ROS operations


@mcp.tool(description=("Get robot configuration from YAML file."))
def get_robot_config(name: str) -> dict:
    """
    Get the robot configuration from the YAML file for connecting to the robot and knowing its capabilities.

    Returns:
        dict: The robot configuration.
    """
    robot_config = parse_robot_config(name)

    if len(robot_config) > 1:
        return {
            "error": f"Multiple configurations found for robot '{name}'. Please specify a more precise name."
        }
    elif not robot_config:
        return {
            "error": f"No configuration found for robot '{name}'. Please check the name and try again. Or you can set the IP/port manually using the 'connect_to_robot' tool."
        }
    return {"robot_config": robot_config}


@mcp.tool(
    description=("List all available robot specifications that can be used with get_robot_config.")
)
def list_verified_robot_specifications() -> dict:
    """
    Get a list of all available robot specification files.

    Returns:
        dict: List of available robot names that can be used with get_robot_config.
    """
    return get_robot_specifications()


@mcp.tool(
    description=(
        "After getting the robot config, connect to the robot by setting the IP/port and testing connectivity."
    )
)
def connect_to_robot(
    ip: str = ROSBRIDGE_IP,
    port: Union[int, str] = ROSBRIDGE_PORT,
    ping_timeout: float = 2.0,
    port_timeout: float = 2.0,
) -> dict:
    """
    Connect to a robot by setting the IP and port for the WebSocket connection, then testing connectivity.

    Args:
        ip (str): The IP address of the rosbridge server. Defaults to "127.0.0.1" (localhost).
        port (int): The port number of the rosbridge server. Defaults to 9090.
        ping_timeout (float): Timeout for ping in seconds. Default = 2.0.
        port_timeout (float): Timeout for port check in seconds. Default = 2.0.

    Returns:
        dict: Connection status with ping and port check results.
    """
    # Set default values if None
    actual_ip = str(ip).strip() if ip else ROSBRIDGE_IP
    actual_port = int(port) if port else ROSBRIDGE_PORT

    # Set the IP and port
    ws_manager.set_ip(actual_ip, actual_port)

    # Test connectivity
    ping_result = ping_ip_and_port(actual_ip, actual_port, ping_timeout, port_timeout)

    # Combine the results
    return {
        "message": f"WebSocket IP set to {actual_ip}:{actual_port}",
        "connectivity_test": ping_result,
    }


@mcp.tool(description="Detect the ROS version and distribution via rosbridge.")
def detect_ros_version() -> dict:
    """
    Detects the ROS version and distro via rosbridge WebSocket.
    Returns:
        dict: {'version': <version or '1'>, 'distro': <distro>} or error info.
    """
    # Try ROS2 detection
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
            return {"version": values.get("version"), "distro": values.get("distro")}
        # Fallback to ROS1 detection
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
            distro_clean = str(distro).strip('"').replace("\\n", "").replace("\n", "")
            return {"version": "1", "distro": distro_clean}
        return {"error": "Could not detect ROS version"}


@mcp.tool(description=("Fetch available topics from the ROS bridge.\nExample:\nget_topics()"))
def get_topics() -> dict:
    """
    Fetch available topics from the ROS bridge.

    Returns:
        dict: Contains two lists - 'topics' and 'types',
            or a message string if no topics are found.
    """
    # rosbridge service call to get topic list
    message = {
        "op": "call_service",
        "service": "/rosapi/topics",
        "type": "rosapi/Topics",
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
        return response["values"]
    else:
        return {"warning": "No topics found"}


@mcp.tool(
    description=("Get the message type for a specific topic.\nExample:\nget_topic_type('/cmd_vel')")
)
def get_topic_type(topic: str) -> dict:
    """
    Get the message type for a specific topic.

    Args:
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


@mcp.tool(
    description=(
        "Get the complete structure/definition of a message type.\n"
        "Example:\n"
        "get_message_details('geometry_msgs/Twist')"
    )
)
def get_message_details(message_type: str) -> dict:
    """
    Get the complete structure/definition of a message type.

    Args:
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


@mcp.tool(
    description=(
        "Get list of nodes that are publishing to a specific topic.\n"
        "Example:\n"
        "get_publishers_for_topic('/cmd_vel')"
    )
)
def get_publishers_for_topic(topic: str) -> dict:
    """
    Get list of nodes that are publishing to a specific topic.

    Args:
        topic (str): The topic name (e.g., '/cmd_vel')

    Returns:
        dict: Contains list of publisher node names,
            or a message if no publishers found.
    """
    # Validate input
    if not topic or not topic.strip():
        return {"error": "Topic name cannot be empty"}

    # rosbridge service call to get publishers
    message = {
        "op": "call_service",
        "service": "/rosapi/publishers",
        "type": "rosapi/Publishers",
        "args": {"topic": topic},
        "id": f"get_publishers_for_topic_request_{topic.replace('/', '_')}",
    }

    # Request publishers from rosbridge
    with ws_manager:
        response = ws_manager.request(message)

    # Check for service response errors first
    if response and "result" in response and not response["result"]:
        # Service call failed - return error with details from values
        error_msg = response.get("values", {}).get("message", "Service call failed")
        return {"error": f"Service call failed: {error_msg}"}

    # Return publishers if present
    if response and "values" in response:
        publishers = response["values"].get("publishers", [])
        return {"topic": topic, "publishers": publishers, "publisher_count": len(publishers)}
    else:
        return {"error": f"Failed to get publishers for topic {topic}"}


@mcp.tool(
    description=(
        "Get list of nodes that are subscribed to a specific topic.\n"
        "Example:\n"
        "get_subscribers_for_topic('/cmd_vel')"
    )
)
def get_subscribers_for_topic(topic: str) -> dict:
    """
    Get list of nodes that are subscribed to a specific topic.

    Args:
        topic (str): The topic name (e.g., '/cmd_vel')

    Returns:
        dict: Contains list of subscriber node names,
            or a message if no subscribers found.
    """
    # Validate input
    if not topic or not topic.strip():
        return {"error": "Topic name cannot be empty"}

    # rosbridge service call to get subscribers
    message = {
        "op": "call_service",
        "service": "/rosapi/subscribers",
        "type": "rosapi/Subscribers",
        "args": {"topic": topic},
        "id": f"get_subscribers_for_topic_request_{topic.replace('/', '_')}",
    }

    # Request subscribers from rosbridge
    with ws_manager:
        response = ws_manager.request(message)

    # Check for service response errors first
    if response and "result" in response and not response["result"]:
        # Service call failed - return error with details from values
        error_msg = response.get("values", {}).get("message", "Service call failed")
        return {"error": f"Service call failed: {error_msg}"}

    # Return subscribers if present
    if response and "values" in response:
        subscribers = response["values"].get("subscribers", [])
        return {"topic": topic, "subscribers": subscribers, "subscriber_count": len(subscribers)}
    else:
        return {"error": f"Failed to get subscribers for topic {topic}"}


@mcp.tool(
    description=(
        "Get comprehensive information about all ROS topics including publishers, subscribers, and message types. Note that this may take time to execute when three are a large number of topics since it queries each one by one under the hood. \n"
        "Example:\n"
        "inspect_all_topics()"
    )
)
def inspect_all_topics() -> dict:
    """
    Get comprehensive information about all ROS topics including publishers, subscribers, and message types.

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
            elif publishers_response and "error" in publishers_response:
                topic_errors.append(f"Topic {topic} publishers: {publishers_response['error']}")

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
            elif subscribers_response and "error" in subscribers_response:
                topic_errors.append(f"Topic {topic} subscribers: {subscribers_response['error']}")

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


@mcp.tool(
    description=(
        "Subscribe to a ROS topic and return the first message received.\n"
        "Example:\n"
        "subscribe_once(topic='/cmd_vel', msg_type='geometry_msgs/msg/TwistStamped')\n"
        "subscribe_once(topic='/slow_topic', msg_type='my_package/SlowMsg', timeout=None)  # Specify timeout only if topic publishes infrequently\n"
        "subscribe_once(topic='/high_rate_topic', msg_type='sensor_msgs/Image', timeout=None, queue_length=5, throttle_rate_ms=100)  # Control message buffering and rate"
    )
)
def subscribe_once(
    topic: str = "",
    msg_type: str = "",
    timeout: float | None = None,
    queue_length: int | None = None,
    throttle_rate_ms: int | None = None,
) -> dict:
    """
    Subscribe to a given ROS topic via rosbridge and return the first message received.

    Args:
        topic (str): The ROS topic name (e.g., "/cmd_vel", "/joint_states").
        msg_type (str): The ROS message type (e.g., "geometry_msgs/Twist").
        timeout (float | None): Timeout in seconds. If None, uses the default timeout.
        queue_length (int | None): How many messages to buffer before dropping old ones. Must be ≥ 1.
        throttle_rate_ms (int | None): Minimum interval between messages in milliseconds. Must be ≥ 0.

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

            if "Image" in msg_type:
                msg_data = parse_image(response)
            else:
                msg_data = parse_json(response)

            if not msg_data:
                continue  # non-JSON or empty

            # Check for status errors from rosbridge
            if msg_data.get("op") == "status" and msg_data.get("level") == "error":
                return {"error": f"Rosbridge error: {msg_data.get('msg', 'Unknown error')}"}

            # Check for the first published message
            if msg_data.get("op") == "publish" and msg_data.get("topic") == topic:
                # Unsubscribe before returning the message
                unsubscribe_msg = {"op": "unsubscribe", "topic": topic}
                ws_manager.send(unsubscribe_msg)
                if "Image" in msg_type:
                    return {
                        "message": "Image received successfully and saved in the MCP server. Run the 'analyze_previously_received_image' tool to analyze it"
                    }
                else:
                    return {"msg": msg_data.get("msg", {})}

        # Timeout - unsubscribe and return error
        unsubscribe_msg = {"op": "unsubscribe", "topic": topic}
        ws_manager.send(unsubscribe_msg)
        return {"error": "Timeout waiting for message from topic"}


@mcp.tool(
    description=(
        "Publish a single message to a ROS topic.\n"
        "Example:\n"
        "publish_once(topic='/cmd_vel', msg_type='geometry_msgs/msg/TwistStamped', msg={'linear': {'x': 1.0}})"
    )
)
def publish_once(topic: str = "", msg_type: str = "", msg: dict = {}) -> dict:
    """
    Publish a single message to a ROS topic via rosbridge.

    Args:
        topic (str): ROS topic name (e.g., "/cmd_vel")
        msg_type (str): ROS message type (e.g., "geometry_msgs/Twist")
        msg (dict): Message payload as a dictionary

    Returns:
        dict:
            - {"success": True} if sent without errors
            - {"error": "<error message>"} if connection/send failed
            - If rosbridge responds (usually it doesn’t for publish), parsed JSON or error info
    """
    # Validate critical args before attempting publish
    if not topic or not msg_type or msg == {}:
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


@mcp.tool(
    description=(
        "Subscribe to a topic for a duration and collect messages.\n"
        "Example:\n"
        "subscribe_for_duration(topic='/cmd_vel', msg_type='geometry_msgs/msg/TwistStamped', duration=5, max_messages=10)\n"
        "subscribe_for_duration(topic='/high_rate_topic', msg_type='sensor_msgs/Image', duration=10, queue_length=5, throttle_rate_ms=100)  # Control message buffering and rate"
    )
)
def subscribe_for_duration(
    topic: str = "",
    msg_type: str = "",
    duration: float = 5.0,
    max_messages: int = 100,
    queue_length: int | None = None,
    throttle_rate_ms: int | None = None,
) -> dict:
    """
    Subscribe to a ROS topic via rosbridge for a fixed duration and collect messages.

    Args:
        topic (str): ROS topic name (e.g. "/cmd_vel", "/joint_states")
        msg_type (str): ROS message type (e.g. "geometry_msgs/Twist")
        duration (float): How long (seconds) to listen for messages
        max_messages (int): Maximum number of messages to collect before stopping
        queue_length (int | None): How many messages to buffer before dropping old ones. Must be ≥ 1.
        throttle_rate_ms (int | None): Minimum interval between messages in milliseconds. Must be ≥ 0.

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

            msg_data = parse_json(response)
            if not msg_data:
                continue  # non-JSON or empty

            # Check for status errors from rosbridge
            if msg_data.get("op") == "status" and msg_data.get("level") == "error":
                status_errors.append(msg_data.get("msg", "Unknown error"))
                continue

            # Check for published messages matching our topic
            if msg_data.get("op") == "publish" and msg_data.get("topic") == topic:
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
    messages: List[Dict[str, Any]] = [],
    durations: List[float] = [],
) -> dict:
    """
    Publish a sequence of messages to a given ROS topic with delays in between.

    Args:
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
    if not topic or not msg_type or messages == [] or durations == []:
        return {
            "error": "Missing required arguments: topic, msg_type, messages, and durations must all be provided."
        }

    # Ensure same length for messages & durations
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


## ############################################################################################## ##
##
##                       ROS SERVICES
##
## ############################################################################################## ##


@mcp.tool(description=("Get list of all available ROS services.\nExample:\nget_services()"))
def get_services() -> dict:
    """
    Get list of all available ROS services.

    Returns:
        dict: Contains list of all active services,
            or a message string if no services are found.
    """
    # rosbridge service call to get service list
    message = {
        "op": "call_service",
        "service": "/rosapi/services",
        "type": "rosapi/Services",
        "args": {},
        "id": "get_services_request_1",
    }

    # Request service list from rosbridge
    with ws_manager:
        response = ws_manager.request(message)

    # Check for service response errors first
    if response and "result" in response and not response["result"]:
        # Service call failed - return error with details from values
        error_msg = response.get("values", {}).get("message", "Service call failed")
        return {"error": f"Service call failed: {error_msg}"}

    # Return service info if present
    if response and "values" in response:
        services = response["values"].get("services", [])
        return {"services": services, "service_count": len(services)}
    else:
        return {"warning": "No services found"}


@mcp.tool(
    description=(
        "Get the service type for a specific service.\nExample:\nget_service_type('/rosapi/topics')"
    )
)
def get_service_type(service: str) -> dict:
    """
    Get the service type for a specific service.

    Args:
        service (str): The service name (e.g., '/rosapi/topics')

    Returns:
        dict: Contains the service type,
            or an error message if service doesn't exist.
    """
    # Validate input
    if not service or not service.strip():
        return {"error": "Service name cannot be empty"}

    # rosbridge service call to get service type
    message = {
        "op": "call_service",
        "service": "/rosapi/service_type",
        "type": "rosapi/ServiceType",
        "args": {"service": service},
        "id": f"get_service_type_request_{service.replace('/', '_')}",
    }

    # Request service type from rosbridge
    with ws_manager:
        response = ws_manager.request(message)

    # Check for service response errors first
    if response and "result" in response and not response["result"]:
        # Service call failed - return error with details from values
        error_msg = response.get("values", {}).get("message", "Service call failed")
        return {"error": f"Service call failed: {error_msg}"}

    # Return service type if present
    if response and "values" in response:
        service_type = response["values"].get("type", "")
        if service_type:
            return {"service": service, "type": service_type}
        else:
            return {"error": f"Service {service} does not exist or has no type"}
    else:
        return {"error": f"Failed to get type for service {service}"}


@mcp.tool(
    description=(
        "Get complete service details including request and response structures.\n"
        "Example:\n"
        "get_service_details('my_package/CustomService')"
    )
)
def get_service_details(service_type: str) -> dict:
    """
    Get complete service details including request and response structures.

    Args:
        service_type (str): The service type (e.g., 'my_package/CustomService')

    Returns:
        dict: Contains complete service definition with request and response structures.
    """
    # Validate input
    if not service_type or not service_type.strip():
        return {"error": "Service type cannot be empty"}

    result = {"service_type": service_type, "request": {}, "response": {}}

    # Get both request and response details in a single WebSocket context
    with ws_manager:
        # Get request details
        request_message = {
            "op": "call_service",
            "service": "/rosapi/service_request_details",
            "type": "rosapi/ServiceRequestDetails",
            "args": {"type": service_type},
            "id": f"get_service_details_request_{service_type.replace('/', '_')}",
        }

        request_response = ws_manager.request(request_message)
        if request_response and "values" in request_response:
            typedefs = request_response["values"].get("typedefs", [])
            if typedefs:
                for typedef in typedefs:
                    field_names = typedef.get("fieldnames", [])
                    field_types = typedef.get("fieldtypes", [])
                    fields = {}
                    for name, ftype in zip(field_names, field_types):
                        fields[name] = ftype
                    result["request"] = {"fields": fields, "field_count": len(fields)}

        # Get response details
        response_message = {
            "op": "call_service",
            "service": "/rosapi/service_response_details",
            "type": "rosapi/ServiceResponseDetails",
            "args": {"type": service_type},
            "id": f"get_service_details_response_{service_type.replace('/', '_')}",
        }

        response_response = ws_manager.request(response_message)
        if response_response and "values" in response_response:
            typedefs = response_response["values"].get("typedefs", [])
            if typedefs:
                for typedef in typedefs:
                    field_names = typedef.get("fieldnames", [])
                    field_types = typedef.get("fieldtypes", [])
                    fields = {}
                    for name, ftype in zip(field_names, field_types):
                        fields[name] = ftype
                    result["response"] = {"fields": fields, "field_count": len(fields)}

    # Check if we got any data
    if not result["request"] and not result["response"]:
        return {"error": f"Service type {service_type} not found or has no definition"}

    return result


@mcp.tool(
    description=(
        "Get list of nodes that provide a specific service.\n"
        "Example:\n"
        "get_service_providers('/rosapi/topics')"
    )
)
def get_service_providers(service: str) -> dict:
    """
    Get list of nodes that provide a specific service.

    Args:
        service (str): The service name (e.g., '/rosapi/topics')

    Returns:
        dict: Contains list of nodes providing this service,
            or an error message if service doesn't exist.
    """
    # Validate input
    if not service or not service.strip():
        return {"error": "Service name cannot be empty"}

    # rosbridge service call to get service providers (using service_node like inspect_all_services)
    message = {
        "op": "call_service",
        "service": "/rosapi/service_node",
        "type": "rosapi/ServiceNode",
        "args": {"service": service},
        "id": f"get_service_providers_request_{service.replace('/', '_')}",
    }

    # Request service providers from rosbridge
    with ws_manager:
        response = ws_manager.request(message)

    # Return service providers if present (using same logic as inspect_all_services)
    providers = []

    # Handle different response formats safely
    if response and isinstance(response, dict):
        if "values" in response:
            node = response["values"].get("node", "")
            if node:
                providers = [node]
        elif "result" in response:
            node = response["result"].get("node", "")
            if node:
                providers = [node]
        elif "error" in response:
            return {"error": f"Service call failed: {response['error']}"}
    elif response is False:
        return {"error": f"No response received for service {service}"}
    elif response is True:
        return {"error": f"Unexpected boolean response for service {service}"}
    else:
        return {"error": f"Failed to get providers for service {service}"}

    return {"service": service, "providers": providers, "provider_count": len(providers)}


@mcp.tool(
    description=(
        "Get comprehensive information about all services including types and providers. Note that this may take time to execute when three are a large number of services since it queries each one by one under the hood. \n"
        "Example:\n"
        "inspect_all_services()"
    )
)
def inspect_all_services() -> dict:
    """
    Get comprehensive information about all services including types and providers.

    Returns:
        dict: Contains detailed information about all services,
            including service names, types, and provider nodes.
    """
    # First get all services
    services_message = {
        "op": "call_service",
        "service": "/rosapi/services",
        "type": "rosapi/Services",
        "args": {},
        "id": "inspect_all_services_request_1",
    }

    with ws_manager:
        services_response = ws_manager.request(services_message)

        if not services_response or "values" not in services_response:
            return {"error": "Failed to get services list"}

        services = services_response["values"].get("services", [])
        service_details = {}

        # Get details for each service
        service_errors = []
        for service in services:
            # Get service type
            type_message = {
                "op": "call_service",
                "service": "/rosapi/service_type",
                "type": "rosapi/ServiceType",
                "args": {"service": service},
                "id": f"get_type_{service.replace('/', '_')}",
            }

            type_response = ws_manager.request(type_message)
            service_type = ""
            if type_response and "values" in type_response:
                service_type = type_response["values"].get("type", "unknown")
            elif type_response and "error" in type_response:
                service_errors.append(f"Service {service}: {type_response['error']}")

            # Get service provider (using service_node instead of service_providers)
            provider_message = {
                "op": "call_service",
                "service": "/rosapi/service_node",
                "type": "rosapi/ServiceNode",
                "args": {"service": service},
                "id": f"get_provider_{service.replace('/', '_')}",
            }

            provider_response = ws_manager.request(provider_message)
            providers = []

            # Handle different response formats safely
            if provider_response and isinstance(provider_response, dict):
                if "values" in provider_response:
                    node = provider_response["values"].get("node", "")
                    if node:
                        providers = [node]
                elif "result" in provider_response:
                    node = provider_response["result"].get("node", "")
                    if node:
                        providers = [node]
                elif "error" in provider_response:
                    service_errors.append(
                        f"Service {service} provider: {provider_response['error']}"
                    )
            elif provider_response is False:
                service_errors.append(f"Service {service} provider: No response received")
            elif provider_response is True:
                service_errors.append(f"Service {service} provider: Unexpected boolean response")

            service_details[service] = {
                "type": service_type,
                "providers": providers,
                "provider_count": len(providers),
            }

        return {
            "total_services": len(services),
            "services": service_details,
            "service_errors": service_errors,  # Include any errors encountered during inspection
        }


@mcp.tool(
    description=(
        "Call a ROS service with specified request data.\n"
        "Example:\n"
        "call_service('/rosapi/topics', 'rosapi/Topics', {})\n"
        "call_service('/slow_service', 'my_package/SlowService', {}, timeout=10.0)  # Specify timeout only for slow services"
    )
)
def call_service(
    service_name: str, service_type: str, request: dict, timeout: float | None = None
) -> dict:
    """
    Call a ROS service with specified request data.

    Args:
        service_name (str): The service name (e.g., '/rosapi/topics')
        service_type (str): The service type (e.g., 'rosapi/Topics')
        request (dict): Service request data as a dictionary
        timeout (float | None): Timeout in seconds. If None, uses the default timeout.

    Returns:
        dict: Contains the service response or error information.
    """
    # rosbridge service call
    message = {
        "op": "call_service",
        "service": service_name,
        "type": service_type,
        "args": request,
        "id": f"call_service_request_{service_name.replace('/', '_')}",
    }

    # Call the service through rosbridge
    with ws_manager:
        response = ws_manager.request(message, timeout=timeout)

    # Check for service response errors first
    if response and "result" in response and not response["result"]:
        # Service call failed - return error with details from values
        error_msg = response.get("values", {}).get("message", "Service call failed")
        return {
            "service": service_name,
            "service_type": service_type,
            "success": False,
            "error": f"Service call failed: {error_msg}",
        }

    # Return service response if present
    if response:
        if response.get("op") == "service_response":
            # Alternative response format
            return {
                "service": service_name,
                "service_type": service_type,
                "success": response.get("result", True),
                "result": response.get("values", {}),
            }
        elif response.get("op") == "status" and response.get("level") == "error":
            # Error response
            return {
                "service": service_name,
                "service_type": service_type,
                "success": False,
                "error": response.get("msg", "Unknown error"),
            }
        else:
            # Unexpected response format
            return {
                "service": service_name,
                "service_type": service_type,
                "success": False,
                "error": "Unexpected response format",
                "raw_response": response,
            }
    else:
        return {
            "service": service_name,
            "service_type": service_type,
            "success": False,
            "error": "No response received from service call",
        }


@mcp.tool(description=("Get list of all currently running ROS nodes.\nExample:\nget_nodes()"))
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
        "service": "/rosapi/nodes",
        "type": "rosapi/Nodes",
        "args": {},
        "id": "get_nodes_request_1",
    }

    # Request node list from rosbridge
    with ws_manager:
        response = ws_manager.request(message)

    # Check for service response errors first
    if response and "result" in response and not response["result"]:
        # Service call failed - return error with details from values
        error_msg = response.get("values", {}).get("message", "Service call failed")
        return {"error": f"Service call failed: {error_msg}"}

    # Return node info if present
    if response and "values" in response:
        nodes = response["values"].get("nodes", [])
        return {"nodes": nodes, "node_count": len(nodes)}
    else:
        return {"warning": "No nodes found"}


@mcp.tool(
    description=(
        "Get a single ROS parameter value by name. Works only with ROS 2.\nExample:\nget_param('/turtlesim:background_b')"
    )
)
def get_parameter(name: str) -> dict:
    """
    Get a single ROS parameter value by name. Works only with ROS 2.

    Args:
        name (str): The parameter name (e.g., '/turtlesim:background_b')

    Returns:
        dict: Contains parameter value and metadata, or error message if parameter not found.
    """
    if not name or not name.strip():
        return {"error": "Parameter name cannot be empty"}

    message = {
        "op": "call_service",
        "service": "/rosapi/get_param",
        "type": "rosapi/GetParam",
        "args": {"name": name},
        "id": f"get_param_{name.replace('/', '_').replace(':', '_')}",
    }

    with ws_manager:
        response = ws_manager.request(message)

    if response and "values" in response:
        result_data = response["values"]
        return {
            "name": name,
            "value": result_data.get("value", ""),
            "successful": result_data.get("successful", False),
            "reason": result_data.get("reason", ""),
        }
    elif response and "result" in response and response["result"]:
        result_data = response["result"]
        return {
            "name": name,
            "value": result_data.get("value", ""),
            "successful": result_data.get("successful", False),
            "reason": result_data.get("reason", ""),
        }
    else:
        error_msg = (
            response.get("values", {}).get("message", "Service call failed")
            if response
            else "No response"
        )
        return {"error": f"Failed to get parameter {name}: {error_msg}"}


@mcp.tool(
    description=(
        "Set a single ROS parameter value. Works only with ROS 2.\nExample:\nset_param('/turtlesim:background_b', '255')"
    )
)
def set_parameter(name: str, value: str) -> dict:
    """
    Set a single ROS parameter value. Works only with ROS 2.

    Args:
        name (str): The parameter name (e.g., '/turtlesim:background_b')
        value (str): The parameter value to set

    Returns:
        dict: Contains success status and metadata, or error message if failed.
    """
    if not name or not name.strip():
        return {"error": "Parameter name cannot be empty"}

    message = {
        "op": "call_service",
        "service": "/rosapi/set_param",
        "type": "rosapi/SetParam",
        "args": {"name": name, "value": value},
        "id": f"set_param_{name.replace('/', '_').replace(':', '_')}",
    }

    with ws_manager:
        response = ws_manager.request(message)

    if response and "values" in response:
        result_data = response["values"]
        return {
            "name": name,
            "value": value,
            "successful": result_data.get("successful", False),
            "reason": result_data.get("reason", ""),
        }
    elif response and "result" in response and response["result"]:
        result_data = response["result"]
        return {
            "name": name,
            "value": value,
            "successful": result_data.get("successful", False),
            "reason": result_data.get("reason", ""),
        }
    else:
        error_msg = (
            response.get("values", {}).get("message", "Service call failed")
            if response
            else "No response"
        )
        return {"error": f"Failed to set parameter {name}: {error_msg}"}


@mcp.tool(
    description=(
        "Check if a ROS parameter exists. Works only with ROS 2.\nExample:\nhas_param('/turtlesim:background_b')"
    )
)
def has_parameter(name: str) -> dict:
    """
    Check if a ROS parameter exists. Works only with ROS 2.

    Args:
        name (str): The parameter name (e.g., '/turtlesim:background_b')

    Returns:
        dict: Contains existence status and metadata, or error message if failed.
    """
    if not name or not name.strip():
        return {"error": "Parameter name cannot be empty"}

    message = {
        "op": "call_service",
        "service": "/rosapi/has_param",
        "type": "rosapi/HasParam",
        "args": {"name": name},
        "id": f"has_param_{name.replace('/', '_').replace(':', '_')}",
    }

    with ws_manager:
        response = ws_manager.request(message)

    if response and "values" in response:
        result_data = response["values"]
        return {
            "name": name,
            "exists": result_data.get("exists", False),
            "successful": result_data.get("successful", False),
            "reason": result_data.get("reason", ""),
        }
    elif response and "result" in response and response["result"]:
        result_data = response["result"]
        return {
            "name": name,
            "exists": result_data.get("exists", False),
            "successful": result_data.get("successful", False),
            "reason": result_data.get("reason", ""),
        }
    else:
        error_msg = (
            response.get("values", {}).get("message", "Service call failed")
            if response
            else "No response"
        )
        return {"error": f"Failed to check parameter {name}: {error_msg}"}


@mcp.tool(
    description=(
        "Delete a ROS parameter. Works only with ROS 2.\nExample:\ndelete_param('/turtlesim:background_b')"
    )
)
def delete_parameter(name: str) -> dict:
    """
    Delete a ROS parameter. Works only with ROS 2.

    Args:
        name (str): The parameter name (e.g., '/turtlesim:background_b')

    Returns:
        dict: Contains success status and metadata, or error message if failed.
    """
    if not name or not name.strip():
        return {"error": "Parameter name cannot be empty"}

    message = {
        "op": "call_service",
        "service": "/rosapi/delete_param",
        "type": "rosapi/DeleteParam",
        "args": {"name": name},
        "id": f"delete_param_{name.replace('/', '_').replace(':', '_')}",
    }

    with ws_manager:
        response = ws_manager.request(message)

    if response and "values" in response:
        result_data = response["values"]
        return {
            "name": name,
            "successful": result_data.get("successful", False),
            "reason": result_data.get("reason", ""),
        }
    elif response and "result" in response and response["result"]:
        result_data = response["result"]
        return {
            "name": name,
            "successful": result_data.get("successful", False),
            "reason": result_data.get("reason", ""),
        }
    else:
        error_msg = (
            response.get("values", {}).get("message", "Service call failed")
            if response
            else "No response"
        )
        return {"error": f"Failed to delete parameter {name}: {error_msg}"}


@mcp.tool(
    description=(
        "Get list of all ROS parameter names. Works only with ROS 2.\nExample:\nget_parameters()"
    )
)
def get_parameters() -> dict:
    """
    Get list of all ROS parameter names. Works only with ROS 2.

    Returns:
        dict: Contains list of all parameter names, or error message if failed.
    """
    message = {
        "op": "call_service",
        "service": "/rosapi/get_param_names",
        "type": "rosapi/GetParamNames",
        "args": {},
        "id": "get_parameters_request_1",
    }

    with ws_manager:
        response = ws_manager.request(message)

    if response and "values" in response:
        names = response["values"].get("names", [])
        return {"parameters": names, "parameter_count": len(names)}
    elif response and "result" in response and response["result"]:
        result_data = response["result"]
        if isinstance(result_data, dict):
            names = result_data.get("names", [])
        else:
            names = []
        return {"parameters": names, "parameter_count": len(names)}
    else:
        error_msg = (
            response.get("values", {}).get("message", "Service call failed")
            if response
            else "No response"
        )
        return {"error": f"Failed to get parameter names: {error_msg}"}


@mcp.tool(
    description=(
        "Get comprehensive information about all ROS parameters including values and metadata.\nWorks only with ROS 2.\n"
        "Example:\n"
        "inspect_all_parameters()"
    )
)
def inspect_all_parameters() -> dict:
    """
    Get comprehensive information about all ROS parameters including values and metadata. Works only with ROS 2.

    Returns:
        dict: Contains detailed information about all parameters,
            including parameter names, values, and metadata.
    """
    # First get all parameters
    parameters_message = {
        "op": "call_service",
        "service": "/rosapi/get_param_names",
        "type": "rosapi/GetParamNames",
        "args": {},
        "id": "inspect_all_parameters_request_1",
    }

    with ws_manager:
        parameters_response = ws_manager.request(parameters_message)

        if not parameters_response or "values" not in parameters_response:
            return {"error": "Failed to get parameters list"}

        parameters = parameters_response["values"].get("names", [])
        parameter_details = {}

        # Get details for each parameter
        parameter_errors = []
        for param_name in parameters:
            # Get parameter value
            value_message = {
                "op": "call_service",
                "service": "/rosapi/get_param",
                "type": "rosapi/GetParam",
                "args": {"name": param_name},
                "id": f"get_param_{param_name.replace('/', '_').replace(':', '_')}",
            }

            value_response = ws_manager.request(value_message)
            param_value = ""
            param_successful = False
            if value_response and "values" in value_response:
                value_data = value_response["values"]
                param_value = value_data.get("value", "")
                param_successful = value_data.get("successful", False)
            elif value_response and "result" in value_response and value_response["result"]:
                value_data = value_response["result"]
                param_value = value_data.get("value", "")
                param_successful = value_data.get("successful", False)
            elif value_response and "error" in value_response:
                parameter_errors.append(f"Parameter {param_name}: {value_response['error']}")

            # Get parameter type (using describe_parameters service)
            type_message = {
                "op": "call_service",
                "service": "/rosapi/describe_parameters",
                "type": "rcl_interfaces/DescribeParameters",
                "args": {"names": [param_name]},
                "id": f"describe_param_{param_name.replace('/', '_').replace(':', '_')}",
            }

            type_response = ws_manager.request(type_message)
            param_type = "unknown"

            # Handle different response formats for parameter type detection
            if type_response and isinstance(type_response, dict):
                if "values" in type_response:
                    result_data = type_response["values"]
                    if isinstance(result_data, dict):
                        descriptors = result_data.get("descriptors", [])
                        if descriptors and len(descriptors) > 0:
                            param_type = descriptors[0].get("type", "unknown")
                elif "result" in type_response and type_response["result"]:
                    result_data = type_response["result"]
                    if isinstance(result_data, dict):
                        descriptors = result_data.get("descriptors", [])
                        if descriptors and len(descriptors) > 0:
                            param_type = descriptors[0].get("type", "unknown")
                elif "error" in type_response:
                    parameter_errors.append(
                        f"Parameter {param_name} type: {type_response['error']}"
                    )

            # Fallback: Try to infer type from value
            if param_type == "unknown" and param_value:
                try:
                    # Remove quotes for type checking
                    clean_value = param_value.strip('"')

                    # Try to parse as different types
                    if clean_value.lower() in ["true", "false"]:
                        param_type = "bool"
                    elif clean_value.isdigit() or (
                        clean_value.startswith("-") and clean_value[1:].isdigit()
                    ):
                        param_type = "int"
                    elif (
                        "." in clean_value
                        and clean_value.replace(".", "").replace("-", "").isdigit()
                    ):
                        param_type = "float"
                    elif param_value.startswith('"') and param_value.endswith('"'):
                        param_type = "string"
                    elif clean_value == "":
                        param_type = "string"
                    else:
                        param_type = "string"
                except Exception:
                    param_type = "string"

            parameter_details[param_name] = {
                "value": param_value,
                "type": param_type,
                "exists": param_successful,
            }

        return {
            "total_parameters": len(parameters),
            "parameters": parameter_details,
            "parameter_errors": parameter_errors,  # Include any errors encountered during inspection
        }


@mcp.tool(
    description=(
        "Get comprehensive details about a specific ROS parameter including value, type, and metadata. Works only with ROS 2.\n    "
        "Example:\n"
        "get_parameter_details('/turtlesim:background_r')"
    )
)
def get_parameter_details(name: str) -> dict:
    """
    Get comprehensive details about a specific ROS parameter including value, type, and metadata. Works only with ROS 2.

    Args:
        name (str): The parameter name (e.g., '/turtlesim:background_r')

    Returns:
        dict: Contains detailed parameter information or error details.
    """
    # Validate input
    if not name or not name.strip():
        return {"error": "Parameter name cannot be empty"}

    # Get parameter value
    value_message = {
        "op": "call_service",
        "service": "/rosapi/get_param",
        "type": "rosapi/GetParam",
        "args": {"name": name},
        "id": f"get_param_details_{name.replace('/', '_').replace(':', '_')}",
    }

    with ws_manager:
        value_response = ws_manager.request(value_message)

    if not value_response or "values" not in value_response:
        return {"error": f"Failed to get parameter {name}"}

    value_data = value_response["values"]
    param_value = value_data.get("value", "")
    param_successful = value_data.get("successful", False)

    if not param_successful:
        return {"error": f"Parameter {name} does not exist"}

    # Get parameter type
    type_message = {
        "op": "call_service",
        "service": "/rosapi/describe_parameters",
        "type": "rcl_interfaces/DescribeParameters",
        "args": {"names": [name]},
        "id": f"describe_param_details_{name.replace('/', '_').replace(':', '_')}",
    }

    with ws_manager:
        type_response = ws_manager.request(type_message)

    param_type = "unknown"
    param_description = ""

    if type_response and isinstance(type_response, dict):
        if "values" in type_response:
            result_data = type_response["values"]
            if isinstance(result_data, dict):
                descriptors = result_data.get("descriptors", [])
                if descriptors and len(descriptors) > 0:
                    descriptor = descriptors[0]
                    param_type = descriptor.get("type", "unknown")
                    param_description = descriptor.get("description", "")
        elif "result" in type_response and type_response["result"]:
            result_data = type_response["result"]
            if isinstance(result_data, dict):
                descriptors = result_data.get("descriptors", [])
                if descriptors and len(descriptors) > 0:
                    descriptor = descriptors[0]
                    param_type = descriptor.get("type", "unknown")
                    param_description = descriptor.get("description", "")

    # Fallback: Try to infer type from value
    if param_type == "unknown" and param_value:
        try:
            clean_value = param_value.strip('"')
            if clean_value.lower() in ["true", "false"]:
                param_type = "bool"
            elif clean_value.isdigit() or (
                clean_value.startswith("-") and clean_value[1:].isdigit()
            ):
                param_type = "int"
            elif "." in clean_value and clean_value.replace(".", "").replace("-", "").isdigit():
                param_type = "float"
            elif param_value.startswith('"') and param_value.endswith('"'):
                param_type = "string"
            elif clean_value == "":
                param_type = "string"
            else:
                param_type = "string"
        except Exception:
            param_type = "string"

    return {
        "name": name,
        "value": param_value,
        "type": param_type,
        "exists": param_successful,
        "description": param_description,
        "node": name.split(":")[0] if ":" in name else "",
        "parameter": name.split(":")[1] if ":" in name else name,
    }


@mcp.tool(
    description=(
        "Get detailed information about a specific node including its publishers, subscribers, and services.\n"
        "Example:\n"
        "get_node_details('/turtlesim')"
    )
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
        "service": "/rosapi/node_details",
        "type": "rosapi/NodeDetails",
        "args": {"node": node},
        "id": f"get_node_details_{node.replace('/', '_')}",
    }

    # Request node details from rosbridge
    with ws_manager:
        response = ws_manager.request(message)

    # Check for service response errors first
    if response and "result" in response and not response["result"]:
        # Service call failed - return error with details from values
        error_msg = response.get("values", {}).get("message", "Service call failed")
        return {"error": f"Service call failed: {error_msg}"}

    # Extract data from the response
    if response and "values" in response:
        values = response["values"]
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


@mcp.tool(
    description=(
        "Get comprehensive information about all ROS nodes including their publishers, subscribers, and services.\n"
        "Example:\n"
        "inspect_all_nodes()"
    )
)
def inspect_all_nodes() -> dict:
    """
    Get comprehensive information about all ROS nodes including their publishers, subscribers, and services.

    Returns:
        dict: Contains detailed information about all nodes including:
            - Node names and details
            - Publishers for each node
            - Subscribers for each node
            - Services provided by each node
            - Connection counts and statistics
    """
    # First get all nodes
    nodes_message = {
        "op": "call_service",
        "service": "/rosapi/nodes",
        "type": "rosapi/Nodes",
        "args": {},
        "id": "inspect_all_nodes_request_1",
    }

    with ws_manager:
        nodes_response = ws_manager.request(nodes_message)

        if not nodes_response or "values" not in nodes_response:
            return {"error": "Failed to get nodes list"}

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

        return {
            "total_nodes": len(nodes),
            "nodes": node_details,
            "node_errors": node_errors,  # Include any errors encountered during inspection
        }


## ############################################################################################## ##
##
##                       NETWORK DIAGNOSTICS
##
## ############################################################################################## ##


@mcp.tool(
    description=(
        "Ping a robot's IP address and check if a specific port is open.\n"
        "A successful ping to the IP but not the port can indicate that ROSbridge is not running.\n"
        "Example:\n"
        "ping_robot(ip='192.168.1.100', port=9090)"
    )
)
def ping_robot(ip: str, port: int, ping_timeout: float = 2.0, port_timeout: float = 2.0) -> dict:
    """
    Ping an IP address and check if a specific port is open.

    Args:
        ip (str): The IP address to ping (e.g., '192.168.1.100')
        port (int): The port number to check (e.g., 9090)
        ping_timeout (float): Timeout for ping in seconds. Default = 2.0.
        port_timeout (float): Timeout for port check in seconds. Default = 2.0.

    Returns:
        dict: Contains ping and port check results with detailed status information.
    """
    return ping_ip_and_port(ip, port, ping_timeout, port_timeout)


## ############################################################################################## ##
##
##                      IMAGE ANALYSIS
##
## ############################################################################################## ##
def _encode_image_to_imagecontent(image):
    """
    Encodes a PIL Image to a format compatible with ImageContent.

    Args:
        image (PIL.Image.Image): The image to encode.

    Returns:
        ImageContent: JPEG-encoded image wrapped in an ImageContent object.
    """
    buffer = io.BytesIO()
    image.save(buffer, format="JPEG")
    img_bytes = buffer.getvalue()
    img_obj = Image(data=img_bytes, format="jpeg")
    return img_obj.to_image_content()


@mcp.tool(
    description=(
        "First, subscribe to an Image topic using 'subscribe_once' to save an image.\n"
        "Then, use this tool to analyze the saved image\n"
    )
)
def analyze_previously_received_image():
    """
    Analyze the previously received image saved at ./camera/received_image.jpeg

    This tool loads the previously saved image from './camera/received_image.jpeg'
    (which must have been created by 'parse_image' or 'subscribe_once'), and converts
    it into an MCP-compatible ImageContent format so that the LLM can interpret it.
    """
    path = "./camera/received_image.jpeg"
    if not os.path.exists(path):
        return {"error": "No image found at ./camera/received_image.jpeg"}
    img = PILImage.open(path)
    return _encode_image_to_imagecontent(img)


def parse_arguments():
    """Parse command line arguments for MCP server configuration."""
    parser = argparse.ArgumentParser(
        description="ROS MCP Server - Connect to ROS robots via MCP protocol",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python server.py                                    # Use stdio transport (default)
  python server.py --transport http --host 0.0.0.0 --port 9000
  python server.py --transport streamable-http --host 127.0.0.1 --port 8080
        """,
    )

    parser.add_argument(
        "--transport",
        choices=["stdio", "http", "streamable-http", "sse"],
        default="stdio",
        help="MCP transport protocol to use (default: stdio)",
    )

    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="Host address for HTTP-based transports (default: 127.0.0.1)",
    )

    parser.add_argument(
        "--port",
        type=int,
        default=9000,
        help="Port number for HTTP-based transports (default: 9000)",
    )

    return parser.parse_args()


def main():
    """Main entry point for the MCP server console script."""
    # Parse command line arguments
    args = parse_arguments()

    # Update global variables with parsed arguments
    global MCP_TRANSPORT, MCP_HOST, MCP_PORT
    MCP_TRANSPORT = args.transport.lower()
    MCP_HOST = args.host
    MCP_PORT = args.port

    if MCP_TRANSPORT == "stdio":
        # stdio doesn't need host/port
        mcp.run(transport="stdio")

    elif MCP_TRANSPORT in {"http", "streamable-http"}:
        # http and streamable-http both require host/port
        print(f"Transport: {MCP_TRANSPORT} -> http://{MCP_HOST}:{MCP_PORT}")
        mcp.run(transport=MCP_TRANSPORT, host=MCP_HOST, port=MCP_PORT)

    elif MCP_TRANSPORT == "sse":
        print(f"Transport: {MCP_TRANSPORT} -> http://{MCP_HOST}:{MCP_PORT}")
        print("Currently unsupported. Use 'stdio', 'http', or 'streamable-http'.")
        mcp.run(transport=MCP_TRANSPORT, host=MCP_HOST, port=MCP_PORT)

    else:
        raise ValueError(
            f"Unsupported MCP_TRANSPORT={MCP_TRANSPORT!r}. "
            "Use 'stdio', 'http', or 'streamable-http'."
        )


if __name__ == "__main__":
    main()
