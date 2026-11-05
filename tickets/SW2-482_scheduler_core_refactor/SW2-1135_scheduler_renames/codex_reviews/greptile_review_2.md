# Greptile's second review (2026-11-02, commit 8f9315c1) and its evaluation

Read with `gh api repos/VolleyAutomation/volley/pulls/1018/comments` (inline),
`gh api repos/VolleyAutomation/volley/issues/1018/comments` (summary, outside diff) and
`gh api repos/VolleyAutomation/volley/pulls/1018/reviews`. Summary: confidence 4/5, "No functional blocker was
established, but the two explicit comment requirements should be satisfied before merging"; outside the
diff: "No findings outside the diff remain" (the deleted tiny_lot test, review 19, is resolved). Both
findings cite Greptile's own custom context ("Commit and PR hygiene"), not a file in the repo; the review
prompt's rule 4 says the same ("`TODO`s carry a key"). Checked here (item 269). Item 2 applied in item 271
(commit 6, with a full comment sweep); item 1 waits for the tickets.

| # | Finding | Check | Verdict |
|---|---|---|---|
| 1 | `tray_assignment.cpp:557` (also `agv_assignment.cpp:96`, `scheduler.cpp:241`): a `TODO` without a ticket key. | The scheduler has five `TODO(any)`, all from commit 1, which turned main's 24 named TODOs (`Gunther`, `isabel`, `Any`, …) into the seven still open: `agv_assignment.cpp:96` (AGVs start idle), `scheduler.cpp:205` (planning depends on `RemoveRedundantEdges` there), `scheduler.cpp:241` (a retrieve without a process-retrieve action reported executing), `tray_assignment.cpp:153` (the advance fallback parks anywhere on the root path), `tray_assignment.cpp:557` (repark destinations ignore the retrieval heading). Greptile names three; the other two are the same case. `acli jira workitem search` finds no open SW2 ticket for any of them. | Agree. Five tickets under SW2-1067 (Scheduler/Dispatcher Improvements), then `TODO(SW2-<n>)` in commit 1 where each was written. Creating tickets is the user's call. |
| 2 | `move_job_tests.cpp:54`: "Was scheduler_advanced_tests' OverlappingAgvAssignmentFailureTest2." records history, not a reason. | Confirmed; the commit message already says where the test came from. | Agree: delete the line in commit 6. |

CI on `8f9315c1` (run 41523411626, still running at the time): `unit-tests / all (sim…)` failed after its
25 tests passed, on "The runner has received a shutdown signal": infrastructure; rerun it when the run ends.
