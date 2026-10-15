# Study site

A static website for the three study documents (`../01-software-background.md`, `../02-issue-and-proposal.md`,
`../03-verification-plan.md`). The Markdown files stay the single source of truth; this folder only renders them.

## Use

```bash
cd site
npm ci              # exact versions from package-lock.json
npm run dev         # http://localhost:4321, rebuilds on save (Markdown changes need a reload)
npm run build       # -> dist/index.html + dist/figures/
npm run check       # type-check the Astro/TypeScript sources
npm run artifact    # -> dist-artifact/ (dist/ without the html/head/body skeleton, for claude.ai artifacts)
```

`dist/` is self-contained: one HTML file with inlined CSS and JS, plus the SVG figures. Open it from any static
host or from disk. Web fonts load from Google Fonts and fall back to system fonts offline.

## What the page does

- **Three tabs**, one per document. Every heading and figure has a stable id, so any URL hash is a deep link
  (`#bg-13-schedulecontext-in-depth-job-indices-and-bookkeeping-maps`, `#pr-fig-3`). Back/forward work.
- **Left contents**: sticky, scrolls on its own, follows your position (scroll spy), expands the current section,
  and filters as you type. Doc 01 is grouped into the four parts of the reading plan.
- **Right rail** (wide screens): the subsections of the section you are reading.
- **Links added at build time**:
  - `section 13.5`, `sections 7–10`, `doc 01, section 16`, `(6.1)` → the heading;
  - `Figure 12` → the figure;
  - `doc 02` → that tab;
  - links between the Markdown files (`02-issue-and-proposal.md#...`) → the matching heading;
  - **keywords** from `src/data/glossary.yaml` → the section that explains them, first mention per subsection,
    with a hover card showing the definition.
- **Search** (`Ctrl K`, `⌘K` or `/`): headings and glossary terms across all three documents.
- **Figures**: click to open a pan/zoom viewer; "Pan / zoom viewer" opens the full figure gallery.
- Keys `1`, `2`, `3` switch documents. Light and dark themes follow the system, with a toggle.

## How it is built

| Piece | File |
|---|---|
| Page shell, tabs, dialogs | `src/pages/index.astro` |
| Contents sidebar, section rail | `src/components/Sidebar.astro`, `src/components/Rail.astro` |
| Markdown → HTML pipeline (unified: remark-gfm → rehype, Shiki highlighting, link and figure transforms) | `src/lib/render.ts` |
| Document list, tab names, doc 01 parts | `src/data/docs.ts` |
| Keyword links and definitions | `src/data/glossary.yaml` |
| Styles (design tokens at the top) | `src/styles/site.css` |
| Client behaviour (routing, scroll spy, search, lightbox) | `src/scripts/app.js` |
| Design system (generated with ui-ux-pro-max) and this page's overrides | `design-system/scheduler-study/` |
| Figure copy step (`predev` / `prebuild`) | `scripts/sync-figures.mjs` |

The pipeline does not use Astro's own Markdown rendering: it runs unified directly, so heading ids, cross-document
links and keyword links are computed with every document's headings known.

### Adding a keyword

Add an entry to `src/data/glossary.yaml`:

```yaml
- term: working_state
  code: [working_state]            # inline-code spellings
  text: [working state]            # plain-text phrases
  to: "01#14.4"                    # doc + section number, or "01:heading text"
  def: A scratch copy of initial_state advanced by replaying events.
```

The build fails if a target does not resolve, so renumbered sections are caught.

### After editing the Markdown

Section and figure numbers live in the Markdown. When sections or figures move, run from the repository root:

```bash
python3 scripts/renumber_figures.py   # caption numbers and "Figure N" references
python3 scripts/add_toc.py            # the Contents block GitHub shows
```
