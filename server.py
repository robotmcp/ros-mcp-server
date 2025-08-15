import json
import time
from typing import Optional

from mcp.server.fastmcp import FastMCP

from utils.websocket_manager import WebSocketManager, parse_json
from utils.network_utils import ping_ip_and_port

# ROS bridge connection settings
ROSBRIDGE_IP = "127.0.0.1"  # Default is localhost. Replace with your local IPor set using the LLM.
ROSBRIDGE_PORT = (
    9090  # Rosbridge default is 9090. Replace with your rosbridge port or set using the LLM.
)

# Initialize MCP server and WebSocket manager
mcp = FastMCP("ros-mcp-server")
ws_manager = WebSocketManager(
    ROSBRIDGE_IP, ROSBRIDGE_PORT, default_timeout=5.0
)  # Increased default timeout for ROS operations


@mcp.tool(description=("Connect to a robot by setting IP/port and testing connectivity."))
def connect_to_robot(ip: Optional[str] = None, port: Optional[int] = None, ping_timeout: float = 2.0, port_timeout: float = 2.0) -> dict:
    """
    Connect to a robot by setting the IP and port for the WebSocket connection, then testing connectivity.

    Args:
        ip (Optional[str]): The IP address of the rosbridge server. Defaults to "127.0.0.1" (localhost).
        port (Optional[int]): The port number of the rosbridge server. Defaults to 9090.
        ping_timeout (float): Timeout for ping in seconds. Default = 2.0.
        port_timeout (float): Timeout for port check in seconds. Default = 2.0.

    Returns:
        dict: Connection status with ping and port check results.
    """
    # Set default values if None
    actual_ip = ip if ip is not None else "127.0.0.1"
    actual_port = port if port is not None else 9090
    
    # Set the IP and port
    ws_manager.set_ip(actual_ip, actual_port)
    
    # Test connectivity
    ping_result = ping_robot(actual_ip, actual_port, ping_timeout, port_timeout)
    
    # Combine the results
    return {
        "message": f"WebSocket IP set to {actual_ip}:{actual_port}",
        "connectivity_test": ping_result
    }


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
        "Subscribe to a ROS topic and return the first message received.\n"
        "Example:\n"
        "subscribe_once(topic='/cmd_vel', msg_type='geometry_msgs/msg/TwistStamped')\n"
        "subscribe_once(topic='/slow_topic', msg_type='my_package/SlowMsg', timeout=10.0)  # Specify timeout only if topic publishes infrequently\n"
        "subscribe_once(topic='/high_rate_topic', msg_type='sensor_msgs/Image', queue_length=5, throttle_rate_ms=100)  # Control message buffering and rate"
    )
)
def subscribe_once(
    topic: str = "",
    msg_type: str = "",
    timeout: Optional[float] = None,
    queue_length: Optional[int] = None,
    throttle_rate_ms: Optional[int] = None,
) -> dict:
    """
    Subscribe to a given ROS topic via rosbridge and return the first message received.

    Args:
        topic (str): The ROS topic name (e.g., "/cmd_vel", "/joint_states").
        msg_type (str): The ROS message type (e.g., "geometry_msgs/Twist").
        timeout (Optional[float]): Timeout in seconds. If None, uses the default timeout.
        queue_length (Optional[int]): How many messages to buffer before dropping old ones. Must be ≥ 1.
        throttle_rate_ms (Optional[int]): Minimum interval between messages in milliseconds. Must be ≥ 0.

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
    queue_length: Optional[int] = None,
    throttle_rate_ms: Optional[int] = None,
) -> dict:
    """
    Subscribe to a ROS topic via rosbridge for a fixed duration and collect messages.

    Args:
        topic (str): ROS topic name (e.g. "/cmd_vel", "/joint_states")
        msg_type (str): ROS message type (e.g. "geometry_msgs/Twist")
        duration (float): How long (seconds) to listen for messages
        max_messages (int): Maximum number of messages to collect before stopping
        queue_length (Optional[int]): How many messages to buffer before dropping old ones. Must be ≥ 1.
        throttle_rate_ms (Optional[int]): Minimum interval between messages in milliseconds. Must be ≥ 0.

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
    topic: str = "", msg_type: str = "", messages: list = [], durations: list = []
) -> dict:
    """
    Publish a sequence of messages to a given ROS topic with delays in between.

    Args:
        topic (str): ROS topic name (e.g., "/cmd_vel")
        msg_type (str): ROS message type (e.g., "geometry_msgs/Twist")
        messages (list): A list of message dictionaries (ROS-compatible payloads)
        durations (list): A list of durations (seconds) to wait between messages

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

    # rosbridge service call to get service providers
    message = {
        "op": "call_service",
        "service": "/rosapi/service_providers",
        "type": "rosapi/ServiceProviders",
        "args": {"service": service},
        "id": f"get_service_providers_request_{service.replace('/', '_')}",
    }

    # Request service providers from rosbridge
    with ws_manager:
        response = ws_manager.request(message)

    # Return service providers if present
    if response and "values" in response:
        providers = response["values"].get("providers", [])
        return {"service": service, "providers": providers, "provider_count": len(providers)}
    else:
        return {"error": f"Failed to get providers for service {service}"}


@mcp.tool(
    description=(
        "Get comprehensive information about all services including types and providers.\n"
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

            # Get service providers
            providers_message = {
                "op": "call_service",
                "service": "/rosapi/service_providers",
                "type": "rosapi/ServiceProviders",
                "args": {"service": service},
                "id": f"get_providers_{service.replace('/', '_')}",
            }

            providers_response = ws_manager.request(providers_message)
            providers = []
            if providers_response and "values" in providers_response:
                providers = providers_response["values"].get("providers", [])
            elif providers_response and "error" in providers_response:
                service_errors.append(f"Service {service} providers: {providers_response['error']}")

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
    service_name: str, service_type: str, request: dict, timeout: Optional[float] = None
) -> dict:
    """
    Call a ROS service with specified request data.

    Args:
        service_name (str): The service name (e.g., '/rosapi/topics')
        service_type (str): The service type (e.g., 'rosapi/Topics')
        request (dict): Service request data as a dictionary
        timeout (Optional[float]): Timeout in seconds. If None, uses the default timeout.

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


if __name__ == "__main__":
    mcp.run(transport="stdio")
