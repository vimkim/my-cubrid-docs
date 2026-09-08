#!/bin/bash
# Probe for log_enc_04 under OOS: which statements produce RVHF_INSERT_NEWHOME, RVOVF_PAGE_UPDATE,
# RVHF_MVCC_UPDATE_OVERFLOW, RVOOS_* on this build. Runs in the isolated namespace only.
. $init_path/init.sh
init test
db_name=db_probe_le04
mkdir $db_name
cd $db_name
cubrid_createdb -r $db_name --db-volume-size=20m --log-volume-size=20m
cd ..
rm -f csql.err
change_db_parameter "er_log_tde=yes"
change_db_parameter "enable_string_compression=no"

echo "### PROBE A: relocation via page fill (SA mode)"
csql -udba -S -c "create table t (a int) encrypt;" $db_name
csql -udba -S -c "insert into t (a) values(4), (5)" $db_name
csql -udba -S -c "alter table t add column b varchar(10000)" $db_name
csql -udba -S -c "update t set b=rpad('b', 10000, ' ') where a=4" $db_name
csql -udba -S -c "insert into t (a, b) values (7, rpad('c', 3800, ' ')), (8, rpad('c', 3800, ' ')), (9, rpad('c', 3800, ' ')), (10, rpad('c', 3800, ' '))" $db_name
csql -udba -S -c "update t set b=rpad('b', 3800, ' ') where a=5" $db_name
echo "A_after_update: $(grep -c 'rcvindex = RVHF_INSERT_NEWHOME' csql.err)"

echo "### PROBE B: fixed-width BIT column -> overflow record (SA mode)"
csql -udba -S -c "create table t_fix (a bit(160000)) encrypt;" $db_name
csql -udba -S -c "insert into t_fix (a) values (cast(rpad('a', 40000, 'a') as bit(160000)))" $db_name
csql -udba -S -c "select bit_length(a) from t_fix" $db_name
csql -udba -S -c "update t_fix set a=cast(rpad('b', 40000, 'b') as bit(160000))" $db_name
echo "B_ovf_insert: $(grep -c 'rcvindex = RVOVF_NEWPAGE_INSERT' csql.err)  B_ovf_update: $(grep -c 'rcvindex = RVOVF_PAGE_UPDATE' csql.err)"

echo "### PROBE C: CS mode MVCC update of the overflow record + OOS records"
cubrid server start $db_name
csql -udba -c "insert into t_fix (a) values (cast(rpad('c', 40000, 'c') as bit(160000)))" $db_name
csql -udba -c "update t_fix set a=cast(rpad('d', 40000, 'd') as bit(160000)) where bit_length(a) = 160000" $db_name
csql -udba -c "create table t2_big (a varchar(20000)) encrypt;" $db_name
csql -udba -c "insert into t2_big (a) values(rpad('a', 20000, ' '))" $db_name
csql -udba -c "update t2_big set a=rpad('b', 20000, ' ')" $db_name
csql -udba -c "delete from t2_big" $db_name
cubrid server stop $db_name

grep -h "prior_set_tde_encrypted" csql.err $CUBRID/log/server/${db_name}_latest.err > result.log 2>&1
echo "### rcvindex counts (all)"
grep -oE 'rcvindex = [A-Z_]+' result.log | sort | uniq -c | sort -rn
echo "### csql errors"
grep -iE 'ERROR|error code' csql.err | grep -v prior_set_tde | head -5
cubrid service stop
cubrid deletedb $db_name
rm -rf $db_name
finish
