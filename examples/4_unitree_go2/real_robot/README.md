# Example - Unitree GO2 (Real)
![Static Badge](https://img.shields.io/badge/ROS-Available-green)
![Static Badge](https://img.shields.io/badge/ROS2-Available-green)

This is an example using the real robot, **Unitree GO2**, in the ROS2 ecosystem. If needed, it can also be run on ROS1.

## Prerequisites

In this example, the **Unitree GO2 Edu** model was used, and the setup was tested on **Ubuntu 20.04 with ROS2 Foxy**. If needed, it can also be run on **Ubuntu 18.04 with ROS1 Noetic**.

⚠️ **Note**: For the Unitree GO2 Air and Pro models, SSH access may be restricted, so using the Edu model is recommended whenever possible.

### Unitree GO2
For more details, please refer to the [Unitree GO2 Documentation](https://support.unitree.com/home/en/developer/about_Go2).

<img src="../images/unitree_go2_real.png" width="300">


## Quick Start
### 1. Network Setup
The Unitree GO2 and the user’s PC can be connected via SSH through the [GO2 Robot Interface](https://www.docs.quadruped.de/projects/go2/html/go2_driver.html#go2-network-interface).
However, by default, the Unitree GO2 does not have internet access, so you need to configure the router as described below to allow the Unitree GO2 to connect to the internet.

#### Requirements
- A router with Internet access
- A computer connected to the router via Wi-Fi or Ethernet
- Unitree GO2 connected to the router via Ethernet cable

#### Steps
- **Access the Router Gateway**
    - Make sure your PC is connected to the router.
    - Run `ifconfig` in the terminal to check the assigned IP address. In this example, the IP is `192.168.50.13`.  
    <img src="../images/unitree_go2_real_router_ip.png" width="500">
    
    - If the IP is in the form `192.168.x.x`, replace the last number with `1` and open it in a browser (e.g., `192.168.x.1`). In this case, it is `192.168.50.1`.  
    <img src="../images/unitree_go2_real_router_connect.png" width="500">

- **Login to the Router**
    - Enter the default username and password of the router.
    - If the credentials were previously changed, use the updated account information.
    - After a successful login, the router configuration page will be displayed.

- **Change Router Gateway Address**
    - Navigate to **Advanced Settings → LAN** (the menu name may vary depending on the manufacturer/model).
    - Change the router’s IP address to `192.168.123.1`.  
    <img src="../images/unitree_go2_real_router_ip_change.png" width="500">
    
    - Reason: The Unitree Go2 robot has a fixed IP address of `192.168.123.18`, so the router must assign addresses in the same subnet `192.168.123.x` to enable communication.

- **Assign a Static IP**
    - By default, the router uses DHCP to dynamically assign IP addresses.
    - However, after disconnection/reconnection, the Unitree Go2’s IP may change. To prevent this, configure a **static IP assignment**.
    - Go to the **DHCP menu**.
    - Enable **Manual Assignment**, enter the Unitree Go2’s **MAC address**, and set the IP address to `192.168.123.18`.  
    <img src="../images/unitree_go2_real_router_dhcp.png" width="500">
    
    - Note: Most routers can automatically detect the MAC address (depending on the model).

- **Check Connectivity**
    - After completing the above steps, check the connectivity between your PC and the Unitree Go2.
    - You can use the `ping` command in the terminal to verify the connection:
      ```
      ping 192.168.123.18
      ```
    - If you receive replies, the connection is successful.

- **SSH Access**
    - You can access the Unitree Go2 via SSH using the following command:
        ```
        ssh -X unitree@192.168.123.18
        ```
    - The default password is `123`.
    - After logging in, you can select the ROS version (ROS1 Noetic or ROS2 Foxy). In this example, Select ROS2 Foxy.  
    <img src="../images/unitree_go2_real_ssh.png" width="500">
 

- **Check Internet Access**
    - Verify that the Unitree Go2 has internet access by running:
        ```
        ping google.com
        ```
    - If you receive replies, the internet connection is working properly.

### 2. Install rosbridge (Unitree GO2 side)
On the Unitree GO2, install rosbridge to enable communication with the **ros-mcp-server**.
```bash
sudo apt install ros-foxy-rosbridge-server
```

### 3. Build `unitree_go` package
[`unitree_go`](https://github.com/unitreerobotics/unitree_ros2) is a ROS2 package provided by Unitree Robotics for controlling the Unitree GO2 robot. It includes various functionalities such as motion control, sensor data processing, and more.
To build the `unitree_go` package, follow these steps:
- **clone the repository** (User PC side)
    ```bash
    git clone https://github.com/unitreerobotics/unitree_ros2.git
    ```
- **move the package to the Unitree GO2's workspace** (User PC side)
    ```bash
    cd unitree_ros2/cyclonedds_ws/src/
    scp -r unitree unitree@192.168.123.18:/home/unitree/cyclonedds_ws/src/
    ```
- **build the package** (Unitree GO2 side)
    ```bash
    cd ~/cyclonedds_ws
    colcon build --symlink-install
    ```
- **source the workspace** (Unitree GO2 side)
    ```bash
    source ~/.bashrc
    ```

### 4. Setup Camera Script (User PC side)
By default, the Unitree GO2 publishes camera data through a custom topic called `/frontvideostream`. To convert this custom topic into a standard ROS2 topic, you can upload and run the following script on the Unitree GO2.

- **move the script to the Unitree GO2** (User PC side)
    ```bash
    cd /<ABSOLUTE_PATH>/ros-mcp-server/examples/4_unitree_go2/real_robot/scripts
    scp ./camera_bridge.py unitree@192.168.123.18:/home/unitree/cyclonedds_ws/src/image_process/
    ```
- **check the script** (Unitree GO2 side)
    ```bash
    cd ~/cyclonedds_ws/src/image_process/
    python3 camera_bridge.py
    ```
    If the camera is working properly, you should see the camera feed from the `/camera/rgb/image_raw` topic.
    
### 5. Launch rosbridge and camera script (Unitree GO2 side)
To enable communication between the **Unitree GO2** and the **ros-mcp-server**, you need to launch the following commands:

On one terminal, run:
```bash
# Launch rosbridge
ros2 launch rosbridge_server rosbridge_websocket_launch.xml
```
On a separate terminal, run:
```bash
# Launch camera script
cd ~/cyclonedds_ws/src/image_process/
python3 camera_bridge.py
```

## **Integration with MCP Server**
    
Once rosbridge is running on the Unitree GO2 and your PC is on the same network, you can connect the MCP server to control the robot. If you haven’t set up the MCP server yet, follow the [installation guide](https://github.com/robotmcp/ros-mcp-server/blob/main/docs/installation.md) .
    
Since The **ros-mcp-server** to recognize the robot, configure it to connect to the robot’s IP address.

### **Example 1** : Connect to robot
By default, the **ros-mcp-server** can access the Unitree GO2 robot on the same network as the user's local PC. Therefore, the IP address of the Unitree GO2 robot is `192.168.123.18`.  
<img src="../images/unitree_go2_real_connect.png" width="500">

### **Example 2** : Check available topics
<img src="../images/unitree_go2_real_topics.png" width="500">

### **Example 3** : Receive camera data and analyze it
<img src="../images/unitree_go2_real_camera.png" width="500">

## **Next Steps**
The Unitree GO2 has various sensors and functionalities. Let's make use of them.
