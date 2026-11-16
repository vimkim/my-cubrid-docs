#!/usr/bin/env bash
# mkattempt.sh NAME INSTALL FIRST LAST [CASE_INDEX...]
# Builds ~/tk/NAME: a disposable copy of INSTALL and CTP, plus the shard 09 cases FIRST..LAST
# (or only the listed indexes) at testcase revision 40cdeddd1d, or the cases under $PROBE_DIR/sql, then prepares the
# native sql config. NO_STACKDUMP=1 leaves call_stack_dump_on_error at its default (no). Broker SQL and error logs go to $A/srvlog/broker. EXTRA_CONF (";"-separated) goes to [sql/cubrid.conf], CREATEDB_OPTS to cubrid_createdb_opts.
set -euo pipefail
NAME=${1:?}; INSTALL=${2:?}; FIRST=${3:?}; LAST=${4:?}; shift 4
HERE=$(cd "$(dirname "$0")/.." && pwd)
ORDER=$HERE/shard09-order.tsv
TC=/home/vimkim/gh/cubrid-testcases/develop
TC_REV=40cdeddd1d142d9af65b104b3bf6ab34e17a3c42
CTP_SRC=/home/vimkim/gh/ctp/run-sql/CTP
JAR=/home/vimkim/.cub/install/build-partition-key-20261112/debug_gcc/jdbc/cubrid-jdbc-11.4.0.0088.jar
TF=/home/vimkim/.claude/skills/cubrid-common/scripts/testkit-focused.py
A=$HOME/tk/$NAME
[ -e "$A" ] && { echo "exists: $A" >&2; exit 1; }
mkdir -p "$A"/{home,conf,group}
cp -a "$INSTALL" "$A/cubrid"
mkdir -p "$A/cubrid/jdbc"
[ -e "$A/cubrid/jdbc/cubrid_jdbc.jar" ] || { cp "$JAR" "$A/cubrid/jdbc/"; ln -s "$(basename "$JAR")" "$A/cubrid/jdbc/cubrid_jdbc.jar"; }
if [ -d "$A/cubrid/databases" ]; then mv "$A/cubrid/databases" "$A/cubrid/databases.copied"; fi
mkdir -p "$A/cubrid/databases" "$A/cubrid/tmp"
cp -a "$CTP_SRC" "$A/CTP"
if [ -n "${PROBE_DIR:-}" ]; then
  cp -a "$PROBE_DIR/sql" "$A/group/sql"
  find "$A/group" -path '*/cases/*.sql' | sed "s#^$A/group/##" | sort > "$A/selected.txt"
elif [ $# -gt 0 ]; then
  for i in "$@"; do awk -F'\t' -v i="$i" '$1==i{print $2}' "$ORDER"; done > "$A/selected.txt"
else
  awk -F'\t' -v f="$FIRST" -v l="$LAST" '$1>=f && $1<=l {print $2}' "$ORDER" > "$A/selected.txt"
fi
sed 's#/cases/[^/]*$##' "$A/selected.txt" | sort -u > "$A/units.txt"
[ -n "${PROBE_DIR:-}" ] || git -C "$TC" archive "$TC_REV" $(cat "$A/units.txt") | tar -x -C "$A/group"
find "$A/group" -path '*/cases/*.sql' | sed "s#^$A/group/##" | sort > "$A/all-cases.txt"
grep -vxF -f "$A/selected.txt" "$A/all-cases.txt" | while read -r c; do rm -f "$A/group/${c:?}"; done || true
echo "$TC_REV" > "$A/tc.head"
cp "$CTP_SRC/conf/sql.conf" "$A/conf/sql.base.conf"
python3 "$TF" prepare-config --suite sql --base-conf "$A/CTP/conf/sql.conf" --output-conf "$A/conf/sql.conf" \
  --scenario "$A/group/sql" --selection "$A/group/sql" --output-expected-list "$A/expected-cases.txt" | tee "$A/prepare.log"
mkdir -p "$A/srvlog"
python3 - "$A/conf/sql.conf" "$A/srvlog" "${EXTRA_CONF:-}" "${CREATEDB_OPTS:-}" <<'PY'
import os, sys
conf, logdir, extra, cdb = sys.argv[1:5]
lines = open(conf).read().split('\n')
i = lines.index('[sql/cubrid.conf]')
add = [f'error_log={logdir}/cubrid.err'] + ([] if os.environ.get('NO_STACKDUMP') else ['call_stack_dump_on_error=yes']) + [x for x in extra.split(';') if x]
lines[i+1:i+1] = add
if cdb:
    j = lines.index('[sql]')
    lines[j+1:j+1] = [f'cubrid_createdb_opts={cdb}']
k = lines.index('[sql/cubrid_broker.conf/%BROKER1]')
lines[k+1:k+1] = [f'LOG_DIR={logdir}/broker/sql_log', f'SLOW_LOG_DIR={logdir}/broker/sql_log', f'ERROR_LOG_DIR={logdir}/broker/error_log']
open(conf, 'w').write('\n'.join(lines))
PY
mkdir -p "$A/srvlog/broker/sql_log" "$A/srvlog/broker/error_log"
grep -n 'error_log\|call_stack\|cubrid_createdb_opts\|LOG_DIR' "$A/conf/sql.conf" | tee -a "$A/prepare.log"
echo "$A"
