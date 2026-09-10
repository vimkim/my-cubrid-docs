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
  CI_ROOT: /home/gha-ci
  CI_BUILD_ROOT: /home/gha-ci/builds
  TIMINGS: /home/gha-ci/timings/shell.tsv
  STAMPS: /home/gha-ci/runs/34186373809/stamps
  BUILD_SENTINEL: .complete
  BUILD_META: .gha-ci-build.meta
  ARTIFACT_URL_BASE: http://192.168.1.48:30080
  RUNDIR: /home/gha-ci/runs/34186373809
  TOTAL: 3274
  BUILD_NS: pr
  TIMED: 3244
  SHA: 2940b1cfbc3c2d4d0fac3f9244a960350debd380
  BRID: 34186373809
  PLANNED: 50
  DONE_N: 50
  READ_N: 50
  EXEC_SUM: 3244
  SUCC_SUM: 3242
  FAIL_SUM: 2
  SKIP_SUM: 30
  FAILED_N: 2
  PROV_REASON: ok
  PROV_UNIQ: 1
  PROV_THIS: yes
  TC_REASON: ok
  TC_UNIQ: 1
  TCREAD_N: 50
  TC_SHA: 01af62db73351ea3fdb445ccd03a19c39084d1cc
  TC_BRANCH: tc/pr-6864
  RERUN_FROM: 
  C_QUEUE: 81s (1.4m)
  C_BUILD: 599s (10.0m)
  C_PLAN: 17s (0.3m)
  C_SMAX: 2087s (34.8m)
  C_SMED: 1683s (28.1m)
  C_SPAN: 2203s (36.7m)
  C_TOTAL: 3028s (50.5m)
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
| passed | 3242 |
| **failed** | **2** |
| cases split by measured timings | 3244 |

### Build provenance

| item | value |
|---|---|
| build SHA | `2940b1cfbc3c2d4d0fac3f9244a960350debd380` |
| build namespace | `pr` |
| built by run | `34186373809` (this run `34186373809`) OK |
| shards that read the meta inside the mounted CUBRID | 50 / 50 OK |
| did every shard read the same build | OK all the same |

Provenance is read through the overlay the shard actually mounted, not through hostPath.

### Testcase provenance

| item | value |
|---|---|
| tc branch | `tc/pr-6864` |
| tc commit | `01af62db73351ea3fdb445ccd03a19c39084d1cc` |
| shards that recorded a tc provenance | 50 / 50 OK |
| same commit across shards | OK all the same |

### Shards and wall clock

| stage | time |
|---|---|
| queue (run start to build start) | 81s (1.4m) |
| build | 599s (10.0m) |
| split | 17s (0.3m) |
| longest shard | 2087s (34.8m) |
| median shard | 1683s (28.1m) |
| shard span (first start to last end) | 2203s (36.7m) |
| **total (run start to collect)** | **3028s (50.5m)** |

### Failed cases (2)

Source: the `<testcase>` entries carrying a `<failure>` in each shard's `test-shell.xml`

| shard | case |
|---|---|
| 31 | `shell/_06_issues/_11_1h/bug_bts_4633/cases/bug_bts_4633.sh` |
| 31 | `shell/_37_elderberry/cbrd_23842_cdc/bug/cbrd_27064/cases/cbrd_27064.sh` |

---
[Artifacts](http://192.168.1.48:30080/runs/34186373809/) · [build log](http://192.168.1.48:30080/builds/pr/2940b1cfbc3c2d4d0fac3f9244a960350debd380/debug/build.log)

Internal network only. The run directory is pruned 7 days after the run.
##[error]2 failed
##[error]Error: failed to run script step: command terminated with non-zero exit code: error executing command [sh -e /__w/_temp/07924120-ab43-11f1-94e6-17c310586d34.sh], exit code 1
##[error]Process completed with exit code 1.
##[error]Executing the custom container implementation failed. Please contact your self hosted runner administrator.
collect	The log of each failed case	﻿2026-09-08T05:06:20.4253361Z ##[group]Run set -eo pipefail
^[[36;1mset -eo pipefail^[[0m
^[[36;1m[ "${FAILED_N:-0}" -gt 0 ] || exit 0^[[0m
^[[36;1m^[[0m
^[[36;1m# Same 50 the table above lists. Sharing the budget out over them lets a^[[0m
^[[36;1m# run with one failure show that log whole, which is the common case.^[[0m
^[[36;1mshown=$FAILED_N^[[0m
^[[36;1m[ "$shown" -gt 50 ] && shown=50^[[0m
^[[36;1mbudget=900000^[[0m
^[[36;1m# 512 for the <details> wrapper of each case, so that the cases which^[[0m
^[[36;1m# all reach their share still add up to less than the budget.^[[0m
^[[36;1mcase_max=$((budget / shown - 512))^[[0m
^[[36;1m[ "$case_max" -gt 131072 ] && case_max=131072^[[0m
^[[36;1mhead_b=$((case_max / 2))^[[0m
^[[36;1mtail_b=$((case_max - head_b))^[[0m
^[[36;1mecho "cases $FAILED_N / shown $shown / per case $case_max bytes"^[[0m
^[[36;1m^[[0m
^[[36;1mesc() { sed -e 's/&/\&amp;/g' -e 's/</\&lt;/g' -e 's/>/\&gt;/g' "$1"; }^[[0m
^[[36;1m^[[0m
^[[36;1mbase="$ARTIFACT_URL_BASE/${RUNDIR#$CI_ROOT/}"^[[0m
^[[36;1m{^[[0m
^[[36;1m  echo "### The log of each failed case"^[[0m
^[[36;1m  echo^[[0m
^[[36;1m  echo "What CTP wrote in the case's \`<failure>\`, trimmed to fit. Untrimmed, it is in the shard's \`test-shell.xml\`."^[[0m
^[[36;1m  echo^[[0m
^[[36;1m} >> "$GITHUB_STEP_SUMMARY"^[[0m
^[[36;1m^[[0m
^[[36;1mused=0^[[0m
^[[36;1mi=0^[[0m
^[[36;1mleft=0^[[0m
^[[36;1mwhile IFS=$'\t' read -r shard name; do^[[0m
^[[36;1m  i=$((i + 1))^[[0m
^[[36;1m  [ "$i" -le "$shown" ] || { left=$((left + 1)); continue; }^[[0m
^[[36;1m  log="/tmp/failed-logs/$i.log"^[[0m
^[[36;1m  {^[[0m
^[[36;1m    echo "<details>"^[[0m
^[[36;1m    echo "<summary>shard $shard &middot; <code>$name</code> &middot; <a href=\"$base/results/$shard/test-shell.xml\">full log</a></summary>"^[[0m
^[[36;1m    echo^[[0m
^[[36;1m    # <pre> opens its own line: a blank line inside the log would end the^[[0m
^[[36;1m    # HTML block that <details> opened, and the rest would render as text.^[[0m
^[[36;1m    echo "<pre>"^[[0m
^[[36;1m  } > /tmp/block^[[0m
^[[36;1m  if [ ! -f "$log" ]; then^[[0m
^[[36;1m    echo "(this case left no log in the XML)" >> /tmp/block^[[0m
^[[36;1m  else^[[0m
^[[36;1m    # The 1 MiB is counted after escaping, so cut the escaped log, not^[[0m
^[[36;1m    # the log: a share measured before escaping is not the share spent.^[[0m
^[[36;1m    esc "$log" > /tmp/esc^[[0m
^[[36;1m    sz=$(wc -c < /tmp/esc)^[[0m
^[[36;1m    if [ "$sz" -le "$case_max" ]; then^[[0m
^[[36;1m      cat /tmp/esc >> /tmp/block^[[0m
^[[36;1m    else^[[0m
^[[36;1m      # sed drops the line the byte cut split, so <pre> holds whole^[[0m
^[[36;1m      # lines and no entity is left half written.^[[0m
^[[36;1m      head -c "$head_b" /tmp/esc | sed '$d' >> /tmp/block^[[0m
^[[36;1m      printf '\n... %d KB of the middle is not here ...\n\n' $(((sz - head_b - tail_b) / 1024)) >> /tmp/block^[[0m
^[[36;1m      tail -c "$tail_b" /tmp/esc | sed '1d' >> /tmp/block^[[0m
^[[36;1m    fi^[[0m
^[[36;1m  fi^[[0m
^[[36;1m  {^[[0m
^[[36;1m    echo "</pre>"^[[0m
^[[36;1m    echo^[[0m
^[[36;1m    echo "</details>"^[[0m
^[[36;1m    echo^[[0m
^[[36;1m  } >> /tmp/block^[[0m
^[[36;1m  size=$(wc -c < /tmp/block)^[[0m
^[[36;1m  if [ $((used + size)) -gt "$budget" ]; then^[[0m
^[[36;1m    left=$((left + 1))^[[0m
^[[36;1m    continue^[[0m
^[[36;1m  fi^[[0m
^[[36;1m  cat /tmp/block >> "$GITHUB_STEP_SUMMARY"^[[0m
^[[36;1m  used=$((used + size))^[[0m
^[[36;1mdone < /tmp/failed.list^[[0m
^[[36;1m^[[0m
^[[36;1mif [ "$left" -gt 0 ]; then^[[0m
^[[36;1m  echo "_$left more cases failed. Their logs are in each shard's \`test-shell.xml\`, under [Artifacts]($base/)._" >> "$GITHUB_STEP_SUMMARY"^[[0m
^[[36;1mfi^[[0m
^[[36;1mecho "wrote $((i - left)) of $i case logs, $used bytes"^[[0m
shell: bash --noprofile --norc -e -o pipefail {0}
env:
  CI_ROOT: /home/gha-ci
  CI_BUILD_ROOT: /home/gha-ci/builds
  TIMINGS: /home/gha-ci/timings/shell.tsv
  STAMPS: /home/gha-ci/runs/34186373809/stamps
  BUILD_SENTINEL: .complete
  BUILD_META: .gha-ci-build.meta
  ARTIFACT_URL_BASE: http://192.168.1.48:30080
  RUNDIR: /home/gha-ci/runs/34186373809
  TOTAL: 3274
  BUILD_NS: pr
  FAILED_N: 2
##[endgroup]
##[group]Run '/home/runner/k8s/index.js'
shell: /home/runner/externals/node20/bin/node {0}
##[endgroup]
cases 2 / shown 2 / per case 131072 bytes
wrote 2 of 2 case logs, 124836 bytes
collect	Clean up the CTP seed	﻿2026-09-08T05:06:21.2842393Z ##[group]Run set -eo pipefail
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
  CI_ROOT: /home/gha-ci
  CI_BUILD_ROOT: /home/gha-ci/builds
  TIMINGS: /home/gha-ci/timings/shell.tsv
  STAMPS: /home/gha-ci/runs/34186373809/stamps
  BUILD_SENTINEL: .complete
  BUILD_META: .gha-ci-build.meta
  ARTIFACT_URL_BASE: http://192.168.1.48:30080
  RUNDIR: /home/gha-ci/runs/34186373809
  TOTAL: 3274
  BUILD_NS: pr
  FAIL_SUM: 2
  DONE_N: 50
  PLANNED: 50
##[endgroup]
##[group]Run '/home/runner/k8s/index.js'
shell: /home/runner/externals/node20/bin/node {0}
##[endgroup]
kept for a re-run: /home/gha-ci/runs/34186373809/testtools
  failed 2 / shards published 50 of 50
collect	Stop containers	﻿2026-09-08T05:06:21.6120068Z ##[group]Run '/home/runner/k8s/index.js'
shell: /home/runner/externals/node20/bin/node {0}
##[endgroup]
collect	Complete job	﻿2026-09-08T05:06:21.9053705Z Cleaning up orphan processes
