#!/bin/bash
# Alternate baseline and change, REPEATS each, same workload; results in OUT/results.csv.
set -u
S=$(dirname "$(realpath "$0")")
BASE=${BASE:?baseline install}
NEW=${NEW:?change install}
OUT=${OUT:?output dir}
REPEATS=${REPEATS:-3}
mkdir -p "$OUT"
for r in $(seq 0 $((REPEATS - 1))); do
  for pair in "base:$BASE" "new:$NEW"; do
    label=${pair%%:*}
    inst=${pair#*:}
    echo "== $label rep $r $(date +%T)"
    timeout 1800 bash "$S/oos_update_churn.sh" "$inst" "$OUT" "$label" "$r" > "$OUT/$label-$r.log" 2>&1
    echo "   exit=$? $(date +%T)"
  done
done
