#!/usr/bin/env bash
set -euo pipefail
task_db=oos_notype289
task_artifacts=/tmp/pr7927-loader-green
CUBRID_NO_DAEMON=1 "$CUBRID/bin/cub_master" > /tmp/pr7927-loader-owned-master.log 2>&1 &
task_master_pid=$!
finish_loader() {
  task_verdict=$?
  trap - EXIT
  cubrid server stop "$task_db" > /tmp/pr7927-loader-stop-green.log 2>&1 || task_verdict=1
  "$CUBRID/bin/cub_commdb" --shutdown-all > /tmp/pr7927-loader-master-stop-green.log 2>&1 || task_verdict=1
  wait "$task_master_pid" || task_verdict=1
  exit "$task_verdict"
}
trap finish_loader EXIT
python3 - <<'PY'
import subprocess,time
for attempt in range(40):
    result=subprocess.run(['csql','-C','-u','dba','-t','-N','-c','select 42;','oos_notype289'],text=True,capture_output=True)
    if result.returncode==0 and result.stdout.strip()=='42':
        print('PASS native client/server readiness')
        break
    time.sleep(0.25)
else:
    raise RuntimeError('Task server did not reconnect to its selected master')
PY
cd "$task_artifacts"
python3 /home/vimkim/gh/my-cubrid-docs-pr7927-temporary-oos-stub/cbrd-27089/design/value-ref-evidence/check-server-loader.py "$task_db" "$task_artifacts"
