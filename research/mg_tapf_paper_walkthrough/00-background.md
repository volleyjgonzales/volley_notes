# Background: why Multi-Goal Task Assignment and Path Finding (MG-TAPF) is relevant

**Paper:** Zhong et al., _Optimal and Bounded-Suboptimal Multi-Goal Task Assignment and Path Finding_ — International Conference on Robotics and Automation (ICRA), 2022. [Portable Document Format (PDF) paper](https://jiaoyangli.me/files/2022-ICRA.pdf). Relevant sections: I and II.

## The motivating requirement

Suppose there are five automated guided vehicles (AGVs) and a job whose two navigation goals must be visited by **one and the same AGV**:

1. Visit a pickup location $P$.
2. Visit a delivery location $Q$.

The planner should choose *which* AGV performs the operation, but **not** split $P$ and $Q$ across different AGVs.

MG-TAPF models that as **one task containing two ordered goals**:

$$
g_1=\langle P,Q\rangle.
$$

Assigning $g_1$ to agent $a_i$ means that agent $a_i$ must visit $P$ and then $Q$. This same-agent requirement follows from the unit of assignment (the whole task), not from a separate equality constraint between individual goal owners.

```mermaid
flowchart LR
    T["One task g1"] --> P["Goal 1: pickup location P"]
    P --> Q["Goal 2: delivery location Q"]
    A["Chosen AGV ai"] -. "assigned whole task" .-> T
```

## Terminology comparison

| Problem family | What is chosen? | What is fixed or constrained? |
|---|---|---|
| Classical Multi-Agent Path Finding (MAPF) | Collision-free paths | Each agent's goal already assigned |
| Task Assignment and Path Finding (TAPF) | Assignments and paths | Typically one goal per task |
| MG-TAPF (this paper) | Assignments of entire multi-goal tasks and paths | Goal order *within* each task |
| Precedence-constrained TAPF / MAPF | Paths and sometimes assignments | Explicit order between tasks or goals |

The paper solves the **same-agent, ordered-goals** requirement directly. It does **not** generally express arbitrary inter-task precedence directed acyclic graphs (DAGs), such as task $g_3$ having to wait for both $g_1$ and $g_2$ to finish.

## Important limitations in the paper's exact formulation

- Exactly $m$ agents and $m$ tasks.
- Every task is assigned to exactly one agent; every agent gets exactly one task.
- Each task contains an ordered sequence of navigation *locations*.
- Edges are unweighted; moves and waits occur in unit timesteps.
- Each agent stays at the final goal location after completing its task.
- The objective is **minimum flowtime**, the sum of completion times.

For **five AGVs and only one real task**, the literal formal problem has unequal numbers of agents and tasks. One *possible adaptation* is to add four carefully designed no-op/idle tasks; that is a modeling extension, not an operation explicitly demonstrated by the paper. Also, the paper's single-task-per-agent assumption does not directly express multiple sequential jobs assigned to one AGV during one planning instance.

Likewise, a navigation goal in the paper is a *vertex*, not a physical pickup/drop-off action. Carry-state, platform lifting, docking, and shared machinery require additional modeling.

## Read next

[Step 1 — Tasks and notation](01-tasks-and-notation.md)
