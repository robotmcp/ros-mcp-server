#!/usr/bin/env python
import rospy
from geometry_msgs.msg import Twist


class CmdVelLatchRepeater(object):
    def __init__(self):
        self.in_topic = rospy.get_param("~in_topic", "/cmd_vel")
        self.out_topic = rospy.get_param("~out_topic", "/cmd_vel_to_motor")
        self.rate_hz = rospy.get_param("~rate_hz", 10.0)
        self.stop_on_shutdown = rospy.get_param("~stop_on_shutdown", True)

        self.pub = rospy.Publisher(self.out_topic, Twist, queue_size=5)
        self.sub = rospy.Subscriber(self.in_topic, Twist, self.cb, queue_size=5)

        self.last_cmd = None
        rospy.loginfo(
            "latch repeater: %s -> %s @ %.1fHz", self.in_topic, self.out_topic, self.rate_hz
        )

    def cb(self, msg):
        self.last_cmd = msg

    def spin(self):
        r = rospy.Rate(self.rate_hz)
        while not rospy.is_shutdown():
            if self.last_cmd is not None:
                self.pub.publish(self.last_cmd)
            r.sleep()

    def shutdown(self):
        if self.stop_on_shutdown:
            self.pub.publish(Twist())


if __name__ == "__main__":
    rospy.init_node("cmd_vel_latch_repeater")
    node = CmdVelLatchRepeater()
    rospy.on_shutdown(node.shutdown)
    node.spin()
