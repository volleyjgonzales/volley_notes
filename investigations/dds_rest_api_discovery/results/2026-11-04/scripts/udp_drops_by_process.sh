#!/bin/sh
# UDP sockets with drops in this network namespace, and the process that owns each one.
for p in /proc/[0-9]*; do
  name=$(tr '\0' ' ' < "$p/cmdline" 2>/dev/null | cut -c1-70)
  for fd in "$p"/fd/*; do
    l=$(readlink "$fd" 2>/dev/null) || continue
    case "$l" in socket:*) i=${l#socket:[}; echo "${i%]} ${p#/proc/} $name";; esac
  done
done > /tmp/sockmap
for f in /proc/net/udp /proc/net/udp6; do
  [ -r "$f" ] && awk 'NR>1 {print $10, $NF, $2, $14}' "$f"
done | while read -r inode drops local rest; do
  [ "$drops" -gt 0 ] 2>/dev/null || continue
  owner=$(grep "^$inode " /tmp/sockmap | head -n 1 | cut -d' ' -f2-)
  echo "$drops $local ${owner:-?}"
done | sort -rn
echo "total RcvbufErrors: $(awk '/^Udp:/{n++; if (n==2) {print $6; exit}}' /proc/net/snmp)"
