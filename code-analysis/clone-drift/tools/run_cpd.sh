#!/usr/bin/env bash
# usage: run_cpd.sh <cubrid-src-root> <outdir> [min-tokens]
set -euo pipefail
SRC=${1:?}; OUT=${2:?}; MIN=${3:-120}
mkdir -p "$OUT"
cd "$SRC"
find src -type f \( -name '*.c' -o -name '*.cpp' -o -name '*.h' -o -name '*.hpp' \) \
  ! -path 'src/base/jisx0212.h' ! -path 'src/base/ksc5601.h' ! -path 'src/base/CRC.h' \
  | sort > "$OUT/files.txt"
pmd cpd --dir src --language cpp --minimum-tokens "$MIN" --format xml \
  --no-fail-on-violation --no-fail-on-error > "$OUT/cpd-plain.xml" 2> "$OUT/cpd-plain.err"
pmd cpd --file-list "$OUT/files.txt" --language cpp --minimum-tokens "$MIN" \
  --ignore-identifiers --ignore-literals --format xml \
  --no-fail-on-violation --no-fail-on-error > "$OUT/cpd-ignore.xml" 2> "$OUT/cpd-ignore.err"
lizard src -l cpp --csv > "$OUT/lizard.csv" 2> "$OUT/lizard.err" || true
