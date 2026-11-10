"""Hardware and grid-deployment reference material (RFID, magnetic tape, node spacing).

Collected 10 Nov 2026 from Google Drive and Slack. HITO has sent no grid installation spec for
the V2, so most numbers come from Volley's own testing; several of them conflict, and the
FACTS rows say so. build.py renders the "Hardware and grid reference" section from this file,
and the site adds a "Docs" row to each figure panel from refs_for().

REFS:  key -> title, url, date, who, topic ("hardware" | "grid"), about, reqs, short
       (panel link text). list=False keeps a source (Slack messages) out of the document
       lists and the panel; it is still cited in FACTS.
FACTS: dicts of topic, subject, text, sources, reqs and (hardware only) parts.
       A source is a REFS key, or (key, locator label, URL fragment or full URL) that jumps to
       the spot: "#page=N" for PDFs, "#heading=h.…" for Google Docs, "#gid=…&range=…" for
       Sheets; "" when the viewer has no anchor (Drive .docx / .xlsx), so only the label helps.
       parts: (label, url) product pages or datasheets for the hardware the row is about.
"""
from data import BY_ID

SLACK = "https://volleyautomation.slack.com/archives/"
DRIVE = "https://drive.google.com/file/d/{}/view"
GDOC = "https://docs.google.com/document/d/{}/edit"
GSHEET = "https://docs.google.com/spreadsheets/d/{}/edit"
CONF = "https://volleyautomation.atlassian.net/wiki/"


def doc(title, url, date, who, topic, about, reqs=(), short=None, list=True):
    return {"title": title, "url": url, "date": date, "who": who, "topic": topic, "about": about,
            "reqs": [*reqs], "short": short or title, "list": list}


def slack(who, date, path, topic):
    return doc(f"Slack, {who}", SLACK + path, date, who, topic, "", list=False)


REFS = {
    # ---- HITO hardware
    "manual": doc("AGV Manual and Maintenance Guide V3.4", DRIVE.format("1CNMOWxIpAE6TKLzAlh1p2PLdbp1Zib1y"),
                  "29 Oct 2026", "HITO", "hardware",
                  "Specs (model MDL-70), initial positioning, navigation screen, alarm list. §6.2.2 and §6.4 cover "
                  "the card-read indicator and the four magnetic sensors.",
                  ["3.6", "3.7", "5.1", "5.4", "5.12", "5.13"], "Manual V3.4"),
    "mag_sensor": doc("CNS-MGS-160N magnetic sensor manual (Google-translated)",
                      DRIVE.format("1cIlDd0ZhLgWJJZ3BQiLSRmMQ_vprqn3o"), "10 Feb 2026", "CNS (sensor vendor)",
                      "hardware", "Sensing points, range, accuracy and mounting height of the tape sensors.",
                      ["3.5", "5.3", "7.4", "7.6"], "Mag sensor"),
    "quote": doc("HITO quotation: tape and RFID tags (导航辅料)", DRIVE.format("1b_hzDnk_DcTUAfTXxPf3yPheSEBDHIXn"),
                 "12 Feb 2026", "HITO to Mike Beebe", "hardware",
                 "Part specs and prices for the RFID tags, magnetic tape and protective strip HITO supplies; "
                 "bilingual (Quotation-Consumables-导航辅料). The PDF is a scanned image.", ["5.1", "5.13"], "Tag quote"),
    "hinson_rfid": doc("Hinson CNS-RFID sensor manual", "https://a.storyblok.com/f/298593/x/9486728474/cns-rfid-sensor-manual-0922.pdf",
                       "Sep 2022", "Foshan Hinson Robot Technology (maker)", "hardware",
                       "Maker's manual for the reader HITO fits (CNS RFID 1S): read range, mounting height, tag "
                       "spacing, signal-strength LED. Generic guidance, not HITO's grid spec; its diagram keeps the "
                       "Chinese labels RFID传感器 / RFID标签.", ["5.1", "5.13"], "Reader manual"),
    "charger": doc("AGV Charger DC-WICS2000-4830Y V1.0", DRIVE.format("1g1vXk7S9dOfLzWRekYp3P0mtwgQ-BAJZ"), "undated",
                   "宁波道充科技有限公司 (Ningbo Douch Power Technology)", "hardware",
                   "Maker's manual for the wireless charger; Chinese company header on every page."),
    "hito_site": doc("HITO website (苏州海通机器人系统有限公司)", "http://www.hitorobotic.com/", "live site", "HITO",
                     "hardware", "HITO's own site; the header gives the Chinese company name."),
    "v2_issues": doc("Hito V2 AGV (16 & 17): Issues Summary and Lessons Learned",
                     GDOC.format("1hg3qedRF_EkAa1SaeswDQSghDDirhweNrIq9TtGN2pw"), "16 Oct 2026", "Brandon Peterson",
                     "hardware", "What arrived without documentation (tags, tape, tag format, API), speed cap, "
                     "lidar pattern limit.", ["5.12", "5.13", "7.7", "8.1", "8.2"], "V2 issues"),
    "node_acc": doc("Hito Dst Node Accuracy Investigation", GDOC.format("1AYT7-MjBx6Gnh8tBlbthG0vc3N93MiuDbKxVKfqYFs0"),
                    "Aug 2026", "Volley engineering", "hardware",
                    "How the AGV decides it is on a node; magnetic offset method and results; a TODO list that "
                    "includes describing how HITO uses RFID and tape to stop.", ["3.6", "5.1", "5.3", "5.12", "7.7"], "Node accuracy"),
    "perf_eval": doc("AGV performance evaluation (sheet)", GSHEET.format("12mzsrw7jmrrpu8DHFdZU1AIJoWyJlYvC8ZsA5Fu72UM"),
                     "31 Aug 2026", "Volley engineering", "hardware",
                     "Node-accuracy runs per AGV and parameter set, with the RFID S value per stop.",
                     ["3.6", "3.7", "5.1"], "Perf data"),
    "tracker": doc("HITO-Volley Action Tracker", GSHEET.format("1_RTpfjN_4MobrjKxKEjdYx8WTaqPK-7x7mJ_CR6YBoc"),
                   "30 Sep 2026", "Karen Ahle", "hardware",
                   "Running list of open issues with HITO, including RFID early-read undershoot and rotation "
                   "steering (HW006).", ["3.6", "3.7", "6.1"], "Action tracker"),
    "components": doc("Volley component list-20250506.xlsx", DRIVE.format("17tWNeVoV8WKC5vVFpZUuN-Gaz-BkrIDv"),
                      "May 2026", "HITO", "hardware",
                      "HITO's list of key components with model and brand (RFID reader, magnetic sensors, lidar, "
                      "drive wheel, controller, battery, charger, touchscreen, lift). Logged as received on 13 May in "
                      "the Action Tracker; the later version with the wifi parts is not on Drive.",
                      ["5.1", "5.13", "8.1", "8.2"], "Component list"),
    "bringup": doc("HITO AGV Bringup Guide (Confluence)", CONF + "spaces/VG/pages/3094970369", "Aug 2026",
                   "Dan Ambrosio", "hardware", "Steps used to bring up AGVs 16 and 17 at Pecos."),
    # ---- grid deployment
    "strip_install": doc("Magnetic Strip Installation Requirements", DRIVE.format("1AiJ4MiWO5IlyyAbac6hc5ZedGK0GYvtG"),
                         "24 Jul 2023 (rev A/0)", "HITO", "grid",
                         "HITO's tape installation rules: strip size, floor prep, joints, protective cover. "
                         "The only grid document from HITO.", ["7.1", "7.6"], "Tape install (HITO)"),
    "tape_layout": doc("Grid Tape Layout '24", GDOC.format("1sW4LwkGhCzGyy3z-IjhpkehFwO-chK1KRxYLTGzAB3o"),
                       "3 Jul 2025", "Volley operations", "grid",
                       "Volley's taping and RFID-tag procedure: tools, floor prep, laser alignment, tag template. "
                       "Written for the homebrew AGV (2-inch tape).", ["5.12", "7.6"], "Tape layout"),
    "grid_layout": doc("Grid Layout (Confluence)", CONF + "spaces/~71202010b7d5fea11e4a499d23a3ffa76d6146/pages/3102474241/Grid+Layout",
                       "undated", "Brandon Peterson", "grid",
                       "Brandon's page, meant to become the authority on grid layout. Not readable from here; "
                       "check it before relying on the Slack numbers below.", ["3.6", "7.7"], "Grid Layout"),
    # ---- Slack sources (cited in FACTS only)
    "s_agvctl": slack("Brandon Peterson", "29 May 2026", "C0AJ0PBMNSJ/p1780090726961909", "hardware"),
    "s_multi_tag": slack("Paul Miller", "21 Sep 2025", "C02MB7YCPAL/p1758473555572589", "hardware"),
    "s_tape_25": slack("Karen Ahle", "13 Apr 2026", "C0AJ0PBMNSJ/p1776098465028989", "grid"),
    "s_tape_cost": slack("Karen Ahle", "13 Apr 2026",
                         "C0AJ0PBMNSJ/p1776099189513519?thread_ts=1776098465.028989&cid=C0AJ0PBMNSJ", "grid"),
    "s_tape_pt": slack("PT (HITO), relayed", "15 Apr 2026",
                       "C0AJ0PBMNSJ/p1776269662377909?thread_ts=1776269654.861309&cid=C0AJ0PBMNSJ", "grid"),
    "s_tape_30": slack("Brandon Peterson", "28 Jul 2026",
                       "C0AJ0PBMNSJ/p1785259484461059?thread_ts=1785258849.373909&cid=C0AJ0PBMNSJ", "grid"),
    "s_tape_50": slack("Matt Johannes", "15 Apr 2026", "C0AJ0PBMNSJ/p1776262140881589", "grid"),
    "s_tape_best": slack("Brandon Peterson", "28 Jul 2026", "C0AJ0PBMNSJ/p1785258849373909", "grid"),
    "s_tape_past": slack("Karen Ahle", "13 Apr 2026", "C0AJ0PBMNSJ/p1776132380499999", "grid"),
    "s_taping": slack("Brandon Peterson", "15 Jun 2026",
                      "C07K5F069U2/p1781545102203429?thread_ts=1781544484.104409&cid=C07K5F069U2", "grid"),
    "s_four_tags": slack("Brandon Peterson", "23 Jun 2026",
                         "CQM1MABHD/p1782255530318999?thread_ts=1782254928.415049&cid=CQM1MABHD", "grid"),
    "s_spacing_24": slack("Brandon Peterson", "13 May 2026",
                          "C09M2PGBE4Q/p1778695948466339?thread_ts=1778631575.528069&cid=C09M2PGBE4Q", "grid"),
    "s_spacing_8": slack("Brandon Peterson", "14 Sep 2026", "C0AJ0PBMNSJ/p1789423163809949", "grid"),
    "s_new_tags": slack("Brandon Peterson", "28 Sep 2026",
                        "C0AVCL4DRFZ/p1790622859129519?thread_ts=1790011121.875789&cid=C0AVCL4DRFZ", "grid"),
    "s_clearance": slack("Brandon Peterson", "10 Jun 2026", "C09U7EHABUL/p1781122284524789", "grid"),
}

AT_SW = "#gid=1599846865&range=A6:K6"       # Action Tracker, Software-Dan tab
AT_HW006 = "#gid=284631547&range=A7:H7"     # Action Tracker, Hardware-Brandon tab
AT_RFID_PARAMS = "#gid=243080004&range=A14:F14"  # Action Tracker, Closed Items tab
GTL_STEPS = "#heading=h.hnsy58gurdmq"       # Grid Tape Layout '24, Assembly Steps
NA_METHOD = "#heading=h.5k82eyhuoqny"       # Node Accuracy, Method
NA_RESULTS = "#heading=h.yfvq61dcqbil"      # Node Accuracy, Results

HINSON_RFID = [("Hinson CNS-RFID sensor manual (maker PDF)",
                "https://a.storyblok.com/f/298593/x/9486728474/cns-rfid-sensor-manual-0922.pdf"),
               ("Hinson CNS-RFID communication manual (maker PDF)",
                "https://a.storyblok.com/f/298593/x/ff2f0e6637/cns-rfid-sensor-communication-manual-0922.pdf")]


def fact(topic, subject, text, sources, reqs=(), parts=()):
    return {"topic": topic, "subject": subject, "text": text, "sources": [*sources], "reqs": [*reqs],
            "parts": [*parts]}


FACTS = [
    # ---- hardware
    fact("hardware", "RFID reader",
         "Hinson CNS RFID 1S, one unit, on the side of the AGV; it reads tags only in certain orientations. "
         "Maker's spec: 13.56 MHz, read range up to 140 mm (depends on the card), IP54, 12–36 VDC, reports signal "
         "strength (an Rssi LED), relative speed under 3.5 m/s.",
         [("components", "row RFID Reader", ""), ("tape_layout", "Assembly Steps, step 3", GTL_STEPS),
          ("hinson_rfid", "§2.3, p. 7", "#page=7"), ("hinson_rfid", "§3.3–3.4, p. 12", "#page=12")],
         ["5.1", "5.13"], HINSON_RFID),
    fact("hardware", "RFID tags",
         "HITO quotes WYN tags: HF 13.56 MHz, ISO 15693, Ø35 × 3.2 mm, IP67, $0.56 each "
         "(高频，工业载码体ISO15693，AGV站点定位地标卡13.56MHz).",
         [("quote", "p. 1, item 1.3", "#page=1")], ["5.13"]),
    fact("hardware", "Reader output",
         "Volley's agvctl view shows the reader on /dev/ttyS3 at about 50 reads/s with a signal value "
         "(\"Signal 7/7\"). The node-accuracy runs record S values of 1, 2 and 7; the scale's meaning is "
         "undocumented.",
         ["s_agvctl", ("perf_eval", "Node Accuracy tab, column L", "#gid=0&range=L2:L57")], ["5.1"], HINSON_RFID[1:]),
    fact("hardware", "Tag format",
         "The V2 tag format was undocumented; Volley decoded it. AGVs 16 and 17 arrived without tags or tape.",
         [("v2_issues", "Integration, 3rd bullet; Unboxing, 2nd bullet", "")], ["5.13"]),
    fact("hardware", "RFID stop tuning",
         "Stopping on a tag uses pre_stop_distance: 15 and tag_predetect_dis: 30 (closed item 26).",
         [("tracker", "Closed Items, row 14", AT_RFID_PARAMS)], ["3.6", "7.7"]),
    fact("hardware", "Early tag read",
         "Strafing with the reader leading, the AGV reads the tag early and stops about 100 mm after detection "
         "(open item).", [("tracker", "Software-Dan tab, row 6", AT_SW)], ["3.6"]),
    fact("hardware", "Heading at start-up",
         "The screen's card-read indicator turns green on a tag read (§6.2.2). Initial positioning takes a "
         "hand-entered \"Current Angle\" (§6.4.2). The manual calls the landmark both \"QR code\" and \"RFID card\".",
         [("manual", "§6.2.2, p. 30", ""), ("manual", "§6.4.2, p. 70", "")], ["5.12"]),
    fact("hardware", "Magnetic sensors",
         "Four Hinson CNS-MGS-160N sensors (front, back, left, right): 16 points at 10 mm pitch, 150 mm range, "
         "1 mm accuracy, 5 ms response, mounted 20–40 mm above a 30 mm strip. HITO's component list spells it "
         "CNS-MSG-160N.",
         [("components", "row Magnetic Navigation Sensor", ""), ("manual", "§6.4.1, p. 66", ""),
          ("mag_sensor", "§1.2, p. 4", "#page=4"), ("mag_sensor", "§3.5, p. 11", "#page=11")],
         ["3.5", "5.3", "7.6"],
         [("Hinson CNS-MLS manual (maker PDF; sister model, no 160N page found)",
           "https://a.storyblok.com/f/298593/x/23d805c5f4/cns-mls-manual-v1-2-1-20231212_.pdf")]),
    fact("hardware", "Sensor spacing",
         "Utilities tab: Distance F/B 2454 mm, Distance L/R 1494 mm (unlabelled; probably between opposite "
         "sensors).", [("perf_eval", "Utilities tab, A1:B2", "#gid=1126988253&range=A1:B2")], ["3.7"]),
    fact("hardware", "Offset saturation",
         "The reported magnetic offset (MagDias) tops out at ±75 mm, so a larger deviation reads as 75.",
         [("node_acc", "Method", NA_METHOD), ("node_acc", "Results", NA_RESULTS)], ["5.3", "7.6"]),
    fact("hardware", "Stopping accuracy",
         "Spec table: parking accuracy ±20 mm. Troubleshooting: \"excessive positional deviation\" (alarm 30) "
         "means more than 5 cm. Requirement 3.6 asks for 10 mm.",
         [("manual", "§3.3 spec table, p. 9", ""), ("manual", "§6.11, p. 100, row 16", "")], ["3.6"]),
    fact("hardware", "Gyroscope",
         "None named in the manual or the component list; HITO's 3.7 answer offers one as a paid upgrade.",
         [("components", "whole list", ""), ("manual", "§3.3, p. 9", "")], ["3.7"]),
    fact("hardware", "Rotation steering",
         "Rotation steers the wheels to −85° against +90° for strafe, a 175° sweep of about 3 s at 60°/s; the AGV "
         "loses its rotation direction on 90° turns (HW006).",
         [("tracker", "Hardware-Brandon tab, HW006", AT_HW006)], ["3.7", "6.1"]),
    fact("hardware", "Drive and speed",
         "Drive wheel per the component list: Tongy TYD200-SM30030BG-32-9814-SM040BB-45; the manual's spares "
         "table names steering wheel TEC198P302SP40-32-22HS-C and servo SMC-0100-30MAK-5DSU. Speed: up to "
         "1.2 m/s unloaded, 1 m/s loaded (manual); HITO says 1.0 m/s is a hardware cap.",
         [("components", "row Drive Wheel", ""), ("manual", "§3.3, p. 9; §7 spares, p. 104", ""),
          ("v2_issues", "Integration, 5th bullet", "")], ["7.7"],
         [("TYD200 drive wheel (distributor listing; maker unconfirmed)",
           "https://www.directindustry.com/prod/suzhou-honpine-precision-industry-co-ltd/product-4614476-2861089.html"),
          ("Kinco SMC80S-0100-30M servo (similar model; match unconfirmed)",
           "https://anaheimautomation.com/media/anaheim/literature/manuals/servo/L011921%20-%20SMC80S-0100-30M%20Servo%20Motor.pdf")]),
    fact("hardware", "Lidar",
         "Hinson SE-1026, front and rear: 270°, 64 detection patterns. HITO says the wiring limits Volley to 16.",
         [("components", "row Lidar", ""), ("manual", "§3.3, p. 9; §4.2, p. 13", ""),
          ("v2_issues", "Integration, 4th bullet", "")], ["8.1", "8.2"],
         [("Hinson SE-1026 (distributor page)", "https://aifitlab.com/products/hinson-se-1026-lidar")]),
    fact("hardware", "Controller and screen",
         "Main controller: HITO-customised EX5510 \"Linglong\" board, firmware GalaxyBattleShip_Qr V0.5. "
         "Touchscreen: Kinco GL070E, the HMI whose values 5.1, 5.4 and 5.13 ask to have reported.",
         [("components", "rows Main Control Board, TouchScreen, Firmware", ""), ("manual", "§6.3.5, p. 46", "")],
         ["5.1", "5.4", "5.13"],
         [("Kinco GL070 flyer (distributor PDF)", "https://www.gotronik.pl/images/Flyer_GL070_EN_M202106.pdf")]),
    fact("hardware", "Network",
         "TP-Link (普联技术有限公司) TL-CPE1300D工业级 wifi bridge, a China-only industrial model.", [("manual", "§6.3.2–6.3.4, pp. 43–46", "")],
         ["2.3", "2.4"],
         [("TP-Link TL-CPE1300D quick-install guide (maker PDF, Chinese)",
           "https://service.tp-link.com.cn/download/20239/TL-CPE1300D%E5%B7%A5%E4%B8%9A%E7%BA%A7%20V1.1"
           "%E5%BF%AB%E9%80%9F%E5%AE%89%E8%A3%85%E6%8C%87%E5%8D%97%201.0.1.pdf")]),
    fact("hardware", "Lift",
         "HITO-customised lifting mechanism M0-050010-D2; no pressure or coupling sensor is named.",
         [("components", "row Lifting Mechanism", "")], ["8.3", "8.5"]),
    fact("hardware", "Power",
         "Battery: Jinyuan JYHYLFP-PH 48 V 100 Ah LiFePO4 per the component list, \"48V 96AH\" per the manual. "
         "Wireless charger: DC-WICS2000-048, listed as \"Daocho\"; the maker is 宁波道充科技有限公司 (Ningbo "
         "Douch Power Technology). 24 V supply: SD-350C-24.",
         [("components", "rows LiFePO4 Battery, Wireless Charging", ""), ("manual", "§3.3, p. 9; §6.7.2, p. 90", ""),
          ("charger", "p. 1", "#page=1")],
         [], [("Mean Well SD-350C-24 (DigiKey)",
               "https://www.digikey.com/en/products/detail/mean-well-usa-inc/SD-350C-24/7706520")]),
    # ---- grid
    fact("grid", "Tape width",
         "**Not settled; the sources conflict.** HITO's install guide and quote: 30 mm (× 1.2 mm). Matt heard "
         "HITO's standard is 50 mm; PT: \"30mm, 50mm, it's doing the same thing\". Karen: use 25 mm for now; the "
         "homebrew used 50 mm, and 30 mm costs $1.20/m against $4.86/m (13 Apr). Brandon: 25 mm looks best, though "
         "30 mm with retuned gains is \"incrementally improved\" (28 Jul). Grid Tape Layout '24: 2 in (50 mm).",
         [("strip_install", "§1.1, p. 3", "#page=3"), ("quote", "p. 1, item 1.1", "#page=1"), "s_tape_50",
          "s_tape_pt", "s_tape_25", "s_tape_cost", "s_tape_best", "s_tape_30",
          ("tape_layout", "Assembly Steps, step 1", GTL_STEPS)], ["7.6"]),
    fact("grid", "Tape at a node",
         "Tape must reach to or past all four magnetic sensors. Bay node stubs are 4 in long, centred on the "
         "nominal sensor position, assuming ±1 in landing.", ["s_tape_past"], ["3.6"]),
    fact("grid", "Parallel strips", "Keep parallel strips more than 50 mm apart.",
         [("mag_sensor", "§4.2, p. 14", "#page=14")]),
    fact("grid", "Installing tape",
         "HITO: dry, clean floor; cover with a wider protective strip; joints under 2 mm; keep magnets away; wear "
         "damage under 10 cm is tolerated. Volley: professional floor clean, alcohol wipe, laser line, continuous "
         "tape node to node; turn circles (20.5 in radius) are no longer needed.",
         [("strip_install", "§2.3, p. 4", "#page=4"), ("strip_install", "§2.4–2.5, p. 5", "#page=5"),
          ("tape_layout", "Assembly Steps", GTL_STEPS), "s_taping"]),
    fact("grid", "Reader height and tag spacing",
         "Maker's guidance for the reader: mount 30–40 mm above the tags; keep tags more than 100 mm apart, because "
         "the reader can't read two at once and close tags give wrong data. Generic Hinson advice, not HITO's grid "
         "spec, and drawn with Hinson's own tag (CNS-CRFID-01), not the WYN tag HITO supplies.",
         [("hinson_rfid", "§3.2, p. 10", "#page=10")], ["3.6", "5.1"]),
    fact("grid", "RFID tags per node",
         "One tag at each intersection, placed with a template. Sandbox nodes 4, 8, 13, 18, 22 and 25 carry all four "
         "tags, so the AGV can stop there in any heading. Several tags per node with an offset reader was proposed "
         "for heading localisation.",
         [("tape_layout", "Assembly Steps, step 3", GTL_STEPS), "s_four_tags", "s_multi_tag"], ["5.12"]),
    fact("grid", "Node spacing",
         "**Not settled.** 24 in minimum from the RFID side (23.6 in absolute, measured with non-production tags; "
         "13 May). 8 in \"theoretical minimum\" for charge nodes (14 Sep). Whether short spacing works depends on "
         "fixing the overshoot on close nodes, and the new tags are not yet characterised (28 Sep).",
         ["s_spacing_24", "s_spacing_8", "s_new_tags"], ["3.6", "7.7"]),
    fact("grid", "Clearance",
         "45 in either side of the tape centreline when carrying a tray, including a 1 in buffer.", ["s_clearance"]),
]

GAPS = [
    "The RFID reader's actual mounting height on the HITO AGV, and the read range with HITO's WYN tags. Only "
    "the maker's generic figures (30–40 mm, up to 140 mm) are known.",
    "What the S signal value means and its scale (5.1 asks for it to be reported).",
    "How the AGV derives heading from the first tag it reads (5.12).",
    "Any HITO spec for tag spacing, tag offset from the node centre, or tags per node. Volley's decoding of the "
    "V2 tag format isn't written down either.",
    "A gyroscope or IMU on the V2: neither the manual nor the component list names one. Only the V3 (Raven) "
    "spec sheet lists inertial navigation.",
    "The hydraulic pump and any pressure sensor (relevant to 8.5), and the wifi antenna.",
    "How far tape should run past a node, other than the 4 in bay stubs.",
    "Chinese originals: the CNS-MGS-160N manual exists on Drive only as a Google-translated copy (original title "
    "CNS-MGS-160N使用手册V1.6.6); HITO's manual, strip guide and component list are English only. No Chinese name "
    "was found for Hinson, Tongy, Jinyuan, Yufeng, WYN or Kinco.",
    "The CN tab's direct link: the workbook is an .xlsx, so its CN tab has no stable gid; open the sheet and switch "
    "tabs.",
    "The Confluence \"Grid Layout\" and \"Layout Design Constraints\" pages could not be read from here; the "
    "second has no known link.",
]

for _k, _r in REFS.items():
    assert all(rid in BY_ID for rid in _r["reqs"]), (_k, _r["reqs"])
for _f in FACTS:
    assert all((src if isinstance(src, str) else src[0]) in REFS for src in _f["sources"]), _f["subject"]
    assert all(rid in BY_ID for rid in _f["reqs"]), _f["subject"]


def refs_for(rid):
    """Listed documents (not Slack messages) that relate to requirement rid, in REFS order."""
    return [k for k, r in REFS.items() if r["list"] and rid in r["reqs"]]
