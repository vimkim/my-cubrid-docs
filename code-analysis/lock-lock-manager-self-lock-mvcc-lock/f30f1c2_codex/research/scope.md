# 연구 범위: CUBRID Lock Manager와 MVCC 잠금

Status: FROZEN

## 한 문장 주제

이 Report Run은 CUBRID Lock Manager의 resource·mode·owner·waiter·lifetime 모델을 재구성하고, MVCC가 일반 read lock을 줄이면서도 class/row lock과 MVCCID self-lock을 필요로 하는 이유를 동일한 동시성 시나리오로 설명한다.

## 독자와 학습 목표

독자는 C/C++, 자료구조, 운영체제의 mutex, SQL transaction과 isolation level을 배운 컴퓨터공학 2학년으로 가정한다. DBMS 내부의 multi-granularity locking, wait-for graph, MVCC version visibility는 처음 접한다고 가정한다.

책을 마친 독자는 다음을 자기 말로 설명할 수 있어야 한다.

1. mutex·latch·transaction lock을 보호 대상과 수명으로 구분한다.
2. CUBRID lock resource key, mode, owner, holder/waiter, conversion, escalation, release를 추적한다.
3. MVCC의 snapshot read가 lock-free에 가까워져도 DDL, writer-writer 충돌, `SELECT ... FOR UPDATE`, unique/FK 검사가 잠금을 요구하는 이유를 설명한다.
4. “MVCC lock”은 하나의 고유 lock mode가 아니라 MVCC 경로에서 선택되는 class/row/transaction lock 정책이라는 점을 설명한다.
5. MVCCID self-lock의 `X_LOCK` holder와 `S_LOCK` waiter가 inserter 종료를 rendezvous하는 과정과 `active publication -> unlock -> wakeup/recheck` 순서를 설명한다.
6. PostgreSQL과 MySQL/InnoDB의 가장 가까운 메커니즘을 `equivalent`, `partial analogy`, `no equivalent`로 구분한다.

## 포함하는 Module과 Interface

### Module A: lock resource와 mode 결정

- `src/transaction/lock_manager.c`, `lock_manager.h`, `lock_table.c`의 외부·내부 Interface
- database/class/instance/transaction resource identity와 hash lookup
- lock mode, compatibility, conversion, class intent lock, escalation
- caller obligation: 올바른 class OID, requested mode, conditional flag, transaction context, timeout
- holder/waiter entry와 transaction hold list의 ownership, allocation, reclamation

### Module B: 획득·대기·교착·해제 lifecycle

- `lock_object`, `lock_internal_perform_lock_object`, wait/suspend/wakeup, conversion, timeout, interrupt
- wait-for graph와 deadlock victim 처리의 Lock Manager 접점
- transaction commit/abort, partial release, `lock_unlock_all`, shutdown cleanup
- fast path, miss/allocation, incompatible wait, retry/recheck, failure path

### Module C: MVCC와 object lock의 역할 분담

- plain snapshot `SELECT`, `SELECT ... FOR UPDATE`, `UPDATE`, `DELETE`, `INSERT`에서의 class/row lock 결정
- query executor → scan manager → locator/heap/B-tree → Lock Manager 호출 경로
- MVCC visibility와 logical transaction lock, page latch의 서로 다른 책임
- write-write 충돌, predicate 재평가, unique/FK 검사, non-MVCC class와의 분기

### Module D: MVCCID self-lock rendezvous

- `LOCK_RESOURCE_TRANSACTION`의 MVCCID key와 inserter의 `X_LOCK`
- lazy MVCCID 발급, `logtb_ensure_mvccid_self_lock`, main/subtransaction 수명
- appended MVCC row의 per-row `X_LOCK` 대체 조건
- unique/FK observer의 `S_LOCK` wait, release, active-state 또는 record 재검사
- self-lock이 일반 object lock과 같은 grant/wait machinery를 재사용하면서도 다른 resource identity를 갖는 이유

## Dependency Seam과 주변 Module

- query policy seam: `src/query/query_executor.c`, `scan_manager.c`
- row/index operation seam: `src/transaction/locator_sr.c`, `src/storage/heap_file.c`, `btree.c`
- transaction/MVCC lifecycle seam: `src/transaction/log_tran_table.c`, `log_manager.c`, `mvcc.c`, `mvcc_table.cpp`
- deadlock seam: `src/transaction/wait_for_graph.c`
- configuration/observability seam: `src/base/system_parameter.c`, `perf_monitor.c`, lock dump와 event log
- PostgreSQL: heavyweight lock manager, relation/tuple/transaction-ID 및 speculative insertion wait
- MySQL/InnoDB: metadata/table intention/record locks, transaction lock wait, read view와 unique/FK checks

## 명시적으로 제외하는 범위

- 모든 SQL 문법과 isolation anomaly의 완전한 목록
- predicate/key-range locking 전체와 serializable 이론의 완전한 증명
- buffer page latch·mutex·lock-free container의 내부 알고리즘 전체
- wait-for graph 구현의 모든 최적화와 모든 victim tie-break 규칙
- WAL, checkpoint, ARIES, vacuum의 전체 설계와 on-disk MVCC record layout
- distributed lock, HA replication lock, client/broker protocol 전체
- PostgreSQL/MySQL 서버 실행 실험
- CUBRID 소스 수정, instrumentation, PR/JIRA/commit/push/publish
- ABI, on-disk byte format, exact error code, exact timing, starvation-free 또는 bit-for-bit 호환성

제외 항목도 Lock Manager Interface의 caller obligation이나 실패·restart 경계를 설명하는 데 필요한 만큼은 다룬다. Lock table은 volatile하므로 crash 뒤 복원되는 persistent lock state를 약속하지 않으며, WAL 자체의 재구현은 이 범위에 포함하지 않는다.

## 세 데이터베이스가 공유하는 시나리오

테이블 `account(id PRIMARY KEY, balance)`에 대해 T1이 기존 행을 갱신하고 새 unique key를 삽입하는 동안 T2가 다음 네 동작을 시도한다고 가정한다.

1. plain snapshot `SELECT`로 기존 행을 읽는다.
2. `SELECT ... FOR UPDATE`로 같은 행을 읽고 쓰기 권리를 예약한다.
3. 같은 행을 `UPDATE`한다.
4. T1이 아직 commit하지 않은 동일 unique key를 `INSERT`한다.

세 DBMS에서 relation/table/class, tuple/record/instance, transaction identity 중 무엇이 resource가 되는지, 누가 기다리고 무엇을 다시 검사하는지, commit/abort가 어떻게 wait를 끝내는지 비교한다.

공통 비교 축은 responsibility와 Module, Interface와 caller obligation, resource identity, owner/lifetime, state transition, compatibility/wait protocol, deadlock/timeout, durability/restart 경계, configuration/observability, 성능 trade-off이다.

## 모든 장이 답해야 하는 질문

1. 보호하려는 논리 상태는 무엇인가?
2. resource key와 owner identity는 무엇인가?
3. 어떤 mode가 왜 선택되고 어떤 mode와 호환되는가?
4. fast path와 slow/wait path는 어디서 갈리는가?
5. wait 전에 무엇을 놓고, wakeup 뒤 무엇을 다시 검사하는가?
6. conversion, escalation, timeout, deadlock, interrupt가 상태를 어떻게 바꾸는가?
7. commit, abort, subtransaction 종료, shutdown에서 누가 해제·회수하는가?
8. MVCC visibility, object lock, self-lock, page latch는 각각 어떤 race를 막는가?
9. source fact, runtime observation, inference, unknown, analogy 중 어떤 근거 등급인가?
10. PostgreSQL/MySQL의 대응은 책임과 불변식까지 같은가, 일부만 비슷한가, 대응이 없는가?

## Central Behaviors

1. `resource-mode-hierarchy`: object/transaction resource identity, lock mode compatibility, class intent hierarchy, conversion과 escalation.
2. `wait-deadlock-release`: incompatible request가 waiter가 되고 timeout/deadlock/interrupt 또는 holder 종료로 깨어나며 transaction 종료가 hold list를 정리하는 lifecycle.
3. `mvcc-lock-policy`: snapshot read, locked read, DML에서 MVCC visibility와 class/row lock이 역할을 나누는 정책과 writer-writer 보호.
4. `mvccid-self-lock-rendezvous`: inserter가 자기 MVCCID에 가진 `X_LOCK`과 unique/FK observer의 `S_LOCK` wait/recheck가 per-row lock 수를 줄이면서 정확성을 보존하는 rendezvous.

각 Central Behavior는 CUBRID/PostgreSQL/MySQL/비교 Claim, 하나 이상의 안전한 CUBRID runtime Experiment, 재현 가능한 Quiz, Book anchor, Live Grill concept에 연결한다.

## Coverage Matrix

| Coverage Obligation | 계획된 답변 위치와 질문 |
|---|---|
| orientation | 01장: 범위, 학습 경로, 핵심 결론, 세 revision과 dirty provenance는 무엇인가? |
| mental-model | 02장: mutex·latch·transaction lock·MVCC visibility를 어떤 보호 대상으로 구분하는가? |
| scope-interface-seams | 03장: caller가 알아야 할 Lock Manager Interface와 query/storage/transaction seam은 무엇인가? |
| data-ownership-lifetime | 04장: resource, holder, waiter, transaction hold list를 누가 만들고 회수하는가? |
| lifecycle-state-machines | 05~06장: request부터 grant/wait/conversion/release까지 legal transition은 무엇인가? |
| core-workflows | 05~08장: fast, miss, wait, retry, failure, MVCC DML, self-lock 흐름은 어떻게 이어지는가? |
| concurrency | 06~08장: mutex/critical section, compatibility, wait/wakeup, recheck, lock ordering, forbidden interleaving은 무엇인가? |
| storage-durability-recovery | 09장: volatile lock table과 persistent MVCC/WAL 상태의 경계, commit/abort/restart cleanup은 무엇인가? |
| policies-algorithms | 05~08장: compatibility, conversion, escalation, victim/timeout, MVCC/self-lock 선택 알고리즘은 무엇인가? |
| errors-resource-pressure | 06·09장: allocation 실패, timeout, deadlock, interrupt, shutdown race의 전파와 cleanup은 무엇인가? |
| performance-observability | 09장: hash contention, waiter cost, row-lock 절감, escalation, counters/dumps/tuning과 측정 한계는 무엇인가? |
| experimental-validation | 10장: 네 Central Behavior를 어떤 owned database와 oracle로 관찰했는가? |
| postgresql-analysis | 11장: heavyweight relation/tuple/transaction-ID mechanism이 같은 시나리오를 어떻게 처리하는가? |
| mysql-analysis | 12장: MySQL server와 InnoDB가 책임을 어떻게 나누고 table/record/trx wait를 수행하는가? |
| cross-database-comparison | 13장: 동일한 책임·resource·wait/recheck를 어떤 analogy class로 매핑하는가? |
| reimplementation-blueprint | 14장: Interface, abstract model, total transitions, 오류, 순서, conformance test를 무엇부터 구현하는가? |
| glossary-evidence-unknowns | 14장: 용어, claim/evidence index, experiment transcript, unknown, compatibility limit, readiness는 무엇인가? |
| teaching-map | 01·10·14장: 각 central behavior와 claim이 Quiz 및 Live Grill mastery에 어떻게 연결되는가? |

## Provenance Freeze

- CUBRID: `/home/vimkim/gh/cb/cubrid-analysis` @ `f30f1c26003e5aa8e93182648e06cad76fc77064` (`WORKTREE`, dirty fingerprint는 `provenance.json` 참조)
- PostgreSQL: `/home/vimkim/gh/pg/postgres` @ `fd2b89854d93d70fe8c9a69d5b8fafd5b9302cfc` (untracked `.omc/`만 존재하는 dirty fingerprint)
- MySQL: `/home/vimkim/gh/mysql/mysql-server` @ `06a5c1c99c377fc41b2eba1ea244e8b220bdc3c8` (clean)

이 범위는 SHA-256으로 고정한다. source가 새로운 필수 seam을 드러내면 넓힌 이유를 기록하되 검증을 통과하려고 의무를 조용히 줄이지 않는다.
