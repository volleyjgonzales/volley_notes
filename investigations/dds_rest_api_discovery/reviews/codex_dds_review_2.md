# Second independent DDS review — 2026-11-05

## 1. Conclusions

**Inferred—high confidence:** Persistent discovery/readiness failure is established; “missing DATA(p), nothing blocked, any join heals” is not. Keep the watchdog as an experimental mitigation; hold the settle gate pending controlled testing.

**Verified:** Diag2 records both services at `0/0` for 777 seconds, then `1/1`, PID 68 unchanged (`logs/central_diag_diag2_recovery.txt`:2–6). Diag15 records one bay node, three publishers and one publisher-derived prefix, then eight nodes, 31 publishers and two prefixes at 04:02:40.891Z (D:231,344,2139–2142).

**Inferred—high:** This demonstrates missing information in the REST process's ROS graph, not absence of the remote PDP participant proxy. The diagnostic derives “participants” from namespace-filtered publishers; it never inspects Fast DDS's participant database (I:116–137). Missing EDP, ROS graph association/processing failure, or reliability state can produce this view even with DATA(p) installed. “Component participant completely known” is also unsupported.

**Verified:** Fast DDS verbosity reads back 1, and **two warnings exist**: machine-ID fallback and SHM buffer invalidation (D:127,130,223). The timer keeps completing in milliseconds (D:2128–2142). **Inferred—high:** Say “no EDP rejection warning; diagnostic callback remained responsive.” Neither proves all middleware threads were unblocked or every processing path succeeded.

**Verified:** The unrelated probe began at 04:02:38Z; both services became ready at 04:02:40.888Z (A:24–26; D:2139–2140). It held a default rclpy node for 20 seconds (`scripts/probe_unrelated.py`:4–14). **Inferred—high:** One no-client intervention supports “same-service clients were unnecessary in this trial,” not “any participant always repairs it.” The earlier recovery windows overlap pre-probe time (summary:51–54); five observations are not five controlled ≤2-second recoveries. The latest timing is approximately three seconds from the second-resolution command timestamp; participant creation itself was not timestamped.

## 2. Rate change

**Verified:** Comparable raw subsets are 1/2 stuck on `29712d9`, 0/10 on `4b00571` with captures, and 1/3 without captures (A:1–26; running log items 362–364). The later 27 healthy watchdog starts are reported in PR texts:78–82; their per-attempt raw records are absent from this supplied `dds_attempts.log`. **Inferred—high:** “7/10 versus 1/~40” pools different builds, interventions and observation methods; it is not an estimated treatment effect.

**Inferred—medium:** Graph-cache locking, CPU scheduling, logging, capture CPU/I/O, container creation, removal of client churn, cached startup resources and changed restart spacing could alter timing. Diag15 proves graph queries do not eliminate the failure. Capture suppression remains speculative.

**Inferred—high:** Cheapest separating experiment: one randomized, interleaved 2×2 trial—extra bay graph scan on/off × captures on/off—using one image with a runtime scan toggle, identical minimal heartbeat/readiness logging, fixed restart spacing, and watchdog disabled. Record actual participant creation times and capture start success. Predeclare attempt counts; compare cells rather than stopping on the first failure. This separates both factors and their interaction without confounding build changes.

## 3. Patch A: watchdog

**Verified:** W:84–106 resets state on stale liveness or readiness, pokes after 60 seconds, then exits after another 30; polling is 10 seconds. **Inferred—high:** Reasonable provisional thresholds, not measured guarantees. With continuous liveness and prompt callbacks, detection adds up to one polling interval; executor stalls or recurring stale reports remove any downtime bound.

**Verified:** Liveness independently accepts receipt age ≤10 seconds and reported staleness ≤10 (REST:453–461). Staleness is computed from the bay report timestamp (`garage_tracker.cpp`:1011–1014). **Inferred—high:** Effective age can approach 20 seconds plus delivery delay; clock skew also matters. A briefly restarting bay may retain “live” status, while a prolonged reporting gap resets the timer. Use aggregate age where clocks permit, reject invalid ages, and test restart transitions. Fresh reports do not establish that confirm services ought already to exist.

**Verified:** There is no persistent restart budget; launch receives `respawn=True`, delay 5 (`central_nodes.py`:31–32). Lyrical launch retries completed processes without testing exit code, including clean exits outside shutdown ([source:553–581](https://github.com/ros2/launch/blob/lyrical/launch/launch/actions/execute_local.py#L553)). **Inferred—high:** A continuously reporting bay with permanently absent/incompatible services can repeatedly kill the entire API; unrelated startup failures can loop every five seconds. Add supervisor-level backoff/budget and an actionable alert, or restrict automatic respawn to the watchdog exit code.

**Verified:** The poke uses an explicit context, five-second sleep, and no spin (W:32–48). Lyrical rclpy defaults nondefault contexts to no signal handlers and shuts down the supplied context ([source:71–91,146–168](https://github.com/ros2/rclpy/blob/lyrical/rclpy/rclpy/__init__.py#L71)). **Inferred—medium:** No obvious default-context shutdown bug, but this shares process/library state and transport environment; it is not equivalent to the external 20-second spinning probe. Five seconds is unvalidated.

**Verified:** Multiple failing bays can launch multiple poke threads; node creation precedes the cleanup `try`, and the restart clock starts before thread creation completes (W:34–41,87–105). **Inferred—high:** Coalesce pokes, guarantee context cleanup on partial failure, and log creation success/failure and GUID. Do not interpret dispatch time as a successful join.

**Verified:** Hard exit bypasses application cleanup (W:51–56); the real-rclpy test merely invokes one context and does not create a concurrent main context (`test_bay_client_watchdog.py`:99–103). **Inferred—high:** Before shipping, test two simultaneous contexts with continuing main callbacks, failed poke creation, stale-to-live transitions, multiple bays, and fallback restart. Validate a real stuck-instance recovery. For hard exit, bound request draining and document ambiguous in-flight command outcomes; automatic client retries need idempotency. Healthy starts validate neither healing nor fallback.

## 4. Patch B: settle gate

**Verified:** The entrypoint probes, sleeps ten seconds, then probes again; stack changes only supply the variable (volley `296cfb40`, `docker/resources/entrypoint.sh`:12–22; swarm-deploy `ec14784`). **Inferred—high:** Two successes do not prove continuous readiness or the same server instance. Equal sleeps can preserve the startup burst; the extra probe is itself a potential healing intervention. Test first, with delay-only and extra-probe effects distinguished.

**Inferred—high:** A healthcheck helps only with an explicit client/deployment wait and meaningful DDS readiness. A separate server stack plus persistent overlay and explicit readiness sequencing better tests a warm-server hypothesis, but changes lifecycle complexity. DNSRR changes VIP routing to task addresses ([Docker](https://docs.docker.com/engine/swarm/networking/#configure-service-discovery)); it supplies no ordering and should follow evidence of address/routing failure, not replace this gate blindly.

## 5. Upstream report

**Inferred—high:** File an observational report now, without claiming root cause. Include exact binaries/profiles, GUIDs, topology, raw positive transitions, intervention timings and stratified denominators. The cheapest decisive next observation is an on-demand snapshot **inside the stuck process**, before probing: remote PDP proxy present? remote EDP proxies present? ROS graph entries and DDS match counters present? That localizes the missing layer without a continuous capture. Reliability sequence/history state on client and server is the next step; merely taking a packet capture after recovery cannot reconstruct startup.

**Verified:** [PR #6542](https://github.com/eProsima/Fast-DDS/pull/6542) describes volatile-reader positioning-GAP desynchronization; discovery proxies here use transient-local durability ([PDPClient:685](https://github.com/eProsima/Fast-DDS/blob/v3.6.2/src/cpp/rtps/builtin/discovery/participant/PDPClient.cpp#L685), [EDPSimple:769](https://github.com/eProsima/Fast-DDS/blob/v3.6.2/src/cpp/rtps/builtin/discovery/endpoint/EDPSimple.cpp#L769)). **Inferred—medium:** Useful lead, not a demonstrated match; identify the affected reader and compare exact patched builds.

## 6. Test/write-up corrections

**Verified:** Offline replay reproduces a parser defect: retained carriage returns prevent `states()`/`ready_at()` matching the last service; A:22 records only insert despite both failures (`scripts/dds_attempt_diag.sh`:52–82). **Inferred—high:** Strip CR at ingestion and require a recovery timestamp for every expected service before taking their maximum.

**Inferred—high:** Treat 180 seconds as an operational threshold, not permanence; require bay-service availability independently of task `1/1`. Ten hands-off minutes strengthen persistence evidence, not “never.” Randomize sham/no-join versus unrelated probes across failures; sequential clients-after-unrelated trials have carryover. Track unsolicited joins and restarts throughout. Keep watchdog-assisted successes separate from naturally healthy starts. Correct the remaining “UDP loss ruled out,” registration-order and server-restart claims as already explained in review 1.

---

Citation key: A = `../results/2026-11-05/logs/dds_attempts.log`; D = its `dds_central_diag15_2026-11-05T03:49:31Z.log`; other logs/scripts share that results directory. W/REST = volley `82df8676`, `src/central_api/central_api/{bay_client_watchdog,rest_api}.py`; I = `4b005718`, same directory's `dds_diagnostics.py`. Other code paths use their named package under `src/`; notes are beside this report. **Verified:** Review was read-only except this report; no garage access or ROS integration tests performed.
