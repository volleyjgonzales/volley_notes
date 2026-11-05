#!/usr/bin/env bash
# Back-to-back attempts until the first one that is not a clean ok: a non-ok result, or an ok whose
# REST API restarted (a second pid on the result line) or the bay client watchdog poked (its line in the saved log).
for n in $(seq "${1:-5}" "${2:-12}"); do
  /home/ops/dds_attempt_diag.sh "diag$n" > "/home/ops/dds_diag_$n.out" 2>&1
  out="/home/ops/dds_diag_$n.out"
  if ! grep -q "result: ok" "$out" || grep -q "rest_api_pids=[0-9]*," "$out" \
      || grep -q "bay-client-watchdog" /home/ops/dds_central_diag"$n"_*.log 2>/dev/null; then echo "stopped after diag$n"; break; fi
  sleep 30
done
