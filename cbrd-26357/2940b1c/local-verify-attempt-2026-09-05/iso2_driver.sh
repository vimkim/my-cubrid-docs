#!/bin/bash
# Entered via iso2_enter.sh:
#   unshare -r --mount-proc -i -p -f -n --kill-child=SIGKILL -- bash -c '<binds>; exec bash /mnt/iso2_driver.sh ...'
# Namespaces: user, mount (+ private tmpfs /tmp, private /etc/hosts, empty /etc/resolv.conf), ipc, pid, net.
# Daemon-starting commands must never write into a pipe (started daemons inherit it and the reader never sees EOF).
set -u
export CUBRID=/mnt CUBRID_DATABASES=/mnt/databases PATH=/mnt/bin:$PATH LD_LIBRARY_PATH=/mnt/lib
export init_path=$HOME/CTP/shell/init_path
ip link set lo up || { echo "[ns] lo up failed"; exit 2; }
echo "[ns] uid=$(id -u) visible-cub=$(pgrep -c cub || echo 0) /tmp-entries=$(ls /tmp | wc -l) listeners=[$(ss -ltn 2>/dev/null | tail -n +2 | awk '{print $4}' | tr '\n' ' ')]"
echo "[ns] $(cubrid_rel | sed -n 2p) | $(grep '^cubrid_port_id' /mnt/conf/cubrid.conf)"
st=$(cubrid service status 2>&1 </dev/null); echo "$st" | head -2 | sed 's/^/[ns] /'
if echo "$st" | grep -q 'master is running'; then echo "[ns] ISOLATION FAILED: a master is reachable before start. Aborting."; exit 3; fi
if [ "${1:-}" = preflight ]; then
  cubrid service start </dev/null >/mnt/svc_start.out 2>&1
  grep -E 'master|broker' /mnt/svc_start.out | sed 's/^/[ns] /'
  echo "[ns] listeners after start=[$(ss -ltn 2>/dev/null | tail -n +2 | awk '{print $4}' | tr '\n' ' ')] /tmp=[$(ls /tmp | tr '\n' ' ')]"
  cubrid service stop </dev/null >/mnt/svc_stop.out 2>&1
  grep -E 'master' /mnt/svc_stop.out | sed 's/^/[ns] /'
  exit 0
fi
cases=$2; name=$(basename "$(dirname "$cases")")
work=/mnt/work_$name; rm -rf "$work"; cp -a "$cases" "$work"; cd "$work"
# keep the logs the testcase would delete, for inspection
sed -i -E "s/^(rm (-f )?\*\.log[[:space:]]*)$/# kept: \1/" "./$name.sh"
echo "[ns] running $name at $(date +%H:%M:%S)"
bash ./$name.sh </dev/null >/mnt/run_$name.out 2>&1; rc=$?
echo "[ns] script rc=$rc at $(date +%H:%M:%S)"
grep -E 'is missing!|-[0-9]+ : (OK|NOK)' /mnt/run_$name.out | grep -v '^+ ' | sort -u | sed 's/^/[ns] /'
