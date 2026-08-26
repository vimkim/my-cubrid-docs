#!/usr/bin/env bash
set -euo pipefail

script_dir=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
# shellcheck source=runtime-common.sh
source "$script_dir/runtime-common.sh"
load_results_root

root=$results_root/bench/pmu-pcores
perf_bin=${PERF_BIN:-perf}

for variant in qa-2029 A B C; do
  "$perf_bin" buildid-cache -a "$results_root/$variant/CUBRID/lib/libcubrid.so.11.5"
done

for variant in qa-2029 A B C; do
  "$perf_bin" report --stdio \
    -i "$root/$variant-profile.perf.data" \
    --no-children --sort dso,symbol --percent-limit 0.5 \
    >"$root/$variant-profile.report.txt"
done
