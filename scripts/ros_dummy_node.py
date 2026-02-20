#!/usr/bin/env python3
"""Simple ROS1 dummy node for debug-tool practical tests."""

import rospy
from std_msgs.msg import Header


def main() -> None:
    rospy.init_node("dummy_debug_node", anonymous=False)
    pub = rospy.Publisher("/debug_header", Header, queue_size=10)
    rate = rospy.Rate(10)
    seq = 0

    while not rospy.is_shutdown():
        msg = Header()
        msg.seq = seq
        msg.stamp = rospy.Time.now()
        msg.frame_id = "debug"
        pub.publish(msg)
        seq += 1
        rate.sleep()


if __name__ == "__main__":
    main()
