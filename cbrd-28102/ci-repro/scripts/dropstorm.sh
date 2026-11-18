#!/bin/bash -l
# CBRD-28058 reporter-style recipe: small log volume, no kept archives, many DROPs between checkpoints.
set -u
cd /home/CUBRID/databases
cat >> /home/CUBRID/conf/cubrid.conf <<'C'
log_max_archives=0
checkpoint_interval=1min
java_stored_procedure=no
C
cubrid createdb --log-volume-size=20M basic en_US.utf8 > /out/createdb.log 2>&1
cubrid server start basic > /out/start.log 2>&1
start=$(date +%s)
timeout 1500 csql -u dba -C -i /dropstorm.sql basic > /out/csql.out 2>&1
echo "csql rc=$? elapsed=$(( $(date +%s) - start ))s" >> /out/csql.out
cubrid server status > /out/status.txt 2>&1
cubrid server stop basic > /out/stop.log 2>&1
cp -a /home/CUBRID/log /out/cubrid_log
cat /home/CUBRID/databases/basic/basic_lginf > /out/lginf.txt 2>&1
