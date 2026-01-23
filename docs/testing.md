# Testing Guide for ROS MCP Server

This guide explains how to test the ROS MCP Server using prompts, resources, and automated tests.

## Running Automated Tests

The ROS MCP Server includes a comprehensive test suite with unit tests and end-to-end (E2E) tests.

### Test Structure

```
tests/
├── utils/              # Unit tests for utility modules
│   ├── test_config_utils.py
│   ├── test_network_utils.py
│   └── test_websocket.py
├── tools/              # Unit tests for tool modules
│   ├── test_actions.py
│   ├── test_images.py
│   ├── test_nodes.py
│   ├── test_parameters.py
│   └── test_robot_config.py
└── e2e/                # End-to-end tests (require Docker)
    ├── conftest.py     # Shared fixtures
    ├── test_e2e_topics.py
    ├── test_e2e_services.py
    ├── test_e2e_actions.py
    ├── test_e2e_nodes.py
    ├── test_e2e_parameters.py
    ├── test_e2e_prompts.py
    ├── test_e2e_resources.py
    ├── test_e2e_main.py
    ├── test_e2e_integration.py
    ├── test_e2e_error_handling.py
    ├── test_e2e_images.py
    └── test_e2e_robot_config.py
```

### Running Unit Tests

Unit tests can be run without any external dependencies:

```bash
# Run all unit tests
pytest tests/utils tests/tools -v

# Run with coverage report
pytest tests/utils tests/tools -v --cov=ros_mcp --cov-report=term-missing

# Run specific test file
pytest tests/tools/test_actions.py -v

# Run tests matching a pattern
pytest tests/ -k "test_get" -v
```

### Running E2E Tests

E2E tests require a ROS environment with turtlesim running in Docker. The test suite supports both ROS 1 (Noetic) and ROS 2 (Humble).

#### ROS 2 E2E Tests (Default)

```bash
# Start the ROS 2 environment
docker compose -f tests/e2e/docker-compose.e2e.yml up -d

# Wait for rosbridge to be ready (typically 10-30 seconds)
sleep 30

# Run E2E tests (default is ROS 2)
pytest tests/e2e/ -v -m e2e

# Run specific E2E test category
pytest tests/e2e/test_e2e_topics.py -v -m e2e

# Stop the Docker environment
docker compose -f tests/e2e/docker-compose.e2e.yml down
```

#### ROS 1 E2E Tests

```bash
# Start the ROS 1 environment (uses port 9091)
docker compose -f tests/e2e/docker-compose.ros1.yml up -d

# Wait for rosbridge to be ready
sleep 30

# Run E2E tests with ROS 1
pytest tests/e2e/ -v -m e2e --ros-version=1

# Run only tests compatible with ROS 1 (excludes ros2-only tests)
pytest tests/e2e/ -v -m "e2e and not ros2" --ros-version=1

# Stop the Docker environment
docker compose -f tests/e2e/docker-compose.ros1.yml down
```

#### Running Both ROS Versions

```bash
# Start both environments simultaneously
docker compose -f tests/e2e/docker-compose.e2e.yml up -d
docker compose -f tests/e2e/docker-compose.ros1.yml up -d

# Wait for both to be ready
sleep 30

# Run ROS 2 tests
pytest tests/e2e/ -v -m e2e --ros-version=2

# Run ROS 1 tests (excludes ROS 2-only tests)
pytest tests/e2e/ -v -m "e2e and not ros2" --ros-version=1

# Stop both environments
docker compose -f tests/e2e/docker-compose.e2e.yml down
docker compose -f tests/e2e/docker-compose.ros1.yml down
```

### Pytest Markers

The test suite uses the following markers:

- `@pytest.mark.e2e` - End-to-end tests requiring ROS environment
- `@pytest.mark.ros1` - Tests specific to ROS 1
- `@pytest.mark.ros2` - Tests specific to ROS 2 (e.g., actions, parameters)
- `@pytest.mark.asyncio` - Async tests using pytest-asyncio

Configure pytest in `pyproject.toml`:

```toml
[tool.pytest.ini_options]
markers = [
    "e2e: End-to-end tests requiring ROS environment",
    "ros1: Tests specific to ROS 1",
    "ros2: Tests specific to ROS 2",
]
asyncio_mode = "auto"
```

### Command Line Options

The test suite supports the following command line options:

- `--ros-version=1|2` - Specify ROS version to test against (default: 2)

### CI/CD

The GitHub Actions workflow automatically runs:
- Unit tests on every push and pull request
- E2E tests on every push and pull request (using Docker)
- Coverage reporting

See `.github/workflows/test.yml` for the full configuration.

---

## Prerequisites

Before testing, ensure you have:

1. **ROS installed** (ROS 1 or ROS 2)
   - ROS 2: `which ros2`
   - ROS 1: TODO

2. **Turtlesim package installed**
   - ROS 2: `ros2 pkg list | grep turtlesim`
   - ROS 1: TODO

3. **Rosbridge server installed**
   - ROS 2: `ros2 pkg list | grep rosbridge`
   - ROS 1: TODO

4. **MCP Server running**
   - The ROS MCP Server should be configured and running in your MCP client (e.g., Cursor, Claude)

## Setting Up the Test Environment

### Step 1: Start ROS Core (if not already running)

<!-- **For ROS 2:** -->
```bash
# Terminal 1: Start ROS 2 daemon 
ros2 daemon start
```

<!-- **For ROS 1:** -->
<!-- ```bash
# Terminal 1: Start roscore
roscore
``` -->

### Step 2: Start Turtlesim

<!-- **For ROS 2:** -->
```bash
# Terminal 2: Start turtlesim node
ros2 run turtlesim turtlesim_node
```

<!-- **For ROS 1:**
```bash
# Terminal 2: Start turtlesim node
rosrun turtlesim turtlesim_node
``` -->

### Step 3: Start Rosbridge

<!-- **For ROS 2:** -->
```bash
# Terminal 3: Start rosbridge WebSocket server
ros2 run rosbridge_server rosbridge_websocket
# or
ros2 launch rosbridge_server rosbridge_websocket_launch.xml
```

<!-- **For ROS 1:**
```bash
# Terminal 3: Start rosbridge WebSocket server
rosrun rosbridge_server rosbridge_websocket
``` -->

The rosbridge server will start on `ws://localhost:9090` by default.

## Using Prompts for Testing

Prompts are interactive guides that provide step-by-step instructions for testing specific tool categories. They are accessed through the MCP prompt interface.

### Available Test Prompts

1. **`test-server-tools`** - High-level overview of all ROS MCP Server tools
2. **`test-connection-tools`** - Connection and ROS version detection tools
3. **`test-topics-tools`** - Topic discovery, subscription, and publishing tools
4. **`test-services-tools`** - Service discovery and calling tools
5. **`test-nodes-tools`** - Node discovery and inspection tools
6. **`test-parameters-tools`** - Parameter tools (ROS 2 only)
7. **`test-actions-tools`** - Action tools (ROS 2 only)

### How to Use Prompts

1. **Access prompts through your MCP client:**
   - Use the prompt selector or command palette (if available) or simply prompt `test server tools`
   - Prompts are registered with names like `test-server-tools`, `test-topics-tools`, etc.

2. **Follow the prompt instructions:**
   - Each prompt provides detailed testing steps
   - Includes tool usage examples
   - Contains troubleshooting information

3. **Example workflow with prompts:**
   ```
   1. Start by prompting  `test server tools` or selecting te template prompts for an overview
   2. Use `test connection tools` to establish connection and test the setup
   3. Use category-specific prompts (e.g., `test topics- tools`) for detailed testing
   ```

### Using Resources for Testing

Resources provide comprehensive system information in JSON format. They are accessed through the MCP resource interface.

### Available Resources

#### ROS Metadata Resources

1. **`ros-mcp://ros-metadata/all`**
   - Complete system overview
   - Includes topics, services, nodes, parameters, and ROS version
   - Useful for getting a snapshot of the entire ROS system

2. **`ros-mcp://ros-metadata/topics/all`**
   - All topics with their types, publishers, and subscribers
   - Comprehensive topic connection information

3. **`ros-mcp://ros-metadata/services/all`**
   - All services with their types and providers
   - Complete service discovery information

4. **`ros-mcp://ros-metadata/nodes/all`**
   - All nodes with their publishers, subscribers, and services
   - Detailed node connection information

5. **`ros-mcp://ros-metadata/actions/all`** (ROS 2 only)
   - All actions with their types
   - Action discovery information

#### Robot Specification Resources

6. **`ros-mcp://robot-specs/get_verified_robots_list`**
   - List of available robot specifications
   - Returns JSON with robot names from `robot_specifications/` directory

### How to Use Resources

1. **Request resources through your AI assistant:**
   - Simply ask: `get ros-metadata resources` or `get topics resource`, or `get services resource`, 
   - Ask to access specific resources: `access ros-mcp://ros-metadata/all` etc.
   - The AI assistant will access the resource and return the JSON data

2. **Alternative: Access through MCP client interface:**
   - Resources are accessed via URI (e.g., `ros-mcp://ros-metadata/all`)
   - Your MCP client may provide a resource browser or URI access
   - Check your MCP client's documentation for resource access methods

3. **Parse the JSON response:**
   - Resources return JSON strings
   - The AI assistant can parse and explain the data for you

### Example: Using Resources

**Get complete system overview:**
```
Access: ros-mcp://ros-metadata/all

Returns JSON with:
{
  "topics": [...],
  "services": [...],
  "nodes": [...],
  "parameters": [...],
  "ros_version": "ROS 2"
}
```

**Get all topic details:**
```
Access: ros-mcp://ros-metadata/topics/all

Returns JSON with:
{
  "total_topics": 5,
  "topics": {
    "/turtle1/cmd_vel": {
      "type": "geometry_msgs/msg/Twist",
      "publishers": [...],
      "subscribers": [...]
    },
    ...
  }
}
```

## Complete Tools Testing Workflow

### 1. Initial Setup and Connection

```python
# Step 1: Connect to ROS system
connect_to_robot(ip='127.0.0.1', port=9090)

# Step 2: Verify connection and detect ROS version
detect_ros_version()
```

### 2. Discovery Phase

**Using Tools:**
```python
# Discover what's available
get_topics()
get_services()
get_nodes()
get_actions()  # ROS 2 only
```

**Using Resources:**
```
Access: ros-mcp://ros-metadata/all
```

### 3. Detailed Testing by Category

**Topics:**
```python
# Get topic details
get_topic_details('/turtle1/cmd_vel')

# Subscribe to a topic
subscribe_once(topic='/turtle1/pose', msg_type='turtlesim/msg/Pose')

# Publish to a topic
publish_once(
    topic='/turtle1/cmd_vel',
    msg_type='geometry_msgs/msg/Twist',
    msg={'linear': {'x': 2.0, 'y': 0.0, 'z': 0.0}}
)
```

**Services:**
```python
# Get service details
get_service_details('/turtle1/teleport_absolute')

# Call a service
call_service(
    service_name='/turtle1/teleport_absolute',
    service_type='turtlesim/srv/TeleportAbsolute',
    request={'x': 5.5, 'y': 5.5, 'theta': 0.0}
)
```

**Nodes:**
```python
# Get node details
get_node_details('/turtlesim')
```

**Parameters (ROS 2 only):**
```python
# Get parameters
get_parameters('turtlesim')

# Set parameter
set_parameter('/turtlesim:background_r', '255')
```

**Actions (ROS 2 only):**
```python
# Get action details
get_action_details('/turtle1/rotate_absolute')

# Send action goal
send_action_goal(
    action_name='/turtle1/rotate_absolute',
    action_type='turtlesim/action/RotateAbsolute',
    goal={'theta': 1.57}
)
```

### 4. Gather Resources

Access resources to get comprehensive system information:

```
1. Access ros-mcp://ros-metadata/topics/all
   - Get all topics with types, publishers, and subscribers

2. Access ros-mcp://ros-metadata/services/all
   - Get all services with types and providers

3. Access ros-mcp://ros-metadata/nodes/all
   - Get all nodes with publishers, subscribers, and services

4. Access ros-mcp://ros-metadata/actions/all (ROS 2 only)
   - Get all actions with their types

5. Access ros-mcp://ros-metadata/all
   - Get complete system overview
```

## Testing Checklist

- [ ] Prerequisites installed and verified
- [ ] ROS core/daemon running
- [ ] Turtlesim node running
- [ ] Rosbridge server running
- [ ] MCP server connected successfully
- [ ] ROS version detected correctly
- [ ] All discovery tools working (topics, services, nodes, actions)
- [ ] Category-specific tools tested (topics, services, nodes, parameters, actions)
- [ ] Resources accessible and returning valid JSON

## Troubleshooting

### Connection Issues

- **Cannot connect to rosbridge:**
  - Verify rosbridge is running: Check terminal output
  - Check port: Default is 9090
  - Verify IP address: Use `127.0.0.1` for localhost

- **ROS version detection fails:**
  - Ensure ROS environment is sourced
  - For ROS 2: `source /opt/ros/<distro>/setup.bash`
  - For ROS 1: `source /opt/ros/<distro>/setup.bash`

### Tool Issues

- **Tools return empty results:**
  - Verify `turtlesim` is running
  - Check that topics/services/nodes exist
  - Ensure rosbridge is connected

- **Service calls fail:**
  - Verify service exists: `get_services()`
  - Check service type: `get_service_details()`
  - Verify request format matches service definition

### Resource Issues

- **Resources return errors:**
  - Verify connection to ROS system
  - Check that rosbridge is running
  - Ensure required ROS services are available

## Next Steps

After completing basic testing:

1. **Explore category-specific prompts:**
   - Use `test-topics-tools` for detailed topic testing
   - Use `test-services-tools` for service testing
   - Use other category prompts as needed

2. **Test with your own robot:**
   - Replace turtlesim with your robot's nodes
   - Test with your robot's topics, services, and actions
   - Gather resources to understand your system structure

3. **Integrate with your workflow:**
   - Use prompts for guided testing
   - Use resources for system monitoring
   - Combine tools and resources for comprehensive testing

## Additional Resources

- **Launch System Guide:** See `docs/launch_system.md` for integrating rosbridge with your robot
- **Installation Guide:** See `docs/installation.md` for setup instructions
- **Category-Specific Prompts:** Access detailed testing guides for each tool category

