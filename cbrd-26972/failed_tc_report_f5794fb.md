# Failed TC Analysis Report: CBRD-26972-oos-show-heap-oos (PR #7382)

## Background

- PR: https://github.com/CUBRID/cubrid/pull/7382
- `/run all` comment: https://github.com/CUBRID/cubrid/pull/7382#issuecomment-5022306991
- Tested revision: `f5794fb4a40d82f630c9fc8ad16e23623c6a2100`
- CircleCI shell job: https://circleci.com/gh/CUBRID/cubrid/138858
- Job interval: 2026-07-20 18:51:05Z to 19:23:07Z
- Result: 3,238 total; 3,190 success; 18 failure; 30 skipped

The remaining PR diff against `origin/feat/oos` adds the standalone `SHOW [ALL] HEAP OOS` parser, metadata, and scan path. It no longer changes `SHOW HEAP CAPACITY`. None of the 18 failed tests invokes `SHOW HEAP OOS`.

The previous shell run at revision `5411058a9` (job 138018) had 23 failures. Sixteen failures are common to both runs. Seven old failures disappeared, including all five `issue_12506_show_heap_header` cases affected by the reverted capacity output. Two tests appeared only in the current run (`cbrd_26403`, `cbrd_26123`).

---

## Category 1: OOS allocation assertion on very large values (1 TC) — OOS base defect, not PR-specific

| # | TC | What it tests | Failure | Related to remaining PR? |
|---|---|---|---|---|
| 1 | `cbrd_25365` | Volume/log/archive creation times and utilities using 8 x 32 MiB `VARCHAR` values | Times out after the server aborts twice in `pgbuf_fix_debug` while `oos_file_alloc_new` allocates pages; archive-log subcases then cascade | No |

**Root cause analysis**: The coredumps show `heap_attrinfo_insert_to_oos` -> `oos_insert_across_pages` -> `oos_file_alloc_new` -> `file_numerable_add_page`/`file_alloc` -> `pgbuf_fix_debug` assertion. This is a real OOS large-value allocation failure. The remaining `SHOW HEAP OOS` code is not on the stack and is not executed by the TC.

**Proposed fix**: Reproduce `cbrd_25365` as a focused shell test and debug the OOS numerable-page allocation invariant in `oos_file_alloc_new`. Treat the later archive/copydb/loaddb NOKs as cascading symptoms until the assertion is fixed.

---

## Category 2: TDE file/page expectations changed by OOS (9 TCs) — OOS base/TC adaptation

| # | TC | What it tests | Failure | Related to remaining PR? |
|---|---|---|---|---|
| 1 | `file_enc_01` | TDE algorithm application to five heap user pages | Expected five-page log sequence is absent because large values follow OOS layout | No |
| 2 | `file_enc_02` | TDE bit/application log pairs during encrypted file allocation | Exact file/page log count differs after OOS file/page allocation | No |
| 3 | `file_enc_03` | TDE page set/dealloc count on a 20 KiB value and DROP | Exact page lifecycle differs because the value is OOS-backed instead of legacy overflow-only | No |
| 4 | `file_enc_04` | TDE algorithm transition AES -> NONE | Extra/different page transitions are produced by OOS storage | No |
| 5 | `file_enc_05` | TDE deallocation and recovery after crash | Exact dealloc/NONE count differs with OOS pages | No |
| 6 | `file_enc_07` | TDE redo after crash | More AES page operations than the two legacy heap operations are logged | No |
| 7 | `log_enc_04` | Presence of legacy TDE recovery indexes | `RVHF_INSERT_NEWHOME` is missing when large-variable updates take the OOS path | No |
| 8 | `tbl_enc_08` | `diagdb` encrypted heap + multipage overflow layout | Expected `MULTIPAGE_OBJECT_HEAP` entry is absent for a large non-key value | No |
| 9 | `tbl_enc_14` | `diagdb` encrypted heap/index + overflow-key layout | Expected heap multipage-overflow entry is absent/changed under OOS | No |

**Root cause analysis**: These tests assert exact legacy heap/overflow page counts or exact TDE diagnostic sequences. OOS introduces a lazily created, encrypted OOS file and moves eligible large variable values out of the heap. That changes which files/pages receive TDE operations. The failures existed before the latest reversion and none executes the new SHOW statement.

**Proposed fix**: Update each TC to distinguish heap, legacy overflow, and OOS files. Verify the security invariant (OOS file and pages inherit the class TDE algorithm) instead of preserving obsolete exact page counts. For `log_enc_04`, verify the OOS recovery indexes that replace the no-longer-exercised legacy path.

---

## Category 3: Legacy overflow cleanup assumption invalidated by OOS (1 TC) — OOS base/TC adaptation

| # | TC | What it tests | Failure | Related to remaining PR? |
|---|---|---|---|---|
| 1 | `cbrd_26527` | Reclaim a `MULTIPAGE_OBJECT_HEAP` after dropping a table | Case 4 cannot extract a multipage HFID from `diagdb_before.log` | No |

**Root cause analysis**: The test uses ten `CHAR(2048)` attributes and explicitly assumes a legacy multipage heap exists. On this branch, CHAR is variable-length and the oversized record is demoted to OOS, so the prerequisite multipage HFID is not present. Cases 1-3 pass; only the legacy-overflow-specific assertion fails.

**Proposed fix**: Preserve a genuine non-OOS overflow scenario for the original CBRD-26527 regression, or split the test into legacy overflow cleanup and OOS file cleanup cases.

---

## Category 4: Expected diagnostic/protocol output drift (3 TCs) — inherited branch behavior

| # | TC | What it tests | Failure | Related to remaining PR? |
|---|---|---|---|---|
| 1 | `cbrd_20145_1` | Communication histogram and complete server-stat dump | `MNT_SERVER_COPY_STATS` receive size is 90,864 instead of expected 86,400 | No |
| 2 | `bug_bts_14120` | `paramdump` default call-stack activation list | Actual list includes newly registered OOS error codes | No |
| 3 | `bug_bts_9836` | Default/list-composed call-stack activation parameters | Cases 2-3 differ by the new OOS default error-code entries | No |

**Root cause analysis**: `bug_bts_14120` and `bug_bts_9836` match the OOS base change that adds `ER_HEAP_OOS_BAD_INLINE_HEADER`, `ER_HEAP_OOS_CORRUPTED_RECORD`, and `ER_HEAP_OOS_INVALID_ARGUMENT` to `call_stack_dump_error_codes`. `cbrd_20145_1` is a persistent server-stat payload baseline drift; the remaining PR diff does not modify performance counters, stat serialization, or communication histogram code.

**Proposed fix**: Re-baseline the two call-stack answer files for accepted OOS error codes. For `cbrd_20145_1`, first identify the inherited counters responsible for the 4,464-byte increase, then update the answer only if the counter set is intended.

---

## Category 5: Large-value unload/loaddb comparison (1 TC) — testcase determinism/output issue

| # | TC | What it tests | Failure | Related to remaining PR? |
|---|---|---|---|---|
| 1 | `bigPageSize` | Unload a 16 KiB-page DB and server-side load into a 4 KiB-page DB | Load succeeds (256/256 objects), but the source/destination query comparison differs on CLOB/BLOB locator lines | No |

**Root cause analysis**: The test contains very large `VARCHAR`, `STRING`, JSON, CLOB, and BLOB values and therefore exercises OOS demotion and cross-page-size serialization. The visible diff is confined to CLOB/BLOB locator text. Preserved local reruns independently confirm that the row data matches and only volatile physical locator paths differ. The OOS specification requires LOB copy semantics to be preserved, but it does not require physical locator strings in two databases to be identical.

**Proposed fix**: Reproduce locally, compare logical CLOB/BLOB content and locator ownership, and then either normalize physical locator text in the TC or fix the copy path if ownership/content differs.

---

## Category 6: Unrelated baseline/environment/timing failures (3 TCs) — not OOS/PR-specific

| # | TC | What it tests | Failure | Evidence |
|---|---|---|---|---|
| 1 | `cbrd_26403` | Exact optimizer costs for correlated subqueries | Costs are 209/259/4016 vs 208/258/4010 | Testcase commit `1642acff` re-baselined these exact values after the CI run |
| 2 | `cbrd_23430` | JSON alter/update crash regression | `createdb` fails because stale `jsondb_vinf` already exists; all DB operations then fail to connect | Environment/test cleanup failure before feature logic runs |
| 3 | `cbrd_26123` | `tranlist`/`killtran` active transaction output | The TC's regex `grep -o "0.00"` also matches `0500` in this runner's hostname, inflating every non-quiet `tranlist` zero count | Testcase regex/runner-hostname collision |

**Root cause analysis**: `cbrd_26403` was already corrected upstream in the testcase repository at 2026-07-21 09:21 KST, after this CI started. `cbrd_23430` never creates its database because stale local files remain despite the registry entry being absent. `cbrd_26123` fails because Basic Regular Expression dots are wildcards: `grep -o "0.00"` matches both the real `0.00` time and `0500` inside hostname `ccita-67c05006-a98f-5ce4-9a2b-48781ae8c15c-mx0alh`. That adds one false match per full `tranlist` row. The paired `killtran -q` checks pass because quiet output omits the hostname. PR #7391 job 138889 ran the same TC successfully; the difference is the randomized runner hostname, not engine behavior.

**Proposed fix**: Pick up testcase commit `1642acff`; harden `cbrd_23430` cleanup to remove its database directory/volumes when registry cleanup cannot; change `cbrd_26123` to count literal time fields (at minimum `grep -Fo "0.00"`, preferably parse the Query/Tran time columns) instead of applying an unescaped regex to the whole row.

---

## Summary

| Category | Count | Remaining PR-specific? | Root cause |
|---|---:|---|---|
| OOS allocation assertion | 1 | No | Real OOS base defect under very large allocation |
| TDE exact layout/output | 9 | No | OOS files/pages invalidate legacy exact-count expectations |
| Legacy overflow cleanup assumption | 1 | No | TC expects multipage overflow where OOS is now used |
| Diagnostic/protocol baseline drift | 3 | No | OOS error-code defaults and inherited stat payload drift |
| Large-value unload/loaddb | 1 | No | TC compares volatile physical LOB locator strings |
| Unrelated baseline/environment/test robustness | 3 | No | Already-fixed baseline, stale workspace, and hostname-sensitive regex |
| **Total** | **18** | **0 directly attributable to standalone SHOW** | |

The reversion achieved its intended shell-test effect: all five former `SHOW HEAP HEADER` failures disappeared. The shell job is still red because of inherited OOS behavior/defects and unrelated test issues, not because the remaining standalone `SHOW HEAP OOS` path was exercised.

## Priority Actions

1. **P0**: Debug the `cbrd_25365` OOS allocation assertion in `oos_file_alloc_new`; it is the only observed server abort and causes cascading failures.
2. **P1**: Rework the nine TDE cases and `cbrd_26527` around explicit OOS-aware invariants instead of legacy exact file/page layouts.
3. **P1**: Reproduce `bigPageSize` and verify logical LOB content/ownership across unload/loaddb and page-size conversion.
4. **P2**: Update OOS call-stack answer files and investigate the persistent `cbrd_20145_1` stat payload increase.
5. **P2**: Pick up the already-merged `cbrd_26403` testcase baseline, harden `cbrd_23430` cleanup, and fix the literal-time match in `cbrd_26123`.

## Comparison with PR #7391 / CBRD-27006

CircleCI job 138889 for PR #7391 reports 17 failures; job 138858 for this PR reports 18. The failed-test set difference is exactly `cbrd_26123`:

| TC | PR #7391 job 138889 | PR #7382 job 138858 | Explanation |
|---|---|---|---|
| `cbrd_26123` | Success, 81.401s | Failure, 81.677s | Runner hostname `ccita-67c05006-...` contains `0500`, which matches the TC's regex `0.00` |

This testcase calculates `zero_num` with:

```sh
grep -o "0.00" "$log_file" | wc -l
```

Because the dots are not escaped or matched literally, the failing runner produces two matches from a row containing one real zero time:

```text
ccita-67c05006-... 0.00 1.80
      ^^^^           ^^^^
      0500           0.00
```

The failure pattern confirms the collision: the full `tranlist` checks are NOK, while paired `killtran -q` checks are OK because quiet output excludes the hostname. Therefore the 18th failure is a testcase false positive, not a CBRD-26972/CBRD-27006 engine behavior difference and not an OOS regression.

## Grill Review Notes

The classification was challenged against the remaining source diff, the authoritative OOS context, preserved local rerun logs, and prior failure analysis:

- No failed TC contains or invokes the remaining `SHOW HEAP OOS` statement, and no failure stack enters its parser, metadata, or scan implementation.
- Sixteen of the 18 failures predate the reversion. The two current-only failures are an optimizer answer already re-baselined after this run and a transaction-list testcase whose unescaped regex collides with the randomized CI hostname.
- The alternative hypothesis that PR #7382 introduced a transaction-list regression does not fit the evidence: both PR heads merge the same `feat/oos` tip `7d73eb765`, the TC last changed in 2025, the failed and successful runtimes are nearly identical, and the NOK/OK split follows whether hostname-bearing output is searched. The hostname collision alone reproduces the extra count.
- Preserved reruns independently reproduce the exact `tbl_enc_08`/`tbl_enc_14`, call-stack error-code, `bigPageSize`, `cbrd_20145_1`, and `cbrd_26527` differences described above.
- `cbrd_25365` remains classified as a real engine defect because it has two server coredumps with an OOS allocation stack; downstream archive/copy/load failures are not counted as independent root causes.
- The source of the `cbrd_20145_1` payload increase still requires confirmation. It is intentionally not labeled an answer-file-only failure.

Cross-check material:

- `/home/vimkim/gh/cubrid-oos-context/OOS-CONTEXT.md`
- `/home/vimkim/gh/my-cubrid-jira/issues/CBRD-27028-file-oos-assert-errors.md`
- `/home/vimkim/gh/my-cubrid-docs/cbrd-27028/c6334f6/local_debug_gcc_rerun_c6334f6.md`
- `/home/vimkim/gh/my-cubrid-docs/cbrd-26814/CBRD-26814-oos-inline-stub-bounds.md`
- `/home/vimkim/gh/my-cubrid-docs/cbrd-26357/5b5ff58/test_shell_failure_5b5ff58_pr6864_circleci135486.md`
