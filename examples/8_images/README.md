# Tutorial - ROS MCP Server with Image Processing

Welcome to the image processing tutorial! This guide will walk you through using the ROS MCP Server to work with camera feeds, analyze images, and perform computer vision tasks using natural language commands.

## What You'll Learn

By the end of this tutorial, you'll be able to:
- Launch camera feeds using different camera types (synthetic or real)
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

## Camera Options

This tutorial supports two camera types:

### 🎮 **Option 1: Synthetic Camera (image_tools)**
- **Best for**: Learning, testing, and development
- **Requirements**: Only ROS2 and image_tools

### 📷 **Option 2: RealSense Camera (realsense2_camera)**
- **Best for**: Real-world applications and advanced computer vision
- **Requirements**: Intel RealSense camera + realsense2_camera package

## Dependencies

### Required for All Camera Types

Install the ROS image transport plugins package (replace `${ROS_DISTRO}` with your current ROS 2 distribution, for example `humble` or `jazzy`):

```bash
sudo apt install ros-${ROS_DISTRO}-image-transport-plugins
```

### For Synthetic Camera (image_tools)

Install image_tools for synthetic camera data:

```bash
sudo apt install ros-${ROS_DISTRO}-image-tools
```

### For RealSense Camera

Install the RealSense ROS2 package:

```bash
sudo apt install ros-${ROS_DISTRO}-realsense2-camera
```

> 💡 **Tip**: Start with the synthetic camera option for learning, then move to RealSense for real-world applications.

## Step 1: Launch the Image Demo System

Choose your camera type and launch the appropriate system:

### 🎮 **Option A: Synthetic Camera (Burger) - Recommended for Beginners**

#### Using Launch File (Easiest)

```bash
# Navigate to the examples directory
cd examples/8_images

# Launch synthetic camera system
ros2 launch ros_mcp_images_demo.launch.py
```

#### Manual Launch (For Learning)

```bash
# Terminal 1: Start rosbridge
ros2 launch rosbridge_server rosbridge_websocket_launch.xml

# Terminal 2: Start synthetic camera feed
ros2 run image_tools cam2image --ros-args -p burger_mode:=true

# Terminal 3: Display images
ros2 run image_tools showimage

# Terminal 4: Start image compression
ros2 run image_transport republish raw in:=/image out:=/image/compressed
```

### 📷 **Option B: RealSense Camera - For Real-World Applications**

#### Using Launch File (Easiest)

```bash
# Navigate to the examples directory
cd examples/8_images

# Launch RealSense camera system
ros2 launch ros_mcp_images_demo_realsense.launch.py
```

#### Manual Launch (For Learning)

```bash
# Terminal 1: Start rosbridge
ros2 launch rosbridge_server rosbridge_websocket_launch.xml

# Terminal 2: Start RealSense camera
ros2 launch realsense2_camera rs_launch.py

# Terminal 3: Display color images
ros2 run image_tools showimage --ros-args --remap /image:=/camera/camera/color/image_raw

# Terminal 4: Display depth images (optional)
ros2 run image_tools showimage --ros-args --remap /image:=/camera/camera/depth/image_rect_raw

# Terminal 5: Start image compression
ros2 run image_transport republish raw in:=/camera/camera/color/image_raw out:=/camera/camera/color/image_raw/compressed
```

### What Each System Provides

#### Synthetic Camera System:
- **rosbridge_server** - WebSocket server for MCP communication
- **cam2image** - Synthetic camera feed (burger images)
- **showimage** - Image display window
- **republish** - Image compression service

#### RealSense Camera System:
- **rosbridge_server** - WebSocket server for MCP communication
- **realsense2_camera** - RealSense camera driver
- **showimage** - Image display windows for color and depth
- **republish** - Image compression service

## Step 2: Verify the System is Running

Check that all components are working:

```bash
# List available topics
ros2 topic list
```

### For Synthetic Camera System, you should see:
```
/image - Raw camera feed (burger images)
/image/compressed - Compressed camera feed
/flip_image - Image flip control
/client_count - Connection count
/connected_clients - Client information
```

### For RealSense Camera System, you should see:
```
/camera/camera/color/image_raw - Color camera feed
/camera/camera/color/camera_info - Color camera calibration
/camera/camera/color/metadata - Color camera metadata
/camera/camera/depth/image_rect_raw - Depth camera feed
/camera/camera/depth/camera_info - Depth camera calibration
/camera/camera/depth/metadata - Depth camera metadata
/camera/camera/extrinsics/depth_to_color - Camera extrinsics
/client_count - Connection count
/connected_clients - Client information
```

### Test Camera Feed

```bash
# For synthetic camera
ros2 topic echo /image --once

# For RealSense camera
ros2 topic echo /camera/camera/color/image_raw --once
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

### Capture Images

Try these commands with your AI assistant:

#### For Synthetic Camera:
```
Read an image from the /image topic
```

```
Capture the current burger image
```

```
Take a picture from the synthetic camera
```

#### For RealSense Camera:
```
Read an image from the RealSense camera
```

```
Capture the current color camera feed
```

```
Take a picture from /camera/camera/color/image_raw
```

### Analyze Images

#### General Analysis:
```
What do you see in this image?
```

```
Count the objects in the image
```

```
Describe what's in the camera feed
```

#### For Synthetic Camera:
```
How many burgers are in the image?
```

```
What color is the burger?
```

```
Describe the synthetic camera scene
```

#### For RealSense Camera:
```
What objects are visible in the room?
```

```
Describe the scene from the RealSense camera
```

```
What's the lighting like in the image?
```

## Step 5: Advanced Camera Control

### Camera Parameters

#### For Synthetic Camera:
```
What are the current camera settings?
```

```
Change the camera resolution
```

```
Adjust the camera frequency
```

#### For RealSense Camera:
```
What are the RealSense camera settings?
```

```
Get the camera calibration information
```

```
Check the depth camera parameters
```

## Troubleshooting

### Common Issues

<details>
<summary><strong>No Image Display</strong></summary>

**Problem**: Camera feed not showing or no images received

**Solutions**:
- Launch the server with HTTP transport. It seems stdio can have difficulties showing images in the chat.
- **For Synthetic Camera**: Check if cam2image is running: `ros2 node list | grep cam2image`
- **For RealSense Camera**: Check if realsense2_camera is running: `ros2 node list | grep realsense`
- Verify image topic exists: `ros2 topic list | grep image`
- **For Synthetic Camera**: Test image publishing: `ros2 topic echo /image --once`
- **For RealSense Camera**: Test image publishing: `ros2 topic echo /camera/camera/color/image_raw --once`

</details>

<details>
<summary><strong>RealSense Camera Issues</strong></summary>

**Problem**: RealSense camera not detected or not working

**Solutions**:
- Check if camera is connected: `lsusb | grep Intel`
- Verify RealSense SDK installation: `realsense-viewer`
- Check camera permissions: `sudo usermod -a -G video $USER` (then logout/login)
- Test with RealSense viewer: `realsense-viewer`
- Check ROS2 RealSense package: `ros2 pkg list | grep realsense`

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
- **For Synthetic Camera**: Verify image message format: `ros2 topic info /image`
- **For RealSense Camera**: Verify image message format: `ros2 topic info /camera/camera/color/image_raw`
- Test with simpler commands first

</details>

<details>
<summary><strong>Display Issues</strong></summary>

**Problem**: showimage window doesn't appear

**Solutions**:
- **WSL users**: Install X11 forwarding: `sudo apt install x11-apps`
- **Remote connections**: Use X11 forwarding: `ssh -X username@hostname`
- **Docker users**: Check X11 forwarding configuration
- **For Synthetic Camera**: Try running without display: `ros2 run image_tools cam2image --ros-args -p show_camera:=false`
- **For RealSense Camera**: Try running without display: `ros2 launch realsense2_camera rs_launch.py enable_color:=true enable_depth:=true`

</details>

<details>
<summary><strong>Topic Not Found</strong></summary>

**Problem**: Expected camera topics not available

**Solutions**:
- **For Synthetic Camera**: Ensure cam2image is running with correct parameters
- **For RealSense Camera**: Check if camera is properly connected and drivers are loaded
- List all available topics: `ros2 topic list`
- Check topic info: `ros2 topic info <topic_name>`
- Verify camera launch parameters

</details>

## Learning Resources

- [ROS2 Image Processing Tutorials](https://docs.ros.org/en/humble/Tutorials/Intermediate/Image_Processing/)
- [OpenCV with ROS2](https://docs.ros.org/en/humble/Tutorials/Intermediate/Image_Processing/)
- [Computer Vision with ROS](https://wiki.ros.org/cv_bridge)
- [Image Transport Tutorials](https://docs.ros.org/en/humble/Tutorials/Intermediate/Image_Processing/)
