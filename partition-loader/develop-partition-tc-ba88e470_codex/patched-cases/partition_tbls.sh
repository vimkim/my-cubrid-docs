#!/bin/bash
# cubrid-testcases-private-ex/shell/_06_issues/_13_2h/bug_bts_11093/cases/
. $init_path/init.sh
init test

set -x

db_name=db11903
sfile=$db_name"_schema"
ofile=$db_name"_objects"
res=bug_bts_11093.output
ans=bug_bts_11093.answer

function recreate_db {
	cubrid server stop $db_name
	cubrid deletedb $db_name >/dev/null 2>&1
	rm -rf $db_name
	#create a new folder
	mkdir $db_name
	cd $db_name

	cubrid_createdb --db-volume-size=20M --log-volume-size=20M -r $db_name
	cd ..
	cubrid server start $db_name
}


cubrid service stop

rm -f $ofile
rm -f $sfile
rm -f $res

#test1 basic case: unload and load database
recreate_db

csql -u dba  -c "create table t(i int) partition by hash (i) partitions 5" $db_name;
csql -u dba  -c "insert into t select rownum from _db_class limit 40;" $db_name;

cubrid unloaddb  $db_name

recreate_db

echo "========== test1 ==========" > $res
cubrid loaddb -C -v -u dba -s $sfile -d $ofile $db_name >> $res 2>&1 

#test2 modify objects so that we generate an error
recreate_db

csql -u dba  -c "create table t(i int) partition by range(i) (partition p0 values less than (10));" $db_name;
csql -u dba -c "insert into t values(1);" $db_name;

cubrid unloaddb  $db_name

# Keep the valid input for a second load after the failed batch.
cp $ofile test2_valid.objects
#add 100 to objects file
echo 100 >> $ofile
recreate_db

# This load must reject 100: p0 only accepts i < 10. Keep its output
# separate from the successful-load answers used by test1 and test3.
cubrid loaddb -C -v -u dba -s $sfile -d $ofile $db_name > test2_invalid.output 2>&1
load_status=$?
cat test2_invalid.output
if [ "$load_status" -ne 0 ]
then
    write_ok "test2: invalid partition load failed"
else
    write_nok "test2: invalid partition load unexpectedly succeeded"
fi
if grep -q "Appropriate partition does not exist" test2_invalid.output
then
    write_ok "test2: partition error reported"
else
    write_nok "test2: missing partition error"
fi

# With no periodic commit, both the valid row and invalid row must be
# rolled back. Check the parent and the physical partition independently.
for tbl in t t__p__p0
do
    if csql -u dba -t -N -c "select count(*) from $tbl;" $db_name > test2_rollback_$tbl.output 2>&1 &&
        [ "$(tr -d '[:space:]' < test2_rollback_$tbl.output)" = "0" ]
    then
        write_ok "test2: $tbl failed batch rolled back"
    else
        write_nok "test2: $tbl failed batch was not empty or query failed"
        cat test2_rollback_$tbl.output
    fi
done

# The same database must remain usable, and the original valid input
# must load exactly one row (i = 1) after the failed attempt.
if cubrid loaddb -C -v -u dba -d test2_valid.objects $db_name > test2_valid.output 2>&1
then
    write_ok "test2: next valid load succeeded"
else
    write_nok "test2: next valid load failed"
    cat test2_valid.output
fi
for tbl in t t__p__p0
do
    if csql -u dba -t -N -c "select case when count(*) = 1 and min(i) = 1 and max(i) = 1 then 1 else 0 end from $tbl;" $db_name > test2_valid_$tbl.output 2>&1 &&
        [ "$(tr -d '[:space:]' < test2_valid_$tbl.output)" = "1" ]
    then
        write_ok "test2: $tbl contains exactly the next valid row"
    else
        write_nok "test2: $tbl next valid row mismatch or query failed"
        cat test2_valid_$tbl.output
    fi
done
rm -f test2_valid.objects

#test3 large table with periodic commits
recreate_db

csql -u dba  -c "create table t(i int) partition by hash(i) partitions 20;" $db_name;
csql -u dba  -c "insert into t select rownum from _db_class a, _db_class b, _db_class c limit 10000;" $db_name;

cubrid unloaddb  $db_name

recreate_db

echo "========== test3 ==========" >> $res
cubrid loaddb -C -c 100 -u dba -s $sfile -d $ofile $db_name >> $res 2>&1 

compare_result_between_files $res $ans sort

echo ";sc t" | csql -u dba $db_name > test.log
csql -u dba $db_name -c " select count(*) from t;" >> test.log
format_csql_output test.log
compare_result_between_files test.log test.answer


cubrid service stop
cubrid deletedb $db_name
rm $ofile $sfile
rm -rf $dbname
rm *.log
finish
