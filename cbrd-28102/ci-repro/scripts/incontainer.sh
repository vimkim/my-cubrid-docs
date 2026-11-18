#!/bin/bash -l
# Runs inside cubridci:test_rl8.10. /out is a per-run host directory.
set -u
cd /home
start=$(date +%s)
echo "[repro] start $(date -u +%FT%TZ) scenario=${TEST_SCENARIO:-full}" 
rc=0
timeout --signal=TERM "${RUN_LIMIT:-3000}" /entrypoint.sh test sql_by_cci > /out/ctp.out 2>&1 || rc=$?
echo "[repro] ctp rc=$rc elapsed=$(( $(date +%s) - start ))s"
echo "$rc" > /out/rc
# keep evidence
cp -a "$CTP_HOME/result/sql_by_cci" /out/result 2>/dev/null || true
mkdir -p /out/cubrid_log && cp -a /home/CUBRID/log/. /out/cubrid_log/ 2>/dev/null || true
cp -a /home/CUBRID/conf /out/conf 2>/dev/null || true
ls -la /home/ERROR_BACKUP > /out/error_backup.ls 2>&1 || true
cp -a /home/ERROR_BACKUP /out/ERROR_BACKUP 2>/dev/null || true
find / -xdev -name 'core*' -type f -newer /out/ctp.out.start 2>/dev/null > /out/cores.list || true
ps -eo pid,etime,args > /out/ps.txt
cubrid server status > /out/server_status.txt 2>&1 || true
cubrid hb status > /out/hb_status.txt 2>&1 || true
exit 0
