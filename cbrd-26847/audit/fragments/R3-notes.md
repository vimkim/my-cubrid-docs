# R3 — Reverse audit: replication / HA record-image paths

Source anchor: `6816023df4ed910687523ab4d34bf667ab32b9cd` (read-only). Scope: replication log
generation (server), HA applier (client `la_*`), `xlocator_repl_force` / `locator_repl_*` /
`locator_oos_insert_force` (server apply), and new-style stream replication (absent — see ledger).

## Bottom line

**Does replication ship logical values (safe) or raw physical images (needs Expand)?**
Per operation type:

| Operation | What travels master -> replica | OOS handling | Safe? |
|-----------|-------------------------------|--------------|-------|
| INSERT | repl log = packed **PK** + LSA pointer; applier reads the **raw master heap after-image** (with OOS inline stubs) from WAL and ships it in the copyarea; separate `LC_FLUSH_INSERT_OOS` items carry the **OOS value payloads** | replica does its **own** `oos_insert`, then `locator_fixup_oos_oids_in_recdes` overwrites each master head OID in the stub with the replica-local head OID before the heap insert | YES |
| UPDATE | same as INSERT (raw after-image + OOS payload items + PK) | same fixup | YES |
| DELETE | repl log = PK only; applier ships `recdes=NULL` | no record body, no stubs | YES |
| STATEMENT/SCHEMA | statement text / schema info | no record image | YES (n/a) |

So the replication **log record** never carries a raw heap RECDES image — it carries the PK
(`or_pack_mem_value`) plus an LSA into the WAL. The **raw physical image with OOS stubs** does travel,
but (a) through the applier reading the WAL redo image and (b) it is repaired on the replica: the
master's OOS head OIDs in the stubs are placeholders that `locator_fixup_oos_oids_in_recdes`
overwrites with replica-local OIDs after the replica performs its own `oos_insert`. The 8-byte full
length in each stub is preserved (value length is identical on both nodes). This satisfies the
invariants: replica OOS OIDs may differ, replica performs its own `oos_insert`, and no source OOS OID
is ever interpreted as a column value. **PRESERVE_PHYSICAL + OID fixup**, not Expand.

**What does `locator_add_or_remove_index_internal` do with OOS replication logs?** (R-202, FIND-R3-01)
When `heap_recdes_contains_oos(recdes)`, on the PK-index path (INSERT/DELETE) it loops
`thread_p->oos_oids` and emits one OOS replication log per master OOS OID
(`RVREPL_OOS_INSERT`, or `RVREPL_DUMMY_OOS_RECORD` when the OID is NULL / a multi-chunk marker),
carrying the PK and an LSA popped from `tdes->oos_insert_lsa_queue` that points at the master OOS
chunk WAL record. This matches the known refactoring item "Unnecessary OOS replication log in
`locator_add_or_remove_index`" (OOS repl-log emission sitting in index-maintenance code rather than
the natural heap-force path; see OOS-CONTEXT Optimization Idea B "Defer `oos_insert` to
`attrinfo_force`"). It is a code-placement/refactoring smell, **not** a correctness bug — the logs
are correct and the replica reconstructs values via the referenced chunk WAL records. Verdict FOLLOWUP.

## Master-side OOS repl-log plumbing (context)

- `tdes->oos_insert_lsa_queue` (`LOG_LSA_QUEUE`, `log_impl.h`) is pushed by the OOS insert WAL path
  (`log_manager.c`, `oos_file.cpp`: multi-chunk pushes `dummy_lsa` then `tail_chunk_lsa`).
- `repl_log_insert` for `RVREPL_OOS_INSERT` / `RVREPL_DUMMY_OOS_RECORD` pops those LSAs into
  `repl_rec->lsa` (`replication.c:459-470`), so the applier's `item->target_lsa` lands on the OOS
  chunk WAL record(s) it must read/rebuild.
- Master `thread_p->oos_oids` is built after heap insert by walking the record's stubs
  (`heap_file.c:27814 oos_oids.emplace_back`, gated by `heap_recdes_contains_oos`).

## Applier -> server flow (verified end to end)

1. `la_apply_oos_insert_log` (single) / `la_rebuild_oos_recdes` (multi) read the OOS chunk value(s)
   from WAL and add `LC_FLUSH_INSERT_OOS` copyarea items (payload = OOS value, header stripped later).
2. `la_apply_insert_log` / `la_apply_update_log` read the raw master heap after-image (stubs intact)
   via `la_get_recdes` and add `LC_FLUSH_INSERT` / `LC_FLUSH_UPDATE` items.
3. `xlocator_repl_force`: applies `LC_FLUSH_INSERT_OOS` first (`locator_oos_insert_force` ->
   replica `oos_insert` -> `thread_p->oos_oids.push_back`), then for the heap row runs
   `locator_fixup_oos_oids_in_recdes` and reinserts the (repaired) raw image.
4. `pending_oos_flush` / `need_oos_rebuild` sequence OOS items ahead of their heap row.

`la_get_current` (sql.log via `la_disk_to_obj`) is the only applier-side path that *parses* the
stub-bearing recdes into DB_VALUEs; it correctly detects `OR_IS_OOS` and resolves each OOS column
through the OOS value cache (`la_resolve_oos_value_for_sql_log`, keyed by master head OID), never
treating stub bytes as the value. RESOLVE, CORRECT (R-216).

## New symbols / aliases discovered

`RVREPL_OOS_INSERT` (recovery.h ~132), `RVREPL_DUMMY_OOS_RECORD` (recovery.h 135, "multi-chunk OOS
replication marker"), `RVOOS_INSERT`; `tdes->oos_insert_lsa_queue`; `LC_FLUSH_INSERT_OOS`;
`la_oos_cache_*` / `LA_OOS_CACHE_ENTRY` (sql.log OOS value cache); `la_rebuild_oos_recdes`,
`la_apply_oos_insert_log`, `la_apply_dummy_oos_log`, `la_get_oos_chunk_oid`, `la_append_oos_chunk`;
`locator_oos_insert_force`, `locator_fixup_oos_oids_in_recdes`, `bridge_locator_fixup_oos_oids_in_recdes`
(unit-test bridge); `heap_recdes_contains_oos`.

## Ambiguities / findings

- **FIND-R3-01 (FOLLOWUP)** — R-202: OOS repl-log emission in `locator_add_or_remove_index_internal`;
  known "Unnecessary OOS replication log in locator_add_or_remove_index" refactoring. Correctness OK.
- **FIND-R3-02 (OVER_EXPAND, low)** — R-223: `locator_repl_prepare_force` fetches the OLD replica
  record with `HEAP_RECDES_CONSUME_RAW_BYTES` (Expand), but `old_recdes` is not consumed as raw bytes
  after the function returns (`locator_update_force` is called with NULL `oldrecdes`). A downgrade to
  `HEAP_RECDES_DONT_CONSUME_RAW_BYTES` would avoid an unnecessary replica-side OOS Expand. Safe today
  (Expand is a superset). This is an explicit-policy site owned by the forward audit — cross-ref
  **fwd-locator** to avoid double-counting; flagged, not fixed (read-only audit).

## Cross-references (out of R3 scope)

- `load_server_loader.cpp` uses `heap_recdes_contains_oos` under an HA guard (loaddb bulk insert) —
  X-204, belongs to fwd-heap / fwd-misc, not the HA replication path.
- CDC / supplemental log (`la_*` overlaps none observed here beyond WAL log-data readers shared with
  recovery) — rev-cdc / rev-wal own those; the applier's WAL readers (`la_get_log_data`,
  `la_get_overflow_recdes`) are shared plumbing, accounted as X-203 duplicate of R-210.

## Search ledger

```text
검색 목적: replication 파일에서 OOS 소비 지점 식별
source anchor: 6816023df
명령: rg -n -i 'oos' src/transaction/replication.c src/transaction/log_applier.c
raw candidate 수: ~60 라인 (log_applier 대부분, replication.c 5)
included: R-201..R-217, R-220..R-223 로 수렴
excluded: 순수 cache 관리자(la_lookup/clear/cache_oos_value) — 저장 헬퍼, 소비 아님
duplicate: la_get_overflow/relocation_recdes -> R-210 (X-203)
pending: 0
새 symbol: oos_insert_lsa_queue, RVREPL_OOS_INSERT/DUMMY, LC_FLUSH_INSERT_OOS
```

```text
검색 목적: repl 로그 생성 payload 형태 (RECDES image vs packed value)
source anchor: 6816023df
명령: read replication.c:280-520 repl_log_insert; grep repl_log_insert callers in locator_sr.c
raw candidate 수: repl_log_insert 호출 5종 (DATA insert/delete/update, OOS insert/dummy, statement)
included: R-201(DATA), R-202(OOS in add_or_remove_index), R-203(OOS in update_force)
excluded: X-201 repl_log_insert_statement (문장 텍스트, 이미지 아님), X-202 *_log_dump (디버그)
duplicate: 0
pending: 0
결론: 로그 payload = packed PK + LSA. 물리 이미지 아님.
```

```text
검색 목적: 신형 stream replication 존재 여부
source anchor: 6816023df
명령: ls src/replication; rg -ln 'log_generator|log_consumer|cubstream|stream_entry|replication_stream' src
raw candidate 수: 0
included: 0
excluded: n/a
duplicate: 0
pending: 0
결론: 이 브랜치는 고전 HA(log_applier + xlocator_repl_force)만 존재. 신형 stream repl 부재. Task item 4 = N/A.
```

```text
검색 목적: replica 측 raw recdes 재삽입 + stub OID 처리
source anchor: 6816023df
명령: read xlocator_repl_force(7004-7220), locator_repl_prepare_force(6886-6960),
      locator_oos_insert_force(5287-5339), locator_fixup_oos_oids_in_recdes(14166-14263)
raw candidate 수: 4 (repl_force, prepare_force, oos_insert_force, fixup)
included: R-220, R-221, R-222, R-223
excluded: 0
duplicate: 0
pending: 0
결론: raw 이미지 재삽입이지만 stub OID를 replica-local OID로 fixup -> source OID 유출 없음. CORRECT.
```
