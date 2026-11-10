"""Import the HITO requirements workbook (.xlsx) into sheet.json, verbatim.

    python generator/import_sheet.py path/to/CN&EN停车场功能需求20261109_V1.1.xlsx

Standard library only. Reads the EN and CN tabs and records, per requirement row:
the sheet row number (for deep links), HITO's colour category, and every text cell
as written. data.py keeps the curated statuses and short paraphrases; this file is
the verbatim record that the Volley remarks and the source links come from.

Download the workbook from Drive (File > Download > .xlsx) when a new version
arrives, rerun this, then review `git diff generator/sheet.json`.
"""
import json
import os
import re
import sys
import zipfile
import xml.etree.ElementTree as ET

M = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
R_NS = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"
# HITO's legend (rows below the table): red = needs hardware, green = done / existing,
# blue = joint working mechanism, white = software work for Volley. Yellow is unlabelled
# in the legend and marks 2.3 / 2.4 ("not related to HITO").
FILL_NAME = {"FFFF0000": "red", "theme7": "green", "FFD3F4F1": "blue", "FFFEF2CA": "yellow",
             None: "white", "theme0": "white"}
EN_COLS = {"B": "requirement", "C": "hito_response", "D": "dev", "E": "test", "F": "hito_remark",
           "G": "volley_remark"}
CN_COLS = {"B": "requirement", "C": "hito_response", "D": "dev", "E": "test", "F": "hito_remark"}


def read(path):
    z = zipfile.ZipFile(path)
    x = lambda name: ET.fromstring(z.read(name))
    strings = ["".join(t.text or "" for t in si.iter(M + "t")) for si in x("xl/sharedStrings.xml").findall(M + "si")]
    styles = x("xl/styles.xml")
    fills = []
    for f in styles.find(M + "fills"):
        p = f.find(M + "patternFill")
        fg = p.find(M + "fgColor") if p is not None else None
        fills.append(None if fg is None else (fg.get("rgb") or "theme" + fg.get("theme")))
    xf_fill = [int(xf.get("fillId", 0)) for xf in styles.find(M + "cellXfs")]
    rels = {r.get("Id"): r.get("Target") for r in x("xl/_rels/workbook.xml.rels")}
    sheets = {s.get("name"): "xl/" + rels[s.get(R_NS + "id")].lstrip("/").removeprefix("xl/")
              for s in x("xl/workbook.xml").find(M + "sheets")}

    def rows(sheet, cols):
        out = []
        for row in x(sheets[sheet]).iter(M + "row"):
            cells = {}
            for c in row.findall(M + "c"):
                col = re.match(r"[A-Z]+", c.get("r")).group()
                v, inline = c.find(M + "v"), c.find(M + "is")
                if v is not None:
                    val = strings[int(v.text)] if c.get("t") == "s" else v.text
                elif inline is not None:
                    val = "".join(t.text or "" for t in inline.iter(M + "t"))
                else:
                    val = None
                cells[col] = (val.strip() if val else None, fills[xf_fill[int(c.get("s", 0))]])
            rid = (cells.get("A") or (None,))[0]
            if not rid or not re.fullmatch(r"\d+(\.\d+)+", rid):
                continue
            rec = {"id": rid, "row": int(row.get("r")), "category": FILL_NAME.get(cells["A"][1], cells["A"][1])}
            for col, key in cols.items():
                rec[key] = (cells.get(col) or (None,))[0]
            out.append(rec)
        return out

    return {"file": os.path.basename(path), "en": rows("EN", EN_COLS), "cn": rows("CN", CN_COLS)}


if __name__ == "__main__":
    data = read(sys.argv[1])
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sheet.json")
    with open(out, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=1)
        fh.write("\n")
    print(f"{out}: {len(data['en'])} EN rows, {len(data['cn'])} CN rows")
