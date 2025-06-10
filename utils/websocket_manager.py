import json
import roslibpy

class WebSocketManager:
    def __init__(self, ip: str, port: 9090):
        self.ip = ip
        self.port = port
        self.ws = None

    def connect(self):
        if self.ws is None or not self.ws.is_connected:
            self.ws = roslibpy.Ros( self.ip, self.port )
            self.ws.run()
            print("[roslibpy] Connected!")

    def send(self, topic: str, topic_data_type: str, message: roslibpy.Message):
        self.connect()
        if self.ws:
            try:
                topic = roslibpy.Topic( self.ws, topic, topic_data_type )
                topic.publish( message )
                self.close()
            except TypeError as e:
                print(f"[roslibpy] JSON serialization error: {e}")
                self.close()
            except Exception as e:
                print(f"[roslibpy] Send error: {e}")
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
        if self.ws and self.ws.is_connected:
            try:
                self.ws.close()
                print("[WebSocket] Closed")
            except Exception as e:
                print(f"[WebSocket] Close error: {e}")
            finally:
                self.ws = None
