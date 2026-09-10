#!/bin/bash
# Replay the bug_bts_4633 JDBC workload with a GDB scheduling probe attached to cub_server.
set -eu
ulimit -c unlimited
attempt=${1:?attempt}
mkdir /mnt/$attempt
cd /mnt/$attempt
CASES_DIR=${CASES_DIR:-/mnt/shell/_06_issues/_11_1h/bug_bts_4633/cases}
echo "cases_dir=$CASES_DIR mode=${PROBE_MODE:-pause}" | tee harness-variant.txt
cp "$CASES_DIR"/*.java .
printf '<ShellConfig><ip>localhost</ip><port>33000</port></ShellConfig>\n' > shell_config.xml
export REAL_INIT_PATH="$PWD"
export CLASSPATH=/mnt/install/jdbc/cubrid_jdbc.jar:/mnt/CTP/shell/init_path/commonforjdbc.jar:.
export PROBE_DIR="$PWD"
export PROBE_MAX_WAIT_S="${PROBE_MAX_WAIT_S:-0.2}"
export PROBE_MODE=none
command -v cubrid
cubrid_rel
cubrid createdb -r db_4633 en_US.utf8 > createdb.log 2>&1
cubrid server start db_4633 > server-start.log 2>&1
cubrid broker start > broker-start.log 2>&1
for pid in $(pgrep -x cub_server); do readlink /proc/$pid/exe; done > engine-identity.txt
server_pid=$(pgrep -x cub_server | head -1)
echo "server_pid=$server_pid" | tee server-pid.txt
javac TestBasel.java Scenario.java > javac.log 2>&1
date +%T.%N > java-start.txt
java -Xms1024m -Xmx1024m -XX:MaxPermSize=512m -XX:+UseParallelGC TestBasel > java.log 2> error.log || true
date +%T.%N > java-end.txt
echo "--- java done; server alive? ---"; pgrep -x cub_server || echo "cub_server gone"
cubrid server status > server-status.log 2>&1 || true
cubrid service stop > service-stop.log 2>&1 || true
# gdb detaches itself on the assert stop or exits when the inferior exits
cp -a /mnt/install/log engine-log 2>/dev/null || true
echo "=== no gdb attached (plain run) ==="
echo "=== java.log ==="; cat java.log
echo "=== error.log (non-MaxPermSize) ==="; grep -v 'ignoring option MaxPermSize' error.log | head -20 || true
echo "=== cores ==="; ls -la core* /mnt/install/core* 2>/dev/null || echo "(none in cwd/install)"
echo "=== server err log ==="; ls engine-log/server/ 2>/dev/null && tail -30 engine-log/server/*.err 2>/dev/null || true
