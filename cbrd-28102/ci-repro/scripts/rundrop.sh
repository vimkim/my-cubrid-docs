#!/bin/bash
# usage: rundrop.sh <head|base> <tag>
R=/mnt/nvme/data-5/tmp/claude-1000/-home-vimkim-gh-cb-CBRD-28102-sysop-postpone/5ad80319-d102-4d58-b5db-dbf9636be283/scratchpad/repro-cci
out=$R/runs/drop-$1/$2; mkdir -p $out
podman run --rm --init --hostname cirepro -v "$R/cibuild/$1/CUBRID:/home/CUBRID:O" -v "$out:/out" \
  -v "$R/scripts/dropstorm.sh:/dropstorm.sh.run:ro" -v "$R/scripts/dropstorm.sql:/dropstorm.sql:ro" \
  --entrypoint /bin/bash docker.io/cubridci/cubridci:test_rl8.10 /dropstorm.sh.run </dev/null > $out/podman.log 2>&1
date -u +%FT%TZ > $out/host_end
