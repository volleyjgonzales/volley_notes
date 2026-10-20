# Stakeholder deck

A reveal.js deck (38 slides, four parts) that introduces the scheduler to software stakeholders with no prior
background and walks through the Scheduler Core Refactor: the problem, the issues and the Jira ticket, the proposed
changes, and future work.

```
npm ci
npm run build      # writes dist/index.html: one self-contained file (reveal.js, fonts and figures inlined)
npm run serve      # build, then serve dist/ on http://localhost:8010
```

- `src/slides.html`: the slides. Speaker notes are in `<aside class="notes">`; press `S` while presenting.
- `src/deck.css`: theme, the same palette and fonts as the study site.
- `src/deck.js`: reveal.js setup and figure stepping.
- `build.mjs`: inlines everything. A placeholder `<div class="fig" data-fig="NAME" data-crop="header" data-play></div>`
  becomes `../figures/NAME.svg`; `data-crop="header"` removes the figure's own title, and `data-play` turns each
  animation step into a fragment, so "next" steps the figure and the caption below it follows.

The light / dark theme follows the OS setting; the button at the top right or `T` switches it. Figures and the deck's own diagrams are recoloured from `figures/theme-map.json` (the build refreshes it with `scripts/diagrams/lightmode.py --map`).

Figures come from two places: the study's figures (`figures/`, rebuilt with `python3 scripts/diagrams/build.py NNN_`) and the deck's own figures (`deck/figures/`, the running example of Part 1, rebuilt with `python3 scripts/diagrams/fig_deck.py`). A placeholder name is looked up in `deck/figures/` first.

Colour roles and naming rules for the slides are listed in the comment at the top of `src/slides.html`.
