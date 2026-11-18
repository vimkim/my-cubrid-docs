#!/bin/bash -l
# inside container: count postpone-cache misses (i.e. log_do_postpone calls on commit / sysop) for cbrd_27485.sql
set -u
cd /home/CUBRID/databases
cat >> /home/CUBRID/conf/cubrid.conf <<'C'
test_mode=yes
java_stored_procedure=no
C
cubrid createdb basic en_US.utf8 > /out/createdb.log 2>&1
cubrid server start basic > /out/start.log 2>&1
cubrid statdump basic > /out/stat_before.txt 2>&1
cubrid statdump -i 1 -c basic > /out/stat_series.txt 2>&1 &
SD=$!
sleep 3
csql -u dba -C -i /home/cubrid-testcases/sql/_36_guava/cbrd_27485/cases/cbrd_27485.sql basic > /out/csql.out 2>&1
echo "csql rc=$?" >> /out/csql.out
sleep 3; kill $SD
cubrid statdump basic > /out/stat_after.txt 2>&1
cubrid server stop basic > /out/stop.log 2>&1
cp -a /home/CUBRID/log /out/cubrid_log
