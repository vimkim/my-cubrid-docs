# PR #6864 at `2940b1c` — next steps and recommended skill paths

- **Companion to**: `ci_analysis_report_2940b1c_claude.md` (rev 2, CircleCI job 152256 + GHA run 33844280456)
- **Written**: 2026-09-05, Claude (Fable 5.1), from the `/ask-matt` route map applied to the confirmed findings
- **Status** (2026-09-05 17:00 KST): path 1 steps 1–2 are applied in the worktree
  `/home/vimkim/gh/tc/cubrid-testcases-private-ex-tc-pr-6864` (branch tc/pr-6864, six files, uncommitted, unpushed).
  Step 3 verification was attempted and **failed unsafely**: see `2940b1c/local-verify-attempt-2026-09-05/INCIDENT.md`.
  Decision taken afterwards: skip local verification and let CI verify. Steps 4 executed 2026-09-05 08:21Z: the six
  edits were committed and pushed as `212149852` on tc/pr-6864 (TC PR #3782 now lists all six files) and `/run all`
  was posted on PR #6864 (comment 5550556895; `/run shell` alone is not a verified trigger form). Waiting on
  `ci/circleci: test_shell` and `gha-ci: test_shell` for head `2940b1c`; work-tracker item 63.
  **08:58Z: GHA finished — 3 failures (log_enc_04, cbrd_27064, cbrd_27075), the predicted set; all five fixes
  confirmed.** CircleCI shell still pending; rev 3 delta in the report is started and will be completed when it lands.

## Where things stand

Eight shell failures at `2940b1c`, one cause each, grouped:

| Group | Tests | Kind of work | Blocking? |
|---|---|---|---|
| A. Renumbered OOS error codes in paramdump answers | `bug_bts_9836`, `bug_bts_14120` | 3 answer files on tc/pr-6864 | no |
| B. OOS TDE answers dropped by develop merges | `file_enc_03`, `file_enc_05` | 2 answer files on tc/pr-6864 (restore from `e7e87aa43`) | no |
| C. Known TC residuals | `log_enc_04`, `bigPageSize` | testcase workload / tiebreaker on tc/pr-6864 | no |
| D. CDC dereferences reclaimed OOS chains | `cbrd_27064`, `cbrd_27075` | **engine**, 3 `cub_server` cores, CBRD-26939 | decision needed |
| GHA-only | `bug_bts_6938` | none; passed on CircleCI | no |

Groups A–C are seven testcase files and no engine change. Group D is the only engineering item.

## Paths, in priority order

### 1. Testcase fixes for groups A–C (Continue in the analysis session, no thinking skill)

Decided, mechanical, small. Do it directly:

1. On `tc/pr-6864` in `cubrid-testcases-private-ex`:
   - `git checkout e7e87aa43 -- shell/_36_damson/cbrd_23608_tde/file_enc_03/cases/result.answer shell/_36_damson/cbrd_23608_tde/file_enc_05/cases/result.answer`
   - In `bug_bts_9836/cases/log2.answer`, `log3.answer`, `bug_bts_14120/cases/bug_bts_14120_1.answer`: `-1378,-1380,-1381` → `-1380,-1382,-1383`
   - `bigPageSize`: `order by 1 desc` → `order by 1 desc, id` in the two csql queries (CBRD-26828 draft)
   - `log_enc_04`: rewrite the insert workload so `RVHF_INSERT_NEWHOME` is produced under OOS (check what fires on develop first)
2. Verify each in isolation. **Not** `just ctp shell-debug` on this host while another master is on port 1523, and
   not the 2026-09-05 namespace attempt either (`2940b1c/local-verify-attempt-2026-09-05/INCIDENT.md`: it stopped
   the host's pgbuf-analysis master). A safe local run needs all of: a PID namespace (`pkill cub`), an IPC namespace
   (broker shm), a **network namespace with `lo` up** (`cubrid service stop` is a TCP call to `cubrid_port_id`,
   default 1523), and a `~/.CUBRID_SHELL_FM` that CTP may delete and recreate (`DeployOneNode`,
   `resetCUBRID_linux`). `just ctp podman-test-new` is not usable as-is: it mounts the install read-only and does
   not provide CTP's `init.sh`. Or verify on a host/VM with no other CUBRID instance.
3. Push tc/pr-6864 (updates TC PR #3782; confirm `file_enc_05/cases/result.answer` now appears in its file list),
   then `/cubrid-ci-trigger` with `/run shell`.
4. When the run finishes, `/cubrid-ci-analyze` again with the pinned SHA and append a rev 3 delta to the report.

Skills touched: `/cubrid-shell-run` only for the container recipe's argument shape; `/cubrid-ci-trigger`;
`/cubrid-ci-analyze`. No `/grill-*`, no `/implement`.

### 2. CDC with OOS (group D) — the one real engineering flow

Start this in a **fresh session and a new engine worktree**, pointing it at the CI report as its primary source.
Do not carry the analysis window into it.

1. **Decision first**: `/grill-with-docs` in the oos-storage worktree, one focused round: does CDC-with-OOS gate the
   feat/oos → develop merge? The `cbrd-26847` report already recommended keeping it as a gate; the OOS epic lists
   "CDC flashback OOS OID 미해석" as open. Record the outcome as an ADR.
2. **If it gates**:
   - `/cubrid-oos-context` to load the OOS design context.
   - `/diagnosing-bugs` for the crash. The tight feedback loop already exists: `cbrd_27064` case 2 (single DELETE
     sweep, 700 rows, ~157 s) in the isolated container runner, debug build, watch for
     `pgbuf_fix_debug page_buffer.c:2487` / `oos_check_head_header oos_file.cpp:2600` from `cdc_make_dml_loginfo`.
   - Two layers of fix, both worth tickets:
     - **Fail soft** (small): `oos_read` returns an error on non-head chunk or deallocated page instead of
       asserting, so `cdc_make_dml_loginfo` fails the record and `cub_server` survives. `/tdd` with a unit test
       under `unit_tests/oos` for the non-head-chunk and deallocated-page paths.
     - **Lifetime** (design): implement CBRD-26939's chosen candidate (materialize OOS payloads into the
       supplemental log, or pin OOS chains until the CDC/flashback safe LSA passes). If the candidate is not yet
       chosen, `/grill-with-docs` again on the trade-off table in the draft before `/to-spec`.
   - `/cubrid-jira-issue-write` to publish CBRD-26939 (the local draft is from `725a32c`; refresh it with the
     `2940b1c` stacks and the CBRD-26786 signature change), then `/cubrid-pr-create` per fix.
3. **If it does not gate**: record the ADR, add both tests to the known-failing list for the tracking PR, and
   leave CBRD-26939 as a post-merge ticket.

### 3. Process guards (no skill)

- After every develop → tc/pr-6864 merge: `gh pr view 3782 --repo CUBRID/cubrid-testcases-private-ex --json files`
  diffed against the known OOS-TC file set. A missing file is a regression before CI runs. Ten lines of shell;
  put it in the justfile `ctp` module.
- Make `bug_bts_9836`/`bug_bts_14120` strip the three OOS error codes before comparing, or reserve OOS error-code
  numbers before the develop merge. Otherwise group A recurs at every merge that adds an error code.

### 4. bug_bts_6938

Nothing now. It passed on CircleCI with the same build and testcases. If it fails on GHA again, `/diagnosing-bugs`
with the isolated single-test run as the loop; until then it is a flake candidate.

### 5. Report hygiene

- `/grill-with-docs` on `ci_analysis_report_2940b1c_claude.md` before it goes to maintainers (the skill contract
  asked for it; it was not invocable from the analysis session).
- The `Check TC PRs` check stays red until TC PRs #3159 and #3782 merge or close. Expected; say so in the PR
  description so reviewers stop asking.

## Session boundary

The analysis session is at a boundary (analysis → fixes). **Continue** it for path 1: the answer paths, refs, and
verification commands are already in context and the work is small. Start path 2 fresh, in a new worktree, with
this file and the CI report as the hand-off; use `/handoff` only if the work goes to another person or harness.
