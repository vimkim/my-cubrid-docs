#!/bin/bash
# usage: run1.sh <head|base> <tag> [scenario-subdir under sql/, empty = whole shard]
set -u
R=/mnt/nvme/data-5/tmp/claude-1000/-home-vimkim-gh-cb-CBRD-28102-sysop-postpone/5ad80319-d102-4d58-b5db-dbf9636be283/scratchpad/repro-cci
which=$1 tag=$2 scen=${3:-}
out=$R/runs/$which/$tag
mkdir -p "$out"; touch "$out/ctp.out.start"
envs=()
[ -n "$scen" ] && envs+=(-e TEST_SCENARIO=/home/cubrid-testcases/sql/$scen)
name=repro-cci-$which-$tag
podman rm -f "$name" >/dev/null 2>&1
date -u +%FT%TZ > "$out/host_start"
podman run --name "$name" --init --hostname cirepro --ulimit core=-1 --shm-size=2g \
  -v "$R/cibuild/$which/CUBRID:/home/CUBRID:O" \
  -v "$R/ctx/cubrid-testtools:/home/cubrid-testtools:O" \
  -v "$R/ctx/tc-shard09:/home/cubrid-testcases:O" \
  -v "$out:/out" -v "$R/scripts/incontainer.sh:/incontainer.sh:ro" \
  "${envs[@]}" -e RUN_LIMIT="${RUN_LIMIT:-3000}" -e CIRCLE_NODE_INDEX=09 \
  --entrypoint /bin/bash docker.io/cubridci/cubridci:test_rl8.10 /incontainer.sh \
  </dev/null > "$out/podman.log" 2>&1
echo "podman rc=$?" >> "$out/podman.log"
date -u +%FT%TZ > "$out/host_end"
podman rm -f "$name" >/dev/null 2>&1
