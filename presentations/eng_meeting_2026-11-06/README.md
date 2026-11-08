# Engineering meeting, Fri 2026-11-06: roadmap slide

One reveal.js slide for the 4-weekly engineering meeting (3 minutes of status, 3 minutes of Q&A): a roadmap from
Oct 2026 to Mar 2027 for the scheduler refactor, the motion planning refactor and MAPF R&D, with AGV Hito as a
support lane, plus what has closed so far.

| File | What it is |
|---|---|
| `src/slide.html` | The slide, with the 3-minute script as speaker notes. Roadmap bars take dates (`data-start`, `data-end`); the build places them |
| `src/slide.css` | The light theme |
| `talking_points.md` | Script, likely questions with answers, and the source of every number on the slide |
| `design_system.md` | Style, colours and type, from the ui-ux-pro-max skill |
| `build.mjs` | Builds `dist/index.html`: one self-contained file (reveal.js, fonts and Lucide icons inlined), works offline |
| `export.mjs` | Writes `exports/slide.png` (3840 × 2160) and `exports/slide.pdf` (one 16:9 page) with headless Chrome |
| `exports/` | The PNG (for pasting into a shared deck) and the PDF |

```
npm ci
npm run build     # dist/index.html
npm run serve     # build, then http://localhost:8011
npm run export    # build, then exports/slide.png and exports/slide.pdf
```

Present: open `dist/index.html`, press `F` for full screen and `S` for the speaker view with the script and timer.
Icons: `<i data-icon="NAME"></i>` with any [Lucide](https://lucide.dev/icons) name (`lucide-static`). Fonts come from `../scheduler_package/scripts/diagrams/fonts`, the same as the study pack and its deck.
