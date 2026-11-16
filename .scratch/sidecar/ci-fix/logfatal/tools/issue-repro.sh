#!/usr/bin/env bash
# issue-repro.sh NAME INSTALL PORT
# Runs the CBRD-28058 reproduction on a private copy of INSTALL: its own databases, CUBRID_TMP and cub_master
# port, ha_mode off, log_max_archives=0, no automatic checkpoint, a 20M log volume. N_CKPT sets the number of
# checkpoints in the final DROP loop (default 3, as in the issue); FULL_UPDATE=1 updates all of big twice per loop
# so each loop makes archives. Writes ~/tk/NAME/result.txt.
set -uo pipefail
NAME=${1:?}; INSTALL=${2:?}; PORT=${3:?}
A=$HOME/tk/$NAME
[ -e "$A" ] && { echo "exists: $A" >&2; exit 1; }
mkdir -p "$A/work"
cp -a "$INSTALL" "$A/cubrid"
[ -d "$A/cubrid/databases" ] && mv "$A/cubrid/databases" "$A/cubrid/databases.copied"
mkdir -p "$A/cubrid/databases" "$A/cubrid/tmp"
rm -f "${A:?}"/cubrid/log/server/*
for v in ${!CUBRID@}; do unset "$v"; done
unset CUBRID_CONF_FILE CUBRID_BROKER_CONF_FILE
export CUBRID="$A/cubrid" CUBRID_DATABASES="$A/cubrid/databases" CUBRID_TMP="$A/cubrid/tmp"
export PATH="$CUBRID/bin:$PATH" LD_LIBRARY_PATH="$CUBRID/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
C=$CUBRID/conf/cubrid.conf
sed -i '/^cubrid_port_id=/d; /^log_max_archives=/d; /^ha_mode=/d; /^checkpoint_/d; /^java_stored_procedure=/d; /^data_buffer_size=/d; /^log_buffer_size=/d' "$C"
sed -i "/^\[common\]/a cubrid_port_id=$PORT\nlog_max_archives=0\ncheckpoint_every_size=10G\ncheckpoint_interval=3600s\nha_mode=no\njava_stored_procedure=no\ndata_buffer_size=256M\nlog_buffer_size=16M\ncall_stack_dump_on_error=yes" "$C"
cubrid_rel > "$A/cubrid_rel.txt" 2>&1
cd "$A/work"
db=lfdb
cubrid createdb --log-volume-size=20M --db-volume-size=128M "$db" en_US.utf8 < /dev/null > createdb.out 2>&1
cubrid server start "$db" < /dev/null > start1.out 2>&1
E=$(ls -t "$CUBRID"/log/server/${db}_2*.err | head -1)
ck() { grep -c "Checkpoint finished" "$E"; }
lost() { grep -c "unable to find log page" "$E"; }
checkpoint() {
  local c t=0
  c=$(ck)
  echo ";checkpoint" > ck.sql; csql -u dba --sysadm -i ck.sql "$db" < /dev/null > /dev/null 2>&1
  while [ "$(ck)" -eq "$c" ] && [ "$(lost)" -eq 0 ] && [ $t -lt 120 ]; do sleep 1; t=$((t+1)); done
}
csql -u dba -c "create table big (a int primary key, b varchar(500))" "$db" < /dev/null
csql -u dba -c "insert into big select rownum, repeat('y', 400) from db_class c1, db_class c2, db_class c3 limit 50000" "$db" < /dev/null
checkpoint
for i in $(seq 300); do echo "create table f$i (a int, b char(2000)); insert into f$i values (1, 'x');"; done > fill.sql
for i in $(seq 300); do echo "drop table f$i;"; done >> fill.sql
csql -u dba -i fill.sql "$db" < /dev/null > /dev/null
csql -u dba -c "update big set b = repeat('z', 400)" "$db" < /dev/null > /dev/null
csql -u dba -c "update big set b = repeat('y', 400)" "$db" < /dev/null > /dev/null
checkpoint
csql -u dba -c "update big set b = repeat('z', 400)" "$db" < /dev/null > /dev/null
csql -u dba -c "update big set b = repeat('y', 400)" "$db" < /dev/null > /dev/null
for i in $(seq 5); do echo "create table g$i (a int, b char(2000)); insert into g$i values (1, 'x');"; done > drop.sql
for i in $(seq 5); do echo "drop table g$i;"; done >> drop.sql
( while [ ! -f stop ]; do csql -u dba -i drop.sql "$db" < /dev/null > /dev/null 2>&1; done ) &
for n in $(seq "${N_CKPT:-3}"); do
  if [ -n "${FULL_UPDATE:-}" ]; then
    csql -u dba -c "update big set b = repeat('v$n', 200)" "$db" < /dev/null > /dev/null 2>&1
    csql -u dba -c "update big set b = repeat('u$n', 200)" "$db" < /dev/null > /dev/null 2>&1
  else
    csql -u dba -c "update big set b = repeat('w$n', 200) where a <= 20000" "$db" < /dev/null > /dev/null 2>&1
  fi
  checkpoint
  [ "$(lost)" -gt 0 ] && break
done
touch stop; wait; rm -f stop
sleep 3
cubrid server start "$db" < /dev/null > start2.out 2>&1
{
  echo "build: $(grep -o 'CUBRID [0-9.]* ([^)]*)' "$A/cubrid_rel.txt" | head -1)"
  echo "checkpoints_finished=$(ck) lost_page_msgs=$(lost) fatal=$(grep -c 'LOG FATAL ERROR' "$E")"
  grep 'Checkpoint finished' "$E" | awk -v p=-1 '{for(i=1;i<=NF;i++) if($i=="redo"){r=$(i+3)+0; if(p>=0 && r<p) print "redo_lowered: " p " -> " r; p=r}}' 
  echo "first_lost: $(grep -m1 'unable to find log page' "$E")"
  echo "restart: $(grep -c 'fail' start2.out) fail lines; $(grep -m1 -o 'Unable to mount[^.]*' start2.out)"
} > "$A/result.txt"
cubrid server stop "$db" < /dev/null > stop.out 2>&1
cubrid service stop < /dev/null >> stop.out 2>&1
cubrid master stop < /dev/null >> stop.out 2>&1 || true
cat "$A/result.txt"
