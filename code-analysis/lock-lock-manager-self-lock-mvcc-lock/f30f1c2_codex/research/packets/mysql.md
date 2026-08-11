# MySQL comparator research packet

## Packet metadata

- role: `Role 3 — MySQL Comparator`
- topic: `CUBRID lock과 lock manager — self lock 및 MVCC lock의 필요성`
- frozen_scope: `/home/vimkim/gh/my-cubrid-docs/code-analysis/lock-lock-manager-self-lock-mvcc-lock/f30f1c2_codex/research/scope.md`
- frozen_scope_sha256: `711d1a0f5bfebdbe1b55b4299973efc353d90636e2f00fc807f51d031766a839`
- mysql_source_root: `/home/vimkim/gh/mysql/mysql-server`
- mysql_revision: `06a5c1c99c377fc41b2eba1ea244e8b220bdc3c8`
- mysql_worktree_state: `clean`
- evidence_cutoff: `2026-08-11T08:42:33Z`
- evidence_mode: `source-only`; 서버 실행 결과나 외부 문서는 근거로 쓰지 않았다.
- writable_output: 이 파일 하나뿐이다.
- central_behaviors:
  - `resource-mode-hierarchy`
  - `wait-deadlock-release`
  - `mvcc-lock-policy`
  - `mvccid-self-lock-rendezvous`
- claim_id_range: `MYSQL-C001..MYSQL-C033`

## 결론 먼저: 실제 소유자와 비교의 경계

MySQL에서 “lock manager”를 하나의 단일 계층으로 부르면 핵심 경계가 사라진다. 이 패킷에서 식별한 실제 소유자는 다음 둘이다.

1. **MySQL server SQL 계층의 Metadata Locking(MDL)** 은 스키마 객체의 정의·사용 관계를 보호한다. 일반 `SELECT`의 `MDL_SHARED_READ`, DML 및 `SELECT ... FOR UPDATE`의 `MDL_SHARED_WRITE`, DDL의 `MDL_EXCLUSIVE`가 대표적이다. 이 잠금의 요청·대기·해제는 `MDL_context`/`MDL_lock`이 소유한다.
2. **InnoDB** 는 테이블 intention lock과 인덱스 레코드/갭 데이터 잠금, MVCC read view, implicit record X lock, 트랜잭션 대기 그래프를 소유한다. SQL 행을 추상적으로 잠그는 것이 아니라 인덱스 레코드와 갭을 잠근다.

따라서 CUBRID class/object lock과 비교할 때 MDL과 InnoDB를 합쳐서 하나의 직접 대응물로 취급하면 안 된다. 특히 InnoDB의 `trx->lock.blocking_trx`는 “트랜잭션 ID라는 자원에 잡는 잠금”이 아니라 대기 간선 bookkeeping이다. InnoDB implicit X lock도 한 트랜잭션에 종속된 모든 레코드를 하나의 MVCCID 자원으로 모으는 self-lock이 아니라, **개별 인덱스 레코드의 행 버전에 기록된 transaction ID로 표현되는 논리적 X 소유권**이다.

직접 대응 분류는 다음과 같다.

| 비교 축 | MySQL의 가장 가까운 메커니즘 | 분류 | 핵심 주의점 |
|---|---|---|---|
| resource/mode/hierarchy | MDL + InnoDB table intention/record/gap locks | partial analogy | 소유 계층과 자원 단위가 갈라져 있다. |
| wait/deadlock/release | MDL wait graph와 InnoDB transaction wait graph | partial analogy | 두 계층을 가로지르는 cycle은 MDL comment가 timeout 해소 경로를 별도로 경고한다. |
| MVCC consistent read vs locking read/DML | `LOCK_NONE` read view vs IS/IX + S/X record locks | responsibility-level equivalent, implementation-level partial analogy | `LOCK_NONE`은 lock-sys에 저장되는 잠금 모드가 아니라 consistent-read 표시다. |
| CUBRID MVCCID self-lock | implicit record X → contention 시 explicit record X 변환 + transaction wait edge | direct equivalent 없음; partial analogy만 존재 | 자원은 transaction ID가 아니라 record/table이다. |

## 조사 파일과 고정 해시

아래 해시는 모두 `mysql_revision`의 작업 트리 파일을 직접 `sha256sum`한 값이다. 이후 claim의 `source_refs`는 이 표의 전체 해시를 반복하여 자체 완결적으로 기록한다.

| path | examined symbols / responsibility | sha256 |
|---|---|---|
| `sql/mdl.h` | `enum_mdl_type`, `enum_mdl_duration` | `c43186485e83c94018abc88b7490bff7281eaf0a94b5f523932fa6bdc7be43a2` |
| `sql/mdl.cc` | `MDL_lock::can_grant_lock`, `MDL_context::{acquire_lock,find_deadlock,release_lock,release_transactional_locks}` | `914aadcc4006be4d314db84063d8d458445bf005ae6e3e78982963b2f26ee4a3` |
| `sql/sql_base.cc` | `open_table_get_mdl_lock` | `2a108465126fceb8e0b996179a912e58a7cb5cd4630f8f7b46366e4816d26e1a` |
| `storage/innobase/include/lock0types.h` | `lock_mode` | `3281fccc3744859eef09eb26d57de386e7a8275c62c5ad5d74005431b5dd08c1` |
| `storage/innobase/include/lock0priv.h` | `lock_compatibility_matrix`, `lock_table_t`, `lock_rec_t`, `lock_t`, implicit-lock contract | `2c035baaf4a24ed0d3d2daa68cdcbf73a81b2c77d89965ecdf530c26b3326ea0` |
| `storage/innobase/include/lock0priv.ic` | `lock_mode_compatible`, `lock_mode_stronger_or_eq`, `lock_table_has`, `lock_clust_rec_some_has_impl` | `a6d743a280290a6b6a6bc7d122853e6a8cd9614e97577408375648ef47c12463` |
| `storage/innobase/include/lock0lock.h` | lock-system model and `LOCK_TABLE`/`LOCK_REC` flags | `47150953daad95254bb80a5e573336d2d8c7bf471fd5cb1eeb93b8723ad2c3bb` |
| `storage/innobase/lock/lock0lock.cc` | table/record acquire, wait edge, grant, dequeue, release, implicit-to-explicit conversion | `f980965075e998cb30a982223411f383c9052d092ad69ebfe5b5aeb5b3726550` |
| `storage/innobase/include/trx0trx.h` | `trx_lock_t`, `trx_t::lock` | `8b451929d5ecc4c7677e55055da3da84ae3e351f5a1da3df98f5e4c1653fc1d3` |
| `storage/innobase/lock/lock0wait.cc` | suspend, wake, timeout, graph snapshot, deadlock victim | `a5735209c324ebd3e2829bd4a1c9b421b5cb41db67aab1072bec9f3a070d6a14` |
| `storage/innobase/trx/trx0trx.cc` | `trx_release_impl_and_expl_locks`, `trx_commit_in_memory`, recovered lock resurrection, read-view assignment | `3128c6a43a6ed4e6465f4b28cc6eff5b3a6ad6e6d4a3e6f03b7788ece7d9cf65` |
| `storage/innobase/row/row0sel.cc` | `sel_set_rec_lock`, `row_search_mvcc` | `418edef00f0a8cba8875deac251f0581ceb98f16af99fac296eab2136b78aa1b` |
| `storage/innobase/handler/ha_innodb.cc` | `ha_innobase::external_lock`, timeout/deadlock-detect variables | `42e7ad557071037a82440c01e34740615663963711dd5691c9226d69a6ec4ea8` |
| `storage/innobase/include/read0types.h` | `ReadView::changes_visible` | `5e4eb1bfe122d01057007ace295adfa7364fa0c1ce1ab7fbafd72e2f4b93916a` |
| `storage/innobase/read/read0read.cc` | `ReadView::prepare` | `e6eb19c27aebf78275cf71af074b3641c9f5dc4a982c87e296a6ee1147f1d840` |
| `storage/innobase/row/row0upd.cc` | `row_upd_step` | `b17615a2fe9e27bfb13f61453a42323485b39bcd076dfe3cac9a51bad5bdda06` |
| `storage/innobase/btr/btr0cur.cc` | `btr_cur_upd_lock_and_undo`, update-in-place path | `107f89e02adef0e504c02298f9d4d7cdfc6f4306094fdc5725f1193624e8b2de` |
| `storage/innobase/row/row0ins.cc` | insert state machine, unique/FK checks | `4663213c4e443450323908184eae6477c63cf5e376cfa7385b3400fcc19c4f30` |
| `storage/innobase/row/row0mysql.cc` | lock-wait handling and insert retry | `08db672d4177b27b5f95a3a4507a0965fe0e3e5991d099a76afa4d37e9489100` |
| `storage/innobase/include/trx0sys.ic` | `trx_rw_is_active` | `5915fb1c33296f4e1401673f1e835490ac303c6a49a365cf4cc6b05f91d69645` |
| `storage/innobase/srv/srv0mon.cc` | lock monitoring counters | `5490df1065f3233683280fbdbef943f7998db7524da3954136be635b21c9fc0e` |
| `storage/innobase/handler/p_s.cc` | Performance Schema `data_locks` traversal | `958f029685f6e5b376f821379169bc1fa0641ee5bf49ec585dc9cdabbd347e08` |

## Claim candidates

공통 필드 규칙:

- 모든 claim의 `database`는 `mysql`, `revision`은 `06a5c1c99c377fc41b2eba1ea244e8b220bdc3c8`이다.
- 모든 `source_refs.evidence_state`는 `COMMIT`이다.
- source-only 역할이므로 모든 `runtime_run_ids`는 빈 배열이다.
- `report_locations`는 책 편집 단계에서 채울 수 있도록 anchor hint만 제안한다.

### resource-mode-hierarchy

#### MYSQL-C001

- id: `MYSQL-C001`
- database: `mysql`
- revision: `06a5c1c99c377fc41b2eba1ea244e8b220bdc3c8`
- claim_ko: MySQL server의 MDL과 InnoDB의 데이터 잠금은 서로 다른 소유자와 자료구조를 가진다. 테이블 open은 `MDL_context`로 metadata lock을 취하고, InnoDB handler/row 경로는 별도로 table/record lock을 취한다.
- kind: `source`
- confidence: `SOURCE-CONFIRMED`
- comparison: `partial analogy`; MDL을 CUBRID object/row lock의 직접 대응물로 부르면 안 된다.
- source_refs:
  - path: `sql/sql_base.cc`; symbol: `open_table_get_mdl_lock`; line_start: 2638; line_end: 2761; file_sha256: `2a108465126fceb8e0b996179a912e58a7cb5cd4630f8f7b46366e4816d26e1a`; evidence_state: `COMMIT`
  - path: `storage/innobase/handler/ha_innodb.cc`; symbol: `ha_innobase::external_lock`; line_start: 18948; line_end: 19135; file_sha256: `42e7ad557071037a82440c01e34740615663963711dd5691c9226d69a6ec4ea8`; evidence_state: `COMMIT`
- runtime_run_ids: []
- limitations_ko: SQL parser에서 모든 문장별 MDL 요청을 만드는 전 경로는 추적하지 않았다. 여기서는 open 시 MDL 획득과 InnoDB 진입 이후 데이터 잠금 정책의 분리를 증명한다.
- report_locations: [`mysql-comparison#MYSQL-C001`]

#### MYSQL-C002

- id: `MYSQL-C002`
- database: `mysql`
- revision: `06a5c1c99c377fc41b2eba1ea244e8b220bdc3c8`
- claim_ko: MDL은 일반 `SELECT`에 `MDL_SHARED_READ`, INSERT/UPDATE/DELETE 및 `SELECT ... FOR UPDATE`에 `MDL_SHARED_WRITE`, 강한 DDL에 `MDL_EXCLUSIVE`를 정의하며, transaction-duration MDL은 트랜잭션 종료 때 자동 해제된다.
- kind: `source`
- confidence: `SOURCE-CONFIRMED`
- comparison: `partial analogy`; 메타데이터/DDL 안정성 책임만 비교한다.
- source_refs:
  - path: `sql/mdl.h`; symbol: `enum_mdl_type`; line_start: 197; line_end: 330; file_sha256: `c43186485e83c94018abc88b7490bff7281eaf0a94b5f523932fa6bdc7be43a2`; evidence_state: `COMMIT`
  - path: `sql/mdl.h`; symbol: `enum_mdl_duration`; line_start: 332; line_end: 349; file_sha256: `c43186485e83c94018abc88b7490bff7281eaf0a94b5f523932fa6bdc7be43a2`; evidence_state: `COMMIT`
  - path: `sql/mdl.cc`; symbol: `MDL_context::release_transactional_locks`; line_start: 4513; line_end: 4517; file_sha256: `914aadcc4006be4d314db84063d8d458445bf005ae6e3e78982963b2f26ee4a3`; evidence_state: `COMMIT`
- runtime_run_ids: []
- limitations_ko: statement-to-request construction의 모든 예외를 열거한 주장이 아니라 enum의 명시적 의도와 transactional release에 한정한다.
- report_locations: [`mysql-comparison#MYSQL-C002`]

#### MYSQL-C003

- id: `MYSQL-C003`
- database: `mysql`
- revision: `06a5c1c99c377fc41b2eba1ea244e8b220bdc3c8`
- claim_ko: InnoDB 기본 모드는 IS, IX, S, X, AUTO_INC이고, 호환성 표에서 IS는 X와 충돌하며 IX는 S/X와 충돌하고 S는 IX/X와 충돌하며 X는 다른 네 모드 모두와 충돌한다. 레코드 잠금은 S/X만 쓰고, 일반 테이블 잠금은 주로 IS/IX를 쓴다.
- kind: `source`
- confidence: `SOURCE-CONFIRMED`
- comparison: `partial analogy`; 모드 이름 일부가 같더라도 전체 compatibility lattice가 동일하다는 뜻은 아니다.
- source_refs:
  - path: `storage/innobase/include/lock0types.h`; symbol: `lock_mode`; line_start: 53; line_end: 64; file_sha256: `3281fccc3744859eef09eb26d57de386e7a8275c62c5ad5d74005431b5dd08c1`; evidence_state: `COMMIT`
  - path: `storage/innobase/include/lock0priv.h`; symbol: `lock_compatibility_matrix`; line_start: 578; line_end: 616; file_sha256: `2c035baaf4a24ed0d3d2daa68cdcbf73a81b2c77d89965ecdf530c26b3326ea0`; evidence_state: `COMMIT`
- runtime_run_ids: []
- limitations_ko: AUTO_INC와 predicate lock의 상세 의미는 범위 밖이다.
- report_locations: [`mysql-comparison#MYSQL-C003`]

#### MYSQL-C004

- id: `MYSQL-C004`
- database: `mysql`
- revision: `06a5c1c99c377fc41b2eba1ea244e8b220bdc3c8`
- claim_ko: InnoDB lock request의 개념적 튜플은 transaction/resource/mode/state이고, 고정 revision의 lock-system 공개 타입에서 실제 잠금 자원 종류는 `LOCK_TABLE`과 `LOCK_REC` 두 가지다. `LOCK_WAIT`, GAP, REC_NOT_GAP, INSERT_INTENTION 등은 record/type 상태 flag다.
- kind: `source`
- confidence: `SOURCE-CONFIRMED`
- comparison: `partial analogy`; 이후 MVCCID 자원 부재를 판단하는 양의 토대다.
- source_refs:
  - path: `storage/innobase/include/lock0lock.h`; symbol: `PAGE_INNODB_LOCK_SYS`; line_start: 57; line_end: 118; file_sha256: `47150953daad95254bb80a5e573336d2d8c7bf471fd5cb1eeb93b8723ad2c3bb`; evidence_state: `COMMIT`
  - path: `storage/innobase/include/lock0lock.h`; symbol: `LOCK_TABLE`; line_start: 959; line_end: 1007; file_sha256: `47150953daad95254bb80a5e573336d2d8c7bf471fd5cb1eeb93b8723ad2c3bb`; evidence_state: `COMMIT`
- runtime_run_ids: []
- limitations_ko: predicate lock은 record type의 flag로 존재하지만 공간 인덱스 세부는 조사하지 않았다.
- report_locations: [`mysql-comparison#MYSQL-C004`]

#### MYSQL-C005

- id: `MYSQL-C005`
- database: `mysql`
- revision: `06a5c1c99c377fc41b2eba1ea244e8b220bdc3c8`
- claim_ko: InnoDB table lock resource는 `dict_table_t *`로, record lock resource는 page identifier와 heap-number bitmap으로 식별된다. `lock_t`는 소유 `trx_t *`와 transaction lock list 연결을 보존한다.
- kind: `source`
- confidence: `SOURCE-CONFIRMED`
- comparison: `partial analogy`; SQL row가 아니라 index record/page+heap identity라는 차이가 중요하다.
- source_refs:
  - path: `storage/innobase/include/lock0priv.h`; symbol: `lock_table_t`; line_start: 53; line_end: 81; file_sha256: `2c035baaf4a24ed0d3d2daa68cdcbf73a81b2c77d89965ecdf530c26b3326ea0`; evidence_state: `COMMIT`
  - path: `storage/innobase/include/lock0priv.h`; symbol: `lock_rec_t`; line_start: 83; line_end: 91; file_sha256: `2c035baaf4a24ed0d3d2daa68cdcbf73a81b2c77d89965ecdf530c26b3326ea0`; evidence_state: `COMMIT`
  - path: `storage/innobase/include/lock0priv.h`; symbol: `lock_t`; line_start: 136; line_end: 171; file_sha256: `2c035baaf4a24ed0d3d2daa68cdcbf73a81b2c77d89965ecdf530c26b3326ea0`; evidence_state: `COMMIT`
- runtime_run_ids: []
- limitations_ko: record bitmap의 압축·재배치 구현은 비교 범위 밖이다.
- report_locations: [`mysql-comparison#MYSQL-C005`]

#### MYSQL-C006

- id: `MYSQL-C006`
- database: `mysql`
- revision: `06a5c1c99c377fc41b2eba1ea244e8b220bdc3c8`
- claim_ko: InnoDB record S lock을 요청하는 트랜잭션은 해당 테이블 IS 이상의 lock을, record X lock을 요청하는 트랜잭션은 IX 이상의 lock을 가져야 한다. locking read는 S일 때 IS, X일 때 IX를 먼저 요청한다.
- kind: `source`
- confidence: `SOURCE-CONFIRMED`
- comparison: `partial analogy`; 다중 granularity 의도 표현의 가장 가까운 대응이다.
- source_refs:
  - path: `storage/innobase/lock/lock0lock.cc`; symbol: `lock_rec_lock`; line_start: 1849; line_end: 1878; file_sha256: `f980965075e998cb30a982223411f383c9052d092ad69ebfe5b5aeb5b3726550`; evidence_state: `COMMIT`
  - path: `storage/innobase/row/row0sel.cc`; symbol: `row_search_mvcc`; line_start: 4437; line_end: 4860; file_sha256: `418edef00f0a8cba8875deac251f0581ceb98f16af99fac296eab2136b78aa1b`; evidence_state: `COMMIT`
- runtime_run_ids: []
- limitations_ko: 내부 assertion/precondition과 정상 SQL 경로를 대상으로 한다.
- report_locations: [`mysql-comparison#MYSQL-C006`]

#### MYSQL-C007

- id: `MYSQL-C007`
- database: `mysql`
- revision: `06a5c1c99c377fc41b2eba1ea244e8b220bdc3c8`
- claim_ko: `lock_table`은 잠금이 불필요한 경우를 건너뛰고, 자신이 가진 동일/강한 table lock이면 즉시 성공하며, 호환 가능한 경우 granted lock을 만들고 충돌 시 waiting lock을 enqueue한다.
- kind: `source`
- confidence: `SOURCE-CONFIRMED`
- comparison: `partial analogy`; table resource의 acquire fast/slow path 비교에 사용한다.
- source_refs:
  - path: `storage/innobase/include/lock0priv.ic`; symbol: `lock_table_has`; line_start: 152; line_end: 178; file_sha256: `a6d743a280290a6b6a6bc7d122853e6a8cd9614e97577408375648ef47c12463`; evidence_state: `COMMIT`
  - path: `storage/innobase/lock/lock0lock.cc`; symbol: `lock_table_create`; line_start: 3231; line_end: 3291; file_sha256: `f980965075e998cb30a982223411f383c9052d092ad69ebfe5b5aeb5b3726550`; evidence_state: `COMMIT`
  - path: `storage/innobase/lock/lock0lock.cc`; symbol: `lock_table`; line_start: 3516; line_end: 3608; file_sha256: `f980965075e998cb30a982223411f383c9052d092ad69ebfe5b5aeb5b3726550`; evidence_state: `COMMIT`
- runtime_run_ids: []
- limitations_ko: AUTOINC와 temporary table 예외는 결론에서 일반화하지 않았다.
- report_locations: [`mysql-comparison#MYSQL-C007`]

#### MYSQL-C008

- id: `MYSQL-C008`
- database: `mysql`
- revision: `06a5c1c99c377fc41b2eba1ea244e8b220bdc3c8`
- claim_ko: record acquire는 fast path와 slow path로 나뉘며, `impl=true`인 변경 경로에서는 충돌이 없으면 별도 explicit `lock_t`를 만들지 않을 수 있다. GAP/REC_NOT_GAP/INSERT_INTENTION flag가 레코드 범위를 세분한다.
- kind: `source`
- confidence: `SOURCE-CONFIRMED`
- comparison: `partial analogy`; InnoDB의 잠금 객체 절약과 next-key/gap 의미를 분리해 읽어야 한다.
- source_refs:
  - path: `storage/innobase/lock/lock0lock.cc`; symbol: `lock_rec_lock_fast`; line_start: 1594; line_end: 1678; file_sha256: `f980965075e998cb30a982223411f383c9052d092ad69ebfe5b5aeb5b3726550`; evidence_state: `COMMIT`
  - path: `storage/innobase/lock/lock0lock.cc`; symbol: `lock_rec_lock_slow`; line_start: 1717; line_end: 1828; file_sha256: `f980965075e998cb30a982223411f383c9052d092ad69ebfe5b5aeb5b3726550`; evidence_state: `COMMIT`
  - path: `storage/innobase/lock/lock0lock.cc`; symbol: `lock_rec_lock`; line_start: 1849; line_end: 1878; file_sha256: `f980965075e998cb30a982223411f383c9052d092ad69ebfe5b5aeb5b3726550`; evidence_state: `COMMIT`
  - path: `storage/innobase/include/lock0lock.h`; symbol: `LOCK_GAP`; line_start: 976; line_end: 1007; file_sha256: `47150953daad95254bb80a5e573336d2d8c7bf471fd5cb1eeb93b8723ad2c3bb`; evidence_state: `COMMIT`
- runtime_run_ids: []
- limitations_ko: 모든 isolation level별 gap-lock 예외는 의도적으로 제외했다.
- report_locations: [`mysql-comparison#MYSQL-C008`]

#### MYSQL-C009

- id: `MYSQL-C009`
- database: `mysql`
- revision: `06a5c1c99c377fc41b2eba1ea244e8b220bdc3c8`
- claim_ko: 이미 가진 동일하거나 더 강한 table lock은 새 요청을 만족시키지만, 약한 own lock에서 강한 모드를 요청할 때 일반 경로는 기존 객체를 제자리에서 바꾸는 대신 own lock을 conflict 검사에서 제외하고 별도 request를 만든다.
- kind: `inference`
- confidence: `INFERRED`
- comparison: `partial analogy`; “conversion”이라는 이름의 단일 공통 연산이 있다는 주장으로 확대하면 안 된다.
- source_refs:
  - path: `storage/innobase/include/lock0priv.ic`; symbol: `lock_mode_stronger_or_eq`; line_start: 101; line_end: 178; file_sha256: `a6d743a280290a6b6a6bc7d122853e6a8cd9614e97577408375648ef47c12463`; evidence_state: `COMMIT`
  - path: `storage/innobase/lock/lock0lock.cc`; symbol: `lock_table`; line_start: 3516; line_end: 3608; file_sha256: `f980965075e998cb30a982223411f383c9052d092ad69ebfe5b5aeb5b3726550`; evidence_state: `COMMIT`
- premises_ko: `lock_table_has`는 own equal/stronger lock만 성공으로 반환하고, `lock_table_other_has_incompatible`는 own lock을 제외하며, 이후 `lock_table_create`가 새 request를 만든다.
- falsifier_ko: 이 일반 acquire 경로에서 약한 own lock 객체의 `type_mode`를 강한 모드로 제자리 변경하는 reachable branch가 확인되면 이 추론은 폐기한다.
- runtime_run_ids: []
- limitations_ko: 위 결론은 이 일반 table-lock acquire 경로의 자료구조 동작을 종합한 추론이다. 특수 lock 종류의 별도 최적화까지 부정하지 않는다.
- report_locations: [`mysql-comparison#MYSQL-C009`]

#### MYSQL-C010

- id: `MYSQL-C010`
- database: `mysql`
- revision: `06a5c1c99c377fc41b2eba1ea244e8b220bdc3c8`
- claim_ko: 조사 범위의 InnoDB table/record lock 구현에는 record-lock 개수 임계값에 따른 table lock escalation 경로가 확인되지 않았다. 많은 잠금과 buffer 압력 상황은 escalation 대신 `DB_LOCK_TABLE_FULL` 오류 경로를 가진다.
- kind: `source`
- confidence: `SOURCE-CONFIRMED`
- comparison: `no equivalent found` for count-based escalation.
- source_refs:
  - path: `storage/innobase/row/row0sel.cc`; symbol: `sel_set_rec_lock`; line_start: 1144; line_end: 1185; file_sha256: `418edef00f0a8cba8875deac251f0581ceb98f16af99fac296eab2136b78aa1b`; evidence_state: `COMMIT`
  - path: `storage/innobase/include/trx0trx.h`; symbol: `n_rec_locks`; line_start: 521; line_end: 544; file_sha256: `8b451929d5ecc4c7677e55055da3da84ae3e351f5a1da3df98f5e4c1653fc1d3`; evidence_state: `COMMIT`
- search_coverage: `rg -n -i "lock escalation|lock_escalat|escalat(e|ion|ing).*lock|lock.*escalat(e|ion|ing)" storage/innobase/lock storage/innobase/row storage/innobase/trx storage/innobase/include sql include` → `0 matches` at pinned revision.
- runtime_run_ids: []
- limitations_ko: “MySQL 어디에도 영원히 escalation이 없다”가 아니라 고정 revision의 조사 디렉터리와 잠금 인터페이스에 대한 강한 음성 검색 결과다.
- report_locations: [`mysql-comparison#MYSQL-C010`]

### wait-deadlock-release

#### MYSQL-C011

- id: `MYSQL-C011`
- database: `mysql`
- revision: `06a5c1c99c377fc41b2eba1ea244e8b220bdc3c8`
- claim_ko: InnoDB의 대기 상태는 waiting `lock_t`, `trx_lock_t::wait_lock`, `blocking_trx`로 연결된다. lock wait request가 만들어질 때 blocker edge를 설정하고 트랜잭션 queue state를 WAIT로 바꾼다.
- kind: `source`
- confidence: `SOURCE-CONFIRMED`
- comparison: `partial analogy`; `blocking_trx`는 자원이 아니라 wait-for edge다.
- source_refs:
  - path: `storage/innobase/include/trx0trx.h`; symbol: `trx_lock_t`; line_start: 396; line_end: 455; file_sha256: `8b451929d5ecc4c7677e55055da3da84ae3e351f5a1da3df98f5e4c1653fc1d3`; evidence_state: `COMMIT`
  - path: `storage/innobase/lock/lock0lock.cc`; symbol: `lock_create_wait_for_edge`; line_start: 1387; line_end: 1408; file_sha256: `f980965075e998cb30a982223411f383c9052d092ad69ebfe5b5aeb5b3726550`; evidence_state: `COMMIT`
  - path: `storage/innobase/lock/lock0lock.cc`; symbol: `RecLock::set_wait_state`; line_start: 1413; line_end: 1428; file_sha256: `f980965075e998cb30a982223411f383c9052d092ad69ebfe5b5aeb5b3726550`; evidence_state: `COMMIT`
  - path: `storage/innobase/lock/lock0lock.cc`; symbol: `RecLock::add_to_waitq`; line_start: 1430; line_end: 1462; file_sha256: `f980965075e998cb30a982223411f383c9052d092ad69ebfe5b5aeb5b3726550`; evidence_state: `COMMIT`
- runtime_run_ids: []
- limitations_ko: MDL 대기 티켓은 별도 계층이며 이 claim에 합치지 않았다.
- report_locations: [`mysql-comparison#MYSQL-C011`]

#### MYSQL-C012

- id: `MYSQL-C012`
- database: `mysql`
- revision: `06a5c1c99c377fc41b2eba1ea244e8b220bdc3c8`
- claim_ko: InnoDB lock wait suspend는 timeout을 정하고 wait slot을 예약한 뒤, 필요한 경우 dictionary-operation latch와 InnoDB concurrency slot을 놓고 OS event를 기다리며, 깨어난 뒤 재진입과 오류 판정을 수행한다.
- kind: `source`
- confidence: `SOURCE-CONFIRMED`
- comparison: `partial analogy`; block 전 보유 자원 정리라는 안전 책임을 비교할 수 있다.
- source_refs:
  - path: `storage/innobase/lock/lock0wait.cc`; symbol: `lock_wait_suspend_thread`; line_start: 206; line_end: 355; file_sha256: `a5735209c324ebd3e2829bd4a1c9b421b5cb41db67aab1072bec9f3a070d6a14`; evidence_state: `COMMIT`
- runtime_run_ids: []
- limitations_ko: OS event 구현과 스케줄러 세부는 추적하지 않았다.
- report_locations: [`mysql-comparison#MYSQL-C012`]

#### MYSQL-C013

- id: `MYSQL-C013`
- database: `mysql`
- revision: `06a5c1c99c377fc41b2eba1ea244e8b220bdc3c8`
- claim_ko: blocker 해제 시 InnoDB는 대기 lock을 grant하거나 blocker edge를 갱신하고, wake 경로는 `blocking_trx`와 wait 상태/pointer를 정리한 뒤 event를 signal한다. 깨어난 DML은 상위 row state machine에서 해당 작업·제약 검사를 다시 수행한다.
- kind: `source`
- confidence: `SOURCE-CONFIRMED`
- comparison: `partial analogy`; wake 자체가 조건 성립을 최종 보증하는 것이 아니므로 retry/recheck가 필수다.
- source_refs:
  - path: `storage/innobase/lock/lock0lock.cc`; symbol: `lock_grant`; line_start: 1910; line_end: 1942; file_sha256: `f980965075e998cb30a982223411f383c9052d092ad69ebfe5b5aeb5b3726550`; evidence_state: `COMMIT`
  - path: `storage/innobase/lock/lock0lock.cc`; symbol: `lock_grant_or_update_wait_for_edge`; line_start: 2222; line_end: 2247; file_sha256: `f980965075e998cb30a982223411f383c9052d092ad69ebfe5b5aeb5b3726550`; evidence_state: `COMMIT`
  - path: `storage/innobase/lock/lock0wait.cc`; symbol: `lock_wait_release_thread_if_suspended`; line_start: 357; line_end: 464; file_sha256: `a5735209c324ebd3e2829bd4a1c9b421b5cb41db67aab1072bec9f3a070d6a14`; evidence_state: `COMMIT`
  - path: `storage/innobase/row/row0mysql.cc`; symbol: `row_insert_for_mysql_using_ins_graph`; line_start: 1498; line_end: 1600; file_sha256: `08db672d4177b27b5f95a3a4507a0965fe0e3e5991d099a76afa4d37e9489100`; evidence_state: `COMMIT`
- runtime_run_ids: []
- limitations_ko: retry는 insert graph 경로를 직접 증명했으며 모든 DML state machine이 동일한 label을 쓰는 것은 아니다.
- report_locations: [`mysql-comparison#MYSQL-C013`]

#### MYSQL-C014

- id: `MYSQL-C014`
- database: `mysql`
- revision: `06a5c1c99c377fc41b2eba1ea244e8b220bdc3c8`
- claim_ko: InnoDB lock wait timeout/interrupt thread는 대기 시간을 검사해 waiting lock을 취소하고 transaction error state를 설정한다. timeout 값은 session 변수로 노출된다.
- kind: `source`
- confidence: `SOURCE-CONFIRMED`
- comparison: `partial analogy`.
- source_refs:
  - path: `storage/innobase/lock/lock0wait.cc`; symbol: `lock_wait_check_and_cancel`; line_start: 465; line_end: 558; file_sha256: `a5735209c324ebd3e2829bd4a1c9b421b5cb41db67aab1072bec9f3a070d6a14`; evidence_state: `COMMIT`
  - path: `storage/innobase/handler/ha_innodb.cc`; symbol: `lock_wait_timeout`; line_start: 1117; line_end: 1121; file_sha256: `42e7ad557071037a82440c01e34740615663963711dd5691c9226d69a6ec4ea8`; evidence_state: `COMMIT`
- runtime_run_ids: []
- limitations_ko: SQL-visible 오류 메시지와 statement/transaction rollback 정책은 범위 밖이다.
- report_locations: [`mysql-comparison#MYSQL-C014`]

#### MYSQL-C015

- id: `MYSQL-C015`
- database: `mysql`
- revision: `06a5c1c99c377fc41b2eba1ea244e8b220bdc3c8`
- claim_ko: InnoDB는 대기 중 트랜잭션을 node로, 각 `blocking_trx`를 outgoing edge로 snapshot하여 cycle을 찾고 victim을 취소한다. deadlock detection은 설정으로 활성화/비활성화할 수 있다.
- kind: `source`
- confidence: `SOURCE-CONFIRMED`
- comparison: `partial analogy`; graph construction과 victim policy 세부는 CUBRID와 동일하다고 가정하지 않는다.
- source_refs:
  - path: `storage/innobase/lock/lock0wait.cc`; symbol: `lock_wait_snapshot_waiting_threads`; line_start: 564; line_end: 690; file_sha256: `a5735209c324ebd3e2829bd4a1c9b421b5cb41db67aab1072bec9f3a070d6a14`; evidence_state: `COMMIT`
  - path: `storage/innobase/lock/lock0wait.cc`; symbol: `lock_wait_find_and_handle_deadlocks`; line_start: 1267; line_end: 1318; file_sha256: `a5735209c324ebd3e2829bd4a1c9b421b5cb41db67aab1072bec9f3a070d6a14`; evidence_state: `COMMIT`
  - path: `storage/innobase/lock/lock0wait.cc`; symbol: `lock_wait_update_schedule_and_check_for_deadlocks`; line_start: 1377; line_end: 1460; file_sha256: `a5735209c324ebd3e2829bd4a1c9b421b5cb41db67aab1072bec9f3a070d6a14`; evidence_state: `COMMIT`
  - path: `storage/innobase/handler/ha_innodb.cc`; symbol: `innobase_deadlock_detect`; line_start: 22701; line_end: 22706; file_sha256: `42e7ad557071037a82440c01e34740615663963711dd5691c9226d69a6ec4ea8`; evidence_state: `COMMIT`
- runtime_run_ids: []
- limitations_ko: victim cost 계산의 세부 비교는 수행하지 않았다.
- report_locations: [`mysql-comparison#MYSQL-C015`]

#### MYSQL-C016

- id: `MYSQL-C016`
- database: `mysql`
- revision: `06a5c1c99c377fc41b2eba1ea244e8b220bdc3c8`
- claim_ko: timeout이나 interrupt로 waiting request를 취소하는 경로와, waiting record lock을 dequeue/discard한 뒤 뒤쪽 waiter를 grant 또는 edge-update하는 경로가 명시적으로 존재한다.
- kind: `source`
- confidence: `SOURCE-CONFIRMED`
- comparison: `partial analogy`.
- source_refs:
  - path: `storage/innobase/lock/lock0wait.cc`; symbol: `lock_wait_check_and_cancel`; line_start: 465; line_end: 558; file_sha256: `a5735209c324ebd3e2829bd4a1c9b421b5cb41db67aab1072bec9f3a070d6a14`; evidence_state: `COMMIT`
  - path: `storage/innobase/lock/lock0lock.cc`; symbol: `lock_rec_dequeue_from_page`; line_start: 2288; line_end: 2323; file_sha256: `f980965075e998cb30a982223411f383c9052d092ad69ebfe5b5aeb5b3726550`; evidence_state: `COMMIT`
  - path: `storage/innobase/lock/lock0lock.cc`; symbol: `lock_cancel_waiting_and_release`; line_start: 5727; line_end: 5740; file_sha256: `f980965075e998cb30a982223411f383c9052d092ad69ebfe5b5aeb5b3726550`; evidence_state: `COMMIT`
- runtime_run_ids: []
- limitations_ko: table-lock dequeue는 별도 구현이며 동일 함수 하나로 통합되어 있지 않다.
- report_locations: [`mysql-comparison#MYSQL-C016`]

#### MYSQL-C017

- id: `MYSQL-C017`
- database: `mysql`
- revision: `06a5c1c99c377fc41b2eba1ea244e8b220bdc3c8`
- claim_ko: InnoDB commit은 트랜잭션을 `TRX_STATE_COMMITTED_IN_MEMORY`로 게시하고 active RW set에서 제거한 뒤 `lock_trx_release_locks`로 모든 explicit lock을 풀고 lock heap을 비운다. source comment는 이 게시 시점을 implicit lock이 해제된 시점으로 정의한다.
- kind: `source`
- confidence: `SOURCE-CONFIRMED`
- comparison: `partial analogy`; visibility/ownership publication과 waiter wake의 순서가 핵심이다.
- source_refs:
  - path: `storage/innobase/trx/trx0trx.cc`; symbol: `trx_release_impl_and_expl_locks`; line_start: 1874; line_end: 1983; file_sha256: `3128c6a43a6ed4e6465f4b28cc6eff5b3a6ad6e6d4a3e6f03b7788ece7d9cf65`; evidence_state: `COMMIT`
  - path: `storage/innobase/trx/trx0trx.cc`; symbol: `trx_commit_in_memory`; line_start: 1985; line_end: 2042; file_sha256: `3128c6a43a6ed4e6465f4b28cc6eff5b3a6ad6e6d4a3e6f03b7788ece7d9cf65`; evidence_state: `COMMIT`
  - path: `storage/innobase/lock/lock0lock.cc`; symbol: `lock_trx_release_locks`; line_start: 5800; line_end: 5850; file_sha256: `f980965075e998cb30a982223411f383c9052d092ad69ebfe5b5aeb5b3726550`; evidence_state: `COMMIT`
- runtime_run_ids: []
- limitations_ko: WAL flush/durability 순서는 이 lock 전용 claim에 포함하지 않았다.
- report_locations: [`mysql-comparison#MYSQL-C017`]

#### MYSQL-C018

- id: `MYSQL-C018`
- database: `mysql`
- revision: `06a5c1c99c377fc41b2eba1ea244e8b220bdc3c8`
- claim_ko: lock system은 startup에 메모리 구조로 새로 만들어지고, recovered transaction의 undo에서 얻은 table IDs를 순회하여 IX table lock을 `lock_table_ix_resurrect`로 재구성한다. 이 근거는 일반 wait queue의 disk persistence가 아니라 제한된 lock resurrection 경로를 보여 준다.
- kind: `source`
- confidence: `SOURCE-CONFIRMED`
- comparison: `partial analogy`; crash recovery 시 잠금 복원의 경계를 비교할 때만 사용한다.
- source_refs:
  - path: `storage/innobase/lock/lock0lock.cc`; symbol: `lock_sys_create`; line_start: 289; line_end: 316; file_sha256: `f980965075e998cb30a982223411f383c9052d092ad69ebfe5b5aeb5b3726550`; evidence_state: `COMMIT`
  - path: `storage/innobase/trx/trx0trx.cc`; symbol: `trx_resurrect_locks`; line_start: 820; line_end: 872; file_sha256: `3128c6a43a6ed4e6465f4b28cc6eff5b3a6ad6e6d4a3e6f03b7788ece7d9cf65`; evidence_state: `COMMIT`
  - path: `storage/innobase/lock/lock0lock.cc`; symbol: `lock_table_ix_resurrect`; line_start: 3611; line_end: 3629; file_sha256: `f980965075e998cb30a982223411f383c9052d092ad69ebfe5b5aeb5b3726550`; evidence_state: `COMMIT`
- runtime_run_ids: []
- limitations_ko: 모든 crash 상태의 complete recovery semantics나 explicit record wait queue 비지속성을 전 파일에서 형식적으로 증명한 것은 아니다.
- report_locations: [`mysql-comparison#MYSQL-C018`]

#### MYSQL-C019

- id: `MYSQL-C019`
- database: `mysql`
- revision: `06a5c1c99c377fc41b2eba1ea244e8b220bdc3c8`
- claim_ko: InnoDB는 lock wait timeout과 deadlock detection 설정을 제공하고, deadlock·timeout·waiting·record/table lock wait/create/remove 카운터 및 Performance Schema의 table/record `data_locks` 순회를 제공한다.
- kind: `source`
- confidence: `SOURCE-CONFIRMED`
- comparison: `partial analogy`; 설정·관찰성 축의 대응이다.
- source_refs:
  - path: `storage/innobase/handler/ha_innodb.cc`; symbol: `lock_wait_timeout`; line_start: 1117; line_end: 1121; file_sha256: `42e7ad557071037a82440c01e34740615663963711dd5691c9226d69a6ec4ea8`; evidence_state: `COMMIT`
  - path: `storage/innobase/handler/ha_innodb.cc`; symbol: `innobase_deadlock_detect`; line_start: 22701; line_end: 22706; file_sha256: `42e7ad557071037a82440c01e34740615663963711dd5691c9226d69a6ec4ea8`; evidence_state: `COMMIT`
  - path: `storage/innobase/srv/srv0mon.cc`; symbol: `MONITOR_DEADLOCK`; line_start: 125; line_end: 184; file_sha256: `5490df1065f3233683280fbdbef943f7998db7524da3954136be635b21c9fc0e`; evidence_state: `COMMIT`
  - path: `storage/innobase/handler/p_s.cc`; symbol: `Innodb_data_lock_iterator`; line_start: 43; line_end: 132; file_sha256: `958f029685f6e5b376f821379169bc1fa0641ee5bf49ec585dc9cdabbd347e08`; evidence_state: `COMMIT`
- runtime_run_ids: []
- limitations_ko: Performance Schema schema/SQL 출력 형식은 runtime으로 확인하지 않았다.
- report_locations: [`mysql-comparison#MYSQL-C019`]

### mvcc-lock-policy

#### MYSQL-C020

- id: `MYSQL-C020`
- database: `mysql`
- revision: `06a5c1c99c377fc41b2eba1ea244e8b220bdc3c8`
- claim_ko: server-to-InnoDB read policy에서 일반 SELECT는 보통 `LOCK_NONE` consistent read, `FOR SHARE`는 S, `FOR UPDATE`는 X이며, SERIALIZABLE의 일반 SELECT는 autocommit read-only 예외를 빼면 S locking read가 된다.
- kind: `source`
- confidence: `SOURCE-CONFIRMED`
- comparison: `responsibility-level equivalent`, `implementation-level partial analogy`.
- source_refs:
  - path: `storage/innobase/handler/ha_innodb.cc`; symbol: `ha_innobase::external_lock`; line_start: 18948; line_end: 19135; file_sha256: `42e7ad557071037a82440c01e34740615663963711dd5691c9226d69a6ec4ea8`; evidence_state: `COMMIT`
  - path: `storage/innobase/handler/ha_innodb.cc`; symbol: `ha_innobase::start_stmt`; line_start: 18804; line_end: 18895; file_sha256: `42e7ad557071037a82440c01e34740615663963711dd5691c9226d69a6ec4ea8`; evidence_state: `COMMIT`
- runtime_run_ids: []
- limitations_ko: `LOCK_NONE`은 lock-sys에 요청되는 잠금이 아니라 row prebuilt의 consistent-read 표시다.
- report_locations: [`mysql-comparison#MYSQL-C020`]

#### MYSQL-C021

- id: `MYSQL-C021`
- database: `mysql`
- revision: `06a5c1c99c377fc41b2eba1ea244e8b220bdc3c8`
- claim_ko: `LOCK_NONE` read는 read view를 할당하고, 현재 버전이 view에 보이지 않으면 previous version을 구성한다. `ReadView::prepare`는 active read-write transaction IDs를 snapshot하고 `changes_visible`이 transaction ID 가시성을 판정한다.
- kind: `source`
- confidence: `SOURCE-CONFIRMED`
- comparison: `responsibility-level equivalent`; 읽기 일관성을 record S lock 없이 달성하는 축이다.
- source_refs:
  - path: `storage/innobase/row/row0sel.cc`; symbol: `row_search_mvcc`; line_start: 4437; line_end: 4860; file_sha256: `418edef00f0a8cba8875deac251f0581ceb98f16af99fac296eab2136b78aa1b`; evidence_state: `COMMIT`
  - path: `storage/innobase/row/row0sel.cc`; symbol: `row_search_mvcc`; line_start: 4437; line_end: 5395; file_sha256: `418edef00f0a8cba8875deac251f0581ceb98f16af99fac296eab2136b78aa1b`; evidence_state: `COMMIT`
  - path: `storage/innobase/trx/trx0trx.cc`; symbol: `trx_assign_read_view`; line_start: 2350; line_end: 2366; file_sha256: `3128c6a43a6ed4e6465f4b28cc6eff5b3a6ad6e6d4a3e6f03b7788ece7d9cf65`; evidence_state: `COMMIT`
  - path: `storage/innobase/read/read0read.cc`; symbol: `ReadView::prepare`; line_start: 441; line_end: 464; file_sha256: `e6eb19c27aebf78275cf71af074b3641c9f5dc4a982c87e296a6ee1147f1d840`; evidence_state: `COMMIT`
  - path: `storage/innobase/include/read0types.h`; symbol: `changes_visible`; line_start: 156; line_end: 175; file_sha256: `5e4eb1bfe122d01057007ace295adfa7364fa0c1ce1ab7fbafd72e2f4b93916a`; evidence_state: `COMMIT`
- runtime_run_ids: []
- limitations_ko: purge/history traversal 전체는 추적하지 않았다.
- report_locations: [`mysql-comparison#MYSQL-C021`]

#### MYSQL-C022

- id: `MYSQL-C022`
- database: `mysql`
- revision: `06a5c1c99c377fc41b2eba1ea244e8b220bdc3c8`
- claim_ko: locking read는 S라면 table IS, X라면 table IX를 잡고, scan 중 isolation/scan 조건에 따라 gap/record 범위를 정해 `sel_set_rec_lock`으로 S/X record lock을 요청한다.
- kind: `source`
- confidence: `SOURCE-CONFIRMED`
- comparison: `partial analogy`; next-key/gap semantics 때문에 단순 row lock과 동일시할 수 없다.
- source_refs:
  - path: `storage/innobase/row/row0sel.cc`; symbol: `row_search_mvcc`; line_start: 4437; line_end: 4860; file_sha256: `418edef00f0a8cba8875deac251f0581ceb98f16af99fac296eab2136b78aa1b`; evidence_state: `COMMIT`
  - path: `storage/innobase/row/row0sel.cc`; symbol: `row_search_mvcc`; line_start: 4437; line_end: 5323; file_sha256: `418edef00f0a8cba8875deac251f0581ceb98f16af99fac296eab2136b78aa1b`; evidence_state: `COMMIT`
  - path: `storage/innobase/row/row0sel.cc`; symbol: `sel_set_rec_lock`; line_start: 1144; line_end: 1185; file_sha256: `418edef00f0a8cba8875deac251f0581ceb98f16af99fac296eab2136b78aa1b`; evidence_state: `COMMIT`
- runtime_run_ids: []
- limitations_ko: 모든 isolation/unique search optimization 조합은 열거하지 않았다.
- report_locations: [`mysql-comparison#MYSQL-C022`]

#### MYSQL-C023

- id: `MYSQL-C023`
- database: `mysql`
- revision: `06a5c1c99c377fc41b2eba1ea244e8b220bdc3c8`
- claim_ko: UPDATE row state machine은 먼저 table IX를 확보하고, 실제 clustered/secondary record 변경 직전에 X record modify lock을 확인·획득한 뒤 undo/write를 수행한다. 동일 레코드 writer 간 직렬화는 이 record X 경로가 담당한다.
- kind: `source`
- confidence: `SOURCE-CONFIRMED`
- comparison: `partial analogy`; physical resource는 index record다.
- source_refs:
  - path: `storage/innobase/row/row0upd.cc`; symbol: `row_upd_step`; line_start: 3242; line_end: 3317; file_sha256: `b17615a2fe9e27bfb13f61453a42323485b39bcd076dfe3cac9a51bad5bdda06`; evidence_state: `COMMIT`
  - path: `storage/innobase/btr/btr0cur.cc`; symbol: `btr_cur_upd_lock_and_undo`; line_start: 3073; line_end: 3123; file_sha256: `107f89e02adef0e504c02298f9d4d7cdfc6f4306094fdc5725f1193624e8b2de`; evidence_state: `COMMIT`
  - path: `storage/innobase/lock/lock0lock.cc`; symbol: `lock_clust_rec_modify_check_and_lock`; line_start: 5246; line_end: 5292; file_sha256: `f980965075e998cb30a982223411f383c9052d092ad69ebfe5b5aeb5b3726550`; evidence_state: `COMMIT`
  - path: `storage/innobase/lock/lock0lock.cc`; symbol: `lock_sec_rec_modify_check_and_lock`; line_start: 5298; line_end: 5353; file_sha256: `f980965075e998cb30a982223411f383c9052d092ad69ebfe5b5aeb5b3726550`; evidence_state: `COMMIT`
- runtime_run_ids: []
- limitations_ko: secondary index별 update ordering 전체는 추적하지 않았다.
- report_locations: [`mysql-comparison#MYSQL-C023`]

#### MYSQL-C024

- id: `MYSQL-C024`
- database: `mysql`
- revision: `06a5c1c99c377fc41b2eba1ea244e8b220bdc3c8`
- claim_ko: INSERT는 table IX를 취하고 새 entry에 현재 transaction ID를 기록한다. 새/변경 record는 그 transaction ID로 implicit X ownership을 표현하므로 충돌이 없을 때 모든 record마다 explicit X `lock_t`를 만들 필요가 없다.
- kind: `source`
- confidence: `SOURCE-CONFIRMED`
- comparison: `partial analogy`; CUBRID self-lock과 목적 일부는 닮았지만 자원 모델은 다르다.
- source_refs:
  - path: `storage/innobase/row/row0ins.cc`; symbol: `row_ins_step`; line_start: 3647; line_end: 3733; file_sha256: `4663213c4e443450323908184eae6477c63cf5e376cfa7385b3400fcc19c4f30`; evidence_state: `COMMIT`
  - path: `storage/innobase/include/lock0priv.h`; symbol: `LOCK_REC_NOT_GAP`; line_start: 344; line_end: 445; file_sha256: `2c035baaf4a24ed0d3d2daa68cdcbf73a81b2c77d89965ecdf530c26b3326ea0`; evidence_state: `COMMIT`
- runtime_run_ids: []
- limitations_ko: transaction ID가 record ownership의 증거라는 뜻이지 transaction ID 자체가 lock resource라는 뜻은 아니다.
- report_locations: [`mysql-comparison#MYSQL-C024`]

#### MYSQL-C025

- id: `MYSQL-C025`
- database: `mysql`
- revision: `06a5c1c99c377fc41b2eba1ea244e8b220bdc3c8`
- claim_ko: secondary/clustered unique-key duplicate scan은 가능한 duplicate record/gap에 보통 S lock을 요청하고, replace/on-duplicate 계열은 X를 쓸 수 있다. 잠금이 성공한 뒤 duplicate를 판정하며, lock wait에서 깨어난 insert는 같은 state를 재실행해 조건을 다시 확인한다.
- kind: `source`
- confidence: `SOURCE-CONFIRMED`
- comparison: `partial analogy`; “같은 미커밋 unique key에서 기다렸다가 결과 재판정”하는 rendezvous가 핵심이다.
- source_refs:
  - path: `storage/innobase/row/row0ins.cc`; symbol: `row_ins_scan_sec_index_for_duplicate`; line_start: 1918; line_end: 2092; file_sha256: `4663213c4e443450323908184eae6477c63cf5e376cfa7385b3400fcc19c4f30`; evidence_state: `COMMIT`
  - path: `storage/innobase/row/row0ins.cc`; symbol: `row_ins_duplicate_error_in_clust`; line_start: 2170; line_end: 2295; file_sha256: `4663213c4e443450323908184eae6477c63cf5e376cfa7385b3400fcc19c4f30`; evidence_state: `COMMIT`
  - path: `storage/innobase/row/row0ins.cc`; symbol: `row_ins_sec_index_entry_low`; line_start: 2827; line_end: 3005; file_sha256: `4663213c4e443450323908184eae6477c63cf5e376cfa7385b3400fcc19c4f30`; evidence_state: `COMMIT`
  - path: `storage/innobase/row/row0mysql.cc`; symbol: `row_mysql_handle_errors`; line_start: 651; line_end: 727; file_sha256: `08db672d4177b27b5f95a3a4507a0965fe0e3e5991d099a76afa4d37e9489100`; evidence_state: `COMMIT`
  - path: `storage/innobase/row/row0mysql.cc`; symbol: `row_insert_for_mysql_using_ins_graph`; line_start: 1498; line_end: 1600; file_sha256: `08db672d4177b27b5f95a3a4507a0965fe0e3e5991d099a76afa4d37e9489100`; evidence_state: `COMMIT`
- runtime_run_ids: []
- limitations_ko: 어떤 unique index record/gap이 선택되는지는 B-tree 탐색과 isolation level에 의존한다.
- report_locations: [`mysql-comparison#MYSQL-C025`]

#### MYSQL-C026

- id: `MYSQL-C026`
- database: `mysql`
- revision: `06a5c1c99c377fc41b2eba1ea244e8b220bdc3c8`
- claim_ko: foreign-key 검사 경로는 referenced table에 IS를 확보하고, 일치하는 referenced record 또는 필요한 gap에 S lock을 건 뒤 제약 결과를 평가한다. 즉 FK conflict 관찰자도 record-lock 기반 rendezvous의 한 사례다.
- kind: `source`
- confidence: `SOURCE-CONFIRMED`
- comparison: `partial analogy`.
- source_refs:
  - path: `storage/innobase/row/row0ins.cc`; symbol: `row_ins_set_rec_lock`; line_start: 1371; line_end: 1400; file_sha256: `4663213c4e443450323908184eae6477c63cf5e376cfa7385b3400fcc19c4f30`; evidence_state: `COMMIT`
  - path: `storage/innobase/row/row0ins.cc`; symbol: `row_ins_check_foreign_constraint`; line_start: 1412; line_end: 1735; file_sha256: `4663213c4e443450323908184eae6477c63cf5e376cfa7385b3400fcc19c4f30`; evidence_state: `COMMIT`
- runtime_run_ids: []
- limitations_ko: FK option별 cascade 수행은 조사하지 않았다. 함수 내부의 FK-check enable predicate 이름/조건을 사용자 관점 의미로 재해석하지 않았다.
- report_locations: [`mysql-comparison#MYSQL-C026`]

#### MYSQL-C027

- id: `MYSQL-C027`
- database: `mysql`
- revision: `06a5c1c99c377fc41b2eba1ea244e8b220bdc3c8`
- claim_ko: MVCC consistent read가 record S lock을 생략해도 SQL layer의 MDL은 테이블 정의/DDL과의 조정을 계속 담당한다. MySQL의 “읽기 무잠금”은 metadata까지 무잠금이라는 뜻이 아니다.
- kind: `inference`
- confidence: `INFERRED`
- comparison: `partial analogy`; lock ownership split을 책에서 반드시 분리해 설명해야 한다.
- source_refs:
  - path: `sql/mdl.h`; symbol: `enum_mdl_type`; line_start: 197; line_end: 327; file_sha256: `c43186485e83c94018abc88b7490bff7281eaf0a94b5f523932fa6bdc7be43a2`; evidence_state: `COMMIT`
  - path: `sql/sql_base.cc`; symbol: `open_table_get_mdl_lock`; line_start: 2638; line_end: 2761; file_sha256: `2a108465126fceb8e0b996179a912e58a7cb5cd4630f8f7b46366e4816d26e1a`; evidence_state: `COMMIT`
  - path: `storage/innobase/row/row0sel.cc`; symbol: `row_search_mvcc`; line_start: 4437; line_end: 5395; file_sha256: `418edef00f0a8cba8875deac251f0581ceb98f16af99fac296eab2136b78aa1b`; evidence_state: `COMMIT`
- premises_ko: 정상 table open은 MDL을 획득하고, 그 뒤 InnoDB `LOCK_NONE` branch는 read view/previous version을 쓰며 record S acquire branch를 타지 않는다.
- falsifier_ko: 정상 persistent table의 plain consistent SELECT가 MDL을 전혀 획득하지 않거나, `LOCK_NONE` branch가 data record S lock을 필수로 생성하는 reachable 경로가 확인되면 이 추론은 폐기한다.
- runtime_run_ids: []
- limitations_ko: MDL과 InnoDB lock을 가로지르는 하나의 통합 compatibility matrix가 있다는 뜻은 아니다.
- report_locations: [`mysql-comparison#MYSQL-C027`]

### mvccid-self-lock-rendezvous

#### MYSQL-C028

- id: `MYSQL-C028`
- database: `mysql`
- revision: `06a5c1c99c377fc41b2eba1ea244e8b220bdc3c8`
- claim_ko: clustered record의 implicit X owner 후보는 record의 `DB_TRX_ID`에서 읽고, `trx_rw_is_active`로 그 transaction ID가 active RW transaction인지 확인한다. secondary index는 별도 heuristic/clustered lookup 경로로 implicit owner를 판정한다.
- kind: `source`
- confidence: `SOURCE-CONFIRMED`
- comparison: `partial analogy`; MVCC transaction ID가 소유자 식별자라는 점만 닮았다.
- source_refs:
  - path: `storage/innobase/include/lock0priv.ic`; symbol: `lock_clust_rec_some_has_impl`; line_start: 52; line_end: 59; file_sha256: `a6d743a280290a6b6a6bc7d122853e6a8cd9614e97577408375648ef47c12463`; evidence_state: `COMMIT`
  - path: `storage/innobase/include/trx0sys.ic`; symbol: `trx_rw_is_active`; line_start: 140; line_end: 185; file_sha256: `5915fb1c33296f4e1401673f1e835490ac303c6a49a365cf4cc6b05f91d69645`; evidence_state: `COMMIT`
  - path: `storage/innobase/lock/lock0lock.cc`; symbol: `lock_sec_rec_some_has_impl`; line_start: 963; line_end: 1007; file_sha256: `f980965075e998cb30a982223411f383c9052d092ad69ebfe5b5aeb5b3726550`; evidence_state: `COMMIT`
- runtime_run_ids: []
- limitations_ko: secondary-index false positive/false negative 회피의 전체 알고리즘은 범위 밖이다.
- report_locations: [`mysql-comparison#MYSQL-C028`]

#### MYSQL-C029

- id: `MYSQL-C029`
- database: `mysql`
- revision: `06a5c1c99c377fc41b2eba1ea244e8b220bdc3c8`
- claim_ko: 다른 트랜잭션이 implicit-X-owned record에 S/X lock을 요청하면 InnoDB는 owner가 아직 committed-in-memory가 아니고 explicit X를 갖지 않은 경우 owner를 대신해 explicit record X를 만든 뒤 requester를 그 record resource에 대기시킨다.
- kind: `source`
- confidence: `SOURCE-CONFIRMED`
- comparison: `partial analogy`; self-lock이 아니라 “implicit record ownership의 contention-time materialization”이다.
- source_refs:
  - path: `storage/innobase/lock/lock0lock.cc`; symbol: `lock_rec_convert_impl_to_expl_for_trx`; line_start: 5137; line_end: 5195; file_sha256: `f980965075e998cb30a982223411f383c9052d092ad69ebfe5b5aeb5b3726550`; evidence_state: `COMMIT`
  - path: `storage/innobase/lock/lock0lock.cc`; symbol: `lock_rec_convert_impl_to_expl`; line_start: 5197; line_end: 5237; file_sha256: `f980965075e998cb30a982223411f383c9052d092ad69ebfe5b5aeb5b3726550`; evidence_state: `COMMIT`
  - path: `storage/innobase/lock/lock0lock.cc`; symbol: `lock_clust_rec_read_check_and_lock`; line_start: 5405; line_end: 5454; file_sha256: `f980965075e998cb30a982223411f383c9052d092ad69ebfe5b5aeb5b3726550`; evidence_state: `COMMIT`
- runtime_run_ids: []
- limitations_ko: 변환 대상은 해당 index record이며 owner transaction 전체를 대표하는 단일 lock resource가 아니다.
- report_locations: [`mysql-comparison#MYSQL-C029`]

#### MYSQL-C030

- id: `MYSQL-C030`
- database: `mysql`
- revision: `06a5c1c99c377fc41b2eba1ea244e8b220bdc3c8`
- claim_ko: materialized record conflict 후 requester의 `wait_lock`과 `blocking_trx`가 transaction-to-transaction wait-for graph를 만들지만, graph edge의 원인이 된 실제 lock resource는 table 또는 record다. 따라서 transaction wait graph의 존재는 transaction-ID lock resource의 존재를 뜻하지 않는다.
- kind: `inference`
- confidence: `INFERRED`
- comparison: `no direct equivalent`; bookkeeping과 resource를 분리하는 핵심 주의점이다.
- source_refs:
  - path: `storage/innobase/include/trx0trx.h`; symbol: `trx_lock_t`; line_start: 396; line_end: 455; file_sha256: `8b451929d5ecc4c7677e55055da3da84ae3e351f5a1da3df98f5e4c1653fc1d3`; evidence_state: `COMMIT`
  - path: `storage/innobase/include/lock0lock.h`; symbol: `LOCK_TABLE`; line_start: 959; line_end: 1007; file_sha256: `47150953daad95254bb80a5e573336d2d8c7bf471fd5cb1eeb93b8723ad2c3bb`; evidence_state: `COMMIT`
  - path: `storage/innobase/lock/lock0lock.cc`; symbol: `lock_create_wait_for_edge`; line_start: 1387; line_end: 1408; file_sha256: `f980965075e998cb30a982223411f383c9052d092ad69ebfe5b5aeb5b3726550`; evidence_state: `COMMIT`
- premises_ko: lock resource type/payload는 table 또는 record이고, `wait_lock`은 그 `lock_t`를 가리키며 `blocking_trx`는 blocker transaction pointer로 기록된다.
- falsifier_ko: transaction ID를 resource key로 해시/queue하고 S/X compatibility를 적용하는 reachable `lock_t` 종류가 확인되면 이 추론은 폐기한다.
- runtime_run_ids: []
- limitations_ko: lock resource type의 부재와 트랜잭션 간 wait edge의 부재를 혼동하지 않는다. 후자는 분명히 존재한다.
- report_locations: [`mysql-comparison#MYSQL-C030`]

#### MYSQL-C031

- id: `MYSQL-C031`
- database: `mysql`
- revision: `06a5c1c99c377fc41b2eba1ea244e8b220bdc3c8`
- claim_ko: same uncommitted unique-key 충돌에서 T1 commit은 먼저 active/implicit ownership 종료를 게시하고 explicit record lock을 해제하여 T2를 깨운다. T2 insert state machine은 깨어난 뒤 동일 duplicate-check 경로를 다시 실행해 commit/rollback 결과에 맞는 최종 판정을 한다.
- kind: `inference`
- confidence: `INFERRED`
- comparison: `partial analogy`; wait–wake–recheck 프로토콜은 닮지만 rendezvous 자원은 record다.
- source_refs:
  - path: `storage/innobase/trx/trx0trx.cc`; symbol: `trx_release_impl_and_expl_locks`; line_start: 1874; line_end: 1983; file_sha256: `3128c6a43a6ed4e6465f4b28cc6eff5b3a6ad6e6d4a3e6f03b7788ece7d9cf65`; evidence_state: `COMMIT`
  - path: `storage/innobase/trx/trx0trx.cc`; symbol: `trx_commit_in_memory`; line_start: 1985; line_end: 2042; file_sha256: `3128c6a43a6ed4e6465f4b28cc6eff5b3a6ad6e6d4a3e6f03b7788ece7d9cf65`; evidence_state: `COMMIT`
  - path: `storage/innobase/lock/lock0lock.cc`; symbol: `lock_trx_release_locks`; line_start: 5800; line_end: 5850; file_sha256: `f980965075e998cb30a982223411f383c9052d092ad69ebfe5b5aeb5b3726550`; evidence_state: `COMMIT`
  - path: `storage/innobase/row/row0ins.cc`; symbol: `row_ins`; line_start: 3576; line_end: 3641; file_sha256: `4663213c4e443450323908184eae6477c63cf5e376cfa7385b3400fcc19c4f30`; evidence_state: `COMMIT`
  - path: `storage/innobase/row/row0mysql.cc`; symbol: `row_mysql_handle_errors`; line_start: 651; line_end: 727; file_sha256: `08db672d4177b27b5f95a3a4507a0965fe0e3e5991d099a76afa4d37e9489100`; evidence_state: `COMMIT`
  - path: `storage/innobase/row/row0mysql.cc`; symbol: `row_insert_for_mysql_using_ins_graph`; line_start: 1498; line_end: 1600; file_sha256: `08db672d4177b27b5f95a3a4507a0965fe0e3e5991d099a76afa4d37e9489100`; evidence_state: `COMMIT`
- premises_ko: duplicate scan이 record lock 뒤 조건을 판정하고, commit은 implicit ownership 종료 게시 뒤 explicit lock을 풀며, successful lock wait 복귀는 `goto run_again`으로 같은 insert node/index state를 재실행한다.
- falsifier_ko: 정상 insert graph가 successful wait 복귀 뒤 duplicate/FK 검사를 건너뛰고 결과를 확정하거나, same-key 충돌이 record가 아닌 transaction-ID lock resource에서 해결되는 경로가 확인되면 이 추론은 폐기한다.
- runtime_run_ids: []
- limitations_ko: T1 rollback의 undo/record removal 전 경로는 추적하지 않았지만 T2의 wake 후 재검사 원칙은 직접 증명된다.
- report_locations: [`mysql-comparison#MYSQL-C031`]

#### MYSQL-C032

- id: `MYSQL-C032`
- database: `mysql`
- revision: `06a5c1c99c377fc41b2eba1ea244e8b220bdc3c8`
- claim_ko: InnoDB implicit record X의 필요성은 새로 삽입·수정한 많은 record마다 explicit lock object를 만들지 않고도 transaction ID로 writer ownership을 나타내고, 실제 waiter가 생길 때만 explicit X를 materialize하는 데 있다.
- kind: `source`
- confidence: `SOURCE-CONFIRMED`
- comparison: `partial analogy`; CUBRID MVCCID self-lock과 “잠금 객체 수 절감 + 미커밋 writer rendezvous” 목적은 일부 겹치지만 aggregation 단위가 정반대다.
- source_refs:
  - path: `storage/innobase/include/lock0priv.h`; symbol: `LOCK_REC_NOT_GAP`; line_start: 344; line_end: 445; file_sha256: `2c035baaf4a24ed0d3d2daa68cdcbf73a81b2c77d89965ecdf530c26b3326ea0`; evidence_state: `COMMIT`
  - path: `storage/innobase/lock/lock0lock.cc`; symbol: `lock_rec_lock`; line_start: 1849; line_end: 1878; file_sha256: `f980965075e998cb30a982223411f383c9052d092ad69ebfe5b5aeb5b3726550`; evidence_state: `COMMIT`
  - path: `storage/innobase/lock/lock0lock.cc`; symbol: `lock_rec_convert_impl_to_expl_for_trx`; line_start: 5137; line_end: 5195; file_sha256: `f980965075e998cb30a982223411f383c9052d092ad69ebfe5b5aeb5b3726550`; evidence_state: `COMMIT`
- runtime_run_ids: []
- limitations_ko: 메모리 절감량을 수치화하지 않았고 runtime benchmark도 수행하지 않았다.
- report_locations: [`mysql-comparison#MYSQL-C032`]

#### MYSQL-C033

- id: `MYSQL-C033`
- database: `mysql`
- revision: `06a5c1c99c377fc41b2eba1ea244e8b220bdc3c8`
- claim_ko: 고정 revision의 MySQL server/InnoDB 잠금 인터페이스와 관련 구현에서 CUBRID식 “MVCCID 자체를 S/X로 잠그고 owner가 자기 MVCCID에 X self-lock을 보유하는” 직접 대응 자원은 확인되지 않았다. 가장 가까운 것은 per-record implicit X conversion과 transaction wait edge이며, 둘 다 direct equivalent가 아니다.
- kind: `source`
- confidence: `SOURCE-CONFIRMED`
- comparison: `no direct equivalent`; implicit record lock과 wait graph는 각각 `partial analogy`.
- source_refs:
  - path: `storage/innobase/include/lock0lock.h`; symbol: `LOCK_TABLE`; line_start: 959; line_end: 1007; file_sha256: `47150953daad95254bb80a5e573336d2d8c7bf471fd5cb1eeb93b8723ad2c3bb`; evidence_state: `COMMIT`
  - path: `storage/innobase/include/lock0priv.h`; symbol: `lock_table_t`; line_start: 53; line_end: 445; file_sha256: `2c035baaf4a24ed0d3d2daa68cdcbf73a81b2c77d89965ecdf530c26b3326ea0`; evidence_state: `COMMIT`
  - path: `storage/innobase/include/trx0trx.h`; symbol: `trx_lock_t`; line_start: 396; line_end: 455; file_sha256: `8b451929d5ecc4c7677e55055da3da84ae3e351f5a1da3df98f5e4c1653fc1d3`; evidence_state: `COMMIT`
- search_coverage:
  - `rg -n -i "self[-_ ]lock|mvcc[-_ ]id|mvccid|lock_resource_transaction|resource_transaction" storage/innobase sql include` → `0 matches`
  - lock resource constants/types and `lock_t` union을 양의 방향으로 확인한 결과 `LOCK_TABLE`/`LOCK_REC`, `dict_table_t *`, page+heap bitmap만 확인했다.
- runtime_run_ids: []
- limitations_ko: 이 음성 결론은 pinned revision의 server/InnoDB source 범위에 한정한다. transaction-to-transaction waiting 자체는 존재하며 부정하지 않는다.
- report_locations: [`mysql-comparison#MYSQL-C033`]

## 공통 account 시나리오의 호출 경로

가정: `account(id UNIQUE/PRIMARY KEY, balance, ...)`. T1은 기존 행을 UPDATE하고 새 unique key를 INSERT한다. T2는 plain SELECT, `SELECT ... FOR UPDATE`, 같은 행 UPDATE, 같은 미커밋 unique key INSERT를 시도한다. SQL parser/planner의 모든 중간 프레임은 범위 밖이며, 아래는 lock 의미를 결정하는 가장 가까운 server/InnoDB 경로다.

### 공통 진입: metadata 보호와 InnoDB data-lock 정책의 분리

```text
SQL table open
  -> open_table_get_mdl_lock()                       sql/sql_base.cc:2638-2761
     -> MDL_context::acquire_lock()                  sql/mdl.cc:3364-3450
        -> MDL_lock::can_grant_lock()                sql/mdl.cc:2399-2463
        -> [conflict] MDL wait/deadlock/timeout

InnoDB handler execution
  -> ha_innobase::external_lock()                    storage/innobase/handler/ha_innodb.cc:19058-19135
     -> selects LOCK_NONE / LOCK_S / LOCK_X policy
  -> row_search_mvcc() or row_upd_step()/row_ins_step()
     -> InnoDB table/record lock_sys
```

MDL wait lifecycle의 가장 가까운 전체 경로:

```text
open_table_get_mdl_lock()
  -> MDL_context::acquire_lock()                     sql/mdl.cc:3364-3450
     -> try immediate grant
     -> enqueue MDL ticket and wait with timeout
     -> MDL_context::find_deadlock()                 sql/mdl.cc:4049-4089
transaction/statement cleanup
  -> MDL_context::release_lock()                     sql/mdl.cc:4100-4212
  -> MDL_context::release_transactional_locks()      sql/mdl.cc:4513-4517
```

`open_table_get_mdl_lock`의 comment(`sql/sql_base.cc:2712-2732`)는 MDL-only deadlock과 MDL/InnoDB row lock을 가로지르는 cycle을 구분하고 후자의 일부가 timeout에 의해 해소됨을 경고한다. 따라서 MDL과 InnoDB에 하나의 통합 deadlock graph가 있다고 서술하면 안 된다.

### T1: 기존 account 행 UPDATE

```text
row_upd_step()                                       storage/innobase/row/row0upd.cc:3242-3317
  -> trx_start_if_not_started_xa_low()
  -> lock_table(..., LOCK_IX, ...)                   storage/innobase/lock/lock0lock.cc:3516-3608
  -> row_upd()
     -> btr_cur_update_in_place()/update path        storage/innobase/btr/btr0cur.cc:3313-3367
        -> btr_cur_upd_lock_and_undo()               storage/innobase/btr/btr0cur.cc:3073-3123
           -> lock_clust_rec_modify_check_and_lock() storage/innobase/lock/lock0lock.cc:5246-5292
              -> lock_rec_convert_impl_to_expl()
              -> lock_rec_lock(impl=true,
                   LOCK_X | LOCK_REC_NOT_GAP, ...)
```

충돌이 없다면 `impl=true` 때문에 explicit record `lock_t`를 생략할 수 있고, 새 row version의 transaction ID가 implicit X ownership을 표현한다. 이미 다른 writer가 있으면 implicit ownership을 explicit X로 변환한 뒤 T1/T2 중 후행 writer가 waiting lock과 `blocking_trx` edge를 가진다.

### T1: 새 unique account key INSERT

```text
row_insert_for_mysql_using_ins_graph()               storage/innobase/row/row0mysql.cc:1551-1600
  -> row_ins_step()                                  storage/innobase/row/row0ins.cc:3647-3733
     -> write current trx id into row entry          storage/innobase/row/row0ins.cc:3685-3686
     -> lock_table(..., LOCK_IX, ...)
     -> row_ins()                                    storage/innobase/row/row0ins.cc:3576-3641
        -> row_ins_sec_index_entry_low()             storage/innobase/row/row0ins.cc:2965-3005
           -> row_ins_scan_sec_index_for_duplicate() storage/innobase/row/row0ins.cc:1918-2092
        -> clustered duplicate path                  storage/innobase/row/row0ins.cc:2170-2295
```

삽입된 record는 row transaction ID로 T1의 implicit X ownership을 표현한다. 이는 T1의 transaction ID 자원 하나에 X self-lock을 잡는 것이 아니라 각 inserted/modified index record의 논리적 X다.

### T2: plain SELECT

보통 REPEATABLE READ/READ COMMITTED의 nonlocking read path:

```text
ha_innobase::external_lock()
  -> select_lock_type = LOCK_NONE                    storage/innobase/handler/ha_innodb.cc:19058-19135
row_search_mvcc()                                    storage/innobase/row/row0sel.cc:4780-4860
  -> trx_assign_read_view()                          storage/innobase/trx/trx0trx.cc:2350-2366
     -> ReadView::prepare()                          storage/innobase/read/read0read.cc:441-464
  -> ReadView::changes_visible()                     storage/innobase/include/read0types.h:156-175
  -> [current version invisible] build previous ver storage/innobase/row/row0sel.cc:5328-5395
```

따라서 T2 plain SELECT는 T1의 record X에 보통 대기하지 않고 snapshot-visible 이전 버전을 읽는다. 다만 table definition을 보호하는 MDL shared read는 별도로 존재한다. SERIALIZABLE/autocommit 예외는 MYSQL-C020의 한계에 따른다.

### T2: `SELECT ... FOR UPDATE`

```text
ha_innobase::external_lock()
  -> select_lock_type = LOCK_X                       storage/innobase/handler/ha_innodb.cc:19058-19135
row_search_mvcc()                                    storage/innobase/row/row0sel.cc:4780-4860
  -> lock_table(..., LOCK_IX, ...)
  -> choose gap/record mode                          storage/innobase/row/row0sel.cc:5232-5323
  -> sel_set_rec_lock(..., LOCK_X, ...)              storage/innobase/row/row0sel.cc:1144-1185
     -> lock_clust_rec_read_check_and_lock()         storage/innobase/lock/lock0lock.cc:5405-5454
        -> lock_rec_convert_impl_to_expl()
        -> lock_rec_lock()
```

T1이 해당 record를 implicit X로 소유하면 먼저 T1을 위한 explicit record X를 만들고, T2 X request가 같은 record resource에 wait한다.

### T2: 같은 기존 행 UPDATE

```text
row_upd_step()
  -> table IX
  -> btr_cur_upd_lock_and_undo()
     -> lock_clust_rec_modify_check_and_lock()
        -> convert T1 implicit X to explicit X if needed
        -> request T2 X on the same record
           -> lock_rec_lock_slow()                   storage/innobase/lock/lock0lock.cc:1717-1828
              -> RecLock::add_to_waitq()             storage/innobase/lock/lock0lock.cc:1413-1462
                 -> lock_create_wait_for_edge()      storage/innobase/lock/lock0lock.cc:1387-1408
                    -> T2.wait_lock, T2.blocking_trx=T1
```

여기서 “T2가 T1 transaction ID lock을 요청한다”고 쓰면 틀리다. T2가 요청한 것은 record X이고, `blocking_trx=T1`은 deadlock/wakeup을 위한 edge다.

### T2: 같은 미커밋 unique key INSERT

```text
row_ins_step()
  -> table IX
  -> row_ins()
     -> row_ins_scan_sec_index_for_duplicate()
        -> row_ins_set_rec_lock(..., LOCK_S, ...)    storage/innobase/row/row0ins.cc:1371-1400
           -> lock_sec/clust_rec_read_check_and_lock()
              -> discover T1 implicit owner
              -> lock_rec_convert_impl_to_expl_for_trx(T1)
                 -> create explicit X for T1 on that record
              -> enqueue T2 S/X request on record
                 -> T2 waits with blocking_trx=T1

T1 commit
  -> trx_commit_in_memory()                          storage/innobase/trx/trx0trx.cc:1985-2042
     -> trx_release_impl_and_expl_locks()            storage/innobase/trx/trx0trx.cc:1874-1983
        -> publish COMMITTED_IN_MEMORY/remove active
        -> lock_trx_release_locks()                  storage/innobase/lock/lock0lock.cc:5800-5850
        -> dequeue/grant/update edge
           -> lock_wait_release_thread_if_suspended() storage/innobase/lock/lock0wait.cc:357-464

T2 wake
  -> row_mysql_handle_errors(DB_LOCK_WAIT)           storage/innobase/row/row0mysql.cc:651-727
  -> row_insert_for_mysql_using_ins_graph(): goto run_again
  -> row_ins_step()/row_ins() same index state
  -> duplicate/FK condition recheck
```

T1 commit이면 T2는 committed duplicate를 보고 duplicate error/ON DUPLICATE 계열 처리를 결정한다. T1 rollback이면 rollback 결과를 반영해 다시 삽입 가능성을 판단한다. 여기서 source가 직접 보장하는 핵심은 **wait 뒤 동일 state의 제약 검사를 다시 실행한다**는 점이다.

### FK observer의 가장 가까운 변형

```text
row_ins_check_foreign_constraint()                   storage/innobase/row/row0ins.cc:1412-1735
  -> lock_table(referenced_table, LOCK_IS, ...)
  -> row_ins_set_rec_lock(LOCK_S, referenced record/gap)
  -> [possible conflict] regular record wait path
  -> evaluate referenced row / constraint after lock success
```

이 경로도 “미커밋 결과가 확정될 때까지 기다린 뒤 재판정” 책임을 수행하지만, transaction-ID self-lock이 아니라 referenced index record/gap S lock이다.

## 대기·deadlock·release 상세 경로

```text
conflicting record request
  -> lock_rec_lock_fast() fails/needs slow path       lock0lock.cc:1594-1678
  -> lock_rec_lock_slow()                            lock0lock.cc:1717-1828
  -> RecLock::add_to_waitq()                         lock0lock.cc:1413-1462
     -> lock_create_wait_for_edge()                  lock0lock.cc:1387-1408
  -> DB_LOCK_WAIT
  -> lock_wait_suspend_thread()                      lock0wait.cc:206-355

timeout/interrupt
  -> lock_wait_check_and_cancel()                    lock0wait.cc:465-558
  -> lock_cancel_waiting_and_release()               lock0lock.cc:5727-5740

deadlock detector thread
  -> lock_wait_snapshot_waiting_threads()            lock0wait.cc:564-690
  -> lock_wait_find_and_handle_deadlocks()           lock0wait.cc:1267-1318
  -> lock_wait_rollback_deadlock_victim()            lock0wait.cc:692-704

normal blocker release
  -> lock_rec_dequeue_from_page()                    lock0lock.cc:2288-2323
  -> lock_grant_or_update_wait_for_edge()            lock0lock.cc:2222-2247
  -> lock_grant()                                    lock0lock.cc:1910-1942
  -> lock_wait_release_thread_if_suspended()         lock0wait.cc:357-464
```

Table lock은 별도 dequeue/grant 경로(`lock0lock.cc:3676-3739`)를 가진다. 스케줄링은 grant 가능한 모든 waiter를 단순 FIFO로 깨우는 한 문장으로 축약하지 말아야 하며, record release 쪽은 CATS schedule/update 코드(`lock0lock.cc:2110-2215`)가 개입한다.

## 강한 음성 검색과 no-equivalent 판정

### CUBRID식 MVCCID self-lock 자원

실행한 검색:

```text
rg -n -i "self[-_ ]lock|mvcc[-_ ]id|mvccid|lock_resource_transaction|resource_transaction" \
  storage/innobase sql include
```

결과: `0 matches`.

이 단어 검색만으로 결론내리지 않고 다음 양의 구조 확인을 함께 수행했다.

- `lock0lock.h:959-1007`: lock object type은 `LOCK_TABLE`, `LOCK_REC`; 나머지는 mode/state/range flag다.
- `lock0priv.h:53-91`: resource payload는 `dict_table_t *` 또는 page ID + heap bitmap이다.
- `trx0trx.h:396-455`: transaction에는 lock list, `wait_lock`, `blocking_trx`가 있지만 “transaction ID resource” union member가 없다.
- `lock0priv.h:344-445`, `lock0lock.cc:5137-5237`: transaction ID는 implicit record owner 탐지와 contention 시 explicit **record X** 생성에 쓰인다.

따라서 고정 revision/source 범위에서 직접 MVCCID S/X resource는 `no equivalent`로 분류한다. 단, 이는 transaction 간 waiting 자체가 없다는 뜻이 아니다. transaction wait edge와 implicit record-lock conversion은 `partial analogy`다.

### Lock escalation

실행한 검색:

```text
rg -n -i "lock escalation|lock_escalat|escalat(e|ion|ing).*lock|lock.*escalat(e|ion|ing)" \
  storage/innobase/lock storage/innobase/row storage/innobase/trx \
  storage/innobase/include sql include
```

결과: `0 matches`.

양의 구조 확인으로 `trx_lock_t::n_rec_locks`는 count/statistics이고, `sel_set_rec_lock`은 매우 많은 lock과 buffer pressure에서 `DB_LOCK_TABLE_FULL`을 반환하는 경로를 보였다. 고정 revision에서 count-based table escalation은 확인되지 않았다. 전 역사/모든 plugin에 대한 보편 부정은 하지 않는다.

## 의미 차이와 책에 넣어야 할 analogy cautions

1. **MDL은 metadata lock이다.** `MDL_SHARED_WRITE`라는 이름 때문에 row X lock과 혼동하면 안 된다. DML 중 table definition 안정성을 잡는 shared metadata intent이지, 수정 대상 record의 데이터 X를 대신하지 않는다.
2. **InnoDB record lock은 index record/gap lock이다.** 동일 SQL row가 여러 index entry와 관계될 수 있으며 next-key/gap 범위가 있다.
3. **`LOCK_NONE`은 저장되는 lock mode가 아니다.** consistent-read 경로를 선택하는 marker이며 read view/old version으로 읽는다.
4. **Implicit X는 per-record ownership이다.** row의 transaction ID가 writer를 가리키고 contention 때 그 record에 explicit X를 materialize한다.
5. **`blocking_trx`는 wait edge다.** T2가 T1을 기다린다는 사실과 T1 ID가 lock resource라는 주장은 다르다.
6. **가장 가까운 self-lock 유사성은 목적에 있다.** explicit 객체 절감, uncommitted result observer의 wait, commit/rollback 뒤 recheck라는 목적은 겹친다. CUBRID MVCCID self-lock처럼 한 transaction-scoped resource에 다수 row observer를 rendezvous시키는 구조는 확인되지 않았다.
7. **MDL과 InnoDB graph는 통합 하나가 아니다.** `open_table_get_mdl_lock` comment는 두 subsystem을 가로지르는 cycle의 timeout 의존 가능성을 명시한다.
8. **Lock escalation을 가정하지 않는다.** record-lock pressure와 table intention lock의 동시 존재를 escalation 결과로 오해하면 안 된다.

## Evidence gaps, unknowns, contradictions

### 확인하지 못했거나 범위를 제한한 항목

- SQL parser/resolver부터 모든 statement 종류가 특정 MDL request를 생성하는 전체 호출 사슬은 추적하지 않았다. `enum_mdl_type`의 명시적 용도와 `open_table_get_mdl_lock` 획득 경로를 근거로 했다.
- isolation level, semi-consistent read, gap/next-key/predicate lock의 모든 특수 조합은 frozen scope 밖이다.
- MySQL server runtime은 수행하지 않았다. 따라서 실제 wait time, PFS 출력, victim 선택 사례는 이 packet의 evidence가 아니다.
- `trx_resurrect_locks`는 recovered transaction의 table ID에서 IX를 재구성하는 경로까지 증명한다. 모든 lock의 crash persistence/recovery semantics에 대한 일반화는 금지한다.
- T1 rollback의 undo 및 record removal 전 호출 사슬은 완주하지 않았다. 공통 unique-key 시나리오에서 필요한 “T2 wait 후 duplicate/FK 재검사”는 insert retry path로 직접 증명했다.
- FK 코드의 enable/disable predicate는 내부 함수 이름과 조건이 직관과 다르게 읽힐 여지가 있어, 사용자 설정 의미를 이 packet에서 독립 claim으로 만들지 않았다.

### 모순 점검

- `lock0priv.h`의 implicit-lock 설명, `lock_rec_convert_impl_to_expl*` 구현, record read/modify caller의 순서는 서로 일치했다.
- `trx_release_impl_and_expl_locks` comment의 implicit-lock release 시점과 `trx_rw_is_active` 기반 owner lookup은 일치했다.
- `LOCK_TABLE`/`LOCK_REC` type 정의와 `lock_t` resource union은 일치했다.
- 발견된 모순은 없다. 다만 source comment가 개념 모델을 설명하는 범위와 특정 isolation/secondary-index 예외를 구분해 사용했다.

## Runtime/experiment handoff

- runtime_run_ids: []
- 이 역할은 source-only이고 서버 runtime을 실행하지 않았다.
- 책/실험 담당이 검증한다면 공통 account 시나리오에서 다음 관찰을 구분해야 한다: plain SELECT의 non-waiting snapshot read, `FOR UPDATE`/same-row UPDATE의 record wait, same-key INSERT의 wait 뒤 duplicate 재판정, metadata DDL wait. 단, 이 제안은 본 packet의 증거가 아니다.
