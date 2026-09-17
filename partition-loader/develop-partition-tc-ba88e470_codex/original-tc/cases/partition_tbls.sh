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

#add 100 to objects file
echo 100 >> $ofile
recreate_db

echo "========== test2 ==========" >> $res
cubrid loaddb -C -v -u dba -s $sfile -d $ofile $db_name >> $res 2>&1 

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
