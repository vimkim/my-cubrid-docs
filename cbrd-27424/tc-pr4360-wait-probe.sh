#!/bin/bash
cd "$(dirname "$0")"
function write_nok
{
  if [ -z "$1" ]
  then
        echo "----------------- $case_no : NOK"
        echo "$case_name-$case_no : NOK" >> ${cur_path}/$result_file
        internal_err=`grep "Internal Error" $CUBRID/log/server/*.err | wc -l`
	if [ $internal_err -gt 0 ]
	then
	    grep "Internal Error" $CUBRID/log/server/*.err >> ${cur_path}/$result_file
	fi
        let "case_no = case_no + 1"
  elif [ -f "$1" ];
  then
	echo "----------------- $case_no : NOK"
	echo "$case_name-$case_no : NOK"  >> ${cur_path}/$result_file
	cat $1 >> ${cur_path}/$result_file
	let "case_no = case_no + 1"
  else
        echo "----------------- $case_no : NOK" $1
        echo "$case_name-$case_no : NOK" $1 >> ${cur_path}/$result_file
        let "case_no = case_no + 1"
  fi
}
function write_ok
{
  if [ -z "$1" ]
  then
        echo "----------------- $case_no : OK"
        echo "$case_name-$case_no : OK" >>  ${cur_path}/$result_file
        let "case_no = case_no + 1"
  else
        echo "----------------- $case_no : OK " $1
        echo "$case_name-$case_no : OK " $1 >>  ${cur_path}/$result_file
        let "case_no = case_no + 1"
  fi
}
function wait_pid_exit {
	i=0
	while kill -0 $1 2>/dev/null && [ $i -lt 60 ]
	do
		sleep 1
		i=$((i+1))
	done
	if kill -0 $1 2>/dev/null
	then
		write_nok "CSQL did not exit after releasing the transaction"
		kill -KILL $1
	fi
	if ! wait $1
	then
		write_nok "CSQL failed"
	fi
}

cur_path=$PWD
result_file=probe-verdict.txt
case_name=probe
case_no=1
: > "$result_file"
bash -c "exit 42" &
pid=$!
wait_pid_exit "$pid"
write_ok "later success"
cat "$result_file"
if [ "$(grep -c NOK "$result_file")" -ne 1 ]; then exit 1; fi
bash -c "exit 0" &
pid=$!
wait_pid_exit "$pid"
if [ "$(grep -c NOK "$result_file")" -ne 1 ]; then exit 1; fi
printf "actual wait_pid_exit failure/success probes passed\n"
