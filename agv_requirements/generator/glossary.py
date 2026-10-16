"""Glossary: (slug, term, variants that should auto-link, definition).

Definitions may mention 'Figure {name}' placeholders, which build.py replaces
with the real figure number so the site builder can link them.
"""

TERMS = [
    ("vda5050", "VDA5050", ["VDA5050", "VDA 5050"],
     "Open interface standard from the German automotive and machinery associations (VDA and VDMA) for "
     "communication between AGVs and a fleet manager. Messages are JSON documents sent over MQTT, one topic "
     "per message type. See Figure {vda_topics}."),
    ("mqtt", "MQTT", ["MQTT"],
     "Lightweight publish/subscribe messaging protocol. Clients publish messages to named topics through a "
     "broker, and every client subscribed to that topic receives them."),
    ("broker", "MQTT broker", ["MQTT broker", "broker"],
     "The server that receives every published message and forwards it to the subscribers of its topic. It "
     "also stores retained messages and publishes Last Will messages."),
    ("last-will", "Last Will", ["Last Will"],
     "A message a client hands to the broker when it connects. If the client later disconnects without saying "
     "goodbye (crash, network loss), the broker publishes that message for it. VDA5050 uses it to announce "
     "CONNECTIONBROKEN."),
    ("retained", "Retained message", ["retained flag", "retain flag", "retained"],
     "A message published with MQTT's retain flag. The broker keeps the latest one per topic and hands it to "
     "any client that subscribes later, so a fleet manager that starts after the AGV still gets the factsheet."),
    ("fleet-manager", "Fleet manager", ["fleet manager", "master control"],
     "The central server that plans routes and sends orders to AGVs. VDA5050 calls it master control; in "
     "this project it is Volley's system."),
    ("topic", "Topic", ["MQTT topic"],
     "The address a message is published to, for example uagv/v2/HITO/AGV001/state."),
    ("order", "order (topic)", [],
     "VDA5050 message from the fleet manager giving the AGV its route as nodes and edges, with optional actions "
     "on each. Structure: Figure {uml_1}."),
    ("instantactions", "instantActions (topic)", [],
     "VDA5050 message carrying commands the AGV must act on immediately, such as cancelOrder, startPause or "
     "stopPause. Structure: Figure {uml_2}."),
    ("state", "state (topic)", [],
     "The AGV's full status report: order progress, position, loads, action progress, battery, errors and "
     "safety state. Structure: Figure {uml_5}."),
    ("visualization", "visualization (topic)", [],
     "A lighter, higher-rate message with just position and velocity, meant for live display. "
     "Structure: Figure {uml_5}."),
    ("connection", "connection (topic)", [],
     "Reports ONLINE, OFFLINE or CONNECTIONBROKEN. The CONNECTIONBROKEN version is registered as the Last Will. "
     "Structure: Figure {uml_2}."),
    ("factsheet", "factsheet (topic)", ["factsheet"],
     "The AGV's self-description: type, physical limits, supported features and the custom actions it "
     "understands. Structure: Figure {uml_2}."),
    ("commonmessage", "commonMessage (topic)", ["commonMessage"],
     "HITO's own extra topic, not part of VDA5050, carrying RFID, tape-sensor and lidar-field values. "
     "See Figure {5_1_common_message}."),
    ("instant-action", "Instant action", ["instant action", "instant actions"],
     "An action sent on the instantActions topic rather than attached to a node or edge, so it runs as soon "
     "as it arrives."),
    ("node", "Node", [],
     "A waypoint in an order. The AGV drives from node to node along edges; nodes can carry a target heading "
     "and actions."),
    ("edge", "Edge", [],
     "The path segment between two nodes in an order."),
    ("horizon", "Base and horizon", ["release horizon", "horizon"],
     "The released part of an order (base) may be driven. The unreleased part (horizon) is a preview the AGV "
     "must not enter until the fleet manager releases it."),
    ("blockingtype", "blockingType", ["blockingType"],
     "Says whether an action stops other things while it runs: NONE (nothing waits), SOFT (driving waits) or "
     "HARD (everything waits)."),
    ("theta", "theta (θ)", ["theta"],
     "Heading angle in radians, measured counter-clockwise from the map's x axis."),
    ("state-estimate", "State estimate", ["state estimate"],
     "The AGV's best estimate of its position and heading, fused from wheel odometry, RFID reads and the tape "
     "sensor."),
    ("magnetic-tape", "Magnetic tape", ["magnetic tape"],
     "A strip on the floor, here assumed 50 mm wide, that the AGV's sensor array follows to stay on its path."),
    ("rfid", "RFID tag", ["RFID tag", "RFID"],
     "Floor tags the AGV reads to know exactly which node it is at."),
    ("hmi", "HMI", ["HMI"],
     "Human-machine interface: the AGV's own on-board screen."),
    ("motion-primitive", "Motion primitive", ["motion primitive", "motion primitives"],
     "One kind of movement the controller handles as a unit, such as straight driving, a curve, an in-place "
     "turn or strafing."),
    ("protective-field", "Protective field", ["protective field", "protective fields", "lidar field", "laser field"],
     "An area watched by the safety laser scanner (lidar). If anything enters the active field, the AGV stops. "
     "Larger fields are needed at higher speeds."),
    ("strafe", "Strafe / sideslip", ["strafe", "strafing", "sideslip"],
     "Moving sideways without turning, possible on vehicles with omnidirectional wheels."),
    ("composition", "UML composition", ["UML composition"],
     "A diagram line with a filled diamond meaning the object on the right only exists inside the object on "
     "the left; in JSON, it is a nested object or array."),
]
