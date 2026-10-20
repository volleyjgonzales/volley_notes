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

Rebuild the figures first (`python3 scripts/diagrams/build.py NNN_`) if a figure changed.
