# 연구 범위: CBRD-27157을 이해하기 위한 CUBRID 잠금 입문

## 한 문장 주제

이 Report Run은 데이터베이스 잠금의 가장 기초적인 모델에서 출발하여 CUBRID의 object lock, transaction MVCCID self-lock, `BU_LOCK`, server-side loaddb의 session/worker transaction 분리, 그리고 OOS lazy file creation이 CBRD-27157 회귀를 드러낸 이유까지 재구성한다.

## 독자와 학습 목표

독자는 C/C++, 자료구조, 운영체제의 mutex 개념, SQL transaction의 `COMMIT`/`ROLLBACK`을 배운 컴퓨터공학 2학년으로 가정한다. DBMS 내부의 lock manager, MVCC, intent lock, loaddb 구현은 처음 접한다고 가정한다.

책을 마친 독자는 다음을 자기 말로 설명할 수 있어야 한다.

1. mutex/latch/transaction lock이 각각 무엇을 보호하고 언제 풀리는지 구분한다.
2. lock을 볼 때 resource key, mode, owner, waiter, lifetime을 따로 묻는다.
3. CUBRID class/instance object lock의 계층과 `BU_LOCK` compatibility를 읽는다.
4. server-side loaddb의 session transaction과 worker batch transaction이 서로 다른 lock을 소유하는 이유를 그린다.
5. MVCCID self-lock의 inserter/waiter rendezvous와 `observable INSID => X self-lock` 불변식을 설명한다.
6. OOS file lazy creation에서 CBRD-27157 assert까지의 호출 경로와 uniform self-lock 수정의 경계를 설명한다.
7. PostgreSQL과 MySQL/InnoDB의 가장 가까운 메커니즘을 CUBRID와 같다고 과장하지 않고 비교한다.

## 포함하는 Module과 Interface

### Module A: lock resource와 loaddb 소유권

- CUBRID lock resource identity, lock mode, compatibility, holder/waiter, conversion, release
- class/instance object lock hierarchy와 intent mode의 목적
- `BU_LOCK`의 정확한 compatibility와 bulk loading 역할
- `lock_object`, `lock_internal_perform_lock_object`, object-lock lookup redirect
- server-side loaddb session transaction과 worker batch transaction의 생성, commit/abort, lock ownership
- transaction 종료 시 `lock_unlock_all`을 통한 lock lifetime 종료

### Module B: MVCCID self-lock rendezvous

- `tran_index`, transaction ID, MVCCID, INSID의 서로 다른 역할
- MVCCID resource에 inserter가 잡는 `X_LOCK`과 unique/FK 검사자가 요청하는 `S_LOCK`
- lazy MVCCID allocation, self-lock acquisition/ensure, wait/recheck, commit/abort release
- bulk insert가 INSID를 생략하는 조건과 현재 observer 부재, 미래 불변식의 차이

### Module C: CBRD-27157 end-to-end 회귀

- OOS demotion은 회귀의 잠금 원인이 아니라 숨은 MVCCID 발급 경로를 여는 trigger라는 점
- `server_object_loader::finish_line`부터 `file_create(FILE_OOS)`, MVCCID self-lock, debug assert까지의 호출 흐름
- 기존 CBRD-23375 object-lock 우회 계약과 CBRD-26942 transaction self-lock 계약의 충돌
- PR #7588의 uniform self-lock 수정이 허용하는 것과 여전히 금지하는 것
- debug/release 차이, 실패/cleanup, 성능 및 관찰 지점

## dependency seam과 주변 Module

- loaddb worker lifecycle: `src/loaddb/load_session.cpp`, `load_server_loader.cpp`
- locator/bulk insert seam: `src/transaction/locator_sr.c`
- heap/OOS/file creation seam: `src/storage/heap_file.c`, `heap_oos.cpp`, `oos_file.cpp`, `file_manager.c`
- lock/MVCC transaction seam: `src/transaction/lock_manager.c`, `lock_table.c`, `log_tran_table.c`, `transaction_sr.c`
- PostgreSQL: heavyweight relation locks, virtual/transaction ID locks, `COPY FROM`
- MySQL/InnoDB: metadata/table intention locks, record/index locks, transaction wait/release, `LOAD DATA`

## 명시적으로 제외하는 범위

- lock manager 전체 hash table 및 wait-for graph의 모든 최적화 세부 구현
- 모든 deadlock victim 선정 정책과 lock escalation의 완전한 재구현
- MVCC snapshot, vacuum, WAL, crash recovery 전체 알고리즘
- OOS binary layout, chunk CRUD, vacuum reclamation 전체 설계
- PostgreSQL/MySQL 서버 실행 실험
- CBRD-27157 수정 코드 변경, PR publish, JIRA description 변경
- ABI, on-disk layout, bit-for-bit 호환성

제외 항목도 CBRD-27157 설명에 필요한 경계에서는 다룬다. 예를 들어 transaction 종료가 self-lock을 해제한다는 사실은 설명하지만 ARIES 복구 전체는 설명하지 않는다.

## 세 데이터베이스가 공유하는 시나리오

큰 가변 길이 값과 unique key를 가진 행을 bulk load한다고 가정한다. 로더는 테이블의 구조와 일반 데이터 접근을 조정해야 하고, 아직 끝나지 않은 inserter의 unique key를 다른 transaction이 발견했을 때 올바르게 기다리거나 다시 검사해야 한다. 세 DBMS가 이 두 책임을 어느 resource, owner, lifetime에 배치하는지 비교한다.

비교 축은 responsibility/module boundary, interface/caller obligation, resource identity, owner/lifetime, compatibility/wait protocol, commit/abort cleanup, failure behavior, performance/observability이다. 대응은 `equivalent`, `partial analogy`, `no equivalent` 중 하나로 표시한다.

## 모든 장이 답해야 하는 질문

1. 보호하려는 상태는 무엇인가?
2. lock resource key는 무엇인가?
3. 어떤 transaction이 어떤 mode를 소유하는가?
4. 누구와 호환되고 누가 기다리는가?
5. 언제 획득하고 언제 해제하는가?
6. wait 뒤 무엇을 다시 검사하는가?
7. 실패, abort, shutdown에서 남는 상태는 무엇인가?
8. 이 동작은 source fact, runtime observation, inference, analogy 중 무엇인가?
9. PostgreSQL/MySQL의 대응 메커니즘은 정말 같은가, 일부만 비슷한가, 대응이 없는가?
10. CBRD-27157에서 이 개념을 모르면 어떤 잘못된 결론을 내리기 쉬운가?

## Central Behaviors

1. `lock-resource-owner-lifecycle`: resource key, mode, compatibility, transaction owner, wait, commit/abort release를 한 덩어리의 Interface로 이해하고 `BU_LOCK`과 MVCCID transaction lock을 구분한다.
2. `mvccid-self-lock-rendezvous`: inserter의 MVCCID `X_LOCK`, unique/FK waiter의 `S_LOCK`, 재검사, release로 이어지는 rendezvous와 불변식을 이해한다.
3. `loaddb-oos-regression`: session `BU_LOCK`, worker batch transaction, OOS lazy file creation, MVCCID 발급, debug assert, uniform self-lock 수정까지의 end-to-end 인과를 이해한다.

각 Central Behavior는 CUBRID/PostgreSQL/MySQL/비교 Claim, 안전한 CUBRID runtime Experiment, 재현 가능한 Quiz, Book anchor, Live Grill concept에 연결한다.

## Coverage Matrix 초안

| Coverage Obligation | 계획된 답변 위치 |
|---|---|
| orientation | 01 읽기 안내와 provenance |
| mental-model | 02 잠금의 다섯 질문 |
| scope-interface-seams | 03 lock manager 지도, 04 loaddb 경계 |
| data-ownership-lifetime | 03 resource/holder/waiter, 04 transaction owner |
| lifecycle-state-machines | 04 batch lifecycle, 05 self-lock lifecycle |
| core-workflows | 05 rendezvous, 06 crash call flow |
| concurrency | 03 compatibility, 05 wait/recheck, 07 interleaving |
| storage-durability-recovery | 07 commit/abort/restart 경계와 이 범위의 Not applicable 설명 |
| policies-algorithms | 03 compatibility lookup, 05 self-lock policy, 06 assert policy |
| errors-resource-pressure | 07 timeout/deadlock/assert/abort/cleanup |
| performance-observability | 07 per-row lock 대 transaction self-lock 비용과 진단 지점 |
| experimental-validation | 10 세 CUBRID 실험 |
| postgresql-analysis | 08 PostgreSQL 비교 |
| mysql-analysis | 09 MySQL/InnoDB 비교 |
| cross-database-comparison | 10 공통 시나리오 비교표 |
| reimplementation-blueprint | 11 최소 재구현 설계와 conformance tests |
| glossary-evidence-unknowns | 11 용어·근거·한계·readiness |
| teaching-map | 01 학습 경로, 10 Quiz, 11 mastery map |

## Provenance Freeze

- CUBRID: `/home/vimkim/gh/cb/feat-oos-fix-regression` @ `f11fc42594732c263d8f10101f9df73a21346ee9` (`WORKTREE` dirty provenance는 `provenance.json` 참조)
- PostgreSQL: `/home/vimkim/gh/pg/postgres` @ `fd2b89854d93d70fe8c9a69d5b8fafd5b9302cfc`
- MySQL: `/home/vimkim/gh/mysql/mysql-server` @ `06a5c1c99c377fc41b2eba1ea244e8b220bdc3c8`

이 범위는 hash로 고정한다. source가 새로운 경계를 드러내면 넓힌 이유를 기록할 수 있지만, 검증 통과를 위해 의무를 조용히 줄이지 않는다.
