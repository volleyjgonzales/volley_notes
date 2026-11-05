# Plan: squash the SW2-1135 branch from sixteen commits to six

Written 2026-10-30 for a fresh session. Read `CLAUDE.local.md` in the workspace first: every git
write goes through `volley-in-container git ...`, never push, never force, stage by name, and stop
if the container is not running. Nothing in this plan changes a single line of code: the tree at
the end must be byte-identical to the tree at the start.

## Starting point

- Repository `/home/jon-gonzales/volley`, branch `jmg/SW2-1135/scheduler-renames-and-cleanups`,
  sixteen commits on base `5d5d7b39` (origin/main), tip `7629d9f7`. Not pushed.
- The sixteen, oldest first:

| # | sha | subject |
|---|---|---|
| 1 | 991502ec | rename scheduler members and expansion methods |
| 2 | a005b90d | rename ScheduleContext to PlanContext and its fields |
| 3 | 891dc19f | remove narration logging and condense comments |
| 4 | 828f4bfb | rename misleading methods and locals |
| 5 | 98bbc0fe | delete dead code and simplify |
| 6 | b1a85516 | give booleans an is_ prefix |
| 7 | 04c5ca33 | include the message headers each file uses |
| 8 | 5fc0e120 | planner_core: rename and trim the event DAG and schedule event APIs |
| 9 | bfc23e67 | extract repeated event-building patterns and named blocks |
| 10 | ebb9de58 | fix(scheduler): fix bugs found during the refactor |
| 11 | aa651a6f | split scheduler.cpp into one file per pipeline stage |
| 12 | 1a76c027 | name the heading helpers after their purpose |
| 13 | 04de7078 | remove the Eccles EV-charging heading exception |
| 14 | f9a55640 | delete the unused reverse-heading mode of ExpandAgvMoveJob |
| 15 | 886bbd6f | report action graph failures with specific errors |
| 16 | 7629d9f7 | validate the repark destination after its heading is final |

## Target: six commits, adjacent groups only

Groups are runs of adjacent commits, so the squash is pure and conflict-free; nothing is reordered.
The fix commit stays fourth: moving it after the split would mean re-applying its changes to the
stage files by hand.

| new | old | one-line summary |
|---|---|---|
| A | 1-6 | rename, trim and simplify the scheduler |
| B | 7-8 | trim the planner_core event API; message headers per file |
| C | 9 | extract repeated patterns; std::format error texts |
| D | 10 | the bug fixes |
| E | 11-12 | split by pipeline stage; scheduler-local heading helpers |
| F | 13-16 | Eccles removal, dead paths, specific action-graph failures, repark heading order |

If five are wanted instead, merge E into F ("split by stage and the review follow-ups"); do not
merge anything into D.

## Messages

Create `log/squashmsg/A.txt` ... `F.txt` with exactly the texts below (the `log/` folder is
gitignored and visible inside the container). Lines are at most 100 characters; summaries are
lower-case after the type; conventional-commit types from `.commitlintrc.yaml`.

### A.txt

```
refactor(scheduler): rename, trim and simplify the scheduler before the tray solver

Renames so that each name states what it holds or does: Scheduler members (gg_ to
motion_graph_, table_ to collision_table_, PrintDags() to ToggleDagPrinting()),
the Plan<Type>Job methods to Expand<Type>Job, ScheduleContext to PlanContext in
its own header with renamed fields and methods, methods named verb first
(AssignTrays, AssignAgvs, BuildActionGraph, Compute*Duration and others), locals
spelled out, every bool with an is_ prefix. Callers in the ROS node, the tests
and the plan viewer follow.

Narration logging is removed: the INFO and DEBUG statements for every planning
step and the WARNs for each failed fallback attempt, with the loops and locals
that only fed them; every ERROR stays. Comments are reduced to the reason, or to
the contract a signature does not show; commented-out code and stale TODOs are
deleted.

Dead code is deleted. BoolStringPair leaves the package: expansions return
stdx::Expected<void, JobFailure>, helpers and stages stdx::Result, all
[[nodiscard]]; Plan() handles every job's failure in one place through
ExpandJob; the assignment helpers take their shared state as structs and no
method takes more than five parameters.

No behaviour change; error strings are unchanged; every recorded scenario is
identical.
```

### B.txt

```
refactor(planner): trim the event DAG API and include message headers per file

planner_core: DagBase becomes Dag; GetNode and GetEvent (were GetFromVertex and
GetEventFromVertex) throw for a missing vertex; Reduce becomes
RemoveRedundantEdges; ScheduleEventDag::ApplyEventsTo(state) returns
stdx::Result and ScheduleEvent::ApplyTo(state) replaces Apply; unused API is
deleted, with one test of it. motion_planner follows the ApplyTo rename.

scheduler: scheduler_msgs.hpp is deleted; every *Msg and *Srv alias becomes the
fully qualified interfaces type and each file includes the message headers it
names. agvhito_tools' move planner adjusts one include. No behaviour change.
```

### C.txt

```
refactor(scheduler): extract repeated event-building patterns and format error texts

Repeated sequences become one helper each (PlanContext::AddChainedEvent,
ChainTrayEvent, ChainAgvEvent, OrderAfterFreeingMoves, the bay-command, VECS,
AGV-pose and tray-move builders, BuildImmobileTrayFilter and others); long
functions hand named blocks to their own methods (AssignAgvs,
ExpandRetrieveJob, ExpandAgvChargeJob, ExpandReparkTrayJob,
AppendAgvMoveToTrayEvent). Error texts are built with std::format through Fail
and a std::formatter for the pose, GUID and entity-id messages; the bay-command
placeholder ids and the path-repair pass cap are named constants.

Events, dependencies, their order and every string are unchanged.
```

### D.txt

```
fix(scheduler): fix bugs found during the refactor

- Plan(): a job that fails expanding is reported once; a job that fails partway
  through its expansion leaves no events behind (the plan context is restored),
  so its events no longer take the next job's identity.
- AssignTrays: the advance move's path is the pose before the advance and the
  next pose; the advance is applied once; a planned move (PlannedTrayMove)
  carries its path and, when already applied, the pose it started from; an
  unblocking move that cannot apply fails the tray assignment.
- AssignTrays: a destination usable only through its reverse heading goes to the
  reverse pose instead of throwing (unreachable today: every heading's vertex is
  created with its reverse).
- ExpandReparkTrayJob no longer reads an empty optional when reparking any empty
  tray; the stop-charging event before a tray leaves a charger is chained after
  the charger's previous event.
- ComputeAgvMoveDuration and ComputeStateBefore fail instead of returning zero
  time or a partial state; their callers propagate the failure.
- SetBayReadinessRatioCallback rejects non-finite values.
- The motion order used to build the schedule breaks ties by the motion's own
  fields after the hash, so a hash collision cannot make distinct motions equal.
- A missing space in "TrayMove with TrayId=<id> does not exist", and a label for
  VRC transitions in the DAG printout.

Tests: RetrieveJob.FailedJobReportedOnce, RetrieveJob.FailedJobLeavesNoEvents,
SchedulerState.RejectsNonFiniteBayReadinessRatio. The recorded scenarios are
unchanged (SCHEDULER_CHECK_RECORDINGS=1).
```

### E.txt

```
refactor(scheduler): split scheduler.cpp by pipeline stage and name the heading helpers

scheduler.cpp (3251 lines) becomes one file per stage of Plan(): job_expansion,
tray_assignment, agv_assignment, validation and action_graph; scheduler.cpp keeps
the constructor, Plan(), ExpandJob(), PlanMotions() and the layout queries
several stages use. Helpers two stages share move to utils; JobFailure and Fail
to the new job_failure.hpp. No function body changes.

ReverseHeading, ReversePoseHeading and IsSameOrOppositeHeading in the
scheduler's utils replace the calls to common's ReciprocalAngle,
ReciprocalGaragePose and IsAngleOrReciprocal, which other packages keep using.
The recorded scenarios are unchanged.
```

### F.txt

```
refactor(scheduler): remove the Eccles exception, dead paths and generic failures

ApplyEvChargeHeading, which forced heading 0 on two nodes of any layout named
576_eccles (a decommissioned site), is deleted with its call sites and the four
scheduler_advanced_tests scenarios that ran on Eccles layouts; the
ApplyPreferredHeading wrapper that remained is deleted as well. ExpandAgvMoveJob
loses its reverse-heading parameter and the branch that no caller reached.

ToActionNode returns stdx::Expected<ActionNode> with one message per failure
instead of a null pointer for five reasons, and the three action-graph helpers
return stdx::Result; BuildActionGraph logs and propagates each failure in one
place. ExpandReparkTrayJob applies the retrieval-heading preference before the
destination is validated.

The recorded scenarios are unchanged; the Eccles removal changes behaviour only
on decommissioned layouts.
```

## Tone of the messages

The six texts above are final; copy them unchanged. If a message has to be adjusted (a subject
the script did not match, a line over 100 characters), keep the register: objective statements
of what changed and why it is safe, no first person, no colloquialisms, no judgement on earlier
authors, no Jira keys in commit messages.

## Backup before anything else

1. Confirm the start: `git status` clean, `git log --format='%h %s' 5d5d7b39..HEAD` shows the
   sixteen above with `7629d9f7` first, `git branch --show-current` prints the branch.
2. Create the safety branch on the host and verify it:
   `git branch jmg/SW2-1135/backup-7629d9f7 7629d9f7`, then
   `git rev-parse jmg/SW2-1135/backup-7629d9f7` must print the full sha of `7629d9f7`.
   Do not start the rebase until it does.
3. Reverting, if anything goes wrong at any later step: with no rebase in progress
   (`ls .git/rebase-merge` fails), `git switch -C jmg/SW2-1135/scheduler-renames-and-cleanups
   jmg/SW2-1135/backup-7629d9f7` restores the branch exactly; with a rebase in progress, first
   `volley-in-container git rebase --abort`, which already returns the branch to `7629d9f7`.
   Report what happened; do not retry blindly.

## Mechanics
2. Write the todo `log/squash-todo.txt` (long shas not needed; eight characters suffice):

```
pick 991502ec
squash a005b90d
squash 891dc19f
squash 828f4bfb
squash 98bbc0fe
squash b1a85516
pick 04c5ca33
squash 5fc0e120
pick bfc23e67
pick ebb9de58
pick aa651a6f
squash 1a76c027
pick 04de7078
squash f9a55640
squash 886bbd6f
squash 7629d9f7
```

   C and D are single picks; their messages are replaced in step 3 by a `reword` instead:
   change those two lines to `reword bfc23e67` and `reword ebb9de58`.
3. Write the editor `log/squash-msg.sh`. Git opens it once per squash group (with the
   concatenated messages) and once per reword; it replaces the file by the group's message,
   chosen from the first subject line in the file. Every subject it can meet must be listed:

```bash
#!/bin/bash
f=$1
subject=$(grep -m1 -v '^#' "$f")
case "$subject" in
  *"rename scheduler members"*) n=A;;
  *"include the message headers"*) n=B;;
  *"extract repeated event-building"*) n=C;;
  *"fix bugs found"*) n=D;;
  *"split scheduler.cpp"*) n=E;;
  *"remove the Eccles"*) n=F;;
  *"split scheduler.cpp by pipeline stage"*) n=E;;
  *"remove the Eccles exception, dead paths"*) n=F;;
  *) echo "squash-msg.sh: unknown subject: $subject" >&2; exit 1;;
esac
cp "/home/jon-gonzales/volley/log/squashmsg/$n.txt" "$f"
```

   Test it on a scratch file before the rebase: copy one of the old messages into
   `/tmp/x`, run `bash log/squash-msg.sh /tmp/x`, and check that `/tmp/x` now holds the group
   text. An unknown subject makes git stop mid-rebase with the old message in place.
4. Run the rebase inside the container, non-interactively:

```bash
VOLLEY_IN_CONTAINER_PRELUDE='export GIT_SEQUENCE_EDITOR="cp /home/jon-gonzales/volley/log/squash-todo.txt"; export GIT_EDITOR="bash /home/jon-gonzales/volley/log/squash-msg.sh"' volley-in-container git rebase -i 5d5d7b39
```

   The wrapper prints a summary and the log path. Adjacent squashes cannot conflict. The
   pre-commit hooks run on each new commit and must pass; they did on every old commit with the
   same trees, so a failure means the editor script or the todo is wrong, not the code.
5. If the rebase stops anyway: read the summary and the log, do not `--abort` reflexively. A stop
   with "there was a problem with the editor" means a subject the script does not know: fix the
   script, then `volley-in-container git commit --amend -F log/squashmsg/<n>.txt` and
   `VOLLEY_IN_CONTAINER_PRELUDE='export GIT_EDITOR="bash /home/jon-gonzales/volley/log/squash-msg.sh"' volley-in-container git rebase --continue`.
   Anything else: stop and report; the backup branch holds the old tip.
6. Inline shell commands run under zsh on the host: unquoted variables are not word-split, so
   `git add $files` passes one argument. Put loops in a bash script file or list the files.

## Verification (all must hold)

- `git diff 7629d9f7 HEAD` prints nothing: the tree is identical.
- `git log --format='%h %s' 5d5d7b39..HEAD` shows six commits with the subjects above; each
  body equals its file (`git log -1 --format=%B <sha>` against `log/squashmsg/<n>.txt`, ignoring
  blank lines); no line longer than 100 characters:
  `git log --format=%B 5d5d7b39..HEAD | awk 'length > 100'` prints nothing.
- `git status` clean; `git branch --show-current` unchanged.
- Build and tests, through the wrapper: `volley-in-container build scheduler
  scheduler_advanced_tests agvhito_tools` (0 warnings), `SCHEDULER_CHECK_RECORDINGS=1
  volley-in-container test scheduler` (189 tests, then `git status` clean under
  `test/scenarios/`), `volley-in-container test planner_core scheduler_advanced_tests` (22 and
  12), `volley-in-container tidy` (0 findings). These cannot change, since the tree did not; run
  them anyway and record the result.

## Clean-up, only after every verification above has passed

The branch's history was rewritten several times today and each rewrite left a local backup
branch. None of them was ever pushed (`git branch -r | grep SW2-1135` prints nothing). Once the
six-commit branch is verified, delete all of them on the host, including the one made in step 2:

```bash
git branch -D jmg/SW2-1135/backup-ec2785b3 jmg/SW2-1135/backup-6d965062 jmg/SW2-1135/backup-04fe81d7 jmg/SW2-1135/backup-270fcb24 jmg/SW2-1135/backup-43f88f6f jmg/SW2-1135/backup-5c764d8c jmg/SW2-1135/backup-7629d9f7
```

Then `git branch --list 'jmg/SW2-1135/*'` must print only
`jmg/SW2-1135/scheduler-renames-and-cleanups`. Delete nothing if any verification failed: the
backups are the way back.

## Afterwards

- Notes (outside the repo, never committed), all under
  `/home/jon-gonzales/repos/volley_notes/tickets/SW2-482_scheduler_core_refactor/`:
  append a section "Squashed to six commits" to `SW2-1135_scheduler_renames/code_notes.md` with
  the six new shas and the old-to-new table above; add a review-log item to `SW2-482_notes.md`
  (the next number after the last `2xx.` entry) and update its Status bullet; rewrite the
  `# What` of `SW2-1135_scheduler_renames/pr_description.md` as six subsections, one per commit,
  keeping the "Behaviour and expectation changes" and "Testing" sections; update the commit list
  and tip in `codex_reviews/codex_review_prompt.md` and the "Sixteen commits" wording in `jira_ticket.md`.
- Tell the user the six shas and that the tree is unchanged. The user force-pushes with lease
  and re-pastes the Jira fields; neither is this session's job.
