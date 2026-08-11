# Research Packet — PostgreSQL Comparator

- **Role:** PostgreSQL Comparator
- **Topic:** CBRD-27157 server-side loaddb locking, transaction MVCCID self-lock, and `BU_LOCK`
- **Frozen scope:** `../scope.md`
- **Scope digest (SHA-256):** `f07826ef64e37143f055cdf4814be26d965d9bc531421f21439871475722fa5b`
- **PostgreSQL root:** `/home/vimkim/gh/pg/postgres`
- **PostgreSQL revision:** `fd2b89854d93d70fe8c9a69d5b8fafd5b9302cfc` (commit time `2026-08-05T11:40:39+02:00`)
- **CUBRID comparison revision:** `f11fc42594732c263d8f10101f9df73a21346ee9` (CUBRID facts are not re-proved in this packet)
- **Authored:** `2026-08-11T16:04:10+09:00`
- **Source state:** PostgreSQL tracked files match the pinned commit. The only `git status --short` entry was untracked `.omc/`.
- **Evidence method:** pinned PostgreSQL source only; PostgreSQL runtime experiments were excluded by the frozen scope.
- **Output boundary:** this packet only. PostgreSQL/CUBRID source, `report.json`, claims ledger, and Book HTML were not modified.

## 1. Comparator verdict

먼저 결론을 짧게 고정한다.

1. PostgreSQL의 `COPY FROM table`은 대상 relation에 `RowExclusiveLock`을 잡는다. 이름에 `Exclusive`가 들어가지만 이 mode는 다른 `RowExclusiveLock`과 호환된다. 즉 여러 일반 `INSERT`/`UPDATE`/`DELETE` 및 여러 `COPY FROM`이 relation lock만으로 서로를 배제하지 않는다.
2. 이 lock은 bulk load 전용 mode가 아니다. 모든 일반 DML이 쓰는 relation lock이다. 따라서 CUBRID `BU_LOCK`과는 **partial analogy**이다.
3. PostgreSQL core `COPY FROM`에는 CUBRID server-side loaddb처럼 “session transaction이 table-level bulk lock을 소유하고 별도 worker batch transaction이 행을 삽입한다”는 ownership split이 없다. 확인한 native COPY 경로는 호출 backend의 현재 transaction 안에서 실행된다. 이 분리 구조에는 **no equivalent**이다.
4. PostgreSQL transaction은 permanent XID를 처음 발급받을 때 자기 XID resource에 `ExclusiveLock`을 잡는다. 다른 transaction은 그 XID에 `ShareLock`을 요청하여 commit/abort까지 기다리고, lock을 받은 직후 놓은 다음 tuple/index 상태를 다시 검사한다.
5. 이 regular XID completion rendezvous는 CUBRID의 “MVCCID 발급자 `X_LOCK`, 관찰자 `S_LOCK`, transaction 종료 후 재검사”와 책임·mode 관계·lifetime이 실질적으로 같으므로, 좁게 한정하면 **equivalent**이다. 단, identifier, subtransaction, speculative insertion, 2PC의 세부 의미는 같지 않다.
6. unique conflict의 exact PostgreSQL 경로는 `SnapshotDirty`로 상대 tuple의 `xmin`/`xmax`를 얻고, XID lock을 기다린 뒤 B-tree 검색 전체를 다시 시작하는 것이다.
7. FK 검사는 같은 XID lock을 직접 “FK 전용 self-lock”으로 쓰는 것이 아니다. referenced PK tuple에 `KEY SHARE` row lock을 표시하는 과정에서 충돌 updater/deleter의 XID 또는 MultiXact 종료를 기다리고 update chain/key를 재검사한다. 이것은 MVCCID self-lock과 **partial analogy**이다.
8. `VirtualXID` lock도 transaction completion wait를 제공하지만 tuple에 기록되는 permanent identity가 아니며 재시작 또는 wraparound 뒤 재사용될 수 있다. 따라서 MVCCID self-lock의 정확한 대응이 아니라 **partial analogy**이다.

## 2. 같은 질문으로 두 종류의 lock 보기

### 2.1 `COPY FROM` relation lock

| 질문 | PostgreSQL 답 |
|---|---|
| 보호 상태 | relation을 사용하는 DML과 강한 DDL/maintenance operation 사이의 coordination |
| resource key | shared relation이면 `(0, rel_oid)`, 그 밖에는 `(database_oid, rel_oid)`인 `LOCKTAG_RELATION` |
| mode | `RowExclusiveLock` |
| owner | `sessionLock=false`이므로 현재 `ResourceOwner`, 즉 현재 transaction |
| lifetime | `DoCopy()` 끝에서 relation descriptor만 닫고 `NoLock`을 전달하므로 lock은 transaction end까지 유지 |
| 호환 | `AccessShare`, `RowShare`, `RowExclusive`, `ShareUpdateExclusive`와 호환 |
| 충돌 | `Share`, `ShareRowExclusive`, `Exclusive`, `AccessExclusive`와 충돌 |
| wait 뒤 | relation lock grant 뒤 command 진행; unique/FK row correctness는 별도 index/tuple protocol이 처리 |

핵심 초보자 함정은 `RowExclusiveLock`의 이름이다. 이것은 “한 행만 exclusive”라는 뜻도, “relation을 나 혼자 사용”이라는 뜻도 아니다. PostgreSQL lock manager의 **relation-level mode 이름**이며, compatibility table이 실제 의미를 결정한다.

### 2.2 XID completion lock

| 질문 | PostgreSQL 답 |
|---|---|
| 보호 상태 | “이 XID의 transaction/subtransaction이 아직 끝나지 않았다”는 completion rendezvous |
| resource key | `LOCKTAG_TRANSACTION(xid)` |
| inserter/holder mode | 자기 XID에 `ExclusiveLock` |
| observer/waiter mode | 상대 XID에 `ShareLock` |
| owner | XID를 부여받은 transaction/subtransaction의 `ResourceOwner` |
| lifetime | top-level XID lock은 정상 commit/abort의 lock release phase까지; subtransaction은 종료 시 별도 처리 가능 |
| wait 뒤 | waiter는 얻은 `ShareLock`을 즉시 release하고 XID/tuple/index 상태를 재검사 |
| prepared transaction | lock이 사라지지 않고 dummy `PGPROC`으로 이전되어 `COMMIT/ROLLBACK PREPARED`까지 유지될 수 있음 |

이 lock은 tuple 자체를 잠그는 lock과 다르다. tuple의 `xmin`/`xmax`가 “기다릴 transaction의 이름표”를 제공하고, heavyweight XID lock이 그 transaction의 종료를 기다리는 rendezvous가 된다.

## 3. Complete call paths

### 3.1 `COPY FROM` target relation lock

```text
DoCopy
  -> lockmode = RowExclusiveLock                # COPY FROM
  -> table_openrv(rangevar, RowExclusiveLock)
     -> relation_openrv
        -> RangeVarGetRelid macro
           -> RangeVarGetRelidExtended
              -> LockRelationOid(rel_oid, RowExclusiveLock)
                 -> LOCKTAG_RELATION(database_oid, rel_oid)
                 -> LockAcquireExtended(
                      sessionLock=false,
                      dontWait=false)
  -> BeginCopyFrom
  -> CopyFrom
  -> EndCopyFrom
  -> table_close(rel, NoLock)
     -> relation_close(rel, NoLock)
        # descriptor closes, relation lock remains
  -> transaction commit/abort
     -> ResourceOwnerRelease(... RESOURCE_RELEASE_LOCKS ...)
     -> ProcReleaseLocks
     -> LockReleaseAll(DEFAULT_LOCKMETHOD, ...)
```

`EndCopyFrom()`의 “release resources”는 COPY state/file/progress/memory cleanup이다. relation lock release가 아니다. 실제 `DoCopy()`가 `table_close(..., NoLock)`을 쓰고, `relation_close()` contract가 `NoLock`이면 transaction end에 자동 해제된다고 명시한다.

### 3.2 Native `COPY FROM` row and unique conflict

```text
DoCopy
  -> CopyFrom
     -> table_tuple_insert
     -> ExecInsertIndexTuples
        -> index_insert(UNIQUE_CHECK_YES)
           -> B-tree aminsert = btinsert
              -> _bt_doinsert
                 -> _bt_check_unique
                    -> SnapshotDirty sees conflicting tuple
                    -> xwait = SnapshotDirty.xmin or xmax
                 -> release B-tree buffer lock
                 -> if speculative token:
                      SpeculativeInsertionWait(xid, token)
                    else:
                      XactLockTableWait(xid)
                         -> acquire ShareLock on LOCKTAG_TRANSACTION(xid)
                         -> release ShareLock immediately after grant
                 -> goto search             # whole B-tree search/recheck
                 -> success, or definite UNIQUE_VIOLATION
```

두 개의 serializing 장치를 구분해야 한다.

- 동일 key 후보를 검사하고 index tuple을 넣는 짧은 구간은 B-tree leaf page write lock으로 직렬화한다.
- 상대 tuple을 만든 transaction이 아직 끝나지 않았다면 page lock을 놓고 XID completion lock을 기다린다. 기다린 동안 page와 tuple 상태가 바뀔 수 있으므로 `goto search`로 전체 검색을 다시 한다.

`INSERT ... ON CONFLICT`의 speculative tuple은 transaction 전체 종료가 아니라 해당 insertion verdict만 기다리기 위해 `(xid, token)` resource를 쓴다. 일반 `COPY FROM` unique check의 기본 경로와 같은 것으로 합치면 안 된다.

### 3.3 FK check and conflict completion

Pinned PostgreSQL에는 두 FK lookup 구현이 있다.

```text
RI_FKey_check
  -> applicable nonpartitioned/non-temporal FK:
       ri_FastPathBatchAdd OR ri_FastPathCheck
         -> direct PK unique-index probe
         -> ri_FastPathProbeOne
            -> ri_LockPKTuple
               -> table_tuple_lock(
                    LockTupleKeyShare,
                    LockWaitBlock,
                    LOCK_UPDATE_IN_PROGRESS,
                    optionally FIND_LAST_VERSION)
  -> fallback:
       open PK relation with RowShareLock
       execute SELECT ... FOR KEY SHARE OF x
       -> executor/heap tuple lock machinery
```

Heap tuple lock의 충돌 처리 핵심은 다음과 같다.

```text
heap_lock_tuple
  -> examine tuple xmax / MultiXact and requested KeyShare compatibility
  -> if conflicting ordinary xid:
       XactLockTableWait(xwait)
     else if conflicting MultiXact:
       MultiXactIdWait(...)
  -> reacquire buffer lock
  -> if xmax changed: goto l3 and re-evaluate
  -> follow update chain when required
  -> store current transaction XID/MultiXact in tuple xmax as row lock
  -> release auxiliary heavyweight tuple queue lock
```

따라서 FK 쪽의 long-lived 의미는 referenced tuple의 `xmax`/MultiXact에 기록되는 `KEY SHARE` row lock이다. heavyweight tuple lock은 공정한 대기열을 만드는 보조 장치이며 tuple에 표시가 끝나면 놓는다. 충돌 transaction의 completion을 기다릴 때 regular XID lock protocol을 재사용하지만, FK 자체가 별도의 transaction-ID self-lock을 발급하는 것은 아니다.

## 4. Lock modes, ownership, and release

### 4.1 Exact compatibility of `RowExclusiveLock`

Pinned source의 `LockConflicts[]`에서 `RowExclusiveLock` row는 다음 네 mode만 conflict bit로 가진다.

| Requested/held counterpart | Compatible with `RowExclusiveLock`? | 대표 의미 |
|---|---:|---|
| `AccessShareLock` | yes | plain `SELECT` |
| `RowShareLock` | yes | `SELECT FOR UPDATE/SHARE`가 relation에 잡는 mode |
| `RowExclusiveLock` | yes | `INSERT`, `UPDATE`, `DELETE`, `COPY FROM` |
| `ShareUpdateExclusiveLock` | yes | 일부 `VACUUM`/`ANALYZE`/concurrent index work |
| `ShareLock` | no | non-concurrent `CREATE INDEX` |
| `ShareRowExclusiveLock` | no | self-conflicting strong table mode |
| `ExclusiveLock` | no | `RowShare` 이상을 차단 |
| `AccessExclusiveLock` | no | 강한 DDL, `DROP`, `VACUUM FULL` 등 |

이 행렬 때문에 PostgreSQL `COPY FROM` relation lock은 “reader는 허용하지만 다른 writer는 막는 bulk lock”이 아니다. reader뿐 아니라 일반 writer도 허용한다.

### 4.2 Transaction owner, not session owner

`LockAcquireExtended()`는 `sessionLock=true`일 때 owner를 `NULL`, 아니면 `CurrentResourceOwner`로 정한다. `LockRelationOid()`, `XactLockTableInsert()`, `XactLockTableWait()`은 모두 `sessionLock=false`를 전달한다.

따라서 PostgreSQL core COPY의 relation lock과 그 transaction의 XID self-lock은 같은 caller transaction의 resource ownership 체계에 속한다. CUBRID server-side loaddb처럼 session transaction이 `BU_LOCK`을 잡고 worker batch transaction이 다른 transaction self-lock을 잡는 두-owner 구조가 아니다.

### 4.3 Commit/abort ordering

정상 commit의 중요한 순서는 다음과 같다.

```text
RecordTransactionCommit             # pg_xact에 durable commit 표시
ProcArrayEndTransaction             # 더 이상 in-progress가 아님을 공개
release visible resources
ResourceOwnerRelease(LOCKS)
  -> ProcReleaseLocks(true)
  -> LockReleaseAll(DEFAULT, false)  # non-session standard locks release
```

abort도 같은 핵심 순서를 가진다.

```text
RecordTransactionAbort
ProcArrayEndTransaction
ResourceOwnerRelease(LOCKS)
  -> ProcReleaseLocks(false)
  -> LockReleaseAll(DEFAULT, true)
```

즉 XID waiter가 `ShareLock`을 받은 시점에는 holder의 commit/abort 상태 publication이 먼저 끝나 있다. 그래서 waiter는 lock grant 자체를 성공/실패 판정으로 쓰지 않고 tuple/index visibility를 다시 읽는다.

Abort 중에는 LWLock과 열린 lock wait cleanup을 일찍 처리하지만, source comment가 말하듯 regular heavyweight locks는 abort가 충분히 정리될 때까지 유지한다.

### 4.4 2PC exception

`PREPARE TRANSACTION`은 보통 commit처럼 lock을 해제하지 않는다. `PostPrepare_Locks()`가 lock을 prepared transaction용 dummy `PGPROC`으로 이전한 뒤 original backend의 ProcArray entry를 지운다. 따라서 “backend가 command를 끝내면 XID lock이 항상 곧 풀린다”는 설명은 틀리다. prepared transaction이 해결될 때까지 relation/XID lock wait가 계속될 수 있다.

## 5. XID, VirtualXID, speculative token: do not merge them

| Resource | Identity | Holder/waiter | 시작 | 종료 | MVCCID self-lock mapping |
|---|---|---|---|---|---|
| regular XID lock | permanent `TransactionId` | owner `Exclusive`, waiter `Share` | XID lazy assignment 시 | commit/abort; 2PC이면 prepared resolution | **equivalent**, bounded to completion rendezvous |
| VirtualXID lock | `(procNumber, localTransactionId)` | owner fast-path/`Exclusive`, waiter `Share` | transaction start, permanent XID 전에도 존재 | top-level transaction end | **partial analogy** |
| speculative token | `(xid, insertion_token)` | inserter `Exclusive`, contender `Share` | speculative insertion 시작 | keep/abort verdict 직후 | **partial analogy** |
| FK tuple KeyShare | tuple `xmax`/MultiXact + auxiliary tuple queue lock | referenced-row reader vs key updater/deleter | PK row check | checking transaction end for logical row lock | **partial analogy** |

`VirtualXID`가 정확한 대응이 아닌 이유:

- tuple에 저장하는 permanent MVCC identity가 아니다.
- `(procNumber, localTransactionId)`는 short-term unique이고 restart/wraparound 뒤 재사용될 수 있어 disk에 저장하면 안 된다.
- transaction start부터 존재하여 “아직 permanent XID가 없는 transaction도 기다린다”는 일반 completion 기능을 제공한다.
- unique B-tree와 traced FK/COPY path에서 `VirtualXactLock()` 직접 호출은 발견되지 않았다.

## 6. Failure, abort, and wait behavior

### 6.1 Lock acquisition and wait

- conflict가 없으면 grant된다.
- conflict가 있고 `dontWait=false`이면 waiter queue에 들어가 `ProcSleep()`을 거친다.
- wait 중 cancel, process death, lock timeout, deadlock detection은 normal error cleanup으로 이어진다. `WaitOnLock()`은 `LockErrorCleanup()`이 회수할 `awaitedLock`/owner를 등록한다.
- lock table shared memory가 부족하면 `max_locks_per_transaction` 증가 hint와 함께 error가 날 수 있다.
- `ProcSleep()`은 wait start timestamp를 기록하고 locktag type을 wait event에 넣는다.

### 6.2 COPY and constraint errors

- definite duplicate는 `_bt_check_unique()`가 `UNIQUE_VIOLATION`을 발생시킨다.
- FK lookup 실패는 `ri_ReportViolation()`으로 이어진다.
- serialization snapshot에서 concurrent PK delete/update는 pinned fast-path가 serialization failure를 낼 수 있다.
- 일반 `ERROR`는 현재 transaction 또는 감싸는 subtransaction의 abort path로 전파되고, 그 owner의 locks/resources가 정리된다.
- `COPY ... ON_ERROR`의 일부 input conversion skip 동작은 존재하지만 lock/unique/FK correctness error를 임의로 성공 처리하는 일반 escape hatch로 해석하면 안 된다.

## 7. Observability

### 7.1 `pg_locks`

`pg_locks`는 `pg_lock_status()` 결과를 노출한다. 이 함수는 다음을 구분한다.

- relation lock: `locktype`, `database`, `relation`
- transaction lock: `transactionid`
- virtual transaction lock: `virtualxid`
- speculative token: `transactionid`와 token field
- 공통: `pid`, `mode`, `granted`, `fastpath`, `waitstart`

따라서 `COPY FROM` 중 대상 relation의 `RowExclusiveLock`, transaction XID의 `ExclusiveLock`, 충돌 waiter의 `ShareLock`을 관찰할 수 있다.

주의: PostgreSQL row lock의 long-lived 상태는 대체로 tuple header의 `xmax`/MultiXact에 저장된다. `heap_lock_tuple()`이 auxiliary heavyweight tuple lock을 tuple 표시 후 놓으므로, `pg_locks`의 tuple entry는 주로 queueing/wait 구간의 보조 상태이며 “모든 held row lock 목록”이 아니다.

### 7.2 COPY progress and wait event

`BeginCopyFrom()`은 `PROGRESS_COMMAND_COPY`를 시작하고 `CopyFrom()`은 processed tuple 수를 갱신하며 `EndCopyFrom()`은 progress command를 끝낸다. `pg_stat_progress_copy`는 다음을 노출한다.

- `pid`, database, target `relid`
- `COPY FROM`/`COPY TO`
- source type
- processed/total bytes
- processed/excluded/skipped tuples

lock wait 중에는 `ProcSleep()`이 `PG_WAIT_LOCK | locktag_type`으로 wait event를 보고하므로 `pg_stat_activity`와 `pg_locks`를 함께 보는 것이 유용하다.

## 8. Semantic mapping to CUBRID

아래 CUBRID 측 설명은 frozen scope가 정의한 비교 대상이다. 최종 comparison Claim에는 CUBRID role packet의 pinned source refs를 반드시 추가해야 한다.

### 8.1 CUBRID `BU_LOCK` ↔ PostgreSQL `COPY FROM RowExclusiveLock`

**Verdict: partial analogy.**

같은 점:

- table/class에 대응하는 coarse resource를 잡는다.
- bulk insert command 시작 전 획득한다.
- transaction lifetime lock manager가 관리한다.
- DML과 강한 schema operation 사이의 coordination에 참여한다.

다른 점:

- PostgreSQL에는 bulk load 전용 standard relation lock mode가 없다.
- `RowExclusiveLock`은 모든 `INSERT`/`UPDATE`/`DELETE`가 사용한다.
- PostgreSQL `RowExclusiveLock`은 self-compatible이며 다른 일반 writer를 막지 않는다.
- frozen scope의 CUBRID `BU_LOCK`은 별도의 mode와 별도의 compatibility 정책을 가진다. exact CUBRID matrix는 CUBRID source packet을 기준으로 해야 한다.
- PostgreSQL core COPY에서는 relation lock holder와 row inserter가 같은 current transaction이다.

### 8.2 CUBRID session `BU_LOCK` owner ↔ worker batch owner split

**Verdict: no equivalent in traced PostgreSQL core COPY.**

Native COPY source에서 transaction start/commit/abort, background worker 등록, thread/fork creation을 검색했지만 해당 ownership split을 만드는 호출을 찾지 못했다. `CopyMultiInsertInfo`의 “multi”는 tuple buffering과 bulk AM insertion 최적화이며 transaction 분리가 아니다.

이 negative conclusion은 PostgreSQL core heap-table COPY path에 한정한다. FDW callback, user trigger/function, extension은 core 밖의 실행이나 side effect를 추가할 수 있다.

### 8.3 CUBRID MVCCID self-lock ↔ PostgreSQL regular XID lock

**Verdict: equivalent within the regular transaction-completion rendezvous responsibility.**

실질적으로 같은 불변식:

```text
observable tuple creator identity
  => creator holds incompatible self lock on that identity
  => observer can wait with shared lock
  => completion publishes commit/abort before self lock release
  => observer rechecks tuple/index state after wait
```

구체적 차이:

- PostgreSQL key는 32-bit `TransactionId`; CUBRID key는 MVCCID이다.
- PostgreSQL은 permanent XID를 받은 top/subtransaction마다 XID lock을 등록한다. CUBRID의 exact lazy allocation 및 INSID omission 조건은 별도 CUBRID evidence가 필요하다.
- PostgreSQL waiter는 subtransaction XID lock이 사라졌는데 top parent가 계속 실행 중이면 `SubTransGetTopmostTransaction()`으로 올라가 다시 기다린다.
- PostgreSQL speculative insertion은 transaction 전체가 아니라 `(xid, token)` verdict lock을 쓴다.
- PostgreSQL 2PC는 XID/relation locks를 prepared transaction으로 이전할 수 있다.
- PostgreSQL VirtualXID는 permanent tuple identity가 아니므로 MVCCID와 합치면 안 된다.

### 8.4 CUBRID FK/unique observer ↔ PostgreSQL constraint protocols

| CUBRID comparison responsibility | Nearest PostgreSQL mechanism | Verdict | Gap |
|---|---|---|---|
| uncommitted unique-key inserter completion wait | B-tree `SnapshotDirty` -> regular XID `ShareLock` wait -> full search restart | equivalent on rendezvous axis | index/page serialization and speculative token details differ |
| referenced row protected from key delete/update | tuple `KEY SHARE`, `xmax`/MultiXact, XID/MultiXact wait, chain recheck | partial analogy | resource is referenced tuple row lock, not only creator-ID self-lock |
| transaction exists before permanent MVCC ID | VirtualXID lock | partial analogy | not tuple-stamped or persistent identity |

## 9. Examined files, symbols, ranges, and immutable hashes

모든 line range는 pinned revision의 1-based line이다. `file_sha256`는 working-tree file bytes의 SHA-256이며 tracked files가 pinned commit과 일치함을 확인했다.

| File | Complete symbols/ranges read | file_sha256 |
|---|---|---|
| `src/backend/commands/copy.c` | `DoCopy` 62-386 | `4c0b985775a2d3ef5aeac77361da7ac30fa6cefd318d71edcb40e8502e7d9915` |
| `src/backend/commands/copyfrom.c` | `CopyFrom` 781-1519; `BeginCopyFrom` 1535-1932; `EndCopyFrom` 1937-1961 | `ca848cd559a6b15f0fde1441b8c1cd7da618ef5fc91132f6b0f62acfaf68b8f6` |
| `src/backend/access/table/table.c` | `table_openrv` 82-92; `table_close` 125-129 | `5b84f0254e8825aae8b335711e0769ff1c099e1a3eaf187d0729edf9c6fe680c` |
| `src/backend/access/common/relation.c` | `relation_openrv` 137-161; `relation_close` 205-217 | `714f3202cac1ae97979465b1efb4deedebe0adf7cc698042462fd10dce5cb566` |
| `src/include/catalog/namespace.h` | `RangeVarGetRelid` macro 98-100 | `68422b5398f2fa38bde7d90a13d4bbff53b130ab5acb6d58dcb413bff514acee` |
| `src/backend/catalog/namespace.c` | `RangeVarGetRelidExtended` 442-643 | `897afff0f3214510ed000e31805effb45964fb971bab3c7a98f6c6711f8053d0` |
| `src/include/storage/lockdefs.h` | standard mode constants 20-59 | `7db1a4531f5da94667f2ca498136e6796d89a8ba56115fd90bef198e09a2af68` |
| `src/include/storage/locktag.h` | `LockTagType` 35-50; relation/XID/VXID/speculative macros 80-153 | `0ffaea18914516886ea4892c642f2274acb65e32b51c9ceca92e1cef1c9c5a81` |
| `src/include/storage/lock.h` | `VirtualTransactionId` 47-82; `PROCLOCK`/`LOCALLOCKOWNER` contracts 160-272 | `9e997e40e45889d6d1b9040440303d244df566546b48e7e6b9d12f99d3767e16` |
| `src/backend/storage/lmgr/lmgr.c` | `LockRelationOid` 106-139; `XactLockTableInsert` 621-629; `XactLockTableDelete` 638-646; `XactLockTableWait` 662-730; `ConditionalXactLockTableWait` 738-772; speculative functions 785-839 | `7301f269a04cb423ff830d5490300185cf7b36c675b515638cda235125688eaf` |
| `src/backend/storage/lmgr/lock.c` | `LockConflicts` 68-108; `LockAcquire` 805-813; `LockAcquireExtended` 832-1278; `WaitOnLock` 1939-2019; `LockReleaseAll` 2315-2582; VXID functions 4599-4826 | `bad8fb3ce27d2a4bda77c4e030202eb6395665096bb0d6bacced8f5f77d75eb5` |
| `src/backend/storage/lmgr/proc.c` | `ProcReleaseLocks` 905-916; `ProcSleep` 1365-1605 | `67031da14df638c9df197a8e77649421836ba5ad4eb6097d01b3661d1f69b9a4` |
| `src/backend/access/transam/xact.c` | `AssignTransactionId` 636-787; `StartTransaction` 2105-2261; `CommitTransaction` 2269-2550; `PrepareTransaction` 2558-2850; `AbortTransaction` 2854-3056 | `b40898eda7d02c7cf4b7671ab3bf1b3d0ea757cf33765f98fe074d98e8382df2` |
| `src/backend/utils/resowner/resowner.c` | `ResourceOwnerRelease` 664-682; `ResourceOwnerReleaseInternal` 684-818 | `0fd0f9cac6abe6817a6cca5ef3755d9916d9571e5b1c381cb5306e4fb484be27` |
| `src/backend/executor/execIndexing.c` | `ExecInsertIndexTuples` 311-519 | `8d8cb227ddb0dd0cb949a840a49db209701937cc0678d4f1bdc5aa44c0a245df` |
| `src/backend/access/index/indexam.c` | `index_insert` 213-235 | `1fb98876ba35025d918c9608c57556259a30b9d6d8ba0b03e0b376672d484b3d` |
| `src/backend/access/nbtree/nbtree.c` | `btinsert` 205-224 | `c2c4644639540da0861dd47b94406f2cd43a17375c5fc9c592f74b9a5038f75c` |
| `src/backend/access/nbtree/nbtinsert.c` | `_bt_doinsert` 104-279; `_bt_check_unique` 410-786 | `0ef3d779ec130b82bd2658c32d71085a629d218e91808e929ee0d0dc43baa617` |
| `src/include/utils/snapshot.h` | `SNAPSHOT_DIRTY` contract 72-98 | `b4c9413a287028a87d7c6f557c16ce002da227c4d5b9a80426a10ad2eda23ea7` |
| `src/backend/utils/adt/ri_triggers.c` | `RI_FKey_check` 364-619; `ri_PerformCheck` 2650-2789; `ri_FastPathCheck` 2802-2865; `ri_FastPathProbeOne` 3240-3265; `ri_LockPKTuple` 3278-3344 | `9aeecd49d4ce8bd9c1695fa733003793d6d0995818f3652e92801565c63c89d8` |
| `src/backend/access/heap/heapam.c` | `heap_lock_tuple` 4727-5439 | `9be2f576df608c95992b65b2009640c3da5a9238aba73cf2cf106af124f77878` |
| `src/backend/utils/adt/lockfuncs.c` | `pg_lock_status` 92-444 | `25318bcb3c2822e5d4f2268f62684d28b70fce21c968684bc85be0eef3b9a613` |
| `src/backend/catalog/system_views.sql` | `pg_locks` 439-440; `pg_stat_progress_copy` 1466-1484 | `6203864baafee05bda77106d6e1bafd48a6ec902f3361b0f4ecda3b9bc2cc9e2` |
| `src/include/commands/progress.h` | COPY progress constants 172-189 | `6780d402b02b7aa5adc26f6597f1f7b51df74a28143b49ac56c8cee93acb5283` |

## 10. Claim candidates following the ledger schema

아래 객체는 PostgreSQL direct-source Claim 후보이다. `report_locations`는 planned PostgreSQL chapter anchor이며 integrator가 실제 Book anchor와 맞춰야 한다. Runtime evidence는 없다.

```json
{
  "id": "PG-C001",
  "claim_ko": "PostgreSQL의 COPY FROM table은 대상 relation에 RowExclusiveLock을 획득하고, DoCopy 종료 시 relation descriptor는 NoLock으로 닫으므로 이 relation lock은 현재 transaction 종료까지 유지된다.",
  "database": "postgresql",
  "revision": "fd2b89854d93d70fe8c9a69d5b8fafd5b9302cfc",
  "kind": "source",
  "confidence": "SOURCE-CONFIRMED",
  "source_refs": [
    {"path":"src/backend/commands/copy.c","symbol":"DoCopy","line_start":62,"line_end":386,"file_sha256":"4c0b985775a2d3ef5aeac77361da7ac30fa6cefd318d71edcb40e8502e7d9915","evidence_state":"COMMIT"},
    {"path":"src/backend/catalog/namespace.c","symbol":"RangeVarGetRelidExtended","line_start":442,"line_end":643,"file_sha256":"897afff0f3214510ed000e31805effb45964fb971bab3c7a98f6c6711f8053d0","evidence_state":"COMMIT"},
    {"path":"src/backend/storage/lmgr/lmgr.c","symbol":"LockRelationOid","line_start":106,"line_end":139,"file_sha256":"7301f269a04cb423ff830d5490300185cf7b36c675b515638cda235125688eaf","evidence_state":"COMMIT"},
    {"path":"src/backend/access/common/relation.c","symbol":"relation_close","line_start":196,"line_end":217,"file_sha256":"714f3202cac1ae97979465b1efb4deedebe0adf7cc698042462fd10dce5cb566","evidence_state":"COMMIT"}
  ],
  "runtime_run_ids": [],
  "limitations_ko": "partition routing이 추가 leaf relation lock을 얻는 세부는 이 Claim에 포함하지 않는다. FDW의 외부 storage lock도 포함하지 않는다.",
  "report_locations": ["chapters/08-postgresql-analysis.html#claim-PG-C001"]
}
```

```json
{
  "id": "PG-C002",
  "claim_ko": "PostgreSQL RowExclusiveLock은 AccessShare, RowShare, RowExclusive, ShareUpdateExclusive와 호환되고 Share, ShareRowExclusive, Exclusive, AccessExclusive와 충돌하므로 COPY FROM relation lock은 다른 일반 writer를 배제하는 bulk-exclusive lock이 아니다.",
  "database": "postgresql",
  "revision": "fd2b89854d93d70fe8c9a69d5b8fafd5b9302cfc",
  "kind": "source",
  "confidence": "SOURCE-CONFIRMED",
  "source_refs": [
    {"path":"src/include/storage/lockdefs.h","symbol":"RowExclusiveLock","line_start":28,"line_end":48,"file_sha256":"7db1a4531f5da94667f2ca498136e6796d89a8ba56115fd90bef198e09a2af68","evidence_state":"COMMIT"},
    {"path":"src/backend/storage/lmgr/lock.c","symbol":"LockConflicts","line_start":68,"line_end":108,"file_sha256":"bad8fb3ce27d2a4bda77c4e030202eb6395665096bb0d6bacced8f5f77d75eb5","evidence_state":"COMMIT"}
  ],
  "runtime_run_ids": [],
  "limitations_ko": "relation lock mode matrix만 설명하며 tuple/index/page-level serialization은 별도 protocol이다.",
  "report_locations": ["chapters/08-postgresql-analysis.html#claim-PG-C002"]
}
```

```json
{
  "id": "PG-C003",
  "claim_ko": "PostgreSQL transaction/subtransaction은 permanent XID를 발급받을 때 자기 XID resource에 ExclusiveLock을 자기 ResourceOwner 소유로 등록하고, 다른 transaction은 그 XID에 ShareLock을 얻어 commit 또는 abort 완료를 기다린 뒤 즉시 release한다.",
  "database": "postgresql",
  "revision": "fd2b89854d93d70fe8c9a69d5b8fafd5b9302cfc",
  "kind": "source",
  "confidence": "SOURCE-CONFIRMED",
  "source_refs": [
    {"path":"src/backend/access/transam/xact.c","symbol":"AssignTransactionId","line_start":636,"line_end":787,"file_sha256":"b40898eda7d02c7cf4b7671ab3bf1b3d0ea757cf33765f98fe074d98e8382df2","evidence_state":"COMMIT"},
    {"path":"src/backend/storage/lmgr/lmgr.c","symbol":"XactLockTableInsert","line_start":614,"line_end":629,"file_sha256":"7301f269a04cb423ff830d5490300185cf7b36c675b515638cda235125688eaf","evidence_state":"COMMIT"},
    {"path":"src/backend/storage/lmgr/lmgr.c","symbol":"XactLockTableWait","line_start":648,"line_end":730,"file_sha256":"7301f269a04cb423ff830d5490300185cf7b36c675b515638cda235125688eaf","evidence_state":"COMMIT"},
    {"path":"src/include/storage/locktag.h","symbol":"SET_LOCKTAG_TRANSACTION","line_start":125,"line_end":132,"file_sha256":"0ffaea18914516886ea4892c642f2274acb65e32b51c9ceca92e1cef1c9c5a81","evidence_state":"COMMIT"}
  ],
  "runtime_run_ids": [],
  "limitations_ko": "subtransaction waiter는 top parent XID로 올라갈 수 있고, speculative insertion과 prepared transaction은 별도 lifetime rule을 가진다.",
  "report_locations": ["chapters/08-postgresql-analysis.html#claim-PG-C003"]
}
```

```json
{
  "id": "PG-C004",
  "claim_ko": "PostgreSQL B-tree immediate unique check는 SnapshotDirty에서 in-progress duplicate tuple의 xmin 또는 xmax를 얻고, page lock을 놓은 뒤 XID 또는 speculative-token completion을 기다리고 전체 B-tree search를 다시 수행하여 최종 성공 또는 unique violation을 결정한다.",
  "database": "postgresql",
  "revision": "fd2b89854d93d70fe8c9a69d5b8fafd5b9302cfc",
  "kind": "source",
  "confidence": "SOURCE-CONFIRMED",
  "source_refs": [
    {"path":"src/backend/access/nbtree/nbtinsert.c","symbol":"_bt_doinsert","line_start":104,"line_end":279,"file_sha256":"0ef3d779ec130b82bd2658c32d71085a629d218e91808e929ee0d0dc43baa617","evidence_state":"COMMIT"},
    {"path":"src/backend/access/nbtree/nbtinsert.c","symbol":"_bt_check_unique","line_start":410,"line_end":786,"file_sha256":"0ef3d779ec130b82bd2658c32d71085a629d218e91808e929ee0d0dc43baa617","evidence_state":"COMMIT"},
    {"path":"src/backend/storage/lmgr/lmgr.c","symbol":"SpeculativeInsertionWait","line_start":774,"line_end":839,"file_sha256":"7301f269a04cb423ff830d5490300185cf7b36c675b515638cda235125688eaf","evidence_state":"COMMIT"}
  ],
  "runtime_run_ids": [],
  "limitations_ko": "B-tree immediate unique index 경로이다. deferrable/exclusion/다른 index AM의 세부 protocol을 일반화하지 않는다.",
  "report_locations": ["chapters/08-postgresql-analysis.html#claim-PG-C004"]
}
```

```json
{
  "id": "PG-C005",
  "claim_ko": "Pinned PostgreSQL의 FK existence check는 적용 가능한 경우 PK unique index를 직접 probe하고 referenced tuple에 KeyShare lock을 요청하며, 충돌 updater/deleter의 XID 또는 MultiXact를 기다린 뒤 xmax와 update chain을 재검사한다. fallback은 SELECT FOR KEY SHARE를 실행한다.",
  "database": "postgresql",
  "revision": "fd2b89854d93d70fe8c9a69d5b8fafd5b9302cfc",
  "kind": "source",
  "confidence": "SOURCE-CONFIRMED",
  "source_refs": [
    {"path":"src/backend/utils/adt/ri_triggers.c","symbol":"RI_FKey_check","line_start":364,"line_end":619,"file_sha256":"9aeecd49d4ce8bd9c1695fa733003793d6d0995818f3652e92801565c63c89d8","evidence_state":"COMMIT"},
    {"path":"src/backend/utils/adt/ri_triggers.c","symbol":"ri_LockPKTuple","line_start":3278,"line_end":3344,"file_sha256":"9aeecd49d4ce8bd9c1695fa733003793d6d0995818f3652e92801565c63c89d8","evidence_state":"COMMIT"},
    {"path":"src/backend/access/heap/heapam.c","symbol":"heap_lock_tuple","line_start":4727,"line_end":5439,"file_sha256":"9be2f576df608c95992b65b2009640c3da5a9238aba73cf2cf106af124f77878","evidence_state":"COMMIT"}
  ],
  "runtime_run_ids": [],
  "limitations_ko": "이미 probe로 찾은 referenced tuple의 concurrent update/delete conflict path를 확인했다. 다른 transaction이 아직 commit하지 않은 parent insert를 현재 snapshot이 어떻게 처리하는지는 이 Claim에 포함하지 않는다.",
  "report_locations": ["chapters/08-postgresql-analysis.html#claim-PG-C005"]
}
```

```json
{
  "id": "PG-C006",
  "claim_ko": "PostgreSQL은 commit/abort 상태를 ProcArray에 먼저 반영한 다음 ResourceOwner lock phase에서 transaction-owned relation/XID/VXID locks를 해제하므로 XID waiter는 grant 후 tuple/index 상태를 안전하게 재검사할 수 있다.",
  "database": "postgresql",
  "revision": "fd2b89854d93d70fe8c9a69d5b8fafd5b9302cfc",
  "kind": "source",
  "confidence": "SOURCE-CONFIRMED",
  "source_refs": [
    {"path":"src/backend/access/transam/xact.c","symbol":"CommitTransaction","line_start":2269,"line_end":2550,"file_sha256":"b40898eda7d02c7cf4b7671ab3bf1b3d0ea757cf33765f98fe074d98e8382df2","evidence_state":"COMMIT"},
    {"path":"src/backend/access/transam/xact.c","symbol":"AbortTransaction","line_start":2854,"line_end":3056,"file_sha256":"b40898eda7d02c7cf4b7671ab3bf1b3d0ea757cf33765f98fe074d98e8382df2","evidence_state":"COMMIT"},
    {"path":"src/backend/utils/resowner/resowner.c","symbol":"ResourceOwnerRelease","line_start":664,"line_end":818,"file_sha256":"0fd0f9cac6abe6817a6cca5ef3755d9916d9571e5b1c381cb5306e4fb484be27","evidence_state":"COMMIT"},
    {"path":"src/backend/storage/lmgr/proc.c","symbol":"ProcReleaseLocks","line_start":889,"line_end":916,"file_sha256":"67031da14df638c9df197a8e77649421836ba5ad4eb6097d01b3661d1f69b9a4","evidence_state":"COMMIT"},
    {"path":"src/backend/storage/lmgr/lock.c","symbol":"LockReleaseAll","line_start":2310,"line_end":2582,"file_sha256":"bad8fb3ce27d2a4bda77c4e030202eb6395665096bb0d6bacced8f5f77d75eb5","evidence_state":"COMMIT"}
  ],
  "runtime_run_ids": [],
  "limitations_ko": "PREPARE TRANSACTION은 locks를 prepared transaction PGPROC으로 이전하므로 ordinary commit/abort release와 다르다.",
  "report_locations": ["chapters/08-postgresql-analysis.html#claim-PG-C006"]
}
```

```json
{
  "id": "PG-C007",
  "claim_ko": "PostgreSQL VirtualXID lock은 permanent XID 발급 전부터 transaction completion wait를 제공하지만 short-term process-local identity이며 disk tuple에 저장하는 permanent transaction identity가 아니다.",
  "database": "postgresql",
  "revision": "fd2b89854d93d70fe8c9a69d5b8fafd5b9302cfc",
  "kind": "source",
  "confidence": "SOURCE-CONFIRMED",
  "source_refs": [
    {"path":"src/include/storage/lock.h","symbol":"VirtualTransactionId","line_start":47,"line_end":82,"file_sha256":"9e997e40e45889d6d1b9040440303d244df566546b48e7e6b9d12f99d3767e16","evidence_state":"COMMIT"},
    {"path":"src/backend/access/transam/xact.c","symbol":"StartTransaction","line_start":2105,"line_end":2261,"file_sha256":"b40898eda7d02c7cf4b7671ab3bf1b3d0ea757cf33765f98fe074d98e8382df2","evidence_state":"COMMIT"},
    {"path":"src/backend/storage/lmgr/lock.c","symbol":"VirtualXactLockTableInsert","line_start":4582,"line_end":4614,"file_sha256":"bad8fb3ce27d2a4bda77c4e030202eb6395665096bb0d6bacced8f5f77d75eb5","evidence_state":"COMMIT"},
    {"path":"src/backend/storage/lmgr/lock.c","symbol":"VirtualXactLock","line_start":4713,"line_end":4826,"file_sha256":"bad8fb3ce27d2a4bda77c4e030202eb6395665096bb0d6bacced8f5f77d75eb5","evidence_state":"COMMIT"}
  ],
  "runtime_run_ids": [],
  "limitations_ko": "general transaction completion mechanism이며 traced COPY unique/FK path의 tuple creator identity로 직접 사용되지는 않는다.",
  "report_locations": ["chapters/08-postgresql-analysis.html#claim-PG-C007"]
}
```

```json
{
  "id": "PG-C008",
  "claim_ko": "PostgreSQL은 pg_locks에서 relation, transaction, virtualxid, speculative-token lock의 mode/granted/waitstart를 노출하고 pg_stat_progress_copy에서 COPY target과 byte/tuple progress를 노출한다.",
  "database": "postgresql",
  "revision": "fd2b89854d93d70fe8c9a69d5b8fafd5b9302cfc",
  "kind": "source",
  "confidence": "SOURCE-CONFIRMED",
  "source_refs": [
    {"path":"src/backend/utils/adt/lockfuncs.c","symbol":"pg_lock_status","line_start":92,"line_end":444,"file_sha256":"25318bcb3c2822e5d4f2268f62684d28b70fce21c968684bc85be0eef3b9a613","evidence_state":"COMMIT"},
    {"path":"src/backend/catalog/system_views.sql","symbol":"pg_locks","line_start":439,"line_end":440,"file_sha256":"6203864baafee05bda77106d6e1bafd48a6ec902f3361b0f4ecda3b9bc2cc9e2","evidence_state":"COMMIT"},
    {"path":"src/backend/catalog/system_views.sql","symbol":"pg_stat_progress_copy","line_start":1466,"line_end":1484,"file_sha256":"6203864baafee05bda77106d6e1bafd48a6ec902f3361b0f4ecda3b9bc2cc9e2","evidence_state":"COMMIT"},
    {"path":"src/backend/commands/copyfrom.c","symbol":"BeginCopyFrom","line_start":1535,"line_end":1932,"file_sha256":"ca848cd559a6b15f0fde1441b8c1cd7da618ef5fc91132f6b0f62acfaf68b8f6","evidence_state":"COMMIT"}
  ],
  "runtime_run_ids": [],
  "limitations_ko": "pg_locks는 tuple xmax/MultiXact에 저장된 모든 logical row lock을 완전한 holder 목록으로 보여 주지 않는다.",
  "report_locations": ["chapters/08-postgresql-analysis.html#claim-PG-C008"]
}
```

## 11. Comparison claim integration notes

다음 두 comparison conclusion은 PostgreSQL 측 evidence는 준비되었지만, claim-ledger rule상 CUBRID/MySQL source refs를 함께 넣기 전에는 최종 `CMP-*` Claim으로 만들면 안 된다.

| Proposed ID | analogy_class | Korean conclusion | PostgreSQL premises | Integration requirement |
|---|---|---|---|---|
| `CMP-Cxxx-BU` | `partial analogy` | CUBRID `BU_LOCK`과 PostgreSQL `COPY FROM RowExclusiveLock`은 coarse table coordination이라는 책임만 비슷하고 mode 목적, compatibility, owner topology가 다르다. | `PG-C001`, `PG-C002` | exact CUBRID BU matrix/owner refs와 MySQL comparator refs 추가 |
| `CMP-Cxxx-XID` | `equivalent` | regular non-speculative completion rendezvous에 한해 CUBRID MVCCID `X/S` self-lock과 PostgreSQL XID `Exclusive/Share` lock은 같은 중심 불변식을 구현한다. | `PG-C003`, `PG-C004`, `PG-C006` | CUBRID lazy MVCCID/self-lock/wait-recheck refs와 MySQL comparator refs 추가; gaps를 limitations에 유지 |

## 12. Negative searches

Negative claim은 검색 범위와 대체 용어를 함께 기록한다.

### 12.1 Native COPY가 별도 transaction/worker를 만드는가

Search scope:

- `src/backend/commands/copy.c`
- `src/backend/commands/copyfrom.c`
- `src/backend/commands/copyfromparse.c`
- `src/include/commands/copyfrom_internal.h`

Patterns:

```text
StartTransaction|CommitTransaction|AbortTransaction
BeginInternalSubTransaction|ReleaseCurrentSubTransaction
RollbackAndReleaseCurrentSubTransaction|SPI_commit|SPI_rollback
BackgroundWorker|RegisterDynamicBackgroundWorker|pthread_|fork(
```

Result: no matches.

Interpretation: traced PostgreSQL core COPY files do not create CUBRID-style session/worker transaction boundaries. This supports the bounded inference that native heap COPY executes in the caller's current transaction. It does not prove that arbitrary FDW callbacks, triggers, procedural code, or extensions cannot start external work.

### 12.2 Dedicated bulk table lock mode

Search scope:

- COPY files above
- `src/include/storage`
- `src/backend/storage/lmgr`

Patterns:

```text
BU_LOCK
BULK UPDATE / BULK INSERT spelling variants
BulkUpdateLock / BulkInsertLock
```

Result: no matches. Positive evidence is stronger: `DoCopy()` explicitly selects the standard `RowExclusiveLock`, and `lockdefs.h` contains the standard relation modes.

### 12.3 VirtualXID or direct XID wait in COPY frontend

Search scope:

- COPY files
- `src/backend/access/nbtree`
- `src/backend/utils/adt/ri_triggers.c`

Results:

- no `VirtualXactLock(` call in the scoped COPY/unique/FK paths;
- no direct `XactLockTableWait(` in COPY frontend files;
- positive calls occur lower in `_bt_doinsert()` and `heap_lock_tuple()`.

Interpretation: COPY delegates transaction-completion waiting to index/tuple access methods. A Book diagram should not draw a fictitious direct `CopyFrom -> XactLockTableWait` call edge.

## 13. Contradictions and beginner traps

1. **`RowExclusiveLock` sounds exclusive but is self-compatible.** Mode name alone is not evidence; use the compatibility matrix.
2. **`EndCopyFrom()` cleanup does not release the relation lock.** `DoCopy()` closes with `NoLock`, and `relation_close()` says this retains the lock until xact end.
3. **`CopyMultiInsertInfo` is not multiple transactions.** It buffers tuples/insertion work inside one current transaction.
4. **XID lock wait success does not mean commit.** The holder might have committed or aborted. The waiter must inspect transaction/tuple/index state again.
5. **VirtualXID is not tuple `xmin`.** It is a short-lived `(procNumber, localTransactionId)` identity and must not be stored on disk.
6. **Speculative token wait is shorter than transaction completion.** It waits for one insertion verdict, not necessarily the transaction end.
7. **FK checks are not all SPI `SELECT FOR KEY SHARE` in this pinned tree.** Applicable nonpartitioned/non-temporal FKs use direct index-probe fast/batch paths; the SQL path is fallback.
8. **`pg_locks` is not a complete row-lock holder catalog.** logical row locks mostly live in tuple `xmax`/MultiXact.
9. **Ordinary commit/abort lifetime does not cover prepared transactions.** 2PC transfers locks instead of releasing them.

## 14. Unknowns and bounded limitations

1. **Concurrent uncommitted parent insert during FK child insert:** this packet traced the pinned RI direct/fallback lock paths and the conflict completion protocol after a referenced tuple is found. It did not establish one universal outcome for every isolation level when the parent insert is not visible to the FK check snapshot. Do not claim a wait/error outcome without a dedicated source trace or runtime test.
2. **Partitioned COPY:** root relation lock is established, and executor partition routing may acquire locks on leaf targets. The exact all-partition lock set/interleaving was not promoted to a central Claim here.
3. **FDW/trigger/extension behavior:** callbacks can add mechanisms outside native core COPY. Negative worker/transaction searches do not cover arbitrary extension code.
4. **Non-B-tree unique/exclusion/deferrable constraints:** exact wait/recheck protocol can differ. `PG-C004` is deliberately B-tree immediate-unique.
5. **Performance:** no runtime experiment was permitted. This packet makes no throughput, wait-time, or contention-number claim.
6. **Cross-database equivalence:** final `analogy` Claims require pinned CUBRID, PostgreSQL, and MySQL refs. This packet supplies only the PostgreSQL premises and a semantic verdict for integration.

## 15. Hand-off summary for the Korean Book

The teaching story can be reduced to two separate pictures.

```text
Table coordination

PostgreSQL COPY transaction
  owns RowExclusiveLock(table)
  performs all row inserts
  releases at transaction end

=> CUBRID BU_LOCK과 일부만 비슷함
=> session owner / worker batch owner split은 PG core COPY에 없음
```

```text
Uncommitted creator rendezvous

creator transaction
  owns ExclusiveLock(XID)
  writes XID into tuple xmin/xmax context

observer transaction
  requests ShareLock(XID)
  waits for creator completion
  releases ShareLock
  rechecks tuple/index state

=> CUBRID MVCCID X/S self-lock과 중심 불변식은 같음
=> VirtualXID, speculative token, FK tuple KeyShare는 별도 개념
```

CBRD-27157 설명에서 PostgreSQL을 가져올 때 가장 안전한 문장은 다음이다.

> PostgreSQL도 “아직 끝나지 않은 tuple creator를 transaction identity lock으로 기다린 뒤 재검사”한다. 그러나 `COPY FROM`의 table lock은 CUBRID `BU_LOCK`과 같은 전용 bulk mode가 아니며, CUBRID server-side loaddb의 session/worker transaction ownership 분리도 PostgreSQL core COPY에는 없다.
