# Study site

A static website for the three study documents. Their **sources are the HTML files in `src/content/`**; they are
the single source of truth (there is no Markdown copy). The build adds everything that could otherwise go stale.

## Use

```bash
cd site
npm ci              # exact versions from package-lock.json
npm run dev         # http://localhost:4321 (reload after editing a content file)
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
- **Computed at build time**:
  - section numbers (from `data-num` on headings) and figure numbers (document order);
  - the text of every `<a class="ref">`: "section 13.5", "Figure 12", always the current number;
  - `doc 02` → that tab;
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
| Document sources (edit these) | `src/content/01-software-background.html`, `02-issue-and-proposal.html`, `03-verification-plan.html` |
| HTML sources → page pipeline (numbering, references, figures, MathML, Shiki highlighting, keyword links) | `src/lib/render.ts` |
| Document list, tab names, doc 01 parts | `src/data/docs.ts` |
| Keyword links and definitions | `src/data/glossary.yaml` |
| Styles (design tokens at the top) | `src/styles/site.css` |
| Client behaviour (routing, scroll spy, search, lightbox) | `src/scripts/app.js` |
| Design system (generated with ui-ux-pro-max) and this page's overrides | `design-system/scheduler-study/` |
| Figure copy step (`predev` / `prebuild`) | `scripts/sync-figures.mjs` |

The pipeline parses the sources with unified/rehype directly (not Astro's Markdown support), so numbers, references
and keyword links are computed with every document's headings known. The build **fails** on a link to a missing id,
a duplicate id, a `ref` to an unnumbered heading, a missing figure file, or a glossary target that does not exist.

### Editing a document

The header comment of each source file lists the conventions. In short:

```html
<h2 data-num id="bg-the-garage-model-in-code">The garage model in code</h2>   <!-- numbered: "6" -->
<h3 data-num id="bg-garagegraph-and-its-vertex">GarageGraph and its Vertex</h3> <!-- numbered: "6.3" -->
<h3 id="bg-how-to-read-the-code-snippets">How to read the code snippets</h3>    <!-- not numbered -->

<p>... see <a class="ref" href="#bg-garagegraph-and-its-vertex">section 6.3</a> and
   <a class="ref" href="#bg-fig-76_garage_graph_vertex">Figure 9</a> ...</p>     <!-- numbers rewritten at build -->

<figure id="bg-fig-76_garage_graph_vertex">
  <img src="figures/76_garage_graph_vertex.svg" alt="What a GarageGraph Vertex is">
  <figcaption>Caption without "Figure N —"; the build adds the label.</figcaption>
</figure>

<span class="math">\mathbf p=[x,y]^\mathsf T</span>   <div class="math">\pi(u) &lt; \pi(v)</div>
<pre><code class="language-cpp">// highlighted by Shiki</code></pre>
```

Ids are permanent: they are the deep links. Give a new heading an id once and keep it when the title changes.
Ids carry the document prefix (`bg-`, `pr-`, `vr-`); figure ids are `<prefix>-fig-<svg name>`.

### Adding a keyword

Add an entry to `src/data/glossary.yaml`:

```yaml
- term: working_state
  code: [working_state]            # inline-code spellings
  text: [working state]            # plain-text phrases
  to: bg-every-job-sees-the-garage-through-working_state   # heading id
  def: A scratch copy of initial_state advanced by replaying events.
```
