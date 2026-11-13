#!/usr/bin/env bash
# usage: run_all.sh <cubrid-src-root> <outdir> [min-tokens]
set -euo pipefail
HERE=$(cd "$(dirname "$0")" && pwd)
"$HERE/run_cpd.sh" "$1" "$2" "${3:-120}"
python3 -I "$HERE/rank_pairs.py" "$1" "$2"
python3 -I "$HERE/filter_pairs.py" "$1" "$2"
python3 -I "$HERE/name_twins.py" "$1" "$2"
