# CI Failure Analysis: PR #7596 at `32cb34e`

## Executive Summary

**Recommendation: PR #7596 is safe to merge into `feat/oos` on the evidence available.** None of the 22
current failures is introduced by the PR delta.

**Merge-gate decision (confirmed by the PR author, 2026-08-14):** inherited failures are allowed; this PR is
judged differentially against its exact `feat/oos` base.

- The exact PR snapshot has 0 medium, 2 SQL, and 20 shell failures; errors and unknown results are zero.
- Both SQL failures and 11 shell failures reproduce at the exact merge-base `725a32c6` with the same decisive
  signatures.
- The remaining 9 shell failures reproduce with the same OOS/TDE/diagnostic signatures on the validated
  `feat/oos` ancestor `0ad6afc0`; the PR changes none of their producing TDE, diagnostic, or OOS-file paths.
- GitHub reports the PR as `MERGEABLE` and `APPROVED`; `mergeStateStatus` is `UNSTABLE` because SQL and shell
  statuses are red.

This is a differential merge recommendation for **CBRD-26847 into `feat/oos`**. It is not evidence that
`feat/oos` itself is ready to merge to `develop`: the inherited loaddb, page-buffer, and CDC crashes are real
OOS base defects and must remain release blockers under their own tickets.

## CI Snapshot

| Suite | State | CircleCI job | Tests | Failures | Errors | Unknown | Warning |
|---|---|---:|---:|---:|---:|---:|---|
| `test_medium` | success | [145316](https://circleci.com/gh/CUBRID/cubrid/145316) | 975 | 0 | 0 | 0 | — |
| `test_sql` | failed | [145318](https://circleci.com/gh/CUBRID/cubrid/145318) | 17,444 | 2 | 0 | 0 | testcase `cbdaad3f...` |
| `test_shell` | failed | [145317](https://circleci.com/gh/CUBRID/cubrid/145317) | 3,241 | 20 | 0 | 0 | 30 skipped; private testcase revision unavailable |

Total: 21,660 tests, 21,608 successes, 22 failures, 30 skips, 0 errors, 0 unknowns.

## Evidence Scope

- PR: `https://github.com/CUBRID/cubrid/pull/7596`
- Head: `32cb34e7ed30f0dc5bdcba7045eaee06075d66d5`
- Exact base / merge-base: `725a32c6ee0d7cb2b27dedd2283b03a9a93de608`
- Historical `feat/oos` ancestor: `0ad6afc0ff871f5aa6c002923868fc6527149ea0`
- Collector: `cubrid-ci 0.1.0 (3e9502f72350, release)`
- Current bundle: `/home/vimkim/gh/cubrid-circleci-analyzer/data/CBRD-26847/32cb34e`
- Exact-base bundle: `/home/vimkim/gh/cubrid-circleci-analyzer/data/CBRD-26357/725a32c`
- Historical bundle: `/home/vimkim/gh/cubrid-circleci-analyzer/data/CBRD-26357/0ad6afc`

The exact-base SQL testcase revision is `479cd5fb...`; the current revision is `cbdaad3f...`. Shell summaries do
not retain a private testcase SHA, and totals differ by three (3,238 base versus 3,241 current), so raw shell
name-set subtraction is not treated as causal proof. Instead, attribution requires matching decisive signatures
plus source-path locality.

## Failure Inventory

| Suite | Test | Observed signature | Category | PR relation | Confidence |
|---|---|---|---|---|---|
| SQL | `bug_bts_10516.sql` | first insert returns `ER_HEAP_OOS_OVERPASS_MAXOBJ_SIZE` (`-1380`); later row-count diffs cascade | OOS big-record/test expectation | unlikely | high |
| SQL | `fbo_ddl02.sql` | identical `-1380` first-insert rejection and cascade | OOS big-record/test expectation | unlikely | high |
| shell | `bug_bts_9836.sh` | `call_stack_dump_activation_list` answer mismatch | configuration expectation | unlikely | high |
| shell | `bug_bts_14120.sh` | server activation-list answer mismatch | configuration expectation | unlikely | high |
| shell | `cbrd_25481.sh` | server-side loaddb aborts; core at `lock_internal_perform_lock_object:3636` | TT_LOADDB/OOS lazy-file self-lock | unlikely | high |
| shell | `cbrd_26527.sh` | cannot extract a `MULTIPAGE_OBJECT_HEAP` HFID after cases 1–3 pass | OOS/overflow diagnostic assumption | unlikely | high |
| shell | `cbrd_23430.sh` | server-side loaddb core at `lock_internal_perform_lock_object:3636`; later connection fails | TT_LOADDB/OOS lazy-file self-lock | unlikely | high |
| shell | `bigPageSize.sh` | object-load completion missing; same self-lock core | TT_LOADDB/OOS lazy-file self-lock | unlikely | high |
| shell | `itrack_10006.sh` | both cases NOK; same self-lock core | TT_LOADDB/OOS lazy-file self-lock | unlikely | high |
| shell | `bug_xdbms_sus880.sh` | same self-lock core during server-side loaddb | TT_LOADDB/OOS lazy-file self-lock | unlikely | high |
| shell | `file_enc_01.sh` | extra/missing TDE file/page algorithm trace lines | TDE/OOS physical trace drift | unlikely | high |
| shell | `file_enc_02.sh` | extra AES allocation/page trace pair | TDE/OOS physical trace drift | unlikely | high |
| shell | `file_enc_03.sh` | AES/deallocation trace-count drift | TDE/OOS physical trace drift | unlikely | high |
| shell | `file_enc_04.sh` | AES/NONE page-algorithm trace-count drift | TDE/OOS physical trace drift | unlikely | high |
| shell | `file_enc_05.sh` | deallocation/NONE trace-count drift | TDE/OOS physical trace drift | unlikely | high |
| shell | `file_enc_07.sh` | two extra AES page-algorithm traces | TDE/OOS physical trace drift | unlikely | high |
| shell | `log_enc_04.sh` | recovery-index workload reports case 1 NOK | inherited recovery-index expectation | unlikely | high |
| shell | `tbl_enc_08.sh` | actual `FILE_OOS`/OOS descriptor replaces expected heap-overflow descriptor | OOS/overflow diagnostic assumption | unlikely | high |
| shell | `tbl_enc_14.sh` | same OOS-versus-overflow descriptor drift; btree overflow remains | OOS/overflow diagnostic assumption | unlikely | high |
| shell | `cbrd_27064.sh` | CDC extractor `rc=-10`; delete 8/700 and update 0/2400, `CORRUPTION=0` | inherited CDC/OOS extractor defect | unlikely | high |
| shell | `cbrd_27075.sh` | core at `oos_check_head_header:1679`; `CONFIGS_OK=0`, `TOTAL_CORRUPTION=0` | inherited CDC/OOS chain defect | unlikely | high |
| shell | `cbrd_25365.sh` | timeout plus repeated cores at `pgbuf_fix_debug:2419`; later archive-time checks cascade | inherited OOS allocation/page bookkeeping | unlikely | high |

Every current `failure` is listed exactly once. There are no `error` or unknown results.

## Root-Cause Analysis

### Exact-base inherited failures (13 tests)

**Observed:** both SQL failures and these 11 shell failures occur on exact merge-base jobs 145306/145308:
`bug_bts_9836`, `bug_bts_14120`, `cbrd_25481`, `cbrd_23430`, `bigPageSize`, `itrack_10006`,
`bug_xdbms_sus880`, `log_enc_04`, `cbrd_27064`, `cbrd_27075`, and `cbrd_25365`.

The decisive signatures match, including the TT_LOADDB self-lock assertion, CDC counts and return code, OOS head
header assertion, page-buffer assertion, configuration diffs, and loaddb completion failures. For the SQL pair,
the exact base also returns `-1380`; only testcase answer context changed between public testcase revisions.

**Inference:** these failures are inherited from `feat/oos`, not introduced by CBRD-26847.

**Falsifier:** a paired run with one pinned testcase tree that passes at `725a32c6` but fails at `32cb34e7` with a
CBRD-26847-changed call path would overturn the attribution. The available exact-base artifacts show the opposite.

### Historical `feat/oos` TDE/diagnostic failures (9 tests)

The nine shell names absent from the exact-base normalized failure list all fail on validated ancestor job 142161:
`cbrd_26527`, six `file_enc_*` tests, `tbl_enc_08`, and `tbl_enc_14`. The current and historical messages have the
same decisive TDE trace or OOS-versus-overflow diagnostic signature.

CBRD-26847 changes visible-version fetch consumption policy at audited callers. It does not change TDE page
application, page allocation/deallocation diagnostics, `diagdb` file descriptors, or the OOS-versus-overflow
storage decision exercised by these tests.

**Inference:** these are branch-wide OOS testcase/diagnostic drifts. They are not CBRD-26847 regressions.

**Falsifier:** a source trace from one of these failures into a changed CBRD-26847 call site, or a paired pinned
testcase reproduction that selects a PR commit, would require reclassification. No such path appears in the exact
diff or evidence.

### Why the touched loaddb and lock-manager files do not make the crashes PR-caused

The PR does touch `load_server_loader.cpp` and `lock_manager.c`, but locality at file granularity is misleading:

- The loaddb change switches one visible-version fetch near line 243 from raw-byte Expand to attribute-layer
  Resolve. Every loaddb core occurs later in `server_object_loader::finish_line` near line 707 while lazily creating
  `FILE_OOS`, through `file_create -> logtb_get_current_mvccid -> lock_transaction_mvccid`.
- The lock-manager change is in `lock_dump_resource` near line 5696. The cores assert in
  `lock_internal_perform_lock_object` near line 3636.
- The exact merge-base produces the same stacks before either PR change exists.

Therefore the relation is `unlikely`, not merely unknown.

## Recommended Actions

1. Merge PR #7596 into `feat/oos`. The confirmed gate allows inherited failures, and the current evidence shows
   no PR-introduced regression.
2. Record or link this report when overriding the red SQL/shell statuses; do not describe those suites as passing.
3. Keep the inherited engine crashes separate from CBRD-26847:
   - TT_LOADDB/OOS self-lock: CBRD-27157 / candidate commit `8bcfd7dd2` is not in the current base.
   - CDC/OOS and OOS page-buffer assertions: retain as OOS merge gates before `feat/oos -> develop`.
4. Update OOS-era testcase expectations only after validating intended behavior; do not blindly churn answer files.
5. Improve shell CI provenance by retaining the private testcase full SHA in `summary.json`.

## Evidence and Limitations

- All current suite manifests, summaries, failure records, failure metadata/messages/diffs, log/artifact/source
  indexes, targeted logs, JUnit XML, and exact PR diff were inspected.
- Collection used `--artifact-mode text`; core binaries were not downloaded. Retained core-analyzer stacks are
  sufficient for signature comparison, not for new post-mortem debugging.
- The exact-base shell testcase SHA is unknown and its total differs by three. This is why the nine non-intersecting
  names are supported by a separately validated historical `feat/oos` run plus source-path analysis.
- Historical job 142161 artifacts have expired (`artifact_count=0`), but its normalized failure records and 20
  retained failed-action logs were recollected and contain the compared signatures.
- Local build/reproduction was not used because this worktree lacks a build directory and `compile_commands.json`.
- No CI was triggered or rerun; no source or testcase was modified.
