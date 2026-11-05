import time
import rclpy

rclpy.init()
node = rclpy.create_node("probe_unrelated")
deadline = time.monotonic() + 20.0
while time.monotonic() < deadline:
    rclpy.spin_once(node, timeout_sec=0.5)
names = node.get_node_names_and_namespaces()
bay7 = sorted(f"{ns}/{name}" for name, ns in names if ns.startswith("/bay/b7"))
print(f"held one node with no clients for 20 s; graph: {len(names)} nodes, bay 7: {bay7 or '-'}")
node.destroy_node()
rclpy.shutdown()
