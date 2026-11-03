# OOS 회수 대안 B2, B3의 엔진 사실

작성 2026-11-04 (Asia/Seoul). 엔진 `feature/oos-merge` `dcbf09e4f7fd02ff9c8fc6493ec8887fc2919d67`.

이 보고서는 [추가 대안 검토](reclaim-decisions.md#추가-대안-검토)의 근거다. 조사 agent가 엔진 소스를 읽기만 하고 썼으며, 빌드나 실행은 하지 않았다. 본문은 agent가 쓴 영어 원문 그대로다. 표시 CONFIRMED는 코드에서 읽었다는 뜻이고, INFERRED는 읽은 코드에서 추론했다는 뜻이다. "explorer read"는 agent가 하위 조사에 맡기고 다시 읽지 않은 주장이다.

추가 대안 검토의 판단을 좌우한 주장 여섯 개는 문서 작성자가 소스에서 다시 확인했다.

- MVCC 레코드는 유효한 트랜잭션 MVCCID가 있어야 쓸 수 있다(`log_append.cpp:966-971`).
- commit은 postpone 실행(`log_manager.c:5285`) 전에 `logtb_complete_mvcc`(`5267`)를 부르고, 그 안에서 MVCC 정보를 지운다(`log_tran_table.c` 4409 근처의 `curr_mvcc_info->reset ()`).
- abort는 `log_rollback`(`log_manager.c:5383`)을 끝낸 뒤에 `logtb_complete_mvcc`(`5396`)를 부른다.
- release 빌드의 `vacuum_heap`은 오류를 지우고 진행하며(`vacuum.c:1606-1615`), 그러면 block은 끝난 것으로 표시된다(`vacuum.c:3785-3799`).
- sysop을 열지 않은 vacuum worker는 undo 로그를 건너뛴다(`log_manager.c:4394-4399`).
- `btree_load`는 oldest visible MVCCID를 한 번 읽고(`btree_load.c:1505`), 그보다 오래된 삭제만 건너뛴다(`btree_load.c:5986`).

---

Engine: `/home/vimkim/gh/cb/feature-oos-merge` at `dcbf09e4f7fd02ff9c8fc6493ec8887fc2919d67`. Read-only investigation. Nothing was built or run, so every fact below comes from reading source. All paths are relative to that checkout.

Labels. CONFIRMED means I read the code and saw it. INFERRED means reasoned from code I read, without seeing the behavior itself.

Purpose. Give the TLA+ models of B2 ("reclaim first") and B3 ("head MVCC mark") the engine facts they need before ADR-0008 is confirmed.

Short vocabulary used below.
- REMOVE: `VACUUM_RECORD_REMOVE`, the verdict of `mvcc_satisfies_vacuum` when a record's delete MVCCID is older than the threshold.
- Threshold: `log_Gl.mvcc_table.get_global_oldest_visible ()`, the "oldest visible MVCCID".
- Forward-walk: today's UPDATE cleanup. Vacuum reads the old record from the `RVHF_UPDATE_NOTIFY_VACUUM` undo image and deletes the chains it names (`vacuum_forward_walk_reclaim_oos`).

---

## Q1. Does vacuum check commit or abort? Is undo always finished before the MVCCID goes inactive?

Verdict: CONFIRMED. Vacuum never asks whether a delete MVCCID committed or aborted. The engine instead orders every abort as "undo everything, then complete the MVCCID", and every commit as "pin the threshold at the committer's MVCCID until the commit record is appended". So a delete MVCCID below the threshold in a record header implies the deleter committed, because an aborted deleter's header change was already undone. Three gaps are listed at the end (forward-walk, undo failure, restart window).

### Vacuum compares numbers only

- `src/transaction/mvcc.c:320-374` `mvcc_satisfies_vacuum`. The whole decision is on header fields and the threshold:
  - `if (!MVCC_IS_HEADER_DELID_VALID (rec_header) || MVCC_IS_REC_DELETED_SINCE_MVCCID (rec_header, oldest_mvccid))` then the record is not removable (`VACUUM_RECORD_CANNOT_VACUUM` or `VACUUM_RECORD_DELETE_INSID_PREV_VER`).
  - else `return VACUUM_RECORD_REMOVE` (line 372), with the comment "The deleter transaction has committed and the record is not visible to any running transactions".
  - `mvcc.c:58-62`: `MVCC_IS_REC_DELETED_SINCE_MVCCID(h, id)` is `!MVCC_ID_PRECEDES (h->mvcc_del_id, id)`. REMOVE therefore means `delid < threshold`.
- No status lookup exists. `logtb_is_mvccid_committed` is declared at `src/transaction/log_impl.h:1204` and has no definition anywhere under `src/` (grep). `mvcctable::complete_mvcc` records only an "inactive" bit plus an event type, not a per-MVCCID outcome (`src/transaction/mvcc_table.cpp:483-485`).
- Callers of `mvcc_satisfies_vacuum`: `src/query/vacuum.c:1805` (heap REMOVE decision, threshold sampled once per block at `vacuum.c:3446`), `vacuum.c:7630` (debug check) and `vacuum.c:7926` (undo-time check).

### Threshold definition

- `src/transaction/mvcc_table.cpp:355-420` `compute_oldest_visible_mvccid`: minimum of the global lowest-active MVCCID and every transaction's `m_transaction_lowest_visible_mvccids[idx]` slot. A completed transaction's slot is normally NULL, so it no longer holds the threshold down.
- `mvcctable::update_global_oldest_visible` (`mvcc_table.cpp:636-649`) stores it. The vacuum master refreshes it each iteration (`vacuum.c:3192`) and dispatches a block only when `newest_mvccid < m_oldest_visible_mvccid` (`vacuum.c:3287`).

### Abort path order (full rollback)

`src/transaction/log_manager.c`, `log_abort` (5552) calls `log_abort_local` then `log_complete` (5625-5626).

1. `log_abort_local` (5367-5424): `tdes->state = TRAN_UNACTIVE_ABORTED` (5372).
2. `log_rollback (thread_p, tdes, NULL)` (5383) undoes every undo record. Each record is undone by `log_rollback_record` (7457), which logs a compensate record (`log_append_compensate`, 7606) then calls the undo function.
3. `logtb_complete_mvcc (thread_p, tdes, false)` (5396; in the no-log-tail branch 5414). This is the first point the MVCCID leaves the active set: `mvcctable::complete_mvcc` calls `set_inactive_mvccid` (`mvcc_table.cpp:483`) and, for abort, sets the transaction's lowest-visible slot to NULL (`mvcc_table.cpp:508-512`).
4. `lock_unlock_all` (5399) releases locks after that.
5. `log_complete` appends the LOG_ABORT record afterwards (`log_manager.c:5796-5799`, `log_append_abort_log` defined at 4907).

So undo happens before the MVCCID turns inactive, and the abort record comes after both. Other abort entry points (`log_abort_by_tdes` at 1645, `log_abort_task_execute` at 10959) call `log_abort` (1656). `logtb_complete_mvcc` has exactly three production callers: `log_manager.c:5267` (commit), `5396`, `5414` (abort). 2PC reaches the same two functions (`src/transaction/log_2pc.c:568-607, 757, 803, 2535, 2575`).

### Commit path order and the pin

`log_commit_local` (`log_manager.c:5249-5352`):

1. `logtb_complete_mvcc (…, true)` first (5267), because it logs unique statistics. The comment at 5254-5261 says no logging may follow the state change.
2. `tdes->state = TRAN_UNACTIVE_WILL_COMMIT` (5269), postpone actions run (5284), then the commit record is appended (5308/5312), locks released (5317), `log_change_tran_as_completed` (5321).
3. The MVCCID is already inactive at step 1, before the commit record exists. Vacuum is protected by a pin: `mvcctable::complete_mvcc` on commit raises the transaction's lowest-visible slot to its own MVCCID (`mvcc_table.cpp:490-507`), comment: "be sure that transaction modifications can't be vacuumed up to LOG_COMMIT. Otherwise ... the system crash before LOG_COMMIT of current transaction ... will corrupt the database".
4. The pin is released only in `log_complete` after the commit record: `log_manager.c:5810` (`unlock_global_oldest_visible_mvccid`) and `5814` (`reset_transaction_lowest_active`, commit only).

Consequence for models: "MVCCID inactive" is not the same as "commit record durable". The threshold moves past a committer's MVCCID only after the commit record is appended.

### Partial (statement or savepoint) rollback

- `log_abort_partial` (`log_manager.c:5649-5728`): `log_sysop_start` (5699), set the sysop's `lastparent_lsa` to the savepoint LSA (5701), `log_sysop_abort` (5716). It never calls `logtb_complete_mvcc`: the transaction's MVCCID stays active and the code at 5649-5728 does not touch `tdes->mvccinfo`. CONFIRMED by reading the whole function.
- `log_sysop_abort` (4126-4176): `log_rollback (…, LOG_TDES_LAST_SYSOP_PARENT_LSA (tdes))` at 4159, then appends `LOG_SYSOP_END_ABORT` (4163-4166).
- Sub-transaction MVCCIDs (used only by the selupd/increment path, `src/query/query_executor.c:15633`): on error `log_sysop_abort` runs first (`query_executor.c:15735-15739`) and `logtb_complete_sub_mvcc` runs at `exit:` afterwards (15689-15693, `log_tran_table.c:4925-4947`, `mvcc_table.cpp:540-563`). Same order: undo first, then inactive. `complete_sub_mvcc` is called for both commit and abort of the sub-transaction.
- A log record's MVCCID is `sub_ids.back ()` when a sub-transaction is open, else the main id (`src/transaction/log_append.cpp:975-982`).

### Does vacuum start only after restart undo finishes? CONFIRMED yes

- `src/transaction/boot_sr.c:2435` `log_initialize (…)` runs `log_recovery` synchronously (`log_manager.c:1433`). `log_recovery` runs analysis, redo, undo, then 2PC finish in one call: `log_recovery.c:835-932` (undo phase at 888-896).
- `boot_sr.c:2450-2451`: "after recovery we can boot vacuum", then `vacuum_boot`. Only `vacuum_boot` creates the worker pool and the master daemon (`src/query/vacuum.c:1384-1409`).
- `vacuum_initialize` (`boot_sr.c:2404`) runs before recovery but only loads vacuum data ("We need to load vacuum data and initialize vacuum routine before recovery").
- The master also returns early until the server is marked restarted: `vacuum.c:3182-3186` (`BO_IS_SERVER_RESTARTED`), and `boot_server_status (BOOT_SERVER_UP)` is set at `boot_sr.c:2751`, after `vacuum_boot`.
- INFERRED only: stand-alone mode runs vacuum through `vacuum_sa_run_job` (`vacuum.c:958`). I did not read that path.

### Gaps in the "delete MVCCID below threshold implies commit" rule

1. The forward-walk does not read a header. It reads the undo image of an UPDATE log record (`vacuum.c:3616-3625`, `vacuum_forward_walk_reclaim_oos` in `src/query/vacuum_oos.cpp:267-350`) and deletes the chains named there. Nothing checks whether that UPDATE committed. An aborted UPDATE's block is processed the same way, so the rolled-back original chain is deleted. This is CBRD-27237 (also in `docs/reference/implementation-observations.md` of `cubrid-oos-context`). CONFIRMED by code reading; the runtime reproduction is recorded there, I did not rerun it.
2. Undo errors are not fatal. `log_rollback_record` on an undo error does `er_set (…, ER_LOG_MAYNEED_MEDIA_RECOVERY …); assert (false)` and continues (`log_manager.c:7609-7619`, `7659-7669`), then the abort completes. In a release build the MVCCID turns inactive with part of the undo missing. Applies equally to heap headers and to any OOS header mark.
3. Restart window. At the end of the redo phase `reset_start_mvccid` makes every MVCCID below `mvcc_next_id` inactive (`log_recovery.c:4070`), before the undo phase runs (`log_recovery.c:894`). So during restart undo the rule "inactive implies undone" does not hold in the MVCC table. It is safe only because vacuum and clients are not running (see above). In-doubt 2PC-prepared transactions are re-marked active afterwards (`log_recovery.c:3289-3326`, called at 4074), so the threshold stays below them.

---

## Q2. Which log records enter vacuum blocks, and how are they dispatched?

Verdict: CONFIRMED. A record enters a vacuum block only if it is an undo-bearing MVCC record: `LOG_MVCC_UNDO_DATA`, `LOG_MVCC_UNDOREDO_DATA`, `LOG_MVCC_DIFF_UNDOREDO_DATA`, or a `LOG_SYSOP_END` of type logical-MVCC-undo. Whether a record gets an MVCC type is decided only by its rcvindex through the closed list `LOG_IS_MVCC_OPERATION`. The worker then dispatches on rcvindex, and only heap, B-tree, `RVES_NOTIFY_VACUUM` and `RVHF_DELETE_NEWHOME_NOTIFY_VACUUM` are handled. An MVCC record with any other rcvindex reaches `assert_release (false)`: abort in a debug build, a logged notification and a skip in a release build. An `RVOOS_*` record is today non-MVCC and is never in a block.

### How a record becomes an MVCC record

- `src/transaction/mvcc.h:251-276`: `LOG_IS_MVCC_OPERATION (rcvindex)` is true for:
  - heap: `RVHF_MVCC_DELETE_REC_HOME`, `RVHF_MVCC_INSERT`, `RVHF_UPDATE_NOTIFY_VACUUM`, `RVHF_MVCC_DELETE_MODIFY_HOME`, `RVHF_MVCC_NO_MODIFY_HOME`, `RVHF_MVCC_REDISTRIBUTE`
  - B-tree: `RVBT_MVCC_DELETE_OBJECT`, `RVBT_MVCC_INSERT_OBJECT`, `RVBT_MVCC_INSERT_OBJECT_UNQ`, `RVBT_MVCC_NOTIFY_VACUUM`
  - `RVES_NOTIFY_VACUUM`, `RVOOS_NOTIFY_VACUUM`, `RVHF_DELETE_NEWHOME_NOTIFY_VACUUM`.
  - The `RVOOS_NOTIFY_VACUUM` clause carries a TODO: "currently has no emitter" (`mvcc.h:268-270`, `src/transaction/recovery.h:206-208`).
- `src/transaction/log_manager.c:2173, 2318, 2455`: the record type is `LOG_IS_MVCC_OPERATION (rcvindex) ? LOG_MVCC_* : LOG_*`. Also `log_manager.c:4037` for logical-undo sysop end.
- OOS records today: `oos_log_insert_physical` / `oos_log_delete_physical` use `log_append_undoredo_recdes (RVOOS_INSERT / RVOOS_DELETE …)` (`src/storage/oos_file.cpp:3202, 3221`). Neither rcvindex is in the list, so they are plain `LOG_UNDOREDO_DATA`. RV_fun entries: `RVOOS_INSERT` undo `oos_rv_redo_delete`, redo `oos_rv_redo_insert`; `RVOOS_DELETE` undo `oos_rv_redo_insert`, redo `oos_rv_redo_delete` (`src/transaction/recovery.c:881-892`). `RVOOS_NOTIFY_VACUUM` is a no-op stub (`recovery.c:905-912`, handler `vacuum_rv_es_nop`).

### What gets chained into vacuum blocks

- Answer to "every LOG_MVCC_* record regardless of rcvindex?": almost. The chaining test looks at the record type only, never at rcvindex (`src/transaction/log_append.cpp:1413-1416`), so every undo-bearing MVCC record is chained whatever its rcvindex. `LOG_MVCC_REDO_DATA` is the exception: it is not chained.
- `src/transaction/log_append.cpp:1411-1452` `prior_lsa_next_record_internal`: only `LOG_MVCC_UNDO_DATA`, `LOG_MVCC_UNDOREDO_DATA`, `LOG_MVCC_DIFF_UNDOREDO_DATA` and `LOG_SYSOP_END` with `LOG_SYSOP_END_LOGICAL_MVCC_UNDO` get `vacuum_info.prev_mvcc_op_log_lsa` and update the block header (`prior_update_header_mvcc_info`, `log_append.cpp:1340-1366`: first MVCC record in a block sets `oldest_visible_mvccid`, every record raises `newest_block_mvccid`).
- `LOG_MVCC_REDO_DATA` (redo-only MVCC) has no `vacuum_info` and is not chained (`log_append.cpp:898-911, 986-1016`). A redo-only MVCC record therefore never reaches a vacuum worker.
- Every chained record needs a non-NULL `addr->vfid` (else `assert_release (false)` and `ER_FAILED`, `log_append.cpp:995-1012`; only `RVES_NOTIFY_VACUUM` may pass NULL).
- Every MVCC record needs a valid transaction MVCCID at append time (else `assert_release (false)` and `ER_FAILED`, `log_append.cpp:966-973`). After `logtb_complete_mvcc` the transaction's MVCC info is reset (`log_tran_table.c:4409`, `mvcc.c:761-770`), and commit runs postpone actions after that call (`log_manager.c:5267` then `5284`). INFERRED: an MVCC-typed log record cannot be appended from a postpone action run at commit.
- A block is handed to a worker when `newest_mvccid < oldest_visible` (`vacuum.c:3287`). Debug builds assert every record's MVCCID is below the threshold and inside the block's bounds (`vacuum.c:3576-3585`).

### Worker dispatch by rcvindex

- `vacuum_process_log_record` (`vacuum.c:4121-4344`) reads the MVCC header of each chained record type and returns the undo image only for a whitelist: B-tree ops, `RVHF_UPDATE_NOTIFY_VACUUM`, `RVES_NOTIFY_VACUUM`, `RVHF_DELETE_NEWHOME_NOTIFY_VACUUM` (`vacuum.c:4275-4283`). Any other rcvindex returns before unpacking the undo data.
- `vacuum_process_log_block` (`vacuum.c:3428-3824`) branches, in order:
  1. `LOG_IS_MVCC_HEAP_OPERATION` (3587): collect the heap OID (`vacuum_collect_heap_objects`, 3594); if rcvindex is `RVHF_UPDATE_NOTIFY_VACUUM` also run the forward-walk (3616-3625).
  2. `LOG_IS_MVCC_BTREE_OPERATION` (3627-3741).
  3. `RVES_NOTIFY_VACUUM` (3742): delete the LOB file.
  4. `RVHF_DELETE_NEWHOME_NOTIFY_VACUUM` (3757-3770): forward-walk only.
  5. else (3771-3775): `/* Safeguard code */ assert_release (false);`.
- `assert_release` is `assert (e)` in debug and `er_set (ER_NOTIFICATION_SEVERITY, …, ER_FAILED_ASSERTION …)` in release (`src/base/error_manager.h:189-197`). So in release an unknown MVCC rcvindex is logged and skipped, the loop continues to the next record. In debug the server asserts.
- Answer to "would an `RVOOS_*` MVCC record be processed or ignored without new code": a new rcvindex that is not added to `LOG_IS_MVCC_OPERATION` is not an MVCC record at all (never chained, never seen by vacuum). One that is added reaches the safeguard branch, so it is ignored in release and asserts in debug. Any B3 mark needs a new branch in `vacuum_process_log_block`, an entry in the undo-image whitelist if it needs undo data, an `LOG_IS_MVCC_OPERATION` entry, and a non-NULL vfid.
- Dropped-file filtering uses the record's vfid (`vacuum.c:4243-4272`). `vacuum_log_add_dropped_file` is called only for heap and B-tree vfids (`src/storage/heap_file.c:5061, 5532, 5598`, `btree*.c`). INFERRED: a record stamped with an OOS file vfid would not be skipped when its table is dropped. Existing MVCC heap records stamp the heap vfid, and the forward-walk finds the OOS file through the heap vfid (`vacuum_oos.cpp:85-142`).

---

## Q3. Can two vacuum jobs REMOVE the same heap record? Is the home page latch held across the OOS chain delete?

Verdict: CONFIRMED yes to both. Blocks are independent jobs run in parallel. The same OID is collected from every block that holds an MVCC operation on it (insert, update, delete), and each job re-reads the record header under the home page WRITE latch and re-decides. An already removed slot is skipped, a reused slot is judged by its new header. The home page WRITE latch is held across the whole REMOVE, including `vacuum_heap_oos_delete_within_sysop`.

### Concurrency of jobs

- Worker pool: `vacuum_worker_count`, default 10, range 1 to 50 (`src/base/system_parameter.c:3848-3856`, `src/query/vacuum.h:132`).
- Master loop (`vacuum.c:3226-3245`) starts a job for every available ready block, pushing it to the pool (`start_job_on_cursor_entry`, 3332-3339), up to `3 * workers` outstanding (`vacuum.c:489, 3268`). It does not wait for earlier blocks, and skips entries already vacuumed or in progress (3313-3329).
- A heap OID can therefore be in two or more blocks (INSERT, UPDATE, DELETE records) and be processed by two workers at once. Within one job duplicates are sorted together and skipped (`vacuum.c:1571-1573, 1769-1773`).

### Handling of a record that is already removed or changed

- Each worker fixes the home page WRITE (`vacuum.c:1727-1728`; `pgbuf_fix_if_not_deallocated` on an interrupted re-run, 1686-1724), then for each OID calls `vacuum_heap_prepare_record` (1778), which reads the slot type and, for HOME or RELOCATION, copies the record and its MVCC header (2025-2262), and `mvcc_satisfies_vacuum` (1805).
- Already removed: `spage_vacuum_slot` leaves the slot as `REC_DELETED_WILL_REUSE` (reusable heap) or `REC_MARKDELETED` (`src/storage/slotted_page.c:4852-4860`). `spage_get_slot` returns the slot for any id below `num_slots` (4793-4804), so `record_type` is that type and the switch falls to `default:` with the comment "Object cannot be vacuumed. Most likely it was already vacuumed by another worker or it was rollbacked and reused." (`vacuum.c:1854-1858`). No OOS action happens. `slotp == NULL` (id beyond `num_slots`) is mapped to `REC_MARKDELETED` (2026-2031).
- The code relies on that type check never letting a second `spage_vacuum_slot` run: calling it on an already vacuumed slot only logs an error and then decrements `num_records` again (`slotted_page.c:4838-4849`). INFERRED corruption risk if the check were ever skipped.
- Reused slot: the new occupant is judged by its own header. A new row with no delete MVCCID and a recent insert id gives `CANNOT_VACUUM`; a visible-to-all, undeleted row gives `CANNOT_VACUUM` (`mvcc.c:323-351`). Only a record whose own `delid < threshold` can be REMOVEd. INFERRED: a later INSERT can take a vacuumed slot in a reusable heap, because vacuum marks it `REC_DELETED_WILL_REUSE`.
- Page status protocol: `HEAP_PAGE_VACUUM_NONE` goes to `ONCE` on the first MVCC op and to `UNKNOWN` on the second (`src/storage/heap_file.c:26855-26900`). A re-run after crash needs extra care, described at `vacuum.c:1872-1883`.
- Concurrent jobs on the same OOS chain: `oos_delete_chain` fixes the head page WRITE and compares the stored stamp with the reference's stamp under that latch. A second deleter no-ops on page gone, slot empty or stamp mismatch (`src/storage/oos_file.cpp:3242-3260, 3282-3360`, outcomes in `oos_file.hpp:61-75`). This is the existing idempotency mechanism (CBRD-26950).

### Home page latch across the whole REMOVE

- `vacuum_heap_record` (`vacuum.c:2464-2654`) never unfixes the home page. `has_oos` is computed at 2496-2498. For `REC_RELOCATION` or `has_oos` it calls `vacuum_heap_page_log_and_reset (…, false, false)` (2504) with `unlatch_page == false` (function at 2739-2799: the page is unfixed only at 2790-2793 when the flag is true), then `log_sysop_start` (2505).
- Order inside the one sysop, `REC_HOME` with OOS: `spage_vacuum_slot` in memory (2516); `vacuum_log_redoundo_vacuum_record` logs the slot removal with the full record as undo (2620, function 7733-7761; undo is `heap_rv_redo_insert`, 7771-7776); then `vacuum_heap_oos_delete_within_sysop` (2623); then `log_sysop_commit` (2631). On OOS error: `log_sysop_abort` (2627).
- `REC_RELOCATION`: the forward page is freed at 2557, then OOS deletes (2561-2570), then `log_sysop_commit` (2572). The home page stays fixed.
- Where the stubs are read from: for `REC_HOME` the home record copy, for `REC_RELOCATION` the forward `REC_NEWHOME` record copy (`helper->record`, `vacuum.c:2125-2130`, and `has_oos` tests that record at 2496-2498). The home slot of a relocated row holds only an 8-byte forwarding OID.
- `REC_BIGONE` and OOS cannot coexist (`vacuum.c:2583`, `assert (!RECORD_HEADER_HAS_OOS (…))`; `heap_file.c:14233-14238`). `vacuum_oos_find_vfid_for_heap_record` is only called for HOME and RELOCATION (`vacuum.c:2140, 2256`).
- Places where the home page is released mid-job: "release latch to favor other threads" between two objects (`vacuum.c:1945-1964`), and the conditional-latch retry for a relocated record's forward page (2086-2119, followed by `goto retry_prepare`). Neither occurs between slot removal and OOS delete.
- Empty OOS page deallocation is deliberately after unfix of the home page (`vacuum.c:1977-1987`).
- `vacuum_heap_oos_delete_within_sysop` (`vacuum_oos.cpp:447-485`) does not open its own sysop. Each chunk is a separate `RVOOS_DELETE` undo/redo record carrying the full chunk as undo (`oos_file.cpp:3378-3381`). Order inside a chain today: head chunk first, then along `next_chunk_oid` (`oos_file.cpp:3277-3418`), one page fixed at a time (3314-3317). That is the reverse of the "tail first, head last" order B2 proposes.
- Chain read for delete: references are `(head OID, identity stamp)`; the chain is walked from the head, so tail-first deletion needs a separate read pass first. The existing code never walks the chain without deleting.

---

## Q4. Readers that dereference OOS stubs without an MVCC snapshot

Verdict: CONFIRMED that readers exist which fetch heap records with no visibility filter and then follow OOS stubs, including records vacuum would already judge REMOVE. The record stays in its slot until the vacuum worker reaches it, and no reader compares the delete MVCCID with the threshold. What protects them today is one of four things (listed at the end of this section). Protection 1, the page latch, works only because vacuum removes the slot and deletes the chains under one continuous latch hold. So today a reader that holds the latch never sees "record present, chains gone". Only a reader that copies the record and reads OOS after releasing the latch can. A read of a chain that is already gone returns the error `ER_HEAP_OOS_CORRUPTED_RECORD` (-1389). The one assert on these paths is in debug builds, on a continuation chunk whose slot was reused mid-read.

Provenance. A sonnet explorer census produced the path list. I re-read these claims myself: the raw-byte call-site count, the NULL-snapshot fetch mode, the DELETE ordering, the btree_load filter, the two DDL pins, where expansion runs relative to the page latch, and the single caller of the old-version-from-log reader. The rest is marked "explorer read, not re-read".

### What a no-snapshot fetch returns

- `heap_get_visible_version_internal` (`src/storage/heap_file.c:27846-27946`) applies a visibility check only when `scan_cache->mvcc_snapshot` is set, its `snapshot_fnc` is set and the class is MVCC enabled (27881-27887). With a NULL snapshot it returns whatever version sits in the slot, including one that carries a delete MVCCID.
- `heap_get_last_version` (`heap_file.c:28069-28120`) never checks visibility.
- `heap_scancache_start` only stores the snapshot argument (`heap_file.c:6636, 6695-6700`). `LC_FETCH_CURRENT_VERSION` sets it to NULL (`src/transaction/locator_sr.c:2895-2897`).
- Expansion of stubs to bytes (`heap_record_replace_oos_oids`) runs inside `heap_get_record_data_when_all_ready` while the home page, and the forward page for relocated rows, are still fixed (`heap_file.c:7587-7648`, calls at 7620 and 7642). Attribute-layer reads (`heap_attrinfo_read_dbvalues`, `heap_attrvalue_read` at `heap_file.c:11540`, `11866`) read the stubs when called, which for a COPY fetch is after the page latch is gone.
- Old versions rebuilt from an UPDATE's undo image are read only for snapshot readers: `heap_get_visible_version_from_log` has one caller, `heap_get_visible_version_internal` at `heap_file.c:27911-27918`, in the `TOO_NEW_FOR_SNAPSHOT` branch (grep over `src/`).

### What happens when the chain is already gone (all CONFIRMED)

`oos_read` returns `ER_HEAP_OOS_CORRUPTED_RECORD` (-1389, `src/base/error_code.h:1795`, `ER_ERROR_SEVERITY`), returned as an error and never skipped, for each of:
- head page deallocated or no longer an OOS page: `src/storage/oos_file.cpp:2595-2601, 2809-2811`
- head slot empty: `oos_file.cpp:2610-2622` (`S_DOESNT_EXIST`)
- slot reused, stamp mismatch: `oos_file.cpp:2753-2763`; also a non-head target (2766-2772) and a length mismatch (2774-2780)
- `oos_read_many`: same codes (`oos_file.cpp:2902, 2927-2930, 2953-2956`, explorer read)
- Propagation: `read_into` returns the code (`heap_oos_value_ref.cpp:122`), the attribute layer returns it (`heap_file.c:11175-11185`), the expand layer returns `S_ERROR` (`heap_oos.cpp:629-632`).
- Chain deleted mid-walk, after the head was read and its page unfixed (`oos_file.cpp:2813-2833`): continuation chunk slot empty gives -1389 (2615); continuation page deallocated makes the plain `pgbuf_fix` fail and return `er_errid ()` (2681-2687); continuation slot reused gives `assert (idx == header.chunk_index)` in debug builds (2715-2716) and -1389 in release (2717-2723). That the interleaving can occur is INFERRED.
- A malformed stub is a different code, `ER_HEAP_OOS_BAD_INLINE_HEADER` (-1387, `heap_oos_value_ref.cpp:103-105`, explorer read).

### Paths

| Path | Snapshot | Follows stubs | What protects it today | Gone chain gives |
| --- | --- | --- | --- | --- |
| `xlocator_fetch_all` for unloaddb `--latest-image` (`locator_sr.c:2817`, mode switch 2895-2897, expand 2948-2949) | NULL | yes, expand under page latch, values needed | page latch only; class IS lock; no instance lock. Default unloaddb uses a snapshot. | error, unload aborts unless `ignore_err_flag` (explorer read) |
| `xlocator_lock_and_fetch_all` (compactdb server path, `locator_sr.c:12242`, raw-byte sites 12371, 12387) | snapshot for non-root classes | yes, expand | snapshot, instance X lock, page latch | `ER_FAILED`, class aborts (explorer read) |
| `xlocator_upgrade_instances_domain` (ALTER type change, `locator_sr.c:12532`) | NULL | yes | pins the threshold (`locator_sr.c:12587`, mechanism `mvcc_table.cpp:639-647`, release at `log_manager.c:5810, 6097`) and vacuums first (12591) | DDL fails |
| `redistribute_partition_data` (`locator_sr.c:13105`) | NULL | yes via attribute layer (`heap_prepare_oos_record`, `heap_file.c:13622, 13632`); copies delete-marked rows with their MVCC header | pins the threshold (`locator_sr.c:13157`), vacuums first (13183), holds the page WRITE latch | DDL fails (explorer read) |
| `btree_load.c` CREATE INDEX (scan at `btree_load.c:1235`) | NULL | yes, filter predicate and key generation read attributes | none found. It skips only records with `delid < sort_args->oldest_visible_mvccid`, a threshold read once at `btree_load.c:1506`; skip tests at 5986 and 6282. Records deleted after that threshold are read even if vacuum later becomes able to REMOVE them. It does not call `lock_global_oldest_visible_mvccid`. | not checked (INFERRED that an attribute read error fails the build) |
| DELETE index maintenance (`locator_delete_force_internal`, `locator_sr.c:6474-6510`) | n/a, the deleter's own copy | yes, `locator_add_or_remove_index` reads the copied record after `heap_delete_logical` | comment at 6477: "MVCC keeps the deleted version readable while indexes are updated". The deleter's own MVCCID is active, so the record cannot be REMOVE-eligible | error, DELETE fails (explorer read) |
| `locator_lock_and_get_object_internal` (`locator_sr.c:13387`) | none | no (all 9 callers use `DONT_CONSUME`); a record that passes the delete check is read later through the attribute layer by `locator_attribute_info_force` (`locator_sr.c:7772, 7886`; `heap_attrinfo_set_uninitialized`, `heap_file.c:14195`) | instance X lock plus the delete check (`locator_sr.c:13495, 13507`) | -1389 (explorer read) |
| HA applier `xlocator_repl_force` (`locator_sr.c:7135`) | by primary-key lookup | via the update and delete force paths above | class IX and instance X lock | -1389 (explorer read) |
| checkdb structural heap check (`heap_chkreloc_next`, `heap_file.c:17049-17200`) | none | no OOS symbol in the range | class SCH_S | n/a |
| checkdb index content checks (`locator_sr.c:9735, 10161`) | snapshot | yes, values of visible records | snapshot | checkdb reports failure |
| catalog scans (`catalog_class.c:4965, 5384, 5575`), `sp_get_code_attr`, `heap_dump`, dblink catalog | NULL | catalog classes carry no OOS in practice (INFERRED); `_db_stored_procedure_code` is OOS-capable (INFERRED); `heap_dump` skips on error | page latch under PEEK; MVCC-disabled classes delete physically | `heap_dump` prints and continues |
| class record reads (`heap_get_class_record`, `heap_file.c:28311`, about 45 callers) | none | class records carry no OOS (exempt: `heap_oos.cpp:59-62`, explorer read) | n/a | n/a |
| dirty-snapshot readers (`LC_FETCH_DIRTY_VERSION`, `mvcc_satisfies_dirty`) | dirty | yes, for a record deleted by another active transaction | the delete is not final, so the record is not REMOVE-eligible | n/a |
| snapshot readers of old versions (undo image) | snapshot | yes, chain named in the undo image | threshold gating: the chain must live until the UPDATE's MVCCID is below the threshold | -1389 if reclaimed too early |

Corrections to the carried spec note (`cubrid-oos-context/docs/reference/implementation-observations.md`, "CBRD-26847"): the code at this commit has 8 `HEAP_RECDES_CONSUME_RAW_BYTES` call sites, not 5: `locator_sr.c:2368, 2949, 3533, 12371, 12387` and `catalog_class.c:4010, 4176, 4503` (my grep). `redistribute_partition_data` is not one of them: it uses `DONT_CONSUME` and the attribute layer (explorer read). The suspected `xlocator_fetch_all` gap to unloaddb: the explorer found none (expansion at `locator_sr.c:2948-2949`, leftover stubs rejected with -1387 at 2192).

### The four protections, and which alternatives change them

1. Page latch. Vacuum removes the slot and deletes the chains in one sysop under the home page WRITE latch (Q3). A reader that expands or peeks while holding that page's latch sees the whole record and chain, or no record.
2. Lock plus delete check. Instance X lock, then an explicit check of the header's delete MVCCID that rejects a delete-marked record (`MVCC_IS_HEADER_DELID_VALID`, `locator_sr.c:13495, 13507`).
3. The deleter's own active MVCCID. While the deleter is active the record's `delid >= threshold`, so it is not REMOVE-eligible and its chains are live.
4. Threshold pin. Only the two DDL paths pin the global oldest visible MVCCID.

A reader that copies a record (COPY) with a NULL snapshot and reads OOS after releasing the page latch has only protection 2, 3 or 4, or none. `btree_load.c` has none, so INFERRED: it can already read a stub whose chain vacuum deleted after the copy, today. B2 does not change this by itself while the home page latch stays held from the first chunk delete to the slot removal. B2 changes it through two other routes, listed in the closing section: any release of that latch between the two steps, and the crash or sysop-abort states where the record survives with its chains gone.

---

## Q5. Does UPDATE fix, read or write the old chain? Where is chain reuse (CBRD-27230)?

Verdict: CONFIRMED. In MVCC mode (server mode, MVCC-enabled class) the UPDATE path neither writes nor deletes the old chain. It does READ the old chain (READ latch, `oos_read`) for every OOS attribute the statement did not assign, and then writes a NEW chain for every OOS-selected column, assigned or not. Chain reuse (CBRD-27230) is not implemented at this commit: `src/` has no mention of 27230 (grep returns nothing) and no code keeps an old stub into the new record.

### Reads of the old chain at UPDATE time

- `heap_attrinfo_transform_to_disk_internal` (`src/storage/heap_file.c:14170-14318`) first calls `heap_attrinfo_set_uninitialized (…, old_recdes, …)` (14195). That function (12932-13030) calls `heap_attrvalue_read` for every attribute still `HEAP_UNINIT_ATTRVALUE`, that is every attribute the statement did not assign (12985-12995), reading from the old record on disk.
- For a variable attribute whose offset-table entry marks OOS, `heap_attrvalue_read` (11540) goes through `heap_attrvalue_point_variable` to `heap_attrvalue_read_oos_inline` (11135), which decodes the stub and calls `oos_ref.read_into` (`src/storage/heap_oos_value_ref.cpp:109-122`), then `oos_read` (`src/storage/oos_file.cpp:2793-2843`). Head page: `oos_fix_page_if_oos (…, PGBUF_LATCH_READ, …)` at 2804. Continuation pages: `pgbuf_fix (…, PGBUF_LATCH_READ …)` at 2681.
- So the UPDATE reads (fixes with READ latch) the old chain's pages, one page at a time, before the new record exists. The old stub's stamp and head OID are checked by `oos_check_head_header` (2753-2782). A gone chain gives `ER_HEAP_OOS_CORRUPTED_RECORD` (-1389, `src/base/error_code.h:1795`).

### New chain is always written

- `heap_attrinfo_determine_disk_layout` (`heap_file.c:13137-13226`) selects OOS columns by size only (FORCE_OUTLINE, or largest-first until the record is at most `DB_PAGESIZE/4`). The plan structure `heap_oos_column_plan` (751-758) has no "reuse old stub" field.
- Selected values are written by `heap_attrinfo_insert_to_oos` (13511-13520, called at 14272) or retained as pending payloads (14245-14269). A column the statement did not assign is therefore read and rewritten as a fresh chain.

### Old chain is neither written nor deleted in MVCC mode

- Eager cleanup `heap_oos_delete_unreferenced` (`src/storage/heap_oos.cpp:953-1063`; it keeps a chain whose head OID is in both images, line 1023) is called only under `!is_mvcc_op`: guards at `heap_file.c:23951` (delete relocation), `24297` (delete home), `24729` (update relocation), `25214` (update home), calls at 23953, 24299, 24731, 25216. The comments at 24720-24728 and 25211-25213 state that in MVCC mode "old OOS is preserved for concurrent readers" and vacuum cleans it.
- In MVCC mode the old record is kept only in the undo image of `RVHF_UPDATE_NOTIFY_VACUUM` (`heap_file.c:25046-25049`, also 24614, 24843, 24932), or `RVHF_DELETE_NEWHOME_NOTIFY_VACUUM` when the old forward record is removed (24887-24893). The updated record keeps its OID and gets `prev_version_lsa` pointing at that undo record (`heap_update_set_prev_version`, 27964-28057; called at 25202 for home updates and 24975 for relocation).
- `RVOOS_NOTIFY_VACUUM` has no emitter (`recovery.h:206-208`). The only reclaim path for UPDATE-dropped chains is the undo-image forward-walk (Q1 gap 1).

### Where the spec puts reuse

Spec text only: `/home/vimkim/gh/cubrid-oos-context/OOS-CONTEXT.md:208-222` and `docs/reference/implementation-observations.md` "CBRD-27230". Both say acceptance does not establish implementation. This investigation confirms that, at `dcbf09e4f`, nothing implements it.

---

## Q6. Restart: are in-progress blocks re-run, and is committed vacuum work kept?

Verdict: CONFIRMED yes to both.

### In-progress blocks are re-run in full

- `vacuum_data_load_and_recover` (`src/query/vacuum.c:4402-4560`): for every data page it loops entries from `index_unvacuumed` to `index_free` and for each `is_job_in_progress ()` entry calls `entry->set_interrupted ()` (4439-4448) and marks the page dirty. `set_interrupted` sets status AVAILABLE and the INTERRUPTED flag (`vacuum.c:8446-8450`). The master will start it again like any available block.
- A re-run walks the whole block: start at the entry's `start_lsa` (the last MVCC operation in the block) and follow `prev_mvcc_op_log_lsa` back until the page id falls below the block's first page (`vacuum.c:3517-3518`). `start_lsa` is not advanced when a job stops early (TODO at 3808-3809).
- `was_interrupted` is passed to `vacuum_heap_page` (3514, 3785) so a heap page that was deallocated during the earlier run is tolerated (1686-1724) and page-status safeguards differ (1884-1885).
- Within one block the order is: walk all chained records newest to oldest (B-tree vacuum, forward-walk OOS reclaim, LOB delete, collect heap OIDs) and only then `vacuum_heap` over the collected OIDs (`vacuum.c:3517-3785`). Heap REMOVE work therefore happens after the OOS forward-walks of the same block.
- Blocks whose entries were still in the in-memory block buffer at crash are rebuilt from the log by `vacuum_recover_lost_block_data` (`vacuum.c:5697` onward, called at 4530; it walks back from the recovery LSA through MVCC-op records, 5729-5754).
- A finished job is recorded only on full success: `vacuum_finished_block_vacuum` sets `set_vacuumed` when `is_vacuum_complete`, else `set_interrupted` (`vacuum.c:3939-3984`).

### Committed sysop work is not undone

- Vacuum worker sysops belong to the worker's system transaction (`vacuum.c:3468`, `assert (thread_p->get_system_tdes () != NULL)`). Recovery handles system worker transactions through `log_system_tdes` (`src/transaction/log_recovery.c:4754-4757`).
- Analysis, on `LOG_SYSOP_END` of type commit: `undo_nxlsa` is set to that record (`log_recovery.c:1648-1650`; `LOG_SYSOP_END_COMMIT` handled at 1671-1678).
- Undo phase, on reaching `LOG_SYSOP_END`: "We found a system top operation that should be skipped from rollback" and it jumps to `lastparent_lsa` (`log_recovery.c:4950-5008`; the commit case at 5001-5008). The records inside a committed sysop are not undone.
- A sysop with no end record at the crash is undone: its records' undo functions run. Undo of `RVVAC_HEAP_RECORD_VACUUM` re-inserts the heap record (`vacuum.c:7771-7776`), undo of `RVOOS_DELETE` re-inserts the chunk (`recovery.c:887-892`). This is the path the `cubrid-verify-vacuum-slot-undo` skill models.
- Redo-only records are never undone: the undo walk skips `LOG_REDO_DATA` and `LOG_MVCC_REDO_DATA` (`log_recovery.c:4921-4937`), and runtime rollback skips them too (`log_manager.c:8049-8050`). They are replayed by the redo phase (`log_recovery.c:3675, 3701`). INFERRED: a redo-only chunk delete issued by an unfinished vacuum job stays applied after restart.
- Redo-only is already what a vacuum worker gets outside a sysop. `log_can_skip_undo_logging` returns true for "a vacuum worker [that] has not started a system operation" (`log_manager.c:4394-4399`), and `log_append_undoredo_crumbs` then degrades the record to `log_append_redo_crumbs` (`log_manager.c:2232-2237`). `oos_log_delete_physical` passes an undo image and no redo image (`oos_file.cpp:3221`, through `log_append_undoredo_recdes2`, `log_manager.c:2586-2628`), so an `oos_delete` called by a worker with no open sysop is logged as `RVOOS_DELETE` redo-only with no undo data. CONFIRMED by code reading, including that a worker thread has `tran_index = LOG_SYSTEM_TRAN_INDEX` (`vacuum.c:913`) and that `LOG_FIND_TDES (LOG_SYSTEM_TRAN_INDEX)` returns the worker's own system tdes (`src/transaction/log_impl.h:1279-1294`, `log_tran_table.c:6409-6426`). Not run. Today every worker call to `oos_delete` is inside a sysop (`vacuum_oos.cpp:153-215`, `vacuum.c:2505`), so the redo-only form is never exercised by vacuum now.
- A re-run sees committed results: a committed heap REMOVE leaves slot type `REC_DELETED_WILL_REUSE` or `REC_MARKDELETED` (falls to `default:` at `vacuum.c:1854-1858`), and committed OOS deletes leave the head page or slot gone, so `oos_delete` no-ops (`oos_file.cpp:3282-3360`; retry rationale at `vacuum_oos.cpp:176-182`).
- The one difference between runs: a re-run may find a slot reused. Both heap (header re-check, Q3) and OOS (stamp check) handle that.

---

## Consequences for B2 and B3

Only facts that break or constrain an alternative are listed. "Breaks" means the alternative as you described it fails unless something outside its description changes. "Constrains" means the model needs an extra state or step to stay faithful. Each item says which section holds the evidence.

### B2 (reclaim first)

**Breaks**

1. **"The block is re-run" is true for crash, shutdown and out-of-memory only. An ordinary error ends the block as complete.** CONFIRMED by reading. `vacuum_heap_record` on an OOS delete error calls `log_sysop_abort` and returns the error (`vacuum.c:2565-2569, 2625-2629`). `vacuum_heap_page` then does `assert_release (false)` and `continue`s (`vacuum.c:1834-1851`). `vacuum_heap` clears the error and continues in release builds unless shutdown is in progress (`vacuum.c:1599-1618`); only `ER_OUT_OF_VIRTUAL_MEMORY` (1594-1598, 1829-1833) and a shutdown-time `ER_INTERRUPTED` keep the block retryable. Since `vacuum_heap` then returns `NO_ERROR`, `vacuum_process_log_block` sets `vacuum_complete` (`vacuum.c:3785-3799`) and the block is marked vacuumed (`vacuum.c:3943-3946`). Today the abort undoes the chunk deletes together with the slot removal, so the record and its chains stay consistent. Under B2 the chunk deletes are redo-only and are not undone (`log_recovery.c:4921-4937`, `log_manager.c:8049-8050`). The abort restores the heap record (undo of `RVVAC_HEAP_RECORD_VACUUM` re-inserts it, `vacuum.c:7771-7776`) while some or all chains stay deleted. The reachable state is: record present and REMOVE-eligible, chains partly or fully gone, block marked vacuumed, no retry through the block mechanism. The only other vacuum entry I saw is `heap_vacuum_all_objects` from two DDL paths (`locator_sr.c:12591, 13183`). ADR-0008 decision 3 leaves "fail-stop or re-queue" open; this is the evidence that the choice is needed. A debug build asserts instead.
2. **"Redo-only" is not what the engine gives inside a sysop.** CONFIRMED by reading. A vacuum worker gets redo-only logging from `oos_delete` only when it has no sysop open (`log_manager.c:4394-4399`, `2232-2237`). Today every worker `oos_delete` is inside a sysop (`vacuum.c:2505`, `vacuum_oos.cpp:153-215`), where `RVOOS_DELETE` is logged with the full chunk as undo (`oos_file.cpp:3221, 3378-3381`) and is undone by abort and by restart undo (`recovery.c:887-892`). B2 needs either chunk deletes outside the sysop, or a new redo-only rcvindex. The two choices give different crash states: outside the sysop, a crash between the last chunk delete and the slot removal leaves the slot intact and the chains gone; with a new rcvindex inside the sysop the same crash state exists but the order inside the sysop is under your control.
3. **Tail-first delete is unsafe without a stamp on every link.** CONFIRMED that the engine has none. The chunk header is `{int total_data_length, int chunk_index, OID next_chunk_oid, LOG_LSA identity_stamp}` (`oos_file.hpp:32-47`, 24 bytes). Only the head is identity-checked, and continuation pages are fixed plainly "because a verified head proves the chain is live" (`oos_file.cpp:3255-3257, 3305-3312`). Under B2 the head is deleted last, so after a crash mid-way the head is alive while some tail slots are already free and may have been reused by new chains. A re-run reads the head, follows `next_chunk_oid` into a slot that now belongs to another chain, and the plain fix gives no way to see it. This is the case ADR-0008 decision 4 (link stamps) addresses. The model must include slot reuse between the crash and the re-run, and it must not give the continuation walk a head-verified guarantee. A continuation page may also be deallocated by empty-page reclaim; the plain `pgbuf_fix` then fails (`oos_file.cpp:3305-3312`).

**Constrains**

4. **Reader atomicity depends on the home page WRITE latch spanning the whole REMOVE.** CONFIRMED (Q3, Q4). Today the slot removal and the chunk deletes happen under one continuous latch hold. Readers that expand raw bytes while holding the page latch (`heap_file.c:7587-7648`) then see the record with its chain or no record. If B2 releases that latch between the chunk deletes and the slot removal, the expand readers in the Q4 table (`xlocator_fetch_all` with `--latest-image`, `xlocator_lock_and_fetch_all`, and the two DDL paths unless they are pinned) can see "record present, chains gone" and fail with -1389. If B2 keeps the latch, the empty-page reclaim must stay after the unfix as it is now (`vacuum.c:1977-1987`).
5. **The state "record live, chains gone" is reachable by crash even if the latch is kept.** CONFIRMED mechanism: redo-only chunk deletes persist across restart, an unfinished sysop's slot removal is undone and re-inserts the record (`vacuum.c:7771-7776`). Until the interrupted block runs again (`vacuum.c:4439-4448`), the record is readable by any NULL-snapshot reader. Today a crash cannot produce this state, because the chunk deletes are undone with the slot. Readers: `btree_load` has no protection (Q4), dirty and snapshot readers cannot see a REMOVE-eligible record, lock-and-get paths reject it at the delete check (`locator_sr.c:13507`).
6. **B2 covers only chains referenced by a heap record that vacuum REMOVEs.** CONFIRMED (Q5). In MVCC mode UPDATE overwrites the record in place and keeps the old version only in the undo image (`heap_file.c:25046-25049`). The dropped chain is referenced by no live record, so B2 cannot reach it. The forward-walk stays the only reclaim for UPDATE-dropped chains and keeps its missing commit check (Q1 gap 1, CBRD-27237). A B2 model of UPDATE needs a separate mechanism; the engine has none (`RVOOS_NOTIFY_VACUUM` has no emitter, `recovery.h:206-209`).
7. **Two workers may REMOVE the same record.** CONFIRMED (Q3). With the latch held they are serialized. In any variant that lets go of the latch, both pre-read the chain. Per-chunk identity (decision 4) is what keeps the second from deleting a reused slot.
8. **The heap-slot removal stays undoable.** CONFIRMED. B2 does not touch `RVVAC_HEAP_RECORD_VACUUM`, so the slot-reuse undo hazard CBRD-27858 and CBRD-27781 (skill `cubrid-verify-vacuum-slot-undo`) is unchanged by B2.

**Supports**

9. Idempotent re-run already exists: a committed chunk delete leaves page gone, slot empty or a different stamp, and `oos_delete` no-ops (`oos_file.cpp:3282-3360`, `vacuum_oos.cpp:176-182`). Interrupted blocks restart from the block start (Q6). Redo-only records are never undone (Q6).

### B3 (head MVCC mark)

**Breaks**

1. **Undo failure at abort is swallowed in release builds, so a mark could survive an abort.** CONFIRMED by reading: `log_rollback_record` sets `ER_LOG_MAYNEED_MEDIA_RECOVERY`, asserts and continues (`log_manager.c:7609-7619, 7659-7669`), and the abort then completes (`logtb_complete_mvcc`, Q1). Heap headers have the same exposure today. A surviving mark makes the aborted UPDATE's chain A look finished-deleted, while the restored old record still points to A. The rule "delid below threshold means committed" is only as strong as the undo succeeding. Restart undo is fail-stop instead (`logpb_fatal_error`, `log_recovery.c:301-305, 337-343`).
2. **The forward-walk must be removed, or B3 does not fix CBRD-27237.** CONFIRMED (Q1 gap 1, Q2). `vacuum_forward_walk_reclaim_oos` runs for every `RVHF_UPDATE_NOTIFY_VACUUM` record (`vacuum.c:3616-3625`) and for `RVHF_DELETE_NEWHOME_NOTIFY_VACUUM` (3757-3770), without any commit check. With B3 added and the forward-walk kept, the rolled-back UPDATE's chain is still deleted by the forward-walk.
3. **Nothing in vacuum handles an OOS MVCC record.** CONFIRMED (Q2). It needs: a new rcvindex in `LOG_IS_MVCC_OPERATION` (`mvcc.h:271-276`); a new branch in `vacuum_process_log_block` before the safeguard (`vacuum.c:3771-3775`); an undo-image whitelist entry if the record carries undo data (`vacuum.c:4275-4283`); a non-NULL vfid (`log_append.cpp:995-1012`); `RV_fun` entries with real undo and redo functions. The existing `RVOOS_NOTIFY_VACUUM` slot is pinned at 140 and its handlers are `vacuum_rv_es_nop` (`recovery.c:905-912`). Without the branch, release builds log a notification and skip, debug builds assert.
4. **The mark cannot be written from a postpone action.** CONFIRMED (Q2). A MVCC record needs a valid transaction MVCCID at append time (`log_append.cpp:966-973`), and commit resets it before running postpone (`log_manager.c:5267` then `5284`). B3 must write the mark at UPDATE time, as you describe it.

**Constrains**

5. **Dropped-file filtering does not know OOS files.** CONFIRMED (Q2): `vacuum_log_add_dropped_file` is called only for heap and B-tree vfids. If the mark carries the OOS file's vfid, a DROP TABLE is invisible to the vacuum worker and it will fix pages of a destroyed OOS file. Stamp the heap vfid, as heap records and the forward-walk do, or register the OOS vfid.
6. **The mark's target may be gone or reused when vacuum gets to it.** INFERRED from the existing behavior. Page deallocated or retyped, slot empty, slot reused by another chain: vacuum has to tolerate all of them the way `oos_delete` does (`oos_file.cpp:3282-3360`). A reused slot is judged by its own header, because `mvcc_satisfies_vacuum` reads only that header (`mvcc.c:320-374`): a live chain with no delete MVCCID gives `CANNOT_VACUUM`, a dead chain with `delid < threshold` is correctly reclaimable, and a continuation chunk has no mark (INFERRED, assumes the mark is stored only in the head).
7. **No chain reuse today, so every UPDATE would mark every OOS column of the old version.** CONFIRMED (Q5). Unassigned values are read and rewritten as new chains, so the old chain of an unassigned column is also dropped. Each mark is an MVCC undo/redo record chained into the vacuum block (`log_append.cpp:1411-1452`). When CBRD-27230 reuse arrives, borrowed chains must not be marked; the model needs "assigned" versus "reused" columns.
8. **Header format.** CONFIRMED (Q3 evidence): the chunk header is 24 bytes with no MVCCID (`oos_file.hpp:32-47`). A mark adds 8 bytes, the ADR's link stamp adds 8 more. `OOS_RECORD_HEADER_SIZE` sizes every chunk payload (`oos_file.cpp:2659`), so this is a storage-format change.
9. **SA mode cannot append MVCC records.** CONFIRMED: `assert_release (!LOG_IS_MVCC_OPERATION (rcvindex))` for non-server builds (`log_manager.c:2193-2195`). SA and non-MVCC classes use the eager path (`heap_oos.cpp:907-951`), so B3 must be server-only.
10. **B3 covers only UPDATE.** DELETE keeps the stubs in the record and its chains are reclaimed at REMOVE (Q3), under today's sysop or under B2. So B3 does not remove the need for a REMOVE-time design.

**Supports**

11. Aborts and statement rollbacks undo the mark before the MVCCID goes inactive (Q1), and a savepoint rollback leaves the MVCCID active. The decision function needs only `delid` and flags (`mvcc.c:320-374`), so it works on a header that has no insert id. Old versions are read from the undo image only by snapshot readers through one call site (`heap_file.c:27911-27918`), so the threshold gate is enough for them. The commit pin keeps the threshold below a committer's MVCCID until the commit record is appended (`mvcc_table.cpp:490-507`, `log_manager.c:5810-5814`). In-doubt 2PC transactions keep their MVCCIDs active across restart (`log_recovery.c:3289-3326`).

### Facts that bear on both

- **Same-record concurrency** (Q3): up to 10 workers by default; a record in an insert block, an update block and a delete block can be seen by three jobs. Every decision is re-made from the current header under the page latch.
- **Error policy in release builds** is "clean as much as possible and carry on" (`vacuum.c:1606-1615`). Either alternative must say what happens to a reclaim that failed for a reason other than out-of-memory or shutdown, because the block will not be retried.
- **Restart ordering** (Q1): vacuum starts after redo, undo and 2PC finish, so no vacuum job runs against a state with loser transactions still being undone.
- **Not checked:** stand-alone vacuum (`vacuum_sa_run_job`), HA replica behavior beyond the applier's forced paths, `heap_vacuum_all_objects` internals, and every query-executor caller of the visible-version functions. Nothing was run.
