#!/bin/bash
# Driver for u1_growth_lock.sh: REPS repetitions, revision order rotated each repetition so
# host-load drift on the shared machine falls on every revision.
# Usage: u1_run_all.sh OUTDIR [REPS]
set -uo pipefail
out=$(realpath -m "${1:?outdir}"); reps=${2:-5}
here=$(cd "$(dirname "$0")" && pwd)
declare -A inst=(
  [base]=$HOME/.cub/install/u1perf-base-c255c7c3b/release_gcc
  [mid]=$HOME/.cub/install/u1perf-mid-e01d8d576/release_gcc
  [head]=$HOME/.cub/install/u1perf-head-8e139f4db/release_gcc
)
declare -A port=([base]=35101 [mid]=35102 [head]=35103)
orders=("base mid head" "head base mid" "mid head base")
mkdir -p "$out"
for r in $(seq 1 "$reps"); do
  for l in ${orders[$(( (r - 1) % 3 ))]}; do
    echo "$(date +%T) rep $r $l start load=$(cut -d' ' -f1-3 /proc/loadavg)"
    PORT=${port[$l]} "$here/u1_growth_lock.sh" "${inst[$l]}" "$out" "$l" "$r" </dev/null > "$out/run-$l-$r.log" 2>&1
    echo "$(date +%T) rep $r $l rc=$?"
  done
done
