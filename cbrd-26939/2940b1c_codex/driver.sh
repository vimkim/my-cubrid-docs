#!/bin/bash
set -eu
ulimit -c 0
if [ "${1:-}" = preflight ]; then exit 0; fi
attempt=${1:?attempt label required}
[[ "$attempt" =~ ^[a-z0-9-]+$ ]] || exit 2
work=/mnt/$attempt
mkdir "$work"
cp /mnt/delete-template.sh "$work/cbrd_27064.sh"
cp /mnt/baseline-case/cdc_extract.c "$work/"
: > /mnt/databases/databases.txt
cd "$work"
set +e
bash cbrd_27064.sh > output.log 2>&1
rc=$?
set -e
cat cbrd_27064.result
exit "$rc"
