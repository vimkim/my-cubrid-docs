#!/usr/bin/env bash
# Reproduce every table in REPORT.md.  Steps run one after another; each uses at most 12 TLC
# workers.  Usage: bash run_all.sh OUT_ROOT   (OUT_ROOT must not exist)
set -euo pipefail
here=$(cd "$(dirname "$0")" && pwd)
out=${1:?usage: run_all.sh OUT_ROOT}
[ -e "$out" ] && { echo "$out exists" >&2; exit 2; }
mkdir -p "$out"
run() { python3 -I -B "$here/run.py" "$@"; }

bounded=cand_fullboot,cand_recheck,reuse,reuse_fast,reuse_norecheck,reuse_noreinit,hybrid,hybrid_cand
lazy=cand_lazy,reuse_lazy,reuse_nocheck

run --out "$out/1-main" --max-pages 4,5 --settings nocrash-quiet,nocrash-writes,crash-quiet --only "$bounded"
run --out "$out/2-lazy" --max-pages 4,5 --settings nocrash-quiet,crash-quiet --only "$lazy"
run --out "$out/3-lazy-writes" --max-pages 4 --settings nocrash-writes --only "$lazy"
run --out "$out/4-leaky" --max-pages 4 --settings nocrash-quiet,nocrash-writes,crash-quiet --only hybrid_leaky
run --out "$out/5-crash-writes" --max-pages 4 --settings crash-writes \
    --only cand_fullboot,cand_recheck,reuse,reuse_fast,reuse_norecheck,hybrid,hybrid_cand
run --out "$out/7-misfit" --misfit --max-pages 4,5 --settings nocrash-quiet,nocrash-writes,crash-quiet \
    --only cand_recheck,reuse,reuse_noreinit,hybrid,hybrid_cand
run --out "$out/8-misfit-crash-writes" --misfit --max-pages 4 --settings crash-writes --only reuse,reuse_noreinit
run --out "$out/9-relatch-any" --relatch-any --max-pages 4,5 --settings nocrash-quiet,nocrash-writes,crash-quiet \
    --only cand_recheck,reuse,hybrid_cand
# Last, because a design that reaches the cap at P4 explodes at P5: a bounded design has the
# same distinct-state count at P4 and P5 (page 5 is unreachable).
run --out "$out/6-crash-writes-P5" --max-pages 5 --settings crash-writes --only cand_recheck,reuse,hybrid_cand
