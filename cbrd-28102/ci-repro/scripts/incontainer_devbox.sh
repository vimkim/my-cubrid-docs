#!/bin/bash
# Runs CTP sql_by_cci inside rocky9 devbox (for the local EL9 release_gcc builds). Mirrors entrypoint copy_conf + apply_scope.
set -u
export WORKDIR=/home CUBRID=/home/CUBRID CUBRID_DATABASES=/home/CUBRID/databases CTP_HOME=/home/cubrid-testtools/CTP
export JAVA_HOME=/opt/jdk8 CTP_SKIP_UPDATE=1 USER=root
export PATH=$CUBRID/bin:$CTP_HOME/bin:$CTP_HOME/common/script:$JAVA_HOME/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
export LD_LIBRARY_PATH=$CUBRID/lib:$CUBRID/cci/lib
unset CUBRID_CONF_FILE CUBRID_BROKER_CONF_FILE CUBRID_TMP
ulimit -c unlimited
touch /out/ctp.out.start
conf=$CTP_HOME/conf/sql_by_cci_runtime.conf
cp -f $CTP_HOME/conf/sql_by_cci.conf $conf
[ -n "${TEST_SCENARIO:-}" ] && sed -i "s|^scenario=.*|scenario=$TEST_SCENARIO|" $conf
start=$(date +%s); rc=0
( cd /home && HOME=/home timeout --signal=TERM "${RUN_LIMIT:-3000}" $CTP_HOME/bin/ctp.sh sql_by_cci -c $conf ) > /out/ctp.out 2>&1 || rc=$?
echo "[repro] ctp rc=$rc elapsed=$(( $(date +%s) - start ))s"
echo "$rc" > /out/rc
cp -a "$CTP_HOME/result/sql_by_cci" /out/result 2>/dev/null || true
mkdir -p /out/cubrid_log && cp -a /home/CUBRID/log/. /out/cubrid_log/ 2>/dev/null || true
find / -xdev -name 'core*' -type f -newer /out/ctp.out.start 2>/dev/null > /out/cores.list || true
ps -eo pid,etime,args > /out/ps.txt
exit 0
