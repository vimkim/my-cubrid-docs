#!/bin/bash
# Feasibility probe only: with auto_restart_server=no, does kill -9 of cub_server leave a
# database that `cubrid server start` recovers, and how long does each step take?
# Uses a trivial non-OOS fixture on purpose, so no expectation of the ticket 14 case is
# observed here before that case's oracle is written.
set -u
ts() { date +%H:%M:%S; }
root=/home/vimkim/.cub/campaign/cbrd-26659/ticket14
mode="${1:-debug_gcc}"
export CUBRID="/home/vimkim/.cub/install/oos-baseline-f4299ac0c/${mode}"
export PATH="$CUBRID/bin:$PATH"
export LD_LIBRARY_PATH="$CUBRID/lib:${LD_LIBRARY_PATH:-}"
export CUBRID_DATABASES="${root}/db"
db=t14rprobe
work="${root}/db/${db}"; rm -rf "$work"; mkdir -p "$work"; cd "$work" || exit 1

cp "$CUBRID/conf/cubrid.conf" "$CUBRID/conf/cubrid.conf.t14probe.bak"
grep -v '^auto_restart_server *=' "$CUBRID/conf/cubrid.conf" > c.tmp
echo 'auto_restart_server=no' >> c.tmp
cp c.tmp "$CUBRID/conf/cubrid.conf"; rm -f c.tmp

echo "$(ts) createdb";  cubrid createdb --db-page-size=16384 --db-volume-size=32M --log-volume-size=32M "$db" en_US.utf8 >/dev/null
echo "$(ts) start";     cubrid server start "$db" >/dev/null 2>&1; echo "$(ts) start rc=$?"
echo "$(ts) ddl";       csql -u dba -c "CREATE TABLE p (i INT); INSERT INTO p VALUES (7);" "$db" >/dev/null 2>&1; echo "$(ts) ddl rc=$?"

pids=$(pgrep -f "cub_server ${db}")
echo "$(ts) kill -9 [$pids]"
for p in $pids; do kill -9 "$p"; done
for i in $(seq 1 40); do pgrep -f "cub_server ${db}" >/dev/null || break; sleep 0.5; done
echo "$(ts) gone=[$(pgrep -f "cub_server ${db}" | tr '\n' ' ')]"
echo "$(ts) master alive=[$(pgrep -x cub_master | tr '\n' ' ')]"

echo "$(ts) restart attempt"
cubrid server start "$db" > restart.out 2>&1; echo "$(ts) restart rc=$?"
sed 's/^/  restart: /' restart.out
echo "$(ts) select"
csql -u dba -c "SELECT i FROM p;" "$db" > sel.out 2>&1; echo "$(ts) select rc=$?"
sed 's/^/  select: /' sel.out

echo "$(ts) teardown"
cubrid server stop "$db" >/dev/null 2>&1
cubrid deletedb "$db" >/dev/null 2>&1
cp "$CUBRID/conf/cubrid.conf.t14probe.bak" "$CUBRID/conf/cubrid.conf"
rm -f "$CUBRID/conf/cubrid.conf.t14probe.bak"
echo "$(ts) done; auto_restart_server lines now=$(grep -c auto_restart_server "$CUBRID/conf/cubrid.conf")"
