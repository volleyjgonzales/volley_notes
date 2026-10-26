# Page override: study site (`src/pages/index.astro`)

Overrides MASTER.md for the single-page study site. Everything not listed here follows MASTER.md.

| Topic | MASTER.md | This page | Why |
|---|---|---|---|
| Interactive accent | Green `#22C55E` | Sky `#38BDF8` (dark) / `#0369A1` (light); green kept for the reading-progress bar and "term" labels | The figures already use green, sky, amber and violet as meanings (response side, request side, ...). Links in sky stay distinct from figure semantics, and green on near-black is a cliché we avoid |
| Background | `#020617` | `#0B1120` page, `#0F172A` surfaces and figure frames | `#0F172A` is the figures' own background, so figures sit flush in their frames |
| Heading font | JetBrains Mono | IBM Plex Sans 600; JetBrains Mono for section numbers, tabs, labels and code | Long headings with inline code read better in a proportional face |
| Themes | Dark | Dark first, full light theme (`prefers-color-scheme` + manual toggle). Figures keep their dark frame in both | Readers print/scan in light mode; the SVGs are dark by design |
| Motion | Scroll reveal | None on content; 150–250 ms hover/focus transitions only; all disabled under `prefers-reduced-motion` | Long-form reading; content is complete at rest |

Layout: sticky top bar (document tabs, search, theme) · left sticky contents that scroll on their own · reading column of ~46rem
with figures, tables and code up to ~62rem · right "On this section" rail at ≥1280 px · contents become a drawer below 960 px.
