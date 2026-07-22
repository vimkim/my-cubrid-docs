# PR #7391 `test_shell` Merge-Safety Report

## Executive Decision

**`test_shell` regression attribution: PASS.** PR [#7391](https://github.com/CUBRID/cubrid/pull/7391) has no new
failed test case relative to `feat/oos`. Sixteen of its 17 failures have affirmative evidence that they are not
CBRD-27006-specific. The remaining case, `bigPageSize`, is underdiagnosed because both CI records omit its failure body;
it is demonstrably pre-existing but cannot be assigned a definitive current root cause.

**Immediate merge decision: CONDITIONAL GO, not an unconditional GO.** The failed `test_shell` job is not a
PR-specific blocker if the `feat/oos` integration policy permits inherited baseline failures. Before merging, however,
the exact candidate should be synchronized with current `feat/oos` and rerun, and the PR's separate failing `test_sql`
and `code-style` checks must be resolved or independently waived. The current evidence is sufficient to waive the 17
shell failures as PR regressions; it is not sufficient to waive unrelated checks or certify the whole OOS branch for
`develop`.

One inherited failure, `cbrd_25365`, is a real OOS baseline server-crash defect. It does not make CBRD-27006 unsafe
relative to its base, but it remains a release-readiness risk for the later `feat/oos` -> `develop` merge.

---

## Scope and CI Identity

| Role | PR / branch direction | Tested engine commit | CircleCI job | Result |
|---|---|---|---|---|
| Current OOS baseline | [#6864](https://github.com/CUBRID/cubrid/pull/6864), `develop` <- `feat/oos` | `c2cbeaf9f08c767290cdf14c9af0726447c59a1b` | [`test_shell` 139543](https://circleci.com/gh/CUBRID/cubrid/139543) | 3,190 passed, 18 failed, 30 skipped |
| Change under review | [#7391](https://github.com/CUBRID/cubrid/pull/7391), `feat/oos` <- `CBRD-27006-oos-recdes-locality` | `3f40e134d0c5b3578fe60de6f1d9f5ca8d12f698` | [`test_shell` 138889](https://circleci.com/gh/CUBRID/cubrid/138889) | 3,191 passed, 17 failed, 30 skipped |

Both jobs were resolved from the PR's current head SHA through the GitHub commit status
`ci/circleci: test_shell`, then validated against CircleCI job metadata (`vcs_revision` and job name). No older job was
substituted for either current head.

This report decides whether PR #7391 caused its shell failures. It does not analyze the PR's failing `test_sql` job or
code-style job.

---

## Set Comparison

```text
PR #6864 current baseline: 18 failed
                         /            \
             16 common failures       2 baseline-only failures
                    |                 cbrd_23828, cbrd_25846
                    |
PR #7391: 17 failed = 16 common failures + cbrd_26403
```

| Set | Count | Finding |
|---|---:|---|
| Failed in both jobs | 16 | Fifteen have the same primary signature; `bigPageSize` has the same body-less failure record. All are inherited at the failed-TC level |
| Failed only in #6864 | 2 | The current testcase branch contains CBRD-26986 hash-join answers, but `feat/oos` commit `c2cbeaf9f0` predates the matching engine merge |
| Failed only in #7391 | 1 | Exact optimizer-cost baseline drift corrected in the testcase repository after job 138889 started |
| #7391 failures demonstrated to be caused by CBRD-27006 | **0** | No new shell regression found |
| Underdiagnosed but reproduced on the baseline | **1** | `bigPageSize`; non-regression is established, current causality is not |

The 16 common cases were compared using their complete CircleCI test records, not names alone. For 15 cases, dynamic
values such as hostnames and timestamps differ, but the first failing subcase, diff shape, or fatal sequence is the
same. `bigPageSize` is the exception: both complete test records contain only `Test failed`.

### Testcase revision reconciliation

The jobs did not use identical `cubrid-testcases-private-ex` revisions:

- Job 138889 started at 2026-07-20 20:13 UTC. Its resolved CircleCI configuration explicitly set
  `BRANCH_TESTCASES=develop`; the `develop` tip available then was `732f2aad9f8c`.
- Job 139543 used `tc/pr-6864` at `458b018f81`, a no-file-change initialization commit whose parent is
  `develop` commit `aff076e4d6`.
- Between `732f2aad9f` and `aff076e4d6`, testcase commit `1642acffe4` corrected `cbrd_26403`, and commit
  `aff076e4d6` added CBRD-26986 answer changes for `cbrd_23828` and `cbrd_25846`.

This revision difference fully explains the three non-common test names. It does not weaken the 16 common comparisons,
whose primary signatures remain the same across both testcase revisions.

---

## Common Failures: Inherited from `feat/oos` (16 TCs)

| Category | TCs | Current evidence | Relation to #7391 |
|---|---|---|---|
| OOS allocation server crash | `cbrd_25365` | Both jobs fail after the archive-generating large-row workload loses the database server; archive/copy/unload checks then cascade | **Not introduced by #7391.** Real OOS baseline defect; P0 for OOS release readiness |
| Underdiagnosed server-side load | `bigPageSize` | Both CircleCI test records contain only `Test failed`; the test loads large mixed values into a 4 KiB-page database | **Not introduced by #7391**, but a focused rerun with logs/core is still required |
| Legacy overflow assumptions and OOS recovery/output | `tbl_enc_08`, `tbl_enc_14`, `cbrd_26527`, `log_enc_04` | Same missing `MULTIPAGE_OBJECT_HEAP`/HFID or recovery-index expectation in both jobs | Branch-wide OOS storage-layout expectation drift, not locality batching |
| TDE physical-page sequence baselines | `file_enc_01`, `file_enc_02`, `file_enc_03`, `file_enc_04`, `file_enc_05`, `file_enc_07` | Same `file_apply_tde_algorithm`, `pgbuf_set_tde_algorithm`, allocation, or deallocation line-count/sequence diffs | FILE_OOS/TDE baseline drift; no failed SQL result or PR-specific signature |
| OOS error-code default lists | `bug_bts_9836`, `bug_bts_14120` | Same stale `call_stack_dump_activation_list` output; OOS error codes are present in actual output but absent from answers | Deterministic answer drift inherited from OOS |
| Statistics payload size | `cbrd_20145_1` | Same communication-histogram/statistics transport-size mismatch | Branch-wide output drift, not OOS recdes locality behavior |
| Test workspace pollution | `cbrd_23430` | Same `jsondb` server connection failure after database setup pollution | Test setup/cleanup failure, not CBRD-27006 |

### Important inherited risks

`cbrd_25365` must not be dismissed as harmless merely because it is inherited. Its script disables string compression
and inserts eight very large `VARCHAR` values to generate archive logs. Existing artifacts for the same failure family
place the server termination in the OOS allocation path beginning at `oos_file_alloc_new()`. The current #6864 and
#7391 records reproduce the same server-loss and cascading missing-archive sequence.

`bigPageSize` also remains unresolved because the tests API omits its diagnostic body in both current records.
Inheritance proves non-regression for #7391, not correctness of the underlying behavior.

---

## Non-Common Failures

| TC | Present in | What it tests / observed failure | Attribution |
|---|---|---|---|
| `cbrd_23828` | #6864 only | Parallel/hash temporary-scan trace changed (`hash temp(m)` versus `hash temp(h)`) while row counts remain correct | Testcase/engine skew: `aff076e4d6` expects CBRD-26986 engine PR #7358, but tested `feat/oos` commit `c2cbeaf9f0` predates that engine merge. It uses small `INT` rows and cannot activate OOS demotion |
| `cbrd_25846` | #6864 only | Partition hash-join trace/method and related expected output changed; result values remain correct | Same CBRD-26986 testcase/engine skew. #7391 changes no hash-join files or behavior |
| `cbrd_26403` | #7391 only | Four exact optimizer cost mismatches (`209/208`, `209/208`, `259/258`, `4016/4010`); every result count matches | Testcase commit `1642acffe4`, created after job 138889 started, changes exactly those expected costs to `209`, `209`, `259`, and `4016`. Current #6864 therefore passes it |

The two #6864-only failures are not product regressions in #7391; they are answer files for a newer hash-join engine
revision being run against a `feat/oos` head that had not yet merged that engine revision. Separately, between #7391's
integrated base `7d73eb765e3fc5a29dca3614b076bd95805d41b2` and current `feat/oos` commit `c2cbeaf9f0`, seven engine commits
were added. Those seven commits and PR #7391 have **zero changed-file overlap**.

---

## Change-Scope Check

PR #7391 changes only these areas:

- OOS heap serialization/insertion and grouped read helpers: `heap_file.c`, `heap_oos.cpp`, and their headers
- OOS page insert/read implementation: `oos_file.cpp` and `oos_file.hpp`
- OOS replication publication handling: `locator_sr.c`
- OOS unit and SQL-level unit tests under `unit_tests/oos/`

It does not change optimizer, hash-join, parameter-default, TDE, utility-test, or shell-test files. Its purpose is to
batch selected OOS values while preserving logical attribute order, independent OOS OIDs, WAL/replication semantics,
and the existing OOS on-disk format.

The PR head is currently **25 commits ahead and 7 commits behind** the current `feat/oos` head. GitHub reports it as
mergeable, and the seven newer base commits do not touch any PR #7391 file. This lowers integration-conflict risk, but
the exact merge result has not run `test_shell`.

---

## Merge-Safety Decision

### Safe conclusions

1. **No `test_shell` failure is shown to be introduced by CBRD-27006.** Fifteen failures reproduce matching primary
   signatures on the current `feat/oos` baseline, and `cbrd_26403` is conclusively a testcase baseline issue.
   `bigPageSize` is also reproduced on the baseline but remains underdiagnosed, so this report makes only a
   non-regression claim for that case.
2. **The `test_shell` failure status alone should not block #7391 -> `feat/oos` as a regression.** A baseline-relative
   waiver is evidence-supported.
3. **Merging #7391 does not make existing OOS failures safe.** In particular, the inherited `cbrd_25365` server crash
   remains a P0 issue before `feat/oos` can be considered ready for `develop`.

### Conditions before merge

1. Merge/rebase current `feat/oos` (`c2cbeaf9f0` or newer) into the PR candidate and rerun `test_shell`, because CI job
   138889 tested the older base `7d73eb765` rather than today's exact merge result.
2. Require no new failed TC beyond the current baseline set. The expected post-sync shell set may include the two
   current-base optimizer/hash-join failures, but must not add a CBRD-27006-specific failure.
3. Resolve or explicitly and independently waive the PR's current `test_sql` and `code-style` failures. They are outside
   this report and prevent an unconditional whole-PR approval.
4. Track `cbrd_25365` and `bigPageSize` as base defects; do not close them as “safe” based on this attribution result.

**Recommended status:** `test_shell` regression gate = **GO**; immediate overall merge = **CONDITIONAL GO** pending the
latest-base rerun and non-shell checks.

---

## Evidence and Limitations

- Read `summary.json`, full `tests.json`, `failed-tests.json`, and `failed-tc.txt` for CircleCI jobs 139543 and 138889.
- Inspected all failed testcase scripts and available SQL/answer files under
  `/home/vimkim/cubrid-testcases-private-ex`.
- Compared GitHub PR metadata, current-head SHAs, job revisions, failure signatures, PR file scope, and the seven commits
  between #7391's tested base and current `feat/oos`.
- Reconciled private testcase history: `732f2aad9f` at #7391 job start, `tc/pr-6864` commit `458b018f81` based on
  `aff076e4d6`, and the intervening fixes `1642acffe4`/`aff076e4d6` that explain all three non-common cases.
- Used the normative OOS context last updated 2026-07-13. The context defines `feat/oos` as incomplete and distinguishes
  OOS Demotion, record-level Expand, attribute-level Resolve, and storage-level Read; this report does not reinterpret
  branch-local failures as normative behavior.
- No CI rerun, merge, source modification, or testcase modification was performed.
- The report does not diagnose `test_sql` or code-style failures and therefore cannot provide an unconditional all-checks
  merge approval.
