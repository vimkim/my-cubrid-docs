#!/usr/bin/env bash
# caswatch.sh OUTDIR MATCH: attach gdb to every cub_cas whose CUBRID env contains MATCH; on a fatal signal save the stack.
OUT=${1:?}; MATCH=${2:?}
mkdir -p "$OUT"
declare -A seen
while true; do
  for p in $(pgrep -u "$USER" -f 'cub_cas'); do
    [ -n "${seen[$p]:-}" ] && continue
    e=$(tr '\0' '\n' < /proc/$p/environ 2>/dev/null | grep '^CUBRID=') || continue
    case "$e" in *"$MATCH"*) ;; *) seen[$p]=skip; continue;; esac
    seen[$p]=1
    echo "$(date +%T) attach $p $e" >> "$OUT/watch.log"
    root=${e#CUBRID=}
    gdb "$root/bin/cub_cas" -p "$p" -batch -nx \
      -ex 'set pagination off' -ex 'set sysroot /' -ex "set solib-search-path $root/lib" \
      -ex 'handle SIGUSR1 nostop noprint pass' -ex 'handle SIGUSR2 nostop noprint pass' \
      -ex 'handle SIGPIPE nostop noprint pass' -ex 'handle SIGTERM nostop noprint pass' \
      -ex 'handle SIGINT nostop noprint pass' -ex 'handle SIGCHLD nostop noprint pass' \
      -x "${GDB_PRE:-/dev/null}" -ex continue -x "$(dirname "$0")/atcrash.gdb" -ex 'x/160ga $sp' -ex 'bt' \
      < /dev/null > "$OUT/gdb.$p.log" 2>&1 &
  done
  sleep 0.5
done
