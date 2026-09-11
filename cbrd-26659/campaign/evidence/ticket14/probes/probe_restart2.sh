#!/bin/bash
# Feasibility probe only (non-OOS fixture): whole-instance crash -- kill -9 of cub_server,
# cub_pl and cub_master -- followed by a controlled restart. Establishes the crash protocol
# the ticket 14 case uses and measures how long each step takes.
set -u
ts() { date +%H:%M:%S; }
root=/home/vimkim/.cub/campaign/cbrd-26659/ticket14
mode="${1:-debug_gcc}"
export CUBRID="/home/vimkim/.cub/install/oos-baseline-f4299ac0c/${mode}"
export PATH="$CUBRID/bin:$PATH"
export LD_LIBRARY_PATH="$CUBRID/lib:${LD_LIBRARY_PATH:-}"
export CUBRID_DATABASES="${root}/db"
db=t14rprobe
work="${root}/db/${db}"
cubrid server stop "$db" >/dev/null 2>&1; cubrid deletedb "$db" >/dev/null 2>&1
rm -rf "$work"; mkdir -p "$work"; cd "$work" || exit 1

cp "$CUBRID/conf/cubrid.conf" "$CUBRID/conf/cubrid.conf.t14probe.bak"
grep -v '^auto_restart_server *=' "$CUBRID/conf/cubrid.conf" > c.tmp
echo 'auto_restart_server=no' >> c.tmp
cp c.tmp "$CUBRID/conf/cubrid.conf"; rm -f c.tmp

echo "$(ts) createdb"; cubrid createdb --db-page-size=16384 --db-volume-size=32M --log-volume-size=32M "$db" en_US.utf8 >/dev/null
echo "$(ts) start";    cubrid server start "$db" >/dev/null 2>&1; echo "$(ts) start rc=$?"
csql -u dba -c "CREATE TABLE p (i INT); INSERT INTO p VALUES (7);" "$db" > ddl.out 2>&1; echo "$(ts) ddl rc=$? out=[$(tr -d '\n' < ddl.out)]"

srv=$(pgrep -f "cub_server ${db}"); pl=$(pgrep -f "cub_pl ${db}"); mst=$(pgrep -x cub_master)
echo "$(ts) crash: server=[$srv] pl=[$pl] master=[$mst]"
for p in $srv $pl $mst; do kill -9 "$p" 2>/dev/null; done
for i in $(seq 1 40); do
  [ -z "$(pgrep -f "cub_server ${db}")$(pgrep -x cub_master)" ] && break
  sleep 0.5
done
echo "$(ts) after crash: server=[$(pgrep -f "cub_server ${db}" | tr '\n' ' ')] master=[$(pgrep -x cub_master | tr '\n' ' ')]"

echo "$(ts) restart"
cubrid server start "$db" > restart.out 2>&1; echo "$(ts) restart rc=$?"
sed 's/^/  restart: /' restart.out
echo "$(ts) select"
csql -u dba -c "SELECT i FROM p;" "$db" > sel.out 2>&1; echo "$(ts) select rc=$?"
sed 's/^/  select: /' sel.out
echo "$(ts) csql exit status on a deliberately bad query:"
csql -u dba -c "SELECT nosuchcolumn FROM p;" "$db" > bad.out 2>&1; echo "  bad rc=$?"; sed 's/^/  bad: /' bad.out
echo "$(ts) csql exit status against a nonexistent database:"
csql -u dba -c "SELECT 1;" nosuchdb_t14 > nodb.out 2>&1; echo "  nodb rc=$?"; sed 's/^/  nodb: /' nodb.out

echo "$(ts) teardown"
cubrid server stop "$db" >/dev/null 2>&1
cubrid deletedb "$db" >/dev/null 2>&1
cp "$CUBRID/conf/cubrid.conf.t14probe.bak" "$CUBRID/conf/cubrid.conf"
rm -f "$CUBRID/conf/cubrid.conf.t14probe.bak"
echo "$(ts) done"
