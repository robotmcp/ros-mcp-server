"""Topic tools testing prompt for ROS1 MCP."""


def register_test_topics_tools_prompts(mcp):
    """Register topic test prompt."""

    @mcp.prompt(name="test-topics-tools")
    def test_topics_tools() -> str:
        return """# Test Topic Tools (ROS1)

- List topics:
  - `get_topics()`
- Inspect topic details:
  - `get_topic_type('/turtle1/pose')`
  - `get_topic_details('/turtle1/pose')`
- Inspect message schema:
  - `get_message_details('turtlesim/Pose')`
- Subscribe once:
  - `subscribe_once(topic='/turtle1/pose', msg_type='turtlesim/Pose')`
- Subscribe for duration:
  - `subscribe_for_duration(topic='/turtle1/pose', msg_type='turtlesim/Pose', duration=5.0, max_messages=10)`
- Publish once:
  - `publish_once(topic='/turtle1/cmd_vel', msg_type='geometry_msgs/Twist', msg={'linear': {'x': 1.0}, 'angular': {'z': 0.5}})`
- Publish sequence:
  - `publish_for_durations(topic='/turtle1/cmd_vel', msg_type='geometry_msgs/Twist', messages=[{'linear': {'x': 1.0}}, {'linear': {'x': 0.0}}], durations=[1.0, 1.0])`

For image topics, set `expects_image='true'` then call `analyze_previously_received_image()`.
"""
