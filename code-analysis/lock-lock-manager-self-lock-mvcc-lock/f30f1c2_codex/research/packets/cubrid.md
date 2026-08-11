# CUBRID source-trace research packet

- role: `CUBRID Source Tracer (Role 1)`
- topic: `CUBRID lock과 lock manager: self lock 및 MVCC lock의 필요성`
- frozen scope: `/home/vimkim/gh/my-cubrid-docs/code-analysis/lock-lock-manager-self-lock-mvcc-lock/f30f1c2_codex/research/scope.md`
- scope SHA-256: `711d1a0f5bfebdbe1b55b4299973efc353d90636e2f00fc807f51d031766a839`
- CUBRID source root: `/home/vimkim/gh/cb/cubrid-analysis`
- source revision: `f30f1c26003e5aa8e93182648e06cad76fc77064`
- evidence state: `WORKTREE` report-run provenance; frozen `git status --porcelain=v1` SHA-256 = `6f459c90a9e5391919b0f19ac04ffd081eab7905b9fde6cc27658f45f817bad1`
- source-reference state: 아래에서 인용한 CUBRID 파일은 모두 `git diff --quiet HEAD -- <file>`로 commit-clean임을 확인했으므로 개별 `source_ref.evidence_state`는 `COMMIT`이다.
- shared-worktree note: 동시 작성 중인 다른 연구 산출물 때문에 패킷 작성 직전(2026-08-11T08:48:35Z) 전체 status digest는 `5396d6b07e97ac3732071a9ba3134e8ec232484d2f5142396d281690c6494852`로 달라졌다. 고정된 Report Run provenance는 위 `6f459...`이며, 인용 소스 파일에는 차이가 없다.
- generated at (UTC): `2026-08-11T08:48:35Z`
- runtime evidence: 이 역할에서는 실행 실험을 하지 않았다. 모든 후보의 `runtime_run_ids=[]`이다.

## Executive source finding

CUBRID의 “MVCC lock”은 별도의 lock mode 하나가 아니다. 일반 객체/클래스 자원에는 `IS/IX/S/X` 등 기존 모드를 쓰되, MVCC가 읽기와 쓰기의 lock 정책을 바꾼다. 평범한 MVCC SELECT는 snapshot-visible version을 읽고 row lock을 생략한다. `SELECT ... FOR UPDATE`, UPDATE, DELETE는 class `IX`와 row `X`를 사용하고, 기다렸다면 최신 version을 다시 읽어 조건을 재평가한다.

`self lock`은 transaction의 MVCCID 자체를 `LOCK_RESOURCE_TRANSACTION` 자원으로 만들어 그 transaction이 `X`를 보유하는 lock이다. MVCC INSERT는 각 새 row에 `X`를 잡는 대신 이 self lock으로 자신의 `INSERT_IN_PROGRESS` 수명을 대표한다. 같은 unique key나 FK를 검사하다 그 MVCCID를 발견한 다른 transaction은 동일 자원에 `S`를 요청한다. `S`는 `X`와 비호환이므로 inserter의 commit/abort/subtransaction completion까지 기다리며, wakeup 뒤에는 반드시 index/record를 다시 탐색한다. 이것이 row마다 holder lock을 두지 않고도 “아직 결정되지 않은 version을 보았다”는 의존 관계를 일반 lock manager의 wait/deadlock/timeout 체계에 연결하는 핵심 필요성이다.

## Evidence conventions and file digest registry

- line ranges are 1-based inclusive ranges from the pinned checkout.
- `state=C` means `evidence_state=COMMIT`; no referenced source file is WORKTREE-modified.
- claim candidates inherit `database=CUBRID`, `revision=f30f1c26003e5aa8e93182648e06cad76fc77064`, and `runtime_run_ids=[]` unless stated otherwise.
- `kind=source` means the sentence is directly established by code. `kind=inference` gives premises and a falsifier.

| Alias | File | SHA-256 | State |
|---|---|---|---|
| LMH | `src/transaction/lock_manager.h` | `d996e4e67bb74f11275c5c3b2f945ad82aa9117eccfa1b7589dce03e5c93b6c3` | C |
| LMC | `src/transaction/lock_manager.c` | `17736dd485b179a2176ce525f85b5e7a59f3c3c3630fbeb96fa00bc4f6121cc9` | C |
| LTH | `src/transaction/lock_table.h` | `90da7b80bca51906b83cc21f9b2222cca23f1181488b8f04538d500ac9f1e04b` | C |
| LTC | `src/transaction/lock_table.c` | `6866e52b0abdb94b82782b50bc6c932f2e94d4e20492af8546e034c7291b2dba` | C |
| LTT | `src/transaction/log_tran_table.c` | `f6b98fcd69697aca8980a6b0d45e57b7eb0b29dac959f93cda59a52e6777e7fc` | C |
| LOG | `src/transaction/log_manager.c` | `73969c9343765e8affdd44ae7b312aac5243365418df08592be90c3325761975` | C |
| MHC | `src/transaction/mvcc.h` | `11b8314d6b2aac6c3075847965ad97e2664a9da4e6a3b3cc46397f56930bb706` | C |
| MVC | `src/transaction/mvcc.c` | `53119c2d78b2b6d2899c9f749243ded256c18743b917939aadd66de872ef8c75` | C |
| MVT | `src/transaction/mvcc_table.cpp` | `5dc09351d6bc1f58da7d1a1a9ac68dbf043b14b66c066e14c713ad1baace7b08` | C |
| L2P | `src/transaction/log_2pc.c` | `fee02b8ff4af4b54a556cedb3e8700ba670a397421122f4c399ed4e2f5faca13` | C |
| QEX | `src/query/query_executor.c` | `6b0e25954aa28b2f96cf27eb72f8a68621e40d21e9b11ece9cbabd4642e3663b` | C |
| SMH | `src/query/scan_manager.h` | `c9ca357bf3bb922849c3707f6f6f132664113e7f981948fe2fab6a11ec01f1fd` | C |
| SMC | `src/query/scan_manager.c` | `5f11836200d3952aa71e46ef4ad140d5e8b53f8c5ec2713931d109ff824bd5ee` | C |
| XAS | `src/query/xasl.h` | `47d57a8abbb6069640b9cf01ba358793a8af56278af21b552b898cad07bc0ef1` | C |
| LOC | `src/transaction/locator_sr.c` | `0f46ead88828969a5d966b06c2e8475d97d7c1cb7e21a606d6d6470fc173cff8` | C |
| LOH | `src/transaction/locator_sr.h` | `8a90ebf57fbe704327645ddaa7876f8c8ed12403396a1bd51ff7f940615618fb` | C |
| HEAP | `src/storage/heap_file.c` | `3210769cb2373b68aca7ad9fb886c85fbf0416b324f7d20d89f19ceaa965fa9d` | C |
| BTR | `src/storage/btree.c` | `740e750d7cd2aa5ef277449b0d4d891c158c8eb83c7c7b460ef92ba391afa0b7` | C |
| PRM | `src/base/system_parameter.c` | `fb3823943a91eb3c059afcfb248761844ac2c87e221d23d79e31db0880c56614` | C |
| PMH | `src/base/perf_monitor.h` | `fce3513a8e14508e0e667c23d6ce2df50dcbafd38e14e7f270873736212caa59` | C |
| PMC | `src/base/perf_monitor.c` | `ea814281c6f84ae4799915b17c11a3f33a84e075171b35802a6fc30a9c601f6a` | C |
| LGI | `src/transaction/log_impl.h` | `128c95f4efffa579c038221eff66a01e43d0b51a3177963a637940c9098778f2` | C |
| XGN | `src/parser/xasl_generation.c` | `b29f1453a53dd169b62b412ad1a0fe090641a545861f29061a6d9c49f3f5149a` | C |

## Examined files and symbols

| Area | Symbols/ranges examined | What it establishes |
|---|---|---|
| Public lock interface | LMH `LOCK`, `LK_GRANTED`, `LK_ENTRY` 44-101; `LOCK_RESOURCE_TYPE`, `LK_RES` 151-211 | modes/status, ownership fields, resource types, holder/waiter/non2pl lists |
| Compatibility/conversion | LTH mode enum 36-53; LTC `lock_Comp` 30-140, `lock_Conv` 142-240 | exact compatibility and conversion tables |
| Resource identity | LMC `lock_make_object_key`, `lock_make_transaction_key` 671-740; copy/compare/hash 865-960 | OID/class/resource type or full MVCCID determines identity; hash collision still compared |
| Runtime ownership | LMC `LK_TRAN_LOCK` 359-386; global `LK_GLOBTABLE` 410-466; hold insert/delete 1392-1607 | transaction-owned lists, resource table, local entry pool, waiter state |
| Main state machine | LMC `lock_internal_perform_lock_object` 3478-4175 | fast grant, fairness, re-request, conversion, wait allocation, error cleanup |
| Hierarchy/escalation | LMC `lock_object` 6234-6430; escalation 3059-3217; granules 9565-9599 | root/class/instance intent protocol and escalation behavior |
| Wait/wakeup | LMC `lock_suspend` 2304-2477; `lock_resume` 2491-2520; grant blocked holders 2665-2769; grant waiters 2782-2893; partial grant 2911-3046 | suspension state, timeout/deadlock outcome, queue grant and wakeup |
| Release | LMC release state machine 4197-4397; isolation-aware release 7137-7217; `lock_unlock_all` 7358-7423 | decrement/full delete, aggregate recompute, transaction-end list order |
| Deadlock | LMC WFG growth 4931-5052; victim validation/selection 5067-5474; detector 8203-8539 | graph construction, stale-edge checks, victim selection and fallback |
| Lifecycle | LTT 430-512, 573-602; LMC 1107-1351, 5889-6174 | startup allocation/unwind, daemon, shutdown order |
| Commit/abort | LOG `log_commit_local` 5189-5291, `log_abort_local` 5307-5363; LTT `logtb_complete_mvcc` 4394-4459 | MVCC completion precedes unlock and waiter wakeup |
| 2PC | LTT OID tracking/materialization 4199-4285; L2P prepare/recovery 1426-1582; LMC crash reacquire 8724-8780 | prepared update locks are serialized and reacquired; exception to ordinary volatile lock table |
| Snapshot | MVC snapshot predicates 145-269; HEAP old-version traversal 24943-25047 and visible get 25070-25322 | active/completed inserter/deleter visibility and previous-version traversal |
| Scan policy | SMH scan flags 481-525; QEX `qexec_open_scan` 7438-7588; SMC heap 5863-6165, index 6805-7000 | ordinary SELECT versus lock-and-recheck scan paths |
| FOR UPDATE | XAS 776-789; XGN 12833-12838; QEX class lock 24349-24379 and invocation 15967-15970 | parser flag to class IX and scan row-lock request |
| DML | QEX UPDATE 10315-10418, DELETE 11188-11280, class lock 24394-24479, INSERT 12760-12868; LOC 13260-13350 | class IX, row X policy, operation dispatch |
| Row lock/recheck | LOC `locator_lock_and_get_object_internal` 12955-13097; `...with_evaluation` 13119-13237 | conditional try, release latches, wait, latest fetch, snapshot/predicate recheck |
| Self-lock lifecycle | MHC `MVCC_INFO` 194-224; MVC initialization/copy 690-724; LTT 4028-4188, 4894-4983 | lazy main/sub IDs, hint, guarded X acquisition, explicit sub completion |
| MVCCID lock interface | LMC `lock_transaction_mvccid` 6433-6487, full release 6502-6548, test 6565-6607, protection predicate 6621-6638 | generic transaction resource uses X holder/S observer semantics |
| Insert/update use | HEAP `heap_get_insert_location_with_lock` 20459-20615, `heap_insert_logical` 23076-23183, `heap_update_logical` 23485-23573 | self-lock before publishing MVCC version; row-X fallback |
| Unique wait/restart | BTR 23679-24013, 24220-24238; root restart 23231-23344; `xbtree_find_unique` 24819-24989 | active-other test, S wait, release, invariant check, root restart |
| FK wait/recheck | BTR `btree_find_foreign_key` 6362-6448; scan/callback 26684-27006 | release pages/row lock, S wait on inserter, scan interruption/recheck |
| Diagnostics/config | PRM 160-170, 1278-1329; PMC 236-247; LMC 2002-2248, 3544-3565, 5593-5739, 10076-10090 | parameters, generic lock counters, dumps/event logs and timeout diagnostic gap |

## End-to-end trace 1 — resource, mode, hierarchy, conversion, escalation

### Interfaces and identity

```text
caller (executor/heap/btree/locator)
  -> lock_object(thread, oid, class_oid, mode, wait)
     -> infer ROOT_CLASS / CLASS / INSTANCE key
     -> for INSTANCE: acquire/convert CLASS to IS (mode <= S) or IX (mode > S)
     -> lock_internal_perform_lock_object(object-key, ...)
        -> mht_get_or_insert(LK_RES) + resource mutex
        -> holder/waiter compatibility and conversion

self-lock/observer
  -> lock_transaction_mvccid(thread, mvccid, X_LOCK|S_LOCK, wait)
     -> lock_make_transaction_key(LOCK_RESOURCE_TRANSACTION, full 64-bit MVCCID)
     -> the same lock_internal_perform_lock_object state machine
```

An object key contains resource type plus `(oid, class_oid)`; a transaction key contains resource type plus `MVCCID`. `LOCK_RESOURCE_TRANSACTION` is tracked in the transaction's `inst_hold_list`, but it skips object class checks, hierarchy and escalation. Thus it shares queueing/deadlock machinery without pretending an MVCCID is a database object.

### Modes and aggregation

`LOCK` includes `NA, NON2PL, NULL, SCH_S, IS, S, IX, BU, SIX, U, X, SCH_M`. Compatibility is table-driven, not inferred from enum order. Each resource caches aggregate granted modes for holders and waiters. A new request is checked against both aggregates, so a compatible newcomer cannot freely bypass an already queued incompatible waiter. A re-request of an equal/weaker lock increments `count`; a compatible upgrade converts immediately; an incompatible upgrade stays in the holder list with a blocked mode until grantable.

### Hierarchy and escalation

For an instance request, `lock_object` first guarantees class `IS` for modes through `S`, otherwise class `IX`; class/root calls do not recurse as instances. Class locks can make an instance request implicit. Granule counters feed escalation. At the threshold, class `IS` escalates to `S`, and `IX/SIX` to `X`; `BU` is excluded. Escalation itself is attempted with zero wait. On success, old instance locks for the class are released. `rollback_on_lock_escalation` controls failure handling. `lock_escalation` is also sampled at initialization to size the hash table, so changing it online changes the policy threshold but does not resize the already allocated hash table.

### Ownership/lifetime and error paths

`LK_RES` lives in the global hash/freelist and owns holder/waiter/non2pl lists. `LK_ENTRY` links a resource to a transaction and a requesting thread. `LK_TRAN_LOCK` owns per-transaction root/class/instance hold lists, wait metadata, non-2PL list, escalation counters and a small local entry pool. Allocation/hash insertion failures unwind the newly created entry/resource. `NULL_LOCK` returns immediately. Conditional zero-wait requests fail without enqueuing a persistent waiter. Ordinary write locks are not early-released; transaction completion drains instance (therefore transaction self-lock), class, root and non-2PL lists.

## End-to-end trace 2 — wait, deadlock, timeout, wakeup, release, restart

```text
lock_internal_perform_lock_object
  -> compatible: link LK_ENTRY to LK_RES + LK_TRAN_LOCK, return LK_GRANTED
  -> incompatible + LK_ZERO_WAIT: cleanup, return timeout/not-granted
  -> incompatible + wait allowed:
       append waiter (or blocked conversion) and update aggregate mode
       -> lock_suspend
          register thread.lockwait + start time + timeout + WFG marker
          release resource mutex
          thread_suspend_wakeup_and_unlock_entry

lock daemon (100 ms loop)
  -> lock_force_timeout_expired_wait_transactions / interrupt wake
  -> when interval elapsed and >=2 waiters: lock_detect_local_deadlock
     -> build/validate wait-for graph -> choose victim -> timeout or abort wake

holder release / conversion release
  -> delete/decrement hold, recompute aggregate
  -> lock_grant_blocked_holder / lock_grant_waiters(head-forward)
  -> lock_resume -> waiting thread restarts after suspend
```

`lock_suspend` asserts the waiter does not carry a permanent page latch across the sleep. After wakeup it distinguishes granted, interrupted, timeout and deadlock-victim states; the first worker chosen as deadlock victim performs abort handling, while sibling threads in the same transaction are woken consistently. Release holds the resource mutex, removes transaction/resource links, recomputes aggregate modes, and grants blocked conversions before eligible waiters. Waiters are visited from the head until an incompatible request prevents further grants.

The WFG includes incompatible holder-to-waiter edges, blocked holder conversions, and waiter ordering dependencies. Detection validates stale edges and active transactions. Victim ranking accounts for priority and rollback cost proxies such as logged work; if a cycle has no immediately abortable victim because all relevant handlers are suspended, the fallback forces a timeout rather than leaving the cycle indefinitely.

At commit, `logtb_complete_mvcc` marks the MVCCID completed/inactive before `lock_unlock_all`. At abort, rollback occurs first, then the MVCC table is completed, then all locks are released. This ordering matters to self-lock observers: after the X lock is released and S waiters wake, their active-ID recheck must already observe a terminal MVCC state.

Startup initializes transaction descriptors and MVCC tables, then lock per-transaction state, object hash/freelist, WFG storage and daemon, with reverse-order error unwind. Shutdown destroys the daemon and lock structures. Ordinary lock table state is volatile. A deliberate exception exists for prepared 2PC: update OIDs are tracked, materialized into object X locks before prepare, serialized in the prepare record, and reacquired with infinite wait during restart. The MVCCID self-lock itself is not the serialized unit.

## End-to-end trace 3 — MVCC SELECT/FOR UPDATE/DML class-row policy

### Plain SELECT

```text
qexec_execute_mainblock_internal
  -> qexec_open_scan
     -> ordinary MVCC class: mvcc_select_lock_needed=false
     -> heap_scan/index_scan obtains MVCC snapshot and class IS
     -> heap_get/index candidate -> mvcc_satisfies_snapshot
        -> current version, or follow previous-version log chain
     -> evaluate predicate/data filter
     -> return visible row without a row S lock
```

The absence of a row lock is safe for read consistency because the snapshot predicate classifies insert/delete MVCCIDs as current, active, completed-too-new or old-enough, and heap access can reconstruct an older version. This is snapshot visibility, not a promise that the current physical row will remain unchanged.

### SELECT FOR UPDATE

```text
parser/xasl_generation: ACCESS_SPEC_FLAG_FOR_UPDATE
  -> qexec_for_update_set_class_locks: class IX
  -> qexec_open_scan: mvcc_select_lock_needed=true
  -> heap/index scan reads a snapshot-visible candidate and evaluates filter
  -> locator_lock_and_get_object_with_evaluation
       X lock latest OID (conditional first; on conflict release page/fix state and wait)
       fetch latest record
       recheck snapshot/isolation and predicate
       keep X only when row remains qualifying; otherwise unlock/skip
```

The scan first filters a snapshot-visible row to avoid locking obvious non-matches, but the row can change before X is acquired. Therefore the locked latest version is re-read and predicates are reevaluated. A wait is not followed by blindly returning the old image.

### UPDATE and DELETE

UPDATE/DELETE obtain the statement snapshot before locking, acquire class `IX` through `qexec_set_class_locks`, and use row `X` for the target/latest version. Scans may mark `need_locking=true` and call the same lock-and-condition-reevaluation helper; force paths receive that flag. Conflict or deletion discovered after the wait becomes a skip or isolation error according to the path. This serializes writers on a row while preserving MVCC read semantics.

### INSERT

INSERT takes class `IX`. For an MVCC class, `heap_insert_logical` adjusts the MVCC header and `heap_get_insert_location_with_lock` ensures the transaction's MVCCID self-lock. If tracking the inserted OID for possible 2PC succeeds, it deliberately avoids a per-row X lock. If tracking allocation fails, or on non-MVCC/other paths, it falls back to object X. `heap_update_logical` also ensures the self-lock before publishing a new version because a unique/FK checker can see that new version as `INSERT_IN_PROGRESS`; the writer's target row remains protected by the normal update X lock.

### Latch versus transaction lock

Buffer/page latch ownership protects in-memory page access, not transaction outcome. Any path that may block on a transaction lock unfixes/releases the relevant heap, btree leaf or overflow pages first. The lock outlives the page access and is the wait/deadlock participant; after wake, the page/index must be refetched and state revalidated.

## End-to-end trace 4 — MVCCID X self-lock and unique/FK S wait/recheck

### Creation and ownership

```text
main/sub MVCCID allocation
  -> logtb_set_mvcc_info_log_lsa / logtb_get_new_subtransaction_mvccid
     -> mvcc_table.get_new_mvccid (mutex-protected monotonically unique ID)
     -> logtb_lock_current_mvccid
        -> if active worker and hint differs:
             lock_transaction_mvccid(mvccid, X_LOCK, LK_UNCOND_LOCK)
             mvcc_info.self_locked_mvccid = mvccid

heap insert/update publication
  -> logtb_ensure_mvccid_self_lock (error-propagating)
  -> record gets insert MVCCID / INSERT_IN_PROGRESS state
```

The `self_locked_mvccid` field is only a per-transaction deduplication hint; the authoritative ownership remains the generic lock table entry. Boot/recovery/non-worker contexts skip the self-lock because the code's stated assumption is that they do not perform ordinary concurrent unlock/wait participation. Copying MVCC info does not copy this hint.

### Unique conflict rendezvous

```text
xbtree_find_unique
  -> btree_search_key_and_apply_functions
     -> unique-key callback sees record.insert_mvccid
     -> btree_is_active_other_inserter
     -> release held object lock + leaf/overflow page latches
     -> btree_wait_for_inserter_end
        -> lock_transaction_mvccid(insert_mvccid, S_LOCK, LK_UNCOND_LOCK)
        -> lock_unlock_transaction_mvccid(...S...) in full
        -> assert/error if the ID is still active
     -> restart search from root and re-evaluate key
```

`S` and `X` are incompatible in the ordinary compatibility table. The waiter is therefore connected to the same timeout/WFG/deadlock system as any object lock. It releases the S immediately after rendezvous because the result is determined by re-searching the index under the now-terminal inserter state, not by retaining a read lock on the transaction identity.

### Foreign-key rendezvous

```text
btree_find_foreign_key
  -> btree_range_scan_find_fk_any_object
     -> btree_fk_object_does_exist
        -> candidate is INSERT_IN_PROGRESS by another active MVCCID
        -> btree_fk_release_pages_and_locks
           release leaf/overflow latches and any current row lock
           mark scan interrupted
        -> S wait on inserter MVCCID, then release S
        -> stop callback; range scan restarts/rechecks
```

For delete-in-progress and other cases, FK validation can instead use object locking. The MVCCID wait is specifically the rendezvous for an active inserting version.

### Completion and necessity

Main transaction completion changes MVCC active status first and releases all locks second. Subtransaction completion explicitly marks the sub-MVCCID inactive, fully releases the X transaction lock, and then pops the ID. Thus wakeup never precedes publication of terminal outcome. This is also why a fresh ID's self-X should normally be a no-wait fast path: the allocator produces a new unique ID, and no observer can request S until that ID has been published in a version/index record.

The mechanism is needed because an MVCC INSERT deliberately has no row-X holder in the successful fast path. Unique/FK readers nevertheless need to wait for commit versus abort. The MVCCID is the stable identity whose lifetime spans all versions inserted by the transaction/subtransaction; one X holder can rendezvous with every observer S request. This reduces the lock-manager holder cardinality from potentially one entry per inserted row to one per active MVCCID, although the 2PC OID tracking list remains row-proportional and the actual memory/throughput saving is not quantified by source inspection alone.

## Claim candidates

IDs `CUBRID-C007..C009`, `CUBRID-C017..C019`, and `CUBRID-C029` are intentionally reserved gaps in the frozen plan. The 31 candidates below cover every planned occupied ID.

### Resource/mode/hierarchy — CUBRID-C001..C006

#### CUBRID-C001

- `claim_ko`: Lock manager는 object를 ROOT_CLASS/CLASS/INSTANCE로, MVCCID를 TRANSACTION으로 구분하는 typed resource key를 사용하며, 두 종류 모두 하나의 global resource table에서 관리한다.
- `kind/confidence/behavior`: `source / high / resource-mode-hierarchy`
- `source_refs`: LMH `LOCK_RESOURCE_TYPE`, `LK_RES` 151-211; LMC `lock_make_object_key`, `lock_make_transaction_key` 671-740; key copy/compare/hash 865-960. 각 alias의 위 SHA, `state=C`.
- `limitations_ko`: hash bucket collision은 key compare로 구별됨을 포함하지만 hash-table 동시성 구현 전체를 분석한 주장은 아니다.
- `report_locations`: `book:자원 식별`, `appendix:source map`

#### CUBRID-C002

- `claim_ko`: CUBRID lock mode의 호환성과 upgrade 결과는 `lock_Comp`와 `lock_Conv` 정적 표가 결정하며, 예를 들어 S와 IX의 conversion은 SIX이고 S와 X는 비호환이다.
- `kind/confidence/behavior`: `source / high / resource-mode-hierarchy`
- `source_refs`: LTH mode enum 36-53; LTC compatibility 30-140, conversion 142-240.
- `limitations_ko`: 표의 의미를 설명하되, 사용되지 않는 조합의 실전 빈도는 측정하지 않았다.
- `report_locations`: `book:lock mode 표`, `quiz:mode compatibility`

#### CUBRID-C003

- `claim_ko`: instance lock은 mode가 S 이하이면 class IS, 그보다 강하면 class IX를 먼저 확보하며, class의 강한 lock이 instance 요청을 implicit하게 만족시킬 수 있다.
- `kind/confidence/behavior`: `source / high / resource-mode-hierarchy`
- `source_refs`: LMC `lock_object` 6234-6430.
- `limitations_ko`: partition/상속 class 전체 조합은 이 후보의 범위 밖이다.
- `report_locations`: `book:다중 granularity hierarchy`

#### CUBRID-C004

- `claim_ko`: `LK_RES`는 holder/waiter/non2pl list와 aggregate mode를, `LK_ENTRY`는 resource-thread-transaction 연결을, `LK_TRAN_LOCK`은 transaction별 hold/wait/escalation 상태를 소유한다.
- `kind/confidence/behavior`: `source / high / resource-mode-hierarchy`
- `source_refs`: LMH `LK_ENTRY` 78-101, `LK_RES` 178-211; LMC `LK_TRAN_LOCK` 359-386, global table 410-466, transaction hold insertion/deletion 1392-1607.
- `limitations_ko`: 메모리 바이트 수와 allocator contention은 측정하지 않았다.
- `report_locations`: `book:자료구조와 소유권`

#### CUBRID-C005

- `claim_ko`: 같은 transaction의 equal/weaker 재요청은 hold count를 늘리고, 호환 가능한 upgrade는 즉시 변환되며, 비호환 upgrade는 holder list에서 blocked mode로 기다린다.
- `kind/confidence/behavior`: `source / high / resource-mode-hierarchy`
- `source_refs`: LMC `lock_internal_perform_lock_object` 3867-4051; same-transaction wait-train handling 3415-3453.
- `limitations_ko`: 모든 mode pair의 예시는 LTC 표를 참조해야 한다.
- `report_locations`: `book:conversion과 reentrancy`

#### CUBRID-C006

- `claim_ko`: escalation threshold에 도달하면 class IS는 S로, IX/SIX는 X로 zero-wait escalation을 시도하고 성공 시 granule instance lock들을 해제한다; threshold는 boot-time hash sizing에도 쓰이므로 online 변경은 hash를 재배치하지 않는다.
- `kind/confidence/behavior`: `source / high / resource-mode-hierarchy`
- `source_refs`: LMC escalation 3059-3217, granule accounting 9565-9599, initialization/hash sizing 1263-1288; PRM parameter definitions 1278-1329.
- `limitations_ko`: 실제 workload별 임계값 최적값은 소스만으로 정할 수 없다.
- `report_locations`: `book:escalation`, `experiment:escalation`

### Wait/deadlock/release — CUBRID-C010..C016

#### CUBRID-C010

- `claim_ko`: 빈 resource 또는 aggregate mode와 호환되는 요청은 즉시 grant되지만, 신규 requester는 holder뿐 아니라 선행 waiter aggregate와도 호환되어야 하므로 대기자를 무제한 우회하지 않는다.
- `kind/confidence/behavior`: `source / high / wait-deadlock-release`
- `source_refs`: LMC fast grant 3631-3694, new-request compatibility/fairness 3712-3771.
- `limitations_ko`: 이 ordering이 starvation-free임을 형식적으로 증명한 것은 아니다.
- `report_locations`: `book:fast path와 fairness`

#### CUBRID-C011

- `claim_ko`: 비호환 unconditional request는 waiter 또는 blocked conversion으로 연결된 뒤 thread lock-wait 상태와 timeout/WFG 정보를 등록하고 suspend하며, permanent page latch를 든 채 잠드는 것은 금지된다.
- `kind/confidence/behavior`: `source / high / wait-deadlock-release`
- `source_refs`: LMC enqueue 3825-3865, blocked upgrade 3949-4051, suspended path 4053-4109, `lock_suspend` 2304-2477.
- `limitations_ko`: OS scheduler latency나 spurious wakeup의 실측은 없다.
- `report_locations`: `book:slow path와 latch 규칙`

#### CUBRID-C012

- `claim_ko`: release는 hold를 decrement/delete하고 aggregate mode를 재계산한 뒤 blocked holder conversion과 queue-head waiter를 grant하여 `lock_resume`으로 깨운다.
- `kind/confidence/behavior`: `source / high / wait-deadlock-release`
- `source_refs`: LMC `lock_resume` 2491-2520, blocked holder grant 2665-2769, waiter grant 2782-2893, partial grant 2911-3046, release 4197-4397.
- `limitations_ko`: wakeup 뒤 상위 caller의 재평가 의무는 MVCC별 후보에서 별도로 다룬다.
- `report_locations`: `book:release와 wakeup`

#### CUBRID-C013

- `claim_ko`: lock daemon은 100 ms 주기로 timeout/interrupt waiter를 확인하고, 설정된 deadlock interval 및 waiter 수 조건이 맞을 때 WFG detection을 실행한다.
- `kind/confidence/behavior`: `source / high / wait-deadlock-release`
- `source_refs`: LMC daemon loop 6039-6119, timeout/interrupt wake 7950-8005, interval 8129-8151; PRM `lock_timeout`, deadlock interval 1278-1329.
- `limitations_ko`: 실제 감지 지연은 scheduling과 workload에 따라 달라진다.
- `report_locations`: `book:timeout/interrupt daemon`, `config table`

#### CUBRID-C014

- `claim_ko`: deadlock detector는 holder, blocked conversion, waiter ordering의 비호환 관계로 WFG를 만들고 stale edge를 검증한 뒤 priority와 rollback-cost proxy를 고려해 victim을 고르며, abort 불가능한 경우 timeout fallback을 둔다.
- `kind/confidence/behavior`: `source / high / wait-deadlock-release`
- `source_refs`: LMC WFG storage/growth 4931-5052, validation/victim selection 5067-5474, graph construction/detection/fallback 8203-8539.
- `limitations_ko`: victim 정책의 workload 공정성은 정적 분석만으로 평가하지 않았다.
- `report_locations`: `book:deadlock detector`, `experiment:two-way deadlock`

#### CUBRID-C015

- `claim_ko`: commit은 MVCC 상태를 완료시킨 후 `lock_unlock_all`을 호출하고, abort는 rollback과 MVCC 완료 후 unlock하므로 self-lock waiter는 terminal MVCC 상태가 공개된 뒤 깨어난다.
- `kind/confidence/behavior`: `source / high / wait-deadlock-release`
- `source_refs`: LOG `log_commit_local` 5189-5291, `log_abort_local` 5307-5363; LTT `logtb_complete_mvcc` 4394-4459; LMC `lock_unlock_all` 7358-7423.
- `limitations_ko`: crash 직전/직후 WAL durability는 recovery 장의 별도 주제다.
- `report_locations`: `book:transaction completion ordering`

#### CUBRID-C016

- `claim_ko`: ordinary lock table은 startup에 메모리 구조와 daemon으로 생성되고 shutdown에 폐기되는 runtime state지만, prepared 2PC update lock은 OID를 materialize/serialize하고 restart에서 reacquire하는 예외가 있다.
- `kind/confidence/behavior`: `source / high / wait-deadlock-release`
- `source_refs`: LTT initialization/finalization 430-512, 573-602; LMC components 1107-1351, 5889-6174; LTT OID tracking/materialization 4199-4285; L2P prepare/recovery 1426-1582; LMC crash reacquire 8724-8780.
- `limitations_ko`: self-lock 자체는 serialization 대상이 아니며, prepared transaction 이외 모든 recovery lock을 열거한 것은 아니다.
- `report_locations`: `book:startup/shutdown/restart`, `book:2PC exception`

### MVCC policy — CUBRID-C020..C028

#### CUBRID-C020

- `claim_ko`: CUBRID에는 `MVCC_LOCK`이라는 독립 mode가 없고, MVCC policy가 기존 class/row IS·IX·S·X와 MVCCID transaction resource의 사용 시점을 결정한다.
- `kind/confidence/behavior`: `source / high / mvcc-lock-policy`
- `source_refs`: LTH mode enum 36-53; LMH resource type 151-164; LOC operation-to-lock policy 13260-13350; LMC MVCCID API 6433-6487.
- `limitations_ko`: 문서에서 “MVCC lock”이라는 표현을 쓸 때 mode와 policy/resource를 구별해야 한다.
- `report_locations`: `book:용어 정리`

#### CUBRID-C021

- `claim_ko`: MVCC read는 inserter/deleter의 current/active/completed 상태를 snapshot과 비교하고, current record가 너무 새로우면 log의 previous-version chain을 따라 visible version을 복원한다.
- `kind/confidence/behavior`: `source / high / mvcc-lock-policy`
- `source_refs`: MVC snapshot visibility 145-269; HEAP previous-version traversal 24943-25047, visible record retrieval 25070-25322; SMC snapshot scan startup 4526-4680.
- `limitations_ko`: vacuum으로 제거 가능한 version의 경계는 범위 밖이다.
- `report_locations`: `book:snapshot visibility`

#### CUBRID-C022

- `claim_ko`: ordinary MVCC SELECT는 class IS를 확보하지만 scan의 `mvcc_select_lock_needed`가 false여서 qualifying row에 S lock을 잡지 않고 snapshot-visible version을 반환한다.
- `kind/confidence/behavior`: `source / high / mvcc-lock-policy`
- `source_refs`: SMH scan state 481-525; QEX `qexec_open_scan` 7438-7588; HEAP class scan lock 6303-6343; SMC heap scan 5863-6023, index scan 6805-6846.
- `limitations_ko`: non-MVCC class 및 explicit locked-select 경로에는 적용되지 않는다.
- `report_locations`: `book:plain SELECT path`

#### CUBRID-C023

- `claim_ko`: SELECT FOR UPDATE는 parser/XASL flag가 class IX와 scan row-X 요구로 이어지고, candidate filter 후 latest row를 X-lock하여 snapshot과 predicate를 재검사한다.
- `kind/confidence/behavior`: `source / high / mvcc-lock-policy`
- `source_refs`: XAS flag 776-789; XGN flag generation 12833-12838; QEX class IX 24349-24379 and call 15967-15970, scan flag 7438-7588; SMC lock/re-eval 6025-6055 and 6848-6874; LOC 13119-13237.
- `limitations_ko`: 모든 SQL 문법 variant의 parser trace는 하지 않았으나 FOR UPDATE flag의 생성과 소비는 연결했다.
- `report_locations`: `book:SELECT FOR UPDATE path`, `experiment:select vs for-update`

#### CUBRID-C024

- `claim_ko`: UPDATE/DELETE는 statement snapshot을 얻고 class IX 및 target row X를 사용하며, lock wait 중 변경될 수 있는 조건은 latest version에서 재평가하거나 force 단계의 `need_locking`으로 보호한다.
- `kind/confidence/behavior`: `source / high / mvcc-lock-policy`
- `source_refs`: QEX UPDATE 10315-10418, DELETE 11188-11280, class locks 24394-24479; SMC 6025-6055, 6848-6874; LOC 12955-13237, policy 13260-13350.
- `limitations_ko`: trigger/partition별 모든 분기까지 열거하지 않았다.
- `report_locations`: `book:UPDATE/DELETE path`

#### CUBRID-C025

- `claim_ko`: MVCC INSERT는 class IX를 잡고 self-lock과 2PC OID tracking이 성공하면 새 row의 X lock을 생략하며, non-MVCC 또는 tracking 실패에서는 row X로 fallback한다.
- `kind/confidence/behavior`: `source / high / mvcc-lock-policy`
- `source_refs`: QEX INSERT 12760-12868; HEAP `heap_insert_logical` 23076-23183, `heap_get_insert_location_with_lock` 20459-20615; LTT tracking 4199-4239.
- `limitations_ko`: bulk operation 및 address-assignment special case는 같은 fast path가 아닐 수 있다.
- `report_locations`: `book:INSERT path`, `book:self-lock bridge`

#### CUBRID-C026

- `claim_ko`: MVCC writer/locked-select는 조건부 row lock이 실패하면 page/fix state를 정리하고 unconditional X/S를 기다린 뒤 latest row를 다시 읽어 deletion, isolation conflict, predicate change를 판정한다.
- `kind/confidence/behavior`: `source / high / mvcc-lock-policy`
- `source_refs`: LOC `locator_lock_and_get_object_internal` 12955-13097, `locator_lock_and_get_object_with_evaluation` 13119-13237; MVC snapshot result rules 145-269.
- `limitations_ko`: 반환 error code별 사용자-visible SQL 메시지는 추적하지 않았다.
- `report_locations`: `book:writer conflict and recheck`

#### CUBRID-C027

- `claim_ko`: page latch는 페이지 접근의 단기 보호이고 transaction lock은 transaction outcome 대기의 장기 보호이므로, lock wait path는 heap/btree leaf/overflow latch를 먼저 놓고 wake 후 다시 fetch/search해야 한다.
- `kind/confidence/behavior`: `source / high / mvcc-lock-policy`
- `source_refs`: LMC no-permanent-latch assertion in `lock_suspend` 2304-2477; LOC conditional-to-unconditional transition 12955-13097; BTR unique release/restart 23744-24013; FK release/recheck 26821-27006.
- `limitations_ko`: buffer manager의 전체 latch protocol은 범위 밖이다.
- `report_locations`: `book:latch versus lock`

#### CUBRID-C028

- `claim_ko`: lock observability는 generic acquire/convert/rerequest/wait counters와 lock dump/event log를 제공하고 transaction resource는 dump에서 MVCCID로 표시되지만, 전용 self-lock metric은 없으며 timeout diagnostic의 transaction 분기는 union의 OID 필드를 format한다.
- `kind/confidence/behavior`: `source / medium / mvcc-lock-policy`
- `source_refs`: PMC generic counters 236-247; LMC counter updates 3680-3682, 3760, 3899, 4061-4079, 4145; dump 5593-5739; event log 10076-10090; timeout diagnostic 2002-2248, especially 2215-2222.
- `limitations_ko`: timeout 출력의 잘못된 값은 source-level defect 의심이며 실제 로그 재현 전에는 runtime fact로 단정하지 않는다. generic counter에 self-lock이 포함되는 비율은 알 수 없다.
- `report_locations`: `book:관측성`, `experiment:lock dump`

### MVCCID self-lock rendezvous — CUBRID-C030..C038

#### CUBRID-C030

- `claim_ko`: MVCCID lock은 `LOCK_RESOURCE_TRANSACTION` key를 만들지만 acquire/wait/deadlock/release는 object와 동일한 generic state machine을 사용하며 X는 self holder, S는 observer 역할을 한다.
- `kind/confidence/behavior`: `source / high / mvccid-self-lock-rendezvous`
- `source_refs`: LMH resource type 151-164; LMC key 713-740, generic call 3478-4175, `lock_transaction_mvccid` 6433-6487, full release 6502-6548.
- `limitations_ko`: transaction resource는 class hierarchy/escalation을 건너뛴다.
- `report_locations`: `book:self-lock resource model`

#### CUBRID-C031

- `claim_ko`: main/sub MVCCID는 lazy allocation choke point에서 X self-lock을 얻고, `self_locked_mvccid` hint로 중복 요청을 피하며, active worker가 아닌 boot/recovery context는 이 lock을 생략한다.
- `kind/confidence/behavior`: `source / high / mvccid-self-lock-rendezvous`
- `source_refs`: MHC `MVCC_INFO` 194-224; MVC initialization/copy 690-724; LTT current ID/helper/ensure 4028-4188, main/sub assignment 4894-4947; MVT ID allocation 566-590.
- `limitations_ko`: non-worker 생략의 안전성은 해당 코드 comment/guard에 의존하며 모든 system path를 exhaustive하게 증명하지 않았다.
- `report_locations`: `book:self-lock creation and hint`

#### CUBRID-C032

- `claim_ko`: MVCC insert와 update는 `INSERT_IN_PROGRESS` version을 외부에 노출하기 전에 error-propagating self-lock ensure를 수행하며, insert fast path에서는 이 X가 row-X 부재를 보완한다.
- `kind/confidence/behavior`: `source / high / mvccid-self-lock-rendezvous`
- `source_refs`: LTT ensure 4169-4188; HEAP insert lock decision 20459-20615 and header path 23076-23183; `heap_update_logical` 23485-23573.
- `limitations_ko`: update의 기존 target row 자체는 normal row X로 보호되므로 self-lock이 그것을 대체한다는 뜻은 아니다.
- `report_locations`: `book:publication invariant`

#### CUBRID-C033

- `claim_ko`: unique 검사에서 active other inserter를 발견하면 보유 page/object 상태를 놓고 그 insert MVCCID에 S를 요청해 기다린 뒤 S를 full-release하고, ID가 inactive인지 확인한 후 btree root부터 key를 다시 검색한다.
- `kind/confidence/behavior`: `source / high / mvccid-self-lock-rendezvous`
- `source_refs`: BTR active-other/wait/release 23679-23724, release/restart 23744-24013, nonunique representation branch 24220-24238, root restart driver 23231-23344, `xbtree_find_unique` 24819-24989.
- `limitations_ko`: duplicate-key 최종 SQL error mapping은 범위 밖이다.
- `report_locations`: `book:unique wait/recheck`, `experiment:unique conflict`

#### CUBRID-C034

- `claim_ko`: FK 검사가 active other inserter의 record를 만나면 leaf/overflow latch와 현재 row lock을 놓고 inserter MVCCID의 S를 기다리며, scan을 interrupted로 표시해 결과를 다시 검사한다.
- `kind/confidence/behavior`: `source / high / mvccid-self-lock-rendezvous`
- `source_refs`: BTR `btree_find_foreign_key` 6362-6448, range scan 26684-26803, release helper 26821-26840, callback 26858-27006.
- `limitations_ko`: delete-in-progress FK case는 object-lock 분기를 쓸 수 있어 이 claim과 구분해야 한다.
- `report_locations`: `book:foreign-key wait/recheck`, `experiment:FK conflict`

#### CUBRID-C035

- `claim_ko`: self-lock이 필요한 직접 이유는 MVCC insert fast path가 row X를 생략해도 unique/FK observer가 commit/abort 결정을 기다려야 하기 때문이며, 동일 MVCCID의 X/S 비호환성이 그 rendezvous를 제공한다.
- `kind/confidence/behavior`: `source / high / mvccid-self-lock-rendezvous`
- `source_refs`: HEAP row-X skip/fallback 20524-20614; LTC S-vs-X and X-vs-S compatibility 98-102, 128-132; BTR unique 23679-24013 and FK 26858-27006; LMC transaction key/API 713-740, 6433-6487.
- `limitations_ko`: “필요성”은 이 구현의 invariant에 대한 설명이며 다른 설계가 이론적으로 불가능하다는 주장은 아니다.
- `report_locations`: `book:왜 self-lock인가`, `quiz:self-lock necessity`

#### CUBRID-C036

- `claim_ko`: main commit/abort와 subtransaction completion 모두 MVCCID를 inactive/completed로 만든 후 X self-lock을 해제하므로, 깨어난 S observer의 active-ID recheck가 terminal outcome을 볼 수 있다.
- `kind/confidence/behavior`: `source / high / mvccid-self-lock-rendezvous`
- `source_refs`: LOG commit/abort 5189-5363; LTT main completion 4394-4459, sub completion 4949-4983; LMC full MVCCID release 6502-6548; BTR post-wait active check 23700-23724.
- `limitations_ko`: hardware memory-order proof가 아니라 mutex/lock call ordering에 대한 source claim이다.
- `report_locations`: `book:completion-before-wakeup invariant`

#### CUBRID-C037

- `claim_ko`: transaction resource entry는 transaction의 instance hold list에 속해 main transaction end의 `lock_unlock_all`로 해제되며, sub-MVCCID는 sub completion에서 count와 무관한 full release를 명시 호출하고 hint는 reset된다.
- `kind/confidence/behavior`: `source / high / mvccid-self-lock-rendezvous`
- `source_refs`: LMC transaction hold handling 1392-1607, full release 6502-6548, `lock_unlock_all` 7358-7423; MVC hint reset/copy 690-724; LTT complete/reset 4394-4459 and sub release 4949-4983.
- `limitations_ko`: 같은 MVCCID를 여러 번 요청할 수 있어 observer/helper는 일반 decrement가 아닌 full release API를 사용한다.
- `report_locations`: `book:ownership and lifetime`

#### CUBRID-C038

- `claim_ko`: 하나의 MVCCID X self-lock은 여러 inserted row의 holder-side lock을 대표해 lock entry cardinality를 줄이는 설계이지만, prepared 2PC를 위해 OID를 별도 추적하고 row X를 materialize하므로 전체 메모리 비용이 항상 O(1)은 아니다.
- `kind/confidence/behavior`: `inference / medium / mvccid-self-lock-rendezvous`
- `source_refs`: HEAP per-row X skip and OID tracking fallback 20524-20614; LTT tracking/materialization 4199-4285; L2P prepare/recovery 1426-1582; LMC reacquire 8724-8780.
- `premises_ko`: (1) successful MVCC insert path does not allocate an object X entry per row, (2) self lock is keyed once per active main/sub MVCCID, (3) 2PC OID tracking appends row identifiers.
- `falsifier_ko`: 동일 commit에서 bulk insert의 live `LK_ENTRY`/tracked-OID 수를 계측했을 때 self-lock 경로도 row마다 holder lock entry를 생성하거나, 실제 메모리/latency가 row-X baseline보다 개선되지 않으면 cardinality/성능 해석을 축소한다.
- `limitations_ko`: cardinality 방향은 source inference이고 실제 byte/throughput 이득은 아직 측정하지 않았다. prepared 2PC에서는 OID list와 materialized X locks가 필요하다.
- `report_locations`: `book:성능 trade-off`, `experiment:resource cardinality`, `book:2PC caveat`

## Configuration, observability, performance notes

| Item | Source behavior | Operational consequence |
|---|---|---|
| `lock_timeout` | PRM 1278-1329, default infinite | finite experiments must set/restore it explicitly; otherwise an unexpected missing wake can hang a session |
| `deadlock_detection_interval_in_secs` | PRM 1278-1329, default 1.0 s, minimum 0.1 s | detection is periodic, not instant |
| `lock_escalation` | PRM 1278-1329, default 100000, minimum 5 | affects escalation threshold and initialization estimate |
| `rollback_on_lock_escalation` | PRM 1278-1329, default false | controls behavior on failed escalation |
| Hash sizing | LMC 1263-1288 uses `num_trans * lock_escalation * 3 / 1000` with clamping | online threshold change does not reallocate hash; restart comparison is needed for sizing effects |
| Generic perf counters | PMC 236-247; LMC counter sites 3680-4145 | self-lock activity is mixed into object acquired/converted/rerequested/wait statistics |
| Lock dump | LMC 5593-5739 | transaction resource is recognizable by printed MVCCID |
| Event log | LMC 10076-10090 | lock event path prints MVCCID for transaction resource |
| Timeout diagnostic | LMC 2215-2222 | transaction branch formats the OID union member; suspected diagnostic defect, needs reproduction |
| Resource-memory bound | LMC WFG 4931-5052 and resource/entry free lists | OOM/error paths exist; no safe numeric capacity claim without runtime/environment data |

## Negative searches and research gaps

1. Direct self-lock tests were not found. Searches for `lock_transaction_mvccid`, `LOCK_RESOURCE_TRANSACTION`, `self_locked_mvccid`, and unique/FK self-lock terms under the checked-out `unit_tests/` and tracked test directories returned no focused regression test. This checkout has no populated top-level CTP `tests` corpus suitable for proving absence beyond the tracked tree.
2. No dedicated self-lock counter was found in `src/base/perf_monitor.*` or self-lock call sites. The generic lock counters are usable only with controlled workload subtraction or extra instrumentation.
3. No enum entry named `MVCC_LOCK` was found in `src/transaction/lock_table.h`; “MVCC lock” must be described as a policy/resource family, not quoted as an engine mode.
4. Starvation-freedom was not proven. The queue/aggregate ordering is visible, but adversarial conversion and multi-thread same-transaction scenarios need stress tests.
5. Exact memory and throughput savings of self-lock are unknown. Source proves row-X skip and one MVCCID key, but allocator overhead, wait contention, and 2PC tracking remain unmeasured.
6. Crash persistence of the MVCCID self-lock was not found. What is explicitly persisted/reacquired for prepared 2PC is the materialized object-lock list.
7. Server concurrency conclusions apply to `SERVER_MODE`. Standalone stubs/no-op behavior was inspected only enough to avoid presenting the server lock manager as universal to every build mode.
8. Predicate/key-range locking theory, phantom prevention, composite locks, distributed deadlock, replication side effects, and complete recovery semantics are outside the frozen scope.
9. The `SELECT FOR UPDATE` parser flag to executor/scan chain was traced; every syntactic rewrite/derived-table variation was not exhaustively enumerated.
10. The source rationale says boot/recovery/non-worker contexts need no self-lock because they have no concurrent observer that will wait/unlock-all. A proof over every system transaction caller remains open.

### Search terms/areas recorded

`rg` searches covered `src/transaction/{lock_manager,lock_table,log_tran_table,log_manager,mvcc,log_2pc}*`, `src/query/{query_executor,scan_manager,xasl}*`, `src/parser/xasl_generation.c`, `src/transaction/locator_sr*`, `src/storage/{heap_file,btree}.c`, `src/base/{system_parameter,perf_monitor}*`, plus `unit_tests/` for: `LOCK_RESOURCE_TRANSACTION`, `lock_transaction_mvccid`, `self_locked_mvccid`, `INSERT_IN_PROGRESS`, `ACCESS_SPEC_FLAG_FOR_UPDATE`, `mvcc_select_lock_needed`, `lock_unlock_all`, `lock_detect_local_deadlock`, `lock_escalation`, `PERFMON_STAT_LOCK`, and `MVCC_LOCK`.

## Contradictions and scope refinements

1. **Pinned source versus newer local report.** The local context packet at `/home/vimkim/gh/my-cubrid-docs/code-analysis/cbrd-27157-server-side-loaddb-locking-transaction-mvccid-self-lo/f11fc42_codex/research/packets/cubrid.md` (SHA-256 `64b786b0a265f432841ac9d7c8ca3bb7b2ce4c4e21f671409a1ef9f25e044e7f`) describes a newer `f11fc42...` assertion permitting transaction-key locks for `TT_LOADDB`. The pinned `f30f1c2...` source at LMC 3539 has the strict `assert (thread_p->type != TT_LOADDB);`. This report must use the pinned behavior and may mention the later change only as version drift, not current evidence.
2. **“Lock table is volatile” requires qualification.** In ordinary transaction processing, in-memory lock entries disappear at shutdown and restart. Prepared 2PC is an explicit exception: object X locks are materialized, written with prepare state, and reacquired on recovery. The self-lock itself is not recovered.
3. **Transaction timeout display discrepancy.** Correct dump/event-log paths branch on transaction resource and print MVCCID, while `lock_set_error_for_timeout`'s transaction branch formats OID fields from the same union. Treat this as a suspected observability bug, not a demonstrated runtime symptom, until an experiment captures it.
4. **“Fresh self-X never waits” is an invariant inference, not a hard-coded no-wait call.** The call is unconditional and may technically enter the generic wait path. Monotonic unique allocation plus publication-after-ensure imply no legitimate prior holder/observer. A wait would indicate ID collision, premature publication, stale resource, or invariant violation.

## Suggested safe experiments (not run)

All experiments must use an isolated disposable database/server, finite waits, unique artifact paths, pre/post health checks, and cleanup/parameter restoration. Do not run on a shared or production instance.

### EXP-CUBRID-LOCK-01 — mode/conversion/escalation

- Setup: two `csql` sessions; create a small table, set a finite `lock_timeout`, choose a low but valid `lock_escalation`, preserve prior values.
- Action: hold row reads/writes and increment locked rows until the threshold; capture `cubrid lockdb` and server statistics before/after.
- Oracle: instance locks appear with class intention; compatible conversion follows the table; successful escalation changes class IS→S or IX/SIX→X and releases class granules.
- Gap addressed: C006 operational effect and hash-threshold distinction. Restart is required if testing boot-time hash sizing.
- Cleanup: rollback/commit sessions, restore parameters, drop DB or tables.

### EXP-CUBRID-LOCK-02 — timeout/deadlock/wakeup

- Setup: two sessions update rows A and B in opposite order with finite timeout; enable/capture lock event and error logs in owned paths.
- Action: T1 locks A, T2 locks B, then cross-request.
- Oracle: WFG reports a cycle and one transaction is abort/timeout victim; the survivor wakes and progresses; `lockdb` has no residual waiter after completion.
- Gap addressed: C011-C014 runtime timing, victim choice, no-hang behavior.
- Safety: watchdog kills only experiment-owned sessions after a bounded deadline.

### EXP-CUBRID-MVCC-03 — plain SELECT versus FOR UPDATE/DML

- Setup: T1 updates a row without commit. T2 runs plain SELECT, then SELECT FOR UPDATE/update with bounded timeout.
- Oracle: plain SELECT returns a snapshot-visible version without waiting on row X; locked read/DML waits or times out, and after T1 completion re-evaluates latest data rather than returning the stale predicate match.
- Evidence capture: SQL transcript, `lockdb` snapshots, session timestamps, isolation level and parameters.
- Gap addressed: C022-C026 behavioral validation.

### EXP-CUBRID-SELF-04 — unique and FK MVCCID rendezvous

- Setup: T1 performs uncommitted unique/PK insert. T2 performs conflicting unique insert; separately, an FK insert referencing T1's uncommitted parent. Run both T1 commit and rollback variants.
- Oracle: while blocked, lock dump shows a transaction resource with inserter MVCCID X and observer S request; after completion, T2 wakes and re-searches. Unique outcome differs for commit versus rollback; FK outcome reflects final parent existence.
- Evidence capture: lock dump before/wait/after, transaction IDs/MVCCIDs if exposed, SQL result/error, bounded timing.
- Gap addressed: C030-C036 and absence of a focused checked-in regression test.

### EXP-CUBRID-SELF-05 — subtransaction completion

- Setup: use a source-supported operation that assigns a sub-MVCCID in a disposable DB; first verify reachability without assuming a SQL savepoint maps directly to this internal sub-ID.
- Oracle: observer waits on sub-MVCCID and wakes at `logtb_complete_sub_mvcc`, before outer transaction completion, with inactive recheck succeeding.
- Gap addressed: C031, C036, C037. If no stable SQL route exists, mark blocked rather than adding unsafe hooks.

### EXP-CUBRID-2PC-06 — prepared-lock restart exception

- Setup: only in a purpose-built owned harness capable of prepare/restart and deterministic cleanup.
- Action: prepare a transaction with MVCC inserted rows, capture serialized lock info, restart, inspect reacquired object X locks.
- Oracle: object locks, not the MVCCID self-lock, are materialized/reacquired.
- Gap addressed: C016/C038 recovery qualification.
- Safety: higher risk; do not run until the harness and recovery cleanup are reviewed.

### EXP-CUBRID-PERF-07 — holder cardinality and metrics

- Setup: bulk insert N rows while sampling lock dump and generic counters; an instrumented or historical row-X baseline is required for quantitative comparison.
- Oracle: one transaction resource X represents many successful MVCC inserts, while tracked OID count grows with rows; measure peak entries/bytes and throughput rather than assuming them.
- Gap addressed: C028/C038. Without a comparable baseline, report only observed cardinality, not a speedup percentage.

## Book handoff points

- Lead with the distinction: **MVCC changes when locks are needed; self-lock changes what resource represents an uncommitted insert.**
- Use one diagram that joins `record.insert_mvccid -> transaction-resource S wait -> inserter X release -> index recheck` for both unique and FK.
- Keep class/row mode hierarchy separate from MVCCID transaction-resource semantics; the generic engine is shared, the key and policy are different.
- State transaction completion ordering explicitly: `MVCC active→terminal` precedes `X unlock/wakeup`.
- Preserve the 2PC qualification so “all locks are volatile” does not become false.
- Label C038 performance benefit as an inference until EXP-CUBRID-PERF-07 produces runtime evidence.
