^[[36;1mecho "=== summary ==="^[[0m
^[[36;1mcat "$GITHUB_STEP_SUMMARY"^[[0m
^[[36;1m^[[0m
^[[36;1m# Guard 3 of 3: a shard dying whole is invisible to guard 2.^[[0m
^[[36;1mrc=0^[[0m
^[[36;1mif [ "$DONE_N" -ne "$PLANNED" ]; then^[[0m
^[[36;1m  echo "::error::only $DONE_N of $PLANNED shards published a result; the rest died whole"^[[0m
^[[36;1m  rc=1^[[0m
^[[36;1mfi^[[0m
^[[36;1mif [ "$covered" -lt "$TOTAL" ]; then^[[0m
^[[36;1m  echo "::error::only $covered of $TOTAL cases were handled; cases went missing"^[[0m
^[[36;1m  rc=1^[[0m
^[[36;1mfi^[[0m
^[[36;1mif [ "$READ_N" -ne "$PLANNED" ]; then^[[0m
^[[36;1m  echo "::error::only $READ_N of $PLANNED shards recorded a build provenance; the rest died before mounting"^[[0m
^[[36;1m  rc=1^[[0m
^[[36;1mfi^[[0m
^[[36;1mcase "$PROV_REASON" in^[[0m
^[[36;1m  ok) ;;^[[0m
^[[36;1m  mixed)^[[0m
^[[36;1m    echo "::error::shards read different builds (run_id $PROV_UNIQ distinct). The artifact changed mid-pipeline"^[[0m
^[[36;1m    rc=1 ;;^[[0m
^[[36;1m  mismatch)^[[0m
^[[36;1m    echo "::error::every shard read the same build, but not the one from the run plan verified($BRID)"^[[0m
^[[36;1m    rc=1 ;;^[[0m
^[[36;1m  *)^[[0m
^[[36;1m    echo "::error::no shard recorded a build provenance"^[[0m
^[[36;1m    rc=1 ;;^[[0m
^[[36;1mesac^[[0m
^[[36;1mif [ "$TCREAD_N" -ne "$PLANNED" ]; then^[[0m
^[[36;1m  echo "::error::only $TCREAD_N of $PLANNED shards recorded a tc provenance"^[[0m
^[[36;1m  rc=1^[[0m
^[[36;1mfi^[[0m
^[[36;1mcase "$TC_REASON" in^[[0m
^[[36;1m  ok) ;;^[[0m
^[[36;1m  mixed)^[[0m
^[[36;1m    echo "::error::shards saw different testcases ($TC_UNIQ distinct). That disagrees with the split list"^[[0m
^[[36;1m    rc=1 ;;^[[0m
^[[36;1m  mismatch)^[[0m
^[[36;1m    echo "::error::every shard is the same, but not the commit plan chose($TC_SHA)"^[[0m
^[[36;1m    rc=1 ;;^[[0m
^[[36;1m  *)^[[0m
^[[36;1m    echo "::error::no shard recorded a tc provenance"^[[0m
^[[36;1m    rc=1 ;;^[[0m
^[[36;1mesac^[[0m
^[[36;1mif [ "$FAIL_SUM" -gt 0 ]; then^[[0m
^[[36;1m  echo "::error::$FAIL_SUM failed"^[[0m
^[[36;1m  rc=1^[[0m
^[[36;1mfi^[[0m
^[[36;1m[ "$rc" -eq 0 ] && echo "completed with no failures."^[[0m
^[[36;1mexit $rc^[[0m
shell: bash --noprofile --norc -e -o pipefail {0}
env:
  CI_ROOT: /home/build-cache/gha-ci
  CI_BUILD_ROOT: /home/build-cache/gha-ci/builds
  TIMINGS: /home/build-cache/gha-ci/timings/shell.tsv
  STAMPS: /home/build-cache/gha-ci/runs/33955055682/stamps
  BUILD_SENTINEL: .complete
  BUILD_META: .gha-ci-build.meta
  ARTIFACT_URL_BASE: http://192.168.1.48:30080
  RUNDIR: /home/build-cache/gha-ci/runs/33955055682
  TOTAL: 3274
  BUILD_NS: pr
  TIMED: 3244
  SHA: 2940b1cfbc3c2d4d0fac3f9244a960350debd380
  BRID: 33843986856
  PLANNED: 50
  DONE_N: 50
  READ_N: 50
  EXEC_SUM: 3244
  SUCC_SUM: 3241
  FAIL_SUM: 3
  SKIP_SUM: 30
  FAILED_N: 3
  PROV_REASON: ok
  PROV_UNIQ: 1
  PROV_THIS: no
  TC_REASON: ok
  TC_UNIQ: 1
  TCREAD_N: 50
  TC_SHA: 212149852ad82d6173f7f7fcb6ced8577991df30
  TC_BRANCH: tc/pr-6864
  RERUN_FROM: 
  C_QUEUE: 33s (0.6m)
  C_BUILD: 2s (0.0m)
  C_PLAN: 15s (0.2m)
  C_SMAX: 1784s (29.7m)
  C_SMED: 1648s (27.5m)
  C_SPAN: 1831s (30.5m)
  C_TOTAL: 1988s (33.1m)
##[endgroup]
##[group]Run '/home/runner/k8s/index.js'
shell: /home/runner/externals/node20/bin/node {0}
##[endgroup]
=== summary ===
## gha-ci: shell suite

### Coverage

| item | value |
|---|---|
| selected cases | 3274 |
| shards | planned 50 / published 50 OK |
| run | 3244 |
| skipped | 30 |
| handled | 3274 / 3274 OK |
| passed | 3241 |
| **failed** | **3** |
| cases split by measured timings | 3244 |

### Build provenance

| item | value |
|---|---|
| build SHA | `2940b1cfbc3c2d4d0fac3f9244a960350debd380` |
| build namespace | `pr` |
| built by run | `33843986856` (this run `33955055682`) reused |
| shards that read the meta inside the mounted CUBRID | 50 / 50 OK |
| did every shard read the same build | OK all the same |

Provenance is read through the overlay the shard actually mounted, not through hostPath.

### Testcase provenance

| item | value |
|---|---|
| tc branch | `tc/pr-6864` |
| tc commit | `212149852ad82d6173f7f7fcb6ced8577991df30` |
| shards that recorded a tc provenance | 50 / 50 OK |
| same commit across shards | OK all the same |

### Shards and wall clock

| stage | time |
|---|---|
| queue (run start to build start) | 33s (0.6m) |
| build | 2s (0.0m) |
| split | 15s (0.2m) |
| longest shard | 1784s (29.7m) |
| median shard | 1648s (27.5m) |
| shard span (first start to last end) | 1831s (30.5m) |
| **total (run start to collect)** | **1988s (33.1m)** |

### Failed cases (3)

Source: the `<testcase>` entries carrying a `<failure>` in each shard's `test-shell.xml`

| shard | case |
|---|---|
| 26 | `shell/_36_damson/cbrd_23608_tde/log_enc_04/cases/log_enc_04.sh` |
| 48 | `shell/_37_elderberry/cbrd_23842_cdc/bug/cbrd_27064/cases/cbrd_27064.sh` |
| 49 | `shell/_37_elderberry/cbrd_23842_cdc/bug/cbrd_27075/cases/cbrd_27075.sh` |

---
[Artifacts](http://192.168.1.48:30080/runs/33955055682/)

Internal network only. The run directory is pruned 7 days after the run.
##[error]3 failed
##[error]Error: failed to run script step: command terminated with non-zero exit code: error executing command [sh -e /__w/_temp/7dcf2a30-a907-11f1-ba1f-3dfad2f8e53c.sh], exit code 1
##[error]Process completed with exit code 1.
##[error]Executing the custom container implementation failed. Please contact your self hosted runner administrator.
collect	Clean up the CTP seed	﻿2026-09-05T08:55:06.6557127Z ##[group]Run set -eo pipefail
^[[36;1mset -eo pipefail^[[0m
^[[36;1mseed="$RUNDIR/testtools"^[[0m
^[[36;1mif [ "${FAIL_SUM:-1}" != '0' ] || [ "${DONE_N:-0}" != "${PLANNED:-1}" ]; then^[[0m
^[[36;1m  echo "kept for a re-run: $seed"^[[0m
^[[36;1m  echo "  failed $FAIL_SUM / shards published ${DONE_N} of ${PLANNED}"^[[0m
^[[36;1m  exit 0^[[0m
^[[36;1mfi^[[0m
^[[36;1mif [ -d "$seed" ]; then^[[0m
^[[36;1m  du -sh "$seed" 2>/dev/null || true^[[0m
^[[36;1m  rm -rf "$seed" "${seed}.tmp.${GITHUB_RUN_ID}" "${seed}.old"^[[0m
^[[36;1m  echo "removed: $seed"^[[0m
^[[36;1melse^[[0m
^[[36;1m  echo "nothing to remove: $seed"^[[0m
^[[36;1mfi^[[0m
shell: bash --noprofile --norc -e -o pipefail {0}
env:
  CI_ROOT: /home/build-cache/gha-ci
  CI_BUILD_ROOT: /home/build-cache/gha-ci/builds
  TIMINGS: /home/build-cache/gha-ci/timings/shell.tsv
  STAMPS: /home/build-cache/gha-ci/runs/33955055682/stamps
  BUILD_SENTINEL: .complete
  BUILD_META: .gha-ci-build.meta
  ARTIFACT_URL_BASE: http://192.168.1.48:30080
  RUNDIR: /home/build-cache/gha-ci/runs/33955055682
  TOTAL: 3274
  BUILD_NS: pr
  FAIL_SUM: 3
  DONE_N: 50
  PLANNED: 50
##[endgroup]
##[group]Run '/home/runner/k8s/index.js'
shell: /home/runner/externals/node20/bin/node {0}
##[endgroup]
kept for a re-run: /home/build-cache/gha-ci/runs/33955055682/testtools
  failed 3 / shards published 50 of 50
collect	Stop containers	﻿2026-09-05T08:55:06.9564138Z ##[group]Run '/home/runner/k8s/index.js'
shell: /home/runner/externals/node20/bin/node {0}
##[endgroup]
collect	Complete job	﻿2026-09-05T08:55:07.2154436Z Cleaning up orphan processes
