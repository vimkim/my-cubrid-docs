#!/usr/bin/env bash
# runattempt.sh NAME WORKTREE PRESET: preflight against the attempt's copied install, run native sql, verify.
set -uo pipefail
NAME=${1:?}; WT=${2:?}; PRESET=${3:?}
A=$HOME/tk/$NAME
TF=/home/vimkim/.claude/skills/cubrid-common/scripts/testkit-focused.py
cd "$WT"
for v in ${!CUBRID@}; do unset "$v"; done
export PRESET_MODE="$PRESET"
eval "$(cub-workenv env --worktree "$WT" --preset "$PRESET" --install "${PREFLIGHT_INSTALL:?}")" 2>"$A/workenv.err"
ulimit -c unlimited

python3 "$TF" preflight --suite sql > "$A/preflight.log" 2>&1
echo "preflight_exit=$?" >> "$A/preflight.log"
TESTKIT=$(sed -n 's/^testkit=//p' "$A/preflight.log" | head -1)
ENV_UNSET=$(sed -n 's/^env_unset=//p' "$A/preflight.log" | head -1)
: "${TESTKIT:=$(command -v testkit)}"
env ${ENV_UNSET:+$(printf -- '-u %s ' $ENV_UNSET)} -u CUBRID_CONF_FILE -u CUBRID_BROKER_CONF_FILE -u CUBRID_CUBRID_PORT_ID \
  CCACHE_DISABLE=1 HOME="$A/home" CUBRID="$A/cubrid" CUBRID_DATABASES="$A/cubrid/databases" CUBRID_TMP="$A/cubrid/tmp" \
  CTP_HOME="$A/CTP" PATH="$A/CTP/bin:$A/CTP/common/script:$A/cubrid/bin:$PATH" \
  LD_LIBRARY_PATH="$A/cubrid/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}" \
  TESTKIT_NATIVE=sql TESTKIT_CONTAIN=1 "$TESTKIT" sql -c "$A/conf/sql.conf" < /dev/null > "$A/run.log" 2>&1
RC=$?
echo "$RC" > "$A/exit.status"
RD=$(sed -n 's/^Result Root Dir://p' "$A/run.log" | tail -1)
python3 "$TF" verify --suite sql --result-dir "$RD" --expected-list "$A/expected-cases.txt" --run-log "$A/run.log" --runner-exit "$RC" > "$A/verify.log" 2>&1
echo "verify_exit=$?" >> "$A/verify.log"
grep -c 'LOG FATAL' "$A/run.log" > "$A/fatal.count" || true
