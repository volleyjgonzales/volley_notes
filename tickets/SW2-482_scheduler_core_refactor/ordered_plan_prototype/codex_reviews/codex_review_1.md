# Codex review 1 of the ordered-plan proposal (2026-11-08)

Pasted by Jon on 2026-11-08, verbatim. The assessment is in `assessment_1.md`.

---

**I support prototyping a canonical ordered plan. I would revise the proposal before committing to “derive all dependencies once at the end.”** Making state evolution explicit should improve readability substantially; deriving correct concurrency remains the difficult part.

The strongest diagnosis is that the scheduler has several competing ways to represent progress: topological replay, entity chains, tray occupancy history, and AGV assignment’s processing of ready events. The current code confirms that `AssignAgvs` repeatedly consumes non-tray roots before matching tray roots. That is different from simply replaying the order validation uses. Centralizing state replay addresses a real source of complexity.

There are several qualifications to the proposed design.

**1. A list makes insertion precise, but replay must check more than `ApplyTo`.**

Inserting an eviction before a later AGV move and replaying the suffix would catch the stale starting pose. That is a strong benefit.

However, successfully applying events only establishes discrete-state consistency. It does not establish collision-free destinations, reachable routes, valid bay operations, or feasible timing. The insertion operation should distinguish:

- applying an event to compute the next state;
- checking the event’s planning preconditions;
- checking motion feasibility.

Keep these responsibilities named and separate. Otherwise, “replay validates the plan” becomes another misleading abstraction.

Also, a later move does not make relocation fundamentally impossible. It makes the **existing resolved move** invalid. A future planner could recompute that move from its new starting state. For the initial refactor, rejecting such insertions is a reasonable policy.

**2. Start/end overlap alone is not enough to derive every necessary dependency.**

Leaving ordinary traffic conflicts to CHUGG is sensible. Adding dependencies for every intersecting route would unnecessarily serialize motion.

But there is an intermediate case: **an event changes persistent occupancy that another event needs for its route**. An AGV can block an intermediate corridor without overlapping either endpoint of the affected move. The current `OrderAgvMoveAfterBlockerDeparture` explicitly searches for this situation; `OrderAfterTraysOnPath` also adds route-related dependencies.

Those rules cannot disappear into endpoint-overlap checks. The design needs to distinguish:

- temporary motion conflicts, resolved by CHUGG;
- occupancy changes that make another move possible, represented by an explicit prerequisite or an equivalent motion-planner contract.

The revised proposal currently draws that boundary too sharply.

**3. “Reorder independent entries” requires a definition of independence before the final graph exists.**

This is the main unresolved design question.

AGV assignment currently matches a frontier of ready tray moves together. A total order by itself does not identify that frontier. Nor does “different resources” suffice: assignment determines the AGV resource, and geometry can couple otherwise separate resources.

I suggest retaining **explicit prerequisites during planning**, attached to events by stable IDs. The list supplies a canonical replay order consistent with those prerequisites. AGV assignment can batch eligible events and revise the order through one checked operation.

That still eliminates arbitrary graph mutation across the pipeline. It does mean dependency information exists before the final graph is emitted.

**4. Forward-only edges remove structural cycles, not contradictory requirements.**

This is useful, but the contradiction still needs detection and a good explanation. “No insertion position satisfies these prerequisites” is constraint checking under another representation.

Likewise, the `RemoveRedundantEdges` TODO deserves investigation rather than assuming the list removes it. Transitive edges should not change dependency semantics. A consumer that behaves differently when redundant edges exist may still need fixing after the representation changes.

**5. One claim about carrier choice is incorrect.**

Evicting an AGV before assignment does **not** prevent that AGV from subsequently becoming the carrier. We have already discussed the unnecessary charger trip this can produce.

Leaving tray carriers unassigned remains appropriate. Eliminating that unnecessary relocation requires jointly considering carrier choice and relocation, or revisiting the relocation after assignment. A list alone does not provide that optimization.

For naming and structure, I would describe the design as:

| Concept | Responsibility |
|---|---|
| `OrderedPlan` | Events with stable IDs and a canonical replay order |
| Explicit prerequisites | Required ordering and its reason |
| `ReplayPlan` | State evolution and identified precondition checks |
| Checked plan edits | Insert, replace, or reorder events transactionally |
| Dependency derivation | Add resource and occupancy prerequisites |
| Execution graph | Final input to motion planning and action generation |

These are responsibilities, not a recommendation to create six classes immediately. The readability gain should come from fewer mutation paths and clearer contracts.

**The proposed prototype is worthwhile, with stronger acceptance criteria.** Compare dependency **reachability**, not raw edge sets; report missing and additional ordering separately. Then run validation and motion planning against the derived graph and compare success, carrier assignments, and concurrency. Include the earlier/later AGV-move regressions, intermediate-route blockers, and the bay-transition/approach example.

Flattening an existing graph already incorporates its decisions, so matching that graph is evidence of compatibility—not proof that dependencies can be reconstructed while planning.

Finally, **do not assume every recording must change**. Start with a behavior-preserving target. Review necessary changes individually before accepting a bulk re-recording. Suffix replay is linear per insertion, but repeated insertions can make total replay work quadratic; measure geometry and path-search costs too.

My recommendation is to proceed with the prototype around **one canonical replay order, explicit prerequisites, and centralized plan editing**. Treat “the graph is emitted once at the end” as an implementation goal; keep the ordering knowledge that planning needs available throughout. This is a credible simplification without pretending the underlying scheduling constraints have disappeared.
