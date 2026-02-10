# Example - PX4 Drone (Real Robot)
![Static Badge](https://img.shields.io/badge/ROS2-Available-green)

This example guides you through controlling a real PX4-based drone using the ROS MCP Server.

**Note:** This setup shares the same ROS2 workspace as the Gazebo simulation example (`../drone_ws`).

## System Requirements
- **Onboard Computer**: Ubuntu 24.04 (Noble) or compatible
- **ROS2**: Jazzy Jalisco
- **Flight Controller**: PX4 Autopilot (Connected via MicroXRCE-DDS)

## Setup & Installation

### 1. Build the Workspace
Since the control code is shared, navigate to the `drone_ws` directory and build it.

```bash
cd ../drone_ws
colcon build --symlink-install
source install/setup.bash
```

### 2. Connect to Flight Controller
Ensure your companion computer is connected to the Flight Controller (Pixhawk/Cube etc.) via serial or USB.

Launch the MicroXRCE-DDS Agent:
```bash
MicroXRCEAgent serial --dev /dev/ttyACM0 -b 921600
```
*(Adjust the device path and baudrate according to your hardware setup)*

### 3. Launch the Control Node
```bash
# In the drone_ws folder
source install/setup.bash
ros2 run drone_controller bridge
```

## Integration with MCP Server

### Start rosbridge
To enable communication with the **ros-mcp-server**:

```bash
ros2 launch rosbridge_server rosbridge_websocket_launch.xml 
```

### Connect with Gemini / MCP Client
1. Ensure your MCP client machine is on the same network as the drone.
2. **Prompt:** "I am controlling a drone_px4. Connect to `<DRONE_IP_ADDRESS>` and load the drone_px4 robot configuration."

## Available Actions
The actions and commands are identical to the simulation example. Please refer to `../gazebo_sim/README.md` or the robot specification for details.
