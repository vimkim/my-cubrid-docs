# CI analysis: PR #8677, run 46011518777, attempt 1 failures

- **PR:** [CUBRID/cubrid#8677](https://github.com/CUBRID/cubrid/pull/8677), "[CBRD-28240] Speed up the fetch of unloaddb ..." (author ctshim). Base: `develop`.
- **Engine head:** `fafffbbab98abfd017f4e8f3eaf975d618512275` (build 11.5.0.3139-fafffbb).
- **Run:** [46011518777](https://github.com/CUBRID/cubrid/actions/runs/46011518777). Attempt 1 failed in two suites. Attempt 2 passed every suite.
- **Testcase revisions:** sql `tc/pr-8677@0f4d67c1af18`, shell `tc/pr-8677@0786da43d0c1`.
- **Analysis date:** 2026-11-28 (Asia/Seoul). Work-tracker item 1122.

## Summary

PR #8677 did not cause either failure. Both are flaky testcases, and both fail the same way on `develop`-only builds and on unrelated PRs.

| Suite | Testcase | Signature | PR relation | Confidence | Tracking |
| --- | --- | --- | --- | --- | --- |
| test_sql_by_cci | `sql/_36_guava/cbrd_28181/cases/cbrd_28181.sql` | `count(*)` returns `20002`, answer has `20000` (line 307, one diff) | unlikely | high (~95%) | none; TC fix needed |
| test_shell | `shell/_06_issues/_26_2h/apis_1125/cases/apis_1125.sh` | only `_19_trailing_dot_host_name` NOK: `ERROR -21013 Cannot connect to a broker[CAS INFO-localhost.:...]` | unlikely | high (~95%) | CBRD-28420 (Open) |

The 20000 → 20002 drift is not an engine wrong-result bug. The query has `rownum < 5000` with no `ORDER BY`, so its result depends on the physical position of two late-inserted rows. See [cbrd_28181](#cbrd_28181-test_sql_by_cci).

**Next action:** no engine change for PR #8677. Fix the cbrd_28181 testcase (owner: CBRD-28181 author). apis_1125 is tracked by CBRD-28420.

## Evidence scope and limits

- `cubrid-ci 0.2.0 (56eb28492c94)` could not collect this run (exit 5, `kind: remote`). GitHub returns HTTP 502 for `repos/CUBRID/cubrid/actions/runs/46011518777/jobs?filter=all&per_page=100&page=2` on every retry. The run has 174 jobs, and `per_page=50` pages work. This is recorded as failure-tracker pattern 14 (repo `cubrid-ci`).
- So `cubrid-ci verify` and the merge-base baseline (`collect-base`) did not run. This report has **no cubrid-ci-validated bundle**. Its evidence comes from:
  - GitHub job metadata and logs, read with `per_page=50`.
  - The CI artifact server (`.../runs/46011518777/sql_by_cci/`, shard 09, `ctp_log.tgz`) for the CCI diff.
  - Chronicle (`cubrid-tcc`) retained shell XML (execution 108410) and testcase history.
- In place of an exact merge-base comparison, the failures were observed on runs whose engine head is a `develop` commit. That is stronger evidence against PR causation than a merge-base pass would be.
- Chronicle does not index `test_sql_by_cci`. The CCI history comes from a bounded scan of gha-ci runs between 2026-11-27 05:04Z and 2026-11-28 07:20Z.
- Neither failure was reproduced locally.

## CI snapshot (2026-11-28)

| Suite | Attempt 1 | Attempt 2 (current) |
| --- | --- | --- |
| build (debug, release) | success | success |
| test_medium | pass | pass |
| test_sql (CSQL, debug) | pass | pass |
| test_sql_by_cci (CCI, release) | **1 fail**: cbrd_28181, job 140551008921 (shard 09) | pass (587 tests, 0 failures) |
| test_shell | **1 fail**: apis_1125, job [140551010341](https://github.com/CUBRID/cubrid/actions/runs/46011518777/job/140551010341) (shard 13, 1/74 cases) | pass (shard 13 job 140819194860, different runner pod) |

`Check TC PRs` (the TC Merge Gate) is failing because the `tc/pr-8677` TC PRs are open. That is expected until the final merge handoff, and it is separate from these regression results.

## cbrd_28181 (test_sql_by_cci)

### Observed

- Failing statement (testcase line 51):

  ```sql
  select count(*) from t28181 where k in (select k from t28181 where rownum < 5000 group by k);
  -20000
  +20002
  ```

- Data setup (lines 6-18): rows with `id` 1..20000 and `k = id mod 97`, then one more `insert` of two rows with `id` 900001 and 900002 and `k = 1000`. The answer `20000` assumes the subquery's first 4999 rows contain only `k` values 0..96.
- The testcase came with CBRD-28181 ("Hash GROUP BY: partition spill and two-level COUNT(DISTINCT)"). Engine PR #8663 merged on 2026-11-27, and the testcase landed then.
- History: 56 gha-ci runs executed the case under sql_by_cci. Four failed on attempt 1, each with the identical `20000 → 20002` diff on this statement. The rate is about 7%.

  | Run | Build | Engine head |
  | --- | --- | --- |
  | 46011518777 | 3139-fafffbb | PR #8677 |
  | 46024594504 | 3105-bead335 | `develop` `f638ca09582e` (workflow_dispatch; no #8677 code) |
  | 45962585500 | 3110-35c4fbf | PR #8798 |
  | 45946769509 | 3106-02487b2 | PR #8771 |

- Under CSQL (test_sql, debug), Chronicle has 60 passes and 0 failures.
- `cubrid-tcr check` matches only the job-level rule `sql-by-cci-every-branch-20270108`. No case signature or issue exists.

### Mechanism (inference from develop source; PR head is identical on these paths)

1. `count(*)` = 20002 means at least one `k = 1000` row was among the first 4999 rows the subquery's heap scan returned. Then `k = 1000` joins the IN-list, and the outer count adds both late rows.
2. The table is about 100 pages, below `parallel_scan_page_threshold` (256), so the scan is serial and returns rows in physical page order.
3. Where the late insert puts its rows depends on the best-space candidates (`heap_find_bestpage`, `bestspace::find`). Vacuum feeds these candidates: after the first insert commits, vacuum removes each record's MVCC insert id, frees space on early pages, and adds those pages as candidates (`vacuum_heap_page` → `heap_add_bestpage`).
4. If vacuum reaches early pages before the second `insert` (its master wakes every 10 ms), the two rows go into an early page, inside the first 4999 rows. Otherwise they go to the last page and the answer holds.

Confidence: high that the testcase depends on physical order and is not a wrong-result bug. Medium (~65%) on the exact vacuum-candidate path. The CCI/release-only occurrence fits the timing dependence (different round trips and timing), but this was not tested.

### PR #8677 relation

The PR does not change `bestspace.cpp`, `vacuum.c`, `scan_manager.c`, `query_executor.c`, or `px_scan.cpp`. In the PR diff, the new heap, locator, MVCC-snapshot export/import, and tran-table code has callers only in the unloaddb path (`unload_object.c`). For ordinary sessions, `heap_next_1page` is a wrapper with unchanged behavior, `logtb_clear_tdes` frees a NULL cache, and the snapshot `pinned` flag stays false.

**Falsifier for "not the PR":** over many runs, `develop`-only builds never fail while #8677 builds fail clearly more often. The develop failure in run 46024594504 already argues against this.

**Falsifier for the mechanism:** the failure persists with `vacuum_disable=yes`, or after a failure `select id from t28181 where rownum < 5000 and k = 1000` returns no row (that would point to the IN or hash GROUP BY path instead).

### Proposed local check (not run)

Use a release build of `develop`:

1. Run the case 300 times and count `20002` results.
2. Run the first insert and commit, wait 50 ms, then run the second insert and the query. The mechanism predicts close to 100% `20002`.
3. Repeat step 2 with `vacuum_disable=yes`. The mechanism predicts 0%.

### Fix direction

Make line 51 independent of order, for example `select k from (select k from t28181 order by id limit 4999) group by k`. The owner is the CBRD-28181 testcase author (cubrid-testcases #4359 follow-up).

## apis_1125 (test_shell)

### Observed

- Only step `_19_trailing_dot_host_name` failed, and the other 44 `conn/` steps passed against the same broker. Both connects in `_19` returned `ERROR -21013 Cannot connect to a broker`:
  - `jdbc:cubrid:localhost.:<port>:apis1125:...?sslmode=verify-full`
  - `...?useSSL=true`
- `_19` is the only step that uses the host name `localhost.` (trailing dot).
- History in Chronicle since 2026-11-25: 299 passes and 30 failures (~9%), all with the identical `_19`-only signature. The failures cover 19 PRs and 5 `develop` post-merge runs, including 45644779630 (`develop` `17eb1f6f2bc7`) and 46024564407 (`develop` `f638ca09582e`).
- CBRD-28420 (Open): "[shell] apis_1125 TC 의 케이스 19 가 runner 에 따라 localhost. 로 브로커에 접속하지 못하고 실패한다".

### Mechanism (inference)

JDBC `BrokerHandler.connectBroker` turns any `IOException` from resolving or connecting to `localhost.` into -21013. `useSSL=true` does no certificate check and fails too, so the failure happens before TLS: in name resolution or the TCP connect. Some runner pods presumably do not resolve `localhost.` to loopback, which would explain why the rerun on another pod passed. No resolver output was retained, so this is unconfirmed.

### PR #8677 relation

The testcase uses createdb, server and broker start with SSL, and a JDBC `select 1`. It uses no unloaddb, loaddb, or csql. The PR changes no broker, CAS, JDBC, SSL, or name-resolution code. Its `tz_support.c` changes are `!SERVER_MODE` only.

**Falsifier:** an apis_1125 failure with a different signature that appears only on #8677 builds, or a server or CAS crash in the failing job.

## Recommended actions

1. **PR #8677:** no change. Attempt 2 is green. Optionally post a short PR comment (needs approval), for example: "Attempt 1 failures (cbrd_28181 via CCI, apis_1125 `_19`) are flaky testcases also seen on develop builds 46024594504 and 46024564407; unrelated to this PR."
2. **cbrd_28181:** open a TC fix, or a JIRA follow-up to CBRD-28181, that makes line 51 independent of order. Optionally run the local check above to confirm the vacuum mechanism.
3. **apis_1125:** add the numbers above to CBRD-28420 (needs approval). The fix belongs there: skip `_19` when `localhost.` does not resolve to loopback, or pin name resolution in the runner image.
4. **cubrid-tcr (needs approval):** add signatures for both shapes, link apis_1125 to CBRD-28420, and consider known-issue rules with an expiry date.
5. **cubrid-ci:** fix the collector so a 502 on a `per_page=100` jobs page triggers a retry with smaller pages (failure-tracker pattern 14).

No `cubrid-tcr`, JIRA, or GitHub writes were made during this analysis.

## Evidence files (local, not in Git)

Under `/mnt/nvme/data-5/tmp/claude-1000/-home-vimkim-gh-cb-CBRD-28240/cf15d8fb-4ba1-4bc3-8658-a2f367d15f0e/scratchpad/`:

- `ci/status.json`, `ci/result.json`: status snapshot and the failed collection result.
- `cci-28181/trace-note.txt`, plus `art/`, `jobs/`, `logs/`, `hist/`: CCI artifacts, job JSON, and the history scan.
- `shell-1125/NOTE.md`, `shell-1125/exec108410.xml`, `shell-1125/hist_all.json`: shell evidence and history.
