import socket
import json
import websocket._core as websocket
import base64

class WebSocketManager:
    def __init__(self, url: str, local_ip: str):
        self.url = url
        self.local_ip = local_ip
        self.ws = None

    def connect(self):
        if self.ws is None or not self.ws.connected:
            try:
                # Use websocket.create_connection instead of manual socket management
                self.ws = websocket.create_connection(self.url)
                print("[WebSocket] Connected")
            except Exception as e:
                print(f"[WebSocket] Connection error: {e}")
                self.ws = None

    def send(self, message: dict):
        self.connect()
        if self.ws:
            try:
                # Ensure message is JSON serializable
                json_msg = json.dumps(message)
                self.ws.send(json_msg)
            except TypeError as e:
                print(f"[WebSocket] JSON serialization error: {e}")
                self.close()
            except Exception as e:
                print(f"[WebSocket] Send error: {e}")
                self.close()


    def receive_binary(self) -> bytes:
        self.connect()
        if self.ws:
            try:
                raw = self.ws.recv()  # raw is JSON string (type: str)
                return raw
            except Exception as e:
                print(f"Receive error: {e}")
                self.close()
        return b""
    
    def get_topics(self) -> list[tuple[str, str]]:
        self.connect()
        if self.ws:
            try:
                self.send({
                    "op": "call_service",
                    "service": "/rosapi/topics",
                    "id": "get_topics_request_1"
                })
                response = self.receive_binary()
                print(f"[WebSocket] Received response: {response}")
                if response:
                    data = json.loads(response)
                    if "values" in data:
                        topics = data["values"].get("topics", [])
                        types = data["values"].get("types", [])
                        if topics and types and len(topics) == len(types):
                            return list(zip(topics, types))
                        else:
                            print("[WebSocket] Mismatch in topics and types length")
            except json.JSONDecodeError as e:
                print(f"[WebSocket] JSON decode error: {e}")
            except Exception as e:
                print(f"[WebSocket] Error: {e}")
        return []

    def close(self):
        if self.ws and self.ws.connected:
            try:
                self.ws.close()
                print("[WebSocket] Closed")
            except Exception as e:
                print(f"[WebSocket] Close error: {e}")
            finally:
                self.ws = None
