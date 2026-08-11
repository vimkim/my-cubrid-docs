# Pedagogy Research Packet

## Metadata

- **Role:** Role 5 — Pedagogy Architect
- **Topic:** CUBRID `lock`과 Lock Manager, 특히 self-lock과 MVCC 경로에서 logical lock이 필요한 이유
- **Declared Scope:** `research/scope.md`
- **Scope digest:** `711d1a0f5bfebdbe1b55b4299973efc353d90636e2f00fc807f51d031766a839`
- **CUBRID revision:** `/home/vimkim/gh/cb/cubrid-analysis` @ `f30f1c26003e5aa8e93182648e06cad76fc77064` (`WORKTREE`; 정확한 dirty provenance는 `provenance.json` 기준)
- **PostgreSQL revision:** `/home/vimkim/gh/pg/postgres` @ `fd2b89854d93d70fe8c9a69d5b8fafd5b9302cfc`
- **MySQL revision:** `/home/vimkim/gh/mysql/mysql-server` @ `06a5c1c99c377fc41b2eba1ea244e8b220bdc3c8`
- **Timestamp:** `2026-08-11T17:37:16+09:00`
- **Audience:** C/C++, 자료구조, 운영체제의 mutex, SQL transaction과 isolation level을 배웠지만 DBMS 내부 잠금은 처음인 컴퓨터공학 2학년
- **Read-only inputs:** 동결된 `research/scope.md`, Korean HTML Book Contract, Research/Evidence Contract, Quiz/Live Grill Contract, 관련 로컬 CUBRID 학습자료

## 1. 교육적 핵심 진단

이 책의 가장 큰 난점은 lock mode의 수가 많다는 데 있지 않다. 같은 `lock`이라는 단어 아래에 보호 대상, owner, lifetime, wait protocol이 전혀 다른 메커니즘이 섞인다는 데 있다.

초급자는 보통 다음과 같은 한 줄 모델로 시작한다.

> MVCC는 reader가 lock을 잡지 않게 하므로 Lock Manager가 거의 필요 없다.

책은 이 모델을 곧바로 부정하기보다 네 단계로 정교화해야 한다.

1. mutex와 latch는 짧은 물리 상태를 보호한다.
2. transaction lock은 logical resource에 대한 transaction 사이의 충돌을 조정한다.
3. MVCC visibility는 어떤 row version을 볼지 결정하지만 DDL, writer-writer 충돌, locked read, unique/FK 판정까지 대신하지 않는다.
4. CUBRID MVCCID self-lock은 일반 row lock mode가 아니라 inserter 종료를 알리는 transaction-resource rendezvous다.

독자가 끝까지 반복해서 사용할 분석 틀은 다음 일곱 칸으로 고정하는 편이 좋다.

```text
(보호하려는 상태, resource key, mode, owner, observer/waiter, lifetime, wakeup 뒤 recheck)
```

기존의 `(resource, mode, owner)`만으로는 self-lock의 필요성을 설명하기 어렵다. `observer/waiter`와 `recheck`가 들어가야 “누가 왜 기다리는가”가 완성된다.

## 2. Concept Ladder

새 개념은 아래 순서로만 도입한다. 뒤 단계의 용어를 앞 단계 결론의 근거로 사용하지 않는다.

### Level 0 — 동시 실행이 깨뜨릴 수 있는 상태

- 하나의 메모리 구조를 두 thread가 동시에 고치는 장면
- 하나의 logical row를 두 transaction이 서로 다른 결론으로 바꾸려는 장면
- 한 transaction이 만든 아직 미확정 version을 다른 transaction이 발견하는 장면
- 핵심 질문: “동시에 실행되었다”가 아니라 “어떤 잘못된 결과가 가능해지는가?”

### Level 1 — mutex, latch, transaction lock 분리

- protected state: in-memory structure / page structure / logical database object
- owner: thread·execution context / thread·page access / transaction
- lifetime: critical section / page access / transaction protocol
- failure if misused: memory corruption / unstable page view / logical anomaly or indefinite wait

### Level 2 — Lock Manager의 최소 모델

- resource identity와 mode를 분리한다.
- holder와 waiter를 분리한다.
- compatibility가 grant와 wait를 결정한다.
- wakeup은 업무 조건의 성립이 아니라 recheck 기회다.

### Level 3 — multi-granularity hierarchy

- database, class, instance, transaction resource를 같은 key namespace라고 가정하지 않는다.
- class intention mode는 instance lock을 대체하지 않는다.
- conversion은 새 owner의 최초 acquire와 다르다.
- escalation은 mode conversion과 같은 말이 아니다.

### Level 4 — lifecycle와 실패

- request → lookup/create → grant 또는 wait → wakeup/retry → release를 한 흐름으로 본다.
- timeout, interrupt, deadlock victim, transaction abort를 서로 다른 종료 이유로 구분한다.
- resource entry, holder/waiter entry, transaction hold list의 reclamation을 호출 결과와 함께 추적한다.

### Level 5 — MVCC visibility와 logical lock의 역할 분담

- plain snapshot read의 질문은 “어떤 version이 보이는가?”다.
- locked read와 DML의 질문은 “누가 변경 권리를 갖고 있는가?”를 포함한다.
- unique/FK 검사의 질문은 “아직 끝나지 않은 transaction의 결과를 지금 확정해도 되는가?”를 포함한다.
- 따라서 “MVCC이면 lock이 없다”와 “MVCC이면 모든 read가 lock을 잡는다”를 모두 버린다.

### Level 6 — MVCCID self-lock rendezvous

- inserter identity가 observer에게 보이는 조건을 먼저 설명한다.
- 같은 MVCCID resource에서 inserter의 holder와 observer의 waiter가 만나는 모델을 소개한다.
- `self`는 자기 자신을 정지시킨다는 뜻이 아니다.
- per-row lock을 transaction-keyed rendezvous로 대신할 수 있는 범위와 조건을 설명한다.
- `inactive publication → unlock → wakeup/recheck` 순서는 반드시 counterexample과 함께 가르친다. 정확한 publication 함수와 happens-before는 CUBRID Claims가 입증해야 한다.

### Level 7 — 세 DBMS의 responsibility placement

- 이름이 아니라 shared scenario의 책임 흐름을 비교한다.
- relation/table/class, tuple/record/instance, transaction identity를 따로 배치한다.
- 모든 mapping은 `equivalent`, `partial analogy`, `no equivalent` 가운데 하나와 semantic gap을 함께 갖는다.

### Level 8 — 재구현

- 독자가 source를 다시 열지 않고 Interface, data model, total transition, error, cleanup, ordering, tests를 말할 수 있어야 한다.
- central unknown 하나라도 correctness protocol에 남으면 `READY WITHIN DECLARED SCOPE`를 선언할 수 없다.

## 3. 첫 등장 전에 잠가야 할 용어와 표현

| 용어 또는 표현 | 첫 정의에 반드시 포함할 것 | 피해야 할 오해 | Evidence 역할이 고정할 것 |
|---|---|---|---|
| lock | 이 책에서 generic word인지 CUBRID transaction lock인지 매번 범위를 밝힌다. | mutex, latch, transaction lock을 서로 대체 가능하다고 읽는다. | 해당 문단이 부르는 구체 API와 protected state |
| mutex | 짧은 in-memory critical section을 execution thread 사이에서 조정한다. | SQL transaction commit까지 유지되는 logical lock이다. | CUBRID Lock Manager 내부 mutex의 실제 보호 필드 |
| latch | page나 내부 물리 구조를 안정화하는 짧은 동기화다. | row 접근 권한 또는 isolation guarantee를 제공한다. | wait 전 release와 wakeup 후 reacquire가 필요한 정확한 latch |
| transaction lock | logical resource의 충돌을 transaction 단위로 조정한다. | 모든 mode가 항상 commit까지 유지된다는 일반 법칙이다. | mode별 release/partial-release 규칙 |
| MVCC visibility | snapshot과 row header 정보를 이용해 읽을 version을 고르는 정책이다. | lock mode 또는 mutex의 한 종류다. | CUBRID의 실제 visibility caller와 결과 |
| “MVCC lock” | 고유 enum mode가 아니라 MVCC 실행 경로가 class/instance/transaction lock을 선택하는 정책이라는 scope 용어다. | `MVCC_LOCK` 같은 단일 mode가 존재한다. | 실제 mode 선택 표와 호출 경로 |
| self-lock | inserter가 자기 MVCCID를 key로 한 resource에 보유하는 rendezvous용 lock이다. | 자기 transaction이 자기 자신을 block하거나 self-deadlock한다. | holder mode, waiter mode, owner, release path |
| resource key | resource type과 type별 identity를 합쳐 “무엇에 대한 lock인가”를 정한다. | mode가 같으면 같은 lock이다. | key layout, equality, hash, alternate namespace |
| mode | resource를 어떤 방식으로 사용하려는지 나타낸다. | mode 이름만으로 resource와 owner를 알 수 있다. | complete compatibility/conversion table |
| owner | grant된 entry와 release 책임을 가진 transaction identity다. | 현재 CPU thread, client connection, SQL session과 항상 같다. | `tran_index`, TRANID, MVCCID의 exact relation/lifetime |
| holder / waiter / observer | grant 보유자 / compatibility 충돌로 기다리는 요청자 / 업무 상태를 발견하고 protocol을 시작한 caller다. | observer는 항상 Lock Manager waiter가 된다. | observer가 wait를 생략하는 분기와 waiter 전환 지점 |
| class / instance | CUBRID의 table 수준 object / row 수준 object를 가리키는 문맥 용어다. | C++ class와 object를 뜻한다. | OID 구성과 resource type |
| intention mode | 하위 instance lock의 존재 또는 의도를 class 수준 충돌 검사에 알린다. | row lock을 자동으로 대신한다. | mode별 caller obligation과 hierarchy invariant |
| conversion | 같은 owner의 held mode를 다른 mode로 바꾸는 요청이다. | 새 owner의 최초 acquire 또는 escalation과 같다. | compatible upgrade, wait, demotion, failure branches |
| escalation | 다수의 세립도 lock을 더 큰 granularity lock으로 대체하는 정책이다. | 단순히 `S → X` conversion을 뜻한다. | threshold, trigger, release/order, 실패 시 fallback |
| wait / wakeup / recheck | 충돌로 suspend하고 상태 변화로 깨어난 뒤 업무 조건을 다시 확인한다. | wakeup이 grant 또는 unique/FK 결과를 보증한다. | wake reason, queue transition, exact recheck predicate |
| timeout / deadlock / interrupt | 시간 제한 / cycle resolution / 외부 취소라는 서로 다른 실패 원인이다. | 모두 “오래 기다려 실패”로 합칠 수 있다. | error propagation, victim/cleanup ownership |
| `tran_index` / TRANID / MVCCID | 각각 runtime transaction lookup, transaction identity, MVCC version ownership에서 쓰는 identity로 나누어 소개한다. | 같은 숫자의 다른 이름이거나 영구 ID다. | allocation, reuse, width, validity, lifetime |
| INSID | row/version에서 inserter를 가리키는 표식이라는 최소 모델로 시작한다. | 모든 row가 항상 가지고 모든 reader가 검사한다. | record conditions, producer/consumer call paths |
| active / inactive | MVCCID가 아직 완료되지 않았는지를 나타내는 protocol state다. | SQL connection이 살아 있다는 뜻이다. | publication mechanism, memory ordering, main/subtransaction ordering |
| lock-free에 가깝다 | transaction lock wait를 줄이는 특정 read path를 뜻한다. | latch, atomic, memory access, 모든 logical lock이 없다. | 해당 read path의 실제 lock/latch behavior |
| row lock | logical row/instance 충돌을 조정하는 용어로 쓰고 physical tuple header와 구분한다. | 세 DBMS가 같은 in-memory entry를 사용한다. | CUBRID/PG/InnoDB별 representation |
| crash / abort / shutdown | process failure / transaction rollback / controlled service termination을 따로 쓴다. | deadlock victim abort와 process crash가 같다. | 각 경계의 volatile/durable cleanup |

추가 언어 규칙은 다음과 같다.

- `read lock이 없다`라고 쓰지 말고 “이 source-confirmed path에서는 어떤 transaction lock 요청을 하지 않는다”라고 쓴다.
- `lock을 건다`보다 `resource R에 mode M을 owner T가 요청한다`를 우선한다.
- `기다린다` 뒤에는 반드시 “누가, 어느 resource에서, 누구의 어떤 종료를, 무엇을 놓은 상태로 기다리는가”를 붙인다.
- `commit하면 풀린다` 뒤에는 정확한 inactive publication, unlock, wakeup, recheck 순서와 abort/subtransaction 변형을 붙인다.
- `self-lock이 row lock을 줄인다`는 성능 문장에는 대체되는 row-lock 조건, 남는 class/row lock, resource 개수 근거가 필요하다.

## 4. 제안 Chapter Map

`index.html`은 요약문이 아니라 읽기 지도로 사용한다. 처음 배우는 독자는 01→14 순서로 읽는다. Lock Manager 구현을 아는 독자는 03→06→07→08→13→14 경로를 선택할 수 있다.

### 01. 왜 MVCC에도 Lock Manager가 필요한가 — 방향과 공통 시나리오

- **학습 질문:** T1이 update와 unique insert를 끝내지 않았을 때 T2의 plain `SELECT`, `SELECT ... FOR UPDATE`, `UPDATE`, 중복 `INSERT`는 왜 같은 방식으로 행동하지 않는가?
- **내용:** Declared Scope, 네 Central Behavior, 18 Coverage Obligation, exact revisions, dirty provenance, evidence label, shared `account` scenario, 제외 범위, 세 읽기 경로.
- **시각화:** T1/T2의 네 동작을 나란히 둔 전체 지도. 아직 결과를 정답처럼 쓰지 않고 “visibility 판단”, “변경 권리”, “constraint 확정”이라는 질문을 붙인다.
- **보이는 한국어 대체 설명:** “T1은 기존 행을 바꾸고 새 unique key를 삽입한 채 종료하지 않았다. T2의 일반 조회는 보이는 version을 묻는다. locked read와 update는 변경 권리를 묻는다. 중복 insert는 T1 결과가 확정됐는지를 묻는다. 책은 네 질문이 어떤 CUBRID resource와 wait로 이어지는지 추적한다.”
- **Recap 질문:** “MVCC가 대신하는 질문과 대신하지 않는 질문을 한 문장씩 말해 보라.”
- **Transition:** “서로 다른 질문이 왜 서로 다른 동기화 도구를 요구하는지부터 분리한다.”
- **Obligations:** `orientation`, `teaching-map`

### 02. 같은 단어, 다른 보호 대상 — mutex, latch, transaction lock, MVCC visibility

- **학습 질문:** page의 slot array를 바꾸는 동안의 보호와 row update 권리를 transaction 종료까지 조정하는 보호는 왜 다를까?
- **내용:** protected state, owner, lifetime, wait style, failure type을 기준으로 네 개념을 분리한다. 비유를 사용한 직후 비유의 중단점을 밝힌다.
- **시각화:** 네 lane timeline. mutex/latch의 짧은 구간과 transaction lock의 긴 lifetime을 보인다. MVCC visibility는 lock bar가 아니라 version-selection decision으로 그린다.
- **보이는 한국어 대체 설명:** “mutex와 latch는 내부 구조를 사용하는 짧은 구간을 안정화한다. transaction lock은 logical resource 충돌을 transaction protocol 동안 조정한다. MVCC visibility는 reader가 볼 version을 고른다. 네 역할은 겹칠 수 있지만 서로 대체되지 않는다.”
- **Recap 질문:** “page latch를 commit까지 들고 있거나 transaction lock을 page access 동안만 들면 각각 무엇이 잘못될 수 있는가?”
- **Transition:** “transaction lock 하나를 identity와 state로 분해한다.”
- **Obligations:** `mental-model`, `concurrency`

### 03. Lock Manager Interface와 resource identity

- **권장 파일/anchor:** `chapters/03-interface-and-resources.html#resource-mode-hierarchy`
- **학습 질문:** 둘 다 `X_LOCK`인데 object lock과 MVCCID self-lock이 왜 다른 resource인가?
- **내용:** 외부 caller obligation, resource type/key, lookup, mode, owner, conditional/wait policy, result/error, dependency seam. 최소 S/X 표에서 시작해 source-confirmed full compatibility 표로 확장한다.
- **시각화:** 요청 카드 `(state, key, mode, owner, waiter, lifetime, recheck)`와 resource namespace map.
- **보이는 한국어 대체 설명:** “요청의 mode가 같아도 resource type과 key가 다르면 충돌하지 않는다. 같은 key를 가리키는 요청들만 compatibility 검사의 대상이 된다. caller는 transaction context, class OID, mode, wait 조건을 올바르게 전달해야 한다.”
- **Recap 질문:** “object `X_LOCK`과 MVCCID `X_LOCK`을 일곱 칸으로 각각 적어 차이를 설명하라.”
- **Transition:** “key를 찾은 뒤 누가 resource와 holder/waiter entry를 만들고 회수하는지 본다.”
- **Central Behavior:** `resource-mode-hierarchy`
- **Obligations:** `scope-interface-seams`, `mental-model`, `policies-algorithms`

### 04. data ownership와 lifetime — resource, holder, waiter, hold list

- **학습 질문:** 한 lock request가 끝나도 resource entry가 남을 수 있는가? transaction 종료 때 무엇을 찾아 해제하는가?
- **내용:** core structures와 identity, allocation, owner, lookup key, transaction hold list, resource holder/waiter chains, reclamation, protected mutable fields, volatile/persistent 구분의 씨앗.
- **시각화:** ownership graph. 실선은 ownership, 화살표는 lookup, 점선은 backlink를 나타낸다. 범례를 text로도 적는다.
- **보이는 한국어 대체 설명:** “hash table은 resource key로 resource entry를 찾는다. resource는 holder와 waiter를 연결한다. transaction은 자기 hold list를 통해 종료 시 보유 entry를 찾는다. 각 allocation과 reclamation 시점 및 이를 보호하는 mutex는 Claims로 고정한다.”
- **Recap 질문:** “resource entry와 transaction hold entry가 서로 다른 이유를 release 비용과 lookup 방향으로 설명하라.”
- **Transition:** “정적인 구조를 request부터 conversion과 escalation까지 움직여 본다.”
- **Central Behavior:** `resource-mode-hierarchy`
- **Obligations:** `data-ownership-lifetime`, `scope-interface-seams`

### 05. acquire, conversion, hierarchy, escalation

- **학습 질문:** class intention mode와 instance mode는 어떻게 함께 grant되며, 이미 가진 mode를 바꾸거나 많은 row lock을 합칠 때 어떤 순서가 필요한가?
- **내용:** fast hit, resource miss/allocation, compatibility, same-owner request, conversion, class/instance hierarchy, escalation trigger와 fallback, conditional request, complete pseudocode branches.
- **시각화:** fast/slow decision tree, class→instance tree, compatibility matrix, conversion/escalation 전후 표.
- **보이는 한국어 대체 설명:** “caller가 class와 instance에 필요한 mode를 준비한다. 기존 holder와 호환되면 grant된다. 충돌하면 wait path로 간다. 같은 owner의 mode 변경과 여러 instance lock의 escalation은 서로 다른 정책이며 정확한 순서와 실패 처리는 source Claims가 정한다.”
- **Recap 질문:** “conversion과 escalation을 입력, 바뀌는 resource 수, 실패 후 상태로 구분하라.”
- **Transition:** “호환되지 않는 요청이 실제 waiter가 된 뒤의 lifecycle을 추적한다.”
- **Central Behavior:** `resource-mode-hierarchy`
- **Obligations:** `core-workflows`, `lifecycle-state-machines`, `policies-algorithms`, `performance-observability`

### 06. wait, deadlock, timeout, interrupt, release

- **권장 파일/anchor:** `chapters/06-wait-deadlock-release.html#wait-deadlock-release`
- **학습 질문:** incompatible request는 어떤 상태로 잠들고 holder가 commit/abort하거나 deadlock victim이 정해지면 어떻게 빠져나오는가?
- **내용:** queue insertion, wait-for dependency, suspend/wakeup, retry/recheck, conversion waiter, timeout, interrupt, victim handling, transaction `lock_unlock_all`, partial release, abort/shutdown cleanup. wait-for graph 전체 최적화는 범위 밖으로 표시한다.
- **시각화:** request state machine과 T1/T2 sequence. 별도 표에 state before/after, held internal mutex/latch, mutation, error, cleanup, Claim ID를 넣는다.
- **보이는 한국어 대체 설명:** “T2의 요청이 T1 holder와 충돌하면 waiter가 된다. wait-for 관계가 기록되는 정확한 시점은 source가 정한다. holder release, timeout, interrupt, deadlock resolution 가운데 하나가 wait를 끝낸다. T2는 wake reason을 처리하고 grant 또는 업무 조건을 다시 확인한다. 실패한 waiter와 빈 resource의 reclamation도 이 흐름에 포함된다.”
- **Recap 질문:** “deadlock victim과 lock timeout을 detection, error, cleanup 주체로 구분하라.”
- **Transition:** “이제 MVCC가 들어오면 어떤 request 자체가 줄고 어떤 request는 남는지 본다.”
- **Central Behavior:** `wait-deadlock-release`
- **Obligations:** `lifecycle-state-machines`, `core-workflows`, `concurrency`, `errors-resource-pressure`

### 07. “MVCC lock”은 mode가 아니다 — visibility와 class/row lock 정책

- **권장 파일/anchor:** `chapters/07-mvcc-lock-policy.html#mvcc-lock-policy`
- **학습 질문:** 같은 row를 대상으로 plain snapshot `SELECT`, `SELECT ... FOR UPDATE`, `UPDATE`, `DELETE`, `INSERT`가 왜 서로 다른 lock policy를 선택하는가?
- **내용:** visibility, logical lock, page latch의 responsibility table. query executor→scan→locator/heap/B-tree→Lock Manager seam을 shared scenario 네 동작에 맞춘다. non-MVCC class, write-write conflict, predicate recheck, unique/FK branch는 source-confirmed 범위만 쓴다.
- **시각화:** SQL operation × responsibility decision matrix와 네 workflow swimlane.
- **보이는 한국어 대체 설명:** “plain snapshot read는 보이는 version을 선택하는 경로가 중심이다. locked read와 DML은 logical 변경 충돌을 조정하는 class/instance lock을 추가로 요구할 수 있다. unique/FK 검사는 미완료 inserter의 결과를 확정하기 전에 기다리는 별도 protocol을 사용할 수 있다. 실제 mode와 호출 여부는 isolation, class type, scan path별 Claims에 묶는다.”
- **Recap 질문:** “MVCC visibility가 해결하는 race와 row/class lock이 해결하는 race를 각각 하나씩 들어라.”
- **Transition:** “unique/FK observer가 unfinished inserter를 만날 때 transaction resource가 어떻게 rendezvous가 되는지 좁혀 본다.”
- **Central Behavior:** `mvcc-lock-policy`
- **Obligations:** `mental-model`, `core-workflows`, `concurrency`, `policies-algorithms`, `performance-observability`

### 08. MVCCID self-lock — inserter와 observer의 rendezvous

- **권장 파일/anchor:** `chapters/08-mvccid-self-lock.html#mvccid-self-lock-rendezvous`
- **학습 질문:** inserter가 자기 MVCCID resource에 `X_LOCK`을 보유하고 observer가 `S_LOCK`으로 기다리는 구조가 왜 자기 자신을 막지 않으며 왜 per-row lock을 줄일 수 있는가?
- **내용:** lazy MVCCID 발급, self-lock ensure, main/subtransaction lifetime, observable row/INSID와 X-holder invariant, unique/FK observer, wait 전에 놓는 latch/object lock, S wait, immediate release, active/record recheck, commit/abort ordering. scope의 `inactive publication → unlock → wakeup/recheck`를 counterexample과 함께 설명한다.
- **시각화:** T1 inserter, MVCC active table, Lock Manager transaction resource, B-tree/page, T2 observer의 다섯 lane sequence. 정상 commit과 abort를 두 갈래로 보인다.
- **보이는 한국어 대체 설명:** “T1이 MVCCID M을 observer가 볼 수 있는 row/version에 남기기 전에 같은 M resource의 rendezvous가 준비되어야 한다. T2의 source-confirmed unique/FK 경로가 M을 발견하면 필요한 latch와 object lock을 놓고 M에 대한 wait를 시작한다. T1은 완료 상태를 공개한 뒤 self-lock을 해제한다. T2는 깨어난 뒤 lock 획득 자체를 결론으로 쓰지 않고 active 상태와 index/record 조건을 다시 검사한다. 각 단계의 실제 함수와 ordering은 Claims로 증명한다.”
- **Counterexample 질문:** “row에서 M이 보이는데 M의 X-holder가 아직 없다면 T2의 S 요청은 어떤 잘못된 결론을 허용할 수 있는가?”
- **Recap 질문:** “`self`, `X`, `S`, `transaction resource`, `recheck`를 모두 사용해 protocol을 설명하라.”
- **Transition:** “정상 protocol뿐 아니라 crash, resource pressure, 관측 비용과 volatile/durable 경계도 확인한다.”
- **Central Behavior:** `mvccid-self-lock-rendezvous`
- **Obligations:** `data-ownership-lifetime`, `lifecycle-state-machines`, `core-workflows`, `concurrency`, `performance-observability`

### 09. 실패, durability 경계, 성능, observability

- **학습 질문:** lock table은 restart 뒤 어떻게 되며, timeout·allocation failure·shutdown race와 hot contention을 운영자가 무엇으로 구분할 수 있는가?
- **내용:** volatile lock state와 WAL/MVCC persistent state의 경계, commit/abort/restart matrix, lock reconstruction의 범위, allocation failure, cancellation, timeout, shutdown, assertion boundary, cleanup, hash/queue contention, memory cost, escalation과 self-lock의 cost model, dump/event/counter/debugger landmarks, 측정 caveat.
- **시각화:** volatile/durable 경계선, crash matrix, memory formula, observability signal→interpretation→limitation 표.
- **보이는 한국어 대체 설명:** “Lock Manager의 coordination entry와 row/log의 durable state를 구분한다. process restart가 in-memory waiter queue를 그대로 복원한다고 가정하지 않는다. recovery가 어떤 logical 상태를 복원하고 새 lock table이 어떻게 시작되는지는 source/test Claims로 적는다. dump와 counter 이름은 increment site를 확인한 뒤에만 의미를 부여한다.”
- **Recap 질문:** “runtime lock entry와 durable row/version state 가운데 restart 후 복원되는 것을 근거 등급과 함께 나눠라.”
- **Transition:** “지금까지의 source 모델을 CUBRID-only runtime observation으로 얼마나 검증할 수 있는지 본다.”
- **Obligations:** `storage-durability-recovery`, `errors-resource-pressure`, `performance-observability`

### 10. 네 Central Behavior를 관찰하는 실험과 해석의 한계

- **학습 질문:** SQL 결과, blocking 시간, lock dump, counter 가운데 무엇이 내부 lock mechanism을 직접 또는 간접 증명하는가?
- **내용:** Experiment 1~4를 Question→Hypothesis→Setup→Action→Observation→Interpretation→Alternative→Cleanup 순서로 제시한다. raw output과 해석을 분리한다. observer effect, repetitions, warm/cold state, owned database, direct/indirect oracle을 명시한다.
- **시각화:** 각 실험의 evidence ladder와 positive/negative control 표.
- **보이는 한국어 대체 설명:** “SQL 결과는 transaction outcome을 직접 관찰할 수 있다. wait 시간은 blocking을 간접 관찰한다. lock dump가 resource와 mode를 보이면 내부 state에 더 가까운 근거가 된다. 그러나 하나의 SQL outcome만으로 정확한 call path나 self-lock 구현을 증명할 수 없다. source Claim과 runtime observation이 어디서 만나는지 실험별로 밝힌다.”
- **Recap 질문:** “중복 key insert가 기다렸다는 관찰만으로 MVCCID self-lock을 증명할 수 없는 이유와 필요한 control을 말하라.”
- **Transition:** “같은 책임이 PostgreSQL에서는 어느 Module에 놓이는지 source로 비교한다.”
- **Obligations:** `experimental-validation`, `teaching-map`

### 11. PostgreSQL — relation, tuple, transaction identity에 나뉜 책임

- **학습 질문:** CUBRID의 class/instance/transaction resource 책임과 가장 가까운 PostgreSQL mechanism은 하나의 Lock Manager인가, 여러 layer의 조합인가?
- **내용:** pinned source tracer가 확인한 heavyweight relation lock, tuple/row update representation, transaction-ID 또는 virtual transaction wait, unique/speculative insertion mechanism을 shared axes로 설명한다. 이름이 비슷하다는 이유로 self-lock equivalent를 선언하지 않는다.
- **시각화:** shared scenario 네 동작을 PostgreSQL responsibility swimlane에 배치한다.
- **보이는 한국어 대체 설명:** “PostgreSQL에서 relation 보호, row update coordination, unfinished transaction 또는 speculative insertion wait가 서로 다른 resource와 code path에 나뉠 수 있다. 각 대응은 owner, lifetime, recheck invariant를 확인한 뒤 CUBRID와 비교한다. source evidence가 없는 대칭은 `Unknown`으로 남긴다.”
- **Recap 질문:** “PostgreSQL의 transaction identity wait가 CUBRID self-lock과 비슷해 보이더라도 확인해야 할 세 semantic gap은 무엇인가?”
- **Transition:** “MySQL server와 InnoDB 사이의 책임 분리도 같은 축으로 읽는다.”
- **Obligations:** `postgresql-analysis`

### 12. MySQL/InnoDB — metadata, intention, record, transaction wait

- **학습 질문:** MySQL server와 InnoDB 중 누가 table metadata, record conflict, unique/FK wait를 소유하는가?
- **내용:** concrete engine owner를 `InnoDB`로 명시한다. MDL과 InnoDB table intention/record locks, read view, transaction wait state, unique/FK checks를 source-confirmed axes로 나눈다. InnoDB의 이름이 비슷한 `S/X/IS/IX`라도 Interface equivalence를 자동 선언하지 않는다.
- **시각화:** MySQL server↔InnoDB seam과 shared scenario flow.
- **보이는 한국어 대체 설명:** “metadata 책임은 server layer에 있고 row/version과 record-lock 책임은 InnoDB에 있을 수 있다. 실제 경계는 pinned source가 정한다. CUBRID class lock과 InnoDB table intention lock, CUBRID instance lock과 InnoDB record lock은 resource representation과 wait/recheck가 다르면 partial analogy다.”
- **Recap 질문:** “동일한 mode 이름보다 Module boundary가 비교에서 중요한 이유를 설명하라.”
- **Transition:** “세 DBMS를 같은 표에 놓되 책임과 semantic gap을 함께 적는다.”
- **Obligations:** `mysql-analysis`

### 13. 세 DBMS 비교 — 같은 시나리오, 다른 responsibility flow

- **학습 질문:** 세 시스템은 T2의 네 동작에서 무엇을 resource로 삼고, 누구를 기다리며, 깨어난 뒤 무엇을 다시 검사하는가?
- **내용:** terminology map, shared scenario flow, resource/owner/lifetime/wait/recheck/durability/observability table. 모든 substantive cell에 Claim IDs와 analogy class를 둔다. negative search 없이 `no equivalent`를 쓰지 않는다.
- **시각화:** 네 SQL operation × 세 DBMS comparison matrix. 한 셀 안에 `resource`, `wait target`, `recheck`, `class`를 짧게 쓴다.
- **보이는 한국어 대체 설명:** “각 행은 같은 SQL 질문을 비교한다. 각 DBMS 칸은 responsibility owner와 resource를 적는다. 마지막 칸은 일부 의미만 같은지 전체 Interface와 invariant까지 같은지를 분류한다. 같은 이름이 없어도 책임이 다른 layer에 있으면 partial analogy일 수 있고, 이름이 같아도 semantics가 다르면 equivalent가 아니다.”
- **Recap 질문:** “self-lock과 가장 가까운 두 mechanism을 고르고, 각각 왜 완전 equivalent가 아닐 수 있는지 말하라.”
- **Transition:** “비교에서 드러난 필수 Interface와 차이를 재구현 blueprint에 반영한다.”
- **Obligations:** `cross-database-comparison`

### 14. source를 다시 열지 않고 재구현하기 — blueprint, evidence, unknowns, mastery

- **학습 질문:** 독립 구현자가 이 범위의 Lock Manager와 MVCC rendezvous를 만들고 conformance test로 검증하려면 무엇이 완전해야 하는가?
- **내용:** Interface contract, abstract data model, initialization/shutdown, total transitions, compatibility/conversion/escalation, wait/deadlock/release, MVCC policy decision table, self-lock ordering, error/resource pressure, durability boundary, dependency seams, implementation order, conformance tests. Korean glossary, Claim index, experiment transcript, coverage matrix, known unknowns, compatibility limits, readiness declaration, Quiz/Live Grill map을 함께 둔다.
- **시각화:** implementation dependency DAG와 behavior×test conformance matrix.
- **보이는 한국어 대체 설명:** “resource identity와 ownership model을 먼저 구현한다. compatibility와 grant/wait state machine을 붙인다. transaction cleanup과 deadlock/error path를 완성한다. 그 위에 operation별 MVCC lock policy와 MVCCID rendezvous를 연결한다. 각 단계는 정상, wait, abort, timeout, restart, comparison limit을 검증하는 독립 test를 가진다.”
- **Recap 질문:** “현재 source를 열지 않고도 구현할 수 없는 한 항목이 남아 있다면 readiness에 어떤 영향을 주는가?”
- **Obligations:** `reimplementation-blueprint`, `glossary-evidence-unknowns`, `teaching-map`

## 5. 18 Coverage Obligations 배치

| Coverage Obligation | 주 장 | 보조 장 | 교육적 완료 조건 |
|---|---:|---:|---|
| `orientation` | 01 | 14 | scope, revisions, dirty state, conclusions, limits, reading path를 첫 화면에서 찾는다. |
| `mental-model` | 02 | 01, 03, 07 | protected state·owner·lifetime으로 mutex/latch/lock/MVCC를 구분한다. |
| `scope-interface-seams` | 03 | 04, 07, 14 | caller obligation과 query/storage/transaction seam을 입력·출력·error까지 말한다. |
| `data-ownership-lifetime` | 04 | 03, 08 | resource/holder/waiter/hold-list와 MVCCID state의 owner 및 reclamation을 설명한다. |
| `lifecycle-state-machines` | 05, 06 | 08, 09 | legal/illegal transition, wait, failure, release, restart boundary가 total하다. |
| `core-workflows` | 05~08 | 10 | fast, miss, wait, retry, failure, 네 SQL operation, self-lock flow를 추적한다. |
| `concurrency` | 06~08 | 02, 04, 09 | 보호 필드, ordering, wait-release-reacquire, forbidden interleaving을 설명한다. |
| `storage-durability-recovery` | 09 | 06, 08, 14 | volatile lock state와 durable MVCC/WAL state를 crash matrix로 구분한다. |
| `policies-algorithms` | 05, 07, 08 | 06, 14 | compatibility, conversion, escalation, operation별 lock policy, self-lock 의사코드가 total하다. |
| `errors-resource-pressure` | 06, 09 | 05, 08 | timeout/deadlock/interrupt/allocation/shutdown failure의 propagation과 cleanup을 말한다. |
| `performance-observability` | 09 | 05, 07, 08, 10 | contention/memory/cost와 dump/counter의 의미 및 측정 한계를 구분한다. |
| `experimental-validation` | 10 | 06~09 | 네 behavior 모두 hypothesis, control, raw output, alternatives, cleanup을 가진다. |
| `postgresql-analysis` | 11 | 13 | shared axes 전체에서 nearest mechanism과 semantic gap을 source로 설명한다. |
| `mysql-analysis` | 12 | 13 | MySQL server/InnoDB owner를 구분하고 same axes로 설명한다. |
| `cross-database-comparison` | 13 | 11, 12, 14 | substantive cell마다 세 DB Claim과 analogy class가 있다. |
| `reimplementation-blueprint` | 14 | 03~09 | source를 다시 열지 않고 Interface, state, error, ordering, tests를 구현할 수 있다. |
| `glossary-evidence-unknowns` | 14 | 모든 장 | first-use glossary, evidence index, unknown, limitation, readiness가 서로 연결된다. |
| `teaching-map` | 01, 14 | 10 | behavior→chapter→Claims→Experiment→Quiz→Grill mapping이 완전하다. |

## 6. 반드시 그릴 Visual과 한국어 Text Alternative

모든 그림은 `<svg>`의 짧은 label만으로 끝내지 않는다. 그림 직후 보이는 한국어 문단이나 표로 동일한 causal content를 제공한다. state 이름, transition 이름, actor 이름은 그림과 대체 설명에서 정확히 일치해야 한다.

| Visual | 핵심 관계 | 필수 한국어 text alternative | Evidence guard |
|---|---|---|---|
| V1 shared scenario timeline | T1 update/insert와 T2 네 동작 | 각 T2 동작이 visibility, 변경 권리, constraint 확정 가운데 어떤 질문을 던지는지 시간순으로 설명 | 결과와 wait 여부는 runtime/source Claim 전에는 물음표로 둔다. |
| V2 primitive lifetime lanes | mutex/latch/transaction lock/MVCC | protected state, owner, acquire/release boundary를 네 문장으로 대비 | CUBRID-specific latch mode를 일반 이론처럼 쓰지 않는다. |
| V3 resource namespace map | database/class/instance/transaction key | type+identity가 key이며 mode가 identity가 아니라는 설명 | exact key fields와 hash는 Claim IDs 필요 |
| V4 ownership graph | hash resource, holder/waiter, transaction hold list | allocation owner, lookup direction, release/reclamation을 문장과 표로 제공 | 포인터 edge마다 source range 필요 |
| V5 hierarchy and compatibility | class intention↔instance, mode matrix | 모든 matrix cell에 `호환/충돌` 텍스트와 condition을 표시 | full matrix를 source에서 생성해야 한다. |
| V6 acquisition state machine | lookup/create/grant/wait/retry/error/release | state/guard/action/error를 별도 table로 반복 | 의사코드 branch마다 Claim IDs 필요 |
| V7 wait/deadlock sequence | holder, waiter, WFG, victim/release | 누가 어떤 resource를 기다리고 wake reason마다 다음 action이 무엇인지 서술 | wakeup=grant라고 생략하지 않는다. |
| V8 MVCC responsibility matrix | SELECT/FOR UPDATE/DML/unique-FK × visibility/lock/latch | 각 cell이 해결하는 race와 해결하지 않는 race를 적는다. | isolation/class/path 조건을 숨기지 않는다. |
| V9 self-lock rendezvous | INSID/MVCCID, X holder, S waiter, inactive→unlock→recheck | actor별 여섯 단계와 commit/abort 갈림, wait 전 release와 후 recheck를 설명 | 가장 높은 evidence bar. 모든 arrow에 Claims가 필요하다. |
| V10 forbidden interleavings | row publish-before-lock, unlock-before-inactive, latch-held wait | 각 잘못된 순서가 허용할 수 있는 잘못된 관찰을 counterexample로 설명 | 실제 forbidden 여부와 memory ordering을 source로 증명 |
| V11 volatile/durable boundary | lock table vs row/log/MVCC recovery | crash 전후 남는/사라지는 state와 reconstruction 주체를 표로 제공 | `not-applicable`도 positive evidence 필요 |
| V12 experiment evidence ladder | SQL outcome→wait→dump/counter→source interpretation | 직접 관찰, 간접 관찰, inference, unknown을 분리 | counter increment site와 observer effect 필요 |
| V13 PostgreSQL responsibility flow | relation/tuple/xid/speculative paths | shared scenario의 resource, owner, wait/recheck를 설명 | 역할을 한 module로 강제하지 않는다. |
| V14 MySQL/InnoDB responsibility flow | MDL/server↔InnoDB table/record/trx | server/engine seam과 각 lock lifetime을 설명 | concrete engine owner를 명시 |
| V15 three-DB matrix | same scenario across three DBMS | 각 analogy class의 공통점과 semantic gap을 문장으로 반복 | 모든 cell에 participating DB Claims 필요 |
| V16 implementation DAG | resource model→wait lifecycle→MVCC policy→self-lock | 구현 순서와 각 단계의 conformance oracle을 설명 | unresolved dependency가 있으면 readiness 하향 |

공통 접근성 규칙:

- matrix는 색뿐 아니라 `호환`, `충돌`, `조건부`, `Unknown` 텍스트를 쓴다.
- holder와 waiter는 색뿐 아니라 `HOLDER`, `WAITER` label을 쓴다.
- historical fact, current source, inference, analogy, unknown을 색과 텍스트 label로 함께 표시한다.
- sequence diagram의 아래에는 번호가 붙은 순서 목록을 둔다.
- state diagram 아래에는 `현재 state / event / guard / action / next state / failure` 표를 둔다.
- 중앙 설명을 `<details>` 안에 숨기지 않는다.

## 7. 빠지기 쉬운 인과 연결

Book writer는 아래 연결마다 한 문단, 한 visual edge, 한 Claim 묶음을 확보해야 한다.

1. **동시 실행 → 깨질 logical state → primitive 선택**  
   “lock이 필요하다” 전에 어떤 invariant가 깨지는지 보여 준다.

2. **resource identity → compatibility → grant/wait**  
   mode 비교 전에 같은 resource인지 확인해야 한다.

3. **instance request → class intention obligation → hierarchy conflict**  
   intention mode가 row permission이 아니라 hierarchy summary라는 원인을 설명한다.

4. **held mode → conversion → conversion waiter**  
   conversion을 새 request로 단순화할 때 생기는 fairness/deadlock 문제를 source 범위에서 설명한다.

5. **row count/threshold → escalation attempt → old locks release or fallback**  
   escalation의 성능 이득과 concurrency 손실을 같은 시나리오로 보여 준다.

6. **incompatible request → wait queue/WFG → suspend**  
   queue insertion과 WFG edge가 원자적으로 어떤 ordering을 요구하는지 확인한다.

7. **release → wakeup → grant/retry → business recheck**  
   wakeup을 곧바로 SQL success로 연결하지 않는다.

8. **MVCC version choice → snapshot reader의 reduced locking**  
   latch와 atomic이 사라진다는 결론으로 확장하지 않는다.

9. **locked read/DML → logical writer coordination**  
   visible version을 고르는 일과 변경 권리를 확보하는 일을 분리한다.

10. **unique/FK candidate → unfinished inserter identity → wait target**  
    일반 snapshot reader와 constraint observer를 한 actor로 그리지 않는다.

11. **MVCCID allocation → X self-lock 준비 → observable identity publication**  
    “row가 보이는 순간 matching rendezvous가 존재한다”는 invariant의 정확한 적용 범위를 source로 고정한다.

12. **observer wait 전 latch/object lock release → S wait → wakeup → reacquire/recheck**  
    latch를 들고 장기 wait할 때 생길 수 있는 cycle과 stale pointer 위험을 설명한다. 실제 release 목록은 source가 정한다.

13. **transaction inactive publication → self-lock unlock → waiter recheck**  
    반대 순서의 counterexample을 제시한다. main/subtransaction 경로를 별도로 검증한다.

14. **one transaction self-lock → many inserted versions → row-lock reduction**  
    모든 row/object lock을 없앤다는 과장 없이 정확한 replacement condition과 남는 locks를 말한다.

15. **commit/abort result → observer’s record/index recheck**  
    같은 wakeup이라도 commit과 abort 뒤 업무 결과가 달라질 수 있음을 보여 준다.

16. **volatile lock cleanup → durable recovery boundary**  
    lock entry 자체 복원과 database consistency 복원을 구분한다.

17. **same responsibility → different Module → analogy classification**  
    함수/enum 이름 비교가 아니라 Interface와 invariant 비교로 결론낸다.

18. **source fact + runtime observation → bounded interpretation**  
    SQL block만으로 내부 resource type을 증명하지 않는다.

## 8. 비교에서 특히 위험한 analogy

다음 문장은 source packet이 완전한 call path와 negative search를 주기 전까지 Book에 넣지 않는다.

| 위험한 문장 | 왜 위험한가 | 대신 물을 Evidence 질문 |
|---|---|---|
| “PostgreSQL tuple lock은 CUBRID instance lock과 equivalent다.” | row conflict representation, lifetime, heavyweight entry 사용 여부, recheck가 다를 수 있다. | 동일 shared scenario에서 resource identity, owner, persistent hint, wait target은 무엇인가? |
| “PostgreSQL TransactionIdLock은 CUBRID self-lock이다.” | 자동 acquisition, holder mode, explicit key, observer 종류, release ordering이 다를 수 있다. | transaction identity wait가 누구에 의해 생성되고 누가 기다리며 completion을 어떻게 재검사하는가? |
| “speculative insertion lock이 CUBRID self-lock과 같다.” | unique insertion 한 축만 비슷하고 general MVCCID lifetime은 다를 수 있다. | speculative token의 scope와 abort/confirm protocol이 CUBRID MVCCID resource와 어느 축에서만 겹치는가? |
| “PostgreSQL에는 lock escalation이 없다.” | negative claim은 광범위한 source search가 필요하다. | relation/tuple/predicate/advisory paths와 alternate terminology에서 promotion/escalation 책임을 찾았는가? |
| “InnoDB `IS/IX/S/X`는 CUBRID mode와 equivalent다.” | 동일한 이름이 hierarchy, gap/next-key, lifetime, engine seam의 동일성을 보장하지 않는다. | compatibility와 caller obligation, resource granularity, release policy가 실제로 같은가? |
| “InnoDB trx wait는 CUBRID MVCCID self-lock이다.” | InnoDB는 record lock owner transaction을 기다릴 수 있고 별도 transaction-key resource가 아닐 수 있다. | waiter가 어떤 lock object/resource를 enqueue하며 transaction completion을 어디서 관찰하는가? |
| “MVCC read view는 CUBRID snapshot과 equivalent다.” | visibility semantics와 isolation details가 다를 수 있다. | shared input에서 visible version 선택 invariant와 refresh/lifetime이 얼마나 같은가? |
| “세 DBMS 모두 unique 충돌에서 같은 row lock을 쓴다.” | speculative token, index record/gap, transaction ID 등 책임 위치가 다를 수 있다. | candidate 발견부터 commit/abort 뒤 recheck까지 concrete flow는 무엇인가? |

Analogy class를 정할 때 다음 순서를 사용한다.

1. 같은 shared scenario의 책임을 찾는다.
2. Interface input/output과 caller obligation을 비교한다.
3. resource identity와 owner/lifetime을 비교한다.
4. wait/wakeup/recheck invariant를 비교한다.
5. durability/restart와 error behavior를 비교한다.
6. 모두 실질적으로 맞을 때만 `equivalent`를 고려한다.
7. 한 축만 교육적으로 닮았으면 `partial analogy`다.
8. `no equivalent`는 alternate terminology와 split responsibility에 대한 negative search가 있을 때만 쓴다.

## 9. Evidence 질문과 Unknown 체크리스트

Pedagogy 역할은 아래 답을 정하지 않는다. Book writer는 source/runtime Claims로 답하거나 material gap으로 남겨야 한다.

### 9.1 `resource-mode-hierarchy`

- database/class/instance/transaction resource의 exact key fields와 hash/equality는 무엇인가?
- transaction resource의 identity는 full MVCCID인가? type tag가 object resource와 alias를 막는가?
- external Interface의 caller가 제공해야 하는 class OID, instance OID, mode, conditional flag, timeout, transaction context는 무엇인가?
- mode compatibility table은 어느 pinned source에서 생성되는가?
- mode conversion에서 old/new mode, non2pl entry, conversion waiter를 어떻게 처리하는가?
- class intention mode와 instance mode 사이의 precondition/order는 무엇인가?
- escalation threshold와 trigger는 무엇이며 failure 시 이전 row locks가 그대로 보존되는가?
- resource/entry allocation failure가 caller error와 partial state cleanup으로 어떻게 연결되는가?
- resource hash와 holder/waiter lists를 보호하는 mutex 순서와 forbidden inversion은 무엇인가?
- transaction hold list와 resource list 사이의 ownership 및 reclamation condition은 무엇인가?
- fast path, resource miss, same-owner re-request, conditional conflict의 complete branch는 무엇인가?
- performance counters와 dumps는 object와 transaction resource를 구분하는가?

### 9.2 `wait-deadlock-release`

- incompatible request는 정확히 어느 함수에서 waiter가 되고 어느 lock/mutex를 놓고 suspend하는가?
- queue order와 fairness policy는 무엇이며 starvation-free를 약속할 수 있는가?
- wait-for graph edge의 생성/갱신/제거 시점과 conversion waiter 표현은 무엇인가?
- deadlock detector는 어떤 cycle을 보고 어떤 victim result를 Lock Manager에 전달하는가?
- victim 선택 전체가 범위 밖이어도 caller-visible error와 cleanup path는 무엇인가?
- timeout, conditional failure, interrupt, shutdown, deadlock의 return/error가 어떻게 다르게 전파되는가?
- wakeup 뒤 request grant를 재검사하는가, 이미 grant state로 깨우는가, 두 형태가 모두 있는가?
- waiter cancellation과 transaction abort가 queue/hold list/WFG에 남기는 state는 없는가?
- holder commit과 abort는 같은 `lock_unlock_all` path를 쓰는가? partial/subtransaction release는 어디서 갈리는가?
- resource entry는 마지막 holder/waiter가 사라진 즉시 free되는가, pool/cache lifetime이 있는가?
- shutdown에서 lock table과 daemons/threads의 종료 순서는 무엇인가?
- lock wait 중 held page latch나 object lock이 있다면 정확히 무엇을 release/reacquire하는가?

### 9.3 `mvcc-lock-policy`

- plain snapshot `SELECT`의 query→scan→heap path에서 어떤 class/instance lock을 어떤 조건으로 요청하거나 생략하는가?
- isolation level별로 같은 결론을 낼 수 있는가? 책의 실험은 어느 isolation을 고정하는가?
- `SELECT ... FOR UPDATE`의 lock hint/mode와 predicate recheck는 어디서 결정되는가?
- `UPDATE`/`DELETE`의 writer-writer conflict는 row lock, MVCC header, both 가운데 어떤 protocol을 사용하며 wait target은 무엇인가?
- `INSERT`가 class intention, instance lock, index/unique check를 어떤 순서로 수행하는가?
- non-MVCC class 또는 special catalog/class 경로는 어디서 갈리는가?
- unique와 FK 검사는 같은 observer helper와 wait/recheck protocol을 공유하는가?
- scan 중 page latch와 transaction lock의 acquisition order는 무엇인가?
- lock timeout과 query cancellation은 executor/scan/locator 계층으로 어떻게 올라가는가?
- `MVCC lock`이라는 교육적 policy table을 만들 때 실제 enum에 없는 이름을 code identifier처럼 표시하지 않았는가?
- range/predicate locking이 명시적 제외 범위인 탓에 어떤 SQL guarantee를 책이 약속하지 않아야 하는가?

### 9.4 `mvccid-self-lock-rendezvous`

- MVCCID는 언제 lazy 발급되며 main/subtransaction ID는 각각 언제 만들어지는가?
- 발급 함수와 `logtb_ensure_mvccid_self_lock`의 success/no-op/error path는 무엇인가?
- inserter의 X-holder가 만들어지기 전 MVCCID/INSID가 observer에게 노출되지 않는 ordering은 어떻게 보장되는가?
- 어느 heap/B-tree row operation이 per-row `X_LOCK`을 생략하고 self-lock invariant에 의존하는가?
- “per-row lock 수를 줄인다”의 denominator와 exact applicability는 무엇인가?
- unique/FK observer가 row/index에서 other MVCCID를 얻는 complete call path는 무엇인가?
- observer가 self/committed/aborted/active MVCCID를 구분하는 branch는 무엇인가?
- S wait 전에 page latch와 보유 object lock 가운데 무엇을 왜 놓는가?
- S request가 grant된 직후 즉시 release되는가? 실패/timeout/deadlock일 때 entry cleanup은 무엇인가?
- wakeup 뒤 active state와 record/index predicate를 어떤 순서로 재검사하는가?
- main commit/abort에서 MVCCID inactive publication과 self-lock release의 exact ordering은 무엇인가?
- subtransaction completion/rollback도 같은 ordering과 waiter semantics를 갖는가?
- active publication의 mutex/atomic/happens-before와 Lock Manager wakeup 사이의 memory visibility는 무엇이 보장하는가?
- boot/recovery/system/vacuum transaction은 self-lock protocol을 사용하는가? 사용하지 않으면 concurrent observer가 없다는 precondition은 어디서 보장되는가?
- transaction resource가 generic object acquire/wait counter에 섞이는가? 별도 self-lock dump/counter가 있는가?
- SQL-only runtime으로 self-lock을 직접 식별할 수 있는가? 할 수 없다면 어떤 source+dump 조합이 가장 강한 bounded evidence인가?

### 9.5 durability, restart, errors, performance

- lock table 전체가 volatile하다는 직접 source와 initialization/shutdown path는 무엇인가?
- crash recovery가 in-flight logical changes를 정리한 뒤 새 lock state를 시작하는 order는 무엇인가?
- restart 뒤 old waiter/holder identity가 재생되지 않는다는 positive evidence는 무엇인가?
- deadlock victim rollback과 process crash recovery를 같은 장에서 어떻게 혼동 없이 나눌 것인가?
- lock allocation pool exhaustion, timeout, cancellation, shutdown race의 cleanup이 leak-free인지 어떤 tests가 보여 주는가?
- hash bucket contention, queue walk, WFG cost, escalation cost, MVCCID self-lock memory saving을 어떤 formula/measurement로 설명할 수 있는가?
- counter 이름의 모든 increment site를 읽었는가?
- lock dump가 observer effect를 만들거나 global state만 보여 주는 제한은 무엇인가?

### 9.6 PostgreSQL/MySQL comparison

- PostgreSQL shared scenario에서 relation, tuple, transaction ID, virtual transaction, speculative token 중 실제 resource는 무엇인가?
- PostgreSQL unique conflict waiter는 누구의 어떤 completion을 기다리고 무엇을 재검사하는가?
- PostgreSQL의 row update lock state는 memory와 tuple header/MultiXact 중 어디에 있으며 lifetime은 무엇인가?
- PostgreSQL에서 CUBRID escalation responsibility의 nearest mechanism 또는 supported negative claim은 무엇인가?
- MySQL server MDL과 InnoDB table/record lock의 Interface seam은 어디인가?
- InnoDB read view가 plain SELECT를 처리할 때 record lock을 요구하지 않는 exact conditions는 무엇인가?
- InnoDB `SELECT ... FOR UPDATE`, DML, unique/FK가 어떤 record/gap/table lock을 사용하며 scope의 range-lock 제외와 어떻게 경계를 긋는가?
- InnoDB waiter는 transaction-key resource를 기다리는가, conflicting record lock owner transaction을 기다리는가?
- 세 DBMS 모두에서 commit과 abort 뒤 waiter가 재검사하는 business condition은 무엇인가?
- 각 comparison cell의 `equivalent/partial analogy/no equivalent`가 참여 DB Claims를 모두 인용하는가?

## 10. Static Quiz 설계

Quiz는 네 Central Behavior에 하나씩 연결한다. 모든 Quiz는 예측→실행→관찰→인과 설명→한계 진술 순서를 따른다. runnable artifact는 CUBRID만 요구한다. PostgreSQL/MySQL은 Book evidence를 이용한 reasoning 문제로만 포함한다.

| Quiz | Central Behavior | 예측과 실행 | Teach-back | 꼭 적을 한계 |
|---|---|---|---|---|
| `quiz-1` resource 카드와 hierarchy | `resource-mode-hierarchy` | owned table/rows에 대한 두 transaction 요청을 실행하기 전에 resource·mode·owner·compatibility를 채운다. source-confirmed lock dump가 가능하면 hierarchy/holder를 관찰한다. conversion 또는 escalation 변형은 deterministic oracle이 있을 때만 포함한다. | “같은 mode인데 다른 resource인 경우”와 “class intention이 instance lock을 대신하지 않는 이유”를 설명한다. | SQL outcome만으로 exact compatibility branch나 escalation threshold를 증명하지 않는다. |
| `quiz-2` wait의 네 출구 | `wait-deadlock-release` | T1이 row를 갱신한 채 대기시키고 T2의 conflicting operation을 실행한다. commit, abort, timeout, controlled deadlock 변형에서 결과를 예측한다. scheduler 순서가 아니라 allowed invariant를 채점한다. | wait queue/WFG/release/cleanup을 transaction timeline으로 설명한다. | blocking 시간 하나로 deadlock detector policy나 fairness를 증명하지 않는다. |
| `quiz-3` snapshot read와 locked read | `mvcc-lock-policy` | 같은 T1 uncommitted update에 대해 T2 plain SELECT, `FOR UPDATE`, `UPDATE`를 고정 isolation에서 비교한다. result, blocking, final value를 예측한다. | “visibility 질문”과 “변경 권리 질문”이 각 operation에서 어떻게 갈리는지 설명한다. | 관찰 결과를 다른 isolation level이나 non-MVCC class 전체로 일반화하지 않는다. |
| `quiz-4` unfinished unique inserter | `mvccid-self-lock-rendezvous` | T1이 unique key insert 후 미종료 상태에서 T2가 같은 key를 insert한다. T1 commit/abort 두 control에서 T2의 wait와 최종 결과를 예측한다. source-confirmed dump로 MVCCID transaction resource를 볼 수 있을 때만 직접 oracle로 사용한다. | X holder, S waiter, inactive→unlock→recheck를 그리고 일반 snapshot reader가 왜 같은 waiter가 아닌지 설명한다. 마지막에 PostgreSQL/MySQL nearest mechanism의 analogy class를 Book Claims로 분류한다. | unique conflict wait만으로 내부 self-lock resource를 독립 증명하지 않는다. source와 dump가 필요하다. |

세트 전체가 충족해야 할 교육 범위:

- normal flow: Quiz 1, 3
- edge/failure flow: Quiz 2, 4 commit/abort variants
- concurrency reasoning: Quiz 2, 3, 4
- durability/restart reasoning: Quiz 2 answer의 제한과 09장 연계. 안전한 crash 실험이 없다면 source/test reasoning으로 명시한다.
- performance/policy trade-off: Quiz 1의 granularity/escalation, Quiz 4의 per-row vs transaction-key rendezvous 설계 문제
- PostgreSQL/MySQL comparison: Quiz 4 마지막 reasoning section
- reimplementation task: Quiz 4에 total self-lock pseudocode와 three counterexample tests를 작성하게 한다.

각 `answer.md`가 다룰 공통 오답 모델:

- lock mode 이름만 보고 같은 resource라고 판단한다.
- mutex owner thread와 transaction lock owner를 합친다.
- intention mode가 row permission을 대신한다고 생각한다.
- wakeup이 SQL 조건의 success를 보증한다고 생각한다.
- MVCC가 있으므로 writer-writer 또는 constraint wait도 없다고 생각한다.
- self-lock이 자기 자신을 기다린다고 생각한다.
- unique insert blocking 하나가 exact internal implementation을 증명한다고 생각한다.
- PostgreSQL/MySQL에서 비슷한 이름을 찾으면 `equivalent`라고 판단한다.

## 11. Live Grill 경로

Live Grill은 정확히 한 turn에 한국어 질문 하나만 묻는다. 아래 표는 질문 bank이지 한 turn에 여러 질문을 묶으라는 뜻이 아니다.

| Mastery area | 첫 질문 방향 | PARTIAL일 때 좁힐 causal step | 연결 장/Quiz |
|---|---|---|---|
| responsibility, scope, Interface, seams | “T2의 네 동작 각각이 Lock Manager에 요구하는 책임과 MVCC visibility 책임을 나눠 보세요.” | 한 operation만 골라 input/output부터 묻는다. | 01, 03, 07 / Quiz 1, 3 |
| data ownership and lifetime | “resource, holder, waiter, transaction hold list를 누가 만들고 언제 회수하나요?” | holder 하나의 두 backlink만 그리게 한다. | 04, 08 / Quiz 1, 4 |
| lifecycle and state transitions | “incompatible request가 생성된 순간부터 grant 또는 failure까지 state를 순서대로 말해 보세요.” | wait queue insertion 다음 event 하나만 묻는다. | 05, 06 / Quiz 2 |
| concurrency invariants | “self-lock protocol에서 순서가 뒤집히면 안 되는 두 publication을 말하고 counterexample을 들어 보세요.” | row identity가 보이기 전 무엇이 준비되어야 하는지만 묻는다. | 06~08 / Quiz 2, 4 |
| durability, recovery, failure | “transaction abort, deadlock victim, process crash 뒤에 각각 어떤 lock/MVCC state가 남나요?” | volatile lock entry 하나와 durable row state 하나만 분류하게 한다. | 09 / Quiz 2 |
| policy and performance trade-offs | “row lock, escalation, MVCCID self-lock이 resource 수와 concurrency에 주는 trade-off를 비교해 보세요.” | self-lock이 대체할 수 있는 row condition 하나만 묻는다. | 05, 07~09 / Quiz 1, 4 |
| experiment interpretation | “Quiz 4의 blocking 관찰이 직접 증명한 것과 source로 해석한 것을 분리해 보세요.” | SQL result와 lock dump 두 evidence class만 나누게 한다. | 10 / Quiz 4 |
| PostgreSQL/MySQL non-equivalence | “CUBRID self-lock과 가장 가까운 PG/InnoDB mechanism을 골라 semantic gap을 말해 보세요.” | resource identity와 wait target 중 하나만 비교하게 한다. | 11~13 / Quiz 4 |

권장 진행 순서:

1. shared scenario에서 learner의 초기 mental model을 먼저 그리게 한다.
2. Interface와 ownership을 통과한 뒤 lifecycle을 묻는다.
3. lifecycle을 이해한 뒤 MVCC policy와 self-lock ordering을 묻는다.
4. failure/durability와 performance를 묻는다.
5. Experiment의 evidence boundary를 묻는다.
6. PostgreSQL/MySQL non-equivalence를 묻는다.
7. 모든 영역이 `MASTERED`일 때만 capstone으로 간다.

오답 교정 규칙:

- “MVCC라 lock 없음”이면 plain read와 locked read 중 하나만 골라 보호하려는 상태를 다시 묻는다.
- “self-lock이라 자기 대기”이면 owner와 waiter의 transaction identity를 따로 쓰게 한다.
- “X_LOCK이니 같은 lock”이면 resource type/key를 먼저 묻는다.
- “commit이 unlock”이면 inactive publication과 business recheck를 사이에 넣도록 좁힌다.
- “PG/MySQL도 똑같음”이면 resource identity 하나만 비교하게 한다.
- 세 번 실패하면 정확한 장 anchor와 Quiz를 지정하고 `RETEACH`로 둔다.

최종 capstone 한 질문:

> “`account` 시나리오에서 T1이 기존 행을 갱신하고 새 unique key를 삽입한 채 종료하지 않았을 때, T2의 plain `SELECT`, `SELECT ... FOR UPDATE`, `UPDATE`, 중복 `INSERT`가 CUBRID의 MVCC visibility, class/instance lock, MVCCID self-lock을 어떻게 다르게 사용하고 commit/abort 뒤 무엇을 재검사하는지 설명한 다음, 같은 책임이 PostgreSQL과 MySQL/InnoDB에서는 어디에 놓이는지 analogy class와 함께 가르쳐 주세요.”

Capstone 평가는 정답 keyword 수가 아니라 다음 causal completeness로 한다.

- resource, mode, owner, waiter, lifetime을 구분한다.
- mutex/latch와 logical transaction lock을 섞지 않는다.
- MVCC policy와 self-lock을 enum mode로 말하지 않는다.
- normal/wait/failure/recheck를 끝까지 연결한다.
- volatile/durable 경계를 말한다.
- 세 DBMS 차이를 source-backed analogy class로 제한한다.

## 12. Reimplementation Readiness 질문

마지막 장은 아래 질문에 “source를 읽으라” 없이 답해야 한다. 하나라도 central unknown이면 readiness를 낮춰야 한다.

### Interface와 data model

- 지원 resource type과 type별 key/equality/hash는 완전한가?
- public/internal acquire, convert, conditional wait, release Interface의 pre/postcondition과 errors는 완전한가?
- holder/waiter/resource/transaction hold-list의 owner, allocation, reclamation은 완전한가?
- `tran_index`, TRANID, MVCCID, OID의 역할과 lifetime이 분리되어 있는가?

### State machine과 concurrency

- grant/wait/conversion/cancel/release의 legal/illegal transition이 total한가?
- compatibility matrix와 hierarchy invariant가 complete한가?
- escalation trigger, success, failure fallback, old-lock release ordering이 complete한가?
- mutable field별 mutex/latch/atomic과 acquisition order가 적혀 있는가?
- wait 전에 놓을 내부 lock/latch와 wakeup 뒤 reacquire/recheck가 적혀 있는가?
- wait queue와 WFG update가 race 없이 연결되는 invariant가 있는가?
- timeout, interrupt, deadlock victim, transaction abort의 cleanup이 각각 complete한가?

### MVCC policy와 self-lock

- plain SELECT, locked read, UPDATE, DELETE, INSERT, unique/FK의 decision table이 input condition까지 complete한가?
- non-MVCC/special class와 isolation-level branch가 숨겨지지 않았는가?
- self-lock X acquire가 observable MVCCID publication보다 앞선다는 ordering을 구현할 수 있는가?
- main/subtransaction inactive publication과 unlock ordering을 구현할 수 있는가?
- observer의 S wait, immediate release, active/record recheck가 total pseudocode로 적혀 있는가?
- per-row lock을 self-lock으로 대신할 exact condition과 남는 class/row locks가 적혀 있는가?

### Failure, restart, observability

- allocation/I/O/corruption/timeout/cancellation/shutdown-race 중 applicable failure가 error와 cleanup으로 연결되는가?
- volatile lock table의 initialization/shutdown과 crash 뒤 reconstruction boundary가 명확한가?
- recovery가 durable logical state를 정리하는 책임과 Lock Manager restart 책임이 분리되어 있는가?
- lock dump, event, counter, debugger landmark가 무엇을 보이고 무엇을 증명하지 못하는지 적혀 있는가?
- memory formula와 contention/scaling limit이 evidence-backed인가?

### Dependency와 tests

- query executor, scan, locator/heap/B-tree, MVCC table, log transaction table, WFG seam의 Interface가 적혀 있는가?
- 구현 순서가 dependency DAG와 일치하는가?
- 각 Central Behavior에 normal, conflict, timeout/deadlock, abort, cleanup, restart-boundary conformance oracle이 있는가?
- self-lock의 두 ordering counterexample을 잡는 test가 있는가?
- shared scenario를 세 DBMS semantic comparison과 무관하게 CUBRID-only로 재현할 수 있는가?
- ABI, on-disk format, exact timing, starvation-free 같은 비약속 항목이 명시되어 있는가?

## 13. Book Writer 품질 체크

- 01장에서 exact revisions와 dirty provenance를 숨기지 않았는가?
- 첫 `lock` 사용이 generic word인지 CUBRID transaction lock인지 분명한가?
- 모든 central lock 설명이 일곱 칸 분석 틀을 채우는가?
- mutex/latch/transaction lock/MVCC visibility를 owner와 lifetime으로 구분했는가?
- “MVCC lock”을 enum identifier처럼 쓰지 않았는가?
- self-lock의 `self`를 owner의 identity로 설명하고 self-blocking으로 설명하지 않았는가?
- `X_LOCK` 이름만으로 object resource와 transaction resource를 합치지 않았는가?
- class intention mode가 instance lock을 대체한다고 쓰지 않았는가?
- conversion과 escalation을 분리했는가?
- wakeup, grant, business predicate success를 세 단계로 구분했는가?
- plain snapshot reader와 unique/FK observer를 같은 actor로 그리지 않았는가?
- wait 전 release와 wakeup 후 reacquire/recheck를 exact source Claims에 묶었는가?
- inactive publication→unlock ordering을 main/subtransaction과 commit/abort 모두에서 검증했는가?
- self-lock의 per-row lock 절감 효과를 exact applicability와 함께 썼는가?
- lock table restart를 persistent lock replay처럼 설명하지 않았는가?
- deadlock victim abort와 process crash를 혼용하지 않았는가?
- counter 이름만 믿지 않고 increment site를 확인했는가?
- PostgreSQL/MySQL mapping이 이름이 아니라 responsibility flow를 비교하는가?
- `no equivalent`마다 negative-search scope가 있는가?
- 모든 substantive comparison cell에 참여 DB Claims가 있는가?
- 모든 그림에 화면에 보이는 한국어 text alternative가 있는가?
- 각 장에 학습 목표, scenario, intuition, mechanics+Claim IDs, failures, recap, transition이 있는가?
- Quiz가 답을 노출하지 않고 CUBRID-only runnable artifact와 safe cleanup을 갖는가?
- Live Grill map이 8 mastery area와 네 Central Behavior를 모두 덮는가?
- 마지막 장이 source 재열람 없이 구현할 수 있는 total Interface와 conformance tests를 제공하는가?
- central `Unknown` 또는 `Inferred`가 readiness declaration에 정직하게 반영되는가?

## 14. Pedagogy Verdict

이 주제는 “잠금 종류를 나열하는 책”으로 쓰면 self-lock과 MVCC lock의 필요성을 설명하지 못한다. 가장 안정적인 학습 경로는 다음 한 줄이다.

```text
깨질 상태 → primitive 선택 → resource identity → compatibility와 wait
→ MVCC가 줄이는 충돌 → 여전히 남는 logical 충돌
→ MVCCID rendezvous ordering → 세 DBMS의 responsibility placement
→ total reimplementation contract
```

이 순서를 지키면 `self-lock`은 낯선 특수 기능이 아니라 “미완료 inserter의 transaction identity를 observer가 안전하게 기다리고 다시 검사하기 위한 protocol”로 이해할 수 있다. 다만 따옴표 안의 각 구체 단계, mode, caller, ordering, performance 효과는 반드시 pinned CUBRID source Claim과 runtime evidence로 고정해야 한다.
