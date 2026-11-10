"""Build site/index.html from docs/AGV_requirements_illustrated.md.

    python sitegen/build_site.py

Pipeline: Python-Markdown (tables, def_list) -> BeautifulSoup post-processing
(figures, requirement anchors, status badges, auto-links) -> Jinja2 template.
Output is deterministic (no timestamps), so diffs in version control only show
real content changes.
"""
import json
import re
import shutil
import sys
from pathlib import Path

import markdown
from bs4 import BeautifulSoup, NavigableString
from jinja2 import Environment, FileSystemLoader, select_autoescape

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "generator"))
from data import (R, GROUPS, SOURCE, SHEET_EN, VERDICT, VERDICTS, FIG_COVERS, PRIORITY, PROPOSED,  # noqa: E402
                  CONTESTED, effort, history, source_url)
from svgkit import STATUS  # noqa: E402
from references import REFS, refs_for  # noqa: E402
from contract import clause, PROPOSAL  # noqa: E402
from data import SHEET_CN  # noqa: E402
from glossary import TERMS  # noqa: E402

DOCS = ROOT / "docs"
SRC = DOCS / "AGV_requirements_illustrated.md"
OUT = ROOT / "site"
HERE = Path(__file__).resolve().parent

REQ_IDS = {r[0] for r in R}
REQ_BY_ID = {r[0]: r for r in R}
STATUS_KEY = {v[2]: k for k, v in STATUS.items()}  # letter -> key
TOPICS = {"order", "instantActions", "state", "visualization", "connection", "factsheet", "commonMessage"}
SKIP_TAGS = {"a", "code", "pre", "h1", "h2", "h3", "h4", "script", "style", "dt", "title", "button", "abbr"}


def slug(text):
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def req_anchor(rid):
    return "req-" + rid.replace(".", "-")


def fig_anchor(label):
    return "fig-" + label.lower().replace(".", "-")


def remark_anchor(rid):
    return "volley-" + rid.replace(".", "-")


def source_link(soup, rid):
    row = SHEET_EN[rid]["row"]
    a = soup.new_tag("a", attrs={"href": source_url(rid), "class": "src", "target": "_blank", "rel": "noopener",
                                 "title": f"Open row {row} of the {SOURCE['version']} sheet (verbatim EN / CN)"})
    a.string = "↗"
    return a


def tag(soup, name, cls=None, text=None, **attrs):
    if cls:
        attrs["class"] = cls
    t = soup.new_tag(name, attrs=attrs)
    if text is not None:
        t.string = text
    return t


def figure_panel(soup, name, label):
    """Status panel shown beside a figure: one card per requirement the figure illustrates.
    Message-structure figures (n.S) get a compact list; drawings get full cards with history."""
    ids = FIG_COVERS.get(name)
    if not ids:
        return None
    compact = label.endswith(".S")
    panel = tag(soup, "aside", "fig-panel" + (" compact" if compact else ""),
                **{"aria-label": f"Status of the requirements in Figure {label}"})
    panel.append(tag(soup, "p", "fp-head", "Requirements using these fields" if compact else
                     ("Requirement in this figure" if len(ids) == 1 else f"{len(ids)} requirements in this figure")))
    for rid in ids:
        _, st, req, resp, d, t = REQ_BY_ID[rid]
        contested = VERDICT.get(rid) in CONTESTED
        card = tag(soup, "div", f"fp-req st-{st}" + (" contested" if contested else ""))
        head = tag(soup, "div", "fp-row")
        head.append(tag(soup, "a", "fp-id", rid, href=f"#{req_anchor(rid)}", title=f"{rid}: {req}"))
        head.append(badge(soup, st))
        if rid in VERDICT:
            head.append(verdict_badge(soup, rid))
        head.append(source_link(soup, rid))
        card.append(head)
        if not compact:
            card.append(tag(soup, "p", "fp-text", req))
            cn = SHEET_CN.get(rid)
            if cn and cn.get("requirement"):
                det_cn = tag(soup, "details", "fp-cn")
                det_cn.append(tag(soup, "summary", None, "中文原文"))
                for k, label in (("requirement", "需求"), ("hito_response", "海通回复"), ("hito_remark", "备注")):
                    if cn.get(k):
                        para = tag(soup, "p", lang="zh-CN")
                        para.append(tag(soup, "span", "fp-k", label))
                        para.append(tag(soup, "span", None, cn[k]))
                        det_cn.append(para)
                src_p = tag(soup, "p", "fp-cn-src", "Verbatim from the CN tab of the ")
                src_p.append(tag(soup, "a", None, "V1.1 workbook", href=source_url(rid), target="_blank",
                                 rel="noopener", title="Opens the EN row; switch to the CN tab"))
                det_cn.append(src_p)
                card.append(det_cn)
            facts = tag(soup, "div", "fp-facts")
            for k, v in (("HITO", resp), ("Effort", effort(d, t)), ("Proposed", PROPOSED)):
                row = tag(soup, "p")
                row.append(tag(soup, "span", "fp-k", k))
                row.append(tag(soup, "span", None, v))
                facts.append(row)
            if rid in PRIORITY:
                row = tag(soup, "p", "fp-priority")
                row.append(tag(soup, "span", "fp-k", "Priority"))
                row.append(tag(soup, "span", None, "Resolve before on-site"))
                facts.append(row)
            lab, url = clause(rid)
            row = tag(soup, "p", "fp-contract")
            row.append(tag(soup, "span", "fp-k", "Contract"))
            links = tag(soup, "span")
            links.append(tag(soup, "a", None, f"Criterion {lab}", href=url, target="_blank", rel="noopener",
                             title=f"Matching acceptance criterion in {PROPOSAL['title']} (gates the $50k QA payment)"))
            links.append(" · ")
            links.append(tag(soup, "a", None, "status", href="#hito-contract"))
            row.append(links)
            facts.append(row)
            docs = refs_for(rid)
            if docs:
                row = tag(soup, "p", "fp-docs")
                row.append(tag(soup, "span", "fp-k", "Docs"))
                links = tag(soup, "span")
                for i, key in enumerate(docs):
                    if i:
                        links.append(" · ")
                    links.append(tag(soup, "a", None, REFS[key]["short"], href=REFS[key]["url"],
                                     target="_blank", rel="noopener",
                                     title=f"{REFS[key]['title']} ({REFS[key]['date']})"))
                links.append(" · ")
                links.append(tag(soup, "a", None, "all", href="#hardware-and-grid-reference"))
                row.append(links)
                facts.append(row)
            card.append(facts)
            det = tag(soup, "details", "fp-history")
            if len(ids) == 1:
                det["open"] = ""
            det.append(tag(soup, "summary", None, "History"))
            ol = tag(soup, "ol")
            for date, who, text, link, kind in history(rid):
                li = tag(soup, "li", f"ev-{kind}")
                li.append(tag(soup, "span", "ev-date", date or "now"))
                body = tag(soup, "span", "ev-body")
                body.append(tag(soup, "strong", None, who))
                body.append(" ")
                if link:
                    ext = not link.startswith("#")
                    a = tag(soup, "a", None, text, href=link)
                    if ext:
                        a["target"], a["rel"] = "_blank", "noopener"
                    body.append(a)
                else:
                    body.append(text)
                li.append(body)
                ol.append(li)
            det.append(ol)
            card.append(det)
        panel.append(card)
    return panel


def verdict_badge(soup, rid):
    key = VERDICT[rid]
    a = soup.new_tag("a", attrs={"href": f"#{remark_anchor(rid)}", "class": f"vbadge v-{key}",
                                 "title": VERDICTS[key][1] + " Read Volley's remark."})
    a.string = VERDICTS[key][0]
    return a


# ---------------------------------------------------------------- regexes
UNIT = r"(?:m/s²|m/s|mm|m|s|kg|rad|V|t|Hz|px|days?)"
REQ_RE = r"(?<![\w.\-/])(\d\.\d{1,2}(?:\.\d)?)(?!\d|\.\d|\s?" + UNIT + r"\b|°|%)"
FIG_RE = r"\bFigure (\d+\.(?:\d+|S))(?![\w.]\w)"


def glossary_patterns(figmap):
    pats = []
    for gslug, term, variants, definition in TERMS:
        definition = definition.format(**figmap)
        for v in variants:
            forms = {v}
            if v[0].islower():
                forms.add(v[0].upper() + v[1:])
            for f_ in forms:
                pats.append((f_, gslug, definition))
    pats.sort(key=lambda p: -len(p[0]))  # longest first
    return pats


GLOSS = []
GLOSS_DEF = {}


def plain(definition, figmap_inv):
    return re.sub(r"\s+", " ", definition)


# ---------------------------------------------------------------- build
def build():
    md_text = SRC.read_text(encoding="utf-8")
    html = markdown.markdown(md_text, extensions=["tables", "def_list", "sane_lists"], output_format="html")
    soup = BeautifulSoup(f"<div id='doc'>{html}</div>", "html.parser")
    doc = soup.find(id="doc")
    figmap = json.loads((DOCS / "figures.json").read_text())
    fig_by_label = {v: k for k, v in figmap.items()}
    GLOSS[:] = glossary_patterns(figmap)
    GLOSS_DEF.update({g[0]: g[3].format(**figmap) for g in TERMS})

    # title + lede
    h1 = doc.find("h1")
    title = h1.get_text()
    h1.decompose()
    lede = []
    for el in list(doc.children):
        if getattr(el, "name", None) == "h2":
            break
        if getattr(el, "name", None) == "p":
            lede.append(el.extract())

    # section ids
    for h2 in doc.find_all("h2"):
        t = h2.get_text()
        m = re.match(r"(\d)\. ", t)
        h2["id"] = f"group-{m.group(1)}" if m else slug(t)
        if m:
            h2.string = ""
            num = soup.new_tag("span", attrs={"class": "group-num"})
            num.string = m.group(1)
            h2.append(num)
            h2.append(t[3:])

    # figures
    for p in doc.find_all("p"):
        img = p.find("img")
        if not img or len(p.get_text(strip=True)) > 0:
            continue
        cap = p.find_next_sibling("p")
        strong = cap.find("strong") if cap else None
        if not strong or not strong.get_text().startswith("Figure"):
            continue
        label = re.match(FIG_RE, strong.get_text()).group(1)
        name = fig_by_label[label]
        src = img["src"]
        svg_head = (DOCS / src).read_text(encoding="utf-8")[:400]
        wm = re.search(r'width="(\d+)" height="(\d+)"', svg_head)
        fig = soup.new_tag("figure", attrs={"class": "fig", "id": fig_anchor(label), "data-name": name,
                                                 "data-label": label})
        if name == "overview":
            fig.append(status_grid(soup))
        else:
            a = soup.new_tag("a", attrs={"class": "fig-media", "href": src, "target": "_blank", "rel": "noopener",
                                         "aria-label": f"Open Figure {label} full size"})
            new_img = soup.new_tag("img", attrs={"src": src, "alt": img.get("alt", ""), "loading": "lazy",
                                                 "width": wm.group(1), "height": wm.group(2)})
            a.append(new_img)
            fig.append(a)
            if int(wm.group(1)) > 1000:
                fig["class"] = fig["class"] + ["fig-wide"]
        fc = soup.new_tag("figcaption")
        label_el = soup.new_tag("span", attrs={"class": "fig-label"})
        label_el.string = f"Figure {label}"
        ttl = soup.new_tag("span", attrs={"class": "fig-title"})
        ttl.string = strong.get_text().split(". ", 1)[1].rstrip(".")
        fc.append(label_el)
        fc.append(ttl)
        strong.decompose()
        body = soup.new_tag("span", attrs={"class": "fig-body"})
        for c in list(cap.contents):
            body.append(c.extract())
        fc.append(body)
        fig.append(fc)
        panel = figure_panel(soup, name, label)
        if panel is not None:
            fig["class"] = fig["class"] + ["has-panel"]
            fig.append(panel)
        p.replace_with(fig)
        cap.decompose()

    # tables
    for table in doc.find_all("table"):
        head = [th.get_text(strip=True) for th in table.find_all("th")]
        wrap = soup.new_tag("div", attrs={"class": "table-wrap"})
        table.wrap(wrap)
        if head[:1] == ["ID"]:
            table["class"] = ["req-table"]
            for tr in table.find("tbody").find_all("tr"):
                tds = tr.find_all("td")
                rid = tds[0].get_text(" ", strip=True).split()[0]
                tr["id"] = req_anchor(rid)
                tds[0]["class"] = ["c-id"]
                link = soup.new_tag("a", attrs={"href": f"#{req_anchor(rid)}", "class": "self"})
                link.string = rid
                tds[0].clear()
                tds[0].append(link)
                tds[0].append(source_link(soup, rid))
                letter = tds[3].get_text(strip=True)[0]
                tds[3].clear()
                tds[3].append(badge(soup, STATUS_KEY[letter]))
                tds[3]["class"] = ["c-status"]
                tds[4]["class"] = ["c-effort"]
                tds[5]["class"] = ["c-volley"]
                tds[5].clear()
                if rid in VERDICT:
                    tds[5].append(verdict_badge(soup, rid))
                    if VERDICT[rid] in CONTESTED:
                        tr["class"] = ["contested"]
                else:
                    tds[5].string = "—"
        elif head[:1] == ["Letter"]:
            for tr in table.find("tbody").find_all("tr"):
                tds = tr.find_all("td")
                key = STATUS_KEY[tds[0].get_text(strip=True)]
                tds[0].clear()
                tds[0].append(badge(soup, key, label=False))

    # Volley remark lists: "<id> — <verdict>" terms get anchors, a verdict badge and a sheet link
    for dl in doc.find_all("dl"):
        dts = dl.find_all("dt")
        if not dts or not all(re.match(r"\d+(?:\.\d+)+ — ", dt.get_text()) for dt in dts):
            continue
        dl["class"] = ["vremarks"]
        for dt in dts:
            rid = dt.get_text().split(" — ")[0]
            dt["id"] = remark_anchor(rid)
            dt.clear()
            back = soup.new_tag("a", attrs={"href": f"#{req_anchor(rid)}", "class": "self"})
            back.string = rid
            dt.append(back)
            dt.append(verdict_badge(soup, rid))
            dt.append(source_link(soup, rid))

    # glossary definition list ids
    gl = doc.find("h2", id="glossary")
    if gl:
        dl = gl.find_next_sibling("dl")
        by_term = {t[1]: t[0] for t in TERMS}
        for dt in dl.find_all("dt"):
            dt["id"] = "g-" + by_term[dt.get_text(strip=True)]

    autolink(soup, doc, figmap)

    # sidebar model
    sections = []
    cur = None
    for el in doc.children:
        nm = getattr(el, "name", None)
        if nm == "h2":
            gid = el["id"]
            gnum = gid.split("-")[1] if gid.startswith("group-") else None
            cur = {"id": gid, "num": gnum, "title": GROUPS[gnum] if gnum else el.get_text(), "entries": [],
                   "keywords": " ".join(r[0] for r in R if gnum and r[0].split(".")[0] == gnum)}
            sections.append(cur)
        elif nm == "figure" and cur is not None:
            cur["entries"].append({"id": el["id"], "label": el.find(class_="fig-title").get_text(),
                                 "num": el["data-label"]})
        elif nm == "div" and "table-wrap" in el.get("class", []) and cur and cur["num"]:
            el.find("table")["id"] = f"table-{cur['num']}"
            cur["entries"].append({"id": f"table-{cur['num']}", "label": "Requirements table", "num": None})

    counts = {}
    for r in R:
        counts[r[1]] = counts.get(r[1], 0) + 1
    stats = [{"key": k, "label": STATUS[k][0], "letter": STATUS[k][2], "n": counts.get(k, 0)}
             for k in ["works", "implement", "conditional", "duplicate", "process", "blocked", "rejected"]]

    # Every link that leaves the page opens in a new tab, so the reader keeps their place here.
    for root in [doc, *(p for p in lede if hasattr(p, "find_all"))]:
        for a in root.find_all("a", href=re.compile(r"^(https?:|mailto:)")):
            a["target"], a["rel"] = "_blank", "noopener"

    env = Environment(loader=FileSystemLoader(HERE / "templates"), autoescape=select_autoescape(["html"]))
    page = env.get_template("page.html.j2").render(
        title=title, lede="".join(str(p) for p in lede), content=str(doc.decode_contents()),
        sections=sections, stats=stats, total=len(R),
        req_index=[{"id": r[0], "anchor": req_anchor(r[0]), "text": r[2]} for r in R])

    if OUT.exists():
        shutil.rmtree(OUT)
    (OUT / "assets").mkdir(parents=True)
    shutil.copytree(DOCS / "images", OUT / "images")
    for f in (HERE / "static").iterdir():
        shutil.copy(f, OUT / "assets" / f.name)
    (OUT / "index.html").write_text(page, encoding="utf-8")
    (OUT / ".nojekyll").write_text("", encoding="utf-8")
    print(f"site/index.html written: {len(sections)} sections, {len(figmap)} figures")


def badge(soup, key, label=True):
    lab, _, letter = STATUS[key]
    span = soup.new_tag("span", attrs={"class": f"badge st-{key}"})
    dot = soup.new_tag("span", attrs={"class": "badge-dot", "aria-hidden": "true"})
    dot.string = letter
    span.append(dot)
    if label:
        t = soup.new_tag("span")
        t.string = lab
        span.append(t)
    else:
        span["aria-label"] = lab
    return span


def status_grid(soup):
    wrap = soup.new_tag("div", attrs={"class": "req-grid", "role": "list"})
    for r in R:
        rid, st = r[0], r[1]
        cls = f"tile st-{st}" + (" contested" if VERDICT.get(rid) in CONTESTED else "")
        title = f"{rid}: {STATUS[st][0]}. {r[2]}"
        if rid in VERDICT:
            title += f" Volley 9 Nov: {VERDICTS[VERDICT[rid]][0]}."
        a = soup.new_tag("a", attrs={"class": cls, "href": f"#{req_anchor(rid)}", "role": "listitem",
                                     "title": title})
        i = soup.new_tag("span", attrs={"class": "tile-id"})
        i.string = rid
        l_ = soup.new_tag("span", attrs={"class": "tile-letter", "aria-label": STATUS[st][0]})
        l_.string = STATUS[st][2]
        a.append(i)
        a.append(l_)
        wrap.append(a)
    return wrap


def autolink(soup, doc, figmap):
    combined = re.compile(f"(?P<fig>{FIG_RE})|(?P<req>{REQ_RE})")
    section = None
    seen_terms = set()
    in_glossary = False
    for el in list(doc.children):
        nm = getattr(el, "name", None)
        if nm == "h2":
            section = el.get("id")
            seen_terms = set()
            in_glossary = section == "glossary"
            continue
        if not hasattr(el, "find_all"):
            continue
        # topic names in code spans -> glossary entries
        for code in el.find_all("code"):
            txt = code.get_text()
            root = re.split(r"[.\[/ ]", txt, maxsplit=1)[0]
            if root in TOPICS and code.parent.name != "a":
                a = soup.new_tag("a", attrs={"href": f"#g-{root.lower()}", "class": "code-link",
                                             "title": re.sub(r"\s+", " ", GLOSS_DEF[root.lower()])})
                code.wrap(a)
        for node in list(el.find_all(string=True)):
            if not isinstance(node, NavigableString) or not node.strip():
                continue
            if any(p.name in SKIP_TAGS for p in node.parents if p is not None and p.name):
                continue
            if any(set(p.get("class") or []) & {"c-id", "fig-label", "fig-title", "fig-panel"}
                   for p in node.parents if p is not None and hasattr(p, "get")):
                continue
            text = str(node)
            pieces = []
            pos = 0
            # pass 1: figure and requirement references
            for m in combined.finditer(text):
                if m.group("fig"):
                    lab = m.group(2)
                    if lab not in figmap.values():
                        continue
                    pieces.append(text[pos:m.start()])
                    pieces.append(("a", f"#{fig_anchor(lab)}", m.group(0), "xref fig-ref", None))
                else:
                    rid = m.group("req")
                    if rid not in REQ_IDS:
                        continue
                    pieces.append(text[pos:m.start()])
                    pieces.append(("a", f"#{req_anchor(rid)}", rid, "xref req-ref",
                                   f"{rid}: {REQ_BY_ID[rid][2]}"))
                pos = m.end()
            pieces.append(text[pos:])
            # pass 2: glossary terms (first occurrence per section)
            if not in_glossary:
                out = []
                for piece in pieces:
                    if not isinstance(piece, str):
                        out.append(piece)
                        continue
                    out.extend(gloss_split(piece, seen_terms))
                pieces = out
            if len(pieces) == 1 and isinstance(pieces[0], str):
                continue
            new = []
            for piece in pieces:
                if isinstance(piece, str):
                    if piece:
                        new.append(NavigableString(piece))
                else:
                    _, href, label, cls, title = piece
                    a = soup.new_tag("a", attrs={"href": href, "class": cls})
                    if title:
                        a["title"] = title
                    a.string = label
                    new.append(a)
            first = new[0]
            node.replace_with(first)
            prev = first
            for n_ in new[1:]:
                prev.insert_after(n_)
                prev = n_


def gloss_split(text, seen):
    for term, gslug, definition in GLOSS:
        if gslug in seen:
            continue
        m = re.search(r"(?<![\w\-])" + re.escape(term) + r"(?![\w\-])", text)
        if m:
            seen.add(gslug)
            left = gloss_split(text[:m.start()], seen)
            right = gloss_split(text[m.end():], seen)
            return left + [("a", f"#g-{gslug}", m.group(0), "xref term", re.sub(r"\s+", " ", definition))] + right
    return [text]


if __name__ == "__main__":
    build()
