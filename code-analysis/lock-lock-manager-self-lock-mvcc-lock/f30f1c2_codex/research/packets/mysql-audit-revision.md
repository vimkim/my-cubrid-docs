# MySQL/InnoDB comparator 독립 감사 보강안

## 감사 메타데이터

- 역할: `Role 3 — MySQL Comparator, independent audit revision`
- 주제: `CUBRID lock과 lock manager — self lock 및 MVCC lock의 필요성`
- frozen scope: `research/scope.md`
- frozen scope SHA-256: `711d1a0f5bfebdbe1b55b4299973efc353d90636e2f00fc807f51d031766a839`
- 감사 대상 MySQL root: `/home/vimkim/gh/mysql/mysql-server`
- MySQL revision: `06a5c1c99c377fc41b2eba1ea244e8b220bdc3c8`
- MySQL worktree: `clean` (`git status --porcelain=v1` 출력 없음)
- evidence cutoff: `2026-08-11T09:59:55Z`
- evidence mode: `source-only`; MySQL server runtime과 외부 문서는 사용하지 않았다.
- 현재 MySQL 장 SHA-256: `878d00eaba4e7ba8beb08542dd3cf17f068ea0e4465aa896a2814811b6fd42bd`
- 현재 ledger SHA-256: `228f9347263601935e6978d0b1ce22418613075417342b14f1e9afe6e572acd7`
- 현재 report manifest SHA-256: `1a4586f96e3c33ace1e5fce63413175ca1b12f5863e3c929c426d4187c28968c`
- 허용 출력: 이 파일과 `mysql-added-claims.jsonl`만 생성했다. Book, `evidence/claims.jsonl`, `report.json`, 실험, 퀴즈, 소스는 수정하지 않았다.

`mysql-added-claims.jsonl`이 신규 source reference의 규범적 기록이다. 각 JSON object에는 고정 revision, 전체 파일 SHA-256, 실제 symbol을 포함하는 line range, `COMMIT` evidence state, 제한, 제안 anchor가 들어 있다. 이 문서는 그 claim을 Book에 안전하게 배치하기 위한 한국어 내용 설계다.

## 감사 결과

현재 ledger의 MySQL claim은 `MYSQL-C001`, `C002`, `C010`, `C011`, `C020`, `C021`, `C030`, `C031` 여덟 개다. 현재 12장은 owner 분리, plain/locking read 개요, implicit record X, wait edge, unique/FK, escalation 음성 결론까지는 다루지만 다음 책임이 비어 있다.

- MDL ticket owner와 statement/transaction/explicit lifetime
- MDL 자체 acquire/wait/deadlock/release와 MDL–InnoDB 교차 cycle 경계
- lock wait 관련 설정, 오류별 rollback 범위, 자원 압력
- `lock_sys` startup/shutdown과 buffer-pool 연동 sizing
- XA prepare 내구성, connection detach, crash recovery, prepared transaction 보존
- detached/recovered XA를 위한 server MDL backup
- lock 객체 절약 구조와 관측 인터페이스의 snapshot 한계
- 정상 실행 lock queue와 recovery reconstruction을 구별하는 durability 경계

신규 claim 후보 21개를 `MYSQL-C003,C004,C005,C006,C007,C008,C009,C012,C013,C014,C015,C016,C017,C018,C019,C022,C023,C024,C025,C028,C033`에 배치했다. `C033`만 의도적으로 `unknown/UNKNOWN`인 비중심 경계이며, 나머지는 `source/SOURCE-CONFIRMED`다.

## Book용 권장 구조와 anchor

아래 문장은 그대로 옮기라는 최종 원고가 아니라, 각 실질 주장을 claim으로 닫은 내용 골격이다. 괄호의 ID를 해당 `<section data-claim-id>` 또는 가장 가까운 문단/표에 연결한다.

### 1. `#mysql-owner-boundary` — 두 lock manager를 먼저 분리한다

- MySQL server의 MDL은 metadata object의 사용과 DDL을 조정하고, InnoDB는 table intention 및 index record/gap data lock을 담당한다. 둘은 owner, 자료구조, wait graph가 다르다. `[MYSQL-C001]`
- MDL ticket의 owner는 connection별 `MDL_context`이며, statement/transaction/explicit duration은 자동 해제 경계를 다르게 만든다. `[MYSQL-C003]`
- InnoDB `lock_t`의 owner는 `trx_t`이고 transaction의 lock list/heap에 연결된다. 실제 payload는 table 또는 page+record bitmap이다. `[MYSQL-C002][MYSQL-C004]`

권장 작은 도식:

```text
THD / MDL_context                         trx_t / trx_lock_t
  └─ MDL_ticket ──> MDL_lock                └─ lock_t ──> table | page+record bitmap
       metadata namespace                         InnoDB data resource
```

도식의 왼쪽 owner/lifetime은 `MYSQL-C003`, 오른쪽 owner/resource는 `MYSQL-C002/C004`, 두 계층이 다르다는 연결선은 `MYSQL-C001`이 담당한다.

### 2. `#mysql-mdl-lifetime` — MDL mode와 수명

권장 표:

| 축 | Book에 넣을 안전한 내용 | claim |
|---|---|---|
| 대표 read mode | 일반 `SELECT`는 `MDL_SHARED_READ` 의미 범주다. | `MYSQL-C003` |
| 대표 write mode | INSERT/UPDATE/DELETE와 `SELECT ... FOR UPDATE`는 `MDL_SHARED_WRITE` 의미 범주다. | `MYSQL-C003` |
| DDL mode | 강한 DDL exclusion은 `MDL_EXCLUSIVE`다. | `MYSQL-C003` |
| statement duration | statement 또는 transaction 종료 때 자동 해제된다. | `MYSQL-C003` |
| transaction duration | transaction 종료 때 자동 해제된다. | `MYSQL-C003` |
| explicit duration | statement/transaction을 넘어가며 명시 해제가 필요하다. | `MYSQL-C003` |

모든 SQL 문법별 MDL request를 전수 매핑했다는 표현은 피한다. 이 표는 enum에 명시된 대표 의미와 lifetime만 주장한다.

### 3. `#mysql-innodb-lock-lifetime` — InnoDB lock owner와 release

- transaction은 `trx_locks`, `lock_heap`, `n_rec_locks`를 소유하고, commit/rollback 종료 경로는 queue에서 lock을 제거해 waiter를 진행시킨 뒤 heap을 한 번에 비운다. `[MYSQL-C004][MYSQL-C011]`
- 같은 page의 여러 record request는 bitmap 하나에 합쳐질 수 있다. 따라서 “row 하나당 lock 객체 하나”라는 모델은 맞지 않는다. `[MYSQL-C018]`
- 변경 fast path의 `impl=true`는 충돌이 없으면 explicit `lock_t` 생성을 생략한다. 이것이 implicit record X의 메모리 절약 동기다. `[MYSQL-C018][MYSQL-C025][MYSQL-C030]`

### 4. `#mysql-wait-lifecycle` — acquire, wait, wake, release

권장 call path:

```text
server MDL
open_table_get_mdl_lock
  → MDL_context::acquire_lock
  → MDL_lock::m_waiting.add_ticket
  → MDL_context::find_deadlock
  → MDL_context::release_lock / reschedule_waiters
  [MYSQL-C001][MYSQL-C005]

InnoDB data lock
row_search_mvcc | row_upd_step | row_ins_step
  → lock_table + record lock/check
  → waiting lock_t + wait_lock + blocking_trx
  → lock_wait_suspend_thread
  → lock_wait_find_and_handle_deadlocks | timeout cancel
  → commit/release → waiter wake
  [MYSQL-C010][MYSQL-C011][MYSQL-C023][MYSQL-C024][MYSQL-C025]
```

`blocking_trx`는 actual lock resource가 아니라 wait-for edge다. 이 구분은 self-lock 비등가 결론의 전제다. `[MYSQL-C010][MYSQL-C030]`

### 5. `#mysql-deadlock-boundary` — 두 detector를 합치지 않는다

- MDL 내부 cycle은 MDL detector가 victim을 고른다. `[MYSQL-C005]`
- InnoDB table/record wait는 InnoDB가 transaction edge snapshot에서 cycle을 찾는다. `[MYSQL-C010]`
- MDL wait와 InnoDB row wait가 섞인 cycle은 MDL graph가 보지 못하는 edge를 포함할 수 있고, 해당 source comment는 timeout 해소를 명시한다. `[MYSQL-C006]`

따라서 “MySQL은 모든 lock을 하나의 전역 wait-for graph로 탐지한다”는 문장을 넣으면 안 된다. `[MYSQL-C001][MYSQL-C006]`

### 6. `#mysql-mvcc-operation-matrix` — 같은 account scenario의 네 동작

권장 scenario: `account(id=1,balance=100)`에서 T1이 갱신 중이고 T2/T3/T4가 같은 논리 계좌를 읽거나 갱신·삽입한다.

| actor / SQL 동작 | server MDL | InnoDB table/data policy | 대기 또는 결과 | claim |
|---|---|---|---|---|
| T1 `UPDATE account SET balance=90 WHERE id=1` | `MDL_SHARED_WRITE` 의미 범주 | table IX 후 clustered/secondary modify X 검사, clustered update undo 기록; 결과 record는 T1의 implicit X owner가 될 수 있다. | 충돌이 없으면 explicit record object가 생략될 수 있다. | `MYSQL-C003,C024,C030` |
| T2 plain `SELECT ... WHERE id=1` | 보통 `MDL_SHARED_READ` | `LOCK_NONE` branch가 read view를 열고 `DB_TRX_ID` 가시성을 판정한다. | T1의 미완료 버전을 그대로 읽는 대신 snapshot에 맞는 version을 찾는 책임이다. | `MYSQL-C003,C020,C022` |
| T3 `SELECT ... FOR UPDATE` | `MDL_SHARED_WRITE` 의미 범주 | table IX + record/gap X. T1의 implicit owner가 발견되면 그 record에 explicit X가 materialize되고 T3 wait edge가 생긴다. | wait/deadlock/timeout 뒤 재개 또는 오류다. | `MYSQL-C003,C010,C023,C030` |
| T4 동일 unique/FK key `INSERT` | `MDL_SHARED_WRITE` 의미 범주 | table IX; candidate record/gap에 S 또는 X를 요청한다. 새 record의 transaction ID가 implicit owner를 표현한다. | wait가 끝나면 insert graph가 다시 실행되어 duplicate/FK를 재판정한다. | `MYSQL-C003,C021,C025` |
| T1 commit | transaction-duration MDL 해제 경계 | commit state/active-set을 게시하고 explicit locks를 제거한다. | waiter가 wake되어 자기 조건을 다시 판정한다. | `MYSQL-C003,C011,C021` |

이 표에서 `LOCK_NONE`을 InnoDB lock mode 또는 “MDL도 없다”로 쓰지 않는다. 이는 consistent-read policy marker다. `[MYSQL-C020][MYSQL-C022]`

### 7. `#mysql-xa-prepared` — prepare는 commit과 다르다

- XA prepare는 undo state를 file-based PREPARED로 만들고 LSN을 durability 설정에 따라 flush한 뒤 in-memory state도 PREPARED로 전환한다. `[MYSQL-C012]`
- READ COMMITTED 이하에서 prepare가 조기 해제하는 것은 전체 S/X lock이 아니라 gap 부분이다. `[MYSQL-C012]`
- 지속 데이터를 변경한 PREPARED transaction은 connection close 때 rollback/free되지 않고 session에서 분리되어 향후 XA COMMIT/ROLLBACK 결정을 기다린다. non-prepared transaction은 close 시 rollback된다. `[MYSQL-C013]`

`prepare 시 모든 lock이 풀린다` 또는 `prepared transaction은 원래 THD가 계속 소유한다`는 설명은 금지한다. `[MYSQL-C012][MYSQL-C013]`

### 8. `#mysql-xa-mdl-backup` — server MDL의 prepared lifetime

- THD가 disconnected prepared XA를 정리할 때 `MDL_context_backup_manager`는 transaction-duration MDL tickets를 XID별 backup context로 clone한다. `[MYSQL-C016]`
- restart recovery에는 원래 mode 정보가 없으므로 modified table 목록에 보수적인 `MDL_SHARED_WRITE` request를 acquire해 backup context를 구성한다. `[MYSQL-C016]`
- 다른 THD가 XA second phase를 수행할 때 backup tickets를 그 THD의 `MDL_context`로 복원한다. `[MYSQL-C016]`

이 section은 server MDL 책임이고 다음 section의 InnoDB IX resurrection과 같은 자료구조가 아니다. `[MYSQL-C001][MYSQL-C014][MYSQL-C016]`

### 9. `#mysql-restart-reconstruction` — recovery에서 무엇을 복구하는가

권장 call path:

```text
trx_lists_init_at_db_start
  → trx_resurrect_insert / trx_resurrect_update
  → trx_resurrect_table_ids (undo record의 table_id 수집)
srv_dict_recover_on_restart
  → trx_resurrect_locks
  → lock_table_ix_resurrect
  [MYSQL-C014][MYSQL-C015]
```

- recovered prepared transaction은 PREPARED/XID를 유지하고 recovery API에 보고되며 background rollback 대상에서 제외된다. `[MYSQL-C015]`
- recovered prepared/DDL transaction에 대해 source-confirmed된 data-lock reconstruction은 undo-derived modified table의 IX lock이다. `[MYSQL-C014]`
- 정상 실행 중의 개별 `lock_t` queue나 waiter order가 그대로 디스크에서 재생된다고 말하면 안 된다. `[MYSQL-C028][MYSQL-C033]`

### 10. `#mysql-startup-shutdown` — lock_sys의 프로세스 수명

- startup은 `trx_sys_create()` 뒤 `lock_sys_create()`를 호출해 hash/slots/mutex/event를 메모리에 만든다. `[MYSQL-C009]`
- shutdown은 변경 생산 중단, buffer flush, shutdown LSN 기록, file close 뒤 resource cleanup 단계에서 `trx_sys_close()` 다음 `lock_sys_close()`를 호출한다. `[MYSQL-C009]`
- 이 순서는 runtime lock manager 수명에 대한 근거이지, individual lock queue를 WAL record로 지속시킨다는 근거가 아니다. `[MYSQL-C028]`

### 11. `#mysql-errors-config` — 설정과 실패 의미

| knob/error | 안전한 설명 | claim |
|---|---|---|
| `innodb_lock_wait_timeout` | session timeout이며 source default는 50초다. 매우 큰 값은 timeout을 사실상 끈다. | `MYSQL-C007` |
| `innodb_deadlock_detect` | default ON; OFF이면 deadlock도 timeout에 의존한다. | `MYSQL-C007` |
| `innodb_rollback_on_timeout` | read-only, default OFF; OFF에서는 timeout이 기본적으로 statement rollback, ON이면 whole transaction rollback이다. | `MYSQL-C007` |
| `DB_DEADLOCK` | whole transaction rollback 범주다. | `MYSQL-C007` |
| `DB_LOCK_TABLE_FULL` | whole transaction rollback 범주다. | `MYSQL-C008` |
| connection kill | pending InnoDB lock request를 cancel/release한다. | 아래 추가 조사 메모 참조; 본 보강 JSONL에는 독립 claim을 만들지 않았으므로 Book 핵심 표에는 넣지 않는 편이 안전하다. |

마지막 행은 `ha_innodb.cc:6512-6525`에서 확인했지만 신규 claim으로 승격하지 않았다. Book에 넣으려면 main writer가 별도 claim을 추가해야 한다.

### 12. `#mysql-resource-pressure` — escalation이 아니라 오류 경계

- 고정 revision과 기록한 검색 범위에서는 record-count 기반 table escalation 경로가 확인되지 않았다. `[MYSQL-C008]`
- `trx_locks`가 10000개보다 많고 buffer pool이 running-out 상태이면 `DB_LOCK_TABLE_FULL`로 실패하며 whole transaction rollback 표시가 이어진다. `[MYSQL-C008]`
- lock hash table의 cell 수는 buffer pool page 수의 5배로 계산되고 큰 buffer resize에 맞춰 재조정된다. 이것은 hash sizing 식이며 lock memory hard cap이나 row-lock quota가 아니다. `[MYSQL-C017]`

### 13. `#mysql-performance` — lock object 비용을 줄이는 세 장치

| 장치 | 비용 모델상 의미 | claim |
|---|---|---|
| page bitmap | 같은 page의 여러 record request가 lock object 하나를 공유할 수 있다. | `MYSQL-C018` |
| implicit record X | uncontended modification은 explicit `lock_t` 생성을 건너뛸 수 있다. | `MYSQL-C018,C025,C030` |
| transaction lock heap | release 후 object별 free 대신 heap을 한 번에 비운다. | `MYSQL-C004,C018` |
| buffer-pool 연동 hash sizing | hash cell 수를 page count에 비례시켜 startup/resize한다. | `MYSQL-C017` |

실제 throughput, 메모리 절감률, latch contention 수치는 runtime으로 검증하지 않았으므로 숫자를 만들지 않는다.

### 14. `#mysql-observability` — 무엇을 볼 수 있고 snapshot은 어디까지인가

- monitor counter는 deadlock, false-positive candidate, graph rounds, waiting threads, timeout, record/table wait/request/create/remove/current count를 노출한다. `[MYSQL-C019]`
- Performance Schema `data_locks`/`data_lock_waits` iterator는 lock_sys shard를 table lock, record hash bucket 순으로 restartable batch scan한다. `[MYSQL-C019]`
- 이 방식은 mutex hold time과 메모리를 제한하는 대신 결과가 전체 원자적 snapshot은 아니며 chunk 단위로만 일관적이다. `[MYSQL-C019]`
- transaction status에는 lock struct count, lock heap bytes, row lock count가 나온다. `[MYSQL-C019]`

### 15. `#mysql-self-lock-gap` — CUBRID MVCCID self-lock의 direct equivalent가 없는 이유

결론을 네 단계로 제시하는 것이 안전하다.

1. InnoDB의 양의 resource model은 table과 record다. record는 page+heap bitmap이고 owner는 `trx_t`다. `[MYSQL-C002][MYSQL-C004][MYSQL-C031]`
2. `DB_TRX_ID`는 개별 clustered record의 implicit X owner를 찾는 단서이며, contention 시 그 **record resource**에 explicit X가 materialize된다. `[MYSQL-C025][MYSQL-C030]`
3. `blocking_trx`는 requester가 blocker transaction을 기다린다는 edge이지, transaction ID라는 lock resource가 아니다. `[MYSQL-C010][MYSQL-C030]`
4. 따라서 unfinished writer를 기다리게 하고 explicit 객체를 줄인다는 목적은 닮았지만, CUBRID의 transaction MVCCID S/X self-lock과 동일한 rendezvous key는 없다. `[MYSQL-C031]`

Nearest analogy 표:

| CUBRID 질문 | MySQL에서 가장 가까운 것 | 분류 | claim |
|---|---|---|---|
| 내 transaction 자신을 MVCCID 자원에 X-lock하는가 | 직접 대응 없음 | no equivalent | `MYSQL-C031` |
| 다른 transaction이 미완료 writer를 기다리는가 | `blocking_trx` wait edge + waiting record `lock_t` | 책임 수준 partial analogy | `MYSQL-C010,C030` |
| uncontended write마다 explicit lock object를 만드는가 | implicit record X라면 생략 가능 | 구현 목적 partial analogy | `MYSQL-C018,C025,C030` |
| unique/FK 충돌 뒤 재판정하는가 | candidate record/gap lock 후 insert graph retry | 책임 수준 partial analogy | `MYSQL-C021` |
| aggregation key가 transaction ID인가 | 아니며 실제 data resource는 table/record다 | semantic gap | `MYSQL-C002,C030,C031` |
| XA prepared가 session을 넘어 lock 책임을 유지하는가 | InnoDB prepared trx detach + server MDL backup | lifecycle analogy일 뿐 self-lock 대응 아님 | `MYSQL-C013,C016` |

### 16. `#mysql-durability-boundary` — durability와 lock reconstruction을 분리한다

- transaction의 prepared 여부는 undo/LSN으로 file-based state가 되지만, 정상 runtime `lock_sys`의 slots/queues는 메모리에서 생성·파기된다. `[MYSQL-C009][MYSQL-C012][MYSQL-C028]`
- restart가 재구성하는 table IX와 server MDL backup은 transaction/modified-table metadata에서 다시 만들어지는 책임이다. `[MYSQL-C014][MYSQL-C016][MYSQL-C028]`
- 따라서 “모든 lock이 durable하다”도, “prepare 후 lock 책임이 모두 사라진다”도 틀린 압축이다. `[MYSQL-C012][MYSQL-C014][MYSQL-C016][MYSQL-C028]`

### 17. `#mysql-na-unknowns` — N/A와 unknown을 명시한다

| 항목 | 상태 | 경계 | claim |
|---|---|---|---|
| CUBRID식 transaction MVCCID S/X resource | N/A / direct equivalent 없음 | pinned server/InnoDB resource model 및 강한 음성 검색 범위 | `MYSQL-C031` |
| record-count table escalation | no equivalent found | pinned revision 및 명시한 디렉터리/검색식에 한정 | `MYSQL-C008` |
| MDL+InnoDB 통합 deadlock detector | N/A | cross-edge cycle은 timeout 경계가 존재 | `MYSQL-C006` |
| runtime `lock_t` wait queue 자체의 durable representation | N/A로 해석하는 것이 안전 | in-memory create/close와 별도 IX reconstruction만 source-confirmed | `MYSQL-C028` |
| crash 전 record waiter 순서·fairness·starvation의 동일 재생 | unknown | server runtime/crash experiment와 모든 serializer 역추적 미수행 | `MYSQL-C033` |
| 모든 isolation별 gap/next-key 조합 | scope-excluded | 공통 LOCK_NONE/S/X policy와 대표 예만 추적 | `MYSQL-C020,C021,C022,C023` |
| 성능 수치와 starvation 보장 | unknown / 측정 안 함 | source layout만 확인, benchmark 없음 | `MYSQL-C018,C019,C033` |

`MYSQL-C033`은 중심 결론의 증거로 쓰지 말고, 독자의 recovery/fairness 과잉 일반화를 막는 boundary disclosure로만 둔다.

## Strong negative search 기록

고정 revision에서 다음 검색을 수행했다.

```text
rg -n -i "mvccid|mvcc_id|mvcc id|self[-_ ]?lock|transaction[-_ ]?id[-_ ]?lock|trx[-_ ]?id[-_ ]?lock" \
  storage/innobase sql include
→ 0 matches

rg -n -i "lock escalation|lock_escalat|escalat(e|ion|ing).*lock|lock.*escalat(e|ion|ing)" \
  storage/innobase/lock storage/innobase/row storage/innobase/trx storage/innobase/include sql include
→ 0 matches
```

음성 검색만으로 비등가를 선언하지 않았다. 양의 구조 근거는 `lock0lock.h:959-1007`의 `LOCK_TABLE/LOCK_REC`, `lock0priv.h:53-171`의 table/record payload와 owner, `lock0lock.cc:5137-5195`의 implicit-to-explicit **record** conversion, `trx0trx.h:396-455`의 `blocking_trx/wait_lock` edge다. 이 결론은 기존 `MYSQL-C030/C031`과 신규 `MYSQL-C004/C025`가 함께 닫는다.

## 정확한 핵심 call path와 claim source 범위

아래는 감사 시 확인한 함수 연결이다. 각 range/hash의 authoritative 값은 `mysql-added-claims.jsonl`의 해당 claim에 있다.

| 책임 | call path | exact range를 가진 claim |
|---|---|---|
| MDL owner/lifetime | `MDL_context` → ticket store → `release_transactional_locks` | `MYSQL-C003` |
| MDL wait/deadlock/release | `MDL_context::acquire_lock` → `m_waiting.add_ticket` → `find_deadlock` → `release_lock` | `MYSQL-C005` |
| MDL/InnoDB cross-cycle | `open_table_get_mdl_lock`의 invisible-edge 분기 | `MYSQL-C006` |
| InnoDB trx ownership/release | `trx_lock_t::trx_locks` → `lock_trx_release_locks` → `mem_heap_empty` | `MYSQL-C004` |
| consistent read | `row_search_mvcc` → `trx_assign_read_view` → `ReadView::prepare/changes_visible` | `MYSQL-C022` |
| locking read | `row_search_mvcc` → `lock_table(IS/IX)` → `sel_set_rec_lock(S/X)` | `MYSQL-C023` |
| update | `row_upd_step` → `lock_table(IX)` → `btr_cur_upd_lock_and_undo` → record modify check | `MYSQL-C024` |
| insert implicit owner | `row_ins_step` → `lock_table(IX)`/trx-id buffer → `lock_rec_lock_fast(impl=true)` | `MYSQL-C025` |
| prepare | `trx_prepare_low` → undo PREPARED/mtr commit → `trx_prepare` → selective gap release/flush | `MYSQL-C012` |
| disconnect | `innobase_close_connection` → `trx_disconnect_prepared` → `trx_disconnect_from_mysql` | `MYSQL-C013` |
| InnoDB restart | `trx_resurrect_table_ids` → `trx_resurrect_locks` → `lock_table_ix_resurrect` | `MYSQL-C014` |
| recovered XA retention | `trx_resurrect_insert/update` → `trx_recover_for_mysql`; rollback switch leaves PREPARED | `MYSQL-C015` |
| server MDL XA lifetime | `THD::cleanup`/recovery → `MDL_context_backup_manager::create_backup` → `restore_backup` | `MYSQL-C016` |
| lock_sys process lifetime | `srv_start` → `lock_sys_create`; shutdown cleanup → `lock_sys_close` | `MYSQL-C009` |
| sizing | InnoDB init/buffer resize → `srv_lock_table_size` → `lock_sys_resize` | `MYSQL-C017` |
| observability | monitor counters + `Innodb_data_lock_iterator` + `trx_print_low` | `MYSQL-C019` |

## 통합 지침

1. Main writer가 `mysql-added-claims.jsonl` 중 채택할 claim만 `evidence/claims.jsonl`에 append한다. 기존 ID의 의미를 바꾸거나 덮어쓰지 않는다.
2. 이 문서의 제안 anchor를 12장에 만들고, 채택한 claim의 `report_locations`와 실제 `<section id>`를 일치시킨다.
3. 표의 각 substantive cell에 위 ID를 포함하는 section-level `data-claim-id` 또는 동등한 추적 연결을 둔다.
4. `MYSQL-C033`은 비중심 unknown disclosure다. readiness를 위해 숨기지 말되 self-lock 비등가의 전제로 사용하지 않는다.
5. Book과 ledger 변경 후 main writer가 claim validator, report validator, link checker를 다시 실행해야 한다. 이 child audit는 그 파일들을 수정하지 않았다.

## 파일 hash 보강 목록

이번 보강에서 새로 직접 사용한 파일의 전체 SHA-256은 다음과 같다. 기존 packet에 이미 있던 파일은 JSONL source refs에서 다시 자체 완결적으로 반복했다.

| path | SHA-256 |
|---|---|
| `storage/innobase/srv/srv0start.cc` | `4f0152b9ca16e7c151063a23a513bdf51ea7fe619d08192128fa35b39bcbd626` |
| `storage/innobase/buf/buf0buf.cc` | `a3e11712993f0542f1e173d08c047637aaeb63293cdf9b0c139dbb593a38e793` |
| `storage/innobase/trx/trx0roll.cc` | `76c46660c6ced1ac4b26a0b40469c45ab2108875ee6a844aaa8a2df741512d36` |
| `sql/mdl_context_backup.h` | `49b829f50e028b49c470dc244d9f085ad7ec8c1ad62b0c3fa057741ad324c7cf` |
| `sql/mdl_context_backup.cc` | `0d1c4f7be1d877b21dc927e5d46acb5473e1b72f313340d914d7f41311c2b453` |
| `sql/sql_class.cc` | `8f4395ada7fd3f97614099310302e740364808c0979730a6ca38397373299149` |
| `sql/xa.cc` | `77d814f55b942217a01cbff20d7eea85f4f27f6b3e5d62c30fad7867281e0427` |

`mdl_context_backup.h`는 owner 의도를 교차 확인하는 데 읽었지만 신규 claim의 source ref는 실제 호출과 구현이 있는 `.cc`/call-site를 우선했다.
