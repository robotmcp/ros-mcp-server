from mcp.server.fastmcp import FastMCP
from typing import List, Any, Optional
from pathlib import Path
import json
from utils.websocket_manager import WebSocketManager
import time
import os
import roslibpy
import base64
import cv2
from datetime import datetime
import numpy as np

ROSBRIDGE_IP = "192.168.20.144"
ROSBRIDGE_PORT = 9090

mcp = FastMCP("ros-mcp-server")
ws_manager = WebSocketManager(ROSBRIDGE_IP, ROSBRIDGE_PORT)

actions_groups_data: dict[str, str] = None

@mcp.tool()
def get_topics():
    
    ws_manager.connect()
    topic_info = ws_manager.ws.get_topics()
    ws_manager.close()

    if topic_info:
       return list(topic_info)
    else:
        return "No topics found"

@mcp.tool(description="This tool makes a robot move by one step in any direction." \
"Tool uses joystick emulate [z][x] -1.0 for right, 1.0 for left, -1.0 for backward, 1.0 for forward")
def make_step(x: float, z: float):
    # Validate input
    right_left = x
    forward_backward = z
    
    # Clamp values between -1.0 and 1.0
    right_left = max(-1.0, min(1.0, right_left))
    forward_backward = max(-1.0, min(1.0, forward_backward))
    
    message = {
        'axes': [right_left, forward_backward, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
        'buttons': [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
    }

    ws_manager.send('/joy', 'sensor_msgs/Joy', message)

    message_to_stop = {
        'axes': [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
        'buttons': [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
    }

    ws_manager.send('/joy', 'sensor_msgs/Joy', message_to_stop)

    return "one step!"

@mcp.tool(description='This tool getting action from topic on robot and write on python dict[file_name, description]')
def get_available_actions():
    global actions_groups_data  # Needed to modify the global variable
    actions_groups_data = None  # Reset before use
    
    ws_manager.connect()

    # topic for read
    topic = roslibpy.Topic(
        ws_manager.ws,
        "/action_groups_data",
        "std_msgs/String"
    )

    def on_action_received(msg):
        global actions_groups_data
        actions_groups_data = msg

    topic.subscribe(on_action_received)

    start_time = time.time()
    while actions_groups_data is None and (time.time() - start_time) < 5:
        time.sleep(0.1)

    topic.unsubscribe()
    ws_manager.close()

    if actions_groups_data:
        return list(actions_groups_data.items())  # Convert dict to list of tuples
    else:
        return []

@mcp.tool(description="This tool run action")
def run_action(action_name: str):

    message = ({
        'data': action_name
    })

    return ws_manager.send('app/set_action', 'std_msgs/String', message)

@mcp.tool(description="This tool used to get raw image from robot and save on user pc on directory like downloads")
def get_image():
    ws_manager.connect()

    image_topic = roslibpy.Topic(
        ws_manager.ws,
        '/camera/image_raw',
        'sensor_msgs/Image'
    )
    
    try:
        received_msg = None

        def on_image_received(msg):
            nonlocal received_msg
            received_msg = msg

        image_topic.subscribe(on_image_received)

        start_time = time.time()
        while received_msg is None and (time.time() - start_time) < 5:
            time.sleep(0.1)

        if received_msg is None:
            print("[Image] No data received from subscriber")
            image_topic.unsubscribe()
            return None

        msg = received_msg

        height = msg["height"]
        width = msg["width"]
        encoding = msg["encoding"]
        data_b64 = msg["data"]

        image_bytes = base64.b64decode(data_b64)
        img_np = np.frombuffer(image_bytes, dtype=np.uint8)

        if encoding == "rgb8":
            img_np = img_np.reshape((height, width, 3))
            img_cv = cv2.cvtColor(img_np, cv2.COLOR_RGB2BGR)
        elif encoding == "bgr8":
            img_cv = img_np.reshape((height, width, 3))
        elif encoding == "mono8":
            img_cv = img_np.reshape((height, width))
        else:
            print(f"[Image] Unsupported encoding: {encoding}")
            image_topic.unsubscribe()
            return None

        if save_path is None:
            downloads_dir = Path.home() / "Downloads"
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            save_path = downloads_dir / f"image_{timestamp}.png"

        Path(save_path).parent.mkdir(parents=True, exist_ok=True)
        cv2.imwrite(str(save_path), img_cv)
        os.startfile(save_path)
        print(f"[Image] Saved to {save_path}")

        image_topic.unsubscribe()
        ws_manager.close()
        return img_cv

    except Exception as e:
        print(f"[Image] Failed to receive or decode: {e}")
        if 'image_topic' in locals():
            image_topic.unsubscribe()
        return None

if __name__ == "__main__":
    mcp.run(transport="stdio")
