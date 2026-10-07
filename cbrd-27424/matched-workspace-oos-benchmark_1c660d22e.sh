#!/usr/bin/env bash
# Parameterized replay of the five alternating pairs recorded on 2026-10-07.
# Usage: bash matched-workspace-oos-benchmark_1c660d22e.sh SOURCE_ROOT INSTALL_ROOT NEW_OUTPUT_ROOT [CPU]
# INSTALL_ROOT must contain separately built direct/ and restored/ installations.
set -euo pipefail
source_root=$(realpath "${1:?source root required}")
install_root=$(realpath "${2:?installation root required}")
output_root=$(realpath -m "${3:?new output root required}")
cpu=${4:-79}
mkdir "$output_root"
printf 'pair,position,side,start_utc,end_utc,load_start,load_end\n' > "$output_root/order.csv"
for pair in 1 2 3 4 5; do
  if (( pair % 2 )); then
    sides=(direct restored)
  else
    sides=(restored direct)
  fi
  position=0
  for side in "${sides[@]}"; do
    position=$((position + 1))
    printf -v sample_name 'pair-%02d-%s' "$pair" "$side"
    if [[ $side == direct ]]; then
      label=direct-a142503dc
    else
      label=restored-1c660d22e
    fi
    start_utc=$(date -u +%FT%TZ)
    load_start=$(cut -d' ' -f1 /proc/loadavg)
    taskset -c "$cpu" bash "$source_root/unit_tests/oos/scripts/benchmark_workspace_oos.sh" \
      "$install_root/$side" "$output_root/$sample_name" "$label" 1
    end_utc=$(date -u +%FT%TZ)
    load_end=$(cut -d' ' -f1 /proc/loadavg)
    printf '%s,%s,%s,%s,%s,%s,%s\n' "$pair" "$position" "$side" "$start_utc" "$end_utc" \
      "$load_start" "$load_end" >> "$output_root/order.csv"
  done
done
