#!/bin/bash
# usage: space24771.sh <yes|no> <rounds>: the cbrd_24771 steps, printing hot pages, store stats and spacedb per round
set -u
FORCE=$1; R=$2
S=/mnt/nvme/data-5/tmp/claude-1000/-home-vimkim-gh-cb-sidecar-fix-btree-del/8ca1794d-1faf-4e13-a525-1aa1ccb4f425/scratchpad
TC=/home/vimkim/gh/cubrid-testcases-private-ex/tc-pr-8504-btree-del/shell/_06_issues/_23_1h/cbrd_24771/cases
source /home/vimkim/gh/cb/sidecar-fix-btree-del/.cub-workenv/env.sh
export CUBRID_SIDECAR_FORCE_EXTERNAL=$FORCE
db=sc24771; d=$S/s24771_$FORCE; rm -rf "${d:?}"; mkdir -p "$d"; cd "$d" || exit 2
cubrid deletedb $db </dev/null >/dev/null 2>&1
cubrid createdb -F "$d" -r $db --db-volume-size=128M --log-volume-size=128M en_US </dev/null > create.log 2>&1 || exit 2
cubrid loaddb $db -u dba -S -s $TC/testdb_schema -d $TC/testdb_objects </dev/null > load.log 2>&1
cubrid server start $db </dev/null > srv.log 2>&1
csql $db --no-auto-commit -u dba -i $TC/insert_data.sql </dev/null > ins.log 2>&1
csql $db --no-auto-commit -u dba -i $TC/utest.sql </dev/null > u0.log 2>&1
probe() {
  local mode=$1 tag=$2
  hot=$(csql $db -u dba $mode -l -c "show heap capacity of gaon_app_send_data_log" </dev/null 2>&1 | grep -E "Num_pages" | tr -s ' ' | tr '\n' ' ')
  sc=$(csql $db -u dba $mode -l -c "show heap sidecar of gaon_app_send_data_log" </dev/null 2>&1 | grep -iE "page|rec" | tr -s ' ' | tr '\n' ' ')
  sp=$(cubrid spacedb $db $mode -s </dev/null 2>&1 | grep "PERMANENT DATA" | tr -s ' ')
  echo "$tag | hot: $hot | store: $sc | spacedb: $sp"
}
probe -C ref
for ((i=0;i<R;i++)); do csql $db --no-auto-commit -u dba -C -i $TC/utest.sql </dev/null >/dev/null 2>&1; probe -C "C$i"; done
cubrid server stop $db </dev/null >> srv.log 2>&1; cubrid service stop </dev/null >> srv.log 2>&1
for ((i=0;i<R;i++)); do csql $db --no-auto-commit -u dba -S -i $TC/utest.sql </dev/null >/dev/null 2>&1; probe -S "S$i"; done
cubrid deletedb $db </dev/null >/dev/null 2>&1
