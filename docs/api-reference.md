# ROS MCP Server API Reference

This document provides a complete reference for all tools available in the ROS MCP Server. The server provides 31 tools organized into functional categories for interacting with ROS 1 and ROS 2 systems via rosbridge.

## Table of Contents

- [Connection Tools](#connection-tools)
- [Topic Tools](#topic-tools)
- [Service Tools](#service-tools)
- [Node Tools](#node-tools)
- [Parameter Tools](#parameter-tools)
- [Action Tools](#action-tools)
- [Image Tools](#image-tools)
- [Robot Configuration Tools](#robot-configuration-tools)

---

## Connection Tools

Tools for establishing and testing connections to ROS systems.

### connect_to_robot

Connect to a robot by setting the IP and port for the WebSocket connection, then testing connectivity.

**Parameters:**

| Name | Type | Default | Description |
|------|------|---------|-------------|
| `ip` | string | "127.0.0.1" | The IP address of the rosbridge server |
| `port` | int | 9090 | The port number of the rosbridge server |
| `ping_timeout` | float | 2.0 | Timeout for ping in seconds |
| `port_timeout` | float | 2.0 | Timeout for port check in seconds |

**Returns:** Connection status with ping and port check results.

**Example:**
```python
connect_to_robot(ip="192.168.1.100", port=9090)
```

---

### ping_robot

Ping a robot's IP address and check if a specific port is open.

**Parameters:**

| Name | Type | Default | Description |
|------|------|---------|-------------|
| `ip` | string | required | The IP address to ping |
| `port` | int | required | The port number to check |
| `ping_timeout` | float | 2.0 | Timeout for ping in seconds |
| `port_timeout` | float | 2.0 | Timeout for port check in seconds |

**Returns:** Dictionary with ping results, port status, and overall accessibility status.

**Example:**
```python
ping_robot(ip="192.168.1.100", port=9090)
```

---

## Topic Tools

Tools for discovering, subscribing to, and publishing on ROS topics.

### get_topics

Get list of all available ROS topics.

**Parameters:** None

**Returns:** Dictionary with `topics` list, `types` list, and `topic_count`.

**Example:**
```python
get_topics()
```

---

### get_topic_type

Get the message type for a specific topic.

**Parameters:**

| Name | Type | Default | Description |
|------|------|---------|-------------|
| `topic` | string | required | The topic name (e.g., "/cmd_vel") |

**Returns:** Dictionary with `topic` and `type` fields.

**Example:**
```python
get_topic_type("/turtle1/cmd_vel")
```

---

### get_topic_details

Get detailed information about a specific topic including its type, publishers, and subscribers.

**Parameters:**

| Name | Type | Default | Description |
|------|------|---------|-------------|
| `topic` | string | required | The topic name (e.g., "/cmd_vel") |

**Returns:** Dictionary with topic information including `type`, `publishers`, `subscribers`, and counts.

**Example:**
```python
get_topic_details("/turtle1/pose")
```

---

### get_message_details

Get the complete structure/definition of a message type.

**Parameters:**

| Name | Type | Default | Description |
|------|------|---------|-------------|
| `message_type` | string | required | The message type (e.g., "geometry_msgs/Twist") |

**Returns:** Dictionary with `message_type` and `structure` containing field definitions.

**Example:**
```python
get_message_details("geometry_msgs/Twist")
```

---

### subscribe_once

Subscribe to a ROS topic and return the first message received.

**Parameters:**

| Name | Type | Default | Description |
|------|------|---------|-------------|
| `topic` | string | required | The ROS topic name |
| `msg_type` | string | required | The ROS message type |
| `timeout` | float | 2.0 | Timeout in seconds |
| `queue_length` | int | 1 | Messages to buffer before dropping |
| `throttle_rate_ms` | int | 0 | Minimum interval between messages in ms |
| `expects_image` | string | "auto" | Hint for image parsing: "true", "false", or "auto" |

**Returns:** Dictionary with `msg` containing the received message.

**Example:**
```python
subscribe_once(topic="/turtle1/pose", msg_type="turtlesim/msg/Pose")
subscribe_once(topic="/camera/image_raw", msg_type="sensor_msgs/Image", expects_image="true")
```

---

### subscribe_for_duration

Subscribe to a topic for a duration and collect messages.

**Parameters:**

| Name | Type | Default | Description |
|------|------|---------|-------------|
| `topic` | string | required | The ROS topic name |
| `msg_type` | string | required | The ROS message type |
| `duration` | float | 5.0 | Duration to listen in seconds |
| `max_messages` | int | 100 | Maximum messages to collect |
| `queue_length` | int | 1 | Messages to buffer before dropping |
| `throttle_rate_ms` | int | 0 | Minimum interval between messages in ms |
| `expects_image` | string | "auto" | Hint for image parsing |

**Returns:** Dictionary with `topic`, `collected_count`, and `messages` list.

**Example:**
```python
subscribe_for_duration(topic="/turtle1/pose", msg_type="turtlesim/msg/Pose", duration=5, max_messages=10)
```

---

### publish_once

Publish a single message to a ROS topic.

**Parameters:**

| Name | Type | Default | Description |
|------|------|---------|-------------|
| `topic` | string | required | The ROS topic name |
| `msg_type` | string | required | The ROS message type |
| `msg` | dict | required | Message payload as a dictionary |

**Returns:** Dictionary with `success` status.

**Example:**
```python
publish_once(
    topic="/turtle1/cmd_vel",
    msg_type="geometry_msgs/msg/Twist",
    msg={"linear": {"x": 1.0, "y": 0.0, "z": 0.0}, "angular": {"x": 0.0, "y": 0.0, "z": 0.5}}
)
```

---

### publish_for_durations

Publish a sequence of messages with delays between them.

**Parameters:**

| Name | Type | Default | Description |
|------|------|---------|-------------|
| `topic` | string | required | The ROS topic name |
| `msg_type` | string | required | The ROS message type |
| `messages` | list[dict] | required | List of message dictionaries |
| `durations` | list[float] | required | List of delays in seconds |

**Returns:** Dictionary with `success`, `published_count`, and `total_messages`.

**Example:**
```python
publish_for_durations(
    topic="/turtle1/cmd_vel",
    msg_type="geometry_msgs/msg/Twist",
    messages=[{"linear": {"x": 1.0}}, {"linear": {"x": 0.0}}],
    durations=[1.0, 0.5]
)
```

---

## Service Tools

Tools for discovering and calling ROS services.

### get_services

Get list of all available ROS services.

**Parameters:** None

**Returns:** Dictionary with `services` list and `service_count`.

**Example:**
```python
get_services()
```

---

### get_service_type

Get the service type for a specific service.

**Parameters:**

| Name | Type | Default | Description |
|------|------|---------|-------------|
| `service` | string | required | The service name (e.g., "/rosapi/topics") |

**Returns:** Dictionary with `service` and `type` fields.

**Example:**
```python
get_service_type("/turtle1/teleport_absolute")
```

---

### get_service_details

Get complete service details including request/response structures and provider nodes.

**Parameters:**

| Name | Type | Default | Description |
|------|------|---------|-------------|
| `service` | string | required | The service name |

**Returns:** Dictionary with `service`, `type`, `request`, `response`, and `providers`.

**Example:**
```python
get_service_details("/turtle1/teleport_absolute")
```

---

### call_service

Call a ROS service with specified request data.

**Parameters:**

| Name | Type | Default | Description |
|------|------|---------|-------------|
| `service_name` | string | required | The service name |
| `service_type` | string | required | The service type |
| `request` | dict | required | Service request data |
| `timeout` | float | 2.0 | Timeout in seconds |

**Returns:** Dictionary with `service`, `service_type`, `success`, and `result`.

**Example:**
```python
call_service(
    service_name="/turtle1/teleport_absolute",
    service_type="turtlesim/srv/TeleportAbsolute",
    request={"x": 5.0, "y": 5.0, "theta": 0.0}
)
```

---

## Node Tools

Tools for discovering and inspecting ROS nodes.

### get_nodes

Get list of all currently running ROS nodes.

**Parameters:** None

**Returns:** Dictionary with `nodes` list and `node_count`.

**Example:**
```python
get_nodes()
```

---

### get_node_details

Get detailed information about a specific node including its publishers, subscribers, and services.

**Parameters:**

| Name | Type | Default | Description |
|------|------|---------|-------------|
| `node` | string | required | The node name (e.g., "/turtlesim") |

**Returns:** Dictionary with `node`, `publishers`, `subscribers`, `services`, and counts.

**Example:**
```python
get_node_details("/turtlesim")
```

---

## Parameter Tools

Tools for managing ROS 2 parameters. **Note: These tools work only with ROS 2.**

### get_parameter

Get a single ROS parameter value by name.

**Parameters:**

| Name | Type | Default | Description |
|------|------|---------|-------------|
| `name` | string | required | The parameter name (e.g., "/turtlesim:background_b") |

**Returns:** Dictionary with `name`, `value`, `successful`, and `reason`.

**Example:**
```python
get_parameter("/turtlesim:background_b")
```

---

### set_parameter

Set a single ROS parameter value.

**Parameters:**

| Name | Type | Default | Description |
|------|------|---------|-------------|
| `name` | string | required | The parameter name |
| `value` | string | required | The parameter value to set |

**Returns:** Dictionary with `name`, `value`, `successful`, and `reason`.

**Example:**
```python
set_parameter("/turtlesim:background_b", "255")
```

---

### has_parameter

Check if a ROS parameter exists.

**Parameters:**

| Name | Type | Default | Description |
|------|------|---------|-------------|
| `name` | string | required | The parameter name |

**Returns:** Dictionary with `name`, `exists`, `successful`, and `reason`.

**Example:**
```python
has_parameter("/turtlesim:background_b")
```

---

### delete_parameter

Delete a ROS parameter.

**Parameters:**

| Name | Type | Default | Description |
|------|------|---------|-------------|
| `name` | string | required | The parameter name |

**Returns:** Dictionary with `name`, `successful`, and `reason`.

**Example:**
```python
delete_parameter("/turtlesim:background_b")
```

---

### get_parameters

Get list of all ROS parameter names for a specific node.

**Parameters:**

| Name | Type | Default | Description |
|------|------|---------|-------------|
| `node_name` | string | required | The node name (e.g., "/turtlesim") |

**Returns:** Dictionary with `node`, `parameters` list, and `parameter_count`.

**Example:**
```python
get_parameters("/turtlesim")
```

---

### get_parameter_details

Get comprehensive details about a specific ROS parameter including value, type, and metadata.

**Parameters:**

| Name | Type | Default | Description |
|------|------|---------|-------------|
| `name` | string | required | The parameter name |

**Returns:** Dictionary with `name`, `value`, `type`, `exists`, `description`, `node`, and `parameter`.

**Example:**
```python
get_parameter_details("/turtlesim:background_r")
```

---

## Action Tools

Tools for interacting with ROS 2 action servers. **Note: These tools work only with ROS 2.**

### get_actions

Get list of all available ROS actions.

**Parameters:** None

**Returns:** Dictionary with `actions` list and `action_count`.

**Example:**
```python
get_actions()
```

---

### get_action_details

Get complete action details including type, goal, result, and feedback structures.

**Parameters:**

| Name | Type | Default | Description |
|------|------|---------|-------------|
| `action` | string | required | The action name (e.g., "/turtle1/rotate_absolute") |

**Returns:** Dictionary with `action`, `action_type`, `goal`, `result`, and `feedback` structures.

**Example:**
```python
get_action_details("/turtle1/rotate_absolute")
```

---

### get_action_status

Get action status for a specific action name.

**Parameters:**

| Name | Type | Default | Description |
|------|------|---------|-------------|
| `action_name` | string | required | The action name |

**Returns:** Dictionary with `action_name`, `success`, `active_goals`, and `goal_count`.

**Example:**
```python
get_action_status("/turtle1/rotate_absolute")
```

---

### send_action_goal

Send a goal to a ROS action server.

**Parameters:**

| Name | Type | Default | Description |
|------|------|---------|-------------|
| `action_name` | string | required | The action name |
| `action_type` | string | required | The action type |
| `goal` | dict | required | The goal message |
| `timeout` | float | 2.0 | Timeout for action completion in seconds |

**Returns:** Dictionary with `action`, `action_type`, `success`, `goal_id`, `status`, and `result`.

**Example:**
```python
send_action_goal(
    action_name="/turtle1/rotate_absolute",
    action_type="turtlesim/action/RotateAbsolute",
    goal={"theta": 1.57}
)
```

---

### cancel_action_goal

Cancel a specific action goal.

**Parameters:**

| Name | Type | Default | Description |
|------|------|---------|-------------|
| `action_name` | string | required | The action name |
| `goal_id` | string | required | The goal ID to cancel |

**Returns:** Dictionary with `action`, `goal_id`, `success`, and `note`.

**Example:**
```python
cancel_action_goal("/turtle1/rotate_absolute", "goal_1758653551839_21acd486")
```

---

## Image Tools

Tools for handling ROS image messages.

### analyze_previously_received_image

Analyze a previously received image that was saved by any ROS operation.

**Parameters:**

| Name | Type | Default | Description |
|------|------|---------|-------------|
| `image_path` | string | "./camera/received_image.jpeg" | Path to the saved image file |

**Returns:** ImageContent object for LLM analysis, or error dictionary.

**Example:**
```python
analyze_previously_received_image()
analyze_previously_received_image(image_path="./camera/custom_image.jpeg")
```

---

## Robot Configuration Tools

Tools for managing robot specifications and detecting ROS versions.

### get_verified_robot_spec

Load specifications and usage context for a verified robot model.

**Parameters:**

| Name | Type | Default | Description |
|------|------|---------|-------------|
| `name` | string | required | The exact robot model name from the verified list |

**Returns:** Dictionary with `robot_config` containing type, prompts, and context.

**Example:**
```python
get_verified_robot_spec("unitree_go2")
```

---

### get_verified_robots_list

List pre-verified robot models that have specification files available.

**Parameters:** None

**Returns:** Dictionary with `robot_specifications` list and `count`.

**Example:**
```python
get_verified_robots_list()
```

---

### detect_ros_version

Detect the ROS version and distribution via rosbridge.

**Parameters:** None

**Returns:** Dictionary with `version` and `distro`, or `error`.

**Example:**
```python
detect_ros_version()
# Returns: {"version": "2", "distro": "humble"}
```

---

## Error Handling

All tools follow a consistent error handling pattern:

- **Success:** Returns a dictionary with the requested data
- **Error:** Returns a dictionary with an `error` key containing the error message
- **Warning:** Returns a dictionary with a `warning` key for non-fatal issues

Example error response:
```python
{"error": "Topic /nonexistent does not exist or has no type"}
```

Example warning response:
```python
{"warning": "No topics found"}
```

---

## Timeouts

Most tools use a default timeout of 2 seconds, which can be overridden. For slow operations or unreliable networks, increase the timeout:

```python
subscribe_once(topic="/slow_topic", msg_type="std_msgs/String", timeout=10.0)
call_service(service_name="/slow_service", service_type="std_srvs/Empty", request={}, timeout=30.0)
```

---

## ROS 1 vs ROS 2 Compatibility

| Tool Category | ROS 1 | ROS 2 |
|---------------|-------|-------|
| Connection | ✓ | ✓ |
| Topics | ✓ | ✓ |
| Services | ✓ | ✓ |
| Nodes | ✓ | ✓ |
| Parameters | ✗ | ✓ |
| Actions | ✗ | ✓ |
| Images | ✓ | ✓ |
| Robot Config | ✓ | ✓ |

Use `detect_ros_version()` to check which version is running before using ROS 2-only features.
