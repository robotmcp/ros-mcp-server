# Example - LIMO (Isaac Sim)
![Static Badge](https://img.shields.io/badge/ROS2-Available-green)

Here is an introduction to the ROS MCP server’s capabilities using the robot simulator Isaac Sim with the mobile robot LIMO!

This example includes the Isaac Sim Docker installation and execution, as well as a USD file with the LIMO robot equipped with a camera and LiDAR sensor. This setup allows you to easily configure the LIMO robot environment within Isaac Sim.

## System Requirements
 This example requires a PC that meets the minimum specifications to run Isaac Sim. Please refer to the [System Requirements](https://docs.isaacsim.omniverse.nvidia.com/5.0.0/installation/requirements.html) to prepare the appropriate hardware.

## Prerequisites
✅ **Note:** This example is designed to run on Linux with ROS2 installed and has been tested on the following versions:  
- **OS**: Ubuntu 20.04, 22.04  
- **ROS2**: Foxy, Humble  
- **Isaac Sim**: Local versions 4.5.0, 5.0.0 and Docker versions 4.5.0, 5.0.0
  
This example is written based on **Docker Isaac Sim 5.0.0** to maximize accessibility and minimize dependencies.

Before starting this example, make sure you have the following installed:
- **ROS2** : [Install ROS2](https://docs.ros.org/en/dashing/Installation/Ubuntu-Install-Binary.html)
- **Docker**: [Install Docker](https://docs.docker.com/get-docker/)

## Quick Start
### 1. Isaac Sim Container Installation
Follow the instructions on the [Isaac Sim Container Installation](https://docs.isaacsim.omniverse.nvidia.com/5.0.0/installation/install_container.html) to install the Isaac Sim Docker container.

### 2. Download Isaac Sim WebRTC Streaming Client
Follow the instructions on the [Isaac Sim WebRTC Streaming Client](https://docs.isaacsim.omniverse.nvidia.com/5.0.0/installation/download.html#isaac-sim-latest-release) to download and install the WebRTC streaming client.    
In this example, the WebRTC Streaming Client was downloaded and executed as follows.  
<img src="https://github.com/robotmcp/ros-mcp-server/blob/feature/lpigeon/limo_examples/docs/images/limo_examples/isaac_sim_webrtc_streaming_client_version.png" width="500">

### 3. Check Installation
To verify that the Isaac Sim Container and WebRTC Streaming Client are properly installed, please follow the steps below.

In the terminal where the Isaac Sim Container is running, execute the following command to run Isaac Sim with native livestream mode.
```bash
./runheadless.sh -v
```
When the message `Isaac Sim Full Streaming App is loaded.` appears, it means the application has been launched successfully.

After that, move to the folder where you downloaded the Isaac Sim WebRTC Streaming Client in a new terminal and run the following command to execute the client.
```bash
./isaacsim-webrtc-streaming-client-1.1.4-linux-x64.AppImage
```

When the GUI is displayed as shown below, it means the application has been launched successfully.

<img src="https://github.com/robotmcp/ros-mcp-server/blob/feature/lpigeon/limo_examples/docs/images/limo_examples/isaac_sim_webrtc_streaming_client.png" width="500">

If the above steps have been executed successfully, press the Connect button on the Isaac Sim WebRTC Streaming Client to check if the Isaac Sim screen appears.  
✅ **Note:** This example is based on installing and running the Isaac Sim container and the Isaac Sim WebRTC streaming client on the same local PC. Therefore, the server address for the Isaac Sim WebRTC Streaming Client is `127.0.0.1`. If the Isaac Sim container is running on another PC, you need to enter the IP address of that PC.

<img src="https://github.com/robotmcp/ros-mcp-server/blob/feature/lpigeon/limo_examples/docs/images/limo_examples/isaac_sim_streaming.png" width="500">

### 4. Copy LIMO example USD file to Isaac Sim
Copy the USD file of the LIMO robot created for this example to Isaac Sim.

```bash
cd /<ABSOLUTE_PATH>/ros-mcp-server/examples/limo/isaac_sim/usd/
docker exec <container_name> mkdir -p /example # default container_name : isaac-sim
docker cp ./limo_example.usd <container_name>:/example/limo_example.usd
```

If successfully copied, you can verify the USD file in the Isaac Sim screen as shown below.
```bash
Path : My Computer > / > example > limo_example.usd
```

<img src="https://github.com/robotmcp/ros-mcp-server/blob/feature/lpigeon/limo_examples/docs/images/limo_examples/limo_isaac_sim_usd_path.png" width="500">

### 5. Launch LIMO Example
Now, double-click the `limo_example.usd` file to run it in Isaac Sim. You should see the LIMO robot loading in the simulation environment as shown below.

<img src="https://github.com/robotmcp/ros-mcp-server/blob/feature/lpigeon/limo_examples/docs/images/limo_examples/limo_isaac_sim.png" width="500">

### 6. Check Simulation
Now, let's check if the LIMO robot is running properly in Isaac Sim. Press the play button (▶︎) in Isaac Sim to start the simulation. Once the simulation starts, ROS2 topics that can be used by the LIMO robot will be created through a predefined [Action Graph](https://docs.isaacsim.omniverse.nvidia.com/latest/omnigraph/omnigraph_tutorial.html) within the USD file.  
You can verify the available topics for the LIMO robot by running the ros2 topic list command in a terminal as shown below.

```bash
ros2 topic list
```
<img src="https://github.com/robotmcp/ros-mcp-server/blob/feature/lpigeon/limo_examples/docs/images/limo_examples/limo_isaac_sim_topic_list.png" width="500">

As shown in the figure, `/camera/image_raw`, `/cmd_vel`, and `/scan` must appear as essential topics.

Each topic serves the following functions:

- `/camera/image_raw`: Transmits raw image data collected from the LIMO robot's camera.
- `/cmd_vel`: Transmits movement commands for the LIMO robot.
- `/scan`: Transmits scan data collected from the LIMO robot's LiDAR sensor.

### 7. Start rosbridge
If the LIMO robot is running properly in Isaac Sim and ROS2 topics have been created, run rosbridge in the terminal to enable communication with the **ros-mcp-server**. Execute rosbridge using the following command:

```bash
ros2 launch rosbridge_server rosbridge_websocket_launch.xml
```

## **Integration with MCP Server**
    
If rosbridge is running, you can connect the MCP server to control the robot. If you haven’t set up the MCP server yet, follow the [installation guide](https://github.com/robotmcp/ros-mcp-server/blob/main/docs/installation.md) .

Since The **ros-mcp-server** needs to recognize the robot, configure it to connect to the robot’s IP address.

## **Example Walkthrough**
Once all the above connections are completed, you can connect to and control the LIMO robot from the **ros-mcp-server**. Below is an example screen showing the connection to the LIMO robot from the **ros-mcp-server**.

### **Example 1** : Connect to robot
By default, the Isaac Sim Container is run with the `--network=host` option, so it can access the LIMO robot on the same network as the user's local PC. Therefore, the IP address of the LIMO robot is the same as the user's local PC.
If the local PC's IP address, confirmed by the `ifconfig` command, is `192.168.50.88`, then the IP address of the LIMO robot will also be `192.168.50.88`.

<img src="https://github.com/robotmcp/ros-mcp-server/blob/feature/lpigeon/limo_examples/docs/images/limo_examples/limo_isaac_sim_connect.png" width="500">

### **Example 2** : ROS2 Topic Check

<img src="https://github.com/robotmcp/ros-mcp-server/blob/feature/lpigeon/limo_examples/docs/images/limo_examples/limo_isaac_sim_check_topic.png" width="500">

### **Example 3** : Simple Movement

<img src="https://github.com/robotmcp/ros-mcp-server/blob/feature/lpigeon/limo_examples/docs/images/limo_examples/limo_isaac_sim_simple_movement.gif" width="1000">

## **Next Steps**
The LIMO is equipped with various sensors, such as vision and LiDAR sensors. Let's make use of them.