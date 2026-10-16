# AGV parking-lot requirements, illustrated

Review of *Functional_requirements-停车场功能需求20261013_V1_0_1.pdf* (v1.0.1, 13 Oct 2026):
52 requirements from Volley, HITO's responses, effort estimates, and generated diagrams,
published as a single static web page.

## Layout

| Path | What it is | Edit by hand? |
|---|---|---|
| `generator/data.py` | The 52 requirements, statuses and estimates | yes |
| `generator/captions.py` | Figure captions | yes |
| `generator/glossary.py` | Glossary terms; also drive auto-linking on the site | yes |
| `generator/figures.py`, `figures2.py`, `uml3.py`, `svgkit.py` | SVG figure code and design tokens | yes |
| `generator/build.py` | Writes `docs/` (SVGs, markdown, figure index) | yes |
| `docs/` | Generated markdown + SVGs (readable on GitHub) | no, regenerate |
| `sitegen/` | Markdown → HTML builder, Jinja2 template, CSS, JS | yes |
| `site/` | Generated website (`index.html`, `images/`, `assets/`) | no, regenerate |
| `design-system/agv-spec/` | Design tokens from UI UX Pro Max (`MASTER.md`, page override) | reference |

## Build

```sh
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
make            # figures + site
make serve      # http://localhost:8000
```

`make check` rebuilds and fails if `docs/` or `site/` differ from what is committed, so CI
can catch hand edits to generated files or forgotten rebuilds. Output is deterministic
(no timestamps), so diffs show only real changes.

## Toolchain choice

- **Python-Markdown + BeautifulSoup + Jinja2**: small, pinned, and the whole transform
  lives in one readable script (`sitegen/build_site.py`). A full static-site generator
  (MkDocs, Docusaurus) would add a theme to fight against for a single page.
- **Static output, no runtime dependencies**: `site/` can be served by any web server,
  GitHub Pages (`.nojekyll` included) or opened from disk.
- Fonts load from Google Fonts with system fallbacks.

## What the site adds over the markdown

- Fixed, scrollable contents sidebar drawn as a tape route; an AGV marker shows the
  current section, and the current group expands to list its figures and table.
- Filter box: filters sections and figures; typing a requirement id (e.g. `5.3`)
  offers a direct link to its table row. Enter follows the first match, Esc clears.
- Auto-links: requirement ids → table rows, `Figure N` → figures, glossary terms
  (first use per section) → glossary entries with the definition as a tooltip.
- Clickable status grid for all 52 requirements; status badges in tables.
- Light and dark colour schemes, mobile drawer, print stylesheet.
