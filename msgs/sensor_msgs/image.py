import base64
import json
from typing import Optional
from pathlib import Path
from typing import Protocol
from datetime import datetime
import numpy as np
import cv2
import roslibpy

class Subscriber(Protocol):
    def receive_binary(self) -> bytes:
        ...
    def send(self, topic: str, topic_data_type: str, message: roslibpy.Message) -> None:
        ...

class Image:
    def __init__(self, subscriber: Subscriber, topic: str = "/camera/image_raw"):
        self.subscriber = subscriber
        self.topic = topic

    def subscribe(self, save_path: Optional[str] = None) -> Optional[bytes]:
        try:
            subscribe_msg = {
                "op": "subscribe"
            }
            self.subscriber.send( self.topic, 'sensor_msgs/Image', subscribe_msg )

            raw = self.subscriber.receive_binary()
            if not raw:
                print("[Image] No data received from subscriber")
                return None

            if isinstance(raw, bytes):
                raw = raw.decode("utf-8")

            msg = json.loads(raw)
            msg = msg["msg"]

            # Extract metadata
            height = msg["height"]
            width = msg["width"]
            encoding = msg["encoding"]
            data_b64 = msg["data"]

            # Decode base64 to raw bytes
            image_bytes = base64.b64decode(data_b64)
            img_np = np.frombuffer(image_bytes, dtype=np.uint8)

            # Handle encoding
            if encoding == "rgb8":
                img_np = img_np.reshape((height, width, 3))
                img_cv = cv2.cvtColor(img_np, cv2.COLOR_RGB2BGR)  # convert to BGR for OpenCV
            elif encoding == "bgr8":
                img_cv = img_np.reshape((height, width, 3))
            elif encoding == "mono8":
                img_cv = img_np.reshape((height, width))
            else:
                print(f"[Image] Unsupported encoding: {encoding}")
                return None

            # Save image
            if save_path is None:
                downloads_dir = Path.home() / "Downloads"
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                save_path = downloads_dir / f"image_{timestamp}.png"

            Path(save_path).parent.mkdir(parents=True, exist_ok=True)
            cv2.imwrite(str(save_path), img_cv)
            print(f"[Image] Saved to {save_path}")
            return img_cv

        except Exception as e:
            print(f"[Image] Failed to receive or decode: {e}")
            return None
