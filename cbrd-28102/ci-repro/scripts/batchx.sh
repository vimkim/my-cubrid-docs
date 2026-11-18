#!/bin/bash
# usage: batch.sh <head|base> <prefix> <count> <parallel> [scenario]
R=/mnt/nvme/data-5/tmp/claude-1000/-home-vimkim-gh-cb-CBRD-28102-sysop-postpone/5ad80319-d102-4d58-b5db-dbf9636be283/scratchpad/repro-cci
which=$1 prefix=$2 n=$3 par=$4 scen=${5:-}
seq -w 1 "$n" | xargs -P "$par" -I{} "$R/scripts/run1x.sh" "$which" "$prefix{}" "$scen"
echo "batch $which $prefix done $(date -u +%FT%TZ)"
