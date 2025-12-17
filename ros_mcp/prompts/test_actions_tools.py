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
        return """# Testing ROS Action Tools - Detailed Guide

This is a detailed guide for testing action tools. For a quick overview of all ROS MCP Server tools, see `test-server-tools`.

## When to Use This Guide

Use this detailed guide when:
- The main action tools from `test-server-tools` are not working
- You need step-by-step instructions for each action tool
- You need troubleshooting help for specific action tool issues
- You want to understand action tool details and advanced usage
- You need to test the actions details resource

For a quick high-level overview, see `test-server-tools`.

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

**Testing the resource:**

1. **Access the resource** through your MCP client:
   - Resource URI: `ros-mcp://ros-metadata/actions/all`
   - This will return a JSON string with all action information

2. **Compare with individual tool calls:**
   ```
   # Get actions list
   get_actions()
   
   # Get details for each action individually
   get_action_details('/turtle1/rotate_absolute')
   
   # Compare with resource output
   # Resource: ros-mcp://ros-metadata/actions/all
   ```

3. **Use the resource for system overview:**
   - The resource is more efficient for getting information about all actions at once
   - Useful for understanding the complete system architecture
   - Provides action types even when detailed structures aren't available

**Response includes:**
- `total_actions`: Total number of actions
- `actions`: Dictionary with details for each action
  - Each action entry contains:
    - `type`: The action type (e.g., "turtlesim/action/RotateAbsolute")
    - `status`: Status of the action ("available" or "type_unknown")
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

**When to use the resource vs individual tools:**
- **Use the resource** when you need a quick overview of all actions and their types
- **Use `get_action_details()`** when you need detailed goal/result/feedback structures for a specific action
- **Use `get_actions()`** when you just need a simple list of action names

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

## Related Guides

- **`test-server-tools`** - High-level overview of all ROS MCP Server tools
"""
