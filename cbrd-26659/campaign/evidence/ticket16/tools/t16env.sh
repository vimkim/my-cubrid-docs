# CBRD-26659 campaign ticket 16 -- environment for the instrumentation install. Source this file.
# Everything here points at ticket-16-owned paths. The pinned install (~/.cub/install/oos-baseline-f4299ac0c)
# is never referenced.
export T16=/home/vimkim/.cub/campaign/cbrd-26659/ticket16
export CUBRID=/home/vimkim/.cub/install/oos-instr-f4299ac0c/debug_gcc
export CUBRID_DATABASES=$T16/db
export PATH=$CUBRID/bin:$PATH
export LD_LIBRARY_PATH=$CUBRID/lib:$CUBRID/cci/lib
export T16_PORT=26671
export T16_BROKER_PORTS="33140 33141 33142"
mkdir -p "$CUBRID_DATABASES"
[ -f "$CUBRID_DATABASES/databases.txt" ] || : > "$CUBRID_DATABASES/databases.txt"

# t16_conf <fault_injection_ids or ""> [extra lines...]: rewrite $CUBRID/conf/cubrid.conf from the template.
t16_conf () {
  local ids="$1"; shift || true
  {
    cat "$T16/conf/cubrid.conf.template"
    if [ -n "$ids" ]; then printf "fault_injection_ids=%s\n" "$ids"; fi
    for l in "$@"; do printf "%s\n" "$l"; done
  } > "$CUBRID/conf/cubrid.conf"
}

# t16_mark <name>: timestamp marker; t16_acks <name>: acknowledgement lines written since the marker.
t16_mark () { touch "$T16/logs/.mark.$1"; sleep 1; }
t16_acks () { find "$CUBRID/log" -name "*.err" -newer "$T16/logs/.mark.$1" -print0 2>/dev/null | xargs -0 grep -H "FAULT INJECTION ACK" 2>/dev/null || true; }
t16_errlogs () { find "$CUBRID/log" -name "*.err" -newer "$T16/logs/.mark.$1" 2>/dev/null; }

# t16_identity: version string and library hashes of the install under test (loader env set above).
t16_identity () {
  echo "CUBRID=$CUBRID"; "$CUBRID/bin/cubrid_rel" | head -1
  sha256sum "$CUBRID/lib/libcubrid.so" "$CUBRID/lib/libcubridsa.so" "$CUBRID/bin/cub_server" "$CUBRID/bin/csql"
}

# t16_ports_free: verify the campaign ports for this ticket are free; prints the ss check.
t16_ports_free () {
  local busy=0
  for p in $T16_PORT $T16_BROKER_PORTS; do
    if ss -ltn | awk "{print \$4}" | grep -qE ":$p\$"; then echo "PORT $p BUSY"; busy=1; else echo "port $p free"; fi
  done
  return $busy
}
