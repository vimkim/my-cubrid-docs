#!/bin/bash
# Runs base, new and fix in a rotated order per repeat so drift and load favor no arm, and records the
# 1-minute load average around each sample. Usage: OUT=.. REPEATS=.. MODE=churn|small|flush run3.sh
set -u
S=$(dirname "$(realpath "$0")")
B=/home/vimkim/gh/my-cubrid-docs/cbrd-27781/bench
OUT=${OUT:?}; REPEATS=${REPEATS:-12}; MODE=${MODE:?}
I=$HOME/.cub/install
arms=(base:$I/CBRD-27781-lat2-base/release_gcc new:$I/CBRD-27781-lat2-new/release_gcc fix:$I/CBRD-27781-lat2-fix/release_gcc)
mkdir -p "$OUT"; res="$OUT/results.csv"; [ -f "$res" ] || echo "label,rep,metric,value" > "$res"
load1 () { cut -d' ' -f1 /proc/loadavg; }
for r in $(seq 0 $((REPEATS - 1))); do
  for k in 0 1 2; do
    pair=${arms[$(( (k + r) % 3 ))]}; [ $((r / 3 % 2)) -eq 1 ] && pair=${arms[$(( (2 - k + r) % 3 ))]}
    label=${pair%%:*}; inst=${pair#*:}; l0=$(load1)
    echo "== $MODE $label rep $r $(date +%T) load $l0"
    case $MODE in
      churn) timeout 1800 bash "$B/oos_update_churn.sh" "$inst" "$OUT" "$label" "$r" ;;
      small) timeout 1800 bash "$S/oos_small_txn.sh" "$inst" "$OUT" "$label" "$r" ;;
      flush) timeout 1800 bash "$S/oos_flush_count.sh" "$inst" "$OUT" "$label" "$r" ;;
    esac > "$OUT/$label-$r.log" 2>&1
    rc=$?; l1=$(load1)
    printf '%s,%s,exit,%s\n%s,%s,load1_before,%s\n%s,%s,load1_after,%s\n' "$label" "$r" "$rc" "$label" "$r" "$l0" "$label" "$r" "$l1" >> "$res"
    echo "   exit=$rc $(date +%T) load $l1"
  done
done
