from mcp.server.fastmcp import FastMCP
from typing import List, Any, Optional
from pathlib import Path
import json
from utils.websocket_manager import WebSocketManager

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


# @mcp.tool()
# def sub_image():
#     msg = image.subscribe()
#     ws_manager.close()
    
#     if msg is not None:
#         return "Image data received and downloaded successfully"
#     else:
#         return "No image data received"

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
