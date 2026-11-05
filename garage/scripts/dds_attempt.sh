#!/usr/bin/env bash
# One full-restart attempt: recreate app-comb, watch it come up, record whether rest_api is stuck.
# On STUCK: watch hands-off for 10 min (does it recover by itself?), then start one fresh participant
# in control and watch 2 min more (does a joining participant make it recover?).
set -u
label="${1:-baseline}"
# SWARM_ROOT=<dir> deploys from a copy of /data/swarm (for experiments that edit stack files without root).
swarm_root="${SWARM_ROOT:-/data/swarm}"
swarmctl=(/data/swarm/bin/swarmctl --root "$swarm_root")
hands_off=600
after_probe=120
say() { echo "[$(date -u +%T)] $*"; }
log() { echo "$*" | tee -a ~/dds_attempts.log; }
udp_drops() { docker exec "$1" awk '/^Udp:/{n++; if (n==2) {print $6; exit}}' /proc/net/snmp 2>/dev/null; }
recreates() { docker logs --since "$start" "$1" 2>&1 | grep -c 'recreating its client'; }
# The REST API's own Fast DDS sockets (not the ones inherited from ros2 launch): port:rb<buffer>/d<drops>.
rest_api_sockets() {
  docker exec "$1" ss -uamnp 2>/dev/null | awk '
    /users:\(\("rest_api"/ && !/\),\(/ { n = split($4, a, ":"); port = a[n]; getline
      if (port !~ /^74[0-9][0-9]$/) next
      match($0, /rb[0-9]+/); rb = substr($0, RSTART, RLENGTH)
      match($0, /d[0-9]+\)/); d = substr($0, RSTART, RLENGTH - 1)
      printf "%s:%s/%s ", port, rb, d }'
}

last_line() { docker logs -t --since "$start" "$1" 2>&1 | grep 'recreating its client' | tail -n 1 | awk '{print $1}'; }

# Watches rest_api for $2 seconds. A stuck rest_api logs a recreate line at least every 70 s, so 75 s
# without a new line means it matched, sometime in the 70 s after its last line. Sets $recovered_at to
# that last line's time (Unix seconds), or leaves it empty if it's still stuck at the end.
watch_recovery() {
  local phase="$1" seconds="$2" begin now ts last
  begin=$(date +%s); recovered_at=""
  while true; do
    sleep 10
    now=$(date +%s)
    ts=$(last_line "$C")
    last=$(date -u -d "$ts" +%s 2>/dev/null || echo "$begin")
    printf '    %s t+%3ds  recreates %-3s last line %3ds ago\n' "$phase" "$((now - begin))" "$(recreates "$C")" "$((now - last))"
    if [ $((now - last)) -ge 75 ]; then recovered_at=$last; return; fi
    [ $((now - begin)) -ge "$seconds" ] && return
  done
}

say "attempt '$label' (root $swarm_root): removing app-comb"
"${swarmctl[@]}" remove --yes app 2>&1 | sed 's/^/    /'
say "removed; waiting 20 s"
sleep 20
say "deploying app-comb"
"${swarmctl[@]}" deploy app 2>&1 | sed 's/^/    /'
start=$(date -u +%FT%TZ)
deployed=$(date +%s)
say "deployed; watching for 180 s (stuck = recreate lines between 90 and 180 s)"

while true; do
  elapsed=$(( $(date +%s) - deployed ))
  [ "$elapsed" -ge 180 ] && break
  sleep 10
  elapsed=$(( $(date +%s) - deployed ))
  up=$(docker service ls --filter name=app-comb_ --format '{{.Replicas}}' | grep -c '^1/1')
  total=$(docker service ls --filter name=app-comb_ -q | wc -l)
  C=$(docker ps -qf name=_central.)
  if [ -n "$C" ]; then
    api=$(docker exec "$C" ps -eo etime,args 2>/dev/null | awk '/[r]est_api/{print $1; exit}')
    count=$(recreates "$C")
    drops=$(udp_drops "$C")
  else
    api="-"; count="-"; drops="-"
  fi
  printf '    t+%3ds  services %s/%s  rest_api up %-6s recreates %-3s udp drops central %s\n' \
    "$elapsed" "$up" "$total" "${api:--}" "$count" "${drops:--}"
done

C=$(docker ps -qf name=_central.)
D=$(docker ps -qf name=_discovery-server.)
if [ -z "$C" ]; then
  say "result: NO_CENTRAL"
  log "$start label=$label result=NO_CENTRAL (central not running after 180 s)"
  exit 1
fi
build=$(docker exec "$C" printenv GITSHA)
late=$(docker logs --since 90s "$C" 2>&1 | grep -c 'recreating its client')
drops_c=$(udp_drops "$C")
drops_d=$(udp_drops "$D")
sockets=$(rest_api_sockets "$C")
result=$([ "$late" -gt 0 ] && echo STUCK || echo ok)
say "result: $result"
log "$start label=$label build=$build result=$result late_recreates=$late rcvbuf_errors central=$drops_c discovery=${drops_d:-n/a} rest_api_sockets=${sockets% }"
[ "$result" = STUCK ] || exit 0

say "STUCK: hands off for up to $((hands_off / 60)) min. Run no ros2 commands, probes or Foxglove reconnects meanwhile."
watch_recovery "hands-off" "$hands_off"
if [ -n "$recovered_at" ]; then
  say "recovered by itself"
  log "  self-recovered: matched between $(date -u -d @"$recovered_at" +%T) and $(date -u -d @$((recovered_at + 70)) +%T) ($((recovered_at - deployed))-$((recovered_at + 70 - deployed)) s after the deploy); no probe run"
  exit 0
fi
log "  still stuck after $((hands_off / 60)) min hands-off"

K=$(docker ps -qf name=_control.)
docker exec -i "$K" sh -c 'cat > /tmp/probe_clients.py' < ~/probe_clients.py
probe_time=$(date +%s)
say "one fresh participant: probe in control"
log "  probe in control at $(date -u +%T):"
docker exec "$K" /opt/volley/entrypoint.sh python3 /tmp/probe_clients.py 2>&1 | grep -v discovery_probe | sed 's/^/    /' | tee -a ~/dds_attempts.log
watch_recovery "after-probe" "$after_probe"
if [ -n "$recovered_at" ]; then
  log "  recovered: matched between $(date -u -d @"$recovered_at" +%T) and $(date -u -d @$((recovered_at + 70)) +%T); the probe started at $(date -u -d @"$probe_time" +%T)"
else
  log "  still stuck $((after_probe / 60)) min after the probe"
fi
say "done: leave the stack as it is for the C++ check and the restart test if it's still stuck"
