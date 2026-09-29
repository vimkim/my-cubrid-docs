# PR #7990 CI repair ledger

> Historical ledger for the revisions below. Archived during cleanup on 2026-09-29.
> The 2026-09-22 [OOS scope decision](https://github.com/vimkim/cubrid-oos-context/blob/75f8b58674ac901d478ba60f9b2cc2fff11f66f6/docs/adr/0005-defer-oos-history-from-the-11-5-merge.md)
> deferred durable CDC/flashback history from PR #7990 and the 11.5 merge. The authorization
> and next action below record the earlier workflow; they are not a current instruction to
> publish changes or rerun that historical head.

- PR: https://github.com/CUBRID/cubrid/pull/7990
- Failed snapshot head: `2c792b423`
- Repaired engine head: `e7580f6714e2480833d57fe11eb427cf741af270`
- CCI dependency: `f271140d70c179775c1fa50e72fbeec848ca8ac0`
- Public testcases: `8be3e498c2eecadbe512d6e57703c59873acfcc1`
- Private testcases: `843aa7d888287afa78fe637e9c1fd9ba6be56ae5`
- Work tracker: `#180`
- State: exact-head CI completed; medium and SQL passed, while three shell cases require rerun/analysis

## Failure inventory

- Medium: `7105`
- SQL: `bug_bts_10516`, `fbo_ddl02`
- Shell: `cbrd_25080`, `cbrd_27064`, `bug_bts_14120`, `bug_bts_9836`, `cbrd_27075`

The failures split into expected-output drift from the OOS record-format change and a real compatibility gap in CDC/history handling. The repair retains OOS history across the required lifecycle, returns explicit client-visible errors for unsupported historical images, aligns CCI error-code numbering with the engine, and updates only the affected testcase expectations.

## Review and local verification

- Two-axis review (repository standards and PR specification): no remaining findings.
- Full debug GCC build/install completed; the wrapper's final nonzero result was only its active-process runtime-manifest guard after installation.
- Incremental compile: 83/83 targets.
- Focused OOS CTest: 6/6 passed.
- CDC lifecycle: default, fault-injection, and 16 KiB incompressible variants passed.
- Exact `2c792b423` baseline to repaired-head compatibility lifecycle passed all cases.
- `git diff --check` passed.
- Original CTP cases were not replayed locally because the runtime guard detected the active Codex process; their changes are deterministic expected-output updates.

## Authorization

The user approved the reviewed commits and then authorized publication with: “create PR there too. and do what you need to do.” The intended sequence is CCI PR, public testcases, private testcases, engine pointer, then one `/run all` trigger on the verified engine head.

## Next action

Analyze or rerun the three shell failures from CI run https://github.com/CUBRID/cubrid/actions/runs/35636610962 for exact engine head `e7580f6714e2480833d57fe11eb427cf741af270`. The supported targeted command is `/run rerun 35636610962`.

## Exact-head CI result

- Medium: 975/975 passed; no cases left unrun.
- SQL: 17,466/17,466 passed; no cases left unrun.
- Shell: 3,253 passed, 3 failed, 30 skipped; no cases left unrun.
- Failed shell cases:
  - shard 08: `shell/_37_elderberry/cbrd_23842_cdc/supp/supp19/cases/supp19.sh`
  - shard 09: `shell/_28_features_844/issue_11202_temp_volume_create/cases/issue_11202_temp_volume_create.sh`
  - shard 43: `shell/_06_issues/_19_2h/cbrd_23119/cases/cbrd_23119.sh`

## Follow-up diagnosis of the two apparently unrelated shell failures

### `issue_11202_temp_volume_create`

This is a pre-existing threshold-sensitive testcase, not attributable to the repair commit. It compares the exact count of temporary-volume `DISK_EXTEND` event pairs. Under the same isolated harness:

- exact repaired head, local debug build: fail / pass / fail;
- exact baseline `2c792b423` CI artifact: pass / fail.

Every failure had the same difference as CI: one additional TEMPORARY_VOLUME extension start/completion pair immediately before the final `EXTEND_VOLUME_INFO`. The behavior being tested still occurred; only the exact number of volume extensions varied. The testcase should assert the required event semantics without fixing a boundary-sensitive extension count.

### `cbrd_23119`

This is a regression introduced by the repair commit:

- exact baseline `2c792b423` CI artifact: local pass with the expected “Continue without present archive. (Partial recovery).” result;
- exact repaired `e7580f671` CI artifact: local failure matching CI;
- local exact-head debug build: two matching failures.

The testcase intentionally removes `log/db23118_lgat` before point-in-time media restore. The repair added an unconditional call to `logpb_sync_history_compatibility()` when the restored log header has compatibility 11.6. During this restore path `log_Gl.append.vdes` is not a valid mounted active-log descriptor, so `fsync(log_Gl.append.vdes)` fails with `EBADF` at `src/transaction/log_page_buffer.c:1609`. `log_initialize_internal()` then takes its fatal path at `src/transaction/log_manager.c:1587`, preventing the previous partial-recovery behavior.

The repair must preserve the durability fence for normal history activation/restart while avoiding or deferring that sync until a valid active-log descriptor exists during media restore.

## Publication receipts

- CCI draft PR: https://github.com/CUBRID/cubrid-cci/pull/112
- Public testcase draft PR: https://github.com/CUBRID/cubrid-testcases/pull/3551
- Private testcase draft PR: https://github.com/CUBRID/cubrid-testcases-private-ex/pull/4210
- Dependency summary comment: https://github.com/CUBRID/cubrid/pull/7990#issuecomment-5765242191
- `/run all` trigger: https://github.com/CUBRID/cubrid/pull/7990#issuecomment-5765243358

The automatic TC Merge Gate failed because both testcase PRs are intentionally still open as drafts. That gate blocks final engine merge until the testcase PRs are merged or closed; it does not prevent the regression suites from running.
