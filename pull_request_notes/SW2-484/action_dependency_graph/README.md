# Action Dependency Graphs & SCP — illustrated learning kit

Ground-up learning materials for **Joachim Dunkel, _Streamlining the Action Dependency Graph Framework: Two Key Enhancements_ (2024)**, arXiv:2412.01277. The paper is included at [`source/2412.01277v1.pdf`](source/2412.01277v1.pdf).

## Reading path

| | Chapter | Time | You will learn |
|---|---|---|---|
| 1 | [Visual foundations: the garage, its graph, time, and the worked example](chapters/01-visual-foundations.md) | 40 min | what is in the garage; facility graph vs timed plan vs ADG; conflicts; the plan as filmstrip and table; paths → actions |
| 2 | [From CBS to an action dependency graph](chapters/02-cbs-to-adg.md) | 45 min | CBS by hand; why clock-driven execution fails; type-1 / type-2 edges; the full ADG |
| 3 | [The paper's two improvements, step by step](chapters/03-scp-illustrated.md) | 60 min | wait removal (Theorems 1–2); CP; SCP and why it is correct (Theorem 3); execution consequences; caveats |
| 4 | [Complete mathematical tutorial](chapters/04-complete-mathematical-tutorial.md) | reference | derivations, C++ sketch, exercises (original text, with one correction note in §12.3) |

Chapters 1–3 share **one worked example**: four AGVs (L, M, N, X) in one corner of a parking garage, all crossing the junction W13. Places use the reference naming (P parking stall, W waypoint, B bay, C charger, T tray); AGV names never clash with them. Each chapter ends with checkpoint questions and hidden answers.

## Figures

All 16 figures are rendered SVGs embedded in the chapters (they work offline in VS Code's Markdown preview and on GitHub). For pan and zoom, open [`figures/viewer.html`](figures/viewer.html) in a browser, or open any `.svg` directly.

**Every figure explains its own symbols** in a key at the bottom. Scenes of the garage (figures 1.1, 1.3–1.5, 2.2, 2.3, 3.6) use the reference pack's garage assets: stalls, bays with doors, chargers, AGVs with lift plate and heading chevron, trays, cars.

**Every ADG edge, path, conflict and timing in the figures is computed, not drawn by hand.** `scripts/adg/adg.py` implements Algorithm 1, CP, SCP (both the printed variant and a walk-back variant), wait removal, reachability checks and an event-driven executor; the figure scripts call it and assert the facts they display.

```bash
pip install fonttools brotli                 # once
python3 scripts/adg/test_adg.py              # worked-example numbers + randomised check vs Algorithm 1
python3 scripts/diagrams/build.py            # regenerate figures/*.svg and figures/viewer.html
python3 scripts/diagrams/build.py 08 12      # only figures whose names start with 08 or 12
```

The figure toolkit (`svgkit.py`, `components.py`, `theme.py`, `viewer.py`) is the one from the reference pack, extended with a swim-lane ADG renderer (`adgdraw.py`), a garage scene module adapted from the reference `facility.py` (`garage.py`, `scene.py`) and figure keys (`keys.py`). Fonts (IBM Plex Sans, JetBrains Mono, both SIL OFL) are subset and embedded in each SVG.

## What changed in this revision

- All Graphviz figures were replaced. The ADG figures now use one lane per robot and one column per plan time step, with orthogonally routed type-2 edges labelled by the vertex being handed over.
- Chapters 1–3 were rewritten around the worked example, with step-by-step walkthroughs, full edge tables and checkpoint answers.
- Two technical corrections, both checked by `scripts/adg/test_adg.py`:
  - **Algorithm 3's same-robot branch is safe either way.** If the latest candidate is the target's own robot, skipping the edge (the literal reading of the pseudocode) loses no ordering; walking back to a different-robot candidate (the wording of Theorem 3) only adds a redundant edge. The previous edition said an implementation must walk backwards (chapter 3, §4.5).
  - **SCP is sparse, not minimal.** It guarantees at most one type-2 edge per action, but is not a transitive reduction; the worked example keeps one implied edge (chapter 3, §5.1).

## Scope

The garage and plans are **illustrative**. Stall and bay sizes are the Pecos XL dimensions from the reference pack, but node positions are invented: the Pecos layout YAML was not part of the reference material. With that file the same scenes could be redrawn on real coordinates. Nothing here describes real AGV footprints, firmware or scheduler code. The paper's collision model is "two robots on one vertex"; chapter 3, §7 lists what to re-check before applying its results to a richer model.

**Notation:** italic $t$ for scalars, $\langle s, g, t, R\rangle$ for actions, $a \to b$ for a direct dependency and $a \leadsto b$ for a path.
