"""Test parameter tools prompts for ROS MCP Server."""


def register_test_parameters_tools_prompts(mcp):
    """Register test parameter tools prompts with the MCP server."""

    @mcp.prompt(name="test-parameters-tools")
    def test_parameters_tools() -> str:
        """
        Guide users on how to test and explore the ROS parameter tools.

        This prompt provides step-by-step instructions for testing parameter operations,
        including getting, setting, checking, and deleting parameters in ROS 2.

        Returns:
            str: Comprehensive guide for testing parameter tools
        """
        return """# Testing ROS Parameter Tools - Detailed Guide

This is a detailed guide for testing parameter tools. For a quick overview of all ROS MCP Server tools, see `test-server-tools`.

**Note: Parameter tools work only with ROS 2.**

## When to Use This Guide

Use this detailed guide when:
- The main parameter tools from `test-server-tools` are not working
- You need step-by-step instructions for each parameter tool
- You need troubleshooting help for specific parameter tool issues
- You want to understand parameter tool details and advanced usage
- You need to test parameter resources or advanced features

For a quick high-level overview, see `test-server-tools`.

## Prerequisites

Before testing parameter tools, ensure you have a working ROS 2 setup:

1. **Verify ROS 2 connection:**
   ```
   detect_ros_version()
   ```
   This should return ROS 2 (e.g., "humble", "foxy", "iron"). Parameter tools only work with ROS 2, not ROS 1.

2. **Check available nodes:**
   ```
   get_nodes()
   ```
   This lists all running nodes. You'll need node names to get their parameters. Common nodes include:
   - `/turtlesim` - Turtlesim simulator
   - `/cam2image` - Camera image publisher
   - `/rosbridge_websocket` - Rosbridge server

3. **Verify node services:**
   Each ROS 2 node should have a `/list_parameters` service. You can check if a service exists:
   ```
   get_services()
   ```
   Look for services like `/turtlesim/list_parameters` or `/cam2image/list_parameters`.

4. **Test basic connectivity:**
   If you can successfully call `get_nodes()` and `get_services()`, your connection is working and ready for parameter operations.
## Step 1: Get Parameters for a Node

Start by listing all available parameters for a specific node:

```
get_parameters('cam2image')
get_parameters('/turtlesim')
```

This will return a list of all parameter names for the specified node. The node name can be provided with or without a leading slash. The function uses the node-specific `/list_parameters` service which is more reliable than the global parameter service.

## Step 2: Check if a Parameter Exists

Before getting or setting a parameter, you can check if it exists:

```
has_parameter('/node_name:parameter_name')
```

Example:
```
has_parameter('/turtlesim:background_r')
```

## Step 3: Get a Single Parameter Value

Retrieve the value of a specific parameter:

```
get_parameter('/node_name:parameter_name')
```

Examples:
```
get_parameter('/turtlesim:background_r')
get_parameter('/turtlesim:background_g')
get_parameter('/turtlesim:background_b')
```

## Step 4: Get Detailed Parameter Information

Get comprehensive information about a parameter including its type and metadata:

```
get_parameter_details('/node_name:parameter_name')
```

Example:
```
get_parameter_details('/turtlesim:background_r')
```

This returns:
- Parameter name
- Current value
- Parameter type (int, string, bool, float, etc.)
- Whether it exists
- Description (if available)
- Node name and parameter name (parsed)

## Step 5: Set a Parameter Value

Modify a parameter value:

```
set_parameter('/node_name:parameter_name', 'value')
```

Examples:
```
set_parameter('/turtlesim:background_r', '255')
set_parameter('/turtlesim:background_g', '0')
set_parameter('/turtlesim:background_b', '0')
```

**Note:** Parameter values should be passed as strings, even for numeric types.

## Step 6: Get Parameters for Multiple Nodes

To get parameters for multiple nodes, call `get_parameters()` for each node:

```
get_parameters('cam2image')
get_parameters('turtlesim')
get_parameters('rosbridge_websocket')
```

Each call returns parameters formatted with the node prefix (e.g., `/cam2image:parameter_name`).

## Step 7: Delete a Parameter

Remove a parameter from the system:

```
delete_parameter('/node_name:parameter_name')
```

Example:
```
delete_parameter('/my_node:temp_parameter')
```

**Warning:** Be careful when deleting parameters as this may affect node behavior.

## Parameter Naming Convention

ROS 2 parameters use the format: `/node_name:parameter_name`

- The node name comes before the colon
- The parameter name comes after the colon
- Both parts are required

Examples:
- `/turtlesim:background_r` - parameter `background_r` in node `turtlesim`
- `/cam2image:use_sim_time` - parameter `use_sim_time` in node `cam2image`

## Common Parameter Types

Parameters can be of various types:
- **Integer**: `'42'`, `'0'`, `'-10'`
- **Float**: `'3.14'`, `'0.5'`, `'-1.0'`
- **Boolean**: `'true'`, `'false'`
- **String**: `'hello'`, `'world'`
- **Arrays**: `'[1, 2, 3]'` (passed as string representation)


## Troubleshooting

### "Service call failed" or timeout errors
- Ensure ROS 2 is running and the target node is running
- Check that you're connected to the correct ROS system
- Verify the node name is correct: `get_nodes()` to see available nodes
- The node must have a `/list_parameters` service (standard for ROS 2 nodes)

### "Parameter does not exist" errors
- Verify the parameter name format: `/node_name:parameter_name`
- Check that the node is running: `get_nodes()`
- Use `get_parameters('node_name')` to see all available parameters for that node

### Parameter value format issues
- Always pass parameter values as strings
- For boolean values, use `'true'` or `'false'` (lowercase strings)
- For arrays, pass as string representation: `'[1, 2, 3]'`

## Tips

- Use `get_parameters()` first to discover available parameters
- `get_parameter_details()` provides the most comprehensive information
- `inspect_all_parameters()` is useful for getting a complete snapshot but may be slow
- Parameter operations are ROS 2 only - they won't work with ROS 1
- Some parameters may be read-only and cannot be modified

## Related Guides

- **`test-server-tools`** - High-level overview of all ROS MCP Server tools
"""
