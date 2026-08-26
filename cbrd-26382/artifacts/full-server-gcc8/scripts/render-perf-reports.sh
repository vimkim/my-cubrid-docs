#!/usr/bin/env bash
set -euo pipefail

script_dir=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
# shellcheck source=runtime-common.sh
source "$script_dir/runtime-common.sh"
load_results_root

root=$results_root/bench/pmu

for variant in qa-2029 A B C; do
  perf buildid-cache -a "$results_root/$variant/CUBRID/lib/libcubrid.so.11.5"
done

for variant in qa-2029 A B C; do
  perf report --stdio \
    -i "$root/$variant-profile.perf.data" \
    --no-children --sort dso,symbol --percent-limit 0.5 \
    >"$root/$variant-profile.report.txt"
done
