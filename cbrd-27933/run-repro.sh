#!/usr/bin/env bash
# CBRD-27933 repro runner. Runs what CTest test_oos_real_vacuum_latch_timeout runs, in the worktree's
# selected preset: for each OosRealVacuumHeaderHeld case, a fresh unittestdb fixture, test_oos_real_vacuum_server
# with CUBRID_PAGE_LATCH_TIMEOUT_IN_MSECS=2000, then the fixture cleanup. Each case gets its own process because
# the binary breaks on the first failure. The fixture database lives in a scratch registry, so the run needs no
# initialized host workenv.
#
# usage: run-repro.sh <label> [case ...]     (from the CUBRID worktree root)
# output: $OUT/<label>/{test.log,<case>.server.err,summary.txt}
set -euo pipefail

label=${1:?label}
shift
cases=("$@")
if [ ${#cases[@]} -eq 0 ]; then
  cases=(HomeRowOosReclaimedAfterHeaderLookupFailure RelocatedRowOosReclaimedAfterHeaderLookupFailure
         ShutdownDuringHeaderLookupFailureLeavesHomeRowToVacuum)
fi
worktree=$(git rev-parse --show-toplevel)
out_root=${OUT:-/mnt/nvme/data-5/tmp/cbrd27933-repro/runs}
out="$out_root/$label"
registry="$out/databases"
mkdir -p "$out" "$registry"

cd "$worktree"
# .envrc unsets inherited CUBRID_* variables, so extra server parameters travel in CBRD27933_EXTRA_ENV.
direnv exec . env CUBRID_DATABASES="$registry" CBRD27933_OUT="$out" CBRD27933_WT="$worktree" \
  CBRD27933_CASES="${cases[*]}" CBRD27933_EXTRA_ENV="${EXTRA_ENV:-CUBRID_ER_LOG_VACUUM=4099}" bash -c '
  set -u
  run ()
  {
    export PATH="$CUBRID/bin:$PATH" LD_LIBRARY_PATH="$CUBRID/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
    if [ "${CUBRID_RUNTIME_READY:-0}" != 1 ]; then
      # A preset other than the initialized one: borrow TMP, port and JDK of this worktree for the in-process server.
      eval "$(grep -E "^export (CUBRID_TMP|CUBRID_CUBRID_PORT_ID|CUBRID_JAVA_HOME)=" "$CBRD27933_WT/.cub-workenv/env.sh")"
      export JAVA_HOME="$CUBRID_JAVA_HOME"
      echo "borrowed runtime: CUBRID_TMP=$CUBRID_TMP port=$CUBRID_CUBRID_PORT_ID JAVA_HOME=$JAVA_HOME"
    fi
    scripts="$CBRD27933_WT/unit_tests/oos/scripts"
    worst=0
    for c in $CBRD27933_CASES; do
      echo "=== case $c"
      bash "$scripts/setup_unittestdb.sh" || { echo "fixture setup failed"; return 1; }
      rc=0
      (cd "$CUBRID_BUILD_DIR/unit_tests/oos" \
        && env CUBRID_PAGE_LATCH_TIMEOUT_IN_MSECS=2000 $CBRD27933_EXTRA_ENV timeout 900 "$CUBRID_BUILD_DIR/bin/test_oos_real_vacuum_server" \
             "--gtest_filter=OosRealVacuumHeaderHeld.$c") || rc=$?
      # The server log is per minute and can hold the previous case too: keep this boot only.
      err="$CUBRID/log/server/unittestdb_latest.err"
      up=$(grep -n "Server status is UP" "$err" 2>/dev/null | tail -1 | cut -d: -f1)
      [ -n "$up" ] && tail -n "+$((up - 1))" "$err" > "$CBRD27933_OUT/$c.server.err"
      bash "$scripts/cleanup_unittestdb.sh" || echo "fixture cleanup failed"
      echo "test binary exit=$rc ($c)"
      [ "$rc" -ne 0 ] && worst=$rc
    done
    return "$worst"
  }
  export -f run
  "${MY_CUBRID:-$HOME/my-cubrid}/bin/cubrid-build-coordinator.sh" installation-use 300 -- bash -c run
' > "$out/test.log" 2>&1 </dev/null && rc=0 || rc=$?

{
  printf 'label=%s rc=%s extra_env=%s\n' "$label" "$rc" "${EXTRA_ENV:-CUBRID_ER_LOG_VACUUM=4099}"
  printf 'source HEAD=%s, dirty paths: %s\n' "$(git rev-parse --short HEAD)" \
    "$(git status --porcelain | awk '{print $2}' | tr '\n' ' ')"
  direnv exec . bash -c 'printf "preset=%s install=%s\nlibcubrid sha256 install=%s build=%s\n" "$PRESET_MODE" "$CUBRID" \
    "$(sha256sum "$CUBRID/lib/libcubrid.so.11.5" | cut -c1-12)" \
    "$(sha256sum "$CUBRID_BUILD_DIR/cubrid/libcubrid.so.11.5" | cut -c1-12)"' 2>/dev/null
  git diff --stat -- src | tail -1 | sed 's/^/engine diff: /'
  grep -E 'borrowed runtime|\[CBRD-27933\]|Assertion|Failure$|must|never |\[  (PASSED|FAILED|SKIPPED) |\[       OK|test binary exit' \
    "$out/test.log" | awk '!seen[$0]++'
  for c in "${cases[@]}"; do
    f="$out/$c.server.err"
    [ -f "$f" ] || continue
    printf '%s server.err: LATCH TIMEDOUT=%s, OOS-flag-without-VFID=%s, could-not-prepare=%s, block interrupted=%s\n' \
      "$c" "$(grep -c 'TIMEDOUT' "$f" || true)" "$(grep -c 'OOS flag set but no OOS VFID' "$f" || true)" \
      "$(grep -c 'Could not prepare vacuum' "$f" || true)" "$(grep -c 'is interrupted' "$f" || true)"
    block=$(awk -v c="=== case $c" '$0==c{on=1;next} /^=== case/{on=0} on && /delete log block/{print; exit}' \
      "$out/test.log" | sed -E 's/.*delete log block ([0-9]+).*/\1/')
    if [ -n "$block" ]; then
      printf '%s delete block %s verdicts: %s\n' "$c" "$block" \
        "$(grep -oE "Processing log block $block is [a-z]+" "$f" | sed 's/.* is //' | tr '\n' ' ')"
    fi
  done
} | tee "$out/summary.txt"
exit "$rc"
