# PostgreSQL comparator research packet

## 연구 고정 정보

- role: Role 2 — PostgreSQL comparator
- topic: CUBRID lock과 lock manager, 특히 self lock 및 MVCC lock의 필요성
- shared scenario: account(id PRIMARY KEY, balance)에서 T1이 기존 행을 UPDATE하고 새 unique key를 INSERT하는 동안 T2가 plain SELECT, SELECT FOR UPDATE, UPDATE, duplicate INSERT를 수행
- scope file: /home/vimkim/gh/my-cubrid-docs/code-analysis/lock-lock-manager-self-lock-mvcc-lock/f30f1c2_codex/research/scope.md
- scope sha256: 711d1a0f5bfebdbe1b55b4299973efc353d90636e2f00fc807f51d031766a839
- PostgreSQL root: /home/vimkim/gh/pg/postgres
- revision: fd2b89854d93d70fe8c9a69d5b8fafd5b9302cfc
- branch: master
- upstream remote: https://github.com/postgres/postgres
- origin remote: https://github.com/vimkim/postgres
- dirty label: source commit-clean; worktree has only untracked .omc/
- git status --porcelain=v1 -z sha256: 6598423bde21de7dd278c14928d14401e35de856b4b2502edbea6b50c4f579c1
- worktree diff sha256: e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855
- index diff sha256: e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855
- evidence state: 모든 인용 파일은 pinned revision의 COMMIT 바이트와 일치
- collected_at_utc: 2026-08-11T08:45:19Z
- method: pinned source의 함수 본문과 도달 가능한 호출 경로만 조사. PostgreSQL 서버 runtime은 실행하지 않음.

## 먼저 읽을 결론

PostgreSQL에서 CUBRID의 MVCCID self-lock과 가장 가까운 것은 하나가 아니라 세 갈래다.

1. LOCKTAG_TRANSACTION: XID를 부여받은 트랜잭션이 ExclusiveLock을 잡고, 튜플의 XMAX 또는 unique 검사에서 그 XID를 본 상대가 ShareLock으로 트랜잭션 종료를 기다린다.
2. LOCKTAG_VIRTUALTRANSACTION: 모든 top-level transaction이 자신의 VXID를 먼저 잠근 뒤 ProcArray에 공개하고, 일부 시스템 작업이 ShareLock으로 종료를 기다린다.
3. LOCKTAG_SPECULATIVE_TOKEN: ON CONFLICT의 한 speculative insertion 판정만 XID+token 자원에 Exclusive/Share rendezvous를 만들고, 판정 상태를 먼저 확정한 뒤 release/wakeup/recheck한다.

그러나 일반 행 lock의 소유권은 transaction-tag lock이 아니라 튜플 헤더 XMAX/MultiXact에 남는다. heavyweight tuple lock은 기다릴 때 공정한 순서를 제공하는 짧은 중재 락이다. 따라서 “MVCC 행마다 heavyweight X lock을 유지하지 않고 트랜잭션 ID 하나에서 완료를 기다린다”는 축은 부분 유사성이 있지만, CUBRID의 특정 appended-row 최적화와 동일한 단일 self-lock 프로토콜이라고 부르면 안 된다.

## 동작별 호출 경로

### 1. 자원, 모드, relation/tuple 관계

일반 SELECT:

    addRangeTableEntry
      -> parserOpenTable(AccessShareLock)
      -> relation LOCKTAG(DB OID, rel OID)
      -> LockAcquireExtended
      -> transaction end까지 유지

SELECT FOR UPDATE/SHARE:

    addRangeTableEntry
      -> parserOpenTable(RowShareLock)
      -> ExecLockRows
      -> table_tuple_lock
      -> heap_lock_tuple

INSERT/UPDATE/DELETE target:

    setTargetTable
      -> parserOpenTable(RowExclusiveLock)
      -> transaction end까지 유지

PostgreSQL의 relation lock과 tuple lock은 동일 conflict table을 사용하는 별도 LOCKTAG 요청이다. tuple tag 안에 relation OID가 포함되지만 lock manager가 부모 relation을 따라 intent mode를 획득하거나 행 lock 수를 relation lock으로 자동 escalation하는 경로는 normal heavyweight/tuple protocol에서 확인되지 않았다. 단, Serializable의 SIREAD predicate lock subsystem은 별도 구조에서 tuple/page/table promotion을 하므로 “PostgreSQL 전체에 escalation이 없다”는 결론은 틀리다.

### 2. acquire, wait, deadlock, timeout, release

    LockAcquireExtended
      -> LOCALLOCK 재획득이면 local refcount만 증가
      -> 약한 relation lock이면 per-backend fast path 시도
      -> 아니면 SetupLockInTable(LOCK + PROCLOCK)
      -> waitMask와 granted conflict 검사
      -> GrantLock 또는 JoinWaitQueue
      -> WaitOnLock
      -> ProcSleep
          -> deadlock_timeout timer
          -> 선택적 lock_timeout timer
          -> CheckDeadLock
              -> DeadLockCheck
                  -> hard edge: conflicting holder
                  -> soft edge: 선행 conflicting waiter
                  -> 가능한 경우 queue reorder
                  -> 불가능하면 DeadLockReport ERROR

release:

    LockRelease / LockReleaseAll
      -> UnGrantLock
      -> CleanUpLock
      -> ProcLockWakeup
          -> GrantLock
          -> ProcWakeup
          -> SetLatch

grant 상태를 공유 lock table에 먼저 기록하고 waiter를 깨우기 때문에, 새 요청자가 깨어난 waiter를 추월하는 race를 피한다. top-level commit/abort에서는 transaction outcome과 ProcArray 종료 상태를 먼저 공개하고 그 뒤 ResourceOwner의 lock phase에서 LockReleaseAll을 호출한다.

### 3. MVCC snapshot read와 tuple lock/update conflict

plain SELECT:

    SeqNext
      -> table_beginscan(es_snapshot)
      -> table_scan_getnextslot
      -> heapgettup
      -> HeapTupleSatisfiesVisibility
      -> HeapTupleSatisfiesMVCC

T1이 old tuple의 XMAX로 in-progress update를 표시해도 T2의 MVCC snapshot에 그 XID가 포함되면 old version은 visible이다. 이 경로에는 XactLockTableWait가 없다. 다만 relation AccessShareLock과 buffer content lock은 존재하므로 “SELECT는 어떤 lock도 잡지 않는다”는 표현도 틀리다. Serializable에서는 SSI conflict tracking도 별도다.

SELECT FOR UPDATE:

    ExecLockRows
      -> 먼저 snapshot subplan에서 후보 획득
      -> table_tuple_lock(mode, waitPolicy)
      -> heap_lock_tuple
          -> HeapTupleSatisfiesUpdate
          -> 필요 시 transient heavyweight tuple lock으로 우선순위 확보
          -> XactLockTableWait(XMAX) 또는 MultiXactIdWait
          -> buffer 재획득
          -> XMAX/infomask가 바뀌었는지 재검사
          -> 자신의 XID/MultiXact를 tuple XMAX에 기록
          -> transient heavyweight tuple lock release
      -> update chain을 따라갔다면 EvalPlanQual 재평가

UPDATE:

    setTargetTable(RowExclusiveLock)
      -> ExecUpdateAct
      -> table_tuple_update(wait=true)
      -> heap_update
          -> key column 변경 여부로 Exclusive/NoKeyExclusive 선택
          -> HeapTupleSatisfiesUpdate
          -> conflicting XMAX이면 tuple 우선순위 lock
          -> XactLockTableWait 또는 MultiXactIdWait
          -> buffer 재획득 및 XMAX/status 재검사
          -> old tuple에 updater XMAX/ctid, 새 MVCC version 삽입
      -> TM_Updated이면
          -> Read Committed: latest version lock + EvalPlanQual + retry
          -> transaction snapshot isolation: serialization failure

foreign key:

    RI_FKey_check
      -> PK relation RowShareLock
      -> SELECT ... FOR KEY SHARE 또는 direct index probe
      -> table_tuple_lock(LockTupleKeyShare)
      -> concurrent key-changing update/delete와 충돌

snapshot visibility만으로는 참조한 PK가 바로 삭제/키 변경되는 것을 막지 못하므로 FK 검사는 row KeyShare lock을 사용한다.

duplicate unique INSERT:

    ExecInsertIndexTuples
      -> btree _bt_doinsert
      -> leaf page write lock 아래 _bt_check_unique(SnapshotDirty)
      -> in-progress equal key의 xmin/xmax 추출
      -> leaf buffer release
      -> ordinary insertion: XactLockTableWait(xwait)
         speculative insertion: SpeculativeInsertionWait(xwait, token)
      -> root search부터 재시작
      -> commit이면 unique violation, abort면 insert 진행

일반 duplicate INSERT는 상대 행의 tuple lock을 기다리는 것이 아니라 index가 찾아낸 in-progress inserting transaction의 XID 완료를 기다린다.

### 4. CUBRID MVCCID self-lock의 가장 가까운 rendezvous

ordinary XID lifecycle:

    GetCurrentTransactionId
      -> AssignTransactionId
      -> GetNewTransactionId (PGPROC/pg_subtrans에 running XID 공개)
      -> XactLockTableInsert(XID, ExclusiveLock)
      -> 이후 heap/index tuple에 XID 기록

    observer가 tuple XMAX 또는 DirtySnapshot xmin/xmax를 읽음
      -> XactLockTableWait(XID)
      -> LOCKTAG_TRANSACTION(XID)에 ShareLock acquire
      -> owner transaction end까지 block
      -> ShareLock을 즉시 release
      -> TransactionIdIsInProgress 재검사
      -> subxid가 끝났지만 top transaction이 running이면 topmost XID로 반복
      -> caller가 tuple/header/index condition을 다시 검사

end ordering:

    commit/abort outcome 기록
      -> ProcArrayEndTransaction
      -> invalidation 및 visible-resource cleanup
      -> ResourceOwnerRelease(...LOCKS...)
      -> LockReleaseAll
      -> XID ExclusiveLock release
      -> waiter grant/wakeup

이 구조는 한 writer transaction이 많은 tuple에 자신의 XID를 남겨도 waiter들이 XID lock 하나를 completion rendezvous로 재사용한다. 하지만 row lock compatibility와 소유권 자체는 XMAX/MultiXact가 담당하며, waiting fairness를 위해 transient heavyweight tuple lock도 여전히 쓴다.

VXID lifecycle:

    StartTransaction
      -> VirtualXactLockTableInsert(VXID) fast-path owner lock
      -> 그 뒤 ProcArray에 VXID advertise

    VirtualXactLock(wait=true)
      -> owner fast-path lock을 main table ExclusiveLock으로 materialize
      -> ShareLock으로 VXID 종료 대기
      -> 필요하면 연결된 real XID 완료도 확인

VXID는 publish-before/after ordering과 “own virtual transaction ID lock”이라는 모양이 더 직접적으로 닮았지만, shared account의 tuple update, FK, unique conflict가 기다리는 자원은 VXID가 아니다.

speculative insertion lifecycle:

    SpeculativeInsertionLockAcquire(XID)
      -> token 생성
      -> LOCKTAG_SPECULATIVE_TOKEN(XID, token) ExclusiveLock
      -> speculative heap tuple와 index entries 생성
      -> tuple을 confirmed 또는 dead로 먼저 확정
      -> SpeculativeInsertionLockRelease
      -> waiter ShareLock grant/wakeup
      -> waiter가 tuple/index를 재검사

이는 “판정 상태를 먼저 게시한 후 unlock, wakeup, recheck” 순서의 가장 가까운 모양이지만 ON CONFLICT 한 건의 tentative decision에 한정된다.

## Claim candidates

아래 33개 항목은 parent가 claims.jsonl로 옮길 수 있도록 claim schema의 핵심 필드를 유지한다. 공통 database는 postgresql, revision은 fd2b89854d93d70fe8c9a69d5b8fafd5b9302cfc, kind는 source, confidence는 SOURCE-CONFIRMED, runtime_run_ids는 빈 배열이다.

### Behavior 1 — resource, mode, relation/tuple organization

#### PG-C001

- claim_ko: LOCKTAG는 lockable object의 고유 hash key이며 relation, page, physical tuple, transaction XID, virtual transaction, speculative insertion token을 서로 다른 자원 종류로 구분한다.
- source_refs:
  - path: src/include/storage/locktag.h; symbol: LockTagType; lines: 29-50; file_sha256: 0ffaea18914516886ea4892c642f2274acb65e32b51c9ceca92e1cef1c9c5a81; evidence_state: COMMIT
- limitations_ko: predicate lock과 LWLock은 이 LOCKTAG 목록의 normal heavyweight lock과 다른 subsystem이다.

#### PG-C002

- claim_ko: relation tag는 database OID와 relation OID, tuple tag는 여기에 block/offset, transaction tag는 XID, VXID tag는 proc number/local transaction id, speculative tag는 XID/token으로 식별된다.
- source_refs:
  - path: src/include/storage/locktag.h; symbol: SET_LOCKTAG_RELATION; lines: 80-87; file_sha256: 0ffaea18914516886ea4892c642f2274acb65e32b51c9ceca92e1cef1c9c5a81; evidence_state: COMMIT
  - path: src/include/storage/locktag.h; symbol: SET_LOCKTAG_TUPLE; lines: 116-123; file_sha256: 0ffaea18914516886ea4892c642f2274acb65e32b51c9ceca92e1cef1c9c5a81; evidence_state: COMMIT
  - path: src/include/storage/locktag.h; symbol: SET_LOCKTAG_TRANSACTION; lines: 125-132; file_sha256: 0ffaea18914516886ea4892c642f2274acb65e32b51c9ceca92e1cef1c9c5a81; evidence_state: COMMIT
  - path: src/include/storage/locktag.h; symbol: SET_LOCKTAG_VIRTUALTRANSACTION; lines: 134-141; file_sha256: 0ffaea18914516886ea4892c642f2274acb65e32b51c9ceca92e1cef1c9c5a81; evidence_state: COMMIT
  - path: src/include/storage/locktag.h; symbol: SET_LOCKTAG_SPECULATIVE_INSERTION; lines: 143-153; file_sha256: 0ffaea18914516886ea4892c642f2274acb65e32b51c9ceca92e1cef1c9c5a81; evidence_state: COMMIT
- limitations_ko: tuple tag에 relation 식별자가 들어간다는 사실은 automatic parent intent locking을 뜻하지 않는다.

#### PG-C003

- claim_ko: standard lock mode는 AccessShare부터 AccessExclusive까지 8단계이고, conflict table bitmask가 요청 모드와 이미 grant된 모드의 충돌을 결정한다.
- source_refs:
  - path: src/include/storage/lockdefs.h; symbol: AccessShareLock; lines: 20-48; file_sha256: 7db1a4531f5da94667f2ca498136e6796d89a8ba56115fd90bef198e09a2af68; evidence_state: COMMIT
  - path: src/backend/storage/lmgr/lock.c; symbol: LockConflicts; lines: 63-108; file_sha256: bad8fb3ce27d2a4bda77c4e030202eb6395665096bb0d6bacced8f5f77d75eb5; evidence_state: COMMIT
- limitations_ko: tuple header의 네 LockTupleMode와 heavyweight LOCKMODE는 별도 추상화이며 내부 표로 대응된다.

#### PG-C004

- claim_ko: shared LOCK은 자원별 grant/wait 상태와 queue를, PROCLOCK은 자원/요청 backend별 hold 상태를, backend-private LOCALLOCK은 mode별 재획득 횟수와 ResourceOwner를 추적하며 같은 backend의 lock은 서로 block하지 않는다.
- source_refs:
  - path: src/include/storage/lock.h; symbol: LOCK; lines: 121-153; file_sha256: 9e997e40e45889d6d1b9040440303d244df566546b48e7e6b9d12f99d3767e16; evidence_state: COMMIT
  - path: src/include/storage/lock.h; symbol: PROCLOCK; lines: 159-211; file_sha256: 9e997e40e45889d6d1b9040440303d244df566546b48e7e6b9d12f99d3767e16; evidence_state: COMMIT
  - path: src/include/storage/lock.h; symbol: LOCALLOCK; lines: 217-272; file_sha256: 9e997e40e45889d6d1b9040440303d244df566546b48e7e6b9d12f99d3767e16; evidence_state: COMMIT
- limitations_ko: parallel query lock group은 여러 backend를 같은 owner group처럼 취급하는 추가 규칙이 있다.

#### PG-C005

- claim_ko: 일반 source relation은 AccessShareLock으로 열리고 relation refcount를 닫아도 lock은 transaction end까지 유지되어 DROP이나 schema 변경을 막는다.
- source_refs:
  - path: src/backend/parser/parse_relation.c; symbol: addRangeTableEntry; lines: 1510-1546; file_sha256: c96240f99aa48499e01a673762f668fb133b6c9352850fba792da5378e48b400; evidence_state: COMMIT
  - path: src/backend/parser/parse_relation.c; symbol: table_close; lines: 1581-1586; file_sha256: c96240f99aa48499e01a673762f668fb133b6c9352850fba792da5378e48b400; evidence_state: COMMIT
- limitations_ko: 이 lock은 row version visibility를 직렬화하는 lock이 아니다.

#### PG-C006

- claim_ko: FOR UPDATE/SHARE source relation은 RowShareLock을 사용하며, 실제 행 강도는 별도의 LockTupleMode로 선택된다.
- source_refs:
  - path: src/backend/parser/parse_relation.c; symbol: RowShareLock; lines: 1529-1546; file_sha256: c96240f99aa48499e01a673762f668fb133b6c9352850fba792da5378e48b400; evidence_state: COMMIT
  - path: src/include/nodes/lockoptions.h; symbol: LockTupleMode; lines: 47-60; file_sha256: 3cfd2f4f76f716cfd57de8c4b40a90f7061bc4215df5df93618201fd5ad43535; evidence_state: COMMIT
- limitations_ko: RowShareLock 이름은 행마다 shared lock을 뜻하지 않고 relation-level DDL coordination mode다.

#### PG-C007

- claim_ko: INSERT/UPDATE/DELETE/MERGE target relation은 source를 처리하기 전에 RowExclusiveLock으로 열리고 그 lock은 transaction end까지 유지된다.
- source_refs:
  - path: src/backend/parser/parse_clause.c; symbol: setTargetTable; lines: 157-217; file_sha256: c7a514d028a3529b4efbc6b53cfbdb07307c4b6bcbaa0e19c43b6a724edfeb70; evidence_state: COMMIT
- limitations_ko: RowExclusiveLock끼리는 충돌하지 않으므로 같은 table의 서로 다른 행 DML을 직렬화하지 않는다.

#### PG-C008

- claim_ko: normal heap row locking은 tuple header XMAX/MultiXact와 짧은 heavyweight tuple tag의 두 단계 protocol이며, 조사한 normal heavyweight/tuple 경로에는 relation parent intent mode 획득이나 row-count 기반 automatic escalation이 없다.
- source_refs:
  - path: src/backend/access/heap/README.tuplock; symbol: Locking tuples; lines: 1-37; file_sha256: 86be226a5db54ac65b29e1f28adabda875fbf1f41bf718d252c1cf872f4fa5a2; evidence_state: COMMIT
  - path: src/backend/storage/lmgr/lmgr.c; symbol: LockTuple; lines: 554-573; file_sha256: 7301f269a04cb423ff830d5490300185cf7b36c675b515638cda235125688eaf; evidence_state: COMMIT
  - path: src/backend/storage/lmgr/README-SSI; symbol: Predicate Locking; lines: 253-291; file_sha256: ea153efc28939c1309e2495599f427121a579c165702e80cbc64e2ccf7cecc7f; evidence_state: COMMIT
- limitations_ko: negative 결론은 normal heavyweight relation/tuple protocol로 한정한다. SIREAD predicate locks는 별도 subsystem에서 tuple/page/table promotion을 수행한다.

### Behavior 2 — acquisition, wait, deadlock, timeout, release

#### PG-C009

- claim_ko: LockAcquireExtended는 이미 가진 lock이면 LOCALLOCK count만 늘리고, eligible weak relation lock은 per-backend fast path를 시도하며, 그 밖에는 partitioned shared LOCK/PROCLOCK table을 사용한다.
- source_refs:
  - path: src/backend/storage/lmgr/lock.c; symbol: LockAcquireExtended; lines: 833-944; file_sha256: bad8fb3ce27d2a4bda77c4e030202eb6395665096bb0d6bacced8f5f77d75eb5; evidence_state: COMMIT
  - path: src/backend/storage/lmgr/lock.c; symbol: EligibleForRelationFastPath; lines: 974-1055; file_sha256: bad8fb3ce27d2a4bda77c4e030202eb6395665096bb0d6bacced8f5f77d75eb5; evidence_state: COMMIT
  - path: src/backend/storage/lmgr/lock.c; symbol: SetupLockInTable; lines: 1057-1095; file_sha256: bad8fb3ce27d2a4bda77c4e030202eb6395665096bb0d6bacced8f5f77d75eb5; evidence_state: COMMIT
- limitations_ko: fast path는 relation의 AccessShare/RowShare/RowExclusive와 VXID의 특수 경로에 한정된다.

#### PG-C010

- claim_ko: lock acquisition은 선행 waiter의 conflicting request까지 고려해 즉시 grant 또는 priority wait queue 진입을 결정하며, 자신과 같은 lock group의 보유 lock은 conflict에서 제외한다.
- source_refs:
  - path: src/backend/storage/lmgr/lock.c; symbol: LockCheckConflicts; lines: 1097-1122; file_sha256: bad8fb3ce27d2a4bda77c4e030202eb6395665096bb0d6bacced8f5f77d75eb5; evidence_state: COMMIT
  - path: src/backend/storage/lmgr/lock.c; symbol: LockCheckConflicts; lines: 1522-1652; file_sha256: bad8fb3ce27d2a4bda77c4e030202eb6395665096bb0d6bacced8f5f77d75eb5; evidence_state: COMMIT
  - path: src/backend/storage/lmgr/proc.c; symbol: JoinWaitQueue; lines: 1182-1362; file_sha256: 67031da14df638c9df197a8e77649421836ba5ad4eb6097d01b3661d1f69b9a4; evidence_state: COMMIT
- limitations_ko: strict FIFO가 아니라 already-held lock과 queue conflict를 고려한 priority/fairness 규칙이다.

#### PG-C011

- claim_ko: ProcSleep는 기본적으로 deadlock_timeout 뒤 deadlock 검사를 예약하고, lock_timeout이 0보다 크면 별도 lock wait timeout도 함께 예약하며 latch wait 중 cancel/die interrupt를 처리한다.
- source_refs:
  - path: src/backend/storage/lmgr/proc.c; symbol: ProcSleep; lines: 1364-1455; file_sha256: 67031da14df638c9df197a8e77649421836ba5ad4eb6097d01b3661d1f69b9a4; evidence_state: COMMIT
  - path: src/backend/storage/lmgr/proc.c; symbol: WaitLatch; lines: 1466-1534; file_sha256: 67031da14df638c9df197a8e77649421836ba5ad4eb6097d01b3661d1f69b9a4; evidence_state: COMMIT
  - path: src/backend/utils/misc/guc_parameters.dat; symbol: deadlock_timeout; lines: 626-634; file_sha256: e308005cebdcbe545fe9fe8635bfcf071dcc5cbb741b599b50cb3ab72ba94a67; evidence_state: COMMIT
  - path: src/backend/utils/misc/guc_parameters.dat; symbol: lock_timeout; lines: 1616-1624; file_sha256: e308005cebdcbe545fe9fe8635bfcf071dcc5cbb741b599b50cb3ab72ba94a67; evidence_state: COMMIT
- limitations_ko: 실제 OS scheduling과 관측 wait duration은 runtime으로 검증하지 않았다.

#### PG-C012

- claim_ko: delayed deadlock 검사기는 waits-for graph의 conflicting holder hard edge와 queue-order soft edge를 추적하고, soft cycle은 queue reorder로 풀며 불가능한 hard cycle은 현재 transaction을 ERROR로 abort시킨다.
- source_refs:
  - path: src/backend/storage/lmgr/proc.c; symbol: CheckDeadLock; lines: 1878-1970; file_sha256: 67031da14df638c9df197a8e77649421836ba5ad4eb6097d01b3661d1f69b9a4; evidence_state: COMMIT
  - path: src/backend/storage/lmgr/deadlock.c; symbol: DeadLockCheck; lines: 205-282; file_sha256: 38a45a2ca98090b3bbdb1ab472f723c5f094323b8c95a9339e371a77e30a7fd6; evidence_state: COMMIT
  - path: src/backend/storage/lmgr/deadlock.c; symbol: FindLockCycle; lines: 428-610; file_sha256: 38a45a2ca98090b3bbdb1ab472f723c5f094323b8c95a9339e371a77e30a7fd6; evidence_state: COMMIT
  - path: src/backend/storage/lmgr/deadlock.c; symbol: DeadLockReport; lines: 1071-1139; file_sha256: 38a45a2ca98090b3bbdb1ab472f723c5f094323b8c95a9339e371a77e30a7fd6; evidence_state: COMMIT
- limitations_ko: predicate-lock serialization failures와 buffer-pin deadlock의 전체 정책은 이 claim의 중심 범위가 아니다.

#### PG-C013

- claim_ko: release path는 partition lock을 잡은 채 waiter의 lock을 먼저 GrantLock으로 공유 상태에 반영한 뒤 SetLatch로 깨워 새 요청자와의 추월 race를 방지한다.
- source_refs:
  - path: src/backend/storage/lmgr/lock.c; symbol: LockRelease; lines: 2098-2108; file_sha256: bad8fb3ce27d2a4bda77c4e030202eb6395665096bb0d6bacced8f5f77d75eb5; evidence_state: COMMIT
  - path: src/backend/storage/lmgr/lock.c; symbol: CleanUpLock; lines: 1735-1790; file_sha256: bad8fb3ce27d2a4bda77c4e030202eb6395665096bb0d6bacced8f5f77d75eb5; evidence_state: COMMIT
  - path: src/backend/storage/lmgr/proc.c; symbol: ProcLockWakeup; lines: 1832-1876; file_sha256: 67031da14df638c9df197a8e77649421836ba5ad4eb6097d01b3661d1f69b9a4; evidence_state: COMMIT
- limitations_ko: 깨어난 caller가 상위 tuple/index 조건을 다시 검사해야 하는지는 각 AM protocol이 별도로 정한다.

#### PG-C014

- claim_ko: operational surface는 max_locks_per_transaction으로 shared table 용량을 산정하고, pg_locks/pg_lock_status로 heavyweight lock을, pg_blocking_pids로 conflicting holder와 선행 waiter를 노출하며 long wait/failure logging을 설정할 수 있다.
- source_refs:
  - path: src/backend/utils/misc/guc_parameters.dat; symbol: max_locks_per_transaction; lines: 2029-2037; file_sha256: e308005cebdcbe545fe9fe8635bfcf071dcc5cbb741b599b50cb3ab72ba94a67; evidence_state: COMMIT
  - path: src/backend/utils/misc/guc_parameters.dat; symbol: log_lock_waits; lines: 1745-1755; file_sha256: e308005cebdcbe545fe9fe8635bfcf071dcc5cbb741b599b50cb3ab72ba94a67; evidence_state: COMMIT
  - path: src/backend/catalog/system_views.sql; symbol: pg_locks; lines: 439-440; file_sha256: 6203864baafee05bda77106d6e1bafd48a6ec902f3361b0f4ecda3b9bc2cc9e2; evidence_state: COMMIT
  - path: src/backend/utils/adt/lockfuncs.c; symbol: pg_lock_status; lines: 93-162; file_sha256: 25318bcb3c2822e5d4f2268f62684d28b70fce21c968684bc85be0eef3b9a613; evidence_state: COMMIT
  - path: src/backend/utils/adt/lockfuncs.c; symbol: pg_blocking_pids; lines: 448-562; file_sha256: 25318bcb3c2822e5d4f2268f62684d28b70fce21c968684bc85be0eef3b9a613; evidence_state: COMMIT
- limitations_ko: tuple header XMAX/MultiXact lock은 항상 별도 heavyweight tuple row로 나타나지 않는다. transient arbitration tuple tag나 XID wait만 보일 수 있다.

#### PG-C015

- claim_ko: top-level commit/abort는 transaction status와 ProcArray의 종료를 먼저 공개한 다음 ResourceOwner lock phase에서 non-session locks를 release하여 waiter가 깨어날 때 종료 상태를 볼 수 있게 한다.
- source_refs:
  - path: src/backend/access/transam/xact.c; symbol: ProcArrayEndTransaction; lines: 2424-2484; file_sha256: b40898eda7d02c7cf4b7671ab3bf1b3d0ea757cf33765f98fe074d98e8382df2; evidence_state: COMMIT
  - path: src/backend/access/transam/xact.c; symbol: ProcArrayEndTransaction; lines: 2997-3032; file_sha256: b40898eda7d02c7cf4b7671ab3bf1b3d0ea757cf33765f98fe074d98e8382df2; evidence_state: COMMIT
  - path: src/backend/utils/resowner/resowner.c; symbol: ProcReleaseLocks; lines: 753-799; file_sha256: 0fd0f9cac6abe6817a6cca5ef3755d9916d9571e5b1c381cb5306e4fb484be27; evidence_state: COMMIT
  - path: src/backend/storage/lmgr/proc.c; symbol: ProcReleaseLocks; lines: 889-916; file_sha256: 67031da14df638c9df197a8e77649421836ba5ad4eb6097d01b3661d1f69b9a4; evidence_state: COMMIT
- limitations_ko: prepared transaction과 standby recovery는 별도 lifecycle을 가진다.

#### PG-C016

- claim_ko: ordinary LOCK/PROCLOCK table은 shared memory의 실행 중 상태지만 tuple XMAX/MultiXact는 WAL/pg_multixact로 crash 후 판정 가능해야 하고, PREPARE TRANSACTION의 qualifying locks는 2PC record로 저장되어 startup에서 재획득되며 VXID lock은 그 대상에서 제외된다.
- source_refs:
  - path: src/backend/storage/lmgr/lock.c; symbol: LockManagerShmemRequest; lines: 444-490; file_sha256: bad8fb3ce27d2a4bda77c4e030202eb6395665096bb0d6bacced8f5f77d75eb5; evidence_state: COMMIT
  - path: src/backend/access/heap/heapam.c; symbol: XLogInsert; lines: 5367-5405; file_sha256: 9be2f576df608c95992b65b2009640c3da5a9238aba73cf2cf106af124f77878; evidence_state: COMMIT
  - path: src/backend/access/heap/README.tuplock; symbol: MultiXacts; lines: 76-113; file_sha256: 86be226a5db54ac65b29e1f28adabda875fbf1f41bf718d252c1cf872f4fa5a2; evidence_state: COMMIT
  - path: src/backend/storage/lmgr/lock.c; symbol: AtPrepare_Locks; lines: 3470-3561; file_sha256: bad8fb3ce27d2a4bda77c4e030202eb6395665096bb0d6bacced8f5f77d75eb5; evidence_state: COMMIT
  - path: src/backend/storage/lmgr/lock.c; symbol: lock_twophase_recover; lines: 4307-4511; file_sha256: bad8fb3ce27d2a4bda77c4e030202eb6395665096bb0d6bacced8f5f77d75eb5; evidence_state: COMMIT
- limitations_ko: hot standby의 AccessExclusive replay와 전체 transaction-status storage recovery는 이 packet에서 완전 추적하지 않았다.

### Behavior 3 — MVCC snapshot read versus row/update conflict

#### PG-C017

- claim_ko: sequential plain SELECT는 executor snapshot으로 heap scan을 시작하고 각 tuple을 HeapTupleSatisfiesVisibility에 넘기며, source relation에는 별도로 AccessShareLock을 유지한다.
- source_refs:
  - path: src/backend/executor/nodeSeqscan.c; symbol: SeqNext; lines: 45-93; file_sha256: fe83e0d0a1cd1b161440b233cf5c85a81b5614ec8b214a7e8069d375a631416d; evidence_state: COMMIT
  - path: src/backend/access/heap/heapam.c; symbol: heapgettup; lines: 943-1058; file_sha256: 9be2f576df608c95992b65b2009640c3da5a9238aba73cf2cf106af124f77878; evidence_state: COMMIT
  - path: src/backend/parser/parse_relation.c; symbol: AccessShareLock; lines: 1529-1546; file_sha256: c96240f99aa48499e01a673762f668fb133b6c9352850fba792da5378e48b400; evidence_state: COMMIT
- limitations_ko: index scan도 같은 snapshot visibility 원칙을 쓰지만 이 claim의 구체 call path는 SeqScan으로 고정했다.

#### PG-C018

- claim_ko: SNAPSHOT_MVCC visibility는 inserting XID가 snapshot 안이면 새 tuple을 보이지 않게 하고, deleting/updating XMAX가 snapshot 안이면 old tuple을 visible로 반환하며 transaction lock wait를 수행하지 않는다.
- source_refs:
  - path: src/backend/access/heap/heapam_visibility.c; symbol: HeapTupleSatisfiesMVCC; lines: 916-1096; file_sha256: 8fdcbfec13791b43c74cbeab351162ea095c23b8d90cee5c86140bba8a8fbc6a; evidence_state: COMMIT
  - path: src/backend/access/heap/heapam_visibility.c; symbol: HeapTupleSatisfiesVisibility; lines: 1721-1752; file_sha256: 8fdcbfec13791b43c74cbeab351162ea095c23b8d90cee5c86140bba8a8fbc6a; evidence_state: COMMIT
- limitations_ko: SnapshotDirty, SnapshotSelf, Serializable SSI는 다른 목적의 visibility/conflict semantics다. SnapshotSelf라는 이름은 CUBRID self lock과 무관하다.

#### PG-C019

- claim_ko: row lock은 KeyShare, Share, NoKeyExclusive, Exclusive 네 강도와 Block, Skip, Error 세 wait policy를 가지며 각 mode는 tuple header lock semantics와 heavyweight arbitration mode를 함께 결정한다.
- source_refs:
  - path: src/include/nodes/lockoptions.h; symbol: LockWaitPolicy; lines: 31-45; file_sha256: 3cfd2f4f76f716cfd57de8c4b40a90f7061bc4215df5df93618201fd5ad43535; evidence_state: COMMIT
  - path: src/include/nodes/lockoptions.h; symbol: LockTupleMode; lines: 47-60; file_sha256: 3cfd2f4f76f716cfd57de8c4b40a90f7061bc4215df5df93618201fd5ad43535; evidence_state: COMMIT
  - path: src/backend/access/heap/heapam.c; symbol: tupleLockExtraInfo; lines: 117-175; file_sha256: 9be2f576df608c95992b65b2009640c3da5a9238aba73cf2cf106af124f77878; evidence_state: COMMIT
- limitations_ko: SQL clause 이름과 내부 heavyweight mode 이름을 직접 동일시하면 안 된다.

#### PG-C020

- claim_ko: ExecLockRows는 snapshot subplan의 후보마다 SQL rowmark를 LockTupleMode로 바꾸어 table_tuple_lock을 호출하고, SKIP/NOWAIT 결과와 concurrent update/delete를 처리한 뒤 update chain을 따라갔으면 EvalPlanQual로 predicate를 다시 평가한다.
- source_refs:
  - path: src/backend/executor/nodeLockRows.c; symbol: ExecLockRows; lines: 38-189; file_sha256: 06b3c78a370e2460e14fdc8fee2e7acfc551fa8cbad5dfd0cd3606dd38b3c5e3; evidence_state: COMMIT
  - path: src/backend/executor/nodeLockRows.c; symbol: EvalPlanQualNext; lines: 191-280; file_sha256: 06b3c78a370e2460e14fdc8fee2e7acfc551fa8cbad5dfd0cd3606dd38b3c5e3; evidence_state: COMMIT
- limitations_ko: FDW의 RefetchForeignRow 경로는 storage implementation에 위임되므로 heap과 동일하다고 단정할 수 없다.

#### PG-C021

- claim_ko: heap tuple lock의 장기 소유권/호환성은 tuple header의 XMAX와 필요 시 MultiXact에 기록되고, heavyweight tuple lock은 waiters의 starvation을 막는 순서 중재용으로 backend당 한 개만 잠시 보유/대기한다.
- source_refs:
  - path: src/backend/access/heap/README.tuplock; symbol: Locking tuples; lines: 1-37; file_sha256: 86be226a5db54ac65b29e1f28adabda875fbf1f41bf718d252c1cf872f4fa5a2; evidence_state: COMMIT
  - path: src/backend/storage/lmgr/lmgr.c; symbol: LockTuple; lines: 554-573; file_sha256: 7301f269a04cb423ff830d5490300185cf7b36c675b515638cda235125688eaf; evidence_state: COMMIT
- limitations_ko: “heavyweight tuple lock을 release했다”는 것이 SQL row lock을 풀었다는 뜻이 아니다.

#### PG-C022

- claim_ko: heap_lock_tuple은 conflicting XMAX를 본 뒤 buffer lock을 놓고 tuple priority lock과 XID/MultiXact completion wait를 수행하며, buffer를 다시 잡아 XMAX 변화와 outcome을 재검사한 후 자신의 XID/MultiXact를 XMAX에 기록하고 transient tuple lock을 푼다.
- source_refs:
  - path: src/backend/access/heap/heapam.c; symbol: heap_lock_tuple; lines: 4697-4732; file_sha256: 9be2f576df608c95992b65b2009640c3da5a9238aba73cf2cf106af124f77878; evidence_state: COMMIT
  - path: src/backend/access/heap/heapam.c; symbol: XactLockTableWait; lines: 5073-5233; file_sha256: 9be2f576df608c95992b65b2009640c3da5a9238aba73cf2cf106af124f77878; evidence_state: COMMIT
  - path: src/backend/access/heap/heapam.c; symbol: HeapTupleHeaderSetXmax; lines: 5297-5345; file_sha256: 9be2f576df608c95992b65b2009640c3da5a9238aba73cf2cf106af124f77878; evidence_state: COMMIT
  - path: src/backend/access/heap/heapam.c; symbol: UnlockTupleTuplock; lines: 5418-5438; file_sha256: 9be2f576df608c95992b65b2009640c3da5a9238aba73cf2cf106af124f77878; evidence_state: COMMIT
- limitations_ko: compatible lockers와 self-held lock upgrade에는 wait/priority lock을 생략하는 세부 분기가 있다.

#### PG-C023

- claim_ko: heap_update는 변경 column이 relation key attribute와 겹치지 않으면 LockTupleNoKeyExclusive, 겹치면 LockTupleExclusive를 선택하여 FK KeyShare와의 불필요한 충돌을 줄인다.
- source_refs:
  - path: src/backend/access/heap/heapam.c; symbol: heap_update; lines: 3340-3489; file_sha256: 9be2f576df608c95992b65b2009640c3da5a9238aba73cf2cf106af124f77878; evidence_state: COMMIT
- limitations_ko: “key attribute”는 primary key만이 아니라 relation이 계산한 index/referential key bitmap에 따른다.

#### PG-C024

- claim_ko: 같은 행을 UPDATE하는 transaction은 conflicting tuple XMAX/MultiXact를 만나면 buffer를 놓고 transient tuple lock으로 우선순위를 잡아 completion을 기다린 뒤 buffer를 재획득하여 XMAX와 commit/abort를 재검사한다.
- source_refs:
  - path: src/backend/access/heap/heapam.c; symbol: HeapTupleSatisfiesUpdate; lines: 3498-3557; file_sha256: 9be2f576df608c95992b65b2009640c3da5a9238aba73cf2cf106af124f77878; evidence_state: COMMIT
  - path: src/backend/access/heap/heapam.c; symbol: MultiXactIdWait; lines: 3558-3630; file_sha256: 9be2f576df608c95992b65b2009640c3da5a9238aba73cf2cf106af124f77878; evidence_state: COMMIT
  - path: src/backend/access/heap/heapam.c; symbol: XactLockTableWait; lines: 3652-3688; file_sha256: 9be2f576df608c95992b65b2009640c3da5a9238aba73cf2cf106af124f77878; evidence_state: COMMIT
- limitations_ko: compatible KeyShare locker와 key-preserving update는 blocker를 보존하면서 기다리지 않을 수 있다.

#### PG-C025

- claim_ko: concurrent update 결과가 TM_Updated이면 transaction-snapshot isolation은 serialization failure를 내고, Read Committed는 latest tuple version을 lock하고 EvalPlanQual로 조건을 재평가하여 새 tuple을 만들어 update를 retry한다.
- source_refs:
  - path: src/backend/executor/nodeModifyTable.c; symbol: table_tuple_lock; lines: 2894-2954; file_sha256: eee5c18399d1741f6518e5419b55aba3fa6e4cc8313ce8998891ca8147943a60; evidence_state: COMMIT
- limitations_ko: trigger, partition move, MERGE에는 추가 retry/side-effect 규칙이 있다.

#### PG-C026

- claim_ko: foreign-key 참조 검사는 PK relation을 RowShareLock으로 열고 matching PK tuple에 LockTupleKeyShare를 걸어 concurrent delete와 key-changing update를 막으며, Read Committed에서는 update chain을 따라가 key를 재검사한다.
- source_refs:
  - path: src/backend/utils/adt/ri_triggers.c; symbol: RowShareLock; lines: 459-508; file_sha256: 9aeecd49d4ce8bd9c1695fa733003793d6d0995818f3652e92801565c63c89d8; evidence_state: COMMIT
  - path: src/backend/utils/adt/ri_triggers.c; symbol: FOR KEY SHARE; lines: 523-580; file_sha256: 9aeecd49d4ce8bd9c1695fa733003793d6d0995818f3652e92801565c63c89d8; evidence_state: COMMIT
  - path: src/backend/utils/adt/ri_triggers.c; symbol: ri_LockPKTuple; lines: 3232-3344; file_sha256: 9aeecd49d4ce8bd9c1695fa733003793d6d0995818f3652e92801565c63c89d8; evidence_state: COMMIT
- limitations_ko: partitioned/temporal FK와 SPI fallback에는 더 넓은 plan/snapshot 규칙이 있다.

#### PG-C027

- claim_ko: normal unique btree insertion은 DirtySnapshot으로 equal key의 in-progress xmin/xmax를 찾으면 leaf write lock을 놓고 그 XID 완료를 기다린 뒤 search를 처음부터 반복하며, commit이면 unique violation이고 abort이면 insertion이 진행될 수 있다.
- source_refs:
  - path: src/backend/access/nbtree/nbtinsert.c; symbol: XactLockTableWait; lines: 163-235; file_sha256: 0ef3d779ec130b82bd2658c32d71085a629d218e91808e929ee0d0dc43baa617; evidence_state: COMMIT
  - path: src/backend/access/nbtree/nbtinsert.c; symbol: _bt_check_unique; lines: 388-433; file_sha256: 0ef3d779ec130b82bd2658c32d71085a629d218e91808e929ee0d0dc43baa617; evidence_state: COMMIT
  - path: src/backend/access/nbtree/nbtinsert.c; symbol: SnapshotDirty; lines: 557-600; file_sha256: 0ef3d779ec130b82bd2658c32d71085a629d218e91808e929ee0d0dc43baa617; evidence_state: COMMIT
  - path: src/backend/access/nbtree/nbtinsert.c; symbol: ERRCODE_UNIQUE_VIOLATION; lines: 603-678; file_sha256: 0ef3d779ec130b82bd2658c32d71085a629d218e91808e929ee0d0dc43baa617; evidence_state: COMMIT
- limitations_ko: partial unique check와 exclusion constraint는 wait policy가 다르며 ON CONFLICT speculative insert는 PG-C032의 token path를 쓴다.

### Behavior 4 — nearest rendezvous for CUBRID MVCCID self-lock

#### PG-C028

- claim_ko: PostgreSQL은 XID를 lazy하게 할당하고 AssignTransactionId가 XID를 만든 뒤 해당 transaction ResourceOwner 아래 LOCKTAG_TRANSACTION(XID)의 ExclusiveLock을 획득하여 running transaction completion lock을 세운다.
- source_refs:
  - path: src/backend/access/transam/xact.c; symbol: GetCurrentTransactionId; lines: 421-475; file_sha256: b40898eda7d02c7cf4b7671ab3bf1b3d0ea757cf33765f98fe074d98e8382df2; evidence_state: COMMIT
  - path: src/backend/access/transam/xact.c; symbol: AssignTransactionId; lines: 627-733; file_sha256: b40898eda7d02c7cf4b7671ab3bf1b3d0ea757cf33765f98fe074d98e8382df2; evidence_state: COMMIT
  - path: src/backend/storage/lmgr/lmgr.c; symbol: XactLockTableInsert; lines: 614-629; file_sha256: 7301f269a04cb423ff830d5490300185cf7b36c675b515638cda235125688eaf; evidence_state: COMMIT
- limitations_ko: XID는 read-only transaction에는 끝까지 할당되지 않을 수 있고 이 owner lock은 CUBRID 명칭의 self lock API가 아니다.

#### PG-C029

- claim_ko: XactLockTableWait는 XID tag에 ShareLock을 잡아 owner의 ExclusiveLock release까지 기다린 뒤 즉시 ShareLock을 풀고 running status를 재검사하며, subxid lock이 먼저 사라졌으면 topmost parent XID를 따라 반복한다.
- source_refs:
  - path: src/backend/storage/lmgr/lmgr.c; symbol: XactLockTableWait; lines: 648-730; file_sha256: 7301f269a04cb423ff830d5490300185cf7b36c675b515638cda235125688eaf; evidence_state: COMMIT
  - path: src/backend/access/transam/xact.c; symbol: CommitSubTransaction; lines: 5151-5236; file_sha256: b40898eda7d02c7cf4b7671ab3bf1b3d0ea757cf33765f98fe074d98e8382df2; evidence_state: COMMIT
  - path: src/backend/access/transam/xact.c; symbol: TransactionIdAbortTree; lines: 1885-1907; file_sha256: b40898eda7d02c7cf4b7671ab3bf1b3d0ea757cf33765f98fe074d98e8382df2; evidence_state: COMMIT
- limitations_ko: ProcArray consumer가 XID lock 등록보다 먼저 running XID를 볼 수 있는 창을 함수가 1ms retry로 처리한다. tuple에 XID를 기록하는 writer path는 AssignTransactionId의 lock 등록 이후 진행한다.

#### PG-C030

- claim_ko: shared account의 row lock/update와 ordinary unique conflict에서 transaction-tag lock은 tuple XMAX 또는 DirtySnapshot이 지목한 writer XID의 완료를 기다리는 공통 rendezvous이고, 실제 tuple/index 조건은 wakeup 뒤 caller가 다시 검사한다.
- source_refs:
  - path: src/backend/access/heap/heapam.c; symbol: XactLockTableWait; lines: 5073-5233; file_sha256: 9be2f576df608c95992b65b2009640c3da5a9238aba73cf2cf106af124f77878; evidence_state: COMMIT
  - path: src/backend/access/heap/heapam.c; symbol: XactLockTableWait; lines: 3652-3680; file_sha256: 9be2f576df608c95992b65b2009640c3da5a9238aba73cf2cf106af124f77878; evidence_state: COMMIT
  - path: src/backend/access/nbtree/nbtinsert.c; symbol: XactLockTableWait; lines: 201-235; file_sha256: 0ef3d779ec130b82bd2658c32d71085a629d218e91808e929ee0d0dc43baa617; evidence_state: COMMIT
- limitations_ko: 이 lock은 row lock mode/holder list를 대체하지 않는다. row compatibility는 XMAX/MultiXact이고 tuple fairness는 transient heavyweight tuple lock이다.

#### PG-C031

- claim_ko: every top-level transaction의 VXID owner lock은 ProcArray advertise 전에 fast path로 세워지고, waiter는 필요할 때 owner ExclusiveLock을 main table에 materialize한 뒤 ShareLock으로 종료를 기다리지만 이 경로는 ordinary tuple/unique conflict의 wait target이 아니다.
- source_refs:
  - path: src/backend/access/transam/xact.c; symbol: VirtualXactLockTableInsert; lines: 2199-2219; file_sha256: b40898eda7d02c7cf4b7671ab3bf1b3d0ea757cf33765f98fe074d98e8382df2; evidence_state: COMMIT
  - path: src/backend/storage/lmgr/lock.c; symbol: VirtualXactLockTableInsert; lines: 4582-4614; file_sha256: bad8fb3ce27d2a4bda77c4e030202eb6395665096bb0d6bacced8f5f77d75eb5; evidence_state: COMMIT
  - path: src/backend/storage/lmgr/lock.c; symbol: VirtualXactLock; lines: 4713-4825; file_sha256: bad8fb3ce27d2a4bda77c4e030202eb6395665096bb0d6bacced8f5f77d75eb5; evidence_state: COMMIT
  - path: src/backend/storage/lmgr/README; symbol: VXID locks; lines: 273-277; file_sha256: 381d8acfeeb061030a495a5fd72755361e2f14e98b168aa1b0efbcae55531874; evidence_state: COMMIT
- limitations_ko: pinned comment가 명시한 주요 waiter는 CREATE INDEX CONCURRENTLY와 Hot Standby이며, VXID는 restart 뒤 재사용되어 disk에 저장하면 안 된다.

#### PG-C032

- claim_ko: speculative insertion은 XID+token tag의 owner ExclusiveLock과 observer ShareLock으로 한 insertion decision을 rendezvous하고, tuple의 confirmed/dead 판정을 먼저 기록한 뒤 owner lock을 release하여 waiter가 재검사하게 한다.
- source_refs:
  - path: src/backend/storage/lmgr/lmgr.c; symbol: SpeculativeInsertionLockAcquire; lines: 774-803; file_sha256: 7301f269a04cb423ff830d5490300185cf7b36c675b515638cda235125688eaf; evidence_state: COMMIT
  - path: src/backend/storage/lmgr/lmgr.c; symbol: SpeculativeInsertionWait; lines: 805-839; file_sha256: 7301f269a04cb423ff830d5490300185cf7b36c675b515638cda235125688eaf; evidence_state: COMMIT
  - path: src/backend/executor/nodeModifyTable.c; symbol: SpeculativeInsertionLockAcquire; lines: 1225-1258; file_sha256: eee5c18399d1741f6518e5419b55aba3fa6e4cc8313ce8998891ca8147943a60; evidence_state: COMMIT
  - path: src/backend/executor/execIndexing.c; symbol: SpeculativeInsertionWait; lines: 872-901; file_sha256: 8d8cb227ddb0dd0cb949a840a49db209701937cc0678d4f1bdc5aa44c0a245df; evidence_state: COMMIT
- limitations_ko: ON CONFLICT의 tentative decision 한 건에 한정되고 ordinary INSERT transaction 전체나 모든 appended row를 대표하지 않는다.

#### PG-C033

- claim_ko: pinned PostgreSQL source의 조사 범위에는 CUBRID의 “MVCCID X self-lock을 잡아 appended MVCC row의 per-row X lock을 생략하고, S waiter가 commit/abort release를 기다린 뒤 재검사한다”는 전체 semantics를 하나로 구현하는 identifier/API/condition이 없고, 그 책임은 tuple XMAX/MultiXact, XID completion lock, transient tuple arbitration lock, speculative token으로 분리되어 있다.
- source_refs:
  - path: src/backend/access/heap/README.tuplock; symbol: Locking tuples; lines: 1-37; file_sha256: 86be226a5db54ac65b29e1f28adabda875fbf1f41bf718d252c1cf872f4fa5a2; evidence_state: COMMIT
  - path: src/backend/storage/lmgr/lmgr.c; symbol: XactLockTableInsert; lines: 614-730; file_sha256: 7301f269a04cb423ff830d5490300185cf7b36c675b515638cda235125688eaf; evidence_state: COMMIT
  - path: src/backend/storage/lmgr/lmgr.c; symbol: SpeculativeInsertionLockAcquire; lines: 774-839; file_sha256: 7301f269a04cb423ff830d5490300185cf7b36c675b515638cda235125688eaf; evidence_state: COMMIT
  - path: src/backend/storage/lmgr/lock.c; symbol: VirtualXactLock; lines: 4582-4825; file_sha256: bad8fb3ce27d2a4bda77c4e030202eb6395665096bb0d6bacced8f5f77d75eb5; evidence_state: COMMIT
- limitations_ko: “없다”는 pinned revision과 아래 명시한 repository areas/terms/call inventory에 한정된 강한 negative search 결과다. 다른 extension이나 다른 revision까지 부정하지 않는다.

## Strong negative search record

### Exact self-lock / substitution terminology

searched areas:

- src/backend/storage/lmgr
- src/include/storage
- src/backend/access/heap
- src/backend/access/nbtree
- src/backend/executor
- src/backend/utils/adt/ri_triggers.c
- src/test/isolation/specs

searched alternate terms:

    self[-_ ]?lock
    selflock
    mvccid
    transaction[-_ ]self
    xid[-_ ]self
    omit.*(row|tuple).*lock
    replace.*(row|tuple).*lock
    append(ed)?.*(self|transaction).*(lock)
    per[-_ ]row.*(self|xid).*lock

result: no matches.

주의: HeapTupleSatisfiesSelf, TM_SelfModified, “found self tuple”은 각각 snapshot visibility 또는 같은 command/transaction의 tuple 상태를 뜻하며 self lock과 무관하다. 위 검색은 self라는 단어 하나만으로 false positive를 모으지 않고 lock/substitution 조합을 찾았다.

### Exhaustive rendezvous symbol inventory

다음 symbol/call을 src/backend, src/include, src/test/isolation/specs 전체에서 inventory했다.

    XactLockTableInsert
    XactLockTableDelete
    XactLockTableWait
    ConditionalXactLockTableWait
    VirtualXactLockTableInsert
    VirtualXactLockTableCleanup
    VirtualXactLock
    SpeculativeInsertionLockAcquire
    SpeculativeInsertionLockRelease
    SpeculativeInsertionWait
    LOCKTAG_TRANSACTION / SET_LOCKTAG_TRANSACTION
    LOCKTAG_VIRTUALTRANSACTION / SET_LOCKTAG_VIRTUALTRANSACTION
    LOCKTAG_SPECULATIVE_TOKEN / SET_LOCKTAG_SPECULATIVE_INSERTION

positive call sites examined include heap delete/update/tuple lock/lock-updated-chain/MultiXact member waits, heapam handler uniqueness paths, btree insertion, exclusion constraint recheck, replication, logical snapshot building, CREATE INDEX CONCURRENTLY, standby, and transaction start/end. Central shared scenario에 도달하는 것은 heap_update/heap_lock_tuple의 XID 또는 MultiXact wait, nbtinsert의 XID/speculative wait, FK의 KeyShare tuple lock이다.

### Normal-lock hierarchy/escalation negative search

searched files:

- src/backend/storage/lmgr/lock.c
- src/backend/storage/lmgr/lmgr.c
- src/backend/storage/lmgr/proc.c
- src/backend/storage/lmgr/deadlock.c
- src/include/storage/lock.h
- src/include/storage/lockdefs.h
- src/include/storage/locktag.h
- src/backend/access/heap/heapam.c
- src/backend/access/heap/README.tuplock

searched terms:

    intent(ion)?[- ]lock
    multi[- ]gran
    lock[-_ ]escalat
    escalat(e|ion|ing).*lock
    lock.*escalat

result: no matches in the normal heavyweight/tuple scope.

contradiction boundary: broader repository inspection found src/backend/storage/lmgr/README-SSI:253-291, where Serializable SIREAD predicate locks use tuple/page/table granularities and promotion. 따라서 negative claim은 normal blocking heavyweight relation/tuple lock manager에만 적용한다.

## Examined symbols

Core resource/model:

- LockTagType, LOCKTAG, SET_LOCKTAG_RELATION, SET_LOCKTAG_TUPLE, SET_LOCKTAG_TRANSACTION, SET_LOCKTAG_VIRTUALTRANSACTION, SET_LOCKTAG_SPECULATIVE_INSERTION
- LOCKMODE, LockConflicts, LockMethodData
- LOCK, PROCLOCK, LOCALLOCK, ResourceOwner
- RelationInitLockInfo, LockRelationOid, LockTuple, UnlockTuple

Acquire/wait/release:

- LockAcquire, LockAcquireExtended, SetupLockInTable, LockCheckConflicts, GrantLock, UnGrantLock, CleanUpLock
- JoinWaitQueue, WaitOnLock, ProcSleep, ProcWakeup, ProcLockWakeup
- CheckDeadLock, DeadLockCheck, FindLockCycle, DeadLockReport
- LockRelease, LockReleaseAll, ProcReleaseLocks, ResourceOwnerRelease

MVCC/row conflict:

- SeqNext, heapgettup, HeapTupleSatisfiesVisibility, HeapTupleSatisfiesMVCC
- ExecLockRows, table_tuple_lock, heap_lock_tuple, heap_acquire_tuplock
- heap_update, ExecUpdateAct, ExecUpdate, EvalPlanQual
- RI_FKey_check, ri_FastPathProbeOne, ri_LockPKTuple
- _bt_doinsert, _bt_check_unique, check_exclusion_or_unique_constraint

Transaction rendezvous:

- GetTopTransactionId, GetCurrentTransactionId, AssignTransactionId
- XactLockTableInsert, XactLockTableDelete, XactLockTableWait, ConditionalXactLockTableWait
- VirtualXactLockTableInsert, VirtualXactLockTableCleanup, VirtualXactLock
- SpeculativeInsertionLockAcquire, SpeculativeInsertionLockRelease, SpeculativeInsertionWait
- CommitTransaction, AbortTransaction, CommitSubTransaction

Durability/operations:

- LockManagerShmemRequest, AtPrepare_Locks, lock_twophase_recover
- max_locks_per_transaction, deadlock_timeout, lock_timeout, log_lock_waits, log_lock_failures
- pg_lock_status, pg_locks, pg_blocking_pids

## File hash inventory

| path | sha256 |
|---|---|
| src/include/storage/locktag.h | 0ffaea18914516886ea4892c642f2274acb65e32b51c9ceca92e1cef1c9c5a81 |
| src/include/storage/lockdefs.h | 7db1a4531f5da94667f2ca498136e6796d89a8ba56115fd90bef198e09a2af68 |
| src/include/storage/lock.h | 9e997e40e45889d6d1b9040440303d244df566546b48e7e6b9d12f99d3767e16 |
| src/include/nodes/lockoptions.h | 3cfd2f4f76f716cfd57de8c4b40a90f7061bc4215df5df93618201fd5ad43535 |
| src/backend/storage/lmgr/README | 381d8acfeeb061030a495a5fd72755361e2f14e98b168aa1b0efbcae55531874 |
| src/backend/storage/lmgr/README-SSI | ea153efc28939c1309e2495599f427121a579c165702e80cbc64e2ccf7cecc7f |
| src/backend/storage/lmgr/lock.c | bad8fb3ce27d2a4bda77c4e030202eb6395665096bb0d6bacced8f5f77d75eb5 |
| src/backend/storage/lmgr/lmgr.c | 7301f269a04cb423ff830d5490300185cf7b36c675b515638cda235125688eaf |
| src/backend/storage/lmgr/proc.c | 67031da14df638c9df197a8e77649421836ba5ad4eb6097d01b3661d1f69b9a4 |
| src/backend/storage/lmgr/deadlock.c | 38a45a2ca98090b3bbdb1ab472f723c5f094323b8c95a9339e371a77e30a7fd6 |
| src/backend/parser/parse_clause.c | c7a514d028a3529b4efbc6b53cfbdb07307c4b6bcbaa0e19c43b6a724edfeb70 |
| src/backend/parser/parse_relation.c | c96240f99aa48499e01a673762f668fb133b6c9352850fba792da5378e48b400 |
| src/backend/executor/nodeSeqscan.c | fe83e0d0a1cd1b161440b233cf5c85a81b5614ec8b214a7e8069d375a631416d |
| src/backend/executor/nodeLockRows.c | 06b3c78a370e2460e14fdc8fee2e7acfc551fa8cbad5dfd0cd3606dd38b3c5e3 |
| src/backend/executor/nodeModifyTable.c | eee5c18399d1741f6518e5419b55aba3fa6e4cc8313ce8998891ca8147943a60 |
| src/backend/executor/execIndexing.c | 8d8cb227ddb0dd0cb949a840a49db209701937cc0678d4f1bdc5aa44c0a245df |
| src/backend/access/heap/README.tuplock | 86be226a5db54ac65b29e1f28adabda875fbf1f41bf718d252c1cf872f4fa5a2 |
| src/backend/access/heap/heapam.c | 9be2f576df608c95992b65b2009640c3da5a9238aba73cf2cf106af124f77878 |
| src/backend/access/heap/heapam_visibility.c | 8fdcbfec13791b43c74cbeab351162ea095c23b8d90cee5c86140bba8a8fbc6a |
| src/backend/access/nbtree/nbtinsert.c | 0ef3d779ec130b82bd2658c32d71085a629d218e91808e929ee0d0dc43baa617 |
| src/backend/utils/adt/ri_triggers.c | 9aeecd49d4ce8bd9c1695fa733003793d6d0995818f3652e92801565c63c89d8 |
| src/backend/access/transam/xact.c | b40898eda7d02c7cf4b7671ab3bf1b3d0ea757cf33765f98fe074d98e8382df2 |
| src/backend/utils/resowner/resowner.c | 0fd0f9cac6abe6817a6cca5ef3755d9916d9571e5b1c381cb5306e4fb484be27 |
| src/backend/utils/misc/guc_parameters.dat | e308005cebdcbe545fe9fe8635bfcf071dcc5cbb741b599b50cb3ab72ba94a67 |
| src/backend/catalog/system_views.sql | 6203864baafee05bda77106d6e1bafd48a6ec902f3361b0f4ecda3b9bc2cc9e2 |
| src/backend/utils/adt/lockfuncs.c | 25318bcb3c2822e5d4f2268f62684d28b70fce21c968684bc85be0eef3b9a613 |

## Comparison suggestions and analogy cautions

### Central behavior 1: resource/mode/hierarchy

- suggested analogy class: partial analogy.
- comparable responsibility: both systems need class/relation coordination plus record-level conflict control.
- semantic gap: PostgreSQL의 relation weak modes는 DDL coordination이고 tuple lock은 별도 tag/header protocol이다. CUBRID class intent hierarchy나 lock escalation과 이름/동작을 강제로 맞추지 말 것.
- caution: RowExclusiveLock은 다른 RowExclusiveLock과 충돌하지 않는다. 이름의 “Exclusive”만 보고 table write serialization으로 설명하면 틀린다.
- caution: predicate SIREAD promotion은 normal blocking lock escalation의 증거로 쓰지 말 것.

### Central behavior 2: wait/deadlock/timeout/release

- suggested analogy class: partial analogy 또는 equivalent only at abstract state-machine level.
- close invariant: conflict 검사 -> queue -> delayed deadlock detection -> grant-before-wakeup -> caller recheck.
- semantic gap: PostgreSQL deadlock graph에는 holder hard edge뿐 아니라 queue-order soft edge와 queue rearrangement가 있다. victim choice/error timing을 CUBRID와 동일하다고 말할 근거는 없다.
- caution: lock_timeout과 deadlock_timeout은 서로 다른 timer다. deadlock_timeout은 보통 deadlock 검사를 늦춰 비용을 줄이는 값이지 lock wait의 상한이 아니다.

### Central behavior 3: snapshot read versus locking read/update

- suggested analogy class: partial analogy.
- close invariant: plain MVCC read는 in-progress updater 때문에 old visible version에서 row wait하지 않지만 locking read/update/FK/unique constraint는 별도 correctness conflict를 기다린다.
- semantic gap: PostgreSQL row lock state는 XMAX/MultiXact에 지속되고 heavyweight tuple lock은 fairness only다. CUBRID object lock table의 record lock lifetime과 1:1 대응시키지 말 것.
- caution: plain SELECT도 AccessShare relation lock, buffer lock, Serializable SSI tracking을 가질 수 있으므로 “lock-free SELECT” 대신 “row-version conflict에서 nonblocking snapshot read”라고 쓸 것.
- caution: foreign key의 KeyShare는 snapshot visibility로 대체할 수 없다. 참조 대상의 future key-changing update/delete를 막는 목적이다.

### Central behavior 4: MVCCID self-lock

- suggested analogy classes:
  - CUBRID MVCCID self-lock ↔ PostgreSQL LOCKTAG_TRANSACTION: partial analogy. 동일 XID에 owner X/observer S, transaction end release, wake/recheck라는 가장 중요한 rendezvous 모양이 닮음.
  - CUBRID self-lock publish ordering ↔ PostgreSQL VXID: partial analogy. owner-before-advertise가 닮았지만 shared row scenario의 wait target이 아님.
  - CUBRID release-after-state-decision ↔ speculative token: partial analogy. decision-before-release/recheck가 가장 선명하지만 ON CONFLICT 단건에만 적용.
  - CUBRID 전체 appended-row lock substitution ↔ PostgreSQL 단일 mechanism: no equivalent within pinned source/search scope.
- essential caution: PostgreSQL XID lock을 “row X lock 하나로 승격한 것”이라고 설명하지 말 것. row compatibility는 tuple XMAX/MultiXact이고 XID lock은 completion wait rendezvous다.
- essential caution: PostgreSQL의 owner transaction lock은 XID가 할당된 모든 transaction/subtransaction에 설치되며 CUBRID의 특정 insert optimization condition과 범위가 다르다.
- essential caution: speculative token은 일반 unique insertion에도 항상 쓰이는 것이 아니다. ordinary insertion conflict는 whole transaction XID를 기다리고, speculative token은 ON CONFLICT tentative verdict를 빨리 기다리기 위한 별도 tag다.
- essential caution: XID tag에는 class OID나 row identity가 없다. 같은 transaction의 많은 tuple waiter가 completion을 공유할 수 있지만 어느 row/mode가 충돌했는지는 tuple/index 상태가 보유한다.

## Unknowns, gaps, and non-claims

- PostgreSQL runtime을 실행하지 않았으므로 shared account 시나리오의 실제 blocking duration, pg_locks row 조합, error message/timing은 source prediction이지 runtime observation이 아니다.
- Serializable isolation의 full SSI/predicate-lock path는 central scope 바깥이다. plain SELECT claim은 MVCC visibility 함수와 relation lock에 한정하며 serialization anomaly 처리 전체를 대표하지 않는다.
- MultiXactIdWait 내부의 member-by-member wake behavior와 pg_multixact SLRU recovery 전체는 읽었지만 이 packet의 33 claims에는 interface-level persistence와 heap caller 의무까지만 반영했다.
- prepared transaction과 hot standby의 모든 lock replay 조합은 완전 추적하지 않았다. qualifying 2PC lock record/recover와 VXID exclusion은 source-confirmed다.
- extension-defined advisory/custom lock protocol은 negative search의 대상이 아니다.
- performance에 대해서는 fast-path의 설계 목적과 lock-table cardinality trade-off만 source-confirmed다. CUBRID 대비 처리량/메모리 우열은 측정하지 않았으므로 주장하지 말 것.
- exact no-equivalent 결론은 frozen revision과 명시한 searched areas/alternate terms/reachable rendezvous inventory로 제한한다. 다른 PostgreSQL revision 또는 extension에 대한 보편 명제가 아니다.
