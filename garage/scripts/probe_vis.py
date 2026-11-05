import time
import rclpy
from rclpy.qos import QoSProfile, DurabilityPolicy, ReliabilityPolicy
from visualization_msgs.msg import MarkerArray

rclpy.init()
node = rclpy.create_node("probe_vis")
topics = ["/vis/agvs", "/vis/bays", "/vis/nodes", "/vis/environment", "/vis/trays"]
seen = {}
for t in topics:
    infos = node.get_publishers_info_by_topic(t)
for t in topics:
    qos = QoSProfile(depth=1, durability=DurabilityPolicy.VOLATILE, reliability=ReliabilityPolicy.RELIABLE)
    node.create_subscription(MarkerArray, t, lambda m, t=t: seen.setdefault(t, (len(m.markers), m.markers[0].header.frame_id if m.markers else "-")), qos)
end = time.monotonic() + 10
while time.monotonic() < end:
    rclpy.spin_once(node, timeout_sec=0.2)
for t in topics:
    pubs = node.get_publishers_info_by_topic(t)
    d = pubs[0].qos_profile.durability.name if pubs else "-"
    print(f"{t}: publishers={len(pubs)} durability={d} -> {seen.get(t, 'no message in 10 s')}")
rclpy.shutdown()
