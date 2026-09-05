#!/bin/bash
# Runs inside: unshare --map-user/--map-group -ipf --mount-proc
set -u
S=/tmp/claude-1000/-home-vimkim-gh-cb-oos-storage/777ff0f7-1761-4b37-9859-227a4803818a/scratchpad
mount --bind "$S/CUBRID_iso" /mnt || { echo "iso bind failed"; exit 2; }
ISO=/mnt
TCW=/home/vimkim/gh/tc/cubrid-testcases-private-ex-tc-pr-6864
export CUBRID=$ISO CUBRID_DATABASES=$ISO/databases
export PATH=$ISO/bin:$PATH LD_LIBRARY_PATH=$ISO/lib
# Shadow the host's CTP install snapshot so nothing on the host is read or replaced.
mkdir -p "$S/fm_home"
mount --bind "$S/fm_home" "$HOME/.CUBRID_SHELL_FM" || { echo "bind mount failed"; exit 2; }
echo "ns uid=$(id -u) visible-cub=$(pgrep -c cub || echo 0) CUBRID=$CUBRID"
cubrid_rel | sed -n 2p
TESTS="_36_damson/cbrd_23608_tde/file_enc_03 _36_damson/cbrd_23608_tde/file_enc_05 _06_issues/_14_2h/bug_bts_14120 _06_issues/_12_2h/bug_bts_9836 _35_cherry/issue_21654_server_side_loaddb/bigPageSize"
for t in $TESTS; do
  name=$(basename "$t")
  conf=$(mktemp /tmp/iso_shell.XXXXXX.conf)
  cp "$HOME/CTP/conf/shell_ci.conf" "$conf"
  sed -i "s|^scenario=.*|scenario=$TCW/shell/$t|" "$conf"
  sed -i 's|^testcase_update_yn=.*|testcase_update_yn=false|' "$conf"
  sed -i 's|^testcase_exclude_from_file=.*|#&|' "$conf"
  sed -i 's|^default.cubrid.cubrid_port_id=.*|default.cubrid.cubrid_port_id=1600|' "$conf"
  sed -i 's|^default.broker1.BROKER_PORT=.*|default.broker1.BROKER_PORT=33600|' "$conf"
  sed -i 's|^default.broker1.APPL_SERVER_SHM_ID=.*|default.broker1.APPL_SERVER_SHM_ID=33600|' "$conf"
  sed -i 's|^default.broker2.BROKER_PORT=.*|default.broker2.BROKER_PORT=33601|' "$conf"
  sed -i 's|^default.broker2.APPL_SERVER_SHM_ID=.*|default.broker2.APPL_SERVER_SHM_ID=33601|' "$conf"
  sed -i 's|^default.ha.ha_port_id=.*|default.ha.ha_port_id=33602|' "$conf"
  echo "=================== $name  ($(date +%H:%M:%S)) ==================="
  "$HOME/CTP/bin/ctp.sh" shell -c "$conf" > "$S/ctp_$name.log" 2>&1
  rc=$?
  grep -E '\[TESTCASE\]|Total (Case|Execution Case|Success Case|Fail Case)' "$S/ctp_$name.log" | sed 's/^/  /'
  echo "  ctp rc=$rc  host-port-1523 check: $(ss -ltn | grep -c ':1523 ')"
  rm -f "$conf"
done
echo "=================== done $(date +%H:%M:%S) ==================="
