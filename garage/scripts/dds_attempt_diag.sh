#!/usr/bin/env bash
# One full-restart attempt for the diagnostic build (branch jmg/test/dds-rest-api-diagnostics): recreate
# app-comb, then judge the REST API from its [dds-diag] heartbeat. STUCK = a deployed bay's confirm service
# still not ready 180 s after the deploy. On STUCK: 10 min hands-off, then one fresh participant in control.
set -u
label="${1:-baseline}"
# SWARM_ROOT=<dir> deploys from a copy of /data/swarm (for experiments that edit stack files without root).
swarm_root="${SWARM_ROOT:-/data/swarm}"
swarmctl=(/data/swarm/bin/swarmctl --root "$swarm_root")
hands_off=600
after_probe=120
# On STUCK, the probes to try in order until one is followed by a recovery: "unrelated" (one rclpy node, no
# clients) and/or "clients" (one rclpy node with bay 7 and central clients).
probe_order="${PROBE_ORDER:-unrelated,clients}"
# Packet captures (nicolaka/netshoot's tcpdump, no DDS participant): the host's eth0 for the VXLAN side (bay 7
# <-> this host) from before the removal, and central's own network namespace from the moment it exists. Each is
# capped at 4 x 500 MB (tcpdump -C/-W rotation, so the file names get a 0-3 suffix).
captures=/home/ops/captures
cap_image=nicolaka/netshoot:v0.16
# CAPTURE=0 runs without either capture (to test whether the captures themselves change the outcome).
capture="${CAPTURE:-1}"
say() { echo "[$(date -u +%T)] $*"; }
log() { echo "$*" | tee -a ~/dds_attempts.log; }
udp_drops() { docker exec "$1" awk '/^Udp:/{n++; if (n==2) {print $6; exit}}' /proc/net/snmp 2>/dev/null; }
# The REST API's own Fast DDS sockets (not the ones inherited from ros2 launch): port:rb<buffer>/d<drops>.
rest_api_sockets() {
  docker exec "$1" ss -uamnp 2>/dev/null | awk '
    /users:\(\("rest_api"/ && !/\),\(/ { n = split($4, a, ":"); port = a[n]; getline
      if (port !~ /^74[0-9][0-9]$/) next
      match($0, /rb[0-9]+/); rb = substr($0, RSTART, RLENGTH)
      match($0, /d[0-9]+\)/); d = substr($0, RSTART, RLENGTH - 1)
      printf "%s:%s/%s ", port, rb, d }'
}
diag() { docker logs --since "$start" "$1" 2>&1 | grep -F '[dds-diag]'; }
# The bays this attempt expects, e.g. "b7": BAY_IDS_OVERRIDE from the root's .env.local, else the bays deployed before
# the removal. The REST API also holds clients for undeployed layout bays, which are never ready.
expected_bays() {
  local ids
  ids=$(sed -n 's/^BAY_IDS_OVERRIDE="\{0,1\}\([0-9 ,]*\)"\{0,1\}$/\1/p' "$swarm_root/.env.local" | tr ', ' '\n\n' | grep .)
  [ -z "$ids" ] && ids=$(docker service ls --filter name=app-comb_bay --format '{{.Name}}' | sed -n 's/.*_bay\([0-9]\+\)$/\1/p')
  echo "$ids" | grep -x '[0-9]\+' | sed 's/^/b/' | sort -u
}
deployed_bays() { echo "$bays"; }
# Expected bays whose service doesn't have its one task running.
bays_not_running() {
  local bay
  for bay in $bays; do
    docker service ls --filter "name=app-comb_bay${bay#b}" --format '{{.Name}} {{.Replicas}}' | grep -q "_bay${bay#b} 1/1" || echo "$bay"
  done | paste -sd,
}
# The latest heartbeat: "<wall> <not-ready services of deployed bays, comma-separated or ->".
heartbeat() {
  local line wall services="" bay svc
  line=$(diag "$1" | grep ' heartbeat ' | tail -n 1)
  [ -z "$line" ] && { echo "0 -"; return; }
  wall=$(echo "$line" | sed -n 's/.*wall=\([0-9]*\).*/\1/p')
  for bay in $(deployed_bays); do
    for svc in $(echo "$line" | sed 's/.*not_ready=//' | tr ',' '\n' | grep "^/bay/$bay/"); do
      services="${services:+$services,}$svc"
    done
  done
  echo "$wall ${services:--}"
}
# The latest state line per service, e.g. "/bay/b7/confirm_insert ready=0 rq_readers=1 rr_writers=1 rq_gids=… rr_gids=…".
states() {
  local svc
  for svc in $(echo "$2" | tr ',' ' '); do
    diag "$1" | grep " change $svc " | tail -n 1 | sed 's/.* change //'
  done | paste -sd';'
}
# When the given services last became ready (wall seconds), or empty. Per service, the first ready=1 after its last
# ready=0: later ready=1 lines are endpoint changes, not readiness.
ready_at() {
  local svc t latest=""
  for svc in $(echo "$2" | tr ',' ' '); do
    t=$(diag "$1" | grep " change $svc ready=" | awk '
      / ready=0 / { t = ""; is_ready = 0; next }
      !is_ready { match($0, /wall=[0-9]+/); t = substr($0, RSTART + 5, RLENGTH - 5); is_ready = 1 }
      END { print t }')
    [ -n "$t" ] && { [ -z "$latest" ] || [ "$t" -gt "$latest" ]; } && latest=$t
  done
  echo "$latest"
}
# Watches until the stuck services are ready or $2 seconds pass. Sets $outcome (recovered, timeout or no_heartbeat)
# and, when recovered, $recovered_at (wall seconds).
watch_recovery() {
  local phase="$1" seconds="$2" begin now hb wall not_ready
  begin=$(date +%s); recovered_at=""; outcome=timeout
  while true; do
    sleep 10
    now=$(date +%s)
    hb=$(heartbeat "$C"); wall=${hb%% *}; not_ready=${hb#* }
    printf '    %s t+%3ds  not ready: %s  heartbeat %ss ago\n' "$phase" "$((now - begin))" "$not_ready" "$((now - wall))"
    if [ $((now - wall)) -gt 15 ]; then say "no heartbeat for $((now - wall)) s (last check: $(last_check "$C"))"; outcome=no_heartbeat; return; fi
    if [ "$not_ready" = "-" ]; then recovered_at=$(ready_at "$C" "$stuck"); outcome=recovered; return; fi
    [ $((now - begin)) -ge "$seconds" ] && return
  done
}
# Where the last check got to: "started n=<n>" (began, never finished: blocked in a graph query) or "finished n=<n>".
last_check() {
  diag "$1" | grep -E ' (check-start|heartbeat) n=' | tail -n 1 |
    sed -n 's/.* check-start n=\([0-9]*\).*/started n=\1/p; s/.* heartbeat n=\([0-9]*\).*/finished n=\1/p'
}
# The REST API's process IDs in this attempt; more than one means it restarted.
rest_api_pids() { diag "$1" | sed -n 's/.* pid=\([0-9]*\) .*/\1/p' | sort -u | paste -sd,; }
# Fast DDS colours its log lines; strip the ANSI escapes before matching, else `[UTILS Warning]` is never seen.
save_warnings() {
  local file=~/dds_warnings_${label}_${start}.txt
  docker logs --since "$start" "$1" 2>&1 | sed 's/\x1b\[[0-9;]*m//g' | grep -E '\[[A-Z0-9_]+ (Warning|Error)\]' > "$file"
  echo "fastdds_warnings=$(wc -l < "$file") unknown_participant=$(grep -c 'UNKNOWN RTPSParticipant' "$file")"
}

start_host_capture() {
  [ "$capture" = 1 ] || { say "captures off (CAPTURE=0)"; return; }
  docker run -d --name "dds-cap-host-$label" --net host --cap-add NET_RAW --cap-add NET_ADMIN \
    -v "$captures:/cap" "$cap_image" tcpdump -i eth0 -s 0 -B 8192 -U -C 500 -W 4 -w "/cap/${label}_host.pcap" udp port 4789 >/dev/null \
    && say "host capture started: $captures/${label}_host.pcap" || say "host capture failed to start"
}
# Shares central's network namespace; starts as soon as the container exists (the entrypoint's discovery probe
# runs for a few seconds first, so the REST API's participant is normally caught from its first packet).
start_central_capture() {
  local i
  [ "$capture" = 1 ] || return 0
  for i in $(seq 1 120); do C=$(docker ps -qf name=_central.); [ -n "$C" ] && break; sleep 0.5; done
  [ -z "$C" ] && { say "central capture: no central container after 60 s"; return; }
  docker run -d --name "dds-cap-central-$label" --net "container:$C" \
    -v "$captures:/cap" "$cap_image" tcpdump -i any -s 0 -B 8192 -U -C 500 -W 4 -w "/cap/${label}_central.pcap" udp >/dev/null \
    && say "central capture started ($(( $(date +%s) - deployed )) s after the deploy): $captures/${label}_central.pcap" \
    || say "central capture failed to start"
}
stop_captures() {
  local name
  for name in "dds-cap-host-$label" "dds-cap-central-$label"; do
    docker ps -aq -f "name=^$name\$" | grep -q . || continue
    docker stop -t 2 "$name" >/dev/null 2>&1; docker rm -f "$name" >/dev/null 2>&1
  done
  ls -la "$captures"/"${label}"_* 2>/dev/null | sed 's/^/    /'
}
save_logs() {
  [ -n "${C:-}" ] && docker logs --since "$start" "$C" > ~/dds_central_${label}_${start}.log 2>&1
  [ -n "${D:-}" ] && docker logs --since "$start" "$D" > ~/dds_discovery_${label}_${start}.log 2>&1
  say "logs saved: ~/dds_central_${label}_${start}.log ~/dds_discovery_${label}_${start}.log"
}
finish() { stop_captures; save_logs; }
# One probe in control: a single rclpy process (source setup.bash, no entrypoint participant).
run_probe() {
  local kind="$1" script
  case "$kind" in unrelated) script=probe_unrelated.py;; clients) script=probe_clients.py;; *) say "unknown probe '$kind'"; return 1;; esac
  K=$(docker ps -qf name=_control.)
  docker exec -i "$K" sh -c "cat > /tmp/$script" < ~/"$script"
  probe_time=$(date +%s)
  say "probe '$kind': one rclpy process in control ($script)"
  log "  probe '$kind' (one rclpy process, no entrypoint probe) in control at $(date -u +%T):"
  docker exec "$K" bash -c "source /opt/volley/setup.bash && exec python3 /tmp/$script" 2>&1 | sed 's/^/    /' | tee -a ~/dds_attempts.log
}

bays=$(expected_bays)
if [ -z "$bays" ]; then echo "no expected bays (BAY_IDS_OVERRIDE or deployed bay services); not starting"; exit 1; fi
mkdir -p "$captures"
C=""; D=""; start=$(date -u +%FT%TZ)
trap finish EXIT
start_host_capture
say "attempt '$label' (root $swarm_root, bays $(echo $bays)): removing app-comb"
"${swarmctl[@]}" remove --yes app 2>&1 | sed 's/^/    /'
say "removed; waiting 20 s"
sleep 20
# Log queries start here, before the deploy, so the earliest startup lines are included.
start=$(date -u +%FT%TZ)
say "deploying app-comb"
"${swarmctl[@]}" deploy app 2>&1 | sed 's/^/    /'
deployed=$(date +%s)
start_central_capture
say "deployed; watching for 180 s (stuck = a deployed bay's confirm service not ready at 180 s)"

while true; do
  elapsed=$(( $(date +%s) - deployed ))
  [ "$elapsed" -ge 180 ] && break
  sleep 10
  elapsed=$(( $(date +%s) - deployed ))
  up=$(docker service ls --filter name=app-comb_ --format '{{.Replicas}}' | grep -c '^1/1')
  total=$(docker service ls --filter name=app-comb_ -q | wc -l)
  C=$(docker ps -qf name=_central.)
  if [ -n "$C" ]; then hb=$(heartbeat "$C"); not_ready=${hb#* }; drops=$(udp_drops "$C"); else not_ready="-"; drops="-"; fi
  printf '    t+%3ds  services %s/%s  not ready: %-50s udp drops central %s\n' "$elapsed" "$up" "$total" "$not_ready" "${drops:--}"
done

C=$(docker ps -qf name=_central.)
D=$(docker ps -qf name=_discovery-server.)
if [ -z "$C" ]; then
  say "result: NO_CENTRAL"
  log "$start label=$label result=NO_CENTRAL (central not running after 180 s)"
  exit 1
fi
build=$(docker exec "$C" printenv GITSHA)
hb=$(heartbeat "$C"); hb_wall=${hb%% *}; stuck=${hb#* }
verbosity=$(diag "$C" | grep -c 'fastdds verbosity=1')
missing=$(bays_not_running)
if [ -n "$missing" ]; then result=BAY_NOT_RUNNING:$missing
elif [ "$hb_wall" = 0 ]; then result=NO_DIAG
elif [ $(( $(date +%s) - hb_wall )) -gt 15 ]; then result=NO_HEARTBEAT
elif [ "$stuck" = "-" ]; then result=ok
else result=STUCK; fi
warnings=$(save_warnings "$C")
sockets=$(rest_api_sockets "$C")
say "result: $result"
log "$start label=$label build=$build result=$result stuck=$stuck states=$(states "$C" "$stuck") warnings_on=$verbosity $warnings last_check=\"$(last_check "$C")\" rest_api_pids=$(rest_api_pids "$C") rcvbuf_errors central=$(udp_drops "$C") discovery=$(udp_drops "$D") rest_api_sockets=${sockets% }"
[ "$result" = STUCK ] || exit 0

say "STUCK: hands off for up to $((hands_off / 60)) min. Run no ros2 commands, probes or Foxglove reconnects meanwhile."
watch_recovery "hands-off" "$hands_off"
case "$outcome" in
  recovered)
    say "recovered by itself"
    log "  self-recovered at $(date -u -d @"$recovered_at" +%T) ($((recovered_at - deployed)) s after the deploy); no probe run; $(save_warnings "$C")"
    exit 0;;
  no_heartbeat)
    log "  NO_HEARTBEAT during hands-off (after $(( $(date +%s) - deployed )) s, last check: $(last_check "$C")); no probe run; $(save_warnings "$C")"
    exit 1;;
esac
log "  still stuck after $((hands_off / 60)) min hands-off: $(states "$C" "$stuck")"

for kind in $(echo "$probe_order" | tr ',' ' '); do
  run_probe "$kind" || continue
  watch_recovery "after-$kind" "$after_probe"
  case "$outcome" in
    recovered) log "  recovered at $(date -u -d @"$recovered_at" +%T), $((recovered_at - probe_time)) s after the '$kind' probe started; $(save_warnings "$C")"; break;;
    no_heartbeat) log "  NO_HEARTBEAT after the '$kind' probe (last check: $(last_check "$C")); $(save_warnings "$C")"; break;;
    *) log "  still stuck $((after_probe / 60)) min after the '$kind' probe: $(states "$C" "$stuck"); $(save_warnings "$C")";;
  esac
done
say "done: leave the stack as it is for the C++ check and the restart test if it's still stuck"
