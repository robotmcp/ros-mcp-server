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

@mcp.tool()
def get_topics():
    # getto method to connect
    ws_manager.connect()

    topic_info = ws_manager.ws.get_topics()
    ws_manager.close()

    if topic_info:
       return list(topic_info)
    else:
        return "No topics found"

@mcp.tool()
def make_one_step():
    ws_manager.connect()

    message = ({
        'axes': [0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
        'buttons': [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
    })

    ws_manager.send('/joy', 'sensor_msgs/Joy', message)

    ws_manager.close()

    return "one step!"


# @mcp.tool()
# def pub_twist(linear: List[Any], angular: List[Any]):
#     msg = twist.publish(linear, angular)
#     ws_manager.close()
    
#     if msg is not None:
#         return "Twist message published successfully"
#     else:
#         return "No message published"

#@mcp.tool()
#def pub_twist_seq(linear: List[Any], angular: List[Any], duration: List[Any]):
#    twist.publish_sequence(linear, angular, duration)


@mcp.tool()
def sub_image(save_path=None):
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

        # Ждём сообщение (например, 5 секунд)
        start_time = time.time()
        while received_msg is None and (time.time() - start_time) < 5:
            time.sleep(0.1)

        if received_msg is None:
            print("[Image] No data received from subscriber")
            image_topic.unsubscribe()  # Важно отписаться
            return None

        # Если сообщение пришло, обрабатываем его
        msg = received_msg  # Допустим, что msg уже распарсен в dict

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

        image_topic.unsubscribe()  # Отписываемся после обработки
        return img_cv

    except Exception as e:
        print(f"[Image] Failed to receive or decode: {e}")
        if 'image_topic' in locals():
            image_topic.unsubscribe()
        return None

# @mcp.tool()
# def pub_jointstate(name: list[str], position: list[float], velocity: list[float], effort: list[float]):
#     msg = jointstate.publish(name, position, velocity, effort)
#     ws_manager.close()
#     if msg is not None:
#         return "JointState message published successfully"
#     else:
#         return "No message published"

# @mcp.tool()
# def sub_jointstate():
#     msg = jointstate.subscribe()
#     ws_manager.close()
#     if msg is not None:
#         return msg
#     else:
#         return "No JointState data received"

if __name__ == "__main__":
    mcp.run(transport="stdio")
