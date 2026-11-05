#!/usr/bin/env bash
# Replies to Dan's three reviews of PR #1018 (2026-11-03). Run after the force-push.
# Each reply goes into the thread of the inline comment whose id it names.
set -euo pipefail

repo=VolleyAutomation/volley
pr=1018

reply() {
  gh api -X POST "repos/${repo}/pulls/${pr}/comments/$1/replies" -f body="$(cat)" >/dev/null
  echo "replied to $1"
}

react() {
  gh api -X POST "repos/${repo}/pulls/comments/$1/reactions" -f content="$2" >/dev/null
  echo "reacted to $1"
}

# Review 1
reply 4457348192 <<'EOF'
01-04 ran on 576_eccles, which is decommissioned (the one tiny_lot test became `MoveJob.TwoTrayMovesWithAgvUnderOneTray`). 05-07 run on layouts still in service and each guards a planning fix, so I kept them and renamed them: `cross_floor_pathing_tests`, `vrc_insertion_cycle_tests` and `chokepoint_pathing_tests`.
EOF
react 4457350408 +1
react 4457556096 +1
reply 4457602136 <<'EOF'
Yes, I'd like to do that as a separate PR (the node and component wrappers and `Param` together). I'll make a ticket.
EOF

# Review 2
reply 4457650562 <<'EOF'
Agreed. On your question: `SucceededEvent` is never called with a message, so no caller relies on a success text. Since this adds API to common_ros, I'll do it in a follow-up PR as you suggested and make a ticket.
EOF
reply 4457650583 <<'EOF'
Agreed. The reasons are only logged inside motion_planner today (`SolveSequential` returns `optional`), so this needs a motion_planner change as well. I'll do it in a follow-up and make a ticket.
EOF
reply 4457650597 <<'EOF'
Throwing is deliberate: callers only pass vertices from the graph itself. Added the one-line note and a test for an unknown vertex.
EOF
reply 4457650611 <<'EOF'
Good catch. It returns `stdx::Result` with "The graph must be a DAG." again, and the callers propagate it. Added a test.
EOF
reply 4457650624 <<'EOF'
Done. The charger search returns `nullopt` on the error.
EOF
reply 4457650634 <<'EOF'
Done. I also made four AGV-ordering methods private, since nothing outside `Scheduler` calls them either.
EOF
reply 4457650642 <<'EOF'
Moved into `volley::scheduler`. The `std::hash` specialisation stays, because task_planner's `BottleneckAssignment` uses the default hasher, but it now lives in `agv_assignment.cpp`.
EOF
reply 4457650653 <<'EOF'
Done: `AgvAssignmentState`, `TrayAssignmentState` and `CandidateMove` are now each defined in the one .cpp that uses them. `ResolveRequest` stays for now, since `ResolveBlockingTrays` is public and tested; it moves with the tray module.
EOF
reply 4457650661 <<'EOF'
Done: they moved to `move_events.hpp`.
EOF

# Review 3
reply 4457901158 <<'EOF'
Done, including moving `GetVersionInfo` into scheduler.cpp.
EOF
for id in 4457901167 4457901176 4457901182 4457901191 4457901199 4457901216 4457901225 4457901238 4457901264; do
  reply "$id" <<'EOF'
Done.
EOF
done
reply 4457901252 <<'EOF'
Done. I left `planner_core_msgs.hpp` itself for a later cleanup.
EOF

# Conversation
gh api -X POST "repos/${repo}/issues/${pr}/comments" -f body="$(cat <<'EOF'
Thanks for the reviews, Dan! The changes are pushed. The `ApplyTo`/`OnEvent` migration, the `PlanMotions` failure reasons and the rclcppx move will be follow-up tickets.
EOF
)" >/dev/null
echo "posted the summary comment"
