#!/bin/bash
# usage: summarize.sh <head|base> <prefix>
R=/mnt/nvme/data-5/tmp/claude-1000/-home-vimkim-gh-cb-CBRD-28102-sysop-postpone/5ad80319-d102-4d58-b5db-dbf9636be283/scratchpad/repro-cci
for d in $R/runs/$1/$2*; do
  s=$(ls -d $d/result/schedule_*/ 2>/dev/null | head -1)
  si=$s/summary.info
  tot=$(command grep -ac TestCase "$si" 2>/dev/null); nok=$(command grep -ac ':NOK:' "$si" 2>/dev/null)
  e677=$(command grep -arl 'Error:-677' "$s" 2>/dev/null | wc -l)
  c=$(command grep -al 'cbrd_27485.sql' "$si" 2>/dev/null >/dev/null && command grep -a 'cbrd_27485.sql' "$si" | awk -F: '{print $(NF-1)":"$NF}')
  crash=$(command grep -a -l -i -E 'SIGSEGV|SIGABRT|SIGBUS|core dump|FATAL|[Cc]rash' $d/cubrid_log/server/*.err 2>/dev/null | wc -l)
  echo "$(basename $d) rc=$(cat $d/rc 2>/dev/null) total=$tot nok=$nok files677=$e677 c27485=$c errlog_hits=$crash ups=$(command grep -a -h -c 'Server status is UP' $d/cubrid_log/server/*.err 2>/dev/null | paste -sd+ | bc) cores=$(wc -l < $d/cores.list 2>/dev/null) start=$(cat $d/host_start 2>/dev/null) end=$(cat $d/host_end 2>/dev/null)"
done
