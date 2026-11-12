#!/bin/bash
# Sidecar scenario: `cubrid diagdb -d 9 [--dump-records]` on a database whose heaps have Sidecar stores.
# Expects: diagdb exits 0 with and without --dump-records, every store appears once as a section of its owner's
# dump and never as a heap of its own, so the heap blocks match a database made with the stores off.
# usage: check_diagdb.sh <cubrid worktree with .cub-workenv> <work dir>
set -u
WT=${1:?worktree}; WORK=${2:?work dir}
. "$WT/.cub-workenv/env.sh"
export CUBRID_ENABLE_STRING_COMPRESSION=no  # keep the big values above the 64-byte force_external floor
fail=0
check() { if [ "$1" = 0 ]; then echo "PASS  $2"; else echo "FAIL  $2"; fail=1; fi; }
run() {
  local mode=$1 db=scdiag_$1 dir=$WORK/$1
  rm -rf "${dir:?}"; mkdir -p "$dir"; cd "$dir" || exit 2
  cubrid deletedb "$db" </dev/null >/dev/null 2>&1
  CUBRID_SIDECAR_FORCE_EXTERNAL=$mode cubrid createdb -F "$dir" --db-volume-size=64M --log-volume-size=64M "$db" en_US \
    </dev/null >create.log 2>&1 || { echo "createdb $mode failed"; exit 2; }
  {
    echo "create table foo(a int, b string);"
    for i in $(seq 100); do echo "insert into foo values($i, 'hello kitty');"; done
    echo "create table big(a int, b varchar);"
    for i in $(seq 20); do echo "insert into big values($i, repeat('sidecar-big-$i ', 300));"; done
  } > load.sql
  CUBRID_SIDECAR_FORCE_EXTERNAL=$mode csql -u dba -S -i load.sql "$db" </dev/null >load.log 2>&1
  cubrid diagdb -d 9 "$db" </dev/null >plain.txt 2>plain.err; echo $? >plain.rc
  cubrid diagdb -d 9 --dump-records "$db" </dev/null >records.txt 2>records.err; echo $? >records.rc
  cubrid deletedb "$db" </dev/null >/dev/null 2>&1
}
run yes; run no
for m in yes no; do
  check "$(cat "$WORK/$m/plain.rc")" "force_external=$m: diagdb -d 9 exits 0"
  check "$(cat "$WORK/$m/records.rc")" "force_external=$m: diagdb -d 9 --dump-records exits 0 [$(tail -1 "$WORK/$m/records.err")]"
done
h_yes=$(grep -c 'DUMPING HEAP FILE' "$WORK/yes/plain.txt"); h_no=$(grep -c 'DUMPING HEAP FILE' "$WORK/no/plain.txt")
s_yes=$(grep -c 'SIDECAR STORE FILE INFORMATION' "$WORK/yes/plain.txt")
[ "$s_yes" -ge 2 ]; check $? "force_external=yes: the dump lists the stores as owner sections [$s_yes, catalog and big at least]"
[ "$h_yes" = "$h_no" ]; check $? "a store is not dumped as a heap of its own [heaps yes $h_yes, no $h_no]"
n=$(grep -c 'hello kitty' "$WORK/yes/records.txt"); [ "$n" = 100 ]; check $? "force_external=yes: --dump-records prints the 100 foo objects [$n]"
n=$(grep -c 'hello kitty' "$WORK/yes/plain.txt"); [ "$n" = 0 ]; check $? "force_external=yes: without --dump-records no object is printed [$n]"
exit $fail
