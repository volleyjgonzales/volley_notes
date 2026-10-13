# 03 — Regression and benchmark plan

## 1. Two distinct verification goals

**Behavioral equivalence** asks whether the extracted default solver produces the same valid decisions and constraints as the old Scheduler method. **Performance benchmarking** asks whether runtime/resource usage changes for comparable inputs. A single GTest success result is not a benchmark baseline.

Current fixtures directly construct `ScheduleContext` from a `DiscreteGarageState`, add `TrayMove`/`BayTransition` events to `ctx->events`, then call `scheduler.DoTrayAssignments(ctx)` and/or `scheduler.DoAgvAssignments(ctx)`. The test snapshot shows both unit-level and end-to-end cases; benchmark-specific code is **not** present in the uploaded files.

## 2. Existing tests worth preserving

| Existing test | Verified scenario | Why it matters |
|---|---|---|
| `TrayAssignmentTest` | Resolve move with unspecified destination | Smallest tray solver smoke test |
| `TrayAssignmentTestComplexDag` | Crowded `triple_pick_lot`, tray 13 toward bay 1 | Blocking/cyclic graph and downstream motion planning |
| `UnblockingTrayMoveTest` | `tiny_lot` tray to bay | Basic blocking and resulting DAG |
| `ResolveBlockingTraysRecursivelyUnblocksChain` | Root at node 6, nested blockage toward free node 14 | Recursive prerequisite ordering |
| `TrayAndAgvAssignments` | Both stages combined | Interface integration |
| `MiAmigaEsSuAmiga` | Closer AGV disabled | Feasible AGV chosen, not just closest |
| `AmigaSaysNo` | Disabled AGV blocks viable path | Proper no-solution result |
| `AmigaStash` | Three chained tray moves, two AGVs | Assignment identity and transitive DAG relations |
| `NoAmigas` | No feasible AGV | Failure semantics; no accidental graph growth |
| `AmigaBaySos` / `AmigaBaySo` | Bay transition traps/releases AGV | Non-tray roots change assignment eligibility |
| `TrayLiftBayTransitionDependencyTest` | Lift/lower around bay transitions | Precise ordering and DAG constraints |
| `CleanGarageUnstashesTrayFromWaypoint` | Waypoint-stashed tray reparked to parking | Tier-2 behavior remains reachable through Plan |

Source: `src/planner/scheduler/test/scheduler_tests.cpp` in the uploaded tests snapshot. Note: some tests primarily assert success, not full assignment equivalence. Strengthen with new snapshot/assertions rather than assuming they already prove parity.

## 3. Proposed benchmarking dataset (requirements, not completed scenarios)

The parent ticket requires **at least 10 scenarios based on real customer site layouts for each solver**. Below is a candidate coverage matrix, **not** a claim that these cases have been located or run. Each row must be backed by an approved actual-site fixture or a documented site-derived anonymized layout.

| ID | Tray benchmark characteristic | AGV benchmark characteristic |
|---|---|---|
| 01 | Low occupancy / short move | One nearby feasible AGV |
| 02 | Occupied destination / repark | Multiple candidates and distance tie |
| 03 | Single blocking tray | Candidate with loaded lift state |
| 04 | Recursive chain of blocking trays | Disabled closer candidate |
| 05 | Cyclic narrow aisle | Occupied/stuck bay AGV |
| 06 | High occupancy / no repark available | Unreachable AGV-to-tray route |
| 07 | Waypoint-stash fallback | Non-tray event gates a tray root |
| 08 | Different payload footprints | Multi-AGV node-arrival dependencies |
| 09 | Several jobs / independent tray moves | Multiple eligible moves / bottleneck matching |
| 10 | Multiple dependent moves of one tray | Reassign same AGV across event chain |

Real-site fixture fields should include approved site/layout identifier, layout content/hash, scenario initial state, requested event DAG, expected observed result, code SHA, and whether the sample is anonymized. Confirm physical geometry from actual layout data before drawing site-accurate 2D maps.

## 4. Compare semantically, not by `shared_ptr` or volatile GUID alone

For a test scenario $k\in\{1,\ldots,K\}$, where $K\in\mathbb N$ is the number of scenarios, capture:

- Success/failure and stable error class; raw diagnostic strings can be compared separately.
- Every tray choice, assigned destination node and heading, assigned AGV, and event job index.
- Vertices by stable *semantic event identity*, not raw pointer address; record deterministic occurrence indexes when events have identical data.
- Directed prerequisite pairs and DAG reachability for ordered actions; `Reduce()` can remove redundant direct edges while preserving ordering.
- The mapping of first clearing events per tray, and the final discrete garage state when event application succeeds.
- Post-solver motion and action outputs in end-to-end tests where available.

Define the Boolean equivalence result $e_k\in\{0,1\}$ to be one only when the documented comparison rules pass. The pass proportion $p\in[0,1]$ for $K$ scenarios is:

$$
p=\frac{1}{K}\sum_{k=1}^{K}e_k.
$$

For a strict parity release gate, require $p=1$ and investigate all deviations. If matching is nondeterministic, define acceptable equivalence classes **before** taking measurements; do not excuse unexpected differences after the fact.

## 5. Benchmark methodology

Measure the solver call in isolation after fixture construction; separately measure `Scheduler::Plan` end-to-end. Avoid mixing startup, YAML parsing, ROS component construction, and graph rendering into a solver-only timing. Use release/optimized build flags consistently and keep test hardware, ROS distro, dependency versions, and thread count pinned.

Let the measured duration $t_{k,r}\in\mathbb R_{\ge0}$ [ms] denote scenario $k$ on repetition $r\in\{1,\ldots,R\}$, where the repetition count $R\in\mathbb N$. For each scenario, record the sample median $\widetilde t_k\in\mathbb R_{\ge0}$ [ms], a high-percentile measurement (e.g., $t_{k,0.95}$ [ms]) when sufficient repetitions exist, and the baseline median $\widetilde t_k^{(0)}$ [ms]. Define the runtime ratio $q_k\in\mathbb R_{\ge0}$ as:

$$
q_k=\frac{\widetilde t_k}{\widetilde t_k^{(0)}}.
$$

The ratio $q_k$ is meaningful only when the baseline duration $\widetilde t_k^{(0)}>0$ [ms]. A ratio above one indicates a slower candidate. Do not set a performance threshold without team agreement and variance measurements. Save raw repeated timings and statistics as machine-readable CSV/JSON, not only screenshots.

Recommended result schema:

```text
solver,scenario_id,site_fixture,code_sha,build_type,host,iteration,elapsed_ms,success,event_count,edge_count,semantic_hash
```

`semantic_hash` means a canonical serializer over semantic event results, **not** the hash of event pointers or container iteration ordering.

## 6. Build and run commands

Inside the configured ROS 2 container/workspace:

```bash
colcon build --packages-up-to scheduler scheduler_advanced_tests --event-handlers console_direct+
colcon test --packages-select planner_core scheduler scheduler_advanced_tests --event-handlers console_direct+
colcon test-result --verbose
```

If existing colcon profiles/wrappers (`poe`, `.colcon`, separate virtual environment) set build flags or environment variables, honor those conventions. A successful build alone does not establish that all tests ran; inspect `colcon test-result` and logs. Specific Google Benchmark integration has not been observed in supplied CMake files and should not be assumed.

## 7. Minimum acceptance checklist

- [ ] Default tray solver returns same semantic assignment/dependency result on curated cases.
- [ ] Default AGV solver does the same, including non-tray root draining and node-arrival constraints.
- [ ] Both solver interfaces can be instantiated with test-controlled dependencies.
- [ ] `Scheduler::Plan` uses only new interfaces for both assignment phases.
- [ ] Legacy production assignment methods removed after test migration.
- [ ] At least 10 approved real-site benchmark scenarios for **each** solver.
- [ ] Baselines from original implementation recorded with code hash, environment, and raw samples.
- [ ] Benchmark output reviewed for reproducibility and semantic parity.
- [ ] Scheduler unit tests, advanced scenarios, and applicable system tests pass.

## 8. Source/evidence limitations

The supplied `scheduler_advanced_tests/CMakeLists.txt` registers seven scenarios but not their bodies. The currently supplied test source does not prove 10 benchmark fixtures exist. The original customer-site geometry and AGV mechanical dimensions were not supplied, so the 2D SVG uses illustrative axes and footprints. No benchmark timings are presented as observed values in this document.

## 9. Example behavior-regression assertions

The current repository has tests verifying `TrayMove` resolution and `DoAgvAssignments`. A parity harness should compare semantic content, not only success flags. The following is schematic GoogleTest code, not a drop-in existing test:

```cpp
EXPECT_EQ(reference.success, candidate.success);
EXPECT_EQ(reference.moves.size(), candidate.moves.size());
for (size_t i = 0; i < reference.moves.size(); ++i) {
  EXPECT_EQ(reference.moves[i].tray_id, candidate.moves[i].tray_id);
  EXPECT_EQ(reference.moves[i].destination, candidate.moves[i].destination);
}
EXPECT_EQ(reference.dependencies, candidate.dependencies);
EXPECT_EQ(reference.first_tray_event, candidate.first_tray_event);
```

`reference` and `candidate` above are hypothetical normalized result structures. In actual tests, the last map must be canonicalized to stable event identifiers rather than compared as pointer values. Generated event order and semantic prerequisite reachability should be recorded independently; a topological sort alone does not establish a unique execution order.

For a runtime sample $t_k\in\mathbb R_{\ge0}$ (seconds), with repetition index $k\in\{1,\ldots,N\}$ and repetition count $N\in\mathbb N_{>0}$, report the median $\widetilde{t}\in\mathbb R_{\ge0}$ and sample dispersion rather than a single best time. Preserve layout provenance and build revision with each result.
