from mcp.server.fastmcp import FastMCP
from typing import List, Any, Optional
from pathlib import Path
import json
from utils.websocket_manager import WebSocketManager
from msgs.geometry_msgs import Twist
from msgs.sensor_msgs import Image, JointState

# Function to load configuration
def load_config(config_path="config.json"):
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
        return config
    except FileNotFoundError:
        print(f"Configuration file not found at {config_path}. Using default values.")
        return {} # Return empty dict to use defaults
    except json.JSONDecodeError:
        print(f"Error decoding JSON from {config_path}. Using default values.")
        return {}

# Load configuration
config = load_config()

# Use configuration values or defaults
LOCAL_IP = config.get("LOCAL_IP", "127.0.0.1")
ROBOT_ID = config.get("ROBOT_ID", "12")
ROSBRIDGE_URL_BASE = config.get("ROSBRIDGE_URL_BASE", "wss://robohub.eng.uwaterloo.ca/uwbot-")
ROSBRIDGE_URL_SUFFIX = config.get("ROSBRIDGE_URL_SUFFIX", "-rosbridge/")

URL = ROSBRIDGE_URL_BASE + ROBOT_ID + ROSBRIDGE_URL_SUFFIX

mcp = FastMCP("ros-mcp-server")
ws_manager = WebSocketManager(URL, LOCAL_IP)
twist = Twist(ws_manager, topic="/cmd_vel")
image = Image(ws_manager, topic="/oakd/rgb/image_raw")
jointstate = JointState(ws_manager, topic="/joint_states")


@mcp.tool()
def get_topics():
    topic_info = ws_manager.get_topics()
    ws_manager.close()

    if topic_info:
        topics, types = zip(*topic_info)
        return {"topics": list(topics), "types": list(types)}
    else:
        return "No topics found"


@mcp.tool()
def pub_twist(linear: List[Any], angular: List[Any]):
    msg = twist.publish(linear, angular)
    ws_manager.close()

    if msg is not None:
        return "Twist message published successfully"
    else:
        return "No message published"


@mcp.tool()
def pub_twist_seq(linear: List[Any], angular: List[Any], duration: List[Any]):
    twist.publish_sequence(linear, angular, duration)


@mcp.tool()
def sub_image():
    msg = image.subscribe()
    ws_manager.close()

    if msg is not None:
        return "Image data received and downloaded successfully"
    else:
        return "No image data received"


@mcp.tool()
def pub_jointstate(
    name: list[str], position: list[float], velocity: list[float], effort: list[float]
):
    msg = jointstate.publish(name, position, velocity, effort)
    ws_manager.close()
    if msg is not None:
        return "JointState message published successfully"
    else:
        return "No message published"


@mcp.tool()
def sub_jointstate():
    msg = jointstate.subscribe()
    ws_manager.close()
    if msg is not None:
        return msg
    else:
        return "No JointState data received"


if __name__ == "__main__":
    mcp.run(transport="streamable-http")