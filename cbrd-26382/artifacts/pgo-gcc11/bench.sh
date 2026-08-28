#!/usr/bin/env bash
# usage: bench.sh <variantA> <variantB> <sessions_per_variant> <queries_per_session> <results_csv>
# Interleaves variants session-by-session (A,B,A,B,...) so slow host drift
# affects both variants equally. Each session is a fresh server start/stop.
set -euo pipefail
script_dir=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
a=${1:?variantA}
b=${2:?variantB}
sessions=${3:?sessions per variant}
queries=${4:?queries per session}
out=${5:?results csv}

if [ ! -f "$out" ]; then
  echo "variant,elapsed_sec,count,timestamp" > "$out"
fi

for i in $(seq "$sessions"); do
  echo "[bench] round $i/$sessions variant $a"
  bash "$script_dir/run-sample.sh" "$a" "$queries" "$out"
  echo "[bench] round $i/$sessions variant $b"
  bash "$script_dir/run-sample.sh" "$b" "$queries" "$out"
done
echo "[bench] done -> $out"
