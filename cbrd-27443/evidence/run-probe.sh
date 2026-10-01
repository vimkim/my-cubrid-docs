#!/usr/bin/env bash
set -euo pipefail
# Usage: bash run-probe.sh /absolute/CUBRID/install /absolute/output-dir MODE
install_root=$(realpath "$1")
output_dir=$(realpath -m "$2")
mode=$3
script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
mkdir -p "$output_dir"
mkdir -p "$HOME/.cache"
run_dir=$(mktemp -d "$HOME/.cache/cbrd27443-${mode}.XXXXXX")
mkdir -p "$run_dir/root"/{conf,databases,log,tmp,var}
for asset in bin lib msg locales timezones vm jdbc; do
  ln -s "$install_root/$asset" "$run_dir/root/$asset"
done
cp "$install_root/conf/"* "$run_dir/root/conf/"
cat > "$run_dir/root/conf/cubrid.conf" <<'CONF'
[service]
service=server
server=fdtest
[common]
cubrid_port_id=35443
ha_mode=off
data_buffer_size=64M
log_buffer_size=4M
CONF
: > "$run_dir/root/databases/databases.txt"
# Private /tmp also isolates Unix socket names. PID namespace init exiting kills leftovers.
# Mount namespaces are private: these mounts do not affect the host.
export CUBRID="$run_dir/root" CUBRID_DATABASES="$run_dir/root/databases"
export PATH="$CUBRID/bin:$PATH" LD_LIBRARY_PATH="$CUBRID/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
unset CUBRID_NO_DAEMON
export PROBE_HOST_PID_NS
PROBE_HOST_PID_NS=$(readlink /proc/self/ns/pid)
printf 'Runtime directory: %s\n' "$run_dir"
# Positional parameters below belong to the namespace shell.
# shellcheck disable=SC2016
unshare --user --map-root-user --mount --net --pid --fork --mount-proc \
  bash -c 'set -e; mount --make-rprivate /; mount -t tmpfs tmpfs /tmp; ip link set lo up; python3 "$1/namespace-init.py" "$1/probe.py" "$2" "$3"' \
  bash "$script_dir" "$mode" "$output_dir/$mode.json"
# Volumes and diagnostic files are retained in run_dir; the private namespace is gone.
