import time
import rclpy

rclpy.init()
node = rclpy.create_node("probe_graph")
end = time.monotonic() + 6.0
while time.monotonic() < end:
    rclpy.spin_once(node, timeout_sec=0.2)
for service in ("/bay/b7/confirm_insert", "/bay/b7/confirm_retrieve", "/bay/b7/command"):
    request = "rq" + service + "Request"
    response = "rr" + service + "Reply"
    readers = node.get_subscriptions_info_by_topic(request, no_mangle=True)
    writers = node.get_publishers_info_by_topic(response, no_mangle=True)
    print(f"{service}: request readers={len(readers)} response writers={len(writers)}")
    for kind, infos in (("  rq reader", readers), ("  rr writer", writers)):
        for info in infos:
            gid = bytes(info.endpoint_gid[:12]).hex()
            print(f"{kind} {info.node_namespace}/{info.node_name} gid={gid}")
node.destroy_node()
rclpy.shutdown()
