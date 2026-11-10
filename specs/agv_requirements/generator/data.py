"""Volley's AGV requirements and HITO's responses, curated from HITO's workbook.

Current source: CN&EN停车场功能需求20261109_V1.1.xlsx (HITO V1.1, 9 Nov 2026, with Volley's
remarks of 9 Nov added as column G). Earlier source: Functional_requirements-停车场功能需求20261013_V1_0_1.pdf.

Each row of R: id, status, requirement (paraphrase of the English column), HITO response
(paraphrase), dev days, test days (None = '/' in source). Status is HITO's position, not ours;
Volley's view is in VERDICT, and the verbatim cells (including Volley's remarks) live in
sheet.json, written by import_sheet.py.
"""
import json
import os

SOURCE = {
    "title": "CN&EN停车场功能需求20261109_V1.1.xlsx",
    "version": "V1.1",
    "date": "9 Nov 2026",
    "file_id": "1--QLW1pHXLbJCk7dSXgfBFyFTqcWJEO8",
    "en_gid": "1204834442",  # Sheets tab id of the EN tab
    "volley_remarks": "Volley remarks of 9 Nov 2026 (column G, added by Dan Ambrosio)",
    # The original PDF (v1.0.1, 13 Oct 2026) arrived by email from Crystal Wang (HITO);
    # Anne Lu forwarded it to the team the same day.
    "pdf_title": "Functional_requirements-停车场功能需求20261013_V1_0_1.pdf",
    "pdf_mail": "https://mail.google.com/mail/?authuser=jon@volleyautomation.com#all/thread-f:1878945626799308276",
}
SHEET_URL = f"https://docs.google.com/spreadsheets/d/{SOURCE['file_id']}/edit?gid={SOURCE['en_gid']}#gid={SOURCE['en_gid']}"


def sheet_row_url(row):
    """Deep link that opens the EN tab with the row's id cell selected."""
    return f"https://docs.google.com/spreadsheets/d/{SOURCE['file_id']}/edit?gid={SOURCE['en_gid']}#gid={SOURCE['en_gid']}&range=A{row}"


GROUPS = {
    "1": "Order execution and rotation at nodes",
    "2": "MQTT connection, factsheet and action reporting",
    "3": "Cancellation, release horizon and stopping precision",
    "4": "Message publishing frequency",
    "5": "State, commonMessage and error reporting",
    "6": "Rotation direction set by actions",
    "7": "Magnetic tape tracking and deceleration",
    "8": "Lidar fields, payload, coupling and remote control",
}

R = [
    ("1.1", "implement", "When the AGV receives an order containing only a single node, and that node is the AGV's current node, if the theta in the order differs from the current theta, the AGV must rotate in place to the commanded theta.",
     "Can be implemented. Current logic requires two nodes. Firmware update after successful testing.", 10, 10),
    ("1.2", "works", "When the AGV reaches the final node of an order and that node's theta differs from the current theta, the AGV must rotate to the theta specified for the final node.",
     "Already how it works.", None, None),
    ("1.3", "implement", "During all edge movements and rotational movements, the AGV must report its driving state as true whenever the commanded wheel speed is non-zero.",
     "Can be implemented.", 4, 2),
    ("1.4", "implement", "When the commanded wheel speed is zero, the AGV must report its driving state as false.",
     "Can be implemented.", 4, 2),
    ("2.1", "conditional", "The AGV must publish the factsheet message with the MQTT retained flag set to true.",
     "Factsheet already published (sent twice at startup). Volley to list which topics need the retained flag.", 10, 4),
    ("2.2", "implement", "The AGV must register an MQTT Last Will message on the connection topic, with connectionState set to CONNECTIONBROKEN.",
     "No issues. Firmware update after successful testing.", 6, 4),
    ("2.3", "process", "When the AGV's main firmware shuts down or crashes, the AGV must ensure that the MQTT broker publishes CONNECTIONBROKEN.",
     "Built-in MQTT broker mechanism, unrelated to AGV firmware shutting down or crashing.", None, None),
    ("2.4", "process", "When the AGV's VDA5050 agent shuts down or crashes, the AGV must ensure that the MQTT broker publishes CONNECTIONBROKEN.",
     "AGV cannot guarantee this; governed by the broker's built-in mechanism.", None, None),
    ("2.5", "works", "For an instant action, the AGV may report FINISHED only after the firmware has actually executed and applied the request, not merely because the VDA5050 agent received it.",
     "Already how it works.", None, None),
    ("2.6", "implement", "For the stopPause instant action, the AGV may report FINISHED only after the firmware has returned to the auto-run state.",
     "No issues. Firmware update after successful testing.", 4, 2),
    ("2.7", "implement", "HITO must provide updated interface documentation listing all deviations from the current VDA5050 specification.",
     "Future maintenance is outside HITO's scope. Documentation can be updated.", 10, None),
    ("2.8", "implement", "HITO must fully document all custom messages, including commonMessage: field names, field types, permitted values and example payloads.",
     "Documentation already provided; can be updated later.", 4, None),
    ("2.9", "process", "Any change to the VDA5050 interface or custom messages must be jointly reviewed and approved by Volley and HITO before release.",
     "No issues.", None, None),
    ("3.1", "conditional", "When an order is canceled, if the AGV can decelerate to zero at the next node (given speed, deceleration, remaining edge distance), it must stop at the next node.",
     "Challenging; will try, and update if testing succeeds. Needs a Volley test vehicle. (V1.1 doubled the estimate from 10 + 10.)", 20, 20),
    ("3.2", "works", "When an order is canceled and the AGV cannot decelerate to zero at the next node, it must stop at the node after the next node.",
     "Already how it works.", None, None),
    ("3.3", "works", "When the AGV reaches the last released node while the following edge is not yet released, it must stop at that last released node.",
     "Already how it works.", None, None),
    ("3.4", "works", "If the following edge and node are released before the AGV reaches the last released node, the AGV must pass through without stopping.",
     "Already how it works.", None, None),
    ("3.5", "works", "The AGV must perform time-based off-magnetic-tape detection only when the commanded wheel speed is non-zero.",
     "Already how it works.", None, None),
    ("3.6", "works", "At any node where a stop is required, the AGV must stop within a 10 mm radius of the node center and must not overshoot the node center.",
     "Standard operating procedure, achieved with the lateral magnetic strip. Abnormal conditions to be discussed separately.", None, None),
    ("3.7", "rejected", "After an in-place rotation at a node, the AGV must stop within ±1.5° of the target angle with rotational overshoot of less than 0.5°.",
     "Overshoot below 0.5° is too demanding for the current configuration; in-place rotation at a node is not meant for positioning and depends on floor and environment. A hardware upgrade or gyroscope could be explored later at extra cost (future custom development).", None, None),
    ("4.1", "conditional", "The AGV must publish visualization messages at the frequency set by parameters in iconfig.yaml.",
     "Parameter not currently available. Use case to be discussed.", 6, 4),
    ("4.2", "conditional", "The AGV must publish commonMessage messages at the frequency set by parameters in iconfig.yaml.",
     "Parameter not currently available. Use case to be discussed.", 6, 4),
    ("5.1", "implement", "The AGV must report RFID signal strength in commonMessage, matching the S value on the AGV's screen.",
     "Not currently available but can be added.", 6, 4),
    ("5.3", "conditional", "When the magnetic tape sensor has no reading, the AGV must report it in commonMessage as an empty string or an optional value.",
     "Counter-proposal: a value that stays at 0 for 1 second means the sensor has no reading.", 6, 4),
    ("5.4", "implement", "The AGV must report all error codes shown on the HMI screen in the errors field of the state message.",
     "Missing information will be added later.", 10, 4),
    ("5.5", "conditional", "The AGV must use defined string enumeration values for errorType rather than undefined raw strings.",
     "Can be added after discussion and agreement.", 6, 4),
    ("5.6", "process", "The errorType string values must be jointly reviewed and approved by Volley and HITO before release.",
     "No issues.", None, None),
    ("5.7", "process", "The errorType string values must not change unless both Volley and HITO agree.",
     "No issues.", None, None),
    ("5.8", "process", "The AGV must populate errorDescription for every reported error.",
     "No issues; can be added later. V1.1 files it under the joint working mechanism (blue). (No estimate given.)", None, None),
    ("5.9", "blocked", "The AGV may populate errorHint for any reported error.",
     "HITO does not understand what this means, yet V1.1 quotes 10 + 5 days.", 10, 5),
    ("5.10", "works", "The AGV must report state-estimated x, y and theta in agvPosition in both state and visualization messages, at a TBD Hz frequency to be agreed.",
     "Already how it works. (Frequency still TBD.)", None, None),
    ("5.11", "works", "The AGV must continuously update x, y and theta from its state estimate, not update one axis by edge distance while keeping the other unchanged.",
     "Already how it works.", None, None),
    ("5.12", "works", "The AGV must report theta from its state estimate, not a fixed value derived from the first RFID reading.",
     "Already how it works.", None, None),
    ("5.13", "implement", "The AGV must report the actual RFID reader reading in commonMessage, matching the RFID value on the AGV's screen.",
     "No issues; can be added later.", 6, 4),
    ("5.14", "works", "The AGV must report velocity in visualization: the derivatives of x, y and theta.",
     "Already available.", None, None),
    ("5.15", "implement", "The AGV must report the currently selected laser protective field in commonMessage.",
     "No issues; can be added later.", 6, 4),
    ("6.1", "implement", "The AGV must rotate to a node's theta in the direction given by an action attached to that node with blockingType NONE.",
     "Can be added; detailed requirements to be discussed with Volley first. Firmware update after successful testing.", 10, 5),
    ("6.1.1", "process", "The action type used to specify rotation direction must be jointly reviewed and approved by Volley and HITO.",
     "No issues.", None, None),
    ("7.1", "works", "Unloaded, with empty pallet and at max payload, the AGV must stably track the tape at all longitudinal speeds up to its maximum.",
     "Expected behavior under normal conditions.", None, None),
    ("7.3", "rejected", "Unloaded, with empty pallet and at max payload, the AGV must stably track the tape at all lateral (sideslip / strafe) speeds up to its maximum.",
     "Cannot be implemented: current vehicle model can't do stable high-speed lateral movement.", None, None),
    ("7.4", "implement", "The AGV must schedule tape tracking control parameters dynamically from the commanded speed, not hard-code them per motion primitive.",
     "Feasible. Update after successful testing.", 30, 30),
    ("7.5", "duplicate", "The AGV must schedule tape tracking parameters so a single set covers all payload conditions, not hard-coded per payload weight.",
     "Duplicates a requirement above.", None, None),
    ("7.6", "rejected", "Across all commanded speeds and all payloads, the AGV must keep lateral tape tracking error within 10 mm.",
     "Cannot be guaranteed with the current vehicle model.", None, None),
    ("7.7", "blocked", "Regardless of the final edge's length, the AGV must start decelerating early enough to reach zero at the final node without overshooting.",
     "Difficult. Will attempt later; update if testing succeeds. V1.1 also marks it as needing hardware customization (red), while keeping the 30 + 30 estimate.", 30, 30),
    ("7.8", "duplicate", "The AGV must compute the deceleration start point from the total remaining distance across consecutive edges with the same motion primitive, not only the final edge.",
     "Duplicate. Currently calculations only work along one edge.", None, None),
    ("7.9", "duplicate", "If the final edge is shorter than the stopping distance, the AGV must begin decelerating on an earlier edge.",
     "Duplicates a requirement above.", None, None),
    ("8.1", "implement", "The AGV must use all 64 available laser protective (lidar) fields.",
     "Can be implemented by changing the electrical wiring and adding software.", 20, 20),
    ("8.2", "conditional", "The AGV must select the lidar field from wheel speed, motion primitive and a runtime-configurable payload size offset. Schema to be agreed.",
     "Good idea; can be added after discussion.", 10, 10),
    ("8.3", "blocked", "The AGV must actively confirm whether a pallet is correctly coupled ('pins in cups') and report it via VDA5050.",
     "Current hardware doesn't support it; feasible solution to be discussed.", None, None),
    ("8.4", "implement", "The AGV must support remote override of a laser protective stop during operation, applied edge by edge.",
     "Can be implemented as part of the instant action function.", 10, 10),
    ("8.5", "blocked", "The AGV must estimate payload weight from hydraulic pressure and publish it as payload data in state.",
     "Current hardware doesn't support it; feasible solution to be discussed.", None, None),
    ("8.6", "implement", "The AGV may support remote joystick / remote movement for recovery, e.g. when off the magnetic tape.",
     "Can be implemented with a new topic interface. Update after successful testing.", 30, 30),
]

BY_ID = {r[0]: r for r in R}
assert len(R) == 52

# ---- verbatim sheet cells (sheet.json, from import_sheet.py)
with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "sheet.json"), encoding="utf-8") as _fh:
    SHEET = json.load(_fh)
SHEET_EN = {r["id"]: r for r in SHEET["en"]}
SHEET_CN = {r["id"]: r for r in SHEET["cn"]}
assert set(SHEET_EN) == set(BY_ID), set(SHEET_EN) ^ set(BY_ID)


def source_url(rid):
    return sheet_row_url(SHEET_EN[rid]["row"])


# ---- Volley's position, from the 9 Nov remarks (column G). Curated label; the text is verbatim.
VERDICTS = {
    #  key        label                   meaning
    "fails":    ("Fails Volley test",    "HITO says it already works; Volley's testing shows it doesn't."),
    "partial":  ("Partly works",         "Some of it works; Volley lists what is still missing."),
    "accepted": ("Accepted as is",       "Behaviour differs from the wording but Volley accepts it."),
    "disagree": ("Volley disagrees",     "Volley rejects HITO's reason for not doing it (usually 'needs hardware')."),
    "agree":    ("Volley agrees",        "Volley accepts HITO's answer."),
}
VERDICT = {
    "1.2": "fails", "2.3": "accepted", "2.4": "partial", "2.5": "fails",
    "3.2": "agree", "3.3": "fails", "3.4": "agree", "3.5": "fails", "3.6": "fails", "3.7": "disagree",
    "5.10": "partial", "5.11": "fails", "5.12": "fails", "5.14": "partial",
    "7.1": "agree", "7.3": "disagree", "7.6": "disagree", "7.7": "disagree",
    "8.3": "agree", "8.5": "agree",
}
_remarked = {k for k, v in SHEET_EN.items() if v.get("volley_remark")}
assert _remarked == set(VERDICT), f"remarks without a verdict / verdicts without a remark: {_remarked ^ set(VERDICT)}"


def volley_remark(rid):
    return SHEET_EN[rid].get("volley_remark")


# ---- which requirements each figure illustrates (drives the status panel beside each figure)
FIG_COVERS = {
    "1_1_single_node_rotation": ["1.1"],
    "1_2_final_node_theta": ["1.2"],
    "1_3_driving_flag": ["1.3", "1.4"],
    "2_1_mqtt_session": ["2.1", "2.2", "2.3", "2.4"],
    "2_5_instant_actions": ["2.5", "2.6"],
    "2_7_change_control": ["2.7", "2.8", "2.9", "5.6", "5.7", "6.1.1"],
    "3_1_cancel_stop": ["3.1", "3.2"],
    "3_3_release_horizon": ["3.3", "3.4"],
    "3_5_off_tape": ["3.5"],
    "3_6_precision": ["3.6", "3.7"],
    "4_publish_rates": ["4.1", "4.2"],
    "5_1_common_message": ["5.1", "5.3", "5.13", "5.15"],
    "5_4_errors": ["5.4", "5.5", "5.6", "5.7", "5.8", "5.9"],
    "5_10_pose": ["5.10", "5.11", "5.12", "5.14"],
    "6_rotation_direction": ["6.1", "6.1.1"],
    "7_1_tracking_direction": ["7.1", "7.3"],
    "7_4_gain_scheduling": ["7.4", "7.5"],
    "7_6_lateral_error": ["7.6"],
    "7_7_deceleration": ["7.7", "7.8", "7.9"],
    "8_1_lidar_fields": ["8.1", "8.2", "8.4"],
    "8_3_pallet_payload": ["8.3", "8.5"],
    "8_6_joystick": ["8.6"],
}
# message-structure figures list every requirement of their groups (uml_5 also carries group 4)
UML_GROUPS = {"uml_1": ["1"], "uml_2": ["2"], "uml_3": ["3"], "uml_5": ["4", "5"], "uml_6": ["6"], "uml_8": ["8"]}
for _name, _groups in UML_GROUPS.items():
    FIG_COVERS[_name] = [r[0] for r in R if r[0].split(".")[0] in _groups]
assert all(rid in BY_ID for ids_ in FIG_COVERS.values() for rid in ids_)
assert {rid for k, v in FIG_COVERS.items() if not k.startswith("uml_") for rid in v} == set(BY_ID), \
    "every requirement should appear in at least one drawing"

# ---- history
# Volley's list was finalised after bench testing on 5 Oct 2026 and reached HITO before 13 Oct;
# the exact send date isn't in Jon's mail or Slack.
PROPOSED = "Oct 2026, before 13 Oct"
# Dan's input for the 13 Oct HITO meeting: items to resolve before HITO's on-site visit.
PRIORITY = {"1.1", "1.2", "1.3", "1.4", "2.5", "2.6", "3.1", "3.2", "3.3", "3.4", "3.5", "3.6", "3.7",
            "5.4", "5.5", "5.6", "5.7", "5.8", "5.9"}
PRIORITY_SOURCE = ("12 Oct 2026", "https://volleyautomation.slack.com/archives/C0C60EUR3T4/p1791853166606129")
# HITO's v1.0.1 answer where it differs from V1.1: status, dev days, test days
V1_0_1 = {"3.1": ("conditional", 10, 10), "5.8": ("implement", None, None), "5.9": ("blocked", None, None),
          "6.1": ("implement", None, None), "7.7": ("conditional", 30, 30)}
V1_1_NOTE = {
    "3.1": "Estimate doubled; HITO needs a Volley test vehicle.",
    "3.7": "Adds a hardware upgrade or gyroscope as future paid work.",
    "5.8": "Moved to the joint working mechanism.",
    "5.9": "Estimate added; meaning still unclear to HITO.",
    "6.1": "Estimate added; HITO wants a detailed spec first.",
    "6.1.1": "Renumbered from 6.2.",
    "7.7": "Tagged as needing hardware customization.",
}
HITO_REPLY_PENDING = True  # set False once HITO answers the 9 Nov remarks, and add the reply below
CONTESTED = {"fails", "partial", "disagree"}


def effort(d, t):
    if d is None:
        return "no estimate"
    return f"{d} + {t if t is not None else '/'} days"


def history(rid):
    """Dated events for one requirement, oldest first: (date, who, text, link or None, kind)."""
    from svgkit import STATUS
    _, st, _, _, d, t = BY_ID[rid]
    ev = []
    if rid in PRIORITY:
        ev.append((PRIORITY_SOURCE[0], "Volley", "On Dan's list to resolve before HITO's on-site visit",
                   PRIORITY_SOURCE[1], "volley"))
    st0, d0, t0 = V1_0_1.get(rid, (st, d, t))
    ev.append(("13 Oct 2026", "HITO v1.0.1", f"{STATUS[st0][0]} · {effort(d0, t0)}", SOURCE["pdf_mail"], "hito"))
    if (st0, d0, t0) != (st, d, t):
        text = f"Changed to {STATUS[st][0]} · {effort(d, t)}. " + V1_1_NOTE.get(rid, "")
    else:
        text = V1_1_NOTE.get(rid, "No change.")
    ev.append(("9 Nov 2026", "HITO V1.1", text.strip(), source_url(rid), "hito"))
    if rid in VERDICT:
        ev.append(("9 Nov 2026", "Volley", VERDICTS[VERDICT[rid]][0], f"#volley-{rid.replace('.', '-')}", "volley"))
        if HITO_REPLY_PENDING and VERDICT[rid] in CONTESTED:
            ev.append(("", "HITO", "No reply to Volley's remark yet", None, "pending"))
    return ev
