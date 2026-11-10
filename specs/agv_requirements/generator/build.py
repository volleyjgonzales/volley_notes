"""Regenerate every SVG figure and the illustrated Markdown document.

    python build.py

Styling tokens: design-system/agv-spec/MASTER.md (UI UX Pro Max).
"""
import os
import re
import figures2 as figures
from data import R, GROUPS, BY_ID, SOURCE, SHEET_URL, SHEET_EN, VERDICT, VERDICTS, source_url, volley_remark
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
          ("2_7_change_control", "2.7–2.9 documentation and joint change control (also covers 5.6, 5.7, 6.1.1).")],
    "3": [("3_1_cancel_stop", "3.1 / 3.2 where the AGV stops after a cancel."),
          ("3_3_release_horizon", "3.3 / 3.4 behaviour at the edge of the released path."),
          ("3_5_off_tape", "3.5 off-tape detection is armed only while moving."),
          ("3_6_precision", "3.6 / 3.7 stopping and rotation tolerances.")],
    "4": [("4_publish_rates", "4.1 / 4.2 configurable publishing rates.")],
    "5": [("5_1_common_message", "5.1, 5.3, 5.13, 5.15 new commonMessage fields."),
          ("5_4_errors", "5.4–5.9 error reporting rules."),
          ("5_10_pose", "5.10–5.12, 5.14 pose and velocity from the state estimate.")],
    "6": [("6_rotation_direction", "6.1 / 6.1.1 rotation direction set by a node action.")],
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


FRONT_NO = [0]
FIG_MAP = {}  # figure name -> label


def fig_label(name):
    """Figure labels follow requirement ids so a figure maps straight to its requirement:
    '5_10_pose' -> 5.10 (the first requirement it shows), 'uml_5' -> 5.S (message structure
    for group 5), and figures before the groups -> 0.1, 0.2, ... in order of appearance."""
    m = re.match(r"(\d+)_(\d+)_", name)
    if m:
        label = f"{m.group(1)}.{m.group(2)}"
        assert label in BY_ID, f"{name}: no requirement {label}"
        return label
    m = re.fullmatch(r"uml_(\d+)", name)
    if m:
        return f"{m.group(1)}.S"
    m = re.match(r"(\d+)_[a-z]", name)  # group-wide figure, e.g. 4_publish_rates: first requirement of the group
    if m:
        return next(r[0] for r in R if r[0].split(".")[0] == m.group(1))
    FRONT_NO[0] += 1
    return f"0.{FRONT_NO[0]}"


def figure(name):
    """Image followed by a labelled, explanatory caption."""
    label = fig_label(name)
    assert label not in FIG_MAP.values(), f"duplicate figure label {label}"
    FIG_MAP[name] = label
    title, body = CAPTIONS[name]
    A(f"![Figure {label}. {title}](images/{name}.svg)")
    A("")
    A(f"**Figure {label}. {title}.** {body}")
    A("")


def esc(t):
    return t.replace("|", "\\|")


def id_cell(rid):
    row = SHEET_EN[rid]["row"]
    return f'**{rid}** [↗]({source_url(rid)} "Row {row} of the {SOURCE["version"]} sheet")'


def ids(keys):
    return ", ".join(keys) if keys else "none"


def remark_md(rid):
    """Volley's remark as a definition-list entry. Text is verbatim from the sheet; each line becomes a
    paragraph, and runs of '- ' lines become a list (indented 4 spaces to stay inside the definition)."""
    blocks, items = [], []
    for line in volley_remark(rid).splitlines():
        line = line.strip()
        if line.startswith("- "):
            items.append(line)
            continue
        if items:
            blocks.append("\n".join("    " + i for i in items))
            items = []
        if line:
            blocks.append("    " + line)
    if items:
        blocks.append("\n".join("    " + i for i in items))
    first = blocks[0].strip()
    rest = "\n\n".join(blocks[1:])
    out = [f"{rid} — {VERDICTS[VERDICT[rid]][0]}", f":   {first}"]
    if rest:
        out += ["", rest]
    return "\n".join(out)


md = []
A = md.append
A("# AGV parking-lot functional requirements, illustrated")
A("")
A(f"Companion to HITO's workbook [{SOURCE['title']}]({SHEET_URL}) ({SOURCE['version']}, {SOURCE['date']}), "
  "which lists 52 requirements from **Volley** (the customer) for a magnetic-tape-guided AGV "
  "that talks to the fleet manager over **VDA5050 / MQTT**, with **HITO** ([苏州海通机器人系统有限公司](http://www.hitorobotic.com/), 海通 in Volley's Chinese text)'s response and effort "
  "estimate for each, plus Volley's remarks of 9 Nov from testing the current firmware. "
  "This document restates every requirement with a diagram, HITO's answer, the quoted effort and Volley's view.")
A("")
A("Every requirement id in the tables has a ↗ link that opens that row in the sheet, which holds the verbatim "
  "English text on the EN tab and the Chinese original on the CN tab (客户需求 / hito建议及措施 / 备注; the links open "
  "the EN tab, so switch tabs for Chinese). Each figure panel also shows the Chinese text under 中文原文. The requirement and HITO-response columns here are paraphrases; "
  f"Volley's remarks are quoted verbatim. The earlier version is [{SOURCE['pdf_title']}]({SOURCE['pdf_mail']}) "
  "(v1.0.1, 13 Oct 2026, email attachment).")
A("")
A("Estimates are business days, written *development + testing*. A `/` means the source gave no number. "
  "Field names inside diagrams are illustrative unless the source names them.")
A("")

# ---------------------------------------------------------------- where things stand
by_verdict = {k: [rid for rid, _ in sorted(VERDICT.items(), key=lambda kv: [int(p) for p in kv[0].split(".")]) if VERDICT[rid] == k]
              for k in VERDICTS}
red = [r["id"] for r in SHEET_EN.values() if r["category"] == "red"]
blue = [r["id"] for r in SHEET_EN.values() if r["category"] == "blue"]
yellow = [r["id"] for r in SHEET_EN.values() if r["category"] == "yellow"]
from contract import PROPOSAL, CRITERIA_HEADING, GROUP_HEADING, PAYMENTS, TIMELINE  # noqa: E402

A("## HITO contract")
A("")
A("**There is no signed agreement with HITO yet.** The live document is Volley's "
  f"[{PROPOSAL['title']}]({PROPOSAL['url']}) ({PROPOSAL['date']}; Chinese first, where HITO is 海通, "
  "then English). Its [acceptance criteria]"
  f"({PROPOSAL['url']}{CRITERIA_HEADING}) (验收标准) are the 52 requirements on this page, group for group and in "
  "the same order, so HITO's answers in the sheet decide whether the $50,000 QA payment can be released. "
  "Each figure panel links its requirement to the matching clause.")
A("")
A("Volley's proposed payments, out of HITO's $100,000 price (which must include the spare-parts package "
  "agreed with Sylvia):")
A("")
for amount, when in PAYMENTS:
    A(f"- **{amount}** {when}.")
A("")
A("| Date | Who | What | Source |")
A("|---|---|---|---|")
for date, who, what, link in TIMELINE:
    kind = "Slack" if "slack.com" in link else "Email" if "mail.google" in link else "Doc"
    A(f"| {date} | {who} | {esc(what)} | [{kind}]({link}) |")
A("")
A("Not found on Drive, Slack or email: HITO's \"version 3.0\" agreement draft, or any signed version. "
  "Clause links: " + "; ".join(f"[{g} {GROUPS[g]} · {GROUP_HEADING[g][0]}]({PROPOSAL['url']}#heading={GROUP_HEADING[g][1]})"
                                for g in GROUP_HEADING) + ".")
A("")
A("## Where things stand")
A("")
A("**As of 10 Nov 2026, HITO has not answered Volley's 9 Nov remarks.** No email from HITO since the "
  "3 Nov firmware V2.2.3 thread, and nothing in Slack. Update this section when they reply.")
A("")
A(f"- **13 Oct 2026**: HITO sends its first response, the v1.0.1 PDF.")
A(f"- **9 Nov 2026**: HITO's [{SOURCE['version']} workbook]({SHEET_URL}): EN and CN tabs, rows colour-coded "
  "by category, a remarks column and revised estimates.")
A(f"- **9 Nov 2026**: Volley adds remarks to {len(VERDICT)} rows (column G), mostly results of testing "
  "the v2.x firmware against HITO's \"already implemented\" answers.")
A("")
A("**What changed from v1.0.1 to V1.1 (HITO's side)**")
A("")
A("- 3.1 estimate doubled to 20 + 20 days, and HITO needs a Volley test vehicle to test it.")
A("- 5.9 and 6.1 now have estimates (10 + 5 each). 5.9 is still marked \"meaning unclear\"; 6.1 needs a "
  "detailed spec from Volley first.")
A("- 7.7 now carries HITO's \"hardware customization required\" tag (red), but keeps its 30 + 30 estimate.")
A("- 5.8 moved to the joint working mechanism (blue), still without an estimate.")
A("- 3.7's answer now offers a hardware upgrade or gyroscope as future paid development.")
A("- 6.2 is renumbered 6.1.1.")
A(f"- HITO's colour legend: red = needs hardware ({ids(red)}); green = done or existing behaviour; "
  f"blue = joint working mechanism ({ids(blue)}); white = software work for Volley. Yellow, not in the "
  f"legend, marks {ids(yellow)} as \"not related to HITO\".")
A("")
A("**Volley's position (9 Nov remarks)**")
A("")
A(f"- **Fails Volley test** (HITO says it's done; testing says not): {ids(by_verdict['fails'])}.")
A(f"- **Partly works**: {ids(by_verdict['partial'])}.")
A(f"- **Volley disagrees** with HITO's \"needs hardware\" or \"too demanding\" answer: {ids(by_verdict['disagree'])}.")
A(f"- **Accepted as is**: {ids(by_verdict['accepted'])}. **Volley agrees**: {ids(by_verdict['agree'])}.")
A("")
A("The \"fails\" and \"partly works\" items carry no estimate in V1.1, because HITO counts them as done.")
A("")
A("## Reading the diagrams")
A("")
A("Figures are labelled after the first requirement they illustrate, so Figure 5.10 shows requirement 5.10 "
  "(its caption lists any others it also covers, here 5.11, 5.12 and 5.14). Figure *n*.S is the message "
  "structure for group *n*, and Figures 0.1–0.4 are the general figures before the groups.")
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
A("The status is HITO's position. The **Volley 9 Nov** column gives Volley's view where the remarks "
  "column has one, and links to the full remark under each table:")
A("")
A("| Volley 9 Nov | Meaning |")
A("|---|---|")
for k, (label, mean) in VERDICTS.items():
    A(f"| {label} | {mean} |")
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
    A("| ID | Requirement | HITO response | Status | Effort | Volley 9 Nov |")
    A("|---|---|---|---|---|---|")
    rows = [r for r in R if r[0].split(".")[0] == g]
    for rid, st, req, resp, d, t in rows:
        v = VERDICTS[VERDICT[rid]][0] if rid in VERDICT else "—"
        A(f"| {id_cell(rid)} | {esc(req)} | {esc(resp)} | {STATUS[st][2]} · {STATUS[st][0]} | {est(d, t)} | {v} |")
    A("")
    remarked = [r[0] for r in rows if r[0] in VERDICT]
    if remarked:
        A("**Volley remarks, 9 Nov 2026** (verbatim from column G of the sheet)")
        A("")
        for rid in remarked:
            A(remark_md(rid))
            A("")

A("## Points to raise with HITO")
A("")
A("**\"Already implemented\" answers that fail testing.** HITO marks " + ids(by_verdict["fails"] + by_verdict["partial"])
  + " as done, so they have no estimate in V1.1. Volley's 9 Nov remarks describe tests that show otherwise. "
  "Ask HITO to reproduce each test and give an estimate, starting with 1.2 (is nodePosition.theta read at "
  "all?) and 2.5 (FINISHED reported on receipt; RUNNING never reported).")
A("")
A("**7.7 is a software change.** V1.1 tags 7.7 as needing hardware, while keeping its 30 + 30 estimate. The "
  "AGV already brakes at its configured rate; the problem is that braking is planned one edge at a time, "
  "which is exactly the gap 7.8 and 7.9 describe, and HITO closed those as duplicates of 7.7. Get it in "
  "writing that 7.7 includes planning across several edges, and that it also fixes the short-final-edge "
  "overshoot reported under 3.6.")
A("")
A("**7.5 is not a duplicate of 7.4.** 7.4 asks for parameters that vary with commanded speed; 7.5 asks for one "
  "parameter set that holds across every payload. A speed-scheduled table kept separately per payload would meet "
  "7.4 and fail 7.5. Because the AGV can't measure payload weight (8.5), a single robust set is the only workable "
  "design anyway. Ask HITO to confirm that the 7.4 work uses one set for all loads and that its 30 + 30 days "
  "include tests at unloaded, empty-pallet and max-payload conditions.")
A("")
A("**Hardware answers need numbers.** For 3.7, 7.3 and 7.6, Volley's remarks argue the limits are in the "
  "control software (stop logic, PID tuning), not the vehicle. Either way, ask what HITO *can* guarantee "
  "today: rotation tolerance, lateral tracking error, and the top speed for stable strafing.")
A("")
A("**5.3 counter-proposal changes the contract.** \"0 for one second\" is ambiguous because 0 can be a real reading. "
  "Decide between an empty / omitted value and HITO's rule.")
A("")
A("**5.8 is firmware work, not a process item.** V1.1 moves it to the joint working mechanism (blue), but "
  "filling errorDescription on every error is a firmware change and needs an estimate.")
A("")
A("**2.3 / 2.4 depend on 2.2.** The broker publishes CONNECTIONBROKEN only if the Will is registered. "
  "Volley's test found it arrives about 45 s after a power-off and isn't retained; ask for a retained Will "
  "and a keepalive short enough to detect the loss in 5–10 s. Test the three together.")
A("")
A("**Open items without owner or date:** reporting frequency in 5.10 (TBD Hz; Volley proposes at least 5 Hz "
  "for visualization), retained-topic list for 2.1, lidar schema for 8.2, rotation-direction spec for 6.1, "
  "hardware options for 8.3 and 8.5, the meaning of errorHint in 5.9 (check which VDA5050 version is the "
  "baseline), and an estimate for 5.8. 2.7's \"future maintenance out of scope\" should be settled contractually.")
A("")
A("**Source housekeeping:** IDs 5.2 and 7.2 are missing; V1.1 renumbered 6.2 as 6.1.1; 3.2's Chinese text "
  "still has a typo (先在 → 现在); the test-days cell is blank instead of `/` for 5.7 and 7.9.")
A("")
# ---------------------------------------------------------------- hardware and grid reference
from references import REFS, FACTS, GAPS, refs_for  # noqa: E402

A("## Hardware and grid reference")
A("")
A("Several requirements depend on the vehicle's sensors and on how the floor grid is laid out (RFID tags, "
  "magnetic tape). HITO has sent no grid installation spec for the V2, so the numbers below come from "
  "Volley's own testing, vendor documents and Slack. Each links to its source; check the date before relying on one.")
A("")


def ref_link(key):
    r = REFS[key]
    return f"[{r['title']}]({r['url']})"


def cite(src):
    """A FACTS source: a REFS key, or (key, locator label, URL fragment or full URL) to jump to the spot."""
    if isinstance(src, str):
        return f"{ref_link(src)} ({REFS[src]['date']})"
    key, label, where = src
    r = REFS[key]
    url = where if where.startswith("http") else r["url"].split("#")[0] + where
    return f"[{r['title']}, {label}]({url}) ({r['date']})"


for topic, heading in (("hardware", "HITO AGV hardware"), ("grid", "Grid deployment")):
    A(f"### {heading}")
    A("")
    hw = topic == "hardware"
    A("| Topic | What the sources say | Source | " + ("Hardware | " if hw else "") + "Related |")
    A("|---|---|---|" + ("---|" if hw else "") + "---|")
    for f in FACTS:
        if f["topic"] != topic:
            continue
        src = "<br>".join(cite(s) for s in f["sources"])
        parts = "<br>".join(f"[{lab}]({url})" for lab, url in f.get("parts", [])) or "—"
        A(f"| {f['subject']} | {esc(f['text'])} | {src} | " + (f"{parts} | " if hw else "")
          + f"{', '.join(f['reqs']) or '—'} |")
    A("")
    A(f"**Documents: {heading.lower()}**")
    A("")
    for key, r in REFS.items():
        if r["topic"] != topic or not r.get("list", True):
            continue
        rel = f" Related: {', '.join(r['reqs'])}." if r["reqs"] else ""
        A(f"- {ref_link(key)}, {r['who']}, {r['date']}. {r['about']}{rel}")
    A("")

A("### Not documented")
A("")
for g in GAPS:
    A(f"- {g}")
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
