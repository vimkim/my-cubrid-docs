#!/usr/bin/env bash
# one.sh NAME INSTALL WORKTREE FIRST LAST: build ~/tk/NAME, run it with the gdb cas watcher, print the verdict line.
# Env: NO_STACKDUMP, EXTRA_CONF (passed to mkattempt.sh), GDB_PRE (gdb script run before continue).
set -u
NAME=${1:?}; INSTALL=${2:?}; WT=${3:?}; FIRST=${4:?}; LAST=${5:?}
T=$(cd "$(dirname "$0")" && pwd)
"$T/mkattempt.sh" "$NAME" "$INSTALL" "$FIRST" "$LAST" > /dev/null 2>&1 || { echo "$NAME mkattempt failed"; exit 1; }
"$T/caswatch.sh" "$HOME/tk/$NAME/gdbwatch" "/tk/$NAME/" < /dev/null > /dev/null 2>&1 &
WP=$!
PREFLIGHT_INSTALL=$INSTALL "$T/runattempt.sh" "$NAME" "$WT" debug_gcc
sleep 3; kill "$WP" 2>/dev/null
ok=$(grep -c '\[OK\]' "$HOME/tk/$NAME/run.log"); nok=$(grep -c 'NOK' "$HOME/tk/$NAME/run.log")
seg=$(grep -l 'SIGSEGV' "$HOME/tk/$NAME"/gdbwatch/gdb.*.log 2>/dev/null | wc -l)
pt=$(grep -h -c 'PING_TIMEOUT' "$HOME/tk/$NAME"/gdbwatch/gdb.*.log 2>/dev/null | paste -sd+ | bc)
p186=$(grep -h -c 'ERROR CODE = -186' "$HOME/tk/$NAME"/srvlog/broker/error_log/*.err 2>/dev/null | paste -sd+ | bc)
echo "$NAME ok=$ok nok=$nok cas_sigsegv=$seg ping_timeout_bp=${pt:-0} cas_err186=${p186:-0} stackdump=$([ -n "${NO_STACKDUMP:-}" ] && echo no || echo yes) extra=${EXTRA_CONF:-}"
