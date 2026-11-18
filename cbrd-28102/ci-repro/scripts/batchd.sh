#!/bin/bash
# usage: batchd.sh <label> <prefix> <count> <parallel> <install> [scenario]
R=/mnt/nvme/data-5/tmp/claude-1000/-home-vimkim-gh-cb-CBRD-28102-sysop-postpone/5ad80319-d102-4d58-b5db-dbf9636be283/scratchpad/repro-cci
seq -w 1 "$3" | xargs -P "$4" -I{} "$R/scripts/run1d.sh" "$1" "$2{}" "$5" "${6:-}"
echo "batch $1 $2 done $(date -u +%FT%TZ)"
