# Justin's review of PR #1018 (2026-11-03, two comments on commit 1 `fb84e9c0`) and the plan

Read with `gh api repos/VolleyAutomation/volley/pulls/1018/reviews` (5757247273, 5757282767, both
without a body) and `gh api "repos/VolleyAutomation/volley/pulls/1018/comments?per_page=100"` (author
`volleyjabel`). Nothing newer as of this file.

| # | Thread | Comment | Check |
|---|---|---|---|
| 1 | 4458633422, `scheduler.hpp:84` | Why isn't `Scheduler` in `volley::scheduler`? Its methods must write `scheduler::` everywhere; only tests and the ROS component name the class. | Confirmed: 169 `scheduler::` prefixes in the package. Outside it, only agvctl's `move_planner.hpp` (one member) and the three advanced tests name `Scheduler` / `SchedulerParams`. Not in PROMPT.md. |
| 2 | 4458661278, `scheduler.hpp:53` | `volley::` inside `namespace volley` is redundant; remove "either here or in the future". | Confirmed: 394 in the library (77 in headers, 317 in sources), 189 in the tests, 9 in the advanced tests. No name declared in `volley::scheduler` collides with one used as `volley::X`, so dropping the prefix changes no lookup. |

Both are mechanical and change no behaviour: the recordings must stay identical.

## Now or later

Either works; Justin calls both nits.

- **Now:** the C1 stage is about a week out, and the user wanted clean-ups for this PR in the meantime
  (review log, review 19). The next stage then starts from the final names. It adds one review pass
  on an already large PR.
- **Later:** the first commit of SW2-484, ahead of the solver. This PR stays as reviewed.
- **Cost either way:** about 600 touched lines. The tidy hook lints every changed line, so findings
  already on those lines will surface (as with the motion_planner renames, memory
  `volley-tidy-committed-only`). Expect a few to fix.

Recommendation: **now, as a seventh commit** rather than folded into commit 1. Reviewers have read
commits 1-6; a separate commit that is only the namespace move and the prefixes can be reviewed on
its own and dropped if the team prefers to wait. If the user prefers six commits, it folds into
commit 1 with a stage-tolerant script instead, because every later commit must be rebuilt.

## Commit 7 (proposed)

`refactor(scheduler): move Scheduler into volley::scheduler and drop redundant namespace prefixes`

1. `Scheduler`, `SchedulerParams`, `SchedulerSPtr` and `SchedulerRos` move into `volley::scheduler`.
   `SchedulerRos` has to move with the class, because `Scheduler` befriends it by unqualified name.
   `SchedulerComponent` stays in `volley`: `volley::SchedulerComponent` is the registered plugin name
   that `CMakeLists.txt` and `launcher/central_nodes.py` use.
2. The stage files define their methods inside `namespace volley::scheduler`; the
   `using volley::scheduler::X;` lines go, and so do the `scheduler::` prefixes.
3. `volley::` prefixes go wherever the code is inside `namespace volley`: library, tests and advanced
   tests. Code outside the namespace keeps them (file-scope using-declarations, specialisations such
   as the edge key's `std::hash`).
4. Callers: agvctl's `move_planner.hpp` names `scheduler::Scheduler`, and the advanced tests name
   `scheduler::Scheduler` and `scheduler::SchedulerParams`.
5. Checks: build with 0 warnings (scheduler, scheduler_advanced_tests, agvhito_tools), the four
   packages' tests with `SCHEDULER_CHECK_RECORDINGS=1`, tidy on the committed tip, and CI's sim tests
   (the component's plugin name is unchanged).

Out of scope: other packages' `volley::` prefixes; moving `SchedulerComponent` (plugin name).

## Replies (posted 2026-11-03 as 4460977058 and 4460977359; commit 7 is `ff6ba632`)

- **4458633422:** Fixed: `Scheduler` (with `SchedulerParams` and `SchedulerRos`) is now in
  `volley::scheduler`. `SchedulerComponent` stays in `volley`, since that's its plugin name.
- **4458661278:** Agreed, they're gone across the package now, in the same commit (ff6ba632).
