# PostgreSQL 장 독립 감사·확장 제안

## 감사 고정 정보

- role: Role 2 — PostgreSQL comparator, independent audit revision
- topic: CUBRID lock과 lock manager, 특히 self lock 및 MVCC lock의 필요성
- frozen scope: `/home/vimkim/gh/my-cubrid-docs/code-analysis/lock-lock-manager-self-lock-mvcc-lock/f30f1c2_codex/research/scope.md`
- scope sha256: `711d1a0f5bfebdbe1b55b4299973efc353d90636e2f00fc807f51d031766a839`
- PostgreSQL root: `/home/vimkim/gh/pg/postgres`
- revision: `fd2b89854d93d70fe8c9a69d5b8fafd5b9302cfc`
- branch: `master`
- dirty label: source commit-clean; worktree에는 untracked `.omc/`만 존재
- evidence state: 인용한 PostgreSQL 파일은 pinned revision의 `COMMIT` 바이트와 일치
- collected_at_utc: `2026-08-11T09:55:25Z`
- method: source-only static trace; PostgreSQL server runtime은 실행하지 않음
- allowed outputs: 이 파일과 `postgresql-added-claims.jsonl`만 작성; Book, ledger, report, quiz, experiment, source는 수정하지 않음

## 감사 결론

현재 11장은 resource 종류, 공통 시나리오, wait/release, self-lock 근접 메커니즘, 음성 결론을 짧게 다루지만, frozen scope가 요구하는 ownership/lifetime, subtransaction, deadlock의 hard/soft edge, MVCC operation별 정책, 2PC·restart 경계, startup/cleanup, 설정·자원 압력·오류, 성능·관측성을 장 수준으로 노출하지 않는다. 이 문서는 최종 Book을 쓰지 않고, main agent가 통합할 수 있는 claim-safe 한국어 구성과 28개 추가 source claim을 제안한다.

PostgreSQL의 핵심 해석은 “CUBRID와 이름이 같은 lock을 찾기”가 아니라 “책임이 어디에 배치되는가”이다. relation 안정성은 heavyweight relation tag, 정상 row ownership은 tuple header의 XMAX/MultiXact, 기다림의 공정성은 짧은 tuple tag, transaction 완료 대기는 XID tag, 모든 top transaction 공개 순서는 VXID tag, `ON CONFLICT`의 잠정 판정은 speculative token으로 나뉜다. [Claims: PG-C001, PG-C002, PG-C101, PG-C128]

CUBRID MVCCID self-lock과 PostgreSQL XID/VXID/speculative rendezvous는 unfinished writer를 기다린 뒤 상태를 재검사한다는 목적만 부분 유사하며, appended-row row-X 생략과 unique/FK observer 대기를 하나의 transaction resource에 결합한 PostgreSQL 단일 메커니즘은 조사 범위에서 확인되지 않았다. [Claims: CUBRID-C030, CUBRID-C031, CUBRID-C032, CUBRID-C033, PG-C030, PG-C031, PG-C126, PG-C127, PG-C128, CMP-C030]

## 통합 규칙

다음은 편집 지침이며 사실 claim이 아니다.

1. main agent만 `chapters/11-postgresql.html`을 수정한다.
2. 현재 `<title>`, 장 제목, 이전/목차/다음 navigation, `../assets/report.css`를 보존한다.
3. 아래 제안 anchor를 실제 `<section id="…">`에 사용하고, section뿐 아니라 표의 각 사실 cell·pseudocode branch·diagram edge에도 대응 `data-claim-id`를 둔다.
4. 모든 표에는 한국어 `<caption>`과 scope가 분명한 `<th scope="col|row">`를 둔다.
5. 흐름 그림은 inline SVG 또는 HTML/CSS로만 만들고, `<figure><figcaption>` 및 화면 판독기용 한국어 텍스트 대안을 제공한다. 원격 font, script, CDN은 쓰지 않는다.
6. “동일하다”는 표현은 피하고 comparison claim이 허용한 `partial analogy` 또는 `no equivalent`를 눈에 보이게 표시한다.
7. source prediction을 runtime observation으로 쓰지 않는다. 실제 wait 시간, `pg_locks` 행 모양, 처리량·메모리 우열은 이 장에서 `Unknown/미측정`으로 표시한다.

## 제안 anchor와 claim 묶음

| 제안 anchor | 장의 질문 | 최소 claim 묶음 |
|---|---|---|
| `postgresql-analysis` | PostgreSQL은 같은 correctness 책임을 어디에 나누는가? | `PG-C001 PG-C002 PG-C101 PG-C128` |
| `pg-learning-goals` | 독자가 끝에서 무엇을 설명해야 하는가? | 아래 학습 목표의 각 claim |
| `pg-account-scenario` | account 시나리오의 여섯 operation은 어디서 기다리고 무엇을 재검사하는가? | `PG-C020 PG-C021 PG-C103 PG-C111..PG-C117 PG-C127` |
| `pg-resource-model` | resource key, mode, relation/tuple 관계는 무엇인가? | `PG-C001 PG-C002 PG-C101 PG-C102 PG-C103 CMP-C001` |
| `pg-ownership-lifetime` | shared/local owner와 transaction/subtransaction 수명은 무엇인가? | `PG-C104 PG-C110 PG-C119` |
| `pg-lock-lifecycle` | fast path, conflict, queue, grant, wakeup, release는 어떻게 이어지는가? | `PG-C010 PG-C011 PG-C105 PG-C106 PG-C109 PG-C110` |
| `pg-deadlock-timeout` | deadlock, timeout, interrupt는 어떻게 갈라지는가? | `PG-C010 PG-C107 PG-C108 CMP-C010` |
| `pg-mvcc-policy` | snapshot read와 locked read/DML/FK/unique는 왜 다른가? | `PG-C020 PG-C021 PG-C111..PG-C117 CMP-C020` |
| `pg-durability-recovery` | volatile lock state와 persistent tuple/2PC state의 경계는 무엇인가? | `PG-C118 PG-C119 PG-C120` |
| `pg-startup-shutdown` | startup, transaction start/end, abort, subtransaction 종료에서 무엇을 초기화·정리하는가? | `PG-C110 PG-C119 PG-C120 PG-C121 PG-C122` |
| `pg-errors-pressure` | timeout, NOWAIT/SKIP, deadlock, shared-memory 부족은 어떻게 드러나는가? | `PG-C107 PG-C108 PG-C112 PG-C123` |
| `pg-performance-observability` | fast path의 의도와 관측 인터페이스, 측정 한계는 무엇인가? | `PG-C002 PG-C104 PG-C105 PG-C123 PG-C124 PG-C125` |
| `pg-self-lock-boundary` | XID/VXID/speculative가 각각 어디까지 닮고 어디서 갈라지는가? | `CUBRID-C030..CUBRID-C033 PG-C030 PG-C031 PG-C121 PG-C126..PG-C128 CMP-C030` |
| `pg-invariants-limits` | 반드시 지켜야 할 순서와 이 조사의 미확인은 무엇인가? | `PG-C011 PG-C109 PG-C111 PG-C113 PG-C117 PG-C122 PG-C126 PG-C127 PG-C128` |
| `pg-recap` | 네 central behavior를 어떤 문장으로 회수하고 MySQL 장으로 넘길 것인가? | `CMP-C001 CMP-C010 CMP-C020 CMP-C030` |

## `pg-learning-goals` 제안

도입 문장은 “이 장을 마치면 다음을 설명할 수 있다”로 시작한다.

- relation, tuple, XID, VXID, speculative token의 resource key가 서로 다르고, 표준 heavyweight mode와 SQL row-lock strength가 같은 이름 공간이 아님을 설명한다. [Claims: PG-C101, PG-C102, PG-C112]
- `LOCK`·`PROCLOCK`·`LOCALLOCK`이 각각 resource 상태, backend별 hold, backend-private 재획득/ResourceOwner 수명을 나누어 맡는 이유를 설명한다. [Claims: PG-C104]
- conflict → queue → delayed deadlock 검사/timeout/interrupt → grant-before-wakeup → transaction cleanup 흐름을 추적한다. [Claims: PG-C010, PG-C011, PG-C105, PG-C106, PG-C107, PG-C108, PG-C109, PG-C110]
- plain snapshot read, `FOR UPDATE`, `UPDATE`, duplicate unique insert, FK check가 서로 다른 visibility/lock/recheck 정책을 갖는 이유를 account 시나리오로 설명한다. [Claims: PG-C020, PG-C021, PG-C111, PG-C112, PG-C113, PG-C114, PG-C115, PG-C116, PG-C117]
- CUBRID self-lock과 XID, VXID, speculative token의 대응을 `partial analogy`와 `no equivalent`로 구분한다. [Claims: CUBRID-C030, CUBRID-C031, CUBRID-C032, CUBRID-C033, PG-C030, PG-C031, PG-C121, PG-C126, PG-C127, PG-C128, CMP-C030]

## `pg-account-scenario` 제안

### 시나리오 텍스트

`account(id PRIMARY KEY, balance)`에서 T1이 기존 행을 갱신하고 새 unique key를 넣는 동안 T2의 plain read, locked read, same-row update, duplicate insert가 어디에서 갈라지는지를 본다. 이 장의 질문은 단순히 “기다리는가”가 아니라 “어떤 resource가 상태를 소유하고, wait 전 무엇을 놓고, wakeup 뒤 무엇을 재검사하는가”이다.

### operation 정책 표

실제 HTML에서는 아래 각 cell의 claim을 그 `<td>`에 직접 노출한다.

| T2 operation | relation 수준 | row/index 수준 | wait와 wakeup 뒤 의무 |
|---|---|---|---|
| plain `SELECT` | source relation에 `AccessShareLock`을 transaction end까지 유지한다. [Claims: PG-C103] | executor snapshot으로 heap visibility를 판정하며 in-progress updater의 old version을 visible로 반환할 수 있다. [Claims: PG-C020, PG-C111] | 이 old-version 경로는 updater XID completion lock을 기다리지 않는다. 단, relation lock·buffer lock·SSI 별도 책임까지 “완전 lock-free”라고 부르지 않는다. [Claims: PG-C111] |
| `SELECT … FOR UPDATE` | source relation에 `RowShareLock`을 유지한다. [Claims: PG-C103] | row strength/wait policy를 `table_tuple_lock`에서 `heap_lock_tuple`로 전달하고, XMAX/MultiXact와 transient tuple arbitration을 사용한다. [Claims: PG-C020, PG-C112, PG-C113] | 충돌 시 buffer lock을 놓고 completion을 기다리며, 다시 buffer를 잡아 XMAX를 재검사한 뒤 자신의 row lock state를 tuple header에 기록한다. [Claims: PG-C113] |
| same-row `UPDATE` | target relation에 `RowExclusiveLock`을 유지하며 이 mode끼리는 서로 충돌하지 않는다. [Claims: PG-C103] | key attribute 변경 여부에 따라 `NoKeyExclusive` 또는 `Exclusive` row strength를 선택한다. [Claims: PG-C114] | concurrent update 뒤 Read Committed는 최신 version을 lock하고 EvalPlanQual로 조건을 재평가해 retry하지만 transaction-snapshot isolation은 serialization failure를 낸다. [Claims: PG-C115] |
| ordinary duplicate unique `INSERT` | target relation에 `RowExclusiveLock`을 유지한다. [Claims: PG-C103] | B-tree unique checker가 `DirtySnapshot`에서 equal key의 in-progress XID 또는 speculative token을 찾는다. [Claims: PG-C021, PG-C117] | leaf buffer를 놓고 XID/token 완료를 기다린 뒤 root search부터 다시 시작해 commit/abort와 index 조건을 재판정한다. [Claims: PG-C021, PG-C117] |
| FK 참조 검사 | PK relation을 `RowShareLock`으로 연다. [Claims: PG-C116] | matching PK tuple에 `KeyShare`를 기록해 delete와 key-changing update를 막는다. [Claims: PG-C114, PG-C116] | Read Committed에서 update chain을 따라가면 key를 다시 검사한다. [Claims: PG-C116] |
| `ON CONFLICT` speculative insertion | transaction 전체가 아니라 한 tentative insertion을 XID+token resource로 식별한다. [Claims: PG-C031, PG-C101, PG-C127] | owner는 token에 X, observer는 S를 사용한다. [Claims: PG-C031, PG-C127] | tuple의 confirmed/dead 판정을 먼저 기록하고 token을 release하므로 waiter는 tuple/index 조건을 다시 검사한다. [Claims: PG-C127] |

### operation call-path 그림/텍스트 대안

그림의 각 화살표에도 끝의 claim ID를 달고, 같은 내용을 `<ol>` 텍스트 대안으로 제공한다.

1. `addRangeTableEntry → parserOpenTable(AccessShareLock) → SeqNext → HeapTupleSatisfiesMVCC → old visible version` [Claims: PG-C103, PG-C111]
2. `addRangeTableEntry(RowShareLock) → ExecLockRows → table_tuple_lock → heap_lock_tuple → XID/MultiXact wait → XMAX recheck` [Claims: PG-C020, PG-C103, PG-C112, PG-C113]
3. `setTargetTable(RowExclusiveLock) → heap_update(lock mode selection) → ExecUpdateAct → EvalPlanQual/retry 또는 serialization failure` [Claims: PG-C103, PG-C114, PG-C115]
4. `_bt_doinsert → _bt_check_unique(DirtySnapshot) → release leaf buffer → XactLockTableWait/SpeculativeInsertionWait → root search restart` [Claims: PG-C021, PG-C117]
5. `RI_FKey_check → PK relation RowShareLock → ri_LockPKTuple(KeyShare) → update-chain/key recheck` [Claims: PG-C116]

## `pg-resource-model` 제안

### 핵심 문단

PostgreSQL은 relation, tuple, transaction XID, virtual transaction, speculative insertion을 서로 다른 typed `LOCKTAG`로 구분하고, tag의 필드 조합이 resource identity를 만든다. [Claims: PG-C001, PG-C101]

표준 heavyweight lock manager는 `AccessShareLock`부터 `AccessExclusiveLock`까지 여덟 mode와 conflict bitmask를 사용한다. SQL row lock의 네 strength는 별도 `LockTupleMode`이며 내부 매핑을 통해 heavyweight arbitration mode와 MultiXact status로 번역된다. [Claims: PG-C102, PG-C112]

tuple tag에 database/relation/block/offset이 들어가도 normal blocking path가 CUBRID식 parent intent mode를 자동 획득한다는 뜻은 아니다. 정상 row ownership은 tuple header XMAX/MultiXact에 남고 heavyweight tuple tag는 충돌 waiter의 우선순위를 중재하는 짧은 자원이다. [Claims: PG-C002, PG-C101]

### resource/mode 표

| resource | key | 이 장에서 맡는 책임 | 대응 한계 |
|---|---|---|---|
| relation tag [Claims: PG-C001, PG-C101] | database OID + relation OID [Claims: PG-C101] | plain/locked read와 DML이 relation 안정성에 맞는 mode를 transaction end까지 유지한다. [Claims: PG-C103] | `RowExclusiveLock`은 같은 mode와 호환되므로 table write X lock으로 읽으면 안 된다. [Claims: PG-C103] |
| tuple tag [Claims: PG-C001, PG-C101] | database OID + relation OID + block + offset [Claims: PG-C101] | row waiter 사이 우선순위와 중재를 제공한다. [Claims: PG-C002, PG-C113] | 정상 row ownership 전체를 shared tuple lock entry가 transaction end까지 대표하지 않는다. [Claims: PG-C002, PG-C113] |
| transaction tag [Claims: PG-C001, PG-C101] | XID [Claims: PG-C101] | XID owner X와 observer S가 transaction completion에서 rendezvous한다. [Claims: PG-C030, PG-C126] | row identity와 row compatibility는 이 tag가 아니라 tuple/index 상태에 남는다. [Claims: PG-C002, PG-C030] |
| VXID tag [Claims: PG-C001, PG-C101] | proc number + local transaction id [Claims: PG-C101] | top transaction을 observer에게 공개하기 전 owner lock을 만든다. [Claims: PG-C121] | account row 충돌의 일반 wait target이 아니다. [Claims: PG-C031, PG-C121] |
| speculative tag [Claims: PG-C001, PG-C101] | XID + token [Claims: PG-C101] | 한 tentative insertion의 confirmed/dead 판정을 기다린다. [Claims: PG-C031, PG-C127] | ordinary insert transaction 전체나 모든 appended row의 대표가 아니다. [Claims: PG-C031, PG-C127] |

비교 문장은 “세 DBMS 모두 relation/class와 row-level correctness를 조정하지만 resource hierarchy와 mode lattice의 Interface는 부분 유사”까지만 쓴다. [Claims: CMP-C001]

## `pg-ownership-lifetime` 제안

shared `LOCK`은 resource별 granted/wait 상태와 queue를, shared `PROCLOCK`은 resource/backend별 hold 상태를, backend-private `LOCALLOCK`은 mode별 재획득 횟수와 ResourceOwner별 소유를 추적한다. 같은 backend의 보유 lock끼리는 서로 block하지 않는다. [Claims: PG-C104]

transaction/subtransaction 수명은 단순히 “commit이면 모두 free”가 아니다. top-level commit은 non-session standard locks를, abort는 session locks까지 release하고, subtransaction commit은 일반 lock ownership을 parent ResourceOwner로 넘기며 subtransaction abort는 해당 owner의 lock을 개별 release한다. [Claims: PG-C110]

prepared transaction은 live backend가 끝난 뒤에도 보존해야 할 transaction-level heavyweight locks를 2PC record에 저장하고 recovery 시 dummy PGPROC owner로 다시 잡지만, VXID와 session-only locks는 restart 뒤 의미가 없어 제외한다. [Claims: PG-C119]

### ownership 표

| 구조/owner | 생성·보유 의미 | 감소·종료 의미 |
|---|---|---|
| `LOCK` [Claims: PG-C104] | 한 resource의 grant mask, wait mask, wait queue를 shared state로 가진다. [Claims: PG-C104] | holder 감소와 waiter grant가 같은 shared resource state에서 조정된다. [Claims: PG-C104, PG-C109] |
| `PROCLOCK` [Claims: PG-C104] | resource와 backend/lock group의 hold mask를 연결한다. [Claims: PG-C104] | backend/transaction release가 보유 mode를 resource에서 제거한다. [Claims: PG-C104, PG-C110] |
| `LOCALLOCK` + ResourceOwner [Claims: PG-C104] | 같은 backend의 mode별 재획득 count와 owner별 count를 추적한다. [Claims: PG-C104] | local count가 남으면 shared table 접근 없이 감소하고, transaction/subtransaction 정책에 따라 넘기거나 release한다. [Claims: PG-C104, PG-C105, PG-C110] |
| prepared dummy owner [Claims: PG-C119] | 2PC record의 qualifying transaction locks를 recovery 시 재획득한다. [Claims: PG-C119] | prepared transaction의 최종 결말 경로 전체는 이 장의 추적 범위를 벗어나므로 세부 순서를 단정하지 않는다. [Claims: PG-C119] |

## `pg-lock-lifecycle` 제안

### acquire/wait/release 흐름

`LockAcquireExtended`는 먼저 backend-local hold를 확인한다. 이미 보유했다면 `LOCALLOCK` count만 늘리고, eligible weak relation lock이면 per-backend fast path를 시도하며, 나머지는 partitioned shared `LOCK/PROCLOCK` table에서 conflict를 검사한다. [Claims: PG-C104, PG-C105]

즉시 grant가 안전하지 않으면 요청은 strict FIFO가 아닌 priority-aware queue 규칙으로 삽입되며, requester의 기존 hold와 앞선 conflicting waiter까지 고려한다. 이 규칙만으로 scheduler-independent starvation freedom을 주장하지 않는다. [Claims: PG-C010, PG-C106]

release 쪽은 wakable waiter를 shared state에 먼저 grant한 뒤 latch를 깨운다. 이 grant-before-wakeup 순서는 새 requester가 깨어나는 중인 waiter를 추월하는 race를 막지만, tuple/index 조건 재검사는 access method caller의 별도 의무다. [Claims: PG-C011, PG-C109]

### pseudocode 제안

실제 HTML에서는 각 `if`/`else`/`wait` branch를 별도 `<li data-claim-id>` 또는 행으로 만든다.

```text
acquire(tag, mode, owner):
  if 같은 backend가 이미 보유:
      LOCALLOCK/ResourceOwner count 증가 후 성공      [Claims: PG-C104, PG-C105]
  else if weak relation lock이고 fast-path eligible:
      per-backend fast path 시도                       [Claims: PG-C105, PG-C125]
  else:
      shared LOCK + PROCLOCK 설정                      [Claims: PG-C104, PG-C105]
      if holder/선행 waiter와 즉시 grant가 안전:
          shared state에 GrantLock                     [Claims: PG-C010, PG-C106]
      else:
          priority-aware wait queue에 삽입              [Claims: PG-C010, PG-C106]
          deadlock/lock-timeout timer와 interrupt 대기   [Claims: PG-C107]
          if soft deadlock을 queue reorder로 해소:
              재배치 뒤 계속 대기/획득                   [Claims: PG-C108]
          else if hard/unresolvable deadlock:
              deadlock ERROR                            [Claims: PG-C108]

release(resource):
  ungrant holder                                         [Claims: PG-C109]
  wakable waiter를 shared state에 먼저 grant             [Claims: PG-C011, PG-C109]
  waiter latch wakeup                                    [Claims: PG-C011, PG-C109]
```

### row conflict pseudocode 제안

```text
read_or_lock(tuple):
  if plain snapshot read가 old version을 visible로 판정:
      updater completion wait 없이 old tuple 반환        [Claims: PG-C111]
  else if locking read/update가 conflicting XMAX를 관찰:
      buffer lock release                                 [Claims: PG-C113]
      transient tuple priority lock + XID/MultiXact wait  [Claims: PG-C113]
      buffer reacquire + XMAX recheck                     [Claims: PG-C113]
      own XID/MultiXact를 header에 기록 후 transient 해제 [Claims: PG-C113]
  else if unique checker가 in-progress equal key 관찰:
      leaf buffer release + XID/token wait                [Claims: PG-C117]
      root search restart                                 [Claims: PG-C021, PG-C117]
```

## `pg-deadlock-timeout` 제안

`ProcSleep`에는 두 timer가 다른 의미로 들어간다. `deadlock_timeout`은 비싼 deadlock 검사를 지연시킬 뿐 lock wait 상한이 아니고, `lock_timeout > 0`은 별도 lock wait timeout을 예약한다. latch wait는 cancel/die interrupt도 처리한다. [Claims: PG-C107]

deadlock graph에는 conflicting holder가 만드는 hard edge와 앞선 conflicting waiter가 만드는 soft edge가 있다. soft cycle은 가능한 wait queue 재배치로 풀고, 해결할 수 없는 cycle은 현재 transaction에 deadlock ERROR를 낸다. [Claims: PG-C108]

세 DBMS 모두 incompatible request, wait dependency, completion-before-release, wakeup이라는 추상 책임을 갖지만 graph ownership, victim policy, timeout 단위는 partial analogy이고 동일 구현으로 읽지 않는다. [Claims: CMP-C010]

### failure 표

| 사건 | PostgreSQL source 정책 | 이 장이 주장하지 않는 것 |
|---|---|---|
| delayed deadlock check [Claims: PG-C107] | `deadlock_timeout` 뒤 검사를 예약한다. [Claims: PG-C107] | lock wait의 확정 상한 또는 실제 검사 시각을 주장하지 않는다. [Claims: PG-C107] |
| lock wait timeout [Claims: PG-C107] | 0보다 큰 `lock_timeout`이면 별도 timer를 예약한다. [Claims: PG-C107] | workload별 실제 wait duration은 미측정이다. [Claims: PG-C107] |
| interrupt [Claims: PG-C107] | latch wait 중 cancel/die interrupt를 처리한다. [Claims: PG-C107] | 모든 error code/message와 client-visible timing은 미확인이다. [Claims: PG-C107] |
| deadlock [Claims: PG-C108] | hard/soft edge를 검사하고 가능한 soft cycle을 reorder하며 불가능하면 ERROR를 낸다. [Claims: PG-C108] | predicate SSI, buffer-pin deadlock, 모든 victim tie-break를 일반화하지 않는다. [Claims: PG-C108] |

## `pg-mvcc-policy` 제안

“MVCC lock”을 하나의 PostgreSQL lock mode로 소개하지 않는다. plain snapshot read, row locking, DML, unique/FK 검사가 visibility·tuple header·heavyweight rendezvous를 각기 다른 정책으로 조합한다고 설명한다. [Claims: PG-C020, PG-C021, PG-C111, PG-C112, PG-C113, PG-C114, PG-C115, PG-C116, PG-C117]

plain MVCC read는 in-progress writer 때문에 언제나 기다리는 대신 snapshot에 맞는 old version을 읽을 수 있다. 그러나 locked read와 update는 future write correctness를 위해 XMAX/MultiXact 및 XID completion을 조정하고, wakeup 뒤 tuple condition을 다시 검사한다. [Claims: PG-C020, PG-C111, PG-C113, CMP-C020]

update mode는 key 변경 여부에 따라 달라진다. key를 바꾸지 않는 update는 `NoKeyExclusive`를 선택해 FK의 `KeyShare`와 불필요한 충돌을 줄이고, key-changing update는 `Exclusive`로 참조 무결성을 보호한다. [Claims: PG-C114, PG-C116]

unique와 FK는 snapshot visibility만으로 대체할 수 없다. unique checker는 아직 끝나지 않은 equal key의 결말을 기다리고 index를 다시 검색하며, FK checker는 referenced key가 이후 delete/key-changing update되지 않도록 `KeyShare`를 건다. [Claims: PG-C021, PG-C116, PG-C117]

### 책임 분리 표

| correctness 질문 | 담당 상태/메커니즘 | caller 의무 |
|---|---|---|
| “내 snapshot에서 어느 version이 보이는가?” [Claims: PG-C111] | executor snapshot + `HeapTupleSatisfiesMVCC` [Claims: PG-C111] | old visible version이면 updater XID completion을 기다리지 않고 반환한다. [Claims: PG-C111] |
| “누가 이 row를 어떤 strength로 lock/update 중인가?” [Claims: PG-C002, PG-C112] | tuple header XMAX/MultiXact + four `LockTupleMode` strengths [Claims: PG-C002, PG-C112] | wait policy(Block/Skip/Error)와 compatible/self-upgrade 분기를 지킨다. [Claims: PG-C112, PG-C113] |
| “여러 waiter의 순서를 어떻게 중재하는가?” [Claims: PG-C002, PG-C113] | transient heavyweight tuple tag [Claims: PG-C002, PG-C113] | buffer를 놓고 기다리고, 돌아와 header를 재검사한 뒤 transient lock을 푼다. [Claims: PG-C113] |
| “writer transaction이 끝났는가?” [Claims: PG-C030, PG-C126] | XID owner X / observer S completion rendezvous [Claims: PG-C030, PG-C126] | S를 즉시 풀고 running status 및 tuple/index condition을 다시 검사한다. [Claims: PG-C030, PG-C126] |
| “equal unique key가 확정되는가?” [Claims: PG-C021, PG-C117] | DirtySnapshot + XID/speculative completion wait [Claims: PG-C021, PG-C117] | leaf buffer를 놓고 기다린 뒤 B-tree root search를 재시작한다. [Claims: PG-C021, PG-C117] |
| “referenced key가 future delete/update로 사라지는가?” [Claims: PG-C116] | PK relation `RowShare` + tuple `KeyShare` [Claims: PG-C116] | update chain을 따라갔으면 key를 다시 검사한다. [Claims: PG-C116] |

## `pg-durability-recovery` 제안

ordinary shared `LOCK/PROCLOCK` table과 backend-local `LOCALLOCK`은 startup에서 초기화되는 메모리 구조다. tuple의 XID/MultiXact row state와 prepared transaction lock ownership은 서로 다른 persistence protocol을 갖는다. [Claims: PG-C118, PG-C119, PG-C120]

tuple header에 기록된 XID/MultiXact는 page가 먼저 disk에 내려가도 ID가 crash 뒤 잘못 재사용되지 않도록 WAL coverage가 필요하고, updater를 포함할 수 있는 MultiXact 상태는 crash/restart를 넘어 보존되어야 한다. [Claims: PG-C118]

`PREPARE TRANSACTION`은 qualifying transaction-level heavyweight locks를 2PC record에 저장하고 startup recovery가 dummy PGPROC ownership으로 재획득한다. restart 뒤 의미 없는 VXID lock과 session-only lock은 record 대상에서 제외한다. [Claims: PG-C119]

### durability 경계 표

| 상태 | crash/restart 경계 | 근거가 허용하는 설명 |
|---|---|---|
| shared `LOCK/PROCLOCK` + fast-path strong-relation state [Claims: PG-C120] | startup이 shared memory table을 요청·초기화한다. [Claims: PG-C120] | 이 source trace만으로 서버 전체 shutdown process 순서나 shared-memory allocator 내부를 단정하지 않는다. [Claims: PG-C120] |
| backend-private `LOCALLOCK` [Claims: PG-C104, PG-C120] | 각 backend가 자신의 local hash를 별도로 초기화한다. [Claims: PG-C120] | persistent row ownership 형식이 아니다. [Claims: PG-C104, PG-C120] |
| tuple XID/MultiXact [Claims: PG-C002, PG-C118] | WAL/transaction-status 및 MultiXact persistence 경계가 필요하다. [Claims: PG-C118] | 이 claim만으로 WAL redo와 status storage 전체를 재구현할 수 없다. [Claims: PG-C118] |
| prepared heavyweight lock [Claims: PG-C119] | 2PC record에 저장하고 recovery가 dummy owner로 다시 잡는다. [Claims: PG-C119] | VXID/session-only lock은 제외하며 hot-standby replay 전체는 범위 밖이다. [Claims: PG-C119] |

## `pg-startup-shutdown` 제안

lock manager startup은 shared `LOCK/PROCLOCK` hash와 fast-path strong-relation data를 shared memory에 요청하고, 각 backend는 backend-private `LOCALLOCK` hash를 초기화한다. [Claims: PG-C120]

top-level transaction start는 자신의 VXID owner lock을 fast path에 먼저 설치한 뒤 ProcArray에 VXID를 공개한다. 이 owner-before-advertise 순서가 공개된 VXID에 owner lock이 없는 race를 막지만, ordinary account row conflict의 waiter가 VXID를 기다린다는 뜻은 아니다. [Claims: PG-C121, PG-C031]

top-level commit/abort는 outcome과 ProcArray 종료를 먼저 공개한 뒤 ResourceOwner lock phase에서 locks를 release한다. abort에서도 own VXID fast-path lock cleanup이 transaction end에 일어난다. [Claims: PG-C011, PG-C122]

subtransaction commit/abort와 prepared transaction은 다른 수명 규칙을 갖는다. 일반 subtransaction commit은 ownership을 parent로 넘기고 abort는 해당 owner lock을 개별 release하며, prepared lock은 2PC recovery owner가 이어받는다. [Claims: PG-C110, PG-C119]

### startup/cleanup 순서 표

| 경계 | source-confirmed 순서 | 명시적 제한 |
|---|---|---|
| process/shared startup [Claims: PG-C120] | shared lock tables 요청·초기화와 per-backend local hash 초기화를 분리한다. [Claims: PG-C120] | postmaster/worker 전체 startup choreography는 Unknown이다. [Claims: PG-C120] |
| top transaction begin [Claims: PG-C121] | VXID owner lock 설치 → ProcArray advertise [Claims: PG-C121] | ordinary tuple/FK/unique wait target으로 일반화하지 않는다. [Claims: PG-C121] |
| top commit [Claims: PG-C011, PG-C110] | outcome/ProcArray 종료 공개 → non-session standard lock release [Claims: PG-C011, PG-C110] | prepared lifecycle은 별도다. [Claims: PG-C011, PG-C119] |
| top abort [Claims: PG-C110, PG-C122] | abort outcome/ProcArray 종료 공개 → locks 및 own VXID cleanup [Claims: PG-C110, PG-C122] | server-wide orderly shutdown의 모든 worker 순서는 Unknown이다. [Claims: PG-C122] |
| subtransaction end [Claims: PG-C110] | commit은 parent ResourceOwner로 이동, abort는 해당 owner lock 개별 release [Claims: PG-C110] | advisory/session 및 prepared owner에는 별도 규칙이 있다. [Claims: PG-C110, PG-C119] |
| startup 2PC recovery [Claims: PG-C119] | qualifying transaction lock을 dummy PGPROC owner로 reacquire [Claims: PG-C119] | VXID/session-only locks는 record에서 제외한다. [Claims: PG-C119] |

## `pg-errors-pressure` 제안

row-lock caller는 `Block`, `Skip`, `Error` wait policy를 선택할 수 있으므로 `SKIP LOCKED`와 `NOWAIT` 성격을 무조건 queue wait로 합치면 안 된다. [Claims: PG-C112]

blocking path에서도 deadlock detection, lock timeout, cancel/die interrupt는 서로 다른 종료 원인이다. [Claims: PG-C107, PG-C108]

shared lock table allocation이 실패하면 acquisition은 out-of-shared-memory ERROR와 `max_locks_per_transaction` 조정 hint를 낼 수 있다. 이 GUC는 transaction별 hard cap이 아니라 backend 또는 prepared transaction당 예상 lockable object 수를 이용한 shared-table sizing assumption이다. [Claims: PG-C123]

### configuration/resource-pressure 표

| knob/event | 의미 | 오해 방지 |
|---|---|---|
| `deadlock_timeout` [Claims: PG-C107] | deadlock 검사 예약을 지연한다. [Claims: PG-C107] | lock wait 상한이 아니다. [Claims: PG-C107] |
| `lock_timeout` [Claims: PG-C107] | 0보다 크면 별도 lock wait timeout timer를 건다. [Claims: PG-C107] | exact runtime duration은 측정하지 않았다. [Claims: PG-C107] |
| `NOWAIT`/`SKIP LOCKED` 계열 [Claims: PG-C112] | row caller가 Error 또는 Skip wait policy를 선택한다. [Claims: PG-C112] | 모든 operation이 Block queue로 들어가지 않는다. [Claims: PG-C112] |
| deadlock ERROR [Claims: PG-C108] | 해결할 수 없는 hard/soft cycle에서 현재 transaction을 중단한다. [Claims: PG-C108] | SSI/buffer-pin/victim tie-break 전체 설명이 아니다. [Claims: PG-C108] |
| shared lock OOM [Claims: PG-C123] | lock table allocation 실패와 sizing hint를 낼 수 있다. [Claims: PG-C123] | `max_locks_per_transaction`은 transaction별 hard lock 수 제한이 아니다. [Claims: PG-C123] |

## `pg-performance-observability` 제안

이미 보유한 lock은 backend-local refcount만 증가시킬 수 있고, weak relation lock과 VXID owner lock fast path는 자주 획득하지만 드물게 충돌하는 요청이 shared partition을 경합시키는 비용을 줄이도록 설계되었다. strong conflicting relation request가 오면 관련 fast-path lock을 main table로 옮긴다. [Claims: PG-C104, PG-C105, PG-C125]

정상 row ownership을 tuple header XMAX/MultiXact에 두는 설계는 row마다 transaction-lifetime heavyweight tuple holder entry를 요구하지 않는다. 그러나 이 source fact만으로 CUBRID보다 메모리·처리량이 낫다고 결론낼 수 없다. [Claims: PG-C002]

`pg_locks`는 heavyweight와 predicate lock 상태를, `pg_blocking_pids`는 conflicting holder와 앞선 conflicting waiter를 blocker로 노출하며, long wait와 acquisition failure logging은 GUC로 제어된다. tuple header XMAX/MultiXact의 모든 logical row lock이 독립 tuple row로 보이는 것은 아니다. [Claims: PG-C124]

### 성능/관측 표

| 축 | source-confirmed 사실 | 미측정/한계 |
|---|---|---|
| local reacquire [Claims: PG-C104, PG-C105] | 같은 backend의 repeat acquire는 local count만 증가시킬 수 있다. [Claims: PG-C104, PG-C105] | workload별 절감량은 미측정이다. [Claims: PG-C105] |
| fast path [Claims: PG-C125] | weak relation/VXID owner lock의 shared partition contention을 줄이고 strong request 시 materialize한다. [Claims: PG-C125] | throughput, cache miss, CUBRID 대비 성능은 미측정이다. [Claims: PG-C125] |
| lock table sizing [Claims: PG-C123] | 예상 lockable object 수로 shared table 크기를 산정하고 allocation failure를 보고한다. [Claims: PG-C123] | 정확한 memory bytes나 transaction별 hard cap으로 읽지 않는다. [Claims: PG-C123] |
| `pg_locks` [Claims: PG-C124] | heavyweight/predicate lock snapshot을 노출한다. [Claims: PG-C124] | 관측 race, fast-path 표현 차이, tuple header row lock 누락 범위가 있다. [Claims: PG-C124] |
| blocker/logging [Claims: PG-C124] | `pg_blocking_pids`와 wait/failure logging GUC가 blocker와 long-wait 진단을 돕는다. [Claims: PG-C124] | 이 report는 PostgreSQL runtime 출력을 검증하지 않았다. [Claims: PG-C124] |

## `pg-self-lock-boundary` 제안

### 먼저 제시할 결론

PostgreSQL에는 CUBRID MVCCID self-lock과 동일한 하나의 subsystem이 없다. XID completion, VXID publication, speculative decision이 서로 다른 resource와 caller를 갖고, normal row ownership은 tuple XMAX/MultiXact 및 transient tuple arbitration에 남는다. [Claims: PG-C002, PG-C030, PG-C031, PG-C126, PG-C127, PG-C128]

### analogy 경계 표

| PostgreSQL 후보 | 닮은 불변식 | 결정적 차이 | 분류 |
|---|---|---|---|
| XID transaction tag [Claims: PG-C030, PG-C126] | writer가 자신의 XID에 X를 잡고 observer가 S로 completion을 기다린 뒤 running/tuple/index 상태를 재검사한다. [Claims: PG-C030, PG-C126] | row identity와 compatibility는 tuple XMAX/MultiXact에 남고, CUBRID의 specific appended-row lock substitution 조건과 같은 Interface가 아니다. [Claims: CUBRID-C030, CUBRID-C031, CUBRID-C033, PG-C002, PG-C030, PG-C128] | `partial analogy` [Claims: CMP-C030] |
| VXID tag [Claims: PG-C031, PG-C121] | owner lock을 ProcArray publication 전에 준비한다. [Claims: PG-C121] | ordinary heap tuple update, FK, unique conflict의 waiter target이 아니다. [Claims: PG-C031, PG-C121] | `partial analogy`, publication ordering에 한정 [Claims: CMP-C030] |
| speculative XID+token [Claims: PG-C031, PG-C127] | confirmed/dead 판정을 먼저 게시하고 release/wakeup 뒤 조건을 재검사한다. [Claims: PG-C127] | `ON CONFLICT` tentative insertion 한 건에 한정되고 ordinary transaction 또는 모든 appended row를 대표하지 않는다. [Claims: PG-C031, PG-C127] | `partial analogy`, decision protocol에 한정 [Claims: CMP-C030] |
| 위 셋을 합친 “PG self-lock” [Claims: PG-C128] | unfinished writer completion을 기다리고 caller state를 재검사하는 책임은 분산되어 존재한다. [Claims: PG-C030, PG-C031, PG-C126, PG-C127, PG-C128] | appended-row per-row-X 생략과 unique/FK observer S-wait를 하나의 transaction resource Interface로 결합한 단일 mechanism은 조사 범위에서 없다. [Claims: CUBRID-C030, CUBRID-C031, CUBRID-C032, CUBRID-C033, PG-C128] | `no equivalent` [Claims: PG-C128, CMP-C030] |

### XID waiter 세부 순서

`XactLockTableWait`는 XID tag에 S를 획득했다가 즉시 풀고 running status를 다시 검사한다. subtransaction XID owner lock이 이미 사라졌다면 topmost parent XID로 반복하고, ProcArray가 owner lock registration보다 먼저 보이는 드문 race는 짧은 retry로 처리한다. [Claims: PG-C030, PG-C126]

이것은 “XID lock 하나가 row X lock을 승격해 보유한다”는 뜻이 아니다. 어떤 row/mode가 충돌했는지는 tuple header와 index 상태가 보유하고, XID resource는 완료시점 rendezvous를 제공한다. [Claims: PG-C002, PG-C030, PG-C126]

### 강한 negative search 기록

아래 검색 기록은 `PG-C128`의 범위를 설명하기 위한 것이며 다른 revision/extension을 부정하지 않는다. [Claims: PG-C128]

- searched areas: `src/backend/storage/lmgr`, `src/include/storage`, `src/backend/access/heap`, `src/backend/access/nbtree`, `src/backend/executor`, `src/backend/utils/adt/ri_triggers.c`, `src/test/isolation/specs`. [Claims: PG-C128]
- alternate terms: `self[-_ ]?lock`, `selflock`, `mvccid`, `transaction[-_ ]self`, `xid[-_ ]self`, `omit.*(row|tuple).*lock`, `replace.*(row|tuple).*lock`, `append(ed)?.*(self|transaction).*(lock)`, `per[-_ ]row.*(self|xid).*lock`; exact self-lock/substitution matches는 없었다. [Claims: PG-C128]
- rendezvous inventory: `XactLockTableInsert/Delete/Wait`, `ConditionalXactLockTableWait`, `VirtualXactLockTableInsert/Cleanup`, `VirtualXactLock`, `SpeculativeInsertionLockAcquire/Release/Wait`, transaction/VXID/speculative tag setters와 caller를 inventory했다. [Claims: PG-C128]
- normal hierarchy/escalation terms: `intent(ion)?[- ]lock`, `multi[- ]gran`, `lock[-_ ]escalat`, `escalat(e|ion|ing).*lock`, `lock.*escalat`는 normal heavyweight/tuple scope에서 match가 없었다. [Claims: PG-C002, PG-C128]
- contradiction boundary: Serializable SIREAD predicate-lock subsystem에는 tuple/page/table promotion이 있으므로 “PostgreSQL 전체에 escalation이 없다”라고 쓰지 않는다. [Claims: PG-C002]
- `HeapTupleSatisfiesSelf`, `TM_SelfModified`, “found self tuple”은 visibility 또는 같은 command/transaction tuple 상태의 `self`이므로 CUBRID식 self-lock positive evidence로 세지 않는다. [Claims: PG-C128]

## `pg-invariants-limits` 제안

### 불변식·금지된 해석 표

| 불변식/경계 | 장에 넣을 문장 |
|---|---|
| grant-before-wakeup [Claims: PG-C011, PG-C109] | waiter latch를 깨우기 전에 shared lock state에서 grant가 완료되어야 한다. [Claims: PG-C011, PG-C109] |
| outcome-before-release [Claims: PG-C011, PG-C122] | top-level commit/abort outcome과 ProcArray 종료를 공개한 뒤 transaction locks를 release한다. [Claims: PG-C011, PG-C122] |
| release-before-wait, recheck-after-wake [Claims: PG-C113, PG-C117] | heap row path는 buffer lock을, unique path는 leaf buffer를 놓고 기다리며, 돌아온 뒤 XMAX 또는 B-tree 조건을 다시 검사한다. [Claims: PG-C113, PG-C117] |
| visibility ≠ writer coordination [Claims: PG-C111, PG-C113, CMP-C020] | snapshot old-version read가 nonblocking이어도 locked read/DML/constraint correctness에는 별도 coordination이 필요하다. [Claims: PG-C111, PG-C113, PG-C116, PG-C117, CMP-C020] |
| tuple arbitration ≠ durable row owner [Claims: PG-C002, PG-C113] | transient tuple tag를 transaction-lifetime row ownership과 동일시하지 않는다. [Claims: PG-C002, PG-C113] |
| XID rendezvous ≠ CUBRID self-lock equivalent [Claims: PG-C030, PG-C128, CMP-C030] | completion wait 모양은 닮았지만 row compatibility와 appended-row substitution 전체 Interface는 동일하지 않다. [Claims: CUBRID-C030, CUBRID-C031, CUBRID-C033, PG-C002, PG-C030, PG-C128, CMP-C030] |
| two timers [Claims: PG-C107] | `deadlock_timeout`과 `lock_timeout`의 목적을 합치지 않는다. [Claims: PG-C107] |
| runtime 미실행 [Claims: PG-C107, PG-C124, PG-C125] | 실제 blocking duration, 관측 view row 조합, error timing, throughput·memory 우열은 source-only 장에서 측정 사실로 제시하지 않는다. [Claims: PG-C107, PG-C124, PG-C125] |
| startup/shutdown 한계 [Claims: PG-C120, PG-C122] | shared/local lock initialization과 transaction cleanup은 traced지만 server-wide worker shutdown 순서는 Unknown으로 남긴다. [Claims: PG-C120, PG-C122] |
| broader SSI 한계 [Claims: PG-C002, PG-C111] | normal blocking lock의 음성 결론을 Serializable predicate-lock promotion/SSI 전체에 확장하지 않는다. [Claims: PG-C002, PG-C111] |

### 명시적 Unknown/non-applicable

- PostgreSQL runtime은 scope에서 제외되어 account 시나리오의 실제 대기 길이, `pg_locks` snapshot, SQL error message/timing은 검증하지 않았다. [Claims: PG-C107, PG-C124]
- full Serializable SSI/predicate-lock algorithm과 모든 serialization anomaly는 이 장의 범위 밖이다. [Claims: PG-C002, PG-C111]
- MultiXact member-by-member wake와 SLRU recovery, WAL redo 전체는 이 장의 interface claim보다 넓으므로 재구현 수준으로 주장하지 않는다. [Claims: PG-C118]
- prepared transaction과 hot standby의 모든 lock replay 조합은 미완전 추적이며, 2PC qualifying lock save/recover와 VXID/session exclusion까지만 source-confirmed다. [Claims: PG-C119]
- server-wide orderly shutdown의 postmaster/worker 순서는 미추적이며 transaction cleanup과 같다고 가정하지 않는다. [Claims: PG-C120, PG-C122]
- extension-defined advisory/custom lock protocol은 no-equivalent negative search 대상이 아니다. [Claims: PG-C128]
- source-confirmed fast-path 목적을 CUBRID 대비 throughput/memory superiority로 바꾸지 않는다. [Claims: PG-C125]

## `pg-recap` 제안

복습 문단은 다음 네 문장을 claim badge와 함께 회수한다.

1. PostgreSQL은 relation·tuple·XID·VXID·speculative token에 책임을 분리하며 CUBRID class/instance hierarchy와 Interface가 동일하지 않다. [Claims: PG-C001, PG-C002, PG-C101, PG-C128, CMP-C001]
2. conflict queue, delayed deadlock check, grant-before-wakeup, outcome-before-release라는 추상 lifecycle은 비교 가능하지만 graph와 victim/timeout 정책은 partial analogy다. [Claims: PG-C010, PG-C011, PG-C106, PG-C107, PG-C108, PG-C109, CMP-C010]
3. snapshot read는 old version을 읽을 수 있어도 locked read, update, unique/FK correctness에는 tuple/XID/index coordination과 wakeup 뒤 recheck가 필요하다. [Claims: PG-C020, PG-C021, PG-C111, PG-C113, PG-C115, PG-C116, PG-C117, CMP-C020]
4. CUBRID MVCCID self-lock에 가장 가까운 PostgreSQL 책임은 XID completion, VXID publication, speculative decision으로 나뉘며 전체 self-lock Interface의 단일 equivalent는 없다. [Claims: CUBRID-C030, CUBRID-C031, CUBRID-C032, CUBRID-C033, PG-C030, PG-C031, PG-C121, PG-C126, PG-C127, PG-C128, CMP-C030]

전환 문장은 사실 단정 대신 질문으로 끝낸다: “다음 장에서는 MySQL server의 metadata lock과 InnoDB의 table/record/transaction wait가 같은 account 시나리오의 책임을 어떻게 다시 나누는지 확인한다.”

## 추가 claim 통합 지침

`postgresql-added-claims.jsonl`은 `PG-C101`부터 `PG-C128`까지 28개 one-line JSON object를 담는다. 각 object에는 pinned revision, exact symbol/range, file SHA-256, `COMMIT` evidence state, Korean limitation, 제안 anchor가 있다. 이 ID들은 현재 `evidence/claims.jsonl`의 ID와 충돌하지 않는다.

main agent는 다음 순서로 통합해야 한다.

1. 각 source ref의 hash와 exact line range를 다시 verifier로 통과시킨다.
2. 승인한 claim만 중앙 ledger에 병합한다.
3. 실제 Book의 section/table/cell/pseudocode/diagram에 `data-claim-id`와 visible claim badge를 붙인다.
4. central behavior mapping과 `report.json` locations를 실제 anchor에 맞춰 main writer가 갱신한다.
5. HTML validator, offline asset scan, visible Korean claim scan을 다시 실행한다.

## 추가 claim 축 요약

| 축 | 추가 claim |
|---|---|
| resource/mode | `PG-C101`–`PG-C103` |
| ownership/lifetime | `PG-C104`, `PG-C110`, `PG-C119` |
| acquire/wait/deadlock/release | `PG-C105`–`PG-C110` |
| MVCC operation policy | `PG-C111`–`PG-C117` |
| durability/recovery | `PG-C118`, `PG-C119` |
| startup/transaction cleanup | `PG-C120`–`PG-C122` |
| errors/resource pressure | `PG-C107`, `PG-C108`, `PG-C112`, `PG-C123` |
| performance/observability | `PG-C104`, `PG-C105`, `PG-C123`–`PG-C125` |
| self-lock analogy boundary | `PG-C121`, `PG-C126`–`PG-C128` |

