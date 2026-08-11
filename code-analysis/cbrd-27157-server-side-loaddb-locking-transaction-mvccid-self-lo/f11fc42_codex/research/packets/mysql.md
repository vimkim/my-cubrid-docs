# MySQL comparator research packet

- Role: MySQL Comparator (Role 3)
- Topic: `CBRD-27157 server-side loaddb locking, transaction MVCCID self-lock, and BU_LOCK`
- Frozen scope digest: `f07826ef64e37143f055cdf4814be26d965d9bc531421f21439871475722fa5b`
- MySQL source root: `/home/vimkim/gh/mysql/mysql-server`
- MySQL revision: `06a5c1c99c377fc41b2eba1ea244e8b220bdc3c8`
- Branch / evidence state: `trunk`, clean, all MySQL references below are `COMMIT`
- CUBRID comparison revision: `f11fc42594732c263d8f10101f9df73a21346ee9` (dirty worktree; comparison references are `WORKTREE` and carry file hashes)
- Research timestamp (UTC): `2026-08-11T07:06:06Z`
- Runtime experiments: none; this is pinned-source research only

## 먼저 잡아야 할 결론

MySQL/InnoDB에는 CUBRID의 `BU_LOCK` 하나와 정확히 같은 잠금이 없다. 일반 `LOAD DATA`는 다음 세 층을 조합한다.

1. SQL 계층의 테이블 metadata lock인 `MDL_SHARED_WRITE`가 테이블 정의를 보호한다.
2. InnoDB의 테이블 `LOCK_IX`가 “이 트랜잭션이 이 테이블의 레코드를 변경할 예정”임을 표시한다.
3. 실제 충돌은 인덱스 레코드·키 범위·gap의 `S/X/insert-intention` 잠금에서 해결한다.

반면 별도 구문인 `LOAD DATA ... ALGORITHM=BULK`는 SQL 계층에서 `MDL_EXCLUSIVE`를 잡고, 여러 실행 스레드가 **같은 InnoDB `trx_t`**를 사용하여 B-tree subtree를 직접 만든 뒤 합친다. CUBRID처럼 “세션 트랜잭션이 BU를 소유하고, 별도 worker 트랜잭션들은 객체 잠금을 생략한다”는 소유권 분리는 확인되지 않았다.

또한 InnoDB 레코드의 `DB_TRX_ID`는 잠금 자원 키가 아니다. 그것은 implicit record X-lock의 소유 트랜잭션을 알아내는 표식이다. 실제 대기 자원은 레코드 `(space, page, heap_no)`이다. 따라서 CUBRID의 “MVCCID를 자원 키로 하는 X/S self-lock”과는 일부 책임만 닮았다.

## 비교 범위와 두 LOAD 경로

| 구분 | 일반 `LOAD DATA` | `LOAD DATA ... ALGORITHM=BULK` |
|---|---|---|
| SQL metadata lock | 기본 `MDL_SHARED_WRITE` (`LOW_PRIORITY`는 저우선순위 변형) | `MDL_EXCLUSIVE` |
| SQL 진입점 | `Sql_cmd_load_table::execute_inner()` | `Sql_cmd_load_table::execute_bulk()` |
| InnoDB 입력 경로 | 한 행씩 `write_record()` → `ha_write_row()` → `row_insert_for_mysql()` | bulk driver → handler bulk API → `ddl_bulk::Loader` |
| InnoDB table lock | 첫 삽입에서 `LOCK_IX` | 추적한 direct-build 경로에는 일반 `row_ins_step()`/`lock_table(LOCK_IX)` 호출이 없음 |
| 데이터 충돌 단위 | 레코드, next-key, gap, insert intention | 강한 MDL X 아래에서 thread별 subtree를 직접 만들고 종료 시 merge |
| 병렬 소유권 | 일반 SQL 세션의 하나의 `trx_t` | 여러 실행 thread가 같은 handler/prebuilt의 하나의 `trx_t`를 공유 |
| unique 검사 | 기존 index 후보에 S 또는 REPLACE일 때 X를 잡고 중복 판정 | 정렬 입력과 subtree/merge 과정에서 중복 판정 |
| FK 검사 | 참조 index record에 S, 다른 table이면 IS | 로드 후 parent table 이름 MDL을 잡고 parallel full scan으로 검사 |
| 성공/실패 끝 | 일반 SQL 트랜잭션 규칙 | scope guard가 성공 시 statement+implicit commit, 실패 시 둘 다 rollback |

`ha_start_bulk_insert()`라는 이름은 일반 `LOAD DATA`에도 등장하지만, 이것은 handler에게 주는 삽입 최적화 힌트이다. 여기서 분석한 별도 `ALGORITHM=BULK` direct B-tree 경로와 동일시하면 안 된다.

## 공유 비교 축

| 축 | MySQL/InnoDB에서 확인한 소유자와 의미 |
|---|---|
| Responsibility / module | SQL server의 MDL은 이름·정의·table-open 안정성을 담당한다. InnoDB lock subsystem은 table intention과 record/gap 충돌을 담당한다. `ALGORITHM=BULK`의 직접 B-tree 생성은 `ddl_bulk::Loader`/`Btree_multi`가 담당한다. |
| Interface / caller obligation | parser가 `Table_ref`에 MDL mode와 transaction duration request를 넣는다. table open이 MDL을 획득한다. 일반 삽입 graph는 `LOCK_IX` 선행을 보장한 뒤 index entry를 넣는다. |
| Resource identity | MDL: `(namespace=TABLE, schema, table)`; InnoDB table lock: `dict_table_t *`; record lock: `(space_id, page_no, heap_no)` bitmap. `trx_id`는 lock owner와 implicit-lock 판별 정보이지 record lock의 자원 주소가 아니다. |
| Owner | MDL ticket은 `THD`의 `MDL_context`; InnoDB `lock_t`는 `trx_t *trx`를 owner로 가진다. Bulk execution thread별 subtree state도 같은 prebuilt transaction을 사용한다. |
| Lifetime / release | DML table MDL은 `MDL_TRANSACTION`. autocommit이면 statement 끝이 곧 transaction 끝이고, explicit multi-statement transaction이면 commit/rollback까지 유지된다. InnoDB transaction 종료는 active-trx registry에서 제거하고 모든 lock을 해제한다. `AUTO_INC`는 예외적으로 statement 끝에 해제된다. |
| Compatibility | MDL SW끼리는 호환되며 MDL X는 모든 object MDL과 비호환이다. InnoDB IX끼리는 호환되고, IX는 S/X table lock과 비호환이다. 레코드에서는 S/X와 gap 규칙이 적용된다. |
| Wait / retry | MDL acquisition 자체가 conflict 해소를 기다린다. InnoDB record/table request는 `DB_LOCK_WAIT`를 만들고 thread를 suspend한다. 일반 insert graph는 wakeup 후 `row_ins_step()`으로 되돌아가 검사를 다시 수행한다. |
| Commit / abort | full commit과 full rollback은 transaction locks를 모두 끝낸다. lock timeout·duplicate·FK 오류는 기본적으로 statement/savepoint 단위 rollback, deadlock/lock-table-full은 whole transaction rollback이다. |
| Error surface | ordinary path: duplicate/FK/timeout/deadlock 등이 handler error로 변환된다. bulk path: interrupted, unsorted, duplicate, generic bulk-load failure가 main session thread에서 보고된다. |
| Observability | `performance_schema.metadata_locks`, `data_locks`, `data_lock_waits`; `SHOW ENGINE INNODB STATUS` 계열 출력의 latest deadlock과 transaction sections. |
| Performance trade-off | implicit record X-lock은 매 insert마다 explicit `lock_t`를 만들지 않는다. bulk algorithm은 강한 MDL X로 동시 접근을 줄이는 대신, thread별 subtree direct build와 merge를 사용한다. |
| Durability / recovery boundary | 이 패킷은 잠금 소유권과 대기 경로를 추적했다. 일반 WAL/undo와 bulk DDL-log recovery의 전체 crash matrix는 추적 범위 밖이며, “lock 자체가 durable하다”는 주장은 하지 않는다. |

## 완전 호출 경로

### 1. 일반 LOAD의 metadata/table-open 경로

```text
PT_load_table::make_cmd
  ├─ default: mdl_type = MDL_SHARED_WRITE
  ├─ ALGORITHM=BULK: mdl_type = MDL_EXCLUSIVE
  └─ Query_block::add_table_to_list(..., lock_type, mdl_type)
       └─ Table_ref::mdl_request (MDL_TRANSACTION)

Sql_cmd_load_table::execute
  └─ execute_inner
       └─ open_and_lock_tables
            ├─ open_tables
            │    └─ open_table
            │         └─ open_table_get_mdl_lock
            │              └─ MDL_context::acquire_lock (conflict 시 wait/deadlock handling)
            └─ lock_tables
                 └─ mysql_lock_tables
                      └─ handler::external_lock / store_lock notification
```

InnoDB는 `ha_innobase::lock_count()`에서 0을 반환한다. 즉 SQL 계층의 `TL_WRITE*` 이름만 보고 “InnoDB table data lock을 하나 잡았다”고 해석할 수 없다. InnoDB는 MDL과 자기 lock subsystem을 조합한다.

### 2. 일반 LOAD의 행 삽입과 IX 경로

```text
Sql_cmd_load_table::execute_inner
  ├─ handler::ha_start_bulk_insert       (최적화 힌트; ALGORITHM=BULK 아님)
  └─ read_sep_field / read_fixed_length / read_xml_field
       └─ write_record
            └─ handler::ha_write_row
                 └─ ha_innobase::write_row
                      └─ row_insert_for_mysql
                           └─ row_insert_for_mysql_using_ins_graph
                                └─ row_ins_step
                                     ├─ trx id를 node->trx_id_buf에 기록
                                     ├─ 첫 실행: lock_table(table, LOCK_IX, thr)
                                     └─ row_ins
                                          └─ 각 index entry 삽입
                                               └─ btr_cur_ins_lock_and_undo
                                                    └─ lock_rec_insert_check_and_lock
```

`LOCK_IX`는 다른 `IX`와 호환되므로 일반 loader 둘을 table 수준에서 직렬화하지 않는다. 실제 unique 후보, FK 참조 레코드, gap에 따라 더 세밀하게 기다린다. 새로 들어간 레코드에는 보통 explicit record lock object 대신 implicit X ownership가 생긴다.

### 3. unique/FK 충돌과 재시도

```text
secondary unique index insert
  └─ row_ins_scan_sec_index_for_duplicate
       ├─ ordinary duplicate check: 후보 record/gap에 LOCK_S
       ├─ REPLACE/UPDATE 허용: 후보에 LOCK_X
       ├─ conflict: DB_LOCK_WAIT
       └─ 확정 중복: DB_DUPLICATE_KEY

foreign-key insert check
  └─ row_ins_check_foreign_constraints
       └─ row_ins_check_foreign_constraint(check_ref=true)
            ├─ 다른 referenced table이면 LOCK_IS
            ├─ parent candidate/record/gap에 LOCK_S
            ├─ conflict: thread suspend
            └─ parent 없음: DB_NO_REFERENCED_ROW

row_insert_for_mysql_using_ins_graph
  └─ row_mysql_handle_errors
       ├─ DB_LOCK_WAIT: lock_wait_suspend_thread → true
       │    └─ caller가 goto run_again → row_ins_step 재실행
       ├─ timeout/duplicate/FK: savepoint/statement rollback 경로
       └─ deadlock/lock-table-full: whole transaction rollback
```

이 경로의 핵심은 “다른 트랜잭션 ID에 S-lock을 건다”가 아니다. **그 트랜잭션이 건드린 index record 또는 그 주변 gap에 S/X request를 건다.**

### 4. implicit record X-lock을 실제 대기로 바꾸는 경로

```text
requester wants S/X on an existing record
  └─ lock_{clust,sec}_rec_read_check_and_lock
       └─ lock_rec_convert_impl_to_expl(record)
            ├─ clustered record: row DB_TRX_ID 읽기
            ├─ trx_rw_is_active(trx_id)로 owner가 아직 active인지 확인
            ├─ secondary record: clustered history를 통해 owner 추론
            └─ active owner이면 그 owner 대신
                 explicit (LOCK_X | LOCK_REC_NOT_GAP) record lock 생성
       └─ requester의 lock_rec_lock(S/X, same record/gap)
            └─ incompatible owner가 있으면 wait queue
```

`trx_rw_is_active(trx_id)`는 active transaction registry 조회다. `trx_id`를 lock table의 독립 자원으로 만들어 X/S compatibility queue를 만드는 함수가 아니다. requester와 blocker가 만나는 주소는 record lock resource이다.

### 5. transaction 종료와 해제

```text
full commit
  └─ innobase_commit(..., will_commit=true)
       └─ trx commit-in-memory transition
            ├─ active_rw_trxs에서 trx id 제거
            ├─ implicit locks가 끝난 것으로 보이는 시점 확정
            └─ lock_trx_release_locks
                 ├─ implicit→explicit conversion reference 종료 대기
                 ├─ try_release_all_locks
                 └─ transaction lock heap 비우기

full rollback
  └─ innobase_rollback
       └─ trx_rollback_for_mysql
            └─ trx_rollback_finish
                 └─ trx_commit(trx)   (undo 완료 후 같은 in-memory 종료/lock release 전이 재사용)

SQL cleanup
  ├─ autocommit/outside multi-stmt trx: MDL_context::release_transactional_locks
  └─ explicit multi-stmt trx: statement MDL만 release, transaction MDL은 commit/rollback까지 유지
```

`LOCK_AUTO_INC`는 transaction owner의 lock list에 들어가지만 statement 끝에서 별도 해제된다. 이 예외 때문에 “모든 InnoDB lock이 무조건 commit까지 간다”고 단순화해서는 안 된다.

### 6. ALGORITHM=BULK 경로

```text
PT_load_table::make_cmd
  └─ is_bulk_load → MDL_EXCLUSIVE

Sql_cmd_load_table::execute_bulk
  ├─ LOCK TABLES 사용 중이면 거부
  ├─ open_tables → target MDL X 획득
  ├─ empty table: truncate/new space
  │   non-empty table: duplicate target table 경로
  ├─ bulk_driver_service
  │    └─ external bulk_load_driver service
  │         └─ handler bulk API
  │              ├─ ha_innobase::bulk_load_begin
  │              │    ├─ m_prebuilt->trx start/register
  │              │    └─ ddl_bulk::Loader(num_threads, keynr, same trx)
  │              ├─ ha_innobase::bulk_load_execute (non-main execution threads)
  │              │    └─ Loader::load(prebuilt, thread_idx, rows)
  │              │         └─ Thread_data::load
  │              │              └─ Btree_multi::Btree_load::insert
  │              └─ ha_innobase::bulk_load_end (main session thread)
  │                   └─ Loader::end → subtree finish/merge
  ├─ check constraints
  ├─ referenced parent table names lock
  ├─ ha_innobase::check_foreign_constraints
  │    └─ Parallel_reader(full scan, same m_prebuilt->trx)
  └─ scope cleanup guard
       ├─ success: trans_commit_stmt + trans_commit_implicit
       └─ failure: trans_rollback_stmt + trans_rollback_implicit
```

`ddl0bulk.cc`, `ddl0bulk.h`, `btr0mtib.cc`, `ha0check.cc`의 위 direct path에서 `row_ins_step`, `lock_table(LOCK_IX)`, `lock_rec_*` 호출은 발견되지 않았다. 이 부정 결론은 오직 추적한 InnoDB bulk direct-build 경로에만 적용한다. 다른 DDL, ordinary LOAD, 다른 storage engine으로 일반화하지 않는다.

## 조사한 파일·심볼·라인

아래 라인 범위는 증거로 사용한 핵심 구간이다. 큰 함수는 관련 없는 parsing/format conversion 코드까지 포함한 전체 본문도 읽었으며, 표에는 claim을 지지하는 최소 구간을 적었다.

| 파일 | 심볼 / 조사 범위 | SHA-256 |
|---|---|---|
| `sql/parse_tree_nodes.cc` | `PT_load_table::make_cmd` 4306-4367 | `09750765443bc97d89092573b2c386de52841a2dc878c42ce96e9f3a2763f2e2` |
| `sql/table.h` | `mdl_type_for_dml`, `Table_ref` MDL init 2885-2895, 3095-3123 | `61c64820068135e2f56bb03a1574711809be4435db30036784220f21ccedff3f` |
| `sql/mdl.h` | MDL SW/X semantics and duration 246-349; namespace list 402-424 | `c43186485e83c94018abc88b7490bff7281eaf0a94b5f523932fa6bdc7be43a2` |
| `sql/mdl.cc` | object compatibility matrix 2183-2242; `release_transactional_locks` 4496-4522 | `914aadcc4006be4d314db84063d8d458445bf005ae6e3e78982963b2f26ee4a3` |
| `sql/sql_base.cc` | `open_table_get_mdl_lock` 2638-2754; `open_and_lock_tables` 6888-6926; `lock_tables` 7293-7385 | `2a108465126fceb8e0b996179a912e58a7cb5cd4630f8f7b46366e4816d26e1a` |
| `sql/sql_parse.cc` | command cleanup / transactional MDL release 5008-5040 | `13a5847de12fe01127cf87bde0f7de01cf2784a9d1dc32338d3f96f8e5f6ece0` |
| `sql/sql_load.cc` | `execute_bulk` 654-1021; `bulk_driver_service` 1023-1148; `execute_inner` 1159-1668; `read_sep_field` 1899-2110; `execute` 3127-3234 | `e549856fb6198a89a618ebf6cf068e7509b69c0c7a79906dc899f7659c130b5e` |
| `sql/sql_insert.cc` | `write_record` 1801-1840 (full duplicate-handling function followed) | `963aab10d9d9acec07738ad196c1412b45ffc0be5f7dd55a5a37707325071334` |
| `sql/handler.cc` | `ha_check_foreign_constraints` 4863-4865; `handler::ha_write_row` 8205-8230 | `da2f367c8133bf8e8be1cb0ed6e68fb083785ce8abf32d544652b4960c38d7e2` |
| `sql/item_func.cc` | user-level lock cleanup 5638-5676; `Item_func_get_lock::val_int` 5802-5880 | `1df8dda8ef06b0df1e99b1061d3f522e29c2b024c9cb11f613f584c373164fe4` |
| `storage/innobase/handler/ha_innodb.cc` | `innobase_commit` 5997-6150; `innobase_rollback` 6155-6218; `innobase_lock_autoinc` 8951-9010; `write_row` 9281-9374; `external_lock` 18948-19035; `lock_count/store_lock` 19748-19815 | `42e7ad557071037a82440c01e34740615663963711dd5691c9226d69a6ec4ea8` |
| `storage/innobase/handler/handler0alter.cc` | bulk begin/execute/end 11346-11423, 11457-11619 | `214e7c5464e29954c91ea554efdf0a29194709445aed067412a9cb58b46039fe` |
| `storage/innobase/handler/ha0check.cc` | `ha_innobase::check_foreign_constraints` 88-115 | `7f3f5dea2846848c21bbe873fadddea996221c66837592e4ceab531ad343a44f` |
| `storage/innobase/row/row0mysql.cc` | error/wait policy 654-760; AUTO_INC request 1139-1202; ordinary insert graph 1498-1710 | `08db672d4177b27b5f95a3a4507a0965fe0e3e5991d099a76afa4d37e9489100` |
| `storage/innobase/row/row0ins.cc` | system trx field 138-191; record-lock adapter 1381-1399; FK 1416-1866; unique scan 1922-2088; insert loop/IX 3579-3738 | `4663213c4e443450323908184eae6477c63cf5e376cfa7385b3400fcc19c4f30` |
| `storage/innobase/btr/btr0cur.cc` | `btr_cur_ins_lock_and_undo` 2553-2620 | `107f89e02adef0e504c02298f9d4d7cdfc6f4306094fdc5725f1193624e8b2de` |
| `storage/innobase/btr/btr0mtib.cc` | `Btree_load::insert` 1739-1780; subtree overlap/merge duplicate paths 3290-3340 | `47aa4928c31dbec38356854fa3afeb1b7f08ba3ffac988bfad1f173c9b581bc9` |
| `storage/innobase/lock/lock0lock.cc` | `lock_table` 3519-3608; insert intention 5035-5134; implicit→explicit 5141-5236; record S/X request 5356-5450; AUTO_INC release 5743-5794; all-lock release 5800-5850 | `f980965075e998cb30a982223411f383c9052d092ad69ebfe5b5aeb5b3726550` |
| `storage/innobase/include/lock0types.h` | basic lock modes 53-64 | `3281fccc3744859eef09eb26d57de386e7a8275c62c5ad5d74005431b5dd08c1` |
| `storage/innobase/include/lock0priv.h` | table/record identity 53-97; `lock_t` owner 136-171; implicit-lock rules 408-445; compatibility 578-599; `RecID` 634-680 | `2c035baaf4a24ed0d3d2daa68cdcbf73a81b2c77d89965ecdf530c26b3326ea0` |
| `storage/innobase/include/lock0priv.ic` | clustered record `DB_TRX_ID` reader 52-59 | `a6d743a280290a6b6a6bc7d122853e6a8cd9614e97577408375648ef47c12463` |
| `storage/innobase/include/trx0sys.ic` | `trx_rw_is_active` active registry lookup 140-180 | `5915fb1c33296f4e1401673f1e835490ac303c6a49a365cf4cc6b05f91d69645` |
| `storage/innobase/include/ddl0bulk.h` | per-thread state and common trx 203-301, 340-415 | `1d0956ebb28cadcb3d8c32b58e87e7a4a4b919cf7247076ce58e30b59b474962` |
| `storage/innobase/ddl/ddl0bulk.cc` | thread init/shared trx id 155-193; loader begin/load 228-279; thread load/errors 494-565; finish/merge 725-778 | `095dda861765d3c123d315cc607440f0ad514668e3aa7237abf8c85ccf63ae84` |
| `storage/innobase/trx/trx0trx.cc` | active registry removal, implicit/explicit lock release 1888-1982 | `3128c6a43a6ed4e6465f4b28cc6eff5b3a6ad6e6d4a3e6f03b7788ece7d9cf65` |
| `storage/innobase/trx/trx0roll.cc` | `trx_rollback_finish` 1107-1115 | `76c46660c6ced1ac4b26a0b40469c45ab2108875ee6a844aaa8a2df741512d36` |
| `storage/perfschema/table_md_locks.cc` | `metadata_locks` columns 45-70 | `2f39aad09a694e3044c2d619e2c05b44d1c5e54f863fcf1fc25b189db9aa52bb` |
| `storage/perfschema/table_data_locks.cc` | `data_locks` columns 46-77 | `ad95ace900601fcccb17ab81bd634b8b3ee73035a1fda88e41e2f952f9e2c263` |
| `storage/perfschema/table_data_lock_waits.cc` | `data_lock_waits` requester/blocker columns 46-76 | `2840ddd03f3747d33401bb8e11bd584a9cc9a169381bc219aa9a66ca06326a32` |
| `storage/innobase/clone/clone0copy.cc` | `Clone_Snapshot::wait_trx_end` near miss 410-429 | `7ea1fdac0f3abf8e6f5346e3e05b6511d6bf96393a04e5ce4ab2c4b8564bd94a` |

## Claim candidates (JSONL schema)

다음은 parent researcher가 central ledger에 병합할 수 있는 MySQL source Claim 후보이다. `report_locations`는 제안 anchor이며 book 조립 시 바꿀 수 있다.

```jsonl
{"id":"MYSQL-C001","claim_ko":"MySQL parser는 일반 LOAD DATA 대상 테이블에 MDL_SHARED_WRITE를, ALGORITHM=BULK에는 MDL_EXCLUSIVE를 요청한다. 이 table MDL은 transaction duration이며 충돌 시 table-open 단계에서 기다리고, autocommit statement 끝 또는 explicit transaction의 commit/rollback에서 해제된다.","database":"mysql","revision":"06a5c1c99c377fc41b2eba1ea244e8b220bdc3c8","kind":"source","confidence":"SOURCE-CONFIRMED","source_refs":[{"path":"sql/parse_tree_nodes.cc","symbol":"PT_load_table::make_cmd","line_start":4306,"line_end":4367,"file_sha256":"09750765443bc97d89092573b2c386de52841a2dc878c42ce96e9f3a2763f2e2","evidence_state":"COMMIT"},{"path":"sql/table.h","symbol":"Table_ref","line_start":3095,"line_end":3108,"file_sha256":"61c64820068135e2f56bb03a1574711809be4435db30036784220f21ccedff3f","evidence_state":"COMMIT"},{"path":"sql/sql_base.cc","symbol":"open_table_get_mdl_lock","line_start":2638,"line_end":2754,"file_sha256":"2a108465126fceb8e0b996179a912e58a7cb5cd4630f8f7b46366e4816d26e1a","evidence_state":"COMMIT"},{"path":"sql/mdl.cc","symbol":"m_object_lock_strategy","line_start":2183,"line_end":2242,"file_sha256":"914aadcc4006be4d314db84063d8d458445bf005ae6e3e78982963b2f26ee4a3","evidence_state":"COMMIT"},{"path":"sql/sql_parse.cc","symbol":"release_transactional_locks","line_start":5008,"line_end":5040,"file_sha256":"13a5847de12fe01127cf87bde0f7de01cf2784a9d1dc32338d3f96f8e5f6ece0","evidence_state":"COMMIT"}],"runtime_run_ids":[],"limitations_ko":"LOW_PRIORITY는 MDL_SHARED_WRITE_LOW_PRIO 변형이다. 다른 storage engine의 data-lock 동작까지 뜻하지 않는다.","report_locations":["chapters/09-mysql-analysis.html#claim-MYSQL-C001"]}
{"id":"MYSQL-C002","claim_ko":"일반 LOAD DATA의 각 행은 write_record에서 InnoDB row insert graph로 들어간다. insert graph는 트랜잭션 ID를 row system field에 기록하고 첫 삽입에서 테이블 LOCK_IX를 얻은 뒤 각 index entry를 삽입한다. IX끼리는 호환되므로 일반 loader 간 실제 충돌은 주로 record/gap lock에서 해결된다.","database":"mysql","revision":"06a5c1c99c377fc41b2eba1ea244e8b220bdc3c8","kind":"source","confidence":"SOURCE-CONFIRMED","source_refs":[{"path":"sql/sql_load.cc","symbol":"Sql_cmd_load_table::read_sep_field","line_start":1899,"line_end":2099,"file_sha256":"e549856fb6198a89a618ebf6cf068e7509b69c0c7a79906dc899f7659c130b5e","evidence_state":"COMMIT"},{"path":"sql/sql_insert.cc","symbol":"write_record","line_start":1801,"line_end":1823,"file_sha256":"963aab10d9d9acec07738ad196c1412b45ffc0be5f7dd55a5a37707325071334","evidence_state":"COMMIT"},{"path":"storage/innobase/handler/ha_innodb.cc","symbol":"ha_innobase::write_row","line_start":9281,"line_end":9374,"file_sha256":"42e7ad557071037a82440c01e34740615663963711dd5691c9226d69a6ec4ea8","evidence_state":"COMMIT"},{"path":"storage/innobase/row/row0mysql.cc","symbol":"row_insert_for_mysql_using_ins_graph","line_start":1498,"line_end":1600,"file_sha256":"08db672d4177b27b5f95a3a4507a0965fe0e3e5991d099a76afa4d37e9489100","evidence_state":"COMMIT"},{"path":"storage/innobase/row/row0ins.cc","symbol":"row_ins_step","line_start":3647,"line_end":3733,"file_sha256":"4663213c4e443450323908184eae6477c63cf5e376cfa7385b3400fcc19c4f30","evidence_state":"COMMIT"},{"path":"storage/innobase/include/lock0priv.h","symbol":"lock_compatibility_matrix","line_start":578,"line_end":599,"file_sha256":"2c035baaf4a24ed0d3d2daa68cdcbf73a81b2c77d89965ecdf530c26b3326ea0","evidence_state":"COMMIT"}],"runtime_run_ids":[],"limitations_ko":"문자 구분 LOAD 경로를 대표로 적었고 fixed/XML reader도 같은 write_record 계열로 이어짐을 확인했다. isolation level과 IGNORE/REPLACE에 따라 gap/mode 세부가 달라질 수 있다.","report_locations":["chapters/09-mysql-analysis.html#claim-MYSQL-C002"]}
{"id":"MYSQL-C003","claim_ko":"일반 InnoDB insert의 unique 검사는 중복 가능 index record와 gap에 보통 S-lock을, REPLACE/UPDATE 계열은 X-lock을 요청한다. FK 검사는 다른 참조 테이블에 IS를 얻고 parent record/gap에 S-lock을 요청한다. 충돌로 DB_LOCK_WAIT가 나면 thread를 재운 뒤 insert graph를 다시 실행하여 검사를 재평가한다.","database":"mysql","revision":"06a5c1c99c377fc41b2eba1ea244e8b220bdc3c8","kind":"source","confidence":"SOURCE-CONFIRMED","source_refs":[{"path":"storage/innobase/row/row0ins.cc","symbol":"row_ins_scan_sec_index_for_duplicate","line_start":1922,"line_end":2088,"file_sha256":"4663213c4e443450323908184eae6477c63cf5e376cfa7385b3400fcc19c4f30","evidence_state":"COMMIT"},{"path":"storage/innobase/row/row0ins.cc","symbol":"row_ins_check_foreign_constraint","line_start":1416,"line_end":1780,"file_sha256":"4663213c4e443450323908184eae6477c63cf5e376cfa7385b3400fcc19c4f30","evidence_state":"COMMIT"},{"path":"storage/innobase/row/row0mysql.cc","symbol":"row_mysql_handle_errors","line_start":654,"line_end":727,"file_sha256":"08db672d4177b27b5f95a3a4507a0965fe0e3e5991d099a76afa4d37e9489100","evidence_state":"COMMIT"},{"path":"storage/innobase/row/row0mysql.cc","symbol":"row_insert_for_mysql_using_ins_graph","line_start":1498,"line_end":1600,"file_sha256":"08db672d4177b27b5f95a3a4507a0965fe0e3e5991d099a76afa4d37e9489100","evidence_state":"COMMIT"}],"runtime_run_ids":[],"limitations_ko":"READ COMMITTED 이하 또는 gap-lock 생략 table에서는 gap mode가 달라진다. bulk direct-build 경로에는 이 claim을 적용하지 않는다.","report_locations":["chapters/09-mysql-analysis.html#claim-MYSQL-C003"]}
{"id":"MYSQL-C004","claim_ko":"InnoDB의 implicit X-lock은 새로 삽입·수정된 record에 대한 소유권이다. clustered record의 DB_TRX_ID로 active owner를 찾고 필요할 때 그 owner 명의의 explicit record X-lock으로 변환한 뒤 requester의 S/X record request와 충돌시킨다. 실제 lock resource identity는 page와 heap number의 record이며 transaction ID 자체가 아니다.","database":"mysql","revision":"06a5c1c99c377fc41b2eba1ea244e8b220bdc3c8","kind":"source","confidence":"SOURCE-CONFIRMED","source_refs":[{"path":"storage/innobase/include/lock0priv.h","symbol":"lock_t","line_start":136,"line_end":171,"file_sha256":"2c035baaf4a24ed0d3d2daa68cdcbf73a81b2c77d89965ecdf530c26b3326ea0","evidence_state":"COMMIT"},{"path":"storage/innobase/include/lock0priv.h","symbol":"RecID","line_start":634,"line_end":680,"file_sha256":"2c035baaf4a24ed0d3d2daa68cdcbf73a81b2c77d89965ecdf530c26b3326ea0","evidence_state":"COMMIT"},{"path":"storage/innobase/include/lock0priv.ic","symbol":"lock_clust_rec_some_has_impl","line_start":52,"line_end":59,"file_sha256":"a6d743a280290a6b6a6bc7d122853e6a8cd9614e97577408375648ef47c12463","evidence_state":"COMMIT"},{"path":"storage/innobase/lock/lock0lock.cc","symbol":"lock_rec_convert_impl_to_expl","line_start":5197,"line_end":5236,"file_sha256":"f980965075e998cb30a982223411f383c9052d092ad69ebfe5b5aeb5b3726550","evidence_state":"COMMIT"},{"path":"storage/innobase/lock/lock0lock.cc","symbol":"lock_clust_rec_read_check_and_lock","line_start":5405,"line_end":5445,"file_sha256":"f980965075e998cb30a982223411f383c9052d092ad69ebfe5b5aeb5b3726550","evidence_state":"COMMIT"},{"path":"storage/innobase/include/trx0sys.ic","symbol":"trx_rw_is_active","line_start":140,"line_end":180,"file_sha256":"5915fb1c33296f4e1401673f1e835490ac303c6a49a365cf4cc6b05f91d69645","evidence_state":"COMMIT"}],"runtime_run_ids":[],"limitations_ko":"transaction-ID keyed self-lock 부재는 아래 bounded negative search에 한정한다. secondary index의 implicit owner 판정은 clustered record version까지 따라갈 수 있다.","report_locations":["chapters/09-mysql-analysis.html#claim-MYSQL-C004"]}
{"id":"MYSQL-C005","claim_ko":"InnoDB lock object의 owner는 trx_t이다. full commit은 transaction을 active registry에서 제거하고 implicit ownership 종료점을 만든 뒤 explicit locks를 모두 해제한다. full rollback도 undo를 마친 뒤 같은 transaction 종료 전이를 재사용한다. explicit multi-statement transaction에서는 일반 statement 끝만으로 IX/X lock 전체를 풀지 않는다.","database":"mysql","revision":"06a5c1c99c377fc41b2eba1ea244e8b220bdc3c8","kind":"source","confidence":"SOURCE-CONFIRMED","source_refs":[{"path":"storage/innobase/include/lock0priv.h","symbol":"lock_t","line_start":136,"line_end":171,"file_sha256":"2c035baaf4a24ed0d3d2daa68cdcbf73a81b2c77d89965ecdf530c26b3326ea0","evidence_state":"COMMIT"},{"path":"storage/innobase/trx/trx0trx.cc","symbol":"lock_trx_release_locks","line_start":1888,"line_end":1982,"file_sha256":"3128c6a43a6ed4e6465f4b28cc6eff5b3a6ad6e6d4a3e6f03b7788ece7d9cf65","evidence_state":"COMMIT"},{"path":"storage/innobase/lock/lock0lock.cc","symbol":"lock_trx_release_locks","line_start":5800,"line_end":5850,"file_sha256":"f980965075e998cb30a982223411f383c9052d092ad69ebfe5b5aeb5b3726550","evidence_state":"COMMIT"},{"path":"storage/innobase/handler/ha_innodb.cc","symbol":"innobase_commit","line_start":5997,"line_end":6140,"file_sha256":"42e7ad557071037a82440c01e34740615663963711dd5691c9226d69a6ec4ea8","evidence_state":"COMMIT"},{"path":"storage/innobase/handler/ha_innodb.cc","symbol":"innobase_rollback","line_start":6155,"line_end":6218,"file_sha256":"42e7ad557071037a82440c01e34740615663963711dd5691c9226d69a6ec4ea8","evidence_state":"COMMIT"},{"path":"storage/innobase/trx/trx0roll.cc","symbol":"trx_rollback_finish","line_start":1107,"line_end":1115,"file_sha256":"76c46660c6ced1ac4b26a0b40469c45ab2108875ee6a844aaa8a2df741512d36","evidence_state":"COMMIT"}],"runtime_run_ids":[],"limitations_ko":"AUTO_INC는 statement 끝에 따로 풀리고, isolation-level 최적화에 따른 일부 read/gap lock 조기 해제는 이 요약의 IX/X ownership 중심 범위 밖이다.","report_locations":["chapters/09-mysql-analysis.html#claim-MYSQL-C005"]}
{"id":"MYSQL-C006","claim_ko":"ALGORITHM=BULK는 target table에 MDL_EXCLUSIVE를 잡고, handler의 하나의 prebuilt trx_t를 여러 execution thread가 공유하여 thread별 B-tree subtree를 직접 만든 뒤 합친다. 각 thread가 별도 transaction을 소유하는 구조가 아니며, 성공은 statement와 implicit transaction을 commit하고 실패는 둘 다 rollback한다.","database":"mysql","revision":"06a5c1c99c377fc41b2eba1ea244e8b220bdc3c8","kind":"source","confidence":"SOURCE-CONFIRMED","source_refs":[{"path":"sql/parse_tree_nodes.cc","symbol":"PT_load_table::make_cmd","line_start":4306,"line_end":4367,"file_sha256":"09750765443bc97d89092573b2c386de52841a2dc878c42ce96e9f3a2763f2e2","evidence_state":"COMMIT"},{"path":"sql/sql_load.cc","symbol":"Sql_cmd_load_table::execute_bulk","line_start":654,"line_end":1021,"file_sha256":"e549856fb6198a89a618ebf6cf068e7509b69c0c7a79906dc899f7659c130b5e","evidence_state":"COMMIT"},{"path":"storage/innobase/handler/handler0alter.cc","symbol":"ha_innobase::bulk_load_begin","line_start":11346,"line_end":11400,"file_sha256":"214e7c5464e29954c91ea554efdf0a29194709445aed067412a9cb58b46039fe","evidence_state":"COMMIT"},{"path":"storage/innobase/handler/handler0alter.cc","symbol":"ha_innobase::bulk_load_execute","line_start":11402,"line_end":11423,"file_sha256":"214e7c5464e29954c91ea554efdf0a29194709445aed067412a9cb58b46039fe","evidence_state":"COMMIT"},{"path":"storage/innobase/include/ddl0bulk.h","symbol":"Loader","line_start":278,"line_end":301,"file_sha256":"1d0956ebb28cadcb3d8c32b58e87e7a4a4b919cf7247076ce58e30b59b474962","evidence_state":"COMMIT"},{"path":"storage/innobase/ddl/ddl0bulk.cc","symbol":"Loader::Thread_data::init","line_start":155,"line_end":193,"file_sha256":"095dda861765d3c123d315cc607440f0ad514668e3aa7237abf8c85ccf63ae84","evidence_state":"COMMIT"},{"path":"storage/innobase/ddl/ddl0bulk.cc","symbol":"Loader::begin","line_start":228,"line_end":279,"file_sha256":"095dda861765d3c123d315cc607440f0ad514668e3aa7237abf8c85ccf63ae84","evidence_state":"COMMIT"},{"path":"storage/innobase/ddl/ddl0bulk.cc","symbol":"Loader::end","line_start":725,"line_end":778,"file_sha256":"095dda861765d3c123d315cc607440f0ad514668e3aa7237abf8c85ccf63ae84","evidence_state":"COMMIT"}],"runtime_run_ids":[],"limitations_ko":"bulk_load_driver component의 구현은 이 source tree 밖이어서 parser thread scheduling 내부는 미확인이다. InnoDB handler contract와 Loader에는 같은 prebuilt trx가 전달됨을 확인했다. direct path의 일반 row-lock 호출 부재는 아래 negative-search 범위에 한정한다.","report_locations":["chapters/09-mysql-analysis.html#claim-MYSQL-C006"]}
{"id":"MYSQL-C007","claim_ko":"일반 LOAD가 AUTO_INCREMENT column을 처리할 때 InnoDB는 설정에 따라 table의 LOCK_AUTO_INC를 요청할 수 있다. 이 lock은 auto-inc counter를 직렬화하는 statement-duration lock이며 IX와는 호환되지만 다른 AUTO_INC/S/X와 충돌한다. table 데이터 전체에 대한 bulk-update 권한은 아니다.","database":"mysql","revision":"06a5c1c99c377fc41b2eba1ea244e8b220bdc3c8","kind":"source","confidence":"SOURCE-CONFIRMED","source_refs":[{"path":"storage/innobase/handler/ha_innodb.cc","symbol":"ha_innobase::innobase_lock_autoinc","line_start":8951,"line_end":9004,"file_sha256":"42e7ad557071037a82440c01e34740615663963711dd5691c9226d69a6ec4ea8","evidence_state":"COMMIT"},{"path":"storage/innobase/row/row0mysql.cc","symbol":"row_lock_table_autoinc_for_mysql","line_start":1139,"line_end":1202,"file_sha256":"08db672d4177b27b5f95a3a4507a0965fe0e3e5991d099a76afa4d37e9489100","evidence_state":"COMMIT"},{"path":"storage/innobase/include/lock0priv.h","symbol":"lock_compatibility_matrix","line_start":578,"line_end":599,"file_sha256":"2c035baaf4a24ed0d3d2daa68cdcbf73a81b2c77d89965ecdf530c26b3326ea0","evidence_state":"COMMIT"},{"path":"storage/innobase/lock/lock0lock.cc","symbol":"lock_unlock_table_autoinc","line_start":5743,"line_end":5794,"file_sha256":"f980965075e998cb30a982223411f383c9052d092ad69ebfe5b5aeb5b3726550","evidence_state":"COMMIT"}],"runtime_run_ids":[],"limitations_ko":"AUTO_INCREMENT column과 innodb_autoinc_lock_mode 설정에 의존한다. ALGORITHM=BULK는 종료 단계에서 auto-inc state를 갱신하는 별도 경로도 가진다.","report_locations":["chapters/09-mysql-analysis.html#claim-MYSQL-C007"]}
{"id":"MYSQL-C008","claim_ko":"MySQL은 metadata_locks에서 MDL의 object/type/duration/status/owner thread를, data_locks에서 InnoDB lock의 transaction/object/index/type/mode/status/data를, data_lock_waits에서 requester와 blocker의 lock·transaction·thread ID를 노출한다. ENGINE_TRANSACTION_ID는 owner 관측 열이지 transaction-ID가 lock resource라는 뜻은 아니다.","database":"mysql","revision":"06a5c1c99c377fc41b2eba1ea244e8b220bdc3c8","kind":"source","confidence":"SOURCE-CONFIRMED","source_refs":[{"path":"storage/perfschema/table_md_locks.cc","symbol":"table_metadata_locks::m_table_def","line_start":47,"line_end":70,"file_sha256":"2f39aad09a694e3044c2d619e2c05b44d1c5e54f863fcf1fc25b189db9aa52bb","evidence_state":"COMMIT"},{"path":"storage/perfschema/table_data_locks.cc","symbol":"table_data_locks::m_table_def","line_start":48,"line_end":77,"file_sha256":"ad95ace900601fcccb17ab81bd634b8b3ee73035a1fda88e41e2f952f9e2c263","evidence_state":"COMMIT"},{"path":"storage/perfschema/table_data_lock_waits.cc","symbol":"table_data_lock_waits::m_table_def","line_start":48,"line_end":76,"file_sha256":"2840ddd03f3747d33401bb8e11bd584a9cc9a169381bc219aa9a66ca06326a32","evidence_state":"COMMIT"},{"path":"storage/innobase/lock/lock0lock.cc","symbol":"lock_print_info_summary","line_start":4359,"line_end":4381,"file_sha256":"f980965075e998cb30a982223411f383c9052d092ad69ebfe5b5aeb5b3726550","evidence_state":"COMMIT"}],"runtime_run_ids":[],"limitations_ko":"실제 출력은 instrumentation 활성화, 권한, 시점에 영향을 받는다. bulk direct-build 동안 일반 record lock이 없으면 data_locks에 대응 record lock도 나타나지 않을 수 있으나 런타임으로 검증하지 않았다.","report_locations":["chapters/09-mysql-analysis.html#claim-MYSQL-C008"]}
{"id":"MYSQL-C009","claim_ko":"일반 InnoDB insert에서 lock wait는 thread suspend 후 재시도되며, lock wait timeout·duplicate·FK 계열 오류는 기본적으로 현재 insertion/savepoint와 SQL statement rollback 경로로 보내진다. deadlock과 lock table full은 whole transaction rollback을 요청한다.","database":"mysql","revision":"06a5c1c99c377fc41b2eba1ea244e8b220bdc3c8","kind":"source","confidence":"SOURCE-CONFIRMED","source_refs":[{"path":"storage/innobase/row/row0mysql.cc","symbol":"row_mysql_handle_errors","line_start":654,"line_end":727,"file_sha256":"08db672d4177b27b5f95a3a4507a0965fe0e3e5991d099a76afa4d37e9489100","evidence_state":"COMMIT"},{"path":"storage/innobase/row/row0mysql.cc","symbol":"row_insert_for_mysql_using_ins_graph","line_start":1498,"line_end":1600,"file_sha256":"08db672d4177b27b5f95a3a4507a0965fe0e3e5991d099a76afa4d37e9489100","evidence_state":"COMMIT"},{"path":"sql/sql_parse.cc","symbol":"transaction_rollback_request","line_start":5008,"line_end":5016,"file_sha256":"13a5847de12fe01127cf87bde0f7de01cf2784a9d1dc32338d3f96f8e5f6ece0","evidence_state":"COMMIT"}],"runtime_run_ids":[],"limitations_ko":"innodb_rollback_on_timeout 설정이 켜지면 timeout도 whole transaction rollback이 될 수 있다. SQL layer의 최종 user error 변환 전체 표는 생략했다.","report_locations":["chapters/09-mysql-analysis.html#claim-MYSQL-C009"]}
```

## CUBRID와의 semantic mapping

이 표의 분류는 이름이 아니라 책임, 자원 키, owner, lifetime, compatibility, waiter 동작을 기준으로 한다. comparison claim을 정식 ledger에 넣을 때에는 PostgreSQL evidence도 함께 붙여야 한다.

| CUBRID 개념 | 가장 가까운 MySQL/InnoDB 메커니즘 | 분류 | 같은 점 | 결정적 semantic gap |
|---|---|---|---|---|
| class의 `BU_LOCK` mode와 BU↔BU compatibility | 없음 | **no equivalent** | 해당 없음 | InnoDB lock mode 집합은 IS/IX/S/X/AUTO_INC이고 BU가 없다. CUBRID BU는 BU끼리 호환하면서 IS/S/IX/SIX/X와 충돌한다. MySQL의 어떤 단일 mode도 이 행렬과 맞지 않는다. |
| BU가 loader의 넓은 table/class 보호 책임을 맡음 | ordinary LOAD의 `MDL_SW + IX + record/gap locks` 조합 | **partial analogy** | table-level 의도와 하위 record 변경을 계층적으로 나눈다. | MySQL은 하나의 BU 권한으로 worker object-lock을 생략하지 않는다. MDL SW와 IX는 동시 DML을 허용하고 실제 충돌은 record-level에서 해결한다. |
| BU를 session transaction이 소유하고 worker transaction이 그 보호를 빌려 object locks를 생략 | ordinary LOAD / bulk algorithm 모두 정확한 대응 없음 | **no equivalent** | bulk algorithm에도 여러 execution thread가 있다. | MySQL bulk execution thread들은 별도 worker transaction이 아니라 같은 `trx_t`를 공유한다. “다른 transaction의 table lock을 신뢰하여 내 object lock을 생략”하는 owner split이 없다. |
| direct bulk build를 위해 table을 넓게 격리 | `ALGORITHM=BULK`의 `MDL_EXCLUSIVE` | **partial analogy** | loader가 작업하는 동안 table 전체에 강한 배타 보호를 둔다. | MDL X는 SQL metadata/object layer lock이고 모든 object MDL과 비호환이다. BU↔BU처럼 동시 loader를 허용하지 않으며, CUBRID BU compatibility와 다르다. |
| LOAD에 민감한 table lock | `LOCK_AUTO_INC` | **partial analogy**지만 교육상 **false friend** | LOAD/INSERT SELECT 계열에서 table 단위 대기를 만들 수 있다. | auto-inc counter만 직렬화하고 statement 끝에 풀린다. row/object 보호나 worker lock-bypass를 제공하지 않는다. BU 대체물이 아니다. |
| inserter가 자기 MVCCID resource에 X, waiter가 같은 MVCCID에 S | implicit record X ownership + requester의 record S/X | **partial analogy** | waiter가 active inserter의 종료/변경 확정을 기다린 뒤 unique/FK 판단을 다시 한다. | InnoDB 자원 키는 transaction ID가 아니라 record `(page, heap_no)`이다. `DB_TRX_ID`는 owner 발견용 표식이고 implicit X를 explicit record X로 바꾼다. CUBRID처럼 하나의 MVCCID self-lock이 여러 appended row를 대표하지 않는다. |
| transaction-ID keyed self-lock resource 자체 | 없음(조사 범위 내) | **no equivalent** | 해당 없음 | MDL namespace에도 transaction-ID resource가 없고 InnoDB `lock_t` union은 table/record resource이다. active-trx map 조회, clone polling, user named lock은 각각 registry/poll/advisory lock일 뿐 DML self-lock이 아니다. |

### 비교에 사용한 CUBRID 근거

- `src/transaction/lock_table.c:30-125`, `lock_Comp`, SHA-256 `833bb45be1b2f278c456f2eb06bbb1e9c7f9ddab5ecef5cb4a3cbe661a8e9953`, `WORKTREE`: BU↔BU는 호환, BU는 IS/S/IX/SIX/X/SCH-M과 비호환.
- `src/transaction/lock_manager.c:3539-3543`, `lock_internal_perform_lock_object`, SHA-256 `b8d47adef644a8f1642dabf6736d80b7b47df66b467e98324d4c1deee1cab8d3`, `WORKTREE`: load worker object-lock 금지와 MVCCID self-lock 예외.
- `src/transaction/lock_manager.c:6281-6313`, `lock_object`, same SHA/state: worker가 session transaction의 BU 존재를 검사하고 instance/class request를 즉시 grant 처리.
- `src/transaction/lock_manager.c:6438-6491`, `lock_transaction_mvccid`, same SHA/state: MVCCID resource에 inserter X / waiter S 요청.
- `src/transaction/lock_manager.c:6495-6553`, `lock_unlock_transaction_mvccid`, same SHA/state: explicit/full release semantics.

이 CUBRID 파일들은 frozen provenance에서 dirty worktree이므로 comparison ledger에 편입할 때 반드시 `WORKTREE`로 유지해야 한다.

## Bounded negative searches

### 1. transaction-ID keyed DML lock이 있는가

검색한 범위:

- `storage/innobase/**`
- `sql/**`
- InnoDB table/record lock types와 resource structures
- MDL namespaces와 user-level named locks
- active transaction registry와 clone transaction-end waiting
- `performance_schema` lock tables

사용한 alternate terminology / patterns:

```text
trx_id_t ... lock|wait
lock|wait ... trx_id_t
trx->id ... lock|wait
lock|wait ... trx->id
transaction id, active_rw_trxs, implicit lock, explicit lock
MDL namespace, USER_LEVEL_LOCK, GET_LOCK
ENGINE_TRANSACTION_ID
wait_trx_end
```

검색 결과와 배제 이유:

- `lock_clust_rec_some_has_impl` / `lock_get_trx_id`: record owner 식별 및 diagnostics accessor이다.
- `trx_rw_is_active`: `active_rw_trxs` map membership lookup이다. compatibility queue를 만들지 않는다.
- `Clone_Snapshot::wait_trx_end`: prepared transaction이 끝날 때까지 registry를 polling하는 clone 전용 경로이다. DML unique/FK lock resource가 아니다.
- `GET_LOCK(name, timeout)`: arbitrary string의 `USER_LEVEL_LOCK` MDL X이며 `MDL_EXPLICIT`, connection-owned, explicit release/connection cleanup 대상이다. transaction MVCC ID로 자동 생성되는 self-lock이 아니다.
- `ENGINE_TRANSACTION_ID`: performance schema에서 lock owner를 연결하는 관측 column이다.
- MDL namespace enum에는 `GLOBAL/BACKUP_LOCK/TABLESPACE/SCHEMA/TABLE/.../USER_LEVEL_LOCK/.../FOREIGN_KEY/CHECK_CONSTRAINT`가 있고 transaction-ID namespace는 없다.
- `lock_t` resource union은 `lock_table_t` 또는 `lock_rec_t`; record identity는 `page_id`와 heap bitmap이다.

따라서 부정 결론은 다음처럼 제한한다.

> pinned MySQL revision의 SQL MDL과 InnoDB ordinary insert/unique/FK/bulk-load 호출 경로에서는, CUBRID처럼 DML이 자신의 numeric transaction ID를 독립 lock resource key로 만들고 X/S mode로 rendezvous하는 메커니즘을 찾지 못했다.

이것은 MySQL 전체 plugin 생태계나 임의의 user-level lock 사용 가능성에 대한 부정이 아니다.

### 2. ALGORITHM=BULK direct path에 ordinary row locking이 있는가

정확한 검색 파일:

```text
storage/innobase/ddl/ddl0bulk.cc
storage/innobase/include/ddl0bulk.h
storage/innobase/btr/btr0mtib.cc
storage/innobase/handler/ha0check.cc
```

검색어:

```text
lock_table(
lock_rec
LOCK_IX
row_ins
```

`ddl0bulk.cc`의 “miniature of `row_ins_index_entry_set_vals()`”라는 comment 외에 ordinary insert/record-lock 호출은 없었다. 대신 `Btree_multi::Btree_load` subtree 생성/merge와 post-load FK full scan이 보인다. 이 부정 결과는 위 네 파일과 traced handler calls에만 한정한다.

## Contradictions and false friends

1. **`ha_start_bulk_insert()` ≠ `ALGORITHM=BULK`.** 전자는 ordinary row insertion 전에 호출되는 handler optimization hint이고, 후자는 별도 SQL/handler/direct-B-tree workflow다.
2. **parser의 `TL_WRITE_CONCURRENT_INSERT` ≠ InnoDB THR_LOCK table lock.** InnoDB `lock_count()`가 0이어서 THR_LOCK을 사용하지 않는다. MDL과 InnoDB lock subsystem을 보아야 한다.
3. **`DB_TRX_ID` ≠ transaction lock resource.** row header 안의 owner marker이다. lock queue의 자원 주소는 record이다.
4. **`MDL_EXCLUSIVE` ≠ BU_LOCK.** 둘 다 table을 넓게 보호하지만 compatibility, layer, 동시 loader 허용, worker-bypass semantics가 다르다.
5. **`LOCK_AUTO_INC` ≠ BU_LOCK.** auto-increment counter만 보호하는 statement lock이다.
6. **`GET_LOCK()` ≠ transaction self-lock.** 이름을 사용자가 정하고 connection이 명시적으로 관리하는 advisory lock이다.
7. **bulk의 여러 thread ≠ 여러 transaction.** thread마다 subtree context는 있지만 handler/prebuilt의 같은 `trx_t`를 쓴다.
8. **`ENGINE_TRANSACTION_ID` 관측 열 ≠ 자원 key.** owner를 보여 주는 열과 lock identity를 혼동하면 안 된다.

## Unknowns and limitations

1. `bulk_load_driver` service의 concrete component 구현은 pinned `mysql-server` source tree에서 찾지 못했다. 파일 parsing, batch dispatch, execution-thread scheduling 내부는 unknown이다. 그러나 handler API와 InnoDB Loader가 동일 prebuilt transaction을 받는 것은 source-confirmed이다.
2. MySQL runtime을 실행하지 않았다. 실제 `performance_schema` snapshot, wait timing, error text, `SHOW ENGINE INNODB STATUS` 출력은 source-only이며 runtime-observed가 아니다.
3. `ALGORITHM=BULK`의 crash-recovery/DDL-log 전체 상태 전이와 WAL byte ordering은 이 locking comparator의 범위 밖이다. `execute_bulk` comment의 atomicity 의도만 읽었으며 별도 durability claim을 만들지 않았다.
4. 일반 LOAD에서 isolation level, `innodb_autoinc_lock_mode`, `IGNORE`, `REPLACE`, generated columns, partition, SQL-layer FK mode에 따라 세부 잠금이 달라질 수 있다. central claims에는 이 조건을 숨기지 말아야 한다.
5. direct bulk path에 ordinary row-lock 호출이 없다는 결론은 조사한 InnoDB implementation files와 call path에만 적용한다. 다른 storage engine 및 unrelated DDL code는 포함하지 않는다.
6. “큰 variable value”의 overflow-page/LOB storage 자체는 이 role의 locking comparison과 직접 연결된 호출에서 추적하지 않았다. MySQL의 overflow storage를 CUBRID OOS와 같다고 주장하지 않는다.
7. `performance_schema` 노출 여부는 instrumentation/privilege/configuration에 따라 달라질 수 있다.
8. MySQL revision은 `trunk`의 pinned commit이다. 다른 released version에서 `ALGORITHM=BULK` 가용성과 구현이 같다는 호환성 주장을 하지 않는다.

## Suggested book explanation for a sophomore reader

- MDL은 “도서관 책의 제목표와 서가 위치를 작업 중에 바꾸지 마세요”라는 표지판이다.
- InnoDB `IX`는 “이 건물의 몇 방에서 공사할 예정입니다”라는 입구 표지판이다. 다른 공사팀도 IX 표지판을 붙일 수 있다.
- record S/X lock은 실제로 같은 방·같은 물건을 두 사람이 동시에 바꾸지 못하게 하는 잠금이다.
- `DB_TRX_ID`는 자물쇠 구멍이 아니라 “이 물건을 마지막으로 작업 중인 팀 번호” 스티커다. 기다리는 사람은 그 번호 자체에 자물쇠를 거는 것이 아니라, 그 물건의 record lock에 줄을 선다.
- CUBRID MVCCID self-lock은 반대로 “팀 번호 자체가 하나의 대기 장소”가 된다. 이 한 문장이 partial analogy와 semantic gap을 가장 쉽게 설명한다.
- CUBRID BU는 여러 load worker가 의지하는 넓은 보호권이다. MySQL ordinary LOAD에는 그런 단일 권한이 없고 MDL+IX+record locks로 책임이 나뉜다. MySQL bulk algorithm은 MDL X를 잡지만, worker들이 별도 transaction인 것이 아니라 같은 transaction의 여러 손처럼 움직인다.
