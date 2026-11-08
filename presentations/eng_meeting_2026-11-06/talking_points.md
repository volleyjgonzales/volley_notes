# Talking points: engineering meeting, Fri 2026-11-06

Format from the agenda: one slide, 3 minutes of status, 3 minutes of Q&A. The
same script is in the slide's speaker notes (press `S`). The slide is a roadmap
from Oct 2026 to Mar 2027: three projects and one auxiliary support lane. **Past
bars are actual dates; blue bars are targets; purple bars are open-ended
research and development**, with no method selected yet. Scheduler stages are
spaced 4–8 days apart, the pace so far, so the refactor mostly finishes by the
new year. Adjust any bar in `src/slide.html` (`data-start` / `data-end`) and run
`npm run export`.

## Script (about 3 minutes)

| Time | Say |
| --- | --- |
| 0:00–0:20 | This roadmap covers three related projects through March: the scheduler refactor, the motion planning refactor, and research in multi-agent path finding. Hito support continues alongside them. |
| 0:20–1:20 | **Scheduler (task planning)**: the objective is to make the scheduler safe to change. The planning tests are recorded scenario files (PR #1007), so every change must reproduce the current plans exactly. PR #1018, merged yesterday, restructured the scheduler into one file per pipeline stage and fixed 14 latent defects. Each stage has merged within about a week, so the remaining stages should largely complete by year end: the tray solver interface, the AGV assignment module, the follow-up cleanup; benchmarks in January. |
| 1:20–1:55 | **Motion planning refactor**: studied in October; in-depth review mid-November to early December. In January, refactor and redesign the interfaces toward a more conventional problem description: tasks as sequences of goals assigned to agents, with constraints between goals across tasks, preserving the event sequencing the scheduler depends on. The design is not final. |
| 1:55–2:20 | **Research**: preliminary notes exist; focused work from December. From February all three areas move to research and development: translating published algorithms into code that can be validated on site. No method has been selected. |
| 2:20–2:50 | **Candidate directions** (for evaluation): the six candidates in the right-hand panel, one sentence each (see below). |
| 2:50–3:00 | **Hito (auxiliary)**: delivered the pause and e-stop policy in October; continuing support as required. |

## Candidate directions (for evaluation)

From a light literature search on 2026-11-06 and the study pack's evaluation of
the event-graph strategy. Each is a direction to read and prototype against the
recorded scenarios and benchmarks, not a plan.

| Idea on the slide | What it would mean here | Where to start |
| --- | --- | --- |
| **Puzzle-based tray rearrangement** (task planning) | Moving blocking trays out of the way is a puzzle-based storage problem: units on a grid, a few empty cells ("escorts"), retrieve one item with the fewest moves. Exact and heuristic searches exist and name cars as a unit load. Could replace or check today's greedy blocking-tray resolution | Rosenfeld, [Optimal retrieval in puzzle-based storage with heuristic search and tabulation](https://cris.iucc.ac.il/en/publications/optimal-retrieval-in-puzzle-based-storage-with-heuristic-search-a/), _Networks_ 2022; Yalcin, Koberstein, Schocke, [An optimal and a heuristic algorithm for the single-item retrieval problem in puzzle-based storage systems with multiple escorts](https://ideas.repec.org/a/taf/tprsxx/v57y2019i1p143-165.html), _IJPR_ 2019 |
| **Off-peak vehicle pre-positioning** (task planning) | Use idle AGV time to move cars expected out soon closer to the bays, so rush-hour retrievals are short. Volley's own patent covers rearranging by pickup time; the paper gives algorithms for a dense robotic garage | Guo, Yu, [Toward Efficient Physical and Algorithmic Design of Automated Garages](https://arxiv.org/abs/2302.01305), 2023; Volley patent [US 12172633](https://patents.justia.com/patent/12172633) |
| **Search over AGV priority orders** (motion planning) | Today the order of every move is fixed before motion planning and the planner follows it. Priority-based search explores orders while respecting the dependencies between jobs, which matches the scheduler's input | Zhang, Chen, Li, Williams, Koenig, [Multi-Agent Path Finding for Precedence-Constrained Goal Sequences](https://www.ri.cmu.edu/publications/multi-agent-path-finding-for-precedence-constrained-goal-sequences), AAMAS 2022 |
| **Plan repair instead of job rejection** (motion planning) | When planning fails today the whole job is discarded. Large neighbourhood search starts from the colliding plan and replans a few AGVs at a time until it is collision-free; its single-AGV search builds on the same safe-interval search the motion planner uses | Li, Chen, Harabor, Stuckey, Koenig, [MAPF-LNS2: Fast Repairing for Multi-Agent Path Finding via Large Neighborhood Search](https://ojs.aaai.org/index.php/AAAI/article/view/21266), AAAI 2022 |
| **Run-time reordering of AGVs** (execution) | The action graph fixes who passes first. A switchable dependency graph lets execution swap that order when an AGV is delayed, keeping the no-deadlock guarantee | Berndt, van Duijkeren, Palmieri, Kleiner, Keviczky, [Receding Horizon Re-ordering of Multi-Agent Execution Schedules](https://arxiv.org/abs/2312.04190), IEEE T-RO 2024 |
| **Scalable fallback planner** (motion planning) | A planner that finds some feasible plan for hundreds of agents in seconds and improves it over time; useful as a fallback when the main planner fails or a large site is busy | Okumura, [Improving LaCAM for Scalable Eventually Optimal Multi-Agent Pathfinding](https://ijcai.org/proceedings/2023/28), IJCAI 2023 |

Caveats: these come from abstracts and summaries, not full reads. Most assume
grid worlds with single-cell agents; the garage has large footprints, headings
and non-AGV resources (bays, VECS), so each needs adapting.

## Likely questions

- **Are the future dates commitments?** Blue bars are targets from the pace so
  far; purple bars are areas, not deliverables.
- **What will you build next year?** Not decided. The candidate directions panel
  lists options; the benchmarks in January give a way to compare them against
  today's planner.
- **Did the refactor change behaviour?** Only where intended: the bug fixes and
  the removal of one site-specific special case in PR #1018. Every other
  recorded scenario is identical.
- **Examples of the bugs?** A job failing partway through left events that took
  the next job's identity; reparking read a tray's starting position instead of
  its planned one; an AGV already on its charger was sent to another; a cycle in
  AGV pickup order threw an exception nothing caught (would crash the node).
- **What does the motion planning redesign involve?** Describing the problem the
  way the literature does: each agent receives a sequence of goals, and goals in
  different tasks carry ordering constraints. The current event graph encodes
  the same sequencing implicitly; the redesign makes it explicit so that other
  planners can consume it. The details are still being worked out.

## Sources

| Claim | Source |
| --- | --- |
| PR #973 / SW2-876 merged Oct 12 | volley `1a917806`; Jira: Done |
| Refactor plan reviewed Oct 22 | `tickets/SW2-482_scheduler_core_refactor/DESIGN-REVIEW.md` |
| PR #1007 / SW2-1126 merged Oct 29 | volley `61e7b0d7`; Jira: Done |
| PR #1018 / SW2-1135 merged Nov 5 | volley `a468657f`; Jira still "In Review" (move it to Done) |
| 14 latent bugs | behavioural bullets of `fbb65ceb` |
| Remaining scheduler stages | `PROMPT.md` sections 5 and 9; study pack `07-issue-and-proposal`, "Staged plan" |
| Follow-up clean-ups | SW2-1170, SW2-1171, SW2-1172 (Jira: To Do) |
| Motion planning wrap | study pack `07-issue-and-proposal`, "A staged plan for motion planning" |
| Preliminary research | `research/action_dependency_graph/`, `research/mg_tapf_paper_walkthrough/`, `research/bottleneck_assignment.md` |
| Candidate directions | the table above |
