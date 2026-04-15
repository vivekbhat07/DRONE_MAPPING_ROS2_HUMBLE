#!/usr/bin/env python3
"""
drone_waypoint_follower.py
==========================
ROS2 Humble node that flies the 'drone' model in Gazebo Classic 11
along a rectangular loop over the city, publishing cmd_vel to the
libgazebo_ros_planar_move plugin.

Topics published:
  /drone/cmd_vel   (geometry_msgs/Twist)   – velocity commands

Topics subscribed:
  /drone/odom      (nav_msgs/Odometry)     – current pose

Run:
  ros2 run <your_package> drone_waypoint_follower
  OR directly:
  python3 drone_waypoint_follower.py
"""

import math
import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist
from nav_msgs.msg import Odometry


# ── Waypoints the drone will visit in order (X, Y, Z) ──────────────────────
# Z is kept constant at 60 m.  The planar_move plugin only controls X/Y, so
# we set the initial pose in the .world file at Z=60 and it stays there.
WAYPOINTS = [
    (0.0,    0.0,   5.0),   # A - start (odom origin)
    (94.0,  0.0,   5.0),   # B - first corner  (94 - (-110) = 204)
    (94.0,  121.0, 5.0),   # C - second corner
    (0.0,    121.0, 5.0),   # D - third corner
    (0.0,    0.0,   5.0),   # A - back to start (LOOP CLOSURE!)
]

CRUISE_SPEED   = 2.0   # m/s forward speed
YAW_GAIN       = 0.5   # proportional gain for heading correction
ARRIVAL_RADIUS = 2.0   # metres – switch to next waypoint when within this dist


class DroneWaypointFollower(Node):
    def __init__(self):
        super().__init__("drone_waypoint_follower")

        self.pub_cmd = self.create_publisher(Twist, "/drone/cmd_vel", 10)
        self.sub_odom = self.create_subscription(
            Odometry, "/drone/odom", self._odom_cb, 10
        )

        self.current_pose = None
        self.wp_index = 0
        self.loop_count = 0

        # Control loop at 20 Hz
        self.timer = self.create_timer(0.05, self._control_loop)
        self.get_logger().info("Drone waypoint follower started. Waypoints loaded.")

    # ── Odometry callback ───────────────────────────────────────────────────
    def _odom_cb(self, msg: Odometry):
        self.current_pose = msg.pose.pose

    # ── Main control loop ───────────────────────────────────────────────────
    def _control_loop(self):
        if self.current_pose is None:
            return   # waiting for first odom message

        target = WAYPOINTS[self.wp_index]
        cx = self.current_pose.position.x
        cy = self.current_pose.position.y

        dx = target[0] - cx
        dy = target[1] - cy
        dist = math.hypot(dx, dy)

        # ── Arrived at waypoint? ────────────────────────────────────────────
        if dist < ARRIVAL_RADIUS:
            self.wp_index = (self.wp_index + 1) % len(WAYPOINTS)
            if self.wp_index == 0:
                self.loop_count += 1
                self.get_logger().info(
                    f"Completed loop #{self.loop_count}. Starting again..."
                )
            else:
                self.get_logger().info(
                    f"Reached waypoint {self.wp_index - 1}. "
                    f"Heading to waypoint {self.wp_index}: "
                    f"({WAYPOINTS[self.wp_index][0]}, {WAYPOINTS[self.wp_index][1]})"
                )
            return

        # ── Extract current yaw from quaternion ─────────────────────────────
        q = self.current_pose.orientation
        siny = 2.0 * (q.w * q.z + q.x * q.y)
        cosy = 1.0 - 2.0 * (q.y * q.y + q.z * q.z)
        current_yaw = math.atan2(siny, cosy)

        # ── Desired heading to target ────────────────────────────────────────
        desired_yaw = math.atan2(dy, dx)
        yaw_error = desired_yaw - current_yaw

        # Normalise to [-pi, pi]
        while yaw_error >  math.pi: yaw_error -= 2.0 * math.pi
        while yaw_error < -math.pi: yaw_error += 2.0 * math.pi

        # ── Build Twist command ──────────────────────────────────────────────
        cmd = Twist()
        # Forward speed – slow down when yaw error is large
        cmd.linear.x = CRUISE_SPEED * max(0.0, math.cos(yaw_error))
        cmd.angular.z = YAW_GAIN * yaw_error

        self.pub_cmd.publish(cmd)


def main(args=None):
    rclpy.init(args=args)
    node = DroneWaypointFollower()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
