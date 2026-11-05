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
from data import R, GROUPS  # noqa: E402
from svgkit import STATUS  # noqa: E402
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


# ---------------------------------------------------------------- regexes
UNIT = r"(?:m/s²|m/s|mm|m|s|kg|rad|V|t|Hz|px|days?)"
REQ_RE = r"(?<![\w.\-/])(\d\.\d{1,2})(?!\d|\.\d|\s?" + UNIT + r"\b|°|%)"
FIG_RE = r"\bFigure (\d+)\b"


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
    fig_by_num = {v: k for k, v in figmap.items()}
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
        num = int(re.match(r"Figure (\d+)", strong.get_text()).group(1))
        name = fig_by_num[num]
        src = img["src"]
        svg_head = (DOCS / src).read_text(encoding="utf-8")[:400]
        wm = re.search(r'width="(\d+)" height="(\d+)"', svg_head)
        fig = soup.new_tag("figure", attrs={"class": "fig", "id": f"fig-{num}", "data-name": name})
        if name == "overview":
            fig.append(status_grid(soup))
        else:
            a = soup.new_tag("a", attrs={"class": "fig-media", "href": src, "target": "_blank", "rel": "noopener",
                                         "aria-label": f"Open figure {num} full size"})
            new_img = soup.new_tag("img", attrs={"src": src, "alt": img.get("alt", ""), "loading": "lazy",
                                                 "width": wm.group(1), "height": wm.group(2)})
            a.append(new_img)
            fig.append(a)
            if int(wm.group(1)) > 1000:
                fig["class"] = fig["class"] + ["fig-wide"]
        fc = soup.new_tag("figcaption")
        label = soup.new_tag("span", attrs={"class": "fig-label"})
        label.string = f"Figure {num}"
        ttl = soup.new_tag("span", attrs={"class": "fig-title"})
        ttl.string = strong.get_text().split(". ", 1)[1].rstrip(".")
        fc.append(label)
        fc.append(ttl)
        strong.decompose()
        body = soup.new_tag("span", attrs={"class": "fig-body"})
        for c in list(cap.contents):
            body.append(c.extract())
        fc.append(body)
        fig.append(fc)
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
                rid = tds[0].get_text(strip=True)
                tr["id"] = req_anchor(rid)
                tds[0]["class"] = ["c-id"]
                link = soup.new_tag("a", attrs={"href": f"#{req_anchor(rid)}", "class": "self"})
                link.string = rid
                tds[0].clear()
                tds[0].append(link)
                letter = tds[3].get_text(strip=True)[0]
                tds[3].clear()
                tds[3].append(badge(soup, STATUS_KEY[letter]))
                tds[3]["class"] = ["c-status"]
                tds[4]["class"] = ["c-effort"]
        elif head[:1] == ["Letter"]:
            for tr in table.find("tbody").find_all("tr"):
                tds = tr.find_all("td")
                key = STATUS_KEY[tds[0].get_text(strip=True)]
                tds[0].clear()
                tds[0].append(badge(soup, key, label=False))

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
                                 "num": el["id"].split("-")[1]})
        elif nm == "div" and "table-wrap" in el.get("class", []) and cur and cur["num"]:
            el.find("table")["id"] = f"table-{cur['num']}"
            cur["entries"].append({"id": f"table-{cur['num']}", "label": "Requirements table", "num": None})

    counts = {}
    for r in R:
        counts[r[1]] = counts.get(r[1], 0) + 1
    stats = [{"key": k, "label": STATUS[k][0], "letter": STATUS[k][2], "n": counts.get(k, 0)}
             for k in ["works", "implement", "conditional", "duplicate", "process", "blocked", "rejected"]]

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
        a = soup.new_tag("a", attrs={"class": f"tile st-{st}", "href": f"#{req_anchor(rid)}", "role": "listitem",
                                     "title": f"{rid}: {STATUS[st][0]}. {r[2]}"})
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
            if any(set(p.get("class") or []) & {"c-id", "fig-label", "fig-title"}
                   for p in node.parents if p is not None and hasattr(p, "get")):
                continue
            text = str(node)
            pieces = []
            pos = 0
            # pass 1: figure and requirement references
            for m in combined.finditer(text):
                if m.group("fig"):
                    n = int(m.group(2))
                    if n not in figmap.values():
                        continue
                    pieces.append(text[pos:m.start()])
                    pieces.append(("a", f"#fig-{n}", m.group(0), "xref fig-ref", None))
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
