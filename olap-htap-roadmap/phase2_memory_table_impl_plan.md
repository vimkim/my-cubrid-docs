# Phase 2: CUBRID In-Memory Table — 상세 구현 계획서

> **대상**: 본 작업을 수행할 엔지니어 / 코드 리뷰어
> **작성일**: 2026-05-08 (v3)
> **작성자**: 김대현
> **연계 문서**: `htap_olap_roadmap.md` (전략 로드맵)
> **상태**: 초안, 사전 리뷰 진행 중
> **줄번호 기준**: 본 문서의 모든 `file:line` 인용은 v3 작성 시점(2026-05-08) `develop` 브랜치 기준. PR 작업 착수 시 재확인 필요.

---

## TL;DR

CUBRID에 `CREATE MEMORY TABLE` 구문을 추가해 WAL/recovery/MVCC 없이 메모리에만 존재하는 테이블을 지원합니다. `SCAN_TYPE` 분기 1개, `SM_CLASS_FLAG` 비트 1개, 신규 모듈(`src/storage/memory_table.{hpp,cpp}`) 1개를 중심으로 약 2,500~4,600 LOC. 1명 14~28주(MVP, conservative).

**MVP 동시성 모델은 의도적으로 단순화**: registry는 `std::shared_mutex + std::unordered_map<OID, std::unique_ptr<memory_table>>`로 시작하고 lockfree 인프라(lf_entry_descriptor + tran::system + tran::index)는 후속 도입. 테이블 내부도 `std::shared_mutex` 단일 락(`#1`).

**DDL+DML 결정안 변경 (v2 → v3)**: 트랜잭션 내 `CREATE MEMORY TABLE`은 **즉시 global registry에 등록**하고, **ROLLBACK 시에는 deferred drop을 호출하지 않는다**(`#3`, `#13`). 즉 ROLLBACK 후에도 테이블과 row가 그대로 남는다. 이중 lookup 비용이 사라지고 DROP+ROLLBACK 데이터 보존 비대칭이 자동으로 해결된다. 사용자 가시성: 다른 세션이 미커밋 테이블을 즉시 본다(이미 read-uncommitted-equivalent 모델과 일관).

통합 지점은 `csql_grammar.y::create_stmt` (line 2540~), `class_object.h::SM_CLASS_FLAG` (line 305~312), `transform_cl.c::class_to_disk` (line 3782의 `or_put_int (buf, class_->flags)` 직렬화), `do_create_entity` (`src/query/execute_schema.c:9025`), `locator_attribute_info_force` (`src/transaction/locator_sr.c:7461`), `scan_start_scan/scan_next_scan_local/scan_end_scan` (`src/query/scan_manager.c`), `boot_restart_server/xboot_shutdown_server` (`src/transaction/boot_sr.c`), 트랜잭션 commit/rollback 콜백은 `log_commit_local`/`log_abort_local` (`src/transaction/log_manager.c:5156, 5274`) 인근입니다.

본 문서는 통합 지점 매핑, 데이터 구조, 모듈별 구현 상세, 트랜잭션 의미론, 동시성 모델, 테스트 전략, 주차별 산출물을 다룹니다.

---

## 1. 개요 및 범위

### 1.1 목표

CUBRID 사용자가 다음 SQL로 사용할 수 있는 in-memory 테이블 기능 제공:

```sql
CREATE MEMORY TABLE cache_lookup (
  key_id INT PRIMARY KEY,
  payload VARCHAR(256)
);

INSERT INTO cache_lookup VALUES (1, 'a'), (2, 'b');
SELECT payload FROM cache_lookup WHERE key_id = 1;
DROP TABLE cache_lookup;
```

### 1.2 확정 스펙 (전략 로드맵에서 확정)

| 항목 | 결정 |
|---|---|
| 가시성 | Global (모든 세션 공유) |
| 영속성 | 카탈로그 영속 / 데이터 서버 재시작 시 wipe |
| DML | INSERT/UPDATE/DELETE 전체 |
| DML 트랜잭션 | row-level autocommit (각 row가 적용 즉시 커밋된 것으로 간주, statement 중간 실패 시 이미 적용된 row는 보존) |
| 인덱스 | PRIMARY KEY hash only |
| 동시성 (MVP) | RW lock per table (`std::shared_mutex`) + registry RW lock |
| MVCC | 없음 (read-uncommitted-equivalent 격리) |
| OOM | `ER_MEMORY_TABLE_FULL` 에러 |
| 빌드 모드 | SERVER_MODE 전용 (1차) — SA_MODE는 DDL 실행 시 `ER_MEMORY_TABLE_NOT_SUPPORTED_IN_SA_MODE` 반환 |
| HA / Backup / Replication | 카탈로그 flag로 자동 제외 |
| DDL | `CREATE MEMORY TABLE foo (...);` |

### 1.3 In-Scope (MVP)

- DDL: `CREATE MEMORY TABLE`, `DROP TABLE` (memory table 인지)
- DML: INSERT/UPDATE/DELETE/SELECT
- PK 단일/복합 컬럼 hash index
- Full table scan
- INFORMATION_SCHEMA에 memory table 표식
- 메모리 한도 시스템 파라미터
- HA/replication에서 자동 skip

### 1.4 Out-of-Scope (Phase 2 외)

- Secondary index (Phase 2.1 또는 Phase 4 검토)
- Range scan optimization (full scan으로 충분)
- 컬럼너 레이아웃 (Phase 4 DuckDB 임베드 시 검토)
- ALTER TABLE for memory table
- 통계 정보 자동 수집 (수동 갱신만)
- SA_MODE 지원 (1차 SERVER_MODE 전용)
- HA replication 통합
- Backup 통합
- lockfree registry 마이그레이션 (Phase 2.1)

---

## 2. CUBRID 코드베이스 통합 지점 매핑

### 2.1 Parser (`src/parser/`)

| 작업 | 위치 | 비고 |
|---|---|---|
| `MEMORY` 토큰 추가 | `csql_lexer.l`, `csql_grammar.y` `%token` 섹션 (`TEMPORARY`는 `csql_grammar.y:1403`에 정의) | `TEMPORARY` 토큰은 의미가 다르므로 손대지 않음 |
| `CREATE MEMORY TABLE` 룰 | `csql_grammar.y:2540` `create_stmt` 룰 | 기존 `create_stmt`에 `MEMORY` 키워드 분기를 추가 |
| `PT_NODE` 플래그 | `parse_tree.h:1951` `struct pt_create_entity_info` | `unsigned is_memory_table:1;` 비트필드 추가 |
| Semantic check | `semantic_check.c` | memory table 제약 검사: NOT NULL on PK, no FK, no AUTO_INCREMENT 등 |
| Name resolution | `name_resolution.c` | 변경 거의 없음 (테이블 이름은 일반 테이블과 동일 네임스페이스) |

#### 2.1.1 `MEMORY` 키워드 충돌 처리

`MEMORY`는 일반 영문 단어이므로 신규 reserved 키워드로 등록하면 기존 사용자 스크립트의 컬럼/테이블/별칭 이름을 깨뜨릴 위험이 있다. 두 가지 안 중 택일:

- **(권장) Non-reserved keyword 등록**: bison 룰에서 컨텍스트 의존 토큰으로 사용. 식별자 위치에서는 `IDENTIFIER`로 환원. 기존 컬럼명 `memory`를 쓰는 스크립트 보존.
- **(차선) DDL 우회 구문**: `CREATE TABLE foo (...) WITH (storage='memory')` 형식. grammar 변경 폭 최소.

본 문서는 (권장)을 1차 채택. **회귀 보존 케이스 테스트 필수**:
- `CREATE TABLE t (memory INT)` 가 기존처럼 통과
- `SELECT memory FROM t` 가 컬럼 참조로 해석
- `CREATE MEMORY TABLE t (...)` 만 신규 분기 진입

### 2.2 Catalog (`src/object/`)

| 작업 | 위치 | 비고 |
|---|---|---|
| 플래그 추가 | `class_object.h:305-312` `SM_CLASS_FLAG` enum | `SM_CLASSFLAG_MEMORY_TABLE = 32` (현재 16 = `SM_CLASSFLAG_SUPPLEMENTAL_LOG`까지 사용) |
| 비트 폭 점검 | `class_object.h:295-299` `SM_CLASS_TYPE`은 별개 enum이며, `SM_CLASS_FLAG`는 클래스의 `flags` 필드(int)에 저장됨 | `or_put_int (buf, class_->flags)` (`transform_cl.c:3710`)로 32-bit int 직렬화 — 신규 비트는 자동 호환 |
| 직렬화 | `src/object/transform_cl.c::class_to_disk()` (line 3782) | `or_put_int (buf, class_->flags)` 한 줄로 round-trip 보장. 별도 변경 불필요하나 unit test로 verify |
| Class 생성 분기 | `src/query/execute_schema.c::do_create_entity()` (line 9025) → `sm_finish_class()` (`schema_manager.c:13431`) | DDL 실행 진입점에서 `is_memory_table` PT 플래그를 보고 `template_->flags |= SM_CLASSFLAG_MEMORY_TABLE` 식으로 직접 set. registry 등록은 §4.4.3 결정안 (b)에 따라 DDL 실행 후 즉시 수행 |
| 헬퍼 추가 | `class_object.h` | `sm_is_memory_table(class)` inline 헬퍼 |

### 2.3 Memory Store (신규 모듈)

| 작업 | 위치 |
|---|---|
| 헤더 | `src/storage/memory_table.hpp` (신규) |
| 구현 | `src/storage/memory_table.cpp` (신규) |
| CMake | `src/storage/CMakeLists.txt` (해당 파일에 추가) |

### 2.4 DML Path (`src/transaction/`, `src/query/`)

| 작업 | 위치 |
|---|---|
| INSERT 분기 | `locator_attribute_info_force()` (`src/transaction/locator_sr.c:7461`) 진입 직후 |
| UPDATE/DELETE 분기 | 같은 함수 또는 `xlocator_force()` (`src/transaction/locator_sr.c:7129`) 진입 직후 |
| Bulk INSERT | `qexec_execute_insert()` (`src/query/query_executor.c`) — list로 모인 row를 일괄 memory_table_bulk_insert로 |

분기 cost 캐싱 (§4.4.1): `HEAP_SCANCACHE` 또는 `HEAP_CACHE_ATTRINFO`에 `is_memory_table:1` 비트를 보관해 매 row마다 카탈로그 lookup을 피한다.

### 2.5 Scan (`src/query/`)

| 작업 | 위치 |
|---|---|
| `SCAN_TYPE` enum 확장 | `scan_manager.h:77-94` (`S_HEAP_SCAN = 1` ~ `}` `SCAN_TYPE`) — 끝에 `S_MEMORY_TABLE_SCAN` 추가 |
| `SCAN_ID` 유니온 | `scan_manager.h:402-413` `struct scan_id_struct` 내 union — `MEMORY_TABLE_SCAN_ID mtsid` 멤버 추가 |
| init 분기 | `scan_start_scan()` (`scan_manager.c:4136`) — 하위 switch에 `case S_MEMORY_TABLE_SCAN` 추가 |
| next 분기 | `scan_next_scan_local()` (`scan_manager.c:5193`) — 동일 switch에 case 추가 |
| close | `scan_end_scan()` (`scan_manager.c:4749`) 인근 |

### 2.6 Optimizer

| 작업 | 위치 |
|---|---|
| Cost model 표식 | `query_planner.c` — memory table 비용을 매우 낮게(disk I/O 0) 책정 |
| Cardinality | 카탈로그가 아닌 registry의 `row_count.load()` 활용. 기타 통계(distinct, hist)는 미수집 → optimizer는 default selectivity로 fallback |

### 2.7 Lifecycle

| 작업 | 위치 |
|---|---|
| 서버 startup | `src/transaction/boot_sr.c::boot_restart_server()` (line 1969) — 카탈로그 스캔 후 memory table 카탈로그 entry 발견 시 빈 registry entry 생성 |
| 서버 shutdown | `src/transaction/boot_sr.c::xboot_shutdown_server()` (line 3044) — registry destroy |
| 트랜잭션 commit/rollback | `src/transaction/log_manager.c::log_commit_local()` (line 5156) / `log_abort_local()` (line 5274) 인근에서 registry 콜백 등록 위치를 확정 (Week 1 PoC). 하위 함수 후보로 `logtb_complete_mvcc` (line 5173, 5302, 5320), `log_complete` (line 5650), 그리고 sysop 경로의 `log_sysop_end_logical_undo` (line 3938) |
| HA failover | 자동 skip (memory table은 HA 비대상) |

### 2.8 Error Codes

신규 코드 6곳 동시 갱신 (CLAUDE.md 규칙):

| 파일 | 추가 항목 |
|---|---|
| `src/base/error_code.h` | `ER_MEMORY_TABLE_FULL`, `ER_MEMORY_TABLE_PK_DUPLICATE`, `ER_MEMORY_TABLE_NOT_FOUND`, `ER_MEMORY_TABLE_NOT_SUPPORTED_IN_SA_MODE`, `ER_MEMORY_TABLE_DROP_TIMEOUT` 등 — 현 마지막 코드는 `ER_AUTO_INCREMENT_SINGLE_COL_ONLY = -1370` (line 1758) |
| `src/compat/dbi_compat.h` | 위 동일 코드 (client-visible) |
| `msg/en_US.utf8/cubrid.msg` | 영문 메시지 |
| `msg/ko_KR.utf8/cubrid.msg` | 한글 메시지 |
| `src/base/error_code.h::ER_LAST_ERROR` (line 1760, 현재 `-1371`) | 신규 코드 수만큼 감소 (예: `-1379`) |
| `cubrid-cci/src/cci/base_error_code.h` | CCI 클라이언트 가시 (서브모듈 — `cubrid-cci/src/cci/`에 위치) |

> **CCI submodule PR 분리** (`#21`): `cubrid-cci`는 별도 git submodule이며 CCI 패키지 릴리스 주기가 다르다. 본 PR 시리즈에서 client-visible memory table 에러 코드를 노출해야 하는 시점에는 **CCI submodule용 PR을 별도 브랜치로 제출**한다. §8 일정에 별도 행으로 등재되어 있다 (Week 14의 `cubrid-cci PR`). 그 사이 서버 측은 client-side 에러 코드 매핑을 generic `CCI_ER_DBMS`로 fallback 시킨다.

### 2.9 System Parameters (`src/base/system_parameter.{h,c}`)

신규 파라미터 — `PRM_ID_*` enum은 현재 `PRM_ID_LOG_POSTPONE_CACHE_SIZE`가 마지막이며 `PRM_LAST_ID = PRM_ID_LOG_POSTPONE_CACHE_SIZE` (`system_parameter.h:529-532`). 신규 ID는 그 직전에 추가하고 `PRM_LAST_ID`를 갱신.

- `memory_table_total_size` (default `256M`, max `64G`) — `PRM_BIGINT` + `PRM_FOR_SERVER` (CUBRID 표준 메모리 sysparam 관례). **startup-only** (런타임 SET 시도 시 §4.10.2 참조).
- `memory_table_max_per_table` (default `64M`) — `PRM_BIGINT` + `PRM_FOR_SERVER` + `PRM_USER_CHANGE`. 런타임 변경 가능.
- `memory_table_chunk_size` (default `64K`, internal/advanced) — `PRM_BIGINT` + `PRM_FOR_SERVER`. **startup-only** (chunk size는 registry 초기화 시 1회 결정 후 고정 — §4.10.1).
- `memory_table_compact_threshold_pct` (default `0` = disabled, percent) — `PRM_INTEGER` + `PRM_FOR_SERVER` + `PRM_USER_CHANGE`.
- `memory_table_drop_timeout_msec` (default `0` = 무한 대기, `>0` = busy-wait timeout, default 단위 ms) — `PRM_INTEGER` + `PRM_FOR_SERVER` + `PRM_USER_CHANGE`.

> 단위는 CUBRID의 다른 메모리 sysparam이 사용하는 byte 기반 BIGINT + suffix(`K`/`M`/`G`) 표기법을 따른다. 본 문서에서 `_mb`/`_kb` suffix는 사용하지 않는다.

### 2.10 INFORMATION_SCHEMA

| 작업 | 위치 |
|---|---|
| `is_memory` 컬럼 노출 | `src/object/schema_system_catalog_install.cpp` + `*_install_query_spec.cpp` |
| SHOW CREATE TABLE | `csql_grammar.y` SHOW 룰에서 memory 표식 출력 |

---

## 3. 데이터 구조 상세

### 3.1 memory_chunk (행 저장 단위)

```cpp
// src/storage/memory_table.hpp
namespace cubmemtab {

// chunk 크기는 sysparam으로 가변 (registry 초기화 시 1회 결정).
// 한 registry 내 모든 chunk는 동일 크기. growth-only — chunks 벡터에서
// 원소를 절대 erase 하지 않으며, DROP 시점에만 registry 차원 일괄 해제.
// 결과: 기존 memory_row_ref{chunk_idx, offset}는 stable handle로 유지된다.
struct memory_chunk {
  std::unique_ptr<std::uint8_t[]> data;  // sysparam 크기 동적 할당
  std::uint32_t capacity;                // 동일 registry 내 모든 chunk 동일
  std::uint32_t used_bytes = 0;
  std::uint32_t row_count = 0;
};

// 행 위치 reference (PK index, scan cursor 등에서 사용).
// growth-only chunks 정책 하에서 stable; UPDATE 재배치 시에만 변경.
struct memory_row_ref {
  std::uint32_t chunk_idx;  // chunks 벡터 인덱스 (절대 erase 안 됨)
  std::uint32_t offset;     // chunk.data 안 오프셋
};

}  // namespace cubmemtab
```

행 직렬화 포맷: 기존 `OR_BUF` 힙 레코드 포맷 그대로 (heap_record.{h,c})를 재사용. `DB_VALUE` ↔ 레코드 변환 코드를 그대로 활용해 INSERT/SELECT 경로 변경 최소화.

`memory_table_chunk_size`는 sysparam (`#11`)으로 등록되며, **startup-only 플래그(`PRM_FOR_SERVER`, `PRM_USER_CHANGE` 미설정)**로 런타임 SET 시도는 표준 sysparam 메커니즘에 의해 거절된다 (§4.10.2 상세).

### 3.2 PK Hash Index

PK 키 표현은 두 안 중 택일. 본 문서는 (B)를 권장하되 4~6주 reserve 일정에 반영.

**(A) DB_VALUE 벡터 + 비교 함수 객체** — 단순. 정규화 없음. 비교 시 `tp_value_compare` 또는 `btree_compare_key` 호출. PK 한 번 lookup마다 N 컬럼 비교. 메모리 효율 낮음.

```cpp
struct pk_key_t {
  std::vector<DB_VALUE> values;  // multi-column PK 컬럼들 (deep copy)
};

struct pk_equal {
  TP_DOMAIN *key_domain;
  bool operator()(const pk_key_t& a, const pk_key_t& b) const;  // tp_value_compare 사용
};

struct pk_hasher {
  std::size_t operator()(const pk_key_t& k) const noexcept;     // 컬럼별 std::hash 결합
};
```

**(B) (권장) 정규화 시리얼라이저 + byte vector** — `btree_compare_key`/`btree_construct_buffer` 등 기존 키 직렬화 인프라를 재사용. multi-column PK는 컬럼 순서대로 직렬화 후 byte 비교 1회. lookup 비용 안정적. 단, 직렬화 함수가 in-memory 컨텍스트에서 직접 호출 가능한지 PoC 필요(R2 리스크) — **+4~6주 reserve**.

```cpp
struct pk_key_t {
  std::vector<std::uint8_t> normalized;  // 기존 키 직렬화 출력
  bool operator==(const pk_key_t& o) const { return normalized == o.normalized; }
};
struct pk_hasher {
  std::size_t operator()(const pk_key_t& k) const noexcept {
    return std::hash<std::string_view>{}(
      std::string_view{ reinterpret_cast<const char*>(k.normalized.data()), k.normalized.size() });
  }
};
```

키 정규화: 기존 `btree_compare_key()` (`src/storage/btree.h:904` 선언, `src/storage/btree.c` 구현) 및 `btree_construct_buffer` 류 함수를 재사용. Phase 4에서 B-tree로 마이그레이션 시 호환성 보장. multi-column PK는 컬럼 순서대로 도메인별 직렬화를 연결.

#### 3.2.1 Hash flooding 위협 모델 (`#24`)

`std::unordered_map`의 hash 함수는 deterministic하므로 동일 bucket으로 충돌하는 키를 의도적으로 만든 공격자가 hash table을 O(N²)로 퇴화시킬 수 있다(hash flooding). 메모리 테이블은 **권한 있는 DB 사용자만 INSERT**할 수 있으므로 위협 모델 측면에서 위험도는 낮다 (외부 무인증 입력이 직접 들어오는 web cache 등과 다름).

- **MVP 정책**: 기본 `std::hash` + std::unordered_map 그대로 사용. 위협 발생 시 운영자가 sysparam으로 hash seed를 randomize 하거나 SipHash 기반 사용자 정의 hasher로 교체. 본 PR 시리즈에는 randomized hasher를 포함하지 않음.
- **후속 작업 등재**: §13에 "PK index hash randomization (SipHash)"으로 기록.

### 3.3 memory_table

```cpp
struct memory_table {
  OID class_oid;                                          // 카탈로그 OID
  std::vector<std::unique_ptr<memory_chunk>> chunks;      // growth-only, erase 금지
  mutable std::shared_mutex rw_lock;                      // RW lock — 모든 read/write 보호
  std::atomic<std::uint64_t> row_count{0};
  std::atomic<std::uint64_t> bytes_used_logical{0};       // DELETE 즉시 감소 (사용자 노출용)
  std::atomic<std::uint64_t> bytes_used_physical{0};      // compaction 시까지 유지 (한도 비교용)
  std::atomic<std::uint32_t> ref_count{0};                // DROP-SCAN race 보호
  std::atomic<bool> is_dropped{false};                    // DROP 표식

  // PK index — rw_lock 하에 보호. unordered_map 동시 read도 별도 보호 필요해
  // 모든 접근 (read/write 공통)이 shared_lock 또는 unique_lock 보유 상태에서만 가능.
  std::unordered_map<pk_key_t, memory_row_ref, pk_hasher> pk_index;

  // tombstone bitmap. 동시성: 비트 단위 atomic으로 보호.
  // word=64 비트, slot 인덱스를 word/bit로 분해해 std::atomic<std::uint64_t>::fetch_or 사용.
  // bitmap의 grow는 unique_lock(rw_lock) 내에서만 push_back. (`#4` 참조)
  std::deque<std::atomic<std::uint64_t>> tombstones_bitmap;

  // 통계
  std::atomic<std::uint64_t> insert_count{0};
  std::atomic<std::uint64_t> update_count{0};
  std::atomic<std::uint64_t> delete_count{0};
  std::atomic<std::uint64_t> scan_count{0};
};
```

#### 3.3.1 Tombstone bitmap 컨테이너 결정 (`#4`)

`std::vector<std::atomic<T>>`는 `T`가 movable이 아니므로 표준 정의상 사용할 수 없고, push_back으로 reallocation 시 atomic 객체의 주소가 이동한다. 다른 스레드가 그 atomic을 동시에 fetch_or 호출 중이면 UB. 두 안 중 택일:

- **(권장) `std::deque<std::atomic<std::uint64_t>>`**: deque는 element 추가 시 기존 element 주소를 보존(중간 erase가 없는 한). bitmap grow가 다른 atomic 비트의 주소 안정성을 깨지 않는다.
- **(차선) chunk별 자체 bitmap**: 각 `memory_chunk`가 자기 row 만큼의 fixed-size `std::array<std::atomic<std::uint64_t>, N>`을 보유. 상위 `tombstones_bitmap` 자체가 사라짐. chunk size가 startup-only이므로 N이 컴파일 타임 또는 chunk 생성 시 1회 고정.

본 문서는 (권장)을 1차 채택. (차선)은 PoC 후 메모리 효율 차이가 크면 전환.

#### 3.3.2 동시성 결정 — RW lock 우선 (MVP)

- **PK index, chunks, tombstones grow** = `rw_lock`의 unique_lock 보유 상태에서만 변형.
- **PK lookup, full scan, tombstone bit read** = `rw_lock`의 shared_lock 보유 상태에서만 read.
- **tombstone bit set/clear** = atomic fetch_or/and (lock과 별개).
- **lockfree 자료구조 도입 안 함** (MVP): registry 자체도 lockfree 인프라(lf_entry_descriptor + tran::system + tran::index)를 회피하기 위해 §3.4의 결정대로 `std::shared_mutex + std::unordered_map`로 단순화. table 내부도 RW lock으로 단순화. lockfree 마이그레이션은 Phase 2.1.

### 3.4 memory_table_registry (전역) — MVP는 RW lock + unordered_map (`#1`)

```cpp
class memory_table_registry {
public:
  static memory_table_registry& instance() noexcept;

  int create(const OID *class_oid, const SM_CLASS *cls);
  // 주의: lookup과 ref_count 증가 사이의 race를 방지하려면
  // find_or_acquire를 사용. find_or_null만 호출하면 use-after-free 가능 (§4.5.3).
  memory_table* find_or_null(const OID *class_oid) const;
  memory_table* find_or_acquire(const OID *class_oid);  // shared_lock 하에 ref_count 증가까지 atomic
  int drop(const OID *class_oid);
  void destroy_all();

  std::uint64_t total_bytes_used() const noexcept;
  std::uint64_t total_limit() const noexcept;

private:
  // MVP: lockfree 인프라(lf_entry_descriptor + tran::system + tran::index) 도입 비용을 피하기 위해
  // 단순한 RW lock + unordered_map 조합으로 시작. 후속(Phase 2.1)에서 lockfree::hashmap으로 전환 검토.
  mutable std::shared_mutex m_registry_lock;
  std::unordered_map<OID, std::unique_ptr<memory_table>, oid_hasher, oid_equal> m_tables;

  std::atomic<std::uint64_t> m_total_bytes{0};   // physical bytes (한도 비교용)
  std::uint64_t m_total_limit;
};
```

`find_or_acquire`의 의도: shared_lock(m_registry_lock) 보유 상태에서 unordered_map::find → ref_count.fetch_add → is_dropped 재검사를 한 임계구역 안에서 수행해 lookup→ref_count 증가 사이 use-after-free를 차단(`#2`). lock-free 전환 시에는 hazard pointer 또는 epoch GC가 필요하다.

전역 registry의 lockfree 전환(Phase 2.1)은 `src/base/lockfree_hashmap.hpp`의 `namespace lockfree`(line 39, 201)에 정의된 `lockfree::hashmap` C++ 래퍼 또는 legacy `LF_HASH_TABLE` C API(`src/base/lock_free.h`)를 후보로 삼되, lf_entry_descriptor + tran::system + tran::index 인프라 통합 비용을 별도 평가한다.

---

## 4. 모듈별 구현 상세

### 4.1 Parser (Week 1)

#### 4.1.1 Lexer

`csql_lexer.l`에 `MEMORY` 키워드 추가 (CUBRID는 keyword-list 방식이므로 `keyword.c`에도 등재). `TEMPORARY` 토큰(`csql_grammar.y:1403` `%token TEMPORARY`)은 의미가 다르므로 손대지 않음. **§2.1.1**에 따라 non-reserved keyword로 등록.

#### 4.1.2 Grammar

기존 `create_stmt` 룰(`csql_grammar.y:2540`)은 `CREATE` → `opt_hint_list` → `of_class_table_type` → `class_name_without_dot` 식의 단일 진입을 하므로, `MEMORY` 키워드를 `of_class_table_type` 또는 별도 옵션 토큰으로 받아 `is_memory_table` 플래그를 set하는 우회 룰을 추가:

```bison
create_stmt
  : CREATE opt_replace MEMORY TABLE class_name '(' attr_def_list ')' table_options
    {
       PT_NODE *node = parser_new_node(this_parser, PT_CREATE_ENTITY);
       node->info.create_entity.entity_type = PT_CLASS;
       node->info.create_entity.is_memory_table = true;
       /* ... */
    }
  ;
```

추가 제약 (semantic_check.c):
- PK 필수 (UNIQUE 단독은 불가)
- FOREIGN KEY 불가
- AUTO_INCREMENT 불가 (1차)
- DEFAULT 값 일반 표현식만 (sysdate 등 동적 함수 불가)
- 컬럼 타입: 일반 SQL 타입 전체 허용. LOB만 1차 거절.
- SA_MODE 빌드에서 `CREATE MEMORY TABLE` DDL 실행 진입 시 `ER_MEMORY_TABLE_NOT_SUPPORTED_IN_SA_MODE` 반환 (§9.2 Issue 5).

#### 4.1.3 PT_NODE 플래그

`parse_tree.h:1951` `struct pt_create_entity_info`에 기존 비트필드(`or_replace:1`, `if_not_exists:1`)와 동일한 스타일로 `unsigned is_memory_table:1;` 추가.

### 4.2 Catalog (Week 1-2)

#### 4.2.1 Flag 추가

```c
// src/object/class_object.h:305-312 (typedef enum ... SM_CLASS_FLAG)
typedef enum
{
  SM_CLASSFLAG_SYSTEM = 1,             /* a system defined class */
  SM_CLASSFLAG_WITHCHECKOPTION = 2,    /* a view with check option */
  SM_CLASSFLAG_LOCALCHECKOPTION = 4,   /* view w/local check option */
  SM_CLASSFLAG_REUSE_OID = 8,          /* the class can reuse OIDs */
  SM_CLASSFLAG_SUPPLEMENTAL_LOG = 16,  /* reserved flag for supplemental log. */
  SM_CLASSFLAG_MEMORY_TABLE = 32       /* NEW: in-memory table */
} SM_CLASS_FLAG;
```

#### 4.2.2 직렬화 점검

`src/object/transform_cl.c::class_to_disk()` (line 3782)에서 클래스 직렬화의 일부로 `or_put_int (buf, class_->flags)` (line 3710)로 저장됨. 32-bit `int`로 round-trip되므로 신규 비트(0x20)도 자동 호환. 별도 변경 불필요. **Week 1 점검 항목**: 신규 비트가 set된 클래스를 만들고 reload하여 비트 보존 확인.

#### 4.2.3 헬퍼

```c
// src/object/class_object.h
static inline bool sm_is_memory_table(const SM_CLASS *cls) {
  return (cls->flags & SM_CLASSFLAG_MEMORY_TABLE) != 0;
}
```

#### 4.2.4 DDL 실행 진입점 분기

CUBRID에 `sm_create_class()`라는 단일 함수는 없고, DDL 실행은 `src/query/execute_schema.c::do_create_entity()` (line 9025) → `sm_finish_class()` (`src/object/schema_manager.c:13431`) 경로로 이루어진다. flag set 패턴은 기존 `schema_manager.c:3071,3135` 의 `class_->flags |= SM_CLASSFLAG_SYSTEM;` 와 동일하게 직접 비트 OR로 처리한다 (CUBRID 코드베이스에 `smt_add_class_flag`라는 헬퍼 함수는 존재하지 않는다 — 직접 set 또는 PR 일부로 신규 헬퍼 작성).

```c
// src/query/execute_schema.c::do_create_entity() 진입 직후
int do_create_entity (PARSER_CONTEXT *parser, PT_NODE *node) {
  /* ...기존 PT 검증/template 빌드... */
  if (node->info.create_entity.is_memory_table) {
    /* SM_TEMPLATE에 SM_CLASSFLAG_MEMORY_TABLE 추가 — 기존 패턴(`schema_manager.c:3071`)과 동일.
     * 헬퍼는 코드베이스에 없으므로 직접 set 하거나, 본 PR에서 신규 헬퍼 추가. */
    template_->flags |= SM_CLASSFLAG_MEMORY_TABLE;
  }
  /* sm_finish_class() 진행 — 일반 경로에서 heap 할당이 일어나는 지점에
   * SM_CLASSFLAG_MEMORY_TABLE 체크를 넣어 skip하고, registry 등록은 §4.4.3 결정안 (b)에 따라
   * DDL 실행 직후 즉시 수행 (commit 시점 defer 아님). */
}
```

`sm_finish_class()`는 내부에서 `locator_create_heap_if_needed()`(또는 동등 경로)로 heap을 할당하므로, 그 호출을 `SM_CLASSFLAG_MEMORY_TABLE` 비트 체크로 가드. 정확한 가드 지점은 Week 1-2 PoC에서 확정.

### 4.3 Memory Store (Week 3-5)

#### 4.3.1 디렉토리 구조

```
src/storage/
  memory_table.hpp     # public API
  memory_table.cpp     # 구현
  memory_table_pk.hpp  # PK index 내부
  memory_table_pk.cpp
```

#### 4.3.2 Public API

```cpp
// src/storage/memory_table.hpp
namespace cubmemtab {

// 등록 (DDL 시) — registry_create는 PK descriptor를 1회 빌드해 memory_table에 보관한다.
int registry_create(const OID *class_oid, const SM_CLASS *cls);
int registry_drop(const OID *class_oid);

// 조회
memory_table* registry_find(const OID *class_oid);            // ref_count 증가 안 함 (catalog probe 등 단순 존재 확인용)
memory_table* registry_find_acquire(const OID *class_oid);    // shared_lock 하에 ref_count 증가까지 atomic — scan/DML이 사용

// PK descriptor — registry_create 시 1회 빌드해 memory_table에 보관. (`#19`)
// 이후 extract_pk는 이 descriptor만 받으므로 cls 재해석이 필요 없다.
struct pk_descriptor {
  std::vector<int>       column_indices;   // SM_CLASS attr 순서의 PK 컬럼 인덱스
  std::vector<TP_DOMAIN*> column_domains;  // 각 PK 컬럼의 도메인
};

// 키 추출 — RECDES에서 PK 컬럼 추출. multi-column PK는 pk_descriptor의 PK 컬럼 순서대로
// 도메인별로 직렬화 연결(§3.2 안 (B))하여 normalized byte vector를 만든다.
// 1차 PoC에서 `btree_construct_buffer`/`btree_compare_key` 등 기존 키 직렬화 인프라
// 재사용 가능 여부를 검증; 안 되면 신규 헬퍼 작성 (R2 리스크).
int extract_pk(const pk_descriptor *pk_desc, const RECDES *recdes, pk_key_t *out_key);

// DML
int insert_row(memory_table *t, const RECDES *recdes);
int update_row_by_pk(memory_table *t, const pk_key_t& key, const RECDES *new_recdes);
int delete_row_by_pk(memory_table *t, const pk_key_t& key);

// SCAN
struct scan_cursor {
  std::uint32_t chunk_idx = 0;
  std::uint32_t offset = 0;
  std::uint64_t scanned_rows = 0;
};

int scan_init(memory_table *t, scan_cursor *cur);
SCAN_CODE scan_next(memory_table *t, scan_cursor *cur, RECDES *out_recdes);  // S_SUCCESS/S_END/S_ERROR
int scan_end(memory_table *t, scan_cursor *cur);

// PK lookup (single-row)
SCAN_CODE scan_pk_lookup(memory_table *t, const pk_key_t& key, RECDES *out_recdes);

// Lifecycle
int registry_init(std::uint64_t total_limit_bytes);
void registry_shutdown();

// 통계
struct stats {
  std::uint64_t row_count;
  std::uint64_t bytes_used_logical;
  std::uint64_t bytes_used_physical;
  std::uint64_t insert_count;
  // ...
};
int get_stats(const OID *class_oid, stats *out);

}  // namespace cubmemtab
```

`out_recdes`의 메모리 소유 — **MVP는 zero-copy 채택** (`#8`): scan-lifetime shared_lock(rw_lock) 동안 chunks 내부 데이터에 대한 비-소유 포인터를 반환. growth-only chunks 정책(§3.1)이 chunk 주소 안정성을 보장하고 tombstone 비트 set은 데이터를 변경하지 않으므로 안전. **Trade-off** (§6에 명시): scan이 shared_lock을 보유하므로 long-running scan은 INSERT/UPDATE/DELETE를 막는다. OLAP 워크로드에서 받아들이는 비용. INSERT-우선 운영 환경에서는 scan 청크 단위로 lock 획득/해제(scan-batch lock) 모드를 sysparam으로 제공하는 것을 후속 작업으로 검토.

#### 4.3.3 INSERT 흐름 (의사 코드)

```cpp
int insert_row(memory_table *t, const RECDES *recdes) {
  pk_key_t key;
  int err = extract_pk(t->pk_desc, recdes, &key);  // pk_descriptor 사용 (`#19`)
  if (err != NO_ERROR) return err;

  std::unique_lock lk(t->rw_lock);

  // PK uniqueness
  if (t->pk_index.find(key) != t->pk_index.end()) {
    return ER_MEMORY_TABLE_PK_DUPLICATE;
  }

  // 메모리 한도 — atomic compare_exchange 루프로 race 없이 예약 (registry physical bytes 기준)
  std::size_t need = recdes->length;
  auto& reg = registry::instance();
  for (;;) {
    std::uint64_t cur = reg.m_total_bytes.load(std::memory_order_acquire);
    if (cur + need > reg.m_total_limit) {
      return ER_MEMORY_TABLE_FULL;
    }
    if (reg.m_total_bytes.compare_exchange_weak(
          cur, cur + need, std::memory_order_acq_rel)) {
      break;
    }
  }

  // 새 chunk 할당 또는 기존 chunk에 append.
  // ensure_chunk_with_space는 (chunk*, chunk_idx)를 함께 반환해
  // 포인터 산술(chunk - chunks.front().get())의 UB를 피한다.
  std::uint32_t chunk_idx = 0;
  memory_chunk *chunk = ensure_chunk_with_space(t, need, &chunk_idx);

  std::memcpy(chunk->data.get() + chunk->used_bytes, recdes->data, need);
  memory_row_ref ref{ chunk_idx, chunk->used_bytes };
  chunk->used_bytes += need;
  chunk->row_count++;

  t->pk_index[key] = ref;
  t->row_count.fetch_add(1, std::memory_order_relaxed);
  t->bytes_used_logical.fetch_add(need, std::memory_order_relaxed);
  t->bytes_used_physical.fetch_add(need, std::memory_order_relaxed);
  t->insert_count.fetch_add(1, std::memory_order_relaxed);

  return NO_ERROR;
}
```

`ensure_chunk_with_space`: 마지막 chunk에 공간이 있으면 그 인덱스(`chunks.size() - 1`)를 그대로 반환. 부족하면 `chunks.emplace_back(...)` 후 새 인덱스(`chunks.size() - 1`)를 반환. **포인터 산술 인덱스 계산은 사용하지 않는다**.

##### 4.3.3.1 bytes_used 매트릭스 (`#5`)

세 카운터(registry physical, table physical, table logical)와 네 액션(INSERT, UPDATE, DELETE, compaction)의 변화를 명시한다. **`m_total_bytes`는 registry physical로 통일** — 메모리 한도 비교는 항상 physical 기준.

| 액션 | registry `m_total_bytes` (physical) | table `bytes_used_physical` | table `bytes_used_logical` |
|---|---|---|---|
| INSERT (new_size) | `+= new_size` | `+= new_size` | `+= new_size` |
| UPDATE in-place same size | 0 | 0 | 0 |
| UPDATE in-place shrink (Δ = old−new) | 0 (compaction까지 유지) | 0 (compaction까지 유지) | `-= Δ` (즉시) |
| UPDATE 재배치 (old → new size) | `+= new_size` (옛 위치는 compaction까지 유지) | `+= new_size` (옛 위치는 compaction까지 유지) | `+= (new_size − old_size)` |
| DELETE (row_size) | 0 (compaction까지 유지) | 0 (compaction까지 유지) | `-= row_size` (즉시) |
| Compaction (live_size 복사 후 옛 chunks 폐기) | `-= (옛 physical − live_size)` | 옛 physical 값을 live_size로 reset | 변동 없음 (이미 logical은 정확) |

> 사용자 노출 통계(INFORMATION_SCHEMA 또는 `SHOW STATS`)는 logical을, OOM 한도 비교는 physical을 사용한다. compaction 직후 두 값은 일치한다.

#### 4.3.4 UPDATE 흐름

- PK index에서 위치 찾기
- 새 row 크기와 기존 row 크기 비교
  - 같으면: in-place 덮어쓰기. logical/physical bytes 변동 없음.
  - 작으면: in-place + 차이만큼 logical bytes 즉시 감소. physical은 그대로 (compaction 대상).
  - 크면: 새 위치에 append, 옛 위치는 tombstone 표시, PK index 업데이트. logical bytes는 (new_size − old_size) 증가, physical bytes는 new_size 증가.

#### 4.3.5 DELETE 흐름

- PK index에서 위치 찾기
- tombstone bitmap에 atomic fetch_or로 비트 set (soft delete)
- PK index에서 제거
- `row_count--`
- `bytes_used_logical -= row_size` 즉시 (사용자 노출 통계 정확)
- `bytes_used_physical`는 compaction 시까지 유지 — registry 한도 비교는 physical 사용

##### 4.3.5.1 row_size 산출 (`#22`)

DELETE/UPDATE에서 logical bytes 갱신을 정확히 하려면 row_size를 알아야 한다. 두 안 중 (b)를 채택.

- **(a) PK lookup 후 RECDES 파싱**: chunk에서 `OR_BUF`로 다시 읽어 length 산출. CPU 비용.
- **(b) (권장) `memory_row_ref`에 length 캐시**:

```cpp
struct memory_row_ref {
  std::uint32_t chunk_idx;
  std::uint32_t offset;
  std::uint32_t length;   // ← row_size 캐시. INSERT 시 기록.
};
```

추가로 `OR_BUF` 직렬화 invariant 확인: CUBRID heap record 첫 4바이트는 record length(little-endian uint32)이며, `memory_row_ref::length`와 일치한다. UPDATE/compaction 시 둘 다 갱신.

#### 4.3.6 Compaction (MVP 단순 정책)

MVP는 자동 compaction을 도입하지 않는다. 다음 두 안 중 (b)를 1차 채택.

- **(a) Phase 2.1로 OOS(Out-of-Scope)**: tombstone 비율이 높아도 그대로 둔다. 사용자에게 운영 가이드로 안내.
- **(b) (권장) 명시적 단순 재구성**: `OPTIMIZE TABLE foo` (또는 sysparam-trigger background daemon)에서 `unique_lock(rw_lock)` 보유하에 (1) live row만 신규 chunks로 복사, (2) PK index 전체 재구성, (3) 옛 chunks/bitmap 일괄 폐기. 단순/안전. lock 보유 시간이 길지만 MVP 허용.

자동 백그라운드 trigger는 `memory_table_compact_threshold_pct` sysparam을 0으로 두면 비활성. MVP에서는 기본 비활성(0)으로 출시. Phase 2.1에서 자동화 검토.

### 4.4 DML Integration (Week 6-9)

#### 4.4.1 분기 위치 + dispatch 캐시 (`#14`)

서버 측 DML 진입점인 `locator_attribute_info_force()`(`src/transaction/locator_sr.c:7461`) 진입 직후 카탈로그 플래그 체크:

```c
// src/transaction/locator_sr.c:7461
int
locator_attribute_info_force (THREAD_ENTRY * thread_p, const HFID * hfid, OID * oid, HEAP_CACHE_ATTRINFO * attr_info,
                              ATTR_ID * att_id, int n_att_id, LC_COPYAREA_OPERATION operation, int op_type,
                              HEAP_SCANCACHE * scan_cache, int *force_count, bool not_check_fk,
                              REPL_INFO_TYPE repl_info, int pruning_type, PRUNING_CONTEXT * pcontext,
                              FUNC_PRED_UNPACK_INFO * func_preds, MVCC_REEV_DATA * mvcc_reev_data,
                              UPDATE_INPLACE_STYLE force_update_inplace, RECDES * rec_descriptor, bool need_locking)
{
  /* dispatch 비용 회피: HEAP_SCANCACHE 또는 HEAP_CACHE_ATTRINFO에
   * is_memory_table 비트를 캐시한다. 첫 row 진입 시 카탈로그 lookup으로 확정,
   * 같은 statement 내 후속 row는 캐시 비트만 본다. */
  if (HEAP_IS_MEMORY_TABLE_BIT_RESOLVED (scan_cache)) {
    if (HEAP_IS_MEMORY_TABLE (scan_cache)) {
      return memory_table_dml_dispatch (thread_p, attr_info, operation, op_type, force_count);
    }
    /* 일반 row store 경로... */
  } else {
    /* 첫 row: 카탈로그 lookup 후 캐시 비트 set. */
    bool is_mt = sm_is_memory_table_oid (&attr_info->class_oid);
    HEAP_SET_MEMORY_TABLE_BIT (scan_cache, is_mt);
    if (is_mt) {
      return memory_table_dml_dispatch (thread_p, attr_info, operation, op_type, force_count);
    }
  }
  /* 기존 row store 경로... */
}
```

**일반 경로 회귀 KPI**: 메모리 테이블이 아닌 일반 INSERT/UPDATE/DELETE 처리량이 캐시 비트 도입 전 대비 **<1% 감소** (§7.4). 캐시 비트 도입 자체는 분기 1개 + 메모리 1바이트만 추가하므로 영향 거의 없음을 검증.

`memory_table_dml_dispatch`는 `LC_COPYAREA_OPERATION operation` (INSERT/UPDATE/DELETE)에 따라 적절한 memory_store API 호출.

#### 4.4.2 트랜잭션 의미론 (사용자 가시 동작)

**Row-level autocommit**: 메모리 테이블에 대한 INSERT/UPDATE/DELETE는 SQL 트랜잭션 컨텍스트와 무관하게 **각 row가 적용 즉시 커밋된 것으로 간주**된다.

```sql
BEGIN;
INSERT INTO regular_tbl VALUES (1);   -- 트랜잭션 적용
INSERT INTO memory_tbl  VALUES (2);   -- 즉시 가시화, ROLLBACK 영향 없음
ROLLBACK;
-- 결과: regular_tbl는 비어 있고, memory_tbl는 (2) 보유
```

**Statement atomicity 정책 — row-level commit**: multi-row statement (예: `INSERT ... SELECT`, `INSERT VALUES (...), (...), (...)`)이 중간에 실패해도 **이미 적용된 row는 그대로 보존**된다. 부분 적용은 메모리 테이블의 명시 동작이며, 일반 row-store 의미론과 다르므로 사용자 가이드 강조.

**Statement abort 콜백 검증** (`#7`): CUBRID는 statement 내 에러 시 일부 abort 콜백(`xtran_server_abort_partial`, savepoint 등)이 호출되는 경로가 있다. 메모리 테이블의 row는 이런 콜백에서 **자동 rollback되면 안 된다**. Week 8 산출물로 다음을 등재:

- `tran_abort_*`/`xtran_server_abort_partial` 등 statement-수준 abort 콜백 목록을 grep으로 추출
- 각 콜백이 메모리 테이블 데이터를 건드리지 않음을 코드 inspection 또는 unit test로 검증 (메모리 테이블 ID는 콜백 dispatch에서 skip)
- 누락 콜백 발견 시 `SM_CLASSFLAG_MEMORY_TABLE` 가드 추가

**격리 수준 매핑 (SQL 표준)**:

| SQL 표준 격리 | 메모리 테이블 동작 | 비고 |
|---|---|---|
| READ UNCOMMITTED | **본 모델과 등가** | 다른 세션의 미커밋(=row 적용 직후) write 가시 |
| READ COMMITTED | 미지원 | snapshot 없음 |
| REPEATABLE READ | 미지원 | snapshot 없음 |
| SERIALIZABLE | 미지원 | MVCC 없음 |

> 본 문서는 이전에 사용한 "dirty read 허용"이라는 표현을 **read-uncommitted-equivalent**로 정정한다. 메모리 테이블의 row는 적용 직후 즉시 다른 세션에 가시되고 ROLLBACK 영향 밖이므로, SQL 표준 정의의 dirty read보다는 "별도 mini-transaction에서 즉시 커밋된 행" 모델에 가깝다.

**SET TRANSACTION ISOLATION LEVEL과의 상호작용** (`#23`): 사용자가 `SET TRANSACTION ISOLATION LEVEL REPEATABLE READ` 등을 설정해도 **메모리 테이블에 대한 access 의미론은 변경되지 않는다**(read-uncommitted-equivalent 그대로). 같은 트랜잭션이 일반 테이블과 메모리 테이블을 함께 SELECT할 때 일반 테이블 부분은 사용자가 설정한 격리 수준의 MVCC snapshot, 메모리 테이블 부분은 read-uncommitted-equivalent로 작동한다 — 한 쿼리 내 격리 모델 혼재(§5 표 마지막 행). 사용자 가이드에 명시 필수.

**근거**: 메모리 테이블은 WAL을 안 쓰므로 ROLLBACK을 위한 undo 정보가 없음. 위 격리 수준 결정과 일관.

**문서화 필수**: 사용자 가이드와 INFORMATION_SCHEMA에 명시.

#### 4.4.3 DDL atomicity (CREATE/DROP과 ROLLBACK) — 결정안 변경 (`#3`, `#13`)

DDL 자체(카탈로그 변경)는 **일반 트랜잭션 + WAL 보호 하에 처리**된다. 메모리 테이블 데이터(휘발 영역)만 WAL에서 빠진다.

**v3 결정안**: **CREATE 즉시 global 등록 + ROLLBACK 시 deferred drop을 호출하지 않음**. 결과:

- **CREATE MEMORY TABLE 후 COMMIT**: 카탈로그 + registry 모두 영속. 그 사이 적재된 row 보존.
- **CREATE MEMORY TABLE 후 ROLLBACK**: **카탈로그는 WAL에 의해 자동 복구되지만, registry entry와 row는 보존된다**. 사용자에게는 "카탈로그가 사라졌으나 registry에는 entry가 남아 있는" 상태로 보일 수 있다 → **registry는 startup-style 카탈로그 reconciliation을 commit/rollback 시점에도 수행**해 카탈로그에 없는 entry는 폐기. 즉:
  - 트랜잭션 commit hook(§2.7)에서 자기 트랜잭션이 만든 메모리 테이블 entry는 그대로 두고,
  - rollback hook에서는 카탈로그가 사라졌음을 인지하고 **자기 트랜잭션이 만든 entry만** 폐기 (row 보존이 목적이라면 폐기 안 함을 1차 정책으로 둘 수도 있으나, 카탈로그 부재 상태로 entry를 남기면 다른 path에서 dangling — **본 문서는 폐기를 1차 정책**으로 한다).

> **v2와의 차이**: v2는 (a) thread-local pending registry로 이중 lookup이 발생했고 commit/rollback hook 모순(rollback 시 row 보존 vs. drop)이 있었다. v3는 (b)로 단일화해 이중 lookup 비용을 제거. ROLLBACK 시 row 보존을 유지하려면 운영자에게 "DDL은 명시 commit 권장" 가이드를 제공.

- **DROP TABLE memory_tbl 후 COMMIT**: 카탈로그 제거. registry entry는 §4.7.3대로 deferred free.
- **DROP TABLE memory_tbl 후 ROLLBACK**: 카탈로그가 복구되며, registry entry도 그대로(deferred drop 호출하지 않음). 결과적으로 사용자에게는 "DROP이 없었던 것처럼" 동작. v2의 "테이블은 살아 있고 비어 있다" 비대칭이 v3에서 해소됨.

**대안 비교**:

| 대안 | (a) thread-local pending registry + commit-merge (v2 채택) | (b) 즉시 등록 + rollback에서 drop 안 함 (v3 채택) |
|---|---|---|
| 구현 복잡도 | 중 (thread-local 컨테이너 + commit hook) | 낮 (등록 콜백만) |
| 이중 lookup | 있음 (자기 트랜잭션 thread-local + global) | **없음** |
| 미커밋 가시성 | 자기 세션만 | 다른 세션도 즉시 봄 (read-uncommitted-equivalent와 일관) |
| CREATE+ROLLBACK 데이터 | row 폐기 (v2) / row 폐기 (v3 정책) | row 폐기 (v3 정책) |
| DROP+ROLLBACK 데이터 | 데이터 손실 (v2 비대칭 문제) | **데이터 보존** (v3 비대칭 해소) |
| 사용자 가이드 강조점 | DDL은 commit 후 다른 세션에 가시 | DDL은 즉시 다른 세션 가시 |

**v3는 (b)를 채택**. 미커밋 가시성은 read-uncommitted-equivalent 모델과 일관해 추가 사용자 혼란을 야기하지 않는다.

**Hook 함수명 — 검증된 함수만** (`#16`):

```c
/* 트랜잭션 commit/rollback 시점에 발동하도록 등록.
 * 본 문서가 직접 grep으로 확인한 실재 함수만 인용:
 *   - log_commit_local         (src/transaction/log_manager.c:5156)
 *   - log_abort_local          (src/transaction/log_manager.c:5274)
 *   - logtb_complete_mvcc      (호출 지점 line 5173, 5302, 5320)
 *   - log_complete             (line 5650)
 *   - log_sysop_end_logical_undo (line 3938, sysop 경로)
 * 이 다섯 후보 중 어느 지점에 hook을 다는지는 Week 1 PoC에서 확정. */
mtab_register_post_commit (thread_p, memory_table_registry_commit_create, class_oid);
mtab_register_post_rollback (thread_p, memory_table_registry_rollback_create, class_oid);
```

`memory_table_registry_commit_create`/`memory_table_registry_rollback_create`는 본 PR에서 신규 작성하는 헬퍼 함수다 — CUBRID 코드베이스 grep으로 확인되지 않으며, 신규 헬퍼임을 명시한다. (코드베이스의 기존 트랜잭션 콜백 등록 인프라가 있다면 그것을 그대로 재사용; 없으면 PR 일부로 신규 추가.)

> **R1 hook PoC는 Week 1 산출물**. 트랜잭션 종료 콜백 후크 위치가 잡히지 않으면 후속 모든 모듈 일정이 영향을 받으므로 1주차에 검증.

**Crash recovery**: 카탈로그 변경은 일반 WAL로 복구된다. 데이터는 휘발이므로 startup 시 빈 entry로만 복원(§4.7.1). recovery 자체에 메모리 테이블 특수 로직은 없다.

### 4.5 Scan Integration (Week 10-11)

#### 4.5.1 SCAN_TYPE 확장

```c
// src/query/scan_manager.h:77-94
typedef enum
{
  S_HEAP_SCAN = 1,
  S_PARALLEL_HEAP_SCAN,
  S_CLASS_ATTR_SCAN,
  S_INDX_SCAN,
  S_LIST_SCAN,
  /* ... S_HEAP_SCAN_RECORD_INFO, S_HEAP_SAMPLING_SCAN 등 ... */
  S_MEMORY_TABLE_SCAN          /* NEW */
} SCAN_TYPE;
```

#### 4.5.2 SCAN_ID 멤버 (실제 union 인용)

`scan_manager.h:402-413` `struct scan_id_struct` 내 union의 실제 멤버는 다음 12개이다 (`HEAP_PAGE_SCAN_ID hpsid` 포함). MEMORY_TABLE_SCAN_ID는 13번째로 추가.

```c
// src/query/scan_manager.h:402-413 (실제 인용)
union
{
  LLIST_SCAN_ID llsid;        /* List File Scan Identifier */
  HEAP_SCAN_ID hsid;          /* Regular Heap File Scan Identifier */
  PARALLEL_HEAP_SCAN_ID phsid;/* Parallel Heap File Scan Identifier */
  HEAP_PAGE_SCAN_ID hpsid;    /* Scan heap pages without going through records */
  INDX_SCAN_ID isid;          /* Indexed Heap File Scan Identifier */
  INDEX_NODE_SCAN_ID insid;   /* Scan b-tree nodes */
  SET_SCAN_ID ssid;           /* Set Scan Identifier */
  DBLINK_SCAN_ID dblid;       /* DBLink Array Identifier */
  REGU_VALUES_SCAN_ID rvsid;  /* regu_variable list identifier */
  SHOWSTMT_SCAN_ID stsid;     /* show stmt identifier */
  JSON_TABLE_SCAN_ID jtid;
  METHOD_SCAN_ID msid;
  MEMORY_TABLE_SCAN_ID mtsid; /* NEW */
} s;
```

**비-trivial 멤버 회피** (`#15`): C union 내부에 비-trivial 타입(예: `std::vector`, `pk_key_t`의 `std::vector<uint8_t>`)을 직접 두면 union의 sizeof와 special member function 처리가 복잡하고, C++ standard layout 보장도 깨진다. 따라서 **MEMORY_TABLE_SCAN_ID 내 무거운 멤버는 모두 heap 포인터**로 둔다.

```c
typedef struct memory_table_scan_id {
  cubmemtab::memory_table *mtable;       /* registry 보유 비-소유 포인터 */
  cubmemtab::scan_cursor   cursor;        /* trivial: chunk_idx, offset, scanned_rows */
  RECDES                   work_recdes;   /* trivial: data 포인터는 zero-copy 시 chunk 내부를 가리킴 */
  PRED_EXPR               *where_pred;    /* WHERE 절 push-down */
  int                      key_lookup_mode;/* 0=full scan, 1=PK lookup, 2=PK lookup done */
  cubmemtab::pk_key_t     *lookup_key;    /* heap에 alloc — union sizeof 영향 없음. NULL이면 full scan */
} MEMORY_TABLE_SCAN_ID;
```

`scan_open`에서 PK lookup 모드일 때만 `lookup_key = new cubmemtab::pk_key_t(...)`를 alloc하고, `scan_end`에서 `delete lookup_key`. C 측에서 보면 `pk_key_t *`는 단순 포인터이므로 union/standard layout 무해.

**Union 크기 점검 + static_assert** (`#6`):

기존 union의 sizeof는 컴파일러/플랫폼별로 결정되며 가장 큰 멤버에 의해 좌우된다. `MEMORY_TABLE_SCAN_ID`가 추가됨으로써 union sizeof가 증가하면 `SCAN_ID`를 임베드하는 모든 자료구조의 메모리 풋프린트가 영향을 받는다.

- **MVP 정책**: 위처럼 무거운 멤버를 모두 heap 포인터로 두어 `MEMORY_TABLE_SCAN_ID` sizeof를 충분히 작게 유지.
- **Compile-time 단언**: 기존 union의 모든 멤버에 대해 sizeof 비교를 거는 대신, 가장 큰 기존 멤버(보통 `INDX_SCAN_ID`)를 측정 헬퍼로 잡아 그 이하임을 단언:

```cpp
// 측정 헬퍼: 기존 union 멤버 12개의 max sizeof.
constexpr std::size_t kSidMaxExisting = std::max({
  sizeof(LLIST_SCAN_ID),
  sizeof(HEAP_SCAN_ID),
  sizeof(PARALLEL_HEAP_SCAN_ID),
  sizeof(HEAP_PAGE_SCAN_ID),
  sizeof(INDX_SCAN_ID),
  sizeof(INDEX_NODE_SCAN_ID),
  sizeof(SET_SCAN_ID),
  sizeof(DBLINK_SCAN_ID),
  sizeof(REGU_VALUES_SCAN_ID),
  sizeof(SHOWSTMT_SCAN_ID),
  sizeof(JSON_TABLE_SCAN_ID),
  sizeof(METHOD_SCAN_ID),
});
static_assert(sizeof(MEMORY_TABLE_SCAN_ID) <= kSidMaxExisting,
              "MEMORY_TABLE_SCAN_ID exceeds existing union members; move heavy fields to heap");
```

- **Runtime 회귀 테스트**: `unit_tests/storage/memory_table_scan_id_size_test.cpp` (Catch2)에서 `sizeof(SCAN_ID)`를 측정해 baseline 대비 증가 없음 확인.

#### 4.5.3 init/next/end — registry-level lock으로 ref_count race 방지 (`#2`)

```c
// src/query/scan_manager.c::scan_start_scan()
case S_MEMORY_TABLE_SCAN:
  {
    MEMORY_TABLE_SCAN_ID *sid = &scan_id->s.mtsid;
    /* lookup과 ref_count 증가를 한 임계구역에서 처리.
     * registry_find_acquire는 m_registry_lock의 shared_lock을 잡고,
     * (1) unordered_map::find,
     * (2) is_dropped 검사,
     * (3) ref_count.fetch_add
     * 를 한 구역에서 수행한다. 이 사이에 DROP이 m_registry_lock의 unique_lock을
     * 잡고 entry를 erase하는 것을 차단하므로 use-after-free 불가. */
    sid->mtable = cubmemtab::registry_find_acquire (&class_oid);
    if (sid->mtable == nullptr) {
      return ER_MEMORY_TABLE_NOT_FOUND;
    }
    /* 이후 read는 sid->mtable->rw_lock의 shared_lock을 cubmemtab::scan_init/scan_next가
     * 내부적으로 잡는다(scan-lifetime hold). zero-copy(§4.3.2) 대응. */
    cubmemtab::scan_init(sid->mtable, &sid->cursor);
  }
  break;

// src/query/scan_manager.c::scan_next_scan_local()
case S_MEMORY_TABLE_SCAN:
  status = scan_next_memory_table_scan(thread_p, scan_id);
  break;

// src/query/scan_manager.c::scan_end_scan()
case S_MEMORY_TABLE_SCAN:
  cubmemtab::scan_end(scan_id->s.mtsid.mtable, &scan_id->s.mtsid.cursor);
  scan_id->s.mtsid.mtable->ref_count.fetch_sub(1, std::memory_order_acq_rel);
  /* lookup_key heap free */
  delete scan_id->s.mtsid.lookup_key;
  scan_id->s.mtsid.lookup_key = nullptr;
  break;
```

PK 단일 lookup 분기 — `out_recdes`는 `MEMORY_TABLE_SCAN_ID::work_recdes`를 가리키며, 반환 코드는 표준 `SCAN_CODE` (`S_SUCCESS`, `S_END`, `S_ERROR`)를 사용:

```c
SCAN_CODE scan_next_memory_table_scan(THREAD_ENTRY *thread_p, SCAN_ID *scan_id) {
  MEMORY_TABLE_SCAN_ID *sid = &scan_id->s.mtsid;
  RECDES *out_recdes = &sid->work_recdes;

  if (sid->key_lookup_mode == 1) {
    /* PK lookup — shared_lock 하에 unordered_map 조회.
     * cubmemtab::scan_pk_lookup가 내부에서 shared_lock을 잡는다. */
    SCAN_CODE c = cubmemtab::scan_pk_lookup(sid->mtable, *sid->lookup_key, out_recdes);
    sid->key_lookup_mode = 2;  // 다음 호출은 S_END
    return c;  // S_SUCCESS or S_END
  }
  if (sid->key_lookup_mode == 2) {
    return S_END;
  }
  /* Full scan — cubmemtab::scan_next 내부에서 shared_lock 보유 */
  return cubmemtab::scan_next(sid->mtable, &sid->cursor, out_recdes);
}
```

### 4.6 Optimizer (Week 11)

`query_planner.c`에서 memory table을 발견하면 cost를 매우 낮게 책정:

```c
// 메모리 테이블 비용 모델
double memory_table_scan_cost(int row_count) {
  return row_count * MEMORY_ROW_COST;   // disk I/O 0
}
```

PK = 상수 조건이 있으면 자동으로 `key_lookup_mode = 1`로 plan 생성.

**카디널리티/통계 전략**:

- `row_count`: registry의 `t->row_count.load()` 실시간 값 사용 (카탈로그 미수집).
- 컬럼별 distinct count, 히스토그램 등 다른 통계: **MVP에서 미수집**. optimizer는 default selectivity로 fallback (예: `=` 조건 1/row_count, 비등치 0.5 등 기존 default).
- JOIN cardinality: 일반 테이블과 JOIN 시 일반 테이블의 카탈로그 통계와 메모리 테이블의 `row_count`만 결합. 메모리 테이블 측 distinct/히스토그램이 없으므로 일반 테이블 통계를 fallback 기반으로 사용.

이 한계는 사용자 가이드에 명시한다 (대형 메모리 테이블의 복잡한 JOIN은 plan이 최적이 아닐 수 있음).

### 4.7 Lifecycle (Week 12)

#### 4.7.1 Server startup

```c
// src/transaction/boot_sr.c:1969 boot_restart_server()
int
boot_restart_server (THREAD_ENTRY * thread_p, bool print_restart, const char *db_name, bool from_backup,
                     CHECK_ARGS * check_coll_and_timezone, BO_RESTART_ARG * r_args, bool skip_vacuum)
{
  /* ...기존 로직 (volume mount, recovery 등)... */

  /* 메모리 테이블 registry 초기화 — sysparam 값은 byte 단위 BIGINT 그대로 받는다.
   * chunk_size sysparam도 이 시점에 1회 읽어 registry에 고정 (§4.10.1). */
  memory_table_registry_init (
    prm_get_bigint_value (PRM_ID_MEMORY_TABLE_TOTAL_SIZE),
    prm_get_bigint_value (PRM_ID_MEMORY_TABLE_CHUNK_SIZE));

  /* 카탈로그 스캔: SM_CLASSFLAG_MEMORY_TABLE 표시된 클래스를 빈 entry로 등록 */
  catalog_scan_for_memory_tables ();
}
```

#### 4.7.2 Server shutdown

```c
// src/transaction/boot_sr.c::xboot_shutdown_server() (line 3044)
memory_table_registry_shutdown();   // 모든 chunk 해제, registry 정리
```

#### 4.7.3 DROP 처리 — busy-wait 위험 제거 (`#9`)

```cpp
int registry_drop(const OID *class_oid) {
  std::unique_lock reg_lk(registry::instance().m_registry_lock);

  auto it = registry::instance().m_tables.find(*class_oid);
  if (it == registry::instance().m_tables.end()) {
    return ER_MEMORY_TABLE_NOT_FOUND;
  }
  memory_table *t = it->second.get();

  /* CAS로 is_dropped 표시 — 동시 drop 호출 race 방지.
   * 이미 dropped면 다른 호출자가 처리 중이므로 즉시 반환. */
  bool expected = false;
  if (!t->is_dropped.compare_exchange_strong(expected, true,
        std::memory_order_acq_rel)) {
    return ER_MEMORY_TABLE_NOT_FOUND;
  }

  /* registry-level lock 해제 후 활성 스캔 대기. 이 사이 새 scan_start_scan은
   * registry_find_acquire에서 is_dropped를 보고 거절된다. */
  reg_lk.unlock();

  std::int64_t timeout_ms = prm_get_integer_value(PRM_ID_MEMORY_TABLE_DROP_TIMEOUT_MSEC);
  auto deadline = std::chrono::steady_clock::now()
                + std::chrono::milliseconds(timeout_ms);
  while (t->ref_count.load(std::memory_order_acquire) > 0) {
    if (timeout_ms > 0 && std::chrono::steady_clock::now() >= deadline) {
      /* 정리: is_dropped 롤백 후 에러 반환 — 다른 트랜잭션이 다시 시도 가능.
       * is_dropped 롤백도 CAS로 처리해 중복 drop 호출과 race 방지. */
      bool was_dropped = true;
      t->is_dropped.compare_exchange_strong(was_dropped, false,
        std::memory_order_acq_rel);
      return ER_MEMORY_TABLE_DROP_TIMEOUT;
    }
    std::this_thread::sleep_for(std::chrono::milliseconds(10));
  }

  /* registry에서 erase. unique_lock 다시 획득. */
  std::unique_lock reg_lk2(registry::instance().m_registry_lock);
  auto it2 = registry::instance().m_tables.find(*class_oid);
  if (it2 != registry::instance().m_tables.end()) {
    /* unique_ptr가 destructor에서 chunks를 해제. */
    registry::instance().m_tables.erase(it2);
  }
  return NO_ERROR;
}
```

**주요 변경 (`#9`)**:

- `ER_LK_OBJECT_TIMEOUT` 인용 제거 — `src/base/error_code.h`에서 grep한 결과 그 이름의 코드는 존재하지 않으며, `ER_LK_OBJECT_TIMEOUT_SIMPLE_MSG` 등 일반 lock timeout류는 lock manager 전용이라 메모리 테이블 DROP 의미와 다르다. **`ER_MEMORY_TABLE_DROP_TIMEOUT` 단독 사용**.
- `is_dropped` 롤백을 plain store가 아닌 **`compare_exchange_strong`**로 처리해 동시 drop과 race 방지.
- registry erase는 unique_lock(m_registry_lock) 보유 상태에서만 — `find_or_acquire`와의 race 차단(§3.4).

`scan_start_scan`은 §4.5.3대로 `registry_find_acquire`에서 lookup + is_dropped 검사 + ref_count 증가가 한 임계구역. `scan_end_scan`에서 `ref_count.fetch_sub(1)`. timeout sysparam 기본값 `0`(무한 대기)은 long-running scan과 호환을 위함이며, 운영자는 OLAP 워크로드 환경에 맞게 ms 단위로 설정.

### 4.8 Error Codes (Week 1, 분산하여 추가)

현재 `src/base/error_code.h:1758` `ER_AUTO_INCREMENT_SINGLE_COL_ONLY = -1370`이 마지막 코드이고 `ER_LAST_ERROR = -1371` (line 1760). 신규 코드는 `-1371`부터 연속 할당하고 `ER_LAST_ERROR`를 갱신.

```c
// src/base/error_code.h (현 ER_LAST_ERROR 자리에 삽입)
#define ER_MEMORY_TABLE_FULL                       -1371
#define ER_MEMORY_TABLE_PK_DUPLICATE               -1372
#define ER_MEMORY_TABLE_NOT_FOUND                  -1373
#define ER_MEMORY_TABLE_INVALID_DDL                -1374    /* PK 없음 등 */
#define ER_MEMORY_TABLE_LOB_NOT_SUPPORTED          -1375
#define ER_MEMORY_TABLE_NOT_IMPLEMENTED            -1376    /* 첫 PR placeholder */
#define ER_MEMORY_TABLE_NOT_SUPPORTED_IN_SA_MODE   -1377
#define ER_MEMORY_TABLE_DROP_TIMEOUT               -1378

#define ER_LAST_ERROR                              -1379    /* was -1371 */
```

(번호는 실제 작업 시점의 최신 `ER_LAST_ERROR`에 맞춰 재계산.)

CLAUDE.md 규칙대로 `dbi_compat.h`, `cubrid.msg` (en/ko), CCI submodule `cubrid-cci/src/cci/base_error_code.h`도 동기화. CCI submodule 동기화는 §2.8 비고대로 **별도 PR**로 분리한다 (`#21`).

### 4.9 INFORMATION_SCHEMA (Week 13-14)

`db_class` 시스템 테이블에 `is_memory` 컬럼 노출:

```sql
SELECT class_name, is_memory FROM db_class WHERE class_type = 'CLASS';
```

`schema_system_catalog_install.cpp`와 `*_install_query_spec.cpp` 수정.

### 4.10 System Parameters

`src/base/system_parameter.h`의 `PRM_ID_*` enum 끝부분(현재 `PRM_ID_LOG_POSTPONE_CACHE_SIZE`가 마지막, line 529)에 신규 ID를 추가하고 `PRM_LAST_ID = PRM_ID_LOG_POSTPONE_CACHE_SIZE` (line 532)를 갱신.

```c
// src/base/system_parameter.h
PRM_ID_MEMORY_TABLE_TOTAL_SIZE,             /* default 256M, max 64G — PRM_BIGINT, byte 단위, startup-only */
PRM_ID_MEMORY_TABLE_MAX_PER_TABLE,          /* default 64M           — PRM_BIGINT, byte 단위, runtime-changeable */
PRM_ID_MEMORY_TABLE_CHUNK_SIZE,             /* default 64K           — PRM_BIGINT, byte 단위, startup-only */
PRM_ID_MEMORY_TABLE_COMPACT_THRESHOLD_PCT,  /* default 0 (=disabled), max 100 — PRM_INTEGER, runtime-changeable */
PRM_ID_MEMORY_TABLE_DROP_TIMEOUT_MSEC,      /* default 0 (=무한)             — PRM_INTEGER, ms, runtime-changeable */
PRM_LAST_ID = PRM_ID_MEMORY_TABLE_DROP_TIMEOUT_MSEC
```

`system_parameter.c`의 `prm_*` 정의 테이블, `cubrid.conf` 템플릿 등록, online change 가능 여부 표식 동기화. byte 단위 sysparam은 CUBRID 표준 suffix(`K`/`M`/`G`)를 conf 파일에서 그대로 받는다.

#### 4.10.1 chunk size 결정

`memory_table_chunk_size`는 **registry 초기화 시 1회 결정되며 그 후 모든 chunk가 동일 크기**로 사용된다. 즉 **컴파일 타임 상수가 아니라 런타임 결정 상수**다. `memory_chunk::SIZE`는 `static constexpr`로 두지 않고, `memory_chunk` 생성 시 sysparam 값을 받아 `data`를 동적 할당한다. 한 번 결정된 chunk size는 서버 lifetime 동안 고정.

#### 4.10.2 chunk_size sysparam의 startup-only 강제 (`#11`)

`memory_table_chunk_size`와 `memory_table_total_size`는 registry 초기화 후 변경하면 정합성이 깨지므로 startup-only로 강제한다. 구현:

- `system_parameter.c`의 `prm_def`에서 두 파라미터에 **`PRM_FOR_SERVER` 플래그만** 부여하고 `PRM_USER_CHANGE`/`PRM_FOR_SESSION`은 부여하지 않는다. 클라이언트가 `SET SYSTEM PARAMETERS chunk_size = 128K`을 보내면 CUBRID 표준 sysparam dispatch가 `PRM_USER_CHANGE` 누락을 보고 `ER_PRM_BAD_VALUE` 또는 동등 에러로 거절한다.
- `cubrid.conf`에서만 변경 가능. 변경은 서버 재시작 후 적용.

> **주의**: `ER_PRM_CANNOT_CHANGE_AT_RUNTIME`은 `src/base/error_code.h` grep 결과 코드베이스에 존재하지 않으므로 인용하지 않는다. CUBRID는 런타임 변경 거절을 `ER_PRM_BAD_VALUE`(`-839`) 등 기존 에러로 처리한다 — 정확한 거절 에러는 PoC 시 확정.

---

## 5. 트랜잭션 의미론 (요약)

| 동작 | 의미 |
|---|---|
| `INSERT INTO mtbl ...` | 즉시 가시화. 동시 트랜잭션 ROLLBACK과 무관. row-level commit. |
| `UPDATE mtbl ...` | 동일. read-uncommitted-equivalent |
| `DELETE FROM mtbl ...` | 동일 |
| Multi-row statement 부분 실패 | 이미 적용된 row 보존, 이후 row만 미적용 (statement atomicity 없음) |
| `CREATE MEMORY TABLE` | 일반 트랜잭션 + WAL 카탈로그 + **즉시 global registry 등록** (v3 결정). ROLLBACK 시 카탈로그 복구되며 registry entry는 폐기 (row 같이 폐기) |
| `DROP TABLE mtbl` | 일반 트랜잭션 + WAL 카탈로그. 활성 스캔이 있으면 deferred free. **ROLLBACK 시 카탈로그 복구되며 registry entry/data 모두 그대로 보존** (v3 결정 — `#13`) |
| 서버 재시작 | 데이터 wipe. 카탈로그는 유지 |
| 트랜잭션 내 SELECT (메모리 테이블) | 다른 세션의 row-level commit된 INSERT/UPDATE 즉시 보임 (read-uncommitted-equivalent). `SET TRANSACTION ISOLATION LEVEL`은 메모리 테이블에 **영향 없음** (`#23`) |
| 트랜잭션 내 SELECT (일반 테이블 + 메모리 테이블 JOIN) | 일반 테이블 부분은 자기 트랜잭션의 MVCC snapshot, 메모리 테이블 부분은 read-uncommitted-equivalent — **격리 모델이 한 쿼리 내에 혼재**한다. 사용자 가이드 강조. |

---

## 6. 동시성 및 락

| 시나리오 | 보호 방식 |
|---|---|
| INSERT vs INSERT (같은 테이블) | `unique_lock(table.rw_lock)` 직렬화 |
| SELECT vs SELECT (같은 테이블) | `shared_lock(table.rw_lock)` 병렬. `pk_index` 등 모든 read는 shared_lock 하에서만. zero-copy를 위해 **scan-lifetime 보유** (`#8`) |
| INSERT vs SELECT | RW lock 정상 동작. SELECT가 진행 중이면 INSERT 대기 (zero-copy의 trade-off) |
| Long-running scan 중 INSERT | **차단됨**. OLAP 워크로드의 받아들이는 비용. 후속에서 scan-batch lock 모드 sysparam 검토 (§4.3.2) |
| PK lookup scan | `shared_lock(rw_lock)` 보유 상태에서 unordered_map::find. lock 없이 read 금지 |
| DROP vs SELECT | `is_dropped` + `ref_count` 패턴 (§4.5.3, §4.7.3). DROP은 timeout sysparam 적용. registry-level shared_lock으로 lookup→ref_count 증가 atomic (`#2`) |
| Registry 조회 | MVP는 `std::shared_mutex + std::unordered_map`. lockfree 전환은 Phase 2.1 (`#1`) |
| 메모리 한도 체크 | `total_bytes_used`는 atomic compare_exchange 루프로 race 없이 예약 (§4.3.3) |
| tombstone bit set/clear | `std::atomic<std::uint64_t>::fetch_or/and` (lock과 별개) |
| tombstone bitmap grow | `unique_lock(table.rw_lock)` 보유 상태에서 `std::deque::emplace_back` (`#4`) |

---

## 7. 테스트 전략

> **테스트 디렉토리 표준은 PR 작업 시점에 grep으로 재확인 필수**. 본 절은 CUBRID 기존 sql/regression 디렉토리 표준에 부합하도록 권장 위치를 적되, 실제 위치는 `find . -name "*.answer" -o -name "*.ctl"` 결과를 기준으로 1주차에 확정.

### 7.1 Unit tests (Catch2, `unit_tests/storage/`)

- `memory_table_basic_test.cpp`: chunk 할당, INSERT, lookup, DELETE
- `memory_table_concurrency_test.cpp`: 다중 스레드 INSERT/SELECT/DELETE race
- `memory_table_oom_test.cpp`: 한도 초과 시 `ER_MEMORY_TABLE_FULL`
- `memory_table_pk_test.cpp`: 단일/복합 PK, 중복 거절
- `memory_table_drop_test.cpp`: 활성 스캔 중 DROP, deferred free, timeout 검증, is_dropped CAS rollback race
- `memory_table_scan_id_size_test.cpp`: SCAN_ID union sizeof 회귀 + `static_assert` (§4.5.2)
- `memory_table_statement_abort_test.cpp`: statement abort 콜백이 메모리 테이블 row를 건드리지 않음 (`#7`, Week 8 산출물)

### 7.2 SQL regression — CUBRID `sql/` 표준

CUBRID 기존 sql 회귀 표준은 케이스를 디렉토리별로 묶고 `.sql` ↔ `.answer` 짝을 유지한다. 권장 배치(실제 디렉토리는 1주차 확정):

```
sql/
  _01_memory_table_create_drop/
    cases/01_create_basic.sql          + .answer
    cases/02_drop_basic.sql            + .answer
  _02_memory_table_dml/
    cases/01_insert_select.sql         + .answer
    cases/02_update_delete.sql         + .answer
    cases/03_pk_uniqueness.sql         + .answer
    cases/04_oom.sql                   + .answer
  _03_memory_table_join/
    cases/01_join_with_regular.sql     + .answer
```

> 실제 표준이 다르면(예: `tests/sql/_xx_yyyy/`) 그 표준에 맞춘다. 이 결정은 작업 시작 시 1차 PR로 합류.

### 7.3 Isolation tests (`.ctl`)

CUBRID isolation 테스트는 별도 위치에 다중 세션 시나리오를 `.ctl` 형식으로 둔다. 본 작업 worktree에는 `.ctl` 파일이 없으므로 (별도 testcase 저장소 가능성), **작업 시작 시 `find` 또는 `cubrid-isolation-test` 스킬로 정확한 디렉토리를 확정** (`#20`)한 뒤 합류한다.

- `memory_table_concurrent_insert.ctl`: 두 세션 동시 INSERT, row-level commit 검증
- `memory_table_uncommitted_visibility.ctl`: 세션 A의 막 적용된 INSERT가 세션 B에 즉시 보이는지 (read-uncommitted-equivalent)
- `memory_table_drop_during_scan.ctl`: 활성 SELECT 중 DROP 시도 → DROP은 ref_count == 0까지 대기, 또는 timeout 시 거절
- `memory_table_create_rollback_visibility.ctl`: 세션 A의 `CREATE MEMORY TABLE` 후 commit 전 세션 B에서 INSERT/SELECT 가능 (v3 결정안 검증, `#3`)
- `memory_table_drop_rollback_preserve.ctl`: `DROP TABLE` 후 ROLLBACK → 데이터 그대로 보존 (v3 결정안 검증, `#13`)

### 7.4 Performance benchmark — KPI는 baseline 측정 후 확정 (`#10`)

- 단일 노드 64GB, 1천만 행, 50바이트 행, AI 보조 환경 표준 하드웨어
- **Week 15 baseline 측정 후 KPI 확정**: 일반 row store에서 동일 워크로드의 PK 단일 조회 throughput, full scan throughput, INSERT throughput을 먼저 측정해 baseline을 확보. 이후 메모리 테이블 KPI는 그 baseline 대비 *상대적 개선*으로 정의한다 (절대 배수 ×5 등 임의 가정 제거).
- **정성 KPI** (baseline 무관 사전 합의):
  - PK 단일 조회 p95 latency가 **disk I/O 1회 미만**일 것 (memory disk-bypass의 자명한 우위 확인). 구체 µs 임계는 baseline 측정 후 확정.
  - Full scan throughput이 row store baseline보다 **유의하게 빠름**(통계적 신뢰구간 기준). 배수는 측정 후 확정.
  - 일반 row store의 일반 INSERT/UPDATE/DELETE throughput 회귀 **<1%** (메모리 테이블 dispatch 캐시 도입이 일반 경로를 거의 건드리지 않음, `#14`).
- p95와 p99를 동시 측정해 변동성 한계 점검.
- 측정 도구: 자체 micro-benchmark + sysbench 어댑터.

비교 baseline: 동일 schema, 동일 row를 일반 row store에 적재한 결과.

### 7.5 HA/backup skip 검증 — 구체 통합 지점 (`#17`)

- **HA**: HA 활성 환경에서 `CREATE MEMORY TABLE` → 슬레이브 노드에 카탈로그만 복제 (DDL은 일반 WAL이므로 자동), 데이터는 무관. 검증: 마스터에서 INSERT 후 슬레이브에서 SELECT 시 빈 결과. 통합 지점: replication apply 경로에서 `SM_CLASSFLAG_MEMORY_TABLE` 클래스의 row apply를 자동 skip하도록 가드. **정확한 위치는 `src/transaction/log_applier.c` 내 `la_apply_insert_log`/`la_apply_update_log`/`la_apply_delete_log`/`la_apply_statement_log` (`log_applier.c:524-529`)** — `src/connection/heartbeat.c`는 노드 상태 관리이므로 row apply 경로가 아니다 (v2 인용 정정). 작업 시 grep으로 정확한 함수 진입 직후를 확정.
- **Backup**: `cubrid backupdb` → 메모리 테이블의 카탈로그는 일반 catalog 페이지의 일부이므로 backup 대상. 데이터는 휘발 영역이라 디스크에 없으므로 자연 제외. **별도 통합 작업은 `is_memory` 플래그를 backup 메시지에 포함해 사용자에게 "이 테이블은 데이터 없이 카탈로그만 백업됨"을 안내하는 것이 핵심**. 검증 sql/script: `tests/backup/memory_table_skip.sh` (가칭) — backup → restore → SELECT 시 빈 결과 확인.

### 7.6 Restart wipe 검증

- INSERT → 서버 재시작 → SELECT가 빈 결과 반환

---

## 8. 일정 (1명 기준, 14~28주, AI-assisted, conservative)

LOC 환산: 2,500~4,600 LOC ÷ (200~300 LOC/주) = 약 8~25주. 통합/리뷰/회귀 보정 +6~8주 = **14~28주**. 12주 하한은 R1 hook PoC 1주차 완료, R2 PoC 6주차 완료, 리뷰 라운드 1회 등 모든 가정이 동시 성립해야 가능하므로 **현실적 하한은 14주**로 상향. 상한은 리뷰 라운드 3~4회와 R1/R2 PoC 실패 mitigation을 모두 반영해 28주.

| Week | 산출물 | 검증 게이트 |
|---|---|---|
| 0 | **R1 트랜잭션 commit/rollback hook spike** (별도, `#12`) | hook 후보 5개(log_commit_local, log_abort_local, logtb_complete_mvcc, log_complete, log_sysop_end_logical_undo) 중 1개 PoC 통과 |
| 1 | Catalog flag 추가 (`SM_CLASSFLAG_MEMORY_TABLE = 32`), 직렬화 round-trip 점검, error code 6곳 갱신 (placeholder 포함). Week 0 spike 결과를 본 일정에 반영. | flag bit 32-bit round-trip unit test 통과 |
| 2 | PT_NODE 비트필드, semantic_check 골격 | smoke 컴파일, 카탈로그 flag set 후 reload 시 비트 보존 |
| 3-4 | memory_chunk, memory_table, registry 골격(`std::shared_mutex + unordered_map`) | INSERT 1건 → SELECT 1건 (full scan만) |
| 5 | OR_BUF / RECDES 직렬화 통합, `memory_row_ref::length` 캐시 | 다양한 DB_VALUE 타입 unit test |
| 6 | **R2 PK 키 정규화 PoC**, PK hash index, btree_compare_key 통합 (또는 신규 헬퍼), pk_descriptor 1회 빌드 | PK uniqueness 단위 테스트 |
| 7 | INSERT 분기 (locator_*) + dispatch 캐시 | 일반 SQL INSERT가 memory table에 도달, 일반 INSERT 회귀 <1% |
| 8 | DELETE + statement abort 콜백 검증 (`#7`) | DELETE → SELECT 빈 결과, abort 콜백이 메모리 테이블 row 미건드림 |
| 9 | UPDATE (in-place + 재배치) | UPDATE 결과 SELECT 검증 |
| 10 | SCAN_TYPE, SCAN_ID 멤버 추가, scan_init/next/end, **union sizeof static_assert + 회귀 테스트** | 옵티마이저 미통합 상태로 EXPLAIN 검증 |
| 11 | Grammar `CREATE MEMORY TABLE` 풀 통합, 옵티마이저 cost model, PK lookup plan, MEMORY 키워드 회귀 보존 케이스 | EXPLAIN이 memory_table_scan을 선택; 기존 컬럼명 `memory` 사용 스크립트 통과 |
| 12 | DROP, deferred free, timeout sysparam, 트랜잭션 commit/rollback 콜백 통합 (v3 결정안 §4.4.3) | DROP 중 SELECT 동시 실행 unit test, DROP timeout test, DROP+ROLLBACK 데이터 보존 isolation test |
| 13 | Server startup/shutdown registry, sysparam 등록 (chunk_size startup-only 검증) | 재시작 wipe 검증, runtime SET 거절 검증 |
| 14 | INFORMATION_SCHEMA, sysparam 단위 검증, 회귀 1차, **cubrid-cci submodule PR 별도 제출** (`#21`) | catalog query 검증, CCI client에서 신규 에러 코드 가시 |
| 15 | **Performance baseline 측정** (일반 row store 기준), KPI 확정 (`#10`) | baseline 표가 산출물로 등재 |
| 16 | HA/backup skip 검증 (log_applier.c 통합), regression 전체, 메모리 테이블 vs row store 비교 | KPI(§7.4) 충족 또는 deviation 분석 |
| 17-19 | 코드 리뷰 1차 대응 | 리뷰어 동의 |
| 20-23 | 코드 리뷰 2차 대응, R1/R2 mitigation 반영 | 리뷰어 동의 |
| 24-28 | 코드 리뷰 3차 대응, merge 준비 | merge ready |

**하한 시나리오 (14주)**: SCAN 단순 full scan only, optimizer 통합 최소(고정 cost), regression 영역 축소, R1/R2 PoC 즉시 성공, 리뷰 라운드 1회. 출시 품질은 낮음.
**상한 시나리오 (28주, conservative)**: 위 일정 + R1/R2 PoC 실패 mitigation +4주. 리뷰 라운드 3~4회.

**R1 실패 시 자동 fallback 결정안** (`#12`): Week 0 spike에서 다섯 후보 모두 hook 통합이 불가하면, fallback으로 **CREATE/DROP DDL 직후 client에서 explicit `COMMIT`을 강제**하는 방식을 채택한다(`do_create_entity` 끝에서 internal commit 호출). 이는 PostgreSQL의 일부 DDL과 유사한 의미론. 단점: DDL이 트랜잭션과 분리되어 사용자 가이드에 추가 강조 필요. fallback 결정으로 일정은 +1~2주만 영향.

---

## 9. 미해결 이슈 결정안

### 9.1 결정안 (본 문서에서 확정)

> **§9 미해결 이슈는 Issue 1, 2, 3, 4, 5의 다섯 항목이 전부**다 (`#18`). 신규 이슈는 본 문서가 추적하는 한 없으며, 발견되면 v4 개정 시 추가한다.

#### Issue 1. CREATE MEMORY TABLE 후 ROLLBACK 시 registry 처리 (v3에서 결정안 변경)

**v3 결정**: §4.4.3에서 (b) **즉시 등록 + rollback 시 deferred drop 호출 안 함**으로 변경. 이중 lookup 비용 제거, DROP+ROLLBACK 비대칭 해소.

| 대안 | (a) thread-local pending registry + commit 시 merge (v2) | **(b) 즉시 global 등록 + ROLLBACK에서 drop 호출 안 함 (v3 채택)** |
|---|---|---|
| 구현 복잡도 | 중 (thread-local 컨테이너 + commit hook) | 낮 (등록 콜백만) |
| 이중 lookup | 있음 | **없음** |
| 사용자 가시 | 트랜잭션 내 자기 세션만 보이고 commit 후에 다른 세션에 가시 | 다른 세션에서 미커밋 테이블이 잠시 보임 — read-uncommitted-equivalent 격리이고 본 모델과 일관 |
| DDL+DML 같은 트랜잭션 | thread-local에서 동작. ROLLBACK 시 자기 세션 데이터도 폐기 | 즉시 global 등록되므로 같은 세션 DML이 즉시 적용; ROLLBACK 시 카탈로그만 복구되고 row 보존 — §4.4.3 ROLLBACK 보존 규칙과 일관 |

**(b)를 1차 채택**. `#3`, `#13` 비판에 따라 v2의 (a) 결정을 뒤집음.

#### Issue 2. DROP 중 동시 SCAN

**결정**: `is_dropped` 플래그 + `ref_count` 조합. DROP은 `is_dropped` CAS로 표시 후 `ref_count == 0`까지 대기 후 실제 free. 새 SCAN은 `registry_find_acquire` 한 임계구역에서 lookup→is_dropped 검사→ref_count 증가. **DROP은 `memory_table_drop_timeout_msec` sysparam(default 0=무한)으로 timeout 적용**. timeout 시 `ER_MEMORY_TABLE_DROP_TIMEOUT` 반환 (`ER_LK_OBJECT_TIMEOUT` 등 lock manager 코드는 사용하지 않음, `#9`).

**대안**: shared_mutex 단독 — DROP이 무한 대기 가능. 채택 안 함.

#### Issue 4. 카탈로그 영속 + 데이터 휘발 모델의 사용자 혼란

**결정**: 다음 3중 가시화로 사용자 인지 강제.

1. INFORMATION_SCHEMA `db_class.is_memory` 컬럼 노출
2. `SHOW CREATE TABLE`에 `MEMORY` 키워드 표시
3. 서버 startup 시 메모리 테이블 발견하면 server log에 `INFO: Memory table 'foo' restored as empty` 출력

**대안**: 서버 startup 시 메모리 테이블 카탈로그 자동 삭제 — DDL 스크립트를 매 부팅마다 재실행해야 하는 부담. 채택 안 함.

### 9.2 구현 단계 결정으로 미룸

#### Issue 3. PK 키 정규화

`btree_compare_key` (`src/storage/btree.h:904` 선언 — `DB_VALUE *key1, DB_VALUE *key2, TP_DOMAIN *key_domain, ...`) 재사용을 권장하되, 실제 함수가 in-memory 컨텍스트(page_buffer/heap 의존 없음)에서 직접 호출 가능한지 Week 6에 PoC 후 확정. 호환 안 되면 별도 정규화 함수 작성 (+4~6주, §3.2 안 (B) reserve).

#### Issue 5. SERVER_MODE vs SA_MODE

**결정**: 1차 SERVER_MODE 전용. SA_MODE 빌드에서 `CREATE MEMORY TABLE` DDL 실행 진입 시 `ER_MEMORY_TABLE_NOT_SUPPORTED_IN_SA_MODE` 즉시 반환. grammar는 동일하게 받아 (lexer/parser 분기 없이) DDL 실행 단계 (`do_create_entity`)에서 `#if defined(SA_MODE)` 가드로 거절. 이유: grammar 분기를 두면 양 모드의 SQL 문법 표면이 달라지는 회귀 위험.

CSQL 인터랙티브에서의 lifecycle은 SA_MODE 자체 특성상 자연스럽지 않으므로 Phase 2.1에서 재검토.

---

## 10. 리스크 및 대응

| ID | 리스크 | 영향 | 확률 | Mitigation |
|---|---|---:|---:|---|
| R1 | 트랜잭션 commit/rollback hook 위치 미확정 | 큼 | 중 | **Week 0 별도 spike** + Week 1 본 task (`#12`). 다섯 후보(log_commit_local, log_abort_local, logtb_complete_mvcc, log_complete, log_sysop_end_logical_undo) 중 통과 가능한 hook 1개 확정. 모두 실패 시 **자동 fallback 결정안 (§8 마지막)**: DDL 직후 internal commit 강제. +1~2주 영향 |
| R2 | btree_compare_key가 in-memory 컨텍스트에서 직접 호출 불가 | 중 | 중 | Week 6 PoC. 실패 시 별도 정규화 함수 작성 (+4~6주, §3.2 reserve) |
| R3 | OR_BUF 직렬화가 page header 의존 → memory chunk에서 부적합 | 중 | 중 | Week 5 PoC. 실패 시 직접 시리얼라이저 작성 (+1~2주) |
| R4 | PR 리뷰 라운드 4회 초과 | 중 | 중 | 일정 24-28주를 리뷰 버퍼로. 리뷰어 사전 협의 |
| R5 | 메모리 단편화로 long-running 서버에서 chunk 낭비 | 낮음 | 중 | compaction sysparam 노출 (default 0=disabled). Phase 2.1에서 본격 |
| R6 | parallel heap scan(PR #7040)과의 통합 누락 → 메모리 테이블이 항상 직렬 스캔 | 낮음 | 높음 | Phase 2 MVP는 직렬 스캔 허용. Phase 2.1에서 parallel memory scan 검토 |
| R7 | read-uncommitted-equivalent 격리로 사용자 컴플레인 | 중 | 중 | 사용자 가이드 강조 + INFORMATION_SCHEMA 표식 + log warning |
| R8 | LOB 컬럼 거절이 사용 사례 차단 | 낮음 | 낮음 | 거절 메시지에서 일반 VARCHAR 권장 |
| R9 | SM_CLASS_FLAG enum 비트 폭이 8비트로 직렬화되고 있을 가능성 | 큼 | 낮음 | Week 1 점검 항목. `or_put_int`로 32-bit 직렬화임이 확인되었으나 round-trip unit test 필수 |
| R10 | SCAN_ID union sizeof 증가로 인한 메모리 회귀 | 중 | 낮음 | 헤비 멤버 heap 포인터화 + sizeof static_assert + 회귀 테스트 (§4.5.2, `#6`, `#15`) |
| R11 | Long-running scan이 INSERT를 차단해 mixed 워크로드 성능 저하 | 중 | 중 | scan-batch lock 모드 sysparam을 후속 작업으로 등재 (§4.3.2). MVP는 zero-copy + scan-lifetime lock 채택 (§6) |
| R12 | hash flooding 공격으로 PK index O(N²) 퇴화 | 낮음 | 낮음 | 권한 있는 사용자만 접근 가능하므로 위협 낮음. SipHash 기반 randomized hasher를 후속 작업으로 등재 (§3.2.1, `#24`) |
| R13 | CCI submodule 릴리스 주기 불일치로 client-visible 에러 코드 노출 지연 | 중 | 중 | CCI submodule용 별도 PR 분리 제출 (§2.8, §4.8). 그 사이 server는 generic `CCI_ER_DBMS`로 fallback (`#21`) |

---

## 11. 첫 PR 후보 (Week 1 산출물, 좁힘)

> **PR 제목**: `[CBRD-XXXXX] Add SM_CLASSFLAG_MEMORY_TABLE catalog flag and serialization round-trip test`

첫 PR의 범위는 두 옵션 중 (b)를 권장. dead flag만 두는 (a)는 grammar/PT/회귀 영향이 0이지만 후속 PR 검토 시 dead code로 보일 위험이 있어 smoke test가 필요하다(`#25`).

| 옵션 | (a) flag만 추가 | **(b) flag + grammar non-reserved + PT bit + smoke test (권장)** |
|---|---|---|
| 변경 범위 | `class_object.h` flag, 헬퍼, 직렬화 round-trip unit test | (a) + `csql_lexer.l`/`csql_grammar.y` non-reserved keyword + `parse_tree.h` PT bit + `do_create_entity` 진입점에서 PT bit를 받아 `template_->flags |= SM_CLASSFLAG_MEMORY_TABLE` 1줄 set, smoke regression `CREATE MEMORY TABLE t (id INT PRIMARY KEY); DROP TABLE t;` (registry 미통합 → 빈 entry도 생성 안 함, 카탈로그만) |
| 리뷰 부담 | 매우 낮음 (1 파일 변경) | 낮음 (5 파일 변경, but 핵심 회귀 차단) |
| 리뷰어가 검증 가능한 것 | flag bit 직렬화 round-trip만 | flag bit + grammar 회귀 보존 (기존 `memory` 컬럼명 사용 가능) + PT bit가 카탈로그까지 흐름 |
| 사후 dead code 위험 | 있음 (flag만 만들고 사용처 없음) | 없음 (PT bit가 카탈로그에 set되는 1줄까지 포함) |

**(b)를 권장 — 본 문서 채택 (`#25`)**.

**범위 (의도적으로 좁힘, (b) 기준)**:
- `class_object.h`에 `SM_CLASSFLAG_MEMORY_TABLE = 32` flag 추가
- `class_object.h`에 `sm_is_memory_table()` inline 헬퍼 추가
- `transform_cl.c::class_to_disk()` (line 3782) round-trip unit test (`or_put_int (buf, class_->flags)` 동작 검증)
- `unit_tests/object/sm_classflag_memory_table_test.cpp` (Catch2) — flag set 후 직렬화/역직렬화 시 비트 보존 검증
- `csql_lexer.l`, `csql_grammar.y`에 `MEMORY` non-reserved 키워드 추가
- `parse_tree.h::pt_create_entity_info`에 `is_memory_table:1` 비트필드 추가
- `do_create_entity()`에 PT bit → `SM_CLASSFLAG_MEMORY_TABLE` set 1줄
- Smoke regression: `CREATE MEMORY TABLE t (id INT PRIMARY KEY); SELECT class_name FROM db_class WHERE class_name = 't'; DROP TABLE t;` (DML/registry 미포함이므로 INSERT/SELECT는 후속 PR)
- 회귀 보존 케이스: `CREATE TABLE t (memory INT)` 통과, `SELECT memory FROM t` 컬럼 참조

**범위 외 (후속 PR 시리즈)**:
- registry, scan, DML 분기 — 후속 PR 시리즈
- 트랜잭션 commit/rollback hook 통합 — Week 12 PR
- HA/backup 통합 — Week 16 PR
- CCI submodule 에러 코드 — Week 14 별도 PR (§2.8)

**의도**: 1주차 PR을 catalog flag + grammar non-reserved keyword + PT bit + 1줄 set으로 한정해 후속 PR이 본 PR의 dead code 우려 없이 점진적으로 grammar → PT → DDL 분기 → registry → scan → DML 순으로 합류.

---

## 12. 관련 문서

- 전략 로드맵: `htap_olap_roadmap.md`
- CUBRID 코딩 스타일: `CLAUDE.md` (root)
- CUBRID 메모리 관리: `src/base/memory_alloc.h`, `src/base/memory_wrapper.hpp`
- 기존 list_file 메커니즘 (참고): `src/query/list_file.h`, `src/query/list_file.c` (`qfile_*` API)
- 기존 lockfree 인프라 (Phase 2.1 참고): `src/base/lock_free.{h,c}` (`LF_HASH_TABLE`), `src/base/lockfree_hashmap.{hpp,cpp}` (`namespace lockfree`)
- 트랜잭션 commit/rollback hook 후보: `src/transaction/log_manager.c::log_commit_local` (line 5156), `log_abort_local` (line 5274), `logtb_complete_mvcc` (호출 line 5173/5302/5320), `log_complete` (line 5650), `log_sysop_end_logical_undo` (line 3938)
- HA replication apply 경로: `src/transaction/log_applier.c::la_apply_*_log` (line 524-529)
- SCAN_ID union 정의: `src/query/scan_manager.h:402-413`
- SM_CLASS flag set 패턴: `src/object/schema_manager.c:3071,3135`

---

## 13. 후속 작업 (Phase 2.1 이후 검토)

- Secondary index (hash 또는 skiplist)
- Range scan optimization
- Parallel memory table scan (PR #7040 통합)
- ALTER MEMORY TABLE
- AUTO_INCREMENT 지원
- Compaction daemon 자동 운영 (sysparam threshold > 0)
- SA_MODE 지원
- HA replication (선택적)
- Backup snapshot 옵션 (메모리 테이블을 정기적으로 디스크 dump)
- 컬럼별 통계 수집 (distinct, 히스토그램) → optimizer 향상
- Lockfree registry 마이그레이션 (lf_entry_descriptor + tran::system + tran::index 통합, `#1`)
- Scan-batch lock 모드 sysparam (long-running scan과 INSERT 공존, `#8`, R11)
- PK index hash randomization (SipHash) — hash flooding 대응 (`#24`, R12)

---

*문서 끝.*
