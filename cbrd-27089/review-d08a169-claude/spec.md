# PR #7927 — Spec review

Reviewed 2026-09-18: `38093ea859a8a08e20405b72b0cb395205bedb2f...d08a169ef5da45dcc4a4fe71c5a131aaf3e6057e`. Independent Spec reviewer, escalated to adversarial verification after the third major finding. Spec sources: the PR body's stated contract, the CBRD-27089 issue drafts (vacuum OOS-VFID abort, partition OOS owner), the deferred-write design docs (`CBRD-27089-deferred-write_bffe13b_claude.md`, `_be7c01a_codex.md`), and the normative OOS specification (`OOS-CONTEXT.md`). All claims verified against code at the PR head, not commit messages. Links pin `d08a169ef`.

**Verdict: REVISE** — no critical findings; all three majors are undisclosed scope or robustness gaps, not violations of the core contract.

## Verified clean

- **Destination ownership** ("write chain AND record together into THAT heap's OOS file"): [locator_sr.c:5063](https://github.com/CUBRID/cubrid/blob/d08a169ef5da45dcc4a4fe71c5a131aaf3e6057e/src/transaction/locator_sr.c#L5063) calls `finalize (thread_p, &real_class_oid)` only after pruning; `heap_oos.cpp:641` resolves that class's HFID/OOS VFID. No path writes a chain before destination selection.
- **Identity stamp** ("the prepared request receives the head identity stamp and the finalizer writes it together"): propagated via `oos_file.hpp:110` `identity_stamp_out` → `or_put_bigint (oos_pack_identity_stamp (...))` in `heap_file.c`; the inline stub stays 24 bytes per the normative spec.
- **No-recopy claim** ("does NOT re-copy the OOS payload for finalization"): requests hold pointers into `col.bytes`; no payload memcpy occurs in `finalize`.
- **Probe suppression** ("duplicate-key probes read only the prepared key and write no chains"): probe paths never call `finalize`.
- **No double-finalize on partition move**: [locator_sr.c:6061](https://github.com/CUBRID/cubrid/blob/d08a169ef5da45dcc4a4fe71c5a131aaf3e6057e/src/transaction/locator_sr.c#L6061) returns after the first finalization.
- **Demotion policy untouched**; the +1442 test lines in `test_oos_sql_show.cpp` are all on-topic (destination ownership, probes, loader, rollback) — **not** scope creep; the Python-runner removal is net-zero within the diff range.

## Major findings

1. **Undisclosed loaddb data-placement change.** Pre-PR `origin/feat/oos:load_server_loader.cpp:741` hardcoded `int pruning_type = 0;`; now [:1239](https://github.com/CUBRID/cubrid/blob/d08a169ef5da45dcc4a4fe71c5a131aaf3e6057e/src/loaddb/load_server_loader.cpp#L1239) derives `DB_PARTITIONED_CLASS`/`DB_PARTITION_CLASS`, [:403](https://github.com/CUBRID/cubrid/blob/d08a169ef5da45dcc4a4fe71c5a131aaf3e6057e/src/loaddb/load_server_loader.cpp#L403) takes `BU_LOCK` on every partition, and [:842](https://github.com/CUBRID/cubrid/blob/d08a169ef5da45dcc4a4fe71c5a131aaf3e6057e/src/loaddb/load_server_loader.cpp#L842) changes `op_type` from `MULTI_ROW_INSERT` to `SINGLE_ROW_INSERT`. This changes where loaded rows land and when unique constraints are checked, against the PR body's "저장/통신 format, demotion 정책, SQL 의미는 바꾸지 않습니다." Confidence high. Fix: disclose it in the PR body (it reads as a latent bug fix) or split it out.
2. **No in-repo coverage for the replica atomic-apply change.** [locator_sr.c:7178](https://github.com/CUBRID/cubrid/blob/d08a169ef5da45dcc4a4fe71c5a131aaf3e6057e/src/transaction/locator_sr.c#L7178) `row_topop_active` adds a new hard `ER_GENERIC_ERROR` when a copy area splits an OOS group; commit `d08a169ef` removed the replication runner and no added `TEST_F` exercises `xlocator_repl_force`. The spec asked that "복제 경로가 같은 준비 → 기록 계약을 따릅니다." Fix: add a test or cite the cubrid-testcases location that covers it.
3. **Bounds-checked writer replaced by unchecked memcpy.** [heap_file.c:14310](https://github.com/CUBRID/cubrid/blob/d08a169ef5da45dcc4a4fe71c5a131aaf3e6057e/src/storage/heap_file.c#L14310) and [:14327](https://github.com/CUBRID/cubrid/blob/d08a169ef5da45dcc4a4fe71c5a131aaf3e6057e/src/storage/heap_file.c#L14327) memcpy into the precomputed buffer with no `endptr` check, guarded only by the debug-only `assert` at [:14338](https://github.com/CUBRID/cubrid/blob/d08a169ef5da45dcc4a4fe71c5a131aaf3e6057e/src/storage/heap_file.c#L14338), replacing `heap_attrinfo_transform_to_disk_internal`'s `S_DOESNT_FIT` grow-and-retry. Mitigated by the capacity deriving from the same serialized lengths, hence downgraded from critical. Fix: check `cursor + length <= buf.endptr` before each memcpy.

## Minor findings

- [locator_sr.c:6662](https://github.com/CUBRID/cubrid/blob/d08a169ef5da45dcc4a4fe71c5a131aaf3e6057e/src/transaction/locator_sr.c#L6662) `locator_prepare_client_row` silently skips preparation when `!catcls_Enable` or the class is ROOT/system — a real exception to the PR's universal prepare→write claim (safe in practice: such classes are never partitioned).
- `heap_attrinfo_dbvalue_to_recdes` now returns bytes-written instead of `get_disk_size_of_value` and rejects `length <= 0`; the changed contract is shared with the pre-existing OOS path at `heap_file.c:13242`.
- The loader error gate changed from `er_has_error ()` to `m_session.is_failed ()`.
