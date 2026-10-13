"""Captions shown underneath each diagram: (short title, explanation)."""

CAPTIONS = {
    "robot_key": (
        "How to read the robot",
        "Every diagram shows the AGV from above. The orange bar marks the front and the chevron points the "
        "direction the vehicle is facing; the two short lines mark the rear. Grey bands are the magnetic tape, "
        "blue dots are order nodes and small orange squares are RFID tags. A faded, dashed robot is a pose the "
        "AGV is moving to or came from, not a second vehicle.",
    ),
    "overview": (
        "Status of all 52 requirements",
        "One tile per requirement, coloured and lettered by how HITO answered it. Read the bar underneath for "
        "the totals: 12 already work, 17 will be built, 8 are conditional (they depend on testing, discussion "
        "or a counter-proposal), and 15 are closed without new work for different reasons — 3 as duplicates, "
        "6 as process items, 3 blocked on hardware or clarification, and 3 rejected as not feasible.",
    ),
    "estimates": (
        "How long HITO says the work takes",
        "Each bar is one requirement that has an estimate. The solid part is development days, the pale part "
        "is testing days. Three items dominate at 30 + 30 days: speed-based tracking parameters (7.4), early "
        "braking for a short final edge (7.7) and remote joystick recovery (8.6). Adding every bar end to end "
        "gives 244 + 196 days, but the source doesn't say how much can run in parallel, so treat that as an "
        "upper bound, not a schedule.",
    ),
    "1_1_single_node_rotation": (
        "Turning on the spot when the order has only one node",
        "Volley wants to send an order that contains only the node the AGV is already standing on, with a new "
        "heading, so the AGV simply turns in place. On the left is today's behaviour: the firmware ignores a "
        "one-node order and needs a second node before it moves. On the right is the requirement: the same "
        "AGV on N1 turns from facing right (0°) to facing up (90°) without driving anywhere.",
    ),
    "1_2_final_node_theta": (
        "Turning to the final node's heading",
        "The AGV drives along N1 → N4. When it reaches N4 it is still facing the direction it drove in (0°). "
        "If the order says N4's heading is −90° (facing down), the AGV must turn to that heading before the "
        "order counts as done. HITO says this already works.",
    ),
    "1_3_driving_flag": (
        "When the 'driving' flag is true",
        "Time runs left to right. The top trace is the wheel speed the controller commands; the bottom trace is "
        "the driving flag the AGV reports. The flag must be true whenever the wheels are commanded to turn — "
        "including during an in-place rotation, where the AGV isn't changing position but its wheels are "
        "moving (1.3). It must drop to false as soon as the commanded speed is zero (1.4).",
    ),
    "2_1_mqtt_session": (
        "Who tells the fleet manager that an AGV has dropped off",
        "Read top to bottom as a message sequence between four parties. When the VDA5050 agent connects, it "
        "hands the MQTT broker a 'Last Will': a message the broker should publish on its behalf if the "
        "connection dies (2.2). It then publishes the factsheet with the retained flag, so the broker keeps a "
        "copy for any subscriber that connects later (2.1). If the firmware or the agent crashes, the "
        "connection drops and the broker — not the AGV — publishes CONNECTIONBROKEN (2.3, 2.4). That's why "
        "HITO says 2.3 and 2.4 aren't its responsibility, and why they only work once 2.2 is done.",
    ),
    "2_5_instant_actions": (
        "When an instant action may be reported as finished",
        "Each line is the life of one instant action, left to right. The red cross marks the moment the AGV "
        "must not yet say FINISHED; the green tick marks the earliest moment it may. For any instant action "
        "(2.5), merely receiving the command isn't enough — the firmware has to have actually applied it. For "
        "stopPause (2.6), the AGV may only report FINISHED once it is back in automatic driving mode, not when "
        "the resume was merely requested.",
    ),
    "2_7_change_control": (
        "Interface documentation and joint sign-off",
        "The flow chart shows the approval rule both parties agreed to: any change goes through both Volley "
        "and HITO before release. The left list names which requirements this rule covers (interface "
        "changes, the error-type strings and the rotation action type). The right list shows the two "
        "documents HITO owes: a list of every place it departs from the VDA5050 standard (2.7) and full "
        "documentation of its custom messages (2.8). Note HITO's remark that keeping 2.7 up to date in "
        "future is outside its scope.",
    ),
    "3_1_cancel_stop": (
        "Where the AGV stops after its order is cancelled",
        "The chart plots speed (up) against distance along the path (right); the dashed orange line is the "
        "moment the cancel arrives. The solid blue curve is a slower AGV that can brake to zero by the next "
        "node, N2, so it must stop there (3.1 — HITO will try). The dashed green curve is a faster AGV that "
        "can't stop by N2 in time, so it carries on and stops at N3 instead (3.2 — already works).",
    ),
    "3_3_release_horizon": (
        "Stopping at the edge of the released path",
        "Fleet managers release a route in pieces: solid edges are released and the AGV may drive them; dashed "
        "edges are planned but not yet released. Top row: nothing beyond N4 has been released by the time the "
        "AGV gets there, so it must stop at N4 (3.3). Bottom row: the fleet manager releases the next stretch "
        "before the AGV arrives, so it must drive straight through N4 without stopping (3.4). Both already work.",
    ),
    "3_5_off_tape": (
        "Off-tape detection only while moving",
        "Time runs left to right. The AGV raises an off-tape fault if it loses the tape for too long, but that "
        "timer should only run while the wheels are commanded to move (blue 'armed' blocks). In the middle the "
        "AGV is standing still and the sensor briefly loses the tape (red hatched block); because the timer "
        "is off, no fault is raised. HITO says this already works.",
    ),
    "3_6_precision": (
        "How precisely the AGV must stop and turn",
        "Left: the AGV approaches a node from the left. It must stop inside the blue circle (10 mm from the "
        "node centre) and must never pass the centre line — the red hatched half is forbidden even inside the "
        "circle. HITO says this is standard behaviour (3.6). Right: after turning on the spot, the AGV's "
        "heading must land inside the blue wedge (±1.5° of the target), and while turning it may swing past "
        "the target by less than 0.5° (the orange arc). The angles are drawn 20 times larger so they're "
        "visible. HITO rejected the 0.5° overshoot limit (3.7).",
    ),
    "4_publish_rates": (
        "Making message rates configurable",
        "Each tick mark is one message sent during a one-second window. Volley wants the rates of the "
        "visualization message (4.1) and of commonMessage (4.2) read from the AGV's iconfig.yaml file, so "
        "they can be tuned without new firmware. Here 10 Hz and 2 Hz are example values. These settings don't "
        "exist today; HITO wants to discuss the use case first.",
    ),
    "5_1_common_message": (
        "New fields in commonMessage",
        "The dark panel is what the AGV's own screen shows today. The light panel is the commonMessage the "
        "AGV sends to the fleet manager, and the dashed arrows show which on-screen value each new field "
        "should carry: RFID signal strength (5.1), the RFID tag read (5.13), the tape sensor reading (5.3) and "
        "which laser field is active (5.15). The tape sensor here reads nothing, so the field is an empty "
        "string — that's what Volley asked for. The note underneath explains HITO's different proposal.",
    ),
    "5_4_errors": (
        "How errors should be reported",
        "Every error code shown on the AGV's screen (left) must also appear in the state message sent to the "
        "fleet manager (5.4). Each error entry should use an agreed name from a fixed list rather than free "
        "text (5.5), always include a readable description (5.8), and may include a hint for the operator "
        "(5.9). The fixed list of names can only change if both companies agree (5.6, 5.7). HITO said it "
        "didn't understand what errorHint means.",
    ),
    "5_10_pose": (
        "Reporting where the AGV actually is",
        "Both panels show an AGV following a curved stretch of tape; dots are the positions it reports, and "
        "the short line on each dot is the heading it reports. Left, the wrong way: the AGV only adds the "
        "distance travelled to x and keeps y and the heading frozen at whatever the first RFID tag said, so "
        "its reported track runs in a straight line away from where it really is. Right, the required way: "
        "x, y and heading all come from the AGV's position estimate, so the reported dots follow the real "
        "path. Velocity is then the rate of change of those values. HITO says all of this already works; only "
        "the reporting rate is still to be agreed.",
    ),
    "6_rotation_direction": (
        "Choosing which way the AGV turns",
        "Both rows show the AGV turning from 0° to 180° on the same spot, but in opposite directions. Turning "
        "clockwise it passes through facing down; turning counter-clockwise it passes through facing up. "
        "Volley wants to pick the direction by attaching an action to the node (example on the right) — "
        "useful when one side of the AGV would hit something during the turn. 'blockingType NONE' means the "
        "action doesn't pause anything else. The action's name and fields still have to be agreed (6.2).",
    ),
    "7_1_tracking_direction": (
        "Following the tape forwards versus sideways",
        "Each row is one load condition: no load, an empty pallet (dashed box), and the heaviest allowed "
        "load (filled box). Left column: the AGV drives forwards along the tape, which must stay stable up to "
        "full speed in every case — HITO says it already does (7.1). Right column: the AGV is turned "
        "crossways and slides sideways along the tape (strafing). HITO says this vehicle can't do that "
        "stably at high speed (7.3).",
    ),
    "7_4_gain_scheduling": (
        "Tuning the tape-following controller",
        "The grid shows which controller settings (K1 to K5) the AGV uses at each combination of speed "
        "(columns) and load (rows). Moving left to right, the settings change with speed — that's 7.4. "
        "Moving top to bottom, they stay the same whatever the load — that's 7.5. The two requirements "
        "constrain different directions of the grid, so meeting one doesn't guarantee the other, even though "
        "HITO closed 7.5 as a duplicate. The note explains why one set for all loads is the only practical "
        "option: the AGV can't weigh its load (8.5).",
    ),
    "7_6_lateral_error": (
        "How far the AGV may drift from the tape",
        "The blue band is ±10 mm either side of the tape centre, and the wavy line is how far the AGV wanders "
        "as speed and load increase from left to right. Slow and light, it stays inside the band; fast and "
        "heavy, it swings out. The requirement is to stay inside the band at every speed and load. HITO says "
        "it can't guarantee that with this vehicle.",
    ),
    "7_7_deceleration": (
        "Braking early enough for a short last edge",
        "The bottom strip is the route: two long edges and then a short final edge into N4. The orange "
        "bracket is how much distance the AGV needs to stop from full speed — longer than the final edge. "
        "The chart above plots speed against distance. Red dashed: today the AGV only starts braking once it "
        "reaches the final edge, so it runs past N4. Blue: the requirement is to start braking back on edge "
        "2, so it reaches zero exactly at N4 (7.7). Doing that means working out the stopping point across "
        "several edges, not just the last one (7.8, 7.9).",
    ),
    "8_1_lidar_fields": (
        "Choosing and overriding the lidar safety zone",
        "The orange shapes in front of the AGV are lidar protective fields: if anything enters the active "
        "one, the AGV stops. Larger fields are needed at higher speeds. Volley wants all 64 fields the "
        "scanner supports to be usable (8.1), with the AGV picking one automatically from its speed, its type "
        "of motion and how far the load sticks out (8.2), shown as the selector on the right. The bottom "
        "strip shows 8.4: an operator can remotely override a protective stop, and the override applies only "
        "to one edge (orange) before switching off again.",
    ),
    "8_3_pallet_payload": (
        "Confirming the pallet is seated and knowing its weight",
        "Left, viewed from the side: the AGV lifts a pallet by pushing pins up into cups underneath it. In "
        "the first picture the pins sit in the cups; in the second the AGV is slightly off and a pin presses "
        "against the pallet beside its cup. Volley wants the AGV to detect which case it is in and report it "
        "(8.3). Right: Volley wants the load's weight estimated from the pressure in the lift cylinder (8.5). "
        "HITO says the current hardware has no sensor for either.",
    ),
    "8_6_joystick": (
        "Driving the AGV back onto the tape by remote control",
        "The AGV has slid off the tape, so its automatic mode stops. An operator uses a remote joystick, "
        "whose commands travel over a new MQTT topic, to drive it back onto the tape (blue dashed path) so "
        "it can resume normal operation. HITO agreed, at 30 + 30 days.",
    ),
}
