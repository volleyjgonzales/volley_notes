import collections
import time
import rclpy

rclpy.init()
node = rclpy.create_node("probe_rest_api_endpoints")
end = time.monotonic() + 6.0
while time.monotonic() < end:
    rclpy.spin_once(node, timeout_sec=0.2)
by_prefix = collections.defaultdict(list)
names = [n for n, _ in node.get_topic_names_and_types(no_demangle=True)]
for topic in names:
    for kind, infos in (("W", node.get_publishers_info_by_topic(topic, no_mangle=True)),
                        ("R", node.get_subscriptions_info_by_topic(topic, no_mangle=True))):
        for info in infos:
            if "rest_api" in info.node_name or info.node_namespace.startswith("/rest_api"):
                prefix = bytes(info.endpoint_gid[:12]).hex(".")
                by_prefix[prefix].append(f"{kind} {topic}")
for prefix, eps in by_prefix.items():
    print(f"participant prefix {prefix}: {len(eps)} endpoints")
    for e in sorted(eps)[:12]:
        print("   ", e)
    if len(eps) > 12:
        print("    …")
rclpy.shutdown()
