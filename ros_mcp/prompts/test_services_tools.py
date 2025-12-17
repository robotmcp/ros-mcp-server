"""Test service tools prompts for ROS MCP Server."""


def register_test_services_tools_prompts(mcp):
    """Register test service tools prompts with the MCP server."""

    @mcp.prompt(name="test-services-tools")
    def test_services_tools() -> str:
        """
        Guide users on how to test and explore the ROS service tools.

        This prompt provides step-by-step instructions for testing service operations,
        including getting service lists, service types, service details, and calling services.

        Returns:
            str: Comprehensive guide for testing service tools
        """
        return """# Testing ROS Service Tools - Detailed Guide

This is a detailed guide for testing service tools. For a quick overview of all ROS MCP Server tools, see `test-server-tools`.

## When to Use This Guide

Use this detailed guide when:
- The main service tools from `test-server-tools` are not working
- You need step-by-step instructions for each service tool
- You need troubleshooting help for specific service tool issues
- You want to understand service tool details and advanced usage
- You need to test service resources or advanced features

For a quick high-level overview, see `test-server-tools`.

## Prerequisites

Before testing service tools, ensure you have:

1. **Active ROS connection** - Connect to a ROS system first:
   ```
   connect_to_robot(ip='127.0.0.1', port=9090)
   ```

2. **Running ROS services** - Make sure you have some services available in your ROS system.
   Common services include:
   - `/rosapi/topics` - Get list of topics
   - `/rosapi/services` - Get list of services
   - `/rosapi/nodes` - Get list of nodes
   - `/clear` - Clear turtlesim screen (if turtlesim is running)
   - `/reset` - Reset turtlesim (if turtlesim is running)

## Service Tools Overview

The ROS MCP Server provides the following service tools:

1. **get_services()** - Get list of all available ROS services
2. **get_service_type(service)** - Get the service type for a specific service
3. **get_service_details(service)** - Get complete service details including request/response structures and provider nodes
4. **call_service(service_name, service_type, request, timeout)** - Call a ROS service with specified request data

Additionally, comprehensive information about all services is available as a resource:
- **ros-mcp://ros-metadata/services/all** - Get detailed information about all services (types, providers)

## Step 1: Get List of All Services

Start by discovering what services are available in your ROS system:

```
get_services()
```

This will return:
- `services`: List of all available service names
- `service_count`: Total number of services

**Example:**
```
get_services()
```

**Expected Response:**
```json
{
  "services": ["/rosapi/topics", "/rosapi/services", "/rosapi/nodes", "/clear"],
  "service_count": 4
}
```

## Step 2: Get Service Type

Get the type of a specific service:

```
get_service_type('/service_name')
```

**Examples:**
```
get_service_type('/rosapi/topics')
get_service_type('/clear')
get_service_type('/rosapi/services')
```

**Response includes:**
- `service`: The service name
- `type`: The service type (e.g., 'rosapi/Topics', 'std_srvs/Empty')

**Example Response:**
```json
{
  "service": "/rosapi/topics",
  "type": "rosapi/Topics"
}
```

## Step 3: Get Service Details

Get complete information about a service, including request/response structures and provider nodes:

```
get_service_details('/service_name')
```

**Examples:**
```
get_service_details('/rosapi/topics')
get_service_details('/clear')
get_service_details('/turtle1/teleport_absolute')
```

**Response includes:**
- `service`: The service name
- `type`: The service type
- `request`: Request structure with fields and types
- `response`: Response structure with fields and types
- `providers`: List of nodes that provide this service
- `provider_count`: Number of provider nodes
- `note`: Important information about field name formatting

**Example Response:**
```json
{
  "service": "/rosapi/topics",
  "type": "rosapi_msgs/srv/Topics",
  "request": {
    "fields": {},
    "field_count": 0
  },
  "response": {
    "fields": {
      "topics": "string",
      "types": "string"
    },
    "field_count": 2
  },
  "providers": ["/rosapi"],
  "provider_count": 1,
  "note": "Field names shown above are formatted for rosbridge (leading underscores removed). Use these exact field names when calling call_service()."
}
```

## Step 4: Get All Services Details (Resource)

Get comprehensive information about all services at once using the resource:

**Resource URI:** `ros-mcp://ros-metadata/services/all`

**Note:** This may take time to execute when there are a large number of services since it queries each one by one.

**How to access:**
The resource can be accessed through the MCP resource interface. It returns a JSON string with comprehensive service information.

**Response includes:**
- `total_services`: Total number of services
- `services`: Dictionary with details for each service
- `service_errors`: List of any errors encountered (if any)

**Example Response:**
```json
{
  "total_services": 3,
  "services": {
    "/rosapi/topics": {
      "type": "rosapi/Topics",
      "providers": ["/rosapi"],
      "provider_count": 1
    },
    "/clear": {
      "type": "std_srvs/Empty",
      "providers": ["/turtlesim"],
      "provider_count": 1
    }
  },
  "service_errors": []
}
```

## Step 6: Call a Service

Call a ROS service with specified request data:

```
call_service(service_name, service_type, request, timeout)
```

**Parameters:**
- `service_name` (str): The service name (e.g., '/rosapi/topics')
- `service_type` (str): The service type (e.g., 'rosapi/Topics')
- `request` (dict): Service request data as a dictionary
- `timeout` (float, optional): Timeout in seconds (only specify for slow services)

**IMPORTANT:** Field names in the request dict should match the field names shown by `get_service_details()`, which are already formatted for rosbridge (without leading underscores).

**Examples:**

1. **Call a service with no parameters:**
   ```
   call_service('/rosapi/topics', 'rosapi/Topics', {})
   ```

2. **Call a service with parameters:**
   ```
   call_service('/rosapi/topic_type', 'rosapi/TopicType', {'topic': '/cmd_vel'})
   ```

3. **Call a service with timeout (for slow services):**
   ```
   call_service('/slow_service', 'my_package/SlowService', {}, timeout=10.0)
   ```

4. **Call turtlesim clear service:**
   ```
   call_service('/clear', 'std_srvs/Empty', {})
   ```

**Response includes:**
- `service`: The service name
- `service_type`: The service type
- `success`: Whether the call was successful
- `result`: Service response data (if successful)
- `error`: Error message (if failed)

**Example Response:**
```json
{
  "service": "/rosapi/topics",
  "service_type": "rosapi/Topics",
  "success": true,
  "result": {
    "topics": ["/cmd_vel", "/rosout"],
    "types": ["geometry_msgs/Twist", "rosgraph_msgs/Log"]
  }
}
```

## Service Naming Convention

ROS services use the format: `/service_name`

- Service names always start with `/`
- Service names are case-sensitive
- Common service patterns:
  - `/rosapi/*` - ROS API services
  - `/node_name/service_name` - Node-specific services
  - `/turtle1/*` - Turtlesim services (if turtlesim is running)


## Troubleshooting

### "No services found" or Empty Service List

**Problem:** `get_services()` returns no services or a warning

**Solutions:**
- Verify ROS connection: `connect_to_robot()`
- Check if ROS system is running: `detect_ros_version()`
- Ensure services are actually available in your ROS system
- Some services may be node-specific and only available when nodes are running

### "Service not found" Error

**Problem:** `get_service_type()` or `get_service_details()` returns "Service not found"

**Solutions:**
- Verify the service name is correct (case-sensitive)
- Check if the service is actually available: `get_services()`
- Ensure service name starts with `/`
- Service might have stopped - check again with `get_services()`

### "Service call failed" Error

**Problem:** `call_service()` returns an error

**Solutions:**
- Verify the service name and type are correct
- Check the request structure matches what `get_service_details()` shows
- Ensure field names don't have leading underscores (rosbridge format)
- Verify the service is actually running and available
- Check if the service requires specific parameters
- Try getting service details first to understand the expected request format

### "Service type not found" Error

**Problem:** `get_service_details()` returns "Service type not found"

**Solutions:**
- Verify the service type is correct
- Get the service type first: `get_service_type('/service_name')`
- Ensure the service type format is correct (e.g., 'rosapi/Topics' not '/rosapi/Topics')

### Wrong Request Format

**Problem:** Service call fails due to incorrect request format

**Solutions:**
- Always use `get_service_details()` first to see the expected structure
- Field names should NOT have leading underscores (rosbridge format)
- Use the exact field names shown in `get_service_details()`
- Check data types match what the service expects
- Example: Use `{'topic': '/image'}` not `{'_topic': '/image'}`

### Timeout Errors

**Problem:** Service call times out

**Solutions:**
- Some services are slow - specify a timeout: `call_service(..., timeout=10.0)`
- Check if the service is actually running and responsive
- Verify the service isn't blocked or waiting for something
- Increase the timeout value if the service is known to be slow

## Tips

- **Start with `get_services()`** - Always start by discovering what services are available
- **Use `get_service_details()` before calling** - Understand the request/response structure and which node provides the service
- **Field names matter** - Use the exact field names from `get_service_details()` (no leading underscores)
- **Service names are case-sensitive** - `/Service` is different from `/service`
- **Use the resource `ros-mcp://ros-metadata/services/all` for complete overview** - Provides comprehensive information about all services
- **`get_service_details()` includes providers** - No need for a separate call to find which node provides a service
- **Test with simple services first** - Start with services that have no parameters (like `/clear`)
- **Handle timeouts** - Specify timeout for services that might be slow

## Related Guides

- **`test-server-tools`** - High-level overview of all ROS MCP Server tools
"""
