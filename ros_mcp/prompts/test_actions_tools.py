"""Test action tools prompts for ROS MCP Server."""


def register_test_actions_tools_prompts(mcp):
    """Register test action tools prompts with the MCP server."""

    @mcp.prompt(name="test-actions-tools")
    def test_actions_tools() -> str:
        """
        Guide users on how to test and explore the ROS action tools.

        This prompt provides step-by-step instructions for testing action operations,
        including getting action lists, action details, sending goals, and monitoring action status.

        Returns:
            str: Comprehensive guide for testing action tools
        """
        return """# Testing ROS Action Tools

This guide will help you test and explore the action tools available in the ROS MCP Server.
These tools allow you to discover, inspect, and interact with ROS actions (ROS 2 only).

## Prerequisites

Before testing action tools, ensure you have:

1. **Active ROS connection** - Connect to a ROS system first:
   ```
   connect_to_robot(ip='127.0.0.1', port=9090)
   ```

2. **ROS 2 system** - Actions are only available in ROS 2, not ROS 1

3. **Running ROS actions** - Make sure you have some actions available in your ROS system.
   Common actions include:
   - `/turtle1/rotate_absolute` - Rotate turtle to absolute angle (turtlesim)
   - `/fibonacci` - Fibonacci action server (if available)
   - `/navigate_to_pose` - Navigation action (if navigation stack is running)

## Action Tools Overview

The ROS MCP Server provides the following action tools:

1. **get_actions()** - Get list of all available ROS actions
2. **get_action_details(action)** - Get complete action details including type, goal, result, and feedback structures
3. **get_action_status(action_name)** - Get action status for a specific action name
4. **send_action_goal(action_name, action_type, goal, timeout)** - Send a goal to a ROS action server
5. **cancel_action_goal(action_name, goal_id)** - Cancel a specific action goal

Additionally, comprehensive information about all actions is available as a resource:
- **ros-mcp://ros-metadata/actions/all** - Get detailed information about all actions (types, status)

## Step 1: Get List of All Actions

Start by discovering what actions are available in your ROS system:

```
get_actions()
```

This will return:
- `actions`: List of all active action names
- `action_count`: Total number of actions

**Example:**
```
get_actions()
```

**Expected Response:**
```json
{
  "actions": ["/turtle1/rotate_absolute"],
  "action_count": 1
}
```

## Step 2: Get Details for a Specific Action

Get detailed information about a specific action, including its type, goal structure, result structure, and feedback structure:

```
get_action_details('/action_name')
```

**Examples:**
```
get_action_details('/turtle1/rotate_absolute')
get_action_details('/fibonacci')
```

**Response includes:**
- `action`: The action name
- `action_type`: The action type (e.g., "turtlesim/action/RotateAbsolute")
- `goal`: Goal message structure with fields, field_details, examples, and constants
- `result`: Result message structure with fields, field_details, examples, and constants
- `feedback`: Feedback message structure with fields, field_details, examples, and constants

**Example Response:**
```json
{
  "action": "/turtle1/rotate_absolute",
  "action_type": "turtlesim/action/RotateAbsolute",
  "goal": {
    "fields": {"theta": "float32"},
    "field_count": 1,
    "field_details": {
      "theta": {
        "type": "float32",
        "array_length": -1,
        "example": null
      }
    },
    "message_type": "turtlesim/action/RotateAbsolute_Goal",
    "examples": [],
    "constants": {}
  },
  "result": {
    "fields": {},
    "field_count": 0,
    "field_details": {},
    "message_type": "turtlesim/action/RotateAbsolute_Result",
    "examples": [],
    "constants": {}
  },
  "feedback": {
    "fields": {"remaining": "float32"},
    "field_count": 1,
    "field_details": {
      "remaining": {
        "type": "float32",
        "array_length": -1,
        "example": null
      }
    },
    "message_type": "turtlesim/action/RotateAbsolute_Feedback",
    "examples": [],
    "constants": {}
  }
}
```

## Step 3: Send an Action Goal

Send a goal to an action server. This will execute the action and return the result:

```
send_action_goal(action_name='/action_name', action_type='package/action/ActionType', goal={'field': value})
```

**Examples:**
```
# Rotate turtle to 90 degrees (1.57 radians)
send_action_goal(
    action_name='/turtle1/rotate_absolute',
    action_type='turtlesim/action/RotateAbsolute',
    goal={'theta': 1.57}
)

# Fibonacci action (if available)
send_action_goal(
    action_name='/fibonacci',
    action_type='action_tutorials_interfaces/action/Fibonacci',
    goal={'order': 10},
    timeout=30.0
)
```

**Response includes:**
- `action`: The action name
- `action_type`: The action type
- `success`: Whether the action completed successfully
- `goal_id`: Unique identifier for the goal
- `status`: Final status of the action
- `result`: Result message from the action (if successful)
- `error`: Error message (if failed)

**Example Response:**
```json
{
  "action": "/turtle1/rotate_absolute",
  "action_type": "turtlesim/action/RotateAbsolute",
  "success": true,
  "goal_id": "goal_1234567890_abcdef12",
  "status": 4,
  "result": {}
}
```

## Step 4: Get Action Status

Get the current status of an action, including active goals and their status. This is useful after sending a goal to check if it's still executing:

```
get_action_status('/action_name')
```

**Examples:**
```
get_action_status('/turtle1/rotate_absolute')
get_action_status('/fibonacci')
```

**Response includes:**
- `action_name`: The action name
- `success`: Whether the status query was successful
- `active_goals`: List of active goals with their status
- `goal_count`: Number of active goals
- Each goal includes:
  - `goal_id`: Unique identifier for the goal
  - `status`: Numeric status code
  - `status_text`: Human-readable status (e.g., "STATUS_EXECUTING")
  - `timestamp`: When the goal was created

**Example Response:**
```json
{
  "action_name": "/turtle1/rotate_absolute",
  "success": true,
  "active_goals": [
    {
      "goal_id": "goal_1234567890_abcdef12",
      "status": 2,
      "status_text": "STATUS_EXECUTING",
      "timestamp": "1234567890.123456789"
    }
  ],
  "goal_count": 1,
  "note": "Found 1 active goal(s) for action /turtle1/rotate_absolute"
}
```

## Step 5: Cancel an Action Goal

Cancel a running action goal:

```
cancel_action_goal(action_name='/action_name', goal_id='goal_id_string')
```

**Example:**
```
cancel_action_goal(
    action_name='/turtle1/rotate_absolute',
    goal_id='goal_1234567890_abcdef12'
)
```

**Response includes:**
- `action`: The action name
- `goal_id`: The goal ID that was cancelled
- `success`: Whether the cancel request was sent successfully
- `note`: Additional information

**Example Response:**
```json
{
  "action": "/turtle1/rotate_absolute",
  "goal_id": "goal_1234567890_abcdef12",
  "success": true,
  "note": "Cancel request sent successfully. Action may still be executing."
}
```

## Step 6: Get All Actions Details (Resource)

Get comprehensive information about all actions at once using the resource:

**Resource URI:** `ros-mcp://ros-metadata/actions/all`

This resource provides:
- Details for every action in the system
- Action types and status for each action
- Connection counts and statistics
- Any errors encountered during inspection

**How to access:**
The resource can be accessed through the MCP resource interface. It returns a JSON string with comprehensive action information.

**Response includes:**
- `total_actions`: Total number of actions
- `actions`: Dictionary with details for each action
- `action_errors`: List of any errors encountered (if any)

**Example Response:**
```json
{
  "total_actions": 1,
  "actions": {
    "/turtle1/rotate_absolute": {
      "type": "turtlesim/action/RotateAbsolute",
      "status": "available"
    }
  },
  "action_errors": []
}
```

## Action Naming Convention

ROS actions use the format: `/action_name`

- Action names always start with `/`
- Action names are case-sensitive
- Common actions include:
  - `/turtle1/rotate_absolute` - Turtlesim rotate action
  - `/fibonacci` - Fibonacci action server
  - `/navigate_to_pose` - Navigation action

## Action Status Codes

Action status codes indicate the current state of a goal:

- `0`: STATUS_UNKNOWN - Unknown status
- `1`: STATUS_ACCEPTED - Goal was accepted
- `2`: STATUS_EXECUTING - Goal is currently executing
- `3`: STATUS_CANCELING - Goal is being cancelled
- `4`: STATUS_SUCCEEDED - Goal completed successfully
- `5`: STATUS_CANCELED - Goal was cancelled
- `6`: STATUS_ABORTED - Goal execution was aborted

## Common Use Cases

### Use Case 1: Discover What Actions Are Available

```
get_actions()
```

This is often the first step to understand your ROS system.

### Use Case 2: Understand a Specific Action

When you want to know what an action does:

```
get_action_details('/turtle1/rotate_absolute')
```

This tells you:
- What the goal structure is (what you need to send)
- What the result structure is (what you'll get back)
- What the feedback structure is (progress updates during execution)

### Use Case 3: Execute an Action and Monitor Progress

Send a goal to execute an action, then check its status:

```
# Send the goal
send_action_goal(
    action_name='/turtle1/rotate_absolute',
    action_type='turtlesim/action/RotateAbsolute',
    goal={'theta': 1.57}
)

# Check the status after sending
get_action_status('/turtle1/rotate_absolute')
```

This workflow allows you to:
- Execute an action and get the result
- Monitor the action status to see if it's still running
- Get the goal_id from the send response to cancel if needed

### Use Case 5: Cancel a Running Action

If you need to stop an action that's currently executing:

```
cancel_action_goal(
    action_name='/turtle1/rotate_absolute',
    goal_id='goal_1234567890_abcdef12'
)
```

### Use Case 6: Get Complete System Overview

For a comprehensive view of all actions and their types:

**Access the resource:** `ros-mcp://ros-metadata/actions/all`

This is useful for:
- Understanding the complete system architecture
- Finding which actions are available
- Discovering action types across all actions

## Testing Checklist

- [ ] Get list of all actions using `get_actions()`
- [ ] Get details for a specific action using `get_action_details('/action_name')`
- [ ] Send an action goal using `send_action_goal()`
- [ ] Get action status using `get_action_status('/action_name')` after sending a goal
- [ ] Cancel an action goal using `cancel_action_goal()`
- [ ] Access all actions details resource: `ros-mcp://ros-metadata/actions/all`
- [ ] Test with different action names
- [ ] Verify goal, result, and feedback structures
- [ ] Test action execution with different goals
- [ ] Test action cancellation

## Troubleshooting

### "No actions found" or Empty Action List

**Problem:** `get_actions()` returns no actions or a warning

**Solutions:**
- Verify ROS connection: `connect_to_robot()`
- Check if ROS 2 system is running: `detect_ros_version()`
- Ensure actions are actually available in your ROS system
- Actions are ROS 2 only - they won't appear in ROS 1 systems
- Try launching some action servers: `ros2 run` with action servers

### "Action type not found" Error

**Problem:** `get_action_details()` returns "Action type not found"

**Solutions:**
- Verify the action name is correct (case-sensitive)
- Check if the action is actually running: `get_actions()`
- Ensure action name starts with `/`
- Action might have stopped running - check again with `get_actions()`
- Some actions may not expose type information through rosapi

### "Service call failed" Error

**Problem:** Service call to get action information fails

**Solutions:**
- Verify rosbridge connection is active
- Check if `/rosapi/action_servers` or other action services are available
- Try reconnecting: `connect_to_robot()`
- Check ROS system is responsive
- Some action services may not be available in all rosbridge versions

### "Action details not found" Error

**Problem:** Action type found but detailed structures are not available

**Solutions:**
- This is normal for some rosbridge/rosapi versions
- Action detail services (`/rosapi/action_*_details`) are not part of standard rosapi
- The action type will still be returned, but goal/result/feedback structures may be empty
- Consider subscribing to action topics directly for live message inspection

### Action Goal Timeout

**Problem:** `send_action_goal()` times out

**Solutions:**
- Increase the timeout parameter: `send_action_goal(..., timeout=30.0)`
- Check if the action server is actually running
- Verify the goal structure matches what the action expects
- Check action status: `get_action_status('/action_name')`
- Some actions may take longer to complete

### Action Goal Fails

**Problem:** `send_action_goal()` returns success=False

**Solutions:**
- Verify the action name is correct
- Verify the action type is correct
- Check the goal structure matches the action's goal message type
- Use `get_action_details()` to see the expected goal structure
- Check if the action server is running and accepting goals

## Tips

- **Start with `get_actions()`** - Always start by discovering what actions are available
- **Use `get_action_details()` for specific actions** - More efficient than getting all actions details
- **Use the resource `ros-mcp://ros-metadata/actions/all` for complete overview** - Provides comprehensive information about all actions
- **Action names are case-sensitive** - `/Turtle1/RotateAbsolute` is different from `/turtle1/rotate_absolute`
- **Actions can be added/removed dynamically** - Re-run `get_actions()` if you expect changes
- **Actions are ROS 2 only** - They won't work with ROS 1 systems
- **Use `get_action_status()` after sending a goal** - Check if actions are still executing after sending a goal
- **Goal IDs are unique** - Save the goal_id from `send_action_goal()` if you need to cancel it later
- **Timeout parameter is optional** - Default is 10 seconds, but you can specify longer for slow actions

## Integration with Other Tools

### With Topic Tools

1. Actions use topics internally for communication
2. Action status topic: `{action_name}/_action/status`
3. Action goal topic: `{action_name}/_action/goal`
4. Action result topic: `{action_name}/_action/result`
5. Action feedback topic: `{action_name}/_action/feedback`
6. Use topic tools to inspect these topics: `get_topic_details('{action_name}/_action/status')`

### With Service Tools

1. Actions are similar to services but with feedback
2. Use service tools to understand the difference
3. Services are one-shot, actions provide progress updates

### With Node Tools

1. Get node details: `get_node_details('/node_name')`
2. See what actions the node provides
3. Use action tools to interact with those actions

## Example Workflow

1. **Discover actions:**
   ```
   get_actions()
   ```

2. **Inspect a specific action:**
   ```
   get_action_details('/turtle1/rotate_absolute')
   ```

3. **Understand action structure:**
   - Check what the goal structure is
   - Check what the result structure is
   - Check what the feedback structure is

4. **Send a goal:**
   ```
   send_action_goal(
       action_name='/turtle1/rotate_absolute',
       action_type='turtlesim/action/RotateAbsolute',
       goal={'theta': 1.57}
   )
   ```

5. **Check status after sending (optional):**
   ```
   get_action_status('/turtle1/rotate_absolute')
   ```
   
   This will show you if there are any active goals still executing.

6. **Get complete system overview:**
   Access the resource: `ros-mcp://ros-metadata/actions/all`

7. **Use the information:**
   - Send goals to execute actions
   - Monitor action status
   - Cancel actions if needed

## Related Tools

- **Topic Tools:** `get_topics()`, `get_topic_details()`, `subscribe_once()`
- **Service Tools:** `get_services()`, `get_service_details()`, `call_service()`
- **Node Tools:** `get_nodes()`, `get_node_details()`
- **Connection Tools:** `connect_to_robot()`, `detect_ros_version()`
"""


