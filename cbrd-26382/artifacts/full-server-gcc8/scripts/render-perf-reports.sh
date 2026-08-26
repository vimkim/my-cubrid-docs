#!/usr/bin/env bash
set -euo pipefail

root=/home/vimkim/gh/cb/cbrd-26382-results/bench/pmu
results=/home/vimkim/gh/cb/cbrd-26382-results

for variant in qa-2029 A B C; do
  perf buildid-cache -a "$results/$variant/CUBRID/lib/libcubrid.so.11.5"
done

for variant in qa-2029 A B C; do
  perf report --stdio \
    -i "$root/$variant-profile.perf.data" \
    --no-children --sort dso,symbol --percent-limit 0.5 \
    >"$root/$variant-profile.report.txt"
done
