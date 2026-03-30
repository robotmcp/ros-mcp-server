# Step 3: Connect to Your Robot

Now that your AI client has the MCP server configured and rosbridge is running on the robot, you're ready to connect.

## 1. Connect

Open your AI client and tell it to connect to the robot:

```
Connect to the robot at <robot-ip>
```

Replace `<robot-ip>` with your robot's IP address on the local network (e.g., `192.168.1.42`). If the MCP server and ROS are on the same machine, use `localhost`.

The MCP server will report that the IP is reachable and the rosbridge port is open — this means you're connected.

> Make sure the rosbridge port (default 9090) is not blocked by a firewall on the robot's machine.

## 2. Explore

Once connected, try asking your AI client to explore the ROS system:

```
What topics and services are available on the robot?
```

```
What nodes are currently running?
```

The MCP server will query rosbridge and return the results from the robot's ROS environment.

## 3. Try It Out

You can interact with the robot using natural language:

```
Make the robot move forward
```

```
Subscribe to the /odom topic and show me the latest message
```

If you don't have a physical robot, turtlesim is the standard "hello world" for ROS and is a great option to explore and experiment. Launch it using:

**ROS 2:**
```bash
ros2 run turtlesim turtlesim_node
```

**ROS 1:**
```bash
rosrun turtlesim turtlesim_node
```

For a full walkthrough, see the [Turtlesim Tutorial](../../examples/1_turtlesim/README.md).

## More Examples

This repo includes several examples to try with different robots and setups:

- [Turtlesim](../../examples/1_turtlesim/README.md) — the "hello world" of ROS
- [Turtlesim with Docker](../../examples/5_docker_turtlesim/README.md) — no ROS install required
- [LIMO Mobile Robot](../../examples/3_limo_mobile_robot/real_robot/README.md)
- [Unitree Go2](../../examples/4_unitree_go2/real_robot/README.md)
- [TurtleBot3](../../examples/9_turtlebot3/README.md)
- [Image Topics](../../examples/8_images/README.md)

For more advanced demos with simulated robots in Gazebo, see the [ROS-MCP Demos repository](https://github.com/robotmcp/demos-ros-mcp-server) which includes a warehouse TugBot, Unitree Go2 quadruped, and drone control with PX4.

---

[Back to Installation Guide](installation.md) | [Troubleshooting](troubleshooting.md)
