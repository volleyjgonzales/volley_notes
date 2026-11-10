"""The HITO software agreement: status, sources, and where each requirement sits in it.

Collected 10 Nov 2026. No signed agreement exists yet. The live document is Volley's proposal
(Anne Lu, dated 5 Oct 2026, Chinese first, then English). Its acceptance criteria, which gate
the $50,000 payment, are the 52 requirements in this document, group for group and in the same
order, so requirement n.k is criterion k of group n (the requirement ids skip 5.2 and 7.2; the
criteria are numbered consecutively). The Chinese group headings have anchors; the English ones
don't, so clause links land on the Chinese heading.
"""
from data import R, GROUPS

SLACK = "https://volleyautomation.slack.com/archives/"
PROPOSAL = {
    "title": "Software Agreement Proposal From Volley 10.5.2026",
    "url": "https://docs.google.com/document/d/1RYQ08xsiU6IrbNiLp4Xqp3qNIR3mJ5d08AnT788HJJQ/edit",
    "date": "5 Oct 2026",
    "who": "Anne Lu (Volley), edited by Sam Richardson, Dan Ambrosio, Brandon Peterson",
}
CRITERIA_HEADING = "#heading=h.z31ox5olqy3f"  # 验收标准 (acceptance criteria)
GROUP_HEADING = {  # requirement group -> (Chinese heading text, heading id)
    "1": ("一、旋转", "h.3q9m81yzsbqo"),
    "2": ("二、VDA5050 合规性", "h.z6yznylkiuek"),
    "3": ("三、订单执行", "h.sadlkac4sywd"),
    "4": ("四、配置", "h.2evqnrhjvckn"),
    "5": ("五、状态监测及错误信息", "h.tc19m0sbifh4"),
    "6": ("六、订单执行——旋转方向", "h.wuo62ycifea"),
    "7": ("七、控制", "h.b3dm91ary2em"),
    "8": ("八、安全", "h.qic6mzlwel48"),
}
CRITERIA_PER_GROUP = {"1": 4, "2": 9, "3": 7, "4": 2, "5": 14, "6": 2, "7": 8, "8": 6}  # counted in the proposal

PAYMENTS = [  # Volley's proposed terms
    ("$25,000", "on signing the software agreement"),
    ("$50,000", "after QA, once every acceptance criterion is met"),
    ("$25,000", "a HITO engineer on site in the US for three more months (Volley pays salary, room and board)"),
]

# (date, who, what, link); the source kind is shown as the link text
TIMELINE = [
    ("1 Oct 2026", "Anne Lu", "asks Brandon and Dan for the functional and performance criteria behind the "
     "deposit and final payment", SLACK + "C0C60EUR3T4/p1790867040257479"),
    ("3 Oct 2026", "Sam Richardson", "sets the terms: $25k on signing, the last $25k is inside the $100k and pays "
     "for an extended HITO developer stay, and the $50k waits for the QA acceptance list",
     SLACK + "C08F7BDG69Z/p1791043835771169?thread_ts=1790874735.178549&cid=C08F7BDG69Z"),
    ("5 Oct 2026", "Volley", "proposal sent, with the 52 acceptance criteria", PROPOSAL["url"]),
    ("9 Oct 2026", "HITO", "replies: the full $100,000 in one payment before the source code is delivered (it "
     "licenses the source code); features built by HITO engineers are separate custom work, priced by scope; "
     "about three weeks on site, not three months; then revise \"version 3.0\" of the agreement",
     SLACK + "C0C60EUR3T4/p1791578124787379"),
    ("13 Oct 2026", "Both", "meeting: HITO accepts handing over the source code and extra engineer support, and will "
     "write Volley's feature list into the contract; target source code in November and an engineer on site "
     "in January 2027", SLACK + "C0C60EUR3T4/p1791920277306039?thread_ts=1791920277.306039&cid=C0C60EUR3T4"),
    ("10 Nov 2026", "Volley", "internal sync (Anne, Dan, Jon) on the exact wording of the acceptance criteria and on "
     "how Volley needs to access the source code",
     "https://mail.google.com/mail/?authuser=jon@volleyautomation.com#all/thread-f:1881422959464826965"),
]

# Check the one-to-one mapping between requirement groups and criteria sections.
_by_group = {}
for _r in R:
    _by_group.setdefault(_r[0].split(".")[0], []).append(_r[0])
assert {g: len(v) for g, v in _by_group.items()} == CRITERIA_PER_GROUP, _by_group
assert set(GROUP_HEADING) == set(GROUPS)


def clause(rid):
    """(label, url) of the acceptance criterion that matches requirement rid."""
    g = rid.split(".")[0]
    k = _by_group[g].index(rid) + 1
    cn, hid = GROUP_HEADING[g]
    return f"{cn} {k}", PROPOSAL["url"] + "#heading=" + hid
