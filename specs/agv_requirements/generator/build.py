"""Regenerate every SVG figure and the illustrated Markdown document.

    python build.py

Styling tokens: design-system/agv-spec/MASTER.md (UI UX Pro Max).
"""
import os
import figures2 as figures
from data import R, GROUPS, BY_ID
from svgkit import STATUS
from captions import CAPTIONS

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DOCS = os.path.join(ROOT, "docs")
IMG = os.path.join(DOCS, "images")
os.makedirs(IMG, exist_ok=True)

for name, fn in figures.ALL:
    fn().save(os.path.join(IMG, f"{name}.svg"))

FIGS = {  # group -> list of (image, caption)
    "1": [("1_1_single_node_rotation", "1.1 rotate in place when the order holds only the current node."),
          ("1_2_final_node_theta", "1.2 turn to the final node's theta on arrival."),
          ("1_3_driving_flag", "1.3 / 1.4 the driving flag mirrors commanded wheel speed, rotations included.")],
    "2": [("2_1_mqtt_session", "2.1–2.4 retained factsheet, Last Will registration, and who publishes CONNECTIONBROKEN."),
          ("2_5_instant_actions", "2.5 / 2.6 when FINISHED may be reported."),
          ("2_7_change_control", "2.7–2.9 documentation and joint change control (also covers 5.6, 5.7, 6.2).")],
    "3": [("3_1_cancel_stop", "3.1 / 3.2 where the AGV stops after a cancel."),
          ("3_3_release_horizon", "3.3 / 3.4 behaviour at the edge of the released path."),
          ("3_5_off_tape", "3.5 off-tape detection is armed only while moving."),
          ("3_6_precision", "3.6 / 3.7 stopping and rotation tolerances.")],
    "4": [("4_publish_rates", "4.1 / 4.2 configurable publishing rates.")],
    "5": [("5_1_common_message", "5.1, 5.3, 5.13, 5.15 new commonMessage fields."),
          ("5_4_errors", "5.4–5.9 error reporting rules."),
          ("5_10_pose", "5.10–5.12, 5.14 pose and velocity from the state estimate.")],
    "6": [("6_rotation_direction", "6.1 / 6.2 rotation direction set by a node action.")],
    "7": [("7_1_tracking_direction", "7.1 / 7.3 longitudinal vs lateral tape tracking."),
          ("7_4_gain_scheduling", "7.4 / 7.5 controller parameters: speed axis vs payload axis."),
          ("7_6_lateral_error", "7.6 lateral error band."),
          ("7_7_deceleration", "7.7–7.9 braking for a short final edge.")],
    "8": [("8_1_lidar_fields", "8.1, 8.2, 8.4 lidar field use, selection and override."),
          ("8_3_pallet_payload", "8.3 / 8.5 coupling check and payload weight."),
          ("8_6_joystick", "8.6 remote joystick recovery.")],
}


def est(d, t):
    if d is None:
        return "/"
    return f"{d} + {t if t is not None else '/'}"


FIG_NO = [0]
FIG_MAP = {}  # figure name -> number


def figure(name):
    """Image followed by a numbered, explanatory caption."""
    FIG_NO[0] += 1
    FIG_MAP[name] = FIG_NO[0]
    title, body = CAPTIONS[name]
    A(f"![Figure {FIG_NO[0]}. {title}](images/{name}.svg)")
    A("")
    A(f"**Figure {FIG_NO[0]}. {title}.** {body}")
    A("")


def esc(t):
    return t.replace("|", "\\|")


md = []
A = md.append
A("# AGV parking-lot functional requirements, illustrated")
A("")
A("Companion to *Functional_requirements-停车场功能需求20261013_V1_0_1.pdf* (13 Oct 2026, v1.0.1). "
  "That document lists 52 requirements from **Volley** (the customer) for a magnetic-tape-guided AGV "
  "that talks to the fleet manager over **VDA5050 / MQTT**, with **HITO**'s response and effort "
  "estimate for each. This document restates every requirement with a diagram, HITO's answer and the quoted effort.")
A("")
A("Estimates are business days, written *development + testing*. A `/` means the source gave no number. "
  "Field names inside diagrams are illustrative unless the source names them.")
A("")
A("## Reading the diagrams")
A("")
figure("robot_key")
A("Every requirement carries a status taken from HITO's reply. The letter repeats the colour so the meaning survives greyscale printing:")
A("")
A("| Letter | Status | Meaning |")
A("|---|---|---|")
meaning = {
    "works": "HITO says the AGV already behaves this way.",
    "implement": "HITO agrees to build it.",
    "conditional": "Agreed only after testing, discussion, or a counter-proposal.",
    "duplicate": "HITO closed it as a repeat of another item.",
    "process": "Joint approval rule, or behaviour HITO places outside the AGV (MQTT broker).",
    "blocked": "Needs new hardware, or HITO didn't understand it.",
    "rejected": "HITO says the current vehicle can't achieve it.",
}
for k in ["works", "implement", "conditional", "duplicate", "process", "blocked", "rejected"]:
    A(f"| **{STATUS[k][2]}** | {STATUS[k][0]} | {meaning[k]} |")
A("")
A("## Scale and data structure conventions")
A("")
A("All plan views share one scale, 1 m = 40 px, and carry a scale bar. Where a requirement is in millimetres or "
  "fractions of a degree, an orange magnifier marks the spot and a zoomed inset shows it at its own stated scale. "
  "Numbers labelled *example values* (speeds, braking rate, field sizes, AGV size) are assumptions for "
  "illustration; the source document doesn't specify them.")
A("")
A("Each section that involves VDA5050 messages ends with a structure figure in UML composition style, showing "
  "where each relevant field sits inside its message. The field set follows VDA 5050 version 2.0, abbreviated; "
  "check it against the version the two companies agree on.")
A("")
figure("vda_topics")
A("## Overview")
A("")
figure("overview")
figure("estimates")

for g, gname in GROUPS.items():
    A(f"## {g}. {gname}")
    A("")
    for img, _ in FIGS[g]:
        figure(img)
    uml_name = {"1": "uml_1", "2": "uml_2", "3": "uml_3", "5": "uml_5", "6": "uml_6", "8": "uml_8"}.get(g)
    if uml_name:
        figure(uml_name)
    if g == "4":
        A("*The message structure for group 4 is shown with group 5, which uses the same messages.*")
        A("")
    if g == "7":
        A("*Group 7 is internal control behaviour and adds no VDA5050 fields, so it has no structure figure.*")
        A("")
    A("| ID | Requirement | HITO response | Status | Effort |")
    A("|---|---|---|---|---|")
    for r in R:
        if r[0].split(".")[0] != g:
            continue
        rid, st, req, resp, d, t = r
        A(f"| **{rid}** | {esc(req)} | {esc(resp)} | {STATUS[st][2]} · {STATUS[st][0]} | {est(d, t)} |")
    A("")

A("## Points to raise with HITO")
A("")
A("**7.5 is not a duplicate of 7.4.** 7.4 asks for parameters that vary with commanded speed; 7.5 asks for one "
  "parameter set that holds across every payload. A speed-scheduled table kept separately per payload would meet "
  "7.4 and fail 7.5. Because the AGV can't measure payload weight (8.5), a single robust set is the only workable "
  "design anyway. Ask HITO to confirm that the 7.4 work uses one set for all loads and that its 30 + 30 days "
  "include tests at unloaded, empty-pallet and max-payload conditions.")
A("")
A("**7.8 and 7.9 are not covered by 7.7 as written.** HITO's own note says deceleration is planned along one edge "
  "only, which is the exact gap 7.9 describes. Get it in writing that the 7.7 estimate includes multi-edge planning.")
A("")
A("**5.3 counter-proposal changes the contract.** \"0 for one second\" is ambiguous because 0 can be a real reading. "
  "Decide between an empty / omitted value and HITO's rule.")
A("")
A("**Rejections need numbers.** For 3.7, 7.3 and 7.6, ask what HITO *can* guarantee: rotation tolerance, "
  "lateral tracking error, and the top speed for stable strafing.")
A("")
A("**2.3 / 2.4 depend on 2.2.** The broker publishes CONNECTIONBROKEN only if the Will is registered; test the three together.")
A("")
A("**Open items without owner or date:** reporting frequency in 5.10 (TBD Hz), retained-topic list for 2.1, "
  "lidar schema for 8.2, hardware options for 8.3 and 8.5, the meaning of errorHint in 5.9 (check which VDA5050 "
  "version is the baseline), and estimates for 5.8 and 6.1. 2.7's \"future maintenance out of scope\" should be "
  "settled contractually.")
A("")
A("**Source housekeeping:** IDs 5.2 and 7.2 are missing; 3.2's Chinese text has a typo (先在 → 现在).")
A("")
from glossary import TERMS

A("## Glossary")
A("")
for slug, term, _, definition in TERMS:
    A(term)
    A(": " + definition.format(**{k: FIG_MAP[k] for k in FIG_MAP}))
    A("")

A("---")
A("")
A("Diagrams are generated by `generator/build.py` (pure Python) from `generator/data.py`. "
  "Visual tokens follow the design system produced by "
  "[UI UX Pro Max](https://github.com/nextlevelbuilder/ui-ux-pro-max-skill) "
  "(Minimalism & Swiss Style, tracking blue + delivery orange, IBM Plex Sans / JetBrains Mono), "
  "saved in `design-system/agv-spec/MASTER.md`.")

with open(os.path.join(DOCS, "AGV_requirements_illustrated.md"), "w", encoding="utf-8") as fh:
    fh.write("\n".join(md) + "\n")
with open(os.path.join(DOCS, "figures.json"), "w", encoding="utf-8") as fh:
    import json
    json.dump(FIG_MAP, fh, indent=1, sort_keys=True)
print("built", len(figures.ALL), "figures")
