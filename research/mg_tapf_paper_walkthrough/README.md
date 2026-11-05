# Multi-Goal Task Assignment and Path Finding (MG-TAPF) paper walkthrough

A self-contained, modular reading companion to:

**Xinyi Zhong, Jiaoyang Li, Sven Koenig, and Hang Ma (2022), _Optimal and Bounded-Suboptimal Multi-Goal Task Assignment and Path Finding_, International Conference on Robotics and Automation (ICRA) 2022.**

- Author Portable Document Format (PDF) paper: https://jiaoyangli.me/files/2022-ICRA.pdf
- Publication record: https://doi.org/10.1109/ICRA46639.2022.9812020
- Carnegie Mellon University (CMU) bibliographic record: https://publications.ri.cmu.edu/optimal-and-bounded-suboptimal-multi-goal-task-assignment-and-path-finding

The examples use an **automated guided vehicle (AGV)** as the robotic agent.

## Acronym reference

Each chapter spells out technical acronyms at first use and uses their short forms afterward. This reference summarizes the terminology across the whole walkthrough.

| Full term | Acronym |
|---|---|
| Automated guided vehicle | AGV |
| Multi-Agent Path Finding | MAPF |
| Task Assignment and Path Finding | TAPF |
| Multi-Goal Task Assignment and Path Finding | MG-TAPF |
| Conflict-Based Search | CBS |
| Conflict-Based Search with Task Assignment | CBS-TA |
| Multi-Label A-star | MLA* |
| Conflict-Based Search with Task Assignment and Multi-Label A-star | CBS-TA-MLA |
| Enhanced Conflict-Based Search with Task Assignment and Multi-Label A-star | ECBS-TA-MLA |
| Constraint tree | CT |
| Multi-Valued Decision Diagram | MDD |
| Cardinal-Conflict Graph | CG |
| Dependency Graph | DG |
| Weighted Dependency Graph | WDG |
| Conflict-Based Search with Task Assignment and Multi-Label A-star with Heuristics | CBSH-TA-MLA |
| Minimum vertex cover | MVC |
| Breadth-first search | BFS |
| Robot Operating System | ROS |
| International Conference on Robotics and Automation | ICRA |
| Portable Document Format | PDF |
| Digital Object Identifier | DOI |
| Carnegie Mellon University | CMU |
| Optical character recognition | OCR |
| Visual Studio Code | VS Code |

## Contents

| File | Topic | Paper sections |
|---|---|---|
| [00-background.md](00-background.md) | Why this paper; what it does and does not solve | Introduction; II |
| [01-tasks-and-notation.md](01-tasks-and-notation.md) | Agents, goals, ordered multi-goal tasks, one-to-one assignments | II |
| [02-paths-time-collisions.md](02-paths-time-collisions.md) | Navigation graph, paths, finish time, collisions, flowtime | II |
| [03-multi-label-a-star.md](03-multi-label-a-star.md) | Multi-Label A-star (MLA*) search state, labels, transitions, and heuristic | IV-B |
| [04-conflict-based-search.md](04-conflict-based-search.md) | Conflict-Based Search (CBS) collisions, constraints, branching, low-level replanning | IV-A |
| [05-task-assignment-cost-matrix.md](05-task-assignment-cost-matrix.md) | **Expanded**: derivation from shortest-path distances, 5-AGV example, complete Hungarian row/column reductions, worked matching, reproducible Python | IV-A |
| [06-search-forest.md](06-search-forest.md) | **Expanded walkthrough**: assignment-specific constraint trees, shared priority queue (`OPEN`), detailed five-AGV queue trace, actual paper example, and conceptual pseudocode | IV-A; IV-D |
| [07-high-level-heuristics.md](07-high-level-heuristics.md) | **New:** high-level A*-style cost bounds, cardinal/semi/non-cardinal conflicts, Multi-Valued Decision Diagrams, CG/DG/WDG graph heuristics, minimum-vertex-cover walkthrough, priority-queue example | V-A; Figure 3 |

## How to read / edit

1. Open this folder in Visual Studio Code (VS Code), then open each `.md` file using Markdown Preview (`Ctrl+Shift+V`).
2. Mathematics uses `$...$` and `$$...$$`; diagrams use fenced Mermaid blocks, compatible with many Markdown previews.
3. Files are separate by design. You can request a change by filename (for example, "revise `03-multi-label-a-star.md`").
4. Diagrams and worked examples are explanatory recreations, not reproduced figures from the paper.
5. Step 6 walks through each high-level expansion, showing exactly which forest nodes enter and leave the shared `OPEN` priority queue.
6. Step 7 explains why some collisions force an increase in cost, using Multi-Valued Decision Diagrams and three related graph heuristics.

## Conventions

- **Paper notation:** $g_j$ is a *task* (an ordered sequence of goal locations); $g_j[k]$ is its $k$-th *goal*. This is a little counterintuitive because the letter $g$ is used for both.
- **Expository notation:** $\sigma(a_i)=g_j$ describes an assignment. The paper's pseudocode writes `N.assignment[ai]` instead; $\sigma$ is not presented as a special paper-defined symbol.
- **Graph vertices vs. Robot Operating System (ROS) poses:** paper goals are graph vertices, not full poses in the two- or three-dimensional special Euclidean groups (SE(2) or SE(3)). The ROS analogy is useful but not an equivalence.
- **Examples:** symbols like $P,Q,R,S$ and illustrative costs are invented small examples to clarify the algorithms. They are not experimental data from the paper.
- **Accuracy:** the formal $m$-agent/$m$-task, one-task-per-agent setup and the stay-at-final-goal assumption are model restrictions, not implementation recommendations for a deployed garage scheduler.

## Not covered yet

This series deliberately does **not** yet cover the inner workings of the next-best assignment generator or bounded-suboptimal Enhanced Conflict-Based Search with Task Assignment and Multi-Label A-star (ECBS-TA-MLA). Step 7 now covers multi-goal Multi-Valued Decision Diagrams and high-level heuristics; the next chapter will cover bounded-suboptimal focal search.
