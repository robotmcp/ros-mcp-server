import cv2
import rclpy
from cv_bridge import CvBridge
from rclpy.node import Node
from rclpy.qos import HistoryPolicy, QoSProfile, ReliabilityPolicy
from sensor_msgs.msg import Image


class ImagePublisher(Node):
    def __init__(self):
        super().__init__("image_publisher")

        qos_profile = QoSProfile(
            reliability=ReliabilityPolicy.RELIABLE, history=HistoryPolicy.KEEP_LAST, depth=10
        )

        # create publisher
        self.publisher_ = self.create_publisher(Image, "camera/rgb/image_raw", qos_profile)
        self.bridge = CvBridge()

        # GStreamer pipeline
        gstreamer_str = (
            "udpsrc address=230.1.1.1 port=1720 multicast-iface=<interface_name> ! "
            "application/x-rtp, media=video, encoding-name=H264 ! "
            "rtph264depay ! h264parse ! avdec_h264 ! videoconvert ! "
            "video/x-raw,width=1280,height=720,format=BGR ! appsink drop=1"
        )

        self.cap = cv2.VideoCapture(gstreamer_str, cv2.CAP_GSTREAMER)

        # create timer for periodic frame reading
        self.timer = self.create_timer(0.016, self.timer_callback)  # ~60fps

    def timer_callback(self):
        if self.cap.isOpened():
            ret, frame = self.cap.read()
            if ret:
                # resize frame to 320x240
                resized = cv2.resize(frame, (320, 240), interpolation=cv2.INTER_AREA)

                # OpenCV frame → ROS Image message conversion
                img_msg = self.bridge.cv2_to_imgmsg(resized, encoding="bgr8")
                img_msg.header.stamp = self.get_clock().now().to_msg()
                img_msg.header.frame_id = "camera_link"
                self.publisher_.publish(img_msg)

            else:
                self.get_logger().warn("Frame capture failed")

    def destroy_node(self):
        self.cap.release()
        cv2.destroyAllWindows()
        super().destroy_node()


def main(args=None):
    rclpy.init(args=args)
    node = ImagePublisher()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
