"""Test topic tools prompts for ROS MCP Server."""


def register_test_topics_tools_prompts(mcp):
    """Register test topic tools prompts with the MCP server."""

    @mcp.prompt(name="test-topics-tools")
    def test_topics_tools() -> str:
        """
        Guide users on how to test and explore the ROS topic tools.

        This prompt provides step-by-step instructions for testing topic operations,
        including getting topic lists, topic types, topic details, subscribing, and publishing.

        Returns:
            str: Comprehensive guide for testing topic tools
        """
        return """# Testing ROS Topic Tools

This guide will help you test and explore the topic tools available in the ROS MCP Server.
These tools allow you to discover, inspect, subscribe to, and publish ROS topics.

## Prerequisites

Before testing topic tools, ensure you have:

1. **Active ROS connection** - Connect to a ROS system first:
   ```
   connect_to_robot(ip='127.0.0.1', port=9090)
   ```

2. **Running ROS topics** - Make sure you have some topics available in your ROS system.
   Common topics include:
   - `/cmd_vel` - Velocity commands (geometry_msgs/Twist)
   - `/turtle1/pose` - Turtle position (turtlesim/Pose)
   - `/turtle1/cmd_vel` - Turtle velocity commands (geometry_msgs/Twist)
   - `/rosout` - ROS logging messages
   - `/image` - Camera images (sensor_msgs/Image)

## Topic Tools Overview

The ROS MCP Server provides the following topic tools:

1. **get_topics()** - Get list of all available ROS topics
2. **get_topic_type(topic)** - Get the message type for a specific topic
3. **get_topic_details(topic)** - Get detailed information about a topic including type, publishers, and subscribers
4. **get_message_details(message_type)** - Get the complete structure/definition of a message type
5. **subscribe_once(topic, msg_type, ...)** - Subscribe to a topic and return the first message received
6. **subscribe_for_duration(topic, msg_type, duration, ...)** - Subscribe to a topic for a duration and collect messages
7. **publish_once(topic, msg_type, msg)** - Publish a single message to a ROS topic
8. **publish_for_durations(topic, msg_type, messages, durations)** - Publish a sequence of messages with delays

Additionally, comprehensive information about all topics is available as a resource:
- **ros-mcp://ros-metadata/topics/all** - Get detailed information about all topics (types, publishers, subscribers)

## Step 1: Get List of All Topics

Start by discovering what topics are available in your ROS system:

```
get_topics()
```

This will return:
- `topics`: List of all available topic names
- `types`: List of message types for each topic
- `topic_count`: Total number of topics

**Example:**
```
get_topics()
```

**Expected Response:**
```json
{
  "topics": ["/cmd_vel", "/rosout", "/turtle1/pose"],
  "types": ["geometry_msgs/msg/Twist", "rcl_interfaces/msg/Log", "turtlesim/msg/Pose"],
  "topic_count": 3
}
```

## Step 2: Get Topic Type

Get the message type for a specific topic:

```
get_topic_type('/topic_name')
```

**Examples:**
```
get_topic_type('/cmd_vel')
get_topic_type('/turtle1/pose')
get_topic_type('/rosout')
```

**Response includes:**
- `topic`: The topic name
- `type`: The message type (e.g., 'geometry_msgs/msg/Twist')

**Example Response:**
```json
{
  "topic": "/cmd_vel",
  "type": "geometry_msgs/msg/Twist"
}
```

## Step 3: Get Topic Details

Get detailed information about a topic, including its type, publishers, and subscribers:

```
get_topic_details('/topic_name')
```

**Examples:**
```
get_topic_details('/cmd_vel')
get_topic_details('/turtle1/pose')
get_topic_details('/rosout')
```

**Response includes:**
- `topic`: The topic name
- `type`: The message type
- `publishers`: List of nodes that publish to this topic
- `subscribers`: List of nodes that subscribe to this topic
- `publisher_count`: Number of publishers
- `subscriber_count`: Number of subscribers

**Example Response:**
```json
{
  "topic": "/cmd_vel",
  "type": "geometry_msgs/msg/Twist",
  "publishers": ["/teleop_turtle"],
  "subscribers": ["/turtlesim"],
  "publisher_count": 1,
  "subscriber_count": 1
}
```

## Step 4: Get Message Details

Get the complete structure/definition of a message type:

```
get_message_details('message_type')
```

**Examples:**
```
get_message_details('geometry_msgs/msg/Twist')
get_message_details('turtlesim/msg/Pose')
get_message_details('std_msgs/msg/String')
```

**Response includes:**
- `message_type`: The message type
- `structure`: Dictionary with field names and types

**Example Response:**
```json
{
  "message_type": "geometry_msgs/msg/Twist",
  "structure": {
    "geometry_msgs/msg/Twist": {
      "fields": {
        "linear": "geometry_msgs/msg/Vector3",
        "angular": "geometry_msgs/msg/Vector3"
      },
      "field_count": 2
    }
  }
}
```

## Step 5: Get All Topics Details (Resource)

Get comprehensive information about all topics at once using the resource:

**Resource URI:** `ros-mcp://ros-metadata/topics/all`

**Note:** This may take time to execute when there are a large number of topics since it queries each one by one.

**How to access:**
The resource can be accessed through the MCP resource interface. It returns a JSON string with comprehensive topic information.

**Response includes:**
- `total_topics`: Total number of topics
- `topics`: Dictionary with details for each topic
- `topic_errors`: List of any errors encountered (if any)

## Step 6: Subscribe to a Topic (Once)

Subscribe to a topic and return the first message received:

```
subscribe_once(topic='/topic_name', msg_type='message_type', ...)
```

**Parameters:**
- `topic` (str): The topic name (e.g., '/cmd_vel')
- `msg_type` (str): The message type (e.g., 'geometry_msgs/msg/Twist')
- `expects_image` (str, optional): 'auto', 'true', or 'false' - hint for image processing
- `timeout` (float, optional): Timeout in seconds (default: 5.0)
- `queue_length` (int, optional): Message queue length
- `throttle_rate_ms` (int, optional): Throttle rate in milliseconds

**Examples:**

1. **Basic subscription:**
   ```
   subscribe_once(topic='/turtle1/pose', msg_type='turtlesim/msg/Pose')
   ```

2. **With timeout:**
   ```
   subscribe_once(topic='/slow_topic', msg_type='my_package/SlowMsg', timeout=10.0)
   ```

3. **For image topics:**
   ```
   subscribe_once(topic='/camera/image_raw', msg_type='sensor_msgs/msg/Image', expects_image='true')
   ```

4. **With rate control:**
   ```
   subscribe_once(topic='/high_rate_topic', msg_type='sensor_msgs/msg/Image', queue_length=5, throttle_rate_ms=100)
   ```

**Response:**
- For regular messages: Returns the message data
- For image messages: Returns a message indicating the image was saved, use `analyze_previously_received_image()` to analyze it

## Step 7: Subscribe to a Topic (For Duration)

Subscribe to a topic for a fixed duration and collect messages:

```
subscribe_for_duration(topic='/topic_name', msg_type='message_type', duration=5.0, ...)
```

**Parameters:**
- `topic` (str): The topic name
- `msg_type` (str): The message type
- `duration` (float): Duration in seconds (default: 5.0)
- `max_messages` (int): Maximum number of messages to collect (default: 100)
- `expects_image` (str, optional): 'auto', 'true', or 'false'
- `queue_length` (int, optional): Message queue length
- `throttle_rate_ms` (int, optional): Throttle rate in milliseconds

**Examples:**

1. **Basic subscription for 5 seconds:**
   ```
   subscribe_for_duration(topic='/cmd_vel', msg_type='geometry_msgs/msg/Twist', duration=5.0)
   ```

2. **Collect up to 10 messages:**
   ```
   subscribe_for_duration(topic='/turtle1/pose', msg_type='turtlesim/msg/Pose', duration=10.0, max_messages=10)
   ```

3. **For image topics:**
   ```
   subscribe_for_duration(topic='/camera/image_raw', msg_type='sensor_msgs/msg/Image', duration=5.0, expects_image='true')
   ```

**Response includes:**
- `topic`: The topic name
- `collected_count`: Number of messages collected
- `messages`: List of collected messages
- `status_errors`: List of any errors encountered

## Step 8: Publish a Single Message

Publish a single message to a ROS topic:

```
publish_once(topic='/topic_name', msg_type='message_type', msg={...})
```

**Parameters:**
- `topic` (str): ROS topic name (e.g., '/cmd_vel')
- `msg_type` (str): ROS message type (e.g., 'geometry_msgs/msg/Twist')
- `msg` (dict): Message payload as a dictionary

**Examples:**

1. **Publish velocity command:**
   ```
   publish_once(topic='/cmd_vel', msg_type='geometry_msgs/msg/Twist', msg={'linear': {'x': 1.0}, 'angular': {'z': 0.5}})
   ```

2. **Publish string message:**
   ```
   publish_once(topic='/chatter', msg_type='std_msgs/msg/String', msg={'data': 'Hello, ROS!'})
   ```

**Response:**
- `success`: True if published successfully
- `error`: Error message if failed

## Step 9: Publish Multiple Messages with Delays

Publish a sequence of messages with delays between them:

```
publish_for_durations(topic='/topic_name', msg_type='message_type', messages=[...], durations=[...])
```

**Parameters:**
- `topic` (str): ROS topic name
- `msg_type` (str): ROS message type
- `messages` (list[dict]): List of message dictionaries
- `durations` (list[float]): List of durations (seconds) to wait between messages

**Example:**
```
publish_for_durations(
    topic='/cmd_vel',
    msg_type='geometry_msgs/msg/Twist',
    messages=[
        {'linear': {'x': 1.0}, 'angular': {'z': 0.0}},
        {'linear': {'x': 0.0}, 'angular': {'z': 0.0}}
    ],
    durations=[2.0, 1.0]
)
```

This publishes the first message, waits 2 seconds, publishes the second message, then waits 1 second.

**Response includes:**
- `success`: True if published successfully
- `published_count`: Number of messages successfully published
- `total_messages`: Total number of messages attempted
- `errors`: List of any errors encountered

## Topic Naming Convention

ROS topics use the format: `/topic_name`

- Topic names always start with `/`
- Topic names are case-sensitive
- Common topic patterns:
  - `/cmd_vel` - Velocity commands
  - `/node_name/topic_name` - Node-specific topics
  - `/turtle1/*` - Turtlesim topics (if turtlesim is running)

## Common Use Cases

### Use Case 1: Discover Available Topics

```
get_topics()
```

This is often the first step to understand what topics are available.

### Use Case 2: Understand a Topic Before Subscribing/Publishing

1. Get topic type:
   ```
   get_topic_type('/topic_name')
   ```

2. Get topic details:
   ```
   get_topic_details('/topic_name')
   ```

3. Get message structure:
   ```
   get_message_details('message_type')
   ```

### Use Case 3: Monitor a Topic

```
subscribe_for_duration(topic='/topic_name', msg_type='message_type', duration=10.0)
```

This collects messages from a topic for monitoring or analysis.

### Use Case 4: Send Commands to a Robot

```
publish_once(topic='/cmd_vel', msg_type='geometry_msgs/msg/Twist', msg={'linear': {'x': 1.0}})
```

This sends a velocity command to move a robot forward.

### Use Case 5: Get Complete System Overview

**Access the resource:** `ros-mcp://ros-metadata/topics/all`

This provides a comprehensive view of all topics and their connections.

## Testing Checklist

- [ ] Get list of all topics using `get_topics()`
- [ ] Get topic type for a specific topic using `get_topic_type('/topic_name')`
- [ ] Get topic details (including publishers and subscribers) using `get_topic_details('/topic_name')`
- [ ] Get message details using `get_message_details('message_type')`
- [ ] Access all topics details resource: `ros-mcp://ros-metadata/topics/all`
- [ ] Subscribe to a topic once using `subscribe_once()`
- [ ] Subscribe to a topic for duration using `subscribe_for_duration()`
- [ ] Publish a single message using `publish_once()`
- [ ] Publish multiple messages using `publish_for_durations()`
- [ ] Test with different message types
- [ ] Test with image topics (expects_image='true')

## Troubleshooting

### "No topics found" or Empty Topic List

**Problem:** `get_topics()` returns no topics or a warning

**Solutions:**
- Verify ROS connection: `connect_to_robot()`
- Check if ROS system is running: `detect_ros_version()`
- Ensure topics are actually being published in your ROS system
- Try launching some nodes that publish topics

### "Topic not found" Error

**Problem:** `get_topic_type()` or `get_topic_details()` returns "Topic not found"

**Solutions:**
- Verify the topic name is correct (case-sensitive)
- Check if the topic is actually available: `get_topics()`
- Ensure topic name starts with `/`
- Topic might have stopped publishing - check again with `get_topics()`

### "Service call failed" Error

**Problem:** Service call to get topic information fails

**Solutions:**
- Verify rosbridge connection is active
- Check if `/rosapi/topics` or `/rosapi/topic_type` services are available
- Try reconnecting: `connect_to_robot()`
- Check ROS system is responsive

### Subscription Timeout

**Problem:** `subscribe_once()` or `subscribe_for_duration()` times out

**Solutions:**
- Check if the topic is actually publishing: `get_topic_details('/topic_name')` (check publishers list)
- Increase the timeout value
- Verify the message type is correct
- Check if the topic is publishing at a very low rate

### No Messages Received

**Problem:** Subscription returns no messages

**Solutions:**
- Verify the topic is publishing: `get_topic_details('/topic_name')` (check publishers list)
- Check the message type matches: `get_topic_type('/topic_name')`
- Ensure the topic is active and publishing messages
- Try increasing duration or timeout

### Publish Errors

**Problem:** `publish_once()` or `publish_for_durations()` fails

**Solutions:**
- Verify the topic name is correct
- Check the message type matches what subscribers expect
- Ensure the message structure matches the message type definition
- Use `get_message_details()` to verify the correct structure
- Check if there are any subscribers (publishing to a topic with no subscribers is usually fine, but verify)

## Tips

- **Start with `get_topics()`** - Always start by discovering what topics are available
- **Use `get_topic_details()` for complete info** - Includes type, publishers, and subscribers in one call
- **Check message structure before publishing** - Use `get_message_details()` to understand the expected format
- **Topic names are case-sensitive** - `/Topic` is different from `/topic`
- **Use the resource `ros-mcp://ros-metadata/topics/all` for complete overview** - Provides comprehensive information about all topics
- **For image topics, use `expects_image='true'`** - Improves processing speed
- **Test subscriptions with short durations first** - Start with 1-2 seconds to verify it works
- **Verify publishers/subscribers** - Use `get_topic_details()` to see both publishers and subscribers in one call

## Integration with Other Tools

### With Node Tools

1. Get topic details: `get_topic_details('/topic_name')`
2. See which nodes publish/subscribe to the topic
3. Get node details: `get_node_details('/node_name')`
4. See what other topics the node uses

### With Service Tools

1. Some services can provide topic information
2. Use `call_service('/rosapi/topics', ...)` as an alternative to `get_topics()`

### With Parameter Tools (ROS 2)

1. Topics can have associated parameters
2. Use parameter tools to configure topic-related settings

## Example Workflow

1. **Discover topics:**
   ```
   get_topics()
   ```

2. **Get topic details:**
   ```
   get_topic_details('/cmd_vel')
   ```

3. **Understand message structure:**
   ```
   get_message_details('geometry_msgs/msg/Twist')
   ```

4. **Subscribe to monitor:**
   ```
   subscribe_for_duration(topic='/cmd_vel', msg_type='geometry_msgs/msg/Twist', duration=5.0)
   ```

5. **Publish commands:**
   ```
   publish_once(topic='/cmd_vel', msg_type='geometry_msgs/msg/Twist', msg={'linear': {'x': 1.0}})
   ```

## Testing Publish/Subscribe Workflows

### Test 1: Basic Publish and Subscribe

**Goal:** Publish a message and verify it can be received.

1. **Get topic information:**
   ```
   get_topic_details('/turtle1/cmd_vel')
   ```

2. **Publish a command:**
   ```
   publish_once(topic='/turtle1/cmd_vel', msg_type='geometry_msgs/msg/Twist', msg={'linear': {'x': 1.0}, 'angular': {'z': 0.0}})
   ```

3. **Subscribe to verify (if topic has subscribers):**
   ```
   subscribe_once(topic='/turtle1/cmd_vel', msg_type='geometry_msgs/msg/Twist', timeout=2.0)
   ```

### Test 2: Monitor a Publishing Topic

**Goal:** Subscribe to a topic that's actively publishing.

1. **Find a topic with publishers:**
   ```
   get_topic_details('/turtle1/pose')
   ```

2. **Subscribe to collect messages:**
   ```
   subscribe_for_duration(topic='/turtle1/pose', msg_type='turtlesim/msg/Pose', duration=3.0, max_messages=10)
   ```

3. **Analyze the collected messages** - Check the pose values, timestamps, etc.

### Test 3: Publish Sequence with Delays

**Goal:** Send a sequence of commands with timing.

1. **Get message structure:**
   ```
   get_message_details('geometry_msgs/msg/Twist')
   ```

2. **Publish a sequence:**
   ```
   publish_for_durations(
       topic='/turtle1/cmd_vel',
       msg_type='geometry_msgs/msg/Twist',
       messages=[
           {'linear': {'x': 1.0}, 'angular': {'z': 0.0}},  # Move forward
           {'linear': {'x': 0.0}, 'angular': {'z': 1.0}},  # Turn
           {'linear': {'x': 0.0}, 'angular': {'z': 0.0}}   # Stop
       ],
       durations=[2.0, 1.0, 0.5]
   )
   ```

### Test 4: Image Topic Subscription

**Goal:** Subscribe to an image topic and analyze it.

1. **Find image topics:**
   ```
   get_topics()
   # Look for topics with type 'sensor_msgs/msg/Image'
   ```

2. **Subscribe with image hint:**
   ```
   subscribe_once(topic='/image', msg_type='sensor_msgs/msg/Image', expects_image='true')
   ```

3. **Analyze the image:**
   ```
   analyze_previously_received_image()
   ```

### Test 5: High-Rate Topic with Throttling

**Goal:** Subscribe to a high-frequency topic without overwhelming the system.

1. **Subscribe with rate control:**
   ```
   subscribe_for_duration(
       topic='/high_rate_topic',
       msg_type='sensor_msgs/msg/Image',
       duration=5.0,
       queue_length=5,
       throttle_rate_ms=100,
       expects_image='true'
   )
   ```

This collects messages at a maximum rate of 10 Hz (100ms between messages).

### Test 6: End-to-End Robot Control

**Goal:** Control a robot by publishing commands and monitoring feedback.

1. **Discover control and feedback topics:**
   ```
   get_topics()
   get_topic_details('/cmd_vel')
   get_topic_details('/odom')  # or feedback topic
   ```

2. **Start monitoring feedback in parallel** (if possible):
   ```
   subscribe_for_duration(topic='/odom', msg_type='nav_msgs/msg/Odometry', duration=10.0)
   ```

3. **Send control commands:**
   ```
   publish_once(topic='/cmd_vel', msg_type='geometry_msgs/msg/Twist', msg={'linear': {'x': 0.5}, 'angular': {'z': 0.2}})
   ```

4. **Verify the robot responded** by checking the feedback messages.

## Related Tools

- **Node Tools:** `get_nodes()`, `get_node_details()` - Find which nodes publish/subscribe to topics
- **Service Tools:** `get_services()`, `call_service()` - Some services provide topic information
- **Parameter Tools:** `get_parameters()`, `set_parameter()` (ROS 2 only)
- **Connection Tools:** `connect_to_robot()`, `detect_ros_version()`
"""
