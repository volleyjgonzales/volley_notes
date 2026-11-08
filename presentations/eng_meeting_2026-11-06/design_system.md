# Design system for the slide

From the [ui-ux-pro-max skill](https://github.com/nextlevelbuilder/ui-ux-pro-max-skill) (`search.py`, run on
2026-11-05), adapted for a light engineering status slide.

```
search.py "engineering status update presentation light minimal" --design-system --variance 4 --motion 3 --density 5
search.py "developer tool engineering dashboard" --domain color
search.py "technical modern developer clean" --domain typography
```

| Decision | Skill result | Applied |
|---|---|---|
| Style | Minimalism & Swiss Style: clean, high contrast, grid-based, light supported | As is |
| Layout | Slides skill: Timeline Flow | Roadmap with a month and year scale and a today line; closed work and next steps below |
| Neutrals | Slate scale (`#0F172A` ink, `#475569` muted, `#E2E8F0` border) | As is; `#64748B` for small captions (4.8:1 on white) |
| Accent | Gold `#A16207` (design system) / green (developer palettes) | Blue `#1D4ED8` for structure; green (done), amber (in progress) and dashed blue (planned) for status, always next to a text label |
| Type | "Developer Mono": JetBrains Mono + IBM Plex Sans | As is; the same woff2 files as the scheduler study pack |
| Motion | Subtle: 300–400 ms, 8–16 px rise, reduced-motion respected | 420 ms staggered rise on load; none under `prefers-reduced-motion` or in print |
| Icons | SVG, no emoji (Heroicons / Lucide) | Lucide (`lucide-static` 0.460.0), inlined at build time |

## Tokens

| Token | Value | Use |
|---|---|---|
| `--ink` | `#0F172A` | Headings, numbers |
| `--ink-2` | `#334155` | Body |
| `--muted` | `#64748B` | Captions, labels |
| `--border` | `#E2E8F0` | Card borders, month grid lines |
| `--surface` | `#F8FAFC` | Bottom cards |
| `--accent` | `#1D4ED8` | Eyebrow, today line, icon badges, asks |
| `--done` | `#15803D` | Merged |
| `--next` | `#B45309` | Next / in progress |
| `--plan` | `#1E40AF` | Planned bars (dashed) |

Canvas 1920 × 1080; body text 19–26 px, so the smallest text is still legible on a shared Meet screen.
