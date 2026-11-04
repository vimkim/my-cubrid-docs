#!/usr/bin/env bash
# CBRD-27933: run the REC_HOME repro case under gdb on a debug build and print the aborting thread stack.
# Run from the CUBRID worktree root: direnv exec . bash <this file>
set -u
B="$CUBRID_BUILD_DIR"
cd "$B/unit_tests/oos" || exit 1
ctest --test-dir "$B" -R '^oos_setup_db$' >/dev/null 2>&1 || { echo "fixture setup failed"; exit 1; }
CUBRID_PAGE_LATCH_TIMEOUT_IN_MSECS=2000 timeout 300 gdb -q -batch \
  -ex 'set pagination off' -ex 'handle SIGUSR1 SIGUSR2 SIGPIPE nostop noprint' \
  -ex run -ex 'info thread' -ex bt \
  --args "$B/bin/test_oos_real_vacuum_server" '--gtest_filter=OosRealVacuumHeaderHeld.HomeRowOosReclaimedAfterHeaderLookupFailure' 2>&1
rc=$?
ctest --test-dir "$B" -R '^oos_cleanup_db$' >/dev/null 2>&1
exit $rc
