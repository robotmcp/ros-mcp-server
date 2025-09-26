# Tutorial - ROS MCP Server with Image Processing

Welcome to the image processing tutorial! This guide will walk you through using the ROS MCP Server to work with camera feeds, analyze images, and perform computer vision tasks using natural language commands.

## What You'll Learn

By the end of this tutorial, you'll be able to:
- Launch a camera feed using ROS image tools
- Capture and analyze images from camera topics
- Count objects in images
- Detect movement between frames
- Control image processing parameters
- Use natural language to interact with camera systems

## Prerequisites

Before starting this tutorial, make sure you have:

✅ **ROS2 installed** (Humble or Jazzy recommended)  
✅ **Basic familiarity with terminal/command line**  
✅ **The ROS MCP Server installed** (see [Installation Guide](../../docs/installation.md))  
✅ **OpenCV and image processing libraries** (usually included with ROS2)

> 💡 **Tip**: This tutorial uses synthetic camera data (burger images) for demonstration. For real camera feeds, you'll need a camera connected to your system.

## Step 1: Launch the Image Demo System

Let's start by launching the complete image processing system:

### Option A: Using the Launch File (Recommended)

```bash
# Navigate to the examples directory
cd examples/8_images

# Launch the complete system
ros2 launch ros_mcp_images_demo.launch.py
```

This will start:
- **rosbridge_server** - WebSocket server for MCP communication
- **cam2image** - Synthetic camera feed (burger images)
- **showimage** - Image display window
- **republish** - Image compression service

### Option B: Manual Launch (For Learning)

If you want to understand each component:

```bash
# Terminal 1: Start rosbridge
ros2 launch rosbridge_server rosbridge_websocket_launch.xml

# Terminal 2: Start camera feed
ros2 run image_tools cam2image --ros-args -p burger_mode:=true

# Terminal 3: Display images
ros2 run image_tools showimage

# Terminal 4: Start image compression
ros2 run image_transport republish raw in:=/image out:=/image/compressed
```

## Step 2: Verify the System is Running

Check that all components are working:

```bash
# List available topics
ros2 topic list

# You should see:
# /image - Raw camera feed
# /image/compressed - Compressed camera feed
# /flip_image - Image flip control
# /client_count - Connection count
# /connected_clients - Client information
```

## Step 3: Connect with MCP Server

Now let's connect the MCP server to the image system:

### Start the MCP Server with HTTP

```bash
# From the project root
cd /path/to/ros-mcp-server
export MCP_TRANSPORT=http
uv run server.py
```

### Connect to the System

Once connected, you can start using natural language commands to interact with the camera system.

## Step 4: Basic Image Operations

### 📸 Capture Images

Try these commands with your AI assistant:

```
Read an image from the camera
```

```
Capture the current camera feed
```

```
Take a picture and save it
```

### 🔍 Analyze Images

```
What do you see in this image?
```

```
Count the objects in the image
```

```
Describe what's in the camera feed
```

### 🎛️ Control Image Processing

```
Flip the image
```

```
Stop flipping the image
```

```
Publish flip commands for 10 seconds
```

## Step 5: Advanced Image Analysis

### Object Detection and Counting

```
How many burgers are in the image?
```

```
Count all the objects you can see
```

```
What objects are visible in the camera feed?
```


## Step 6: Advanced Camera Control

### Camera Parameters

```
What are the current camera settings?
```

```
Change the camera resolution
```

```
Adjust the camera frequency
```

### Image Topics

```
What image topics are available?
```

```
Subscribe to the compressed image topic
```

```
Monitor both raw and compressed feeds
```


## Troubleshooting

### Common Issues

<details>
<summary><strong>No Image Display</strong></summary>

**Problem**: Camera feed not showing or no images received

**Solutions**:
- Launch the server with HTTP transport. It seems stdio can have difficulties showing images in the chat.
- Check if cam2image is running: `ros2 node list | grep cam2image`
- Verify image topic exists: `ros2 topic list | grep image`
- Test image publishing: `ros2 topic echo /image --once`

</details>

<details>
<summary><strong>MCP Connection Issues</strong></summary>

**Problem**: AI assistant can't access camera data

**Solutions**:
- Verify that you are configuring your MCP server correctly
- First connect to the MCP server with `connect_to_robot` tool
- Ensure MCP server is connected
- Restart rosbridge if connection fails

</details>

<details>
<summary><strong>Image Processing Errors</strong></summary>

**Problem**: Image analysis commands fail

**Solutions**:
- Check if OpenCV is properly installed
- Verify image message format: `ros2 topic info /image`
- Test with simpler commands first

</details>

<details>
<summary><strong>Display Issues</strong></summary>

**Problem**: showimage window doesn't appear

**Solutions**:
- **WSL users**: Install X11 forwarding: `sudo apt install x11-apps`
- **Remote connections**: Use X11 forwarding: `ssh -X username@hostname`
- **Docker users**: Check X11 forwarding configuration
- Try running without display: `ros2 run image_tools cam2image --ros-args -p show_camera:=false`

</details>


## Next Steps

### 🎯 Immediate Next Steps

1. **Try different image analysis commands** with your AI assistant
2. **Experiment with image manipulation** - flipping, filtering, enhancement
3. **Test movement detection** with dynamic scenes
4. **Explore object counting** with different objects

### 🚀 Advanced Exploration

1. **Connect to real cameras**:
   - USB webcams
   - ROS-compatible cameras
   - Simulation environments

2. **Implement custom image processing**:
   - Edge detection
   - Color filtering
   - Object tracking
   - Face detection

3. **Integrate with other ROS systems**:
   - Navigation stacks
   - Manipulation systems
   - SLAM algorithms

### 📚 Learning Resources

- [ROS2 Image Processing Tutorials](https://docs.ros.org/en/humble/Tutorials/Intermediate/Image_Processing/)
- [OpenCV with ROS2](https://docs.ros.org/en/humble/Tutorials/Intermediate/Image_Processing/)
- [Computer Vision with ROS](https://wiki.ros.org/cv_bridge)
- [Image Transport Tutorials](https://docs.ros.org/en/humble/Tutorials/Intermediate/Image_Processing/)


---

**Happy image processing!** 📸🤖

This tutorial has shown you how to use natural language to interact with camera systems through the ROS MCP Server. You can now apply these same principles to real robots, surveillance systems, or any ROS-based image processing pipeline!