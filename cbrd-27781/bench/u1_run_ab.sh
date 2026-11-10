#!/bin/bash
# Focused base/head series for u1_growth_lock.sh: insert points only, strict A/B alternation,
# order flipped every repetition (ABBA...). Usage: u1_run_ab.sh OUTDIR [REPS]
set -uo pipefail
out=$(realpath -m "${1:?outdir}"); reps=${2:-10}
here=$(cd "$(dirname "$0")" && pwd)
declare -A inst=(
  [base]=$HOME/.cub/install/u1perf-base-c255c7c3b/release_gcc
  [head]=$HOME/.cub/install/u1perf-head-8e139f4db/release_gcc
)
declare -A port=([base]=35101 [head]=35103)
mkdir -p "$out"
for r in $(seq 1 "$reps"); do
  if (( r % 2 )); then order="base head"; else order="head base"; fi
  for l in $order; do
    echo "$(date +%T) rep $r $l start load=$(cut -d' ' -f1-3 /proc/loadavg)"
    CONC="${CONC:-16 32 64}" MIXED=" " PORT=${port[$l]} "$here/u1_growth_lock.sh" "${inst[$l]}" "$out" "$l" "$r" </dev/null > "$out/run-$l-$r.log" 2>&1
    echo "$(date +%T) rep $r $l rc=$?"
  done
done
