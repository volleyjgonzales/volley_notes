import time
import rclpy
from interfaces.srv import BayCommand, SetPayloadInfo
from std_srvs.srv import Trigger

rclpy.init()
node = rclpy.create_node("probe_clients")
targets = [
    (SetPayloadInfo, "/bay/b7/confirm_insert"),
    (Trigger, "/bay/b7/confirm_retrieve"),
    (BayCommand, "/bay/b7/command"),
    (Trigger, "/central/start"),
]
clients = [(name, node.create_client(srv, name)) for srv, name in targets]
deadline = time.monotonic() + 20.0
ready = {}
while time.monotonic() < deadline and len(ready) < len(clients):
    rclpy.spin_once(node, timeout_sec=0.2)
    for name, client in clients:
        if name not in ready and client.service_is_ready():
            ready[name] = round(20.0 - (deadline - time.monotonic()), 1)
for name, _ in clients:
    print(f"{name}: {'ready after ' + str(ready[name]) + ' s' if name in ready else 'NOT ready after 20 s'}")
node.destroy_node()
rclpy.shutdown()
