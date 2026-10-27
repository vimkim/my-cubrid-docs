# CBRD-26357: OOS 엔진 PR #7990 설명

작성일: 2026-10-27 (Asia/Seoul). 작성: `claude`.

| 항목 | 값 |
| --- | --- |
| PR | [CUBRID/cubrid#7990](https://github.com/CUBRID/cubrid/pull/7990) `[CBRD-26357] Add out-of-row overflow storage` |
| 브랜치 | `feature/oos-merge` → `develop` |
| head | `5a70787feea9e0488222af7e3a0249cc431562ca` (develop `4781495f0`까지 머지됨) |
| 변경 규모 | 149개 파일, +34,740 / −902 (테스트 `unit_tests/oos/` 약 22,000줄 포함) |
| 기준 명세 | [OOS-CONTEXT.md](https://github.com/vimkim/cubrid-oos-context/blob/c6fc51b/OOS-CONTEXT.md) (2026-10-08), [ADR 목록](https://github.com/vimkim/cubrid-oos-context/tree/c6fc51b/docs/adr) |

이 문서의 `path:line`은 모두 head `5a70787fe` 기준입니다. "구현됨"은 그 리비전의 코드를 읽어 확인했다는 뜻이고, 실행 확인은 [Test Plan](#test-plan)에 따로 적었습니다.

**상태 갱신 (2026-10-27):** PR head는 이후 `dcbf09e4f7fd02ff9c8fc6493ec8887fc2919d67`이 되었습니다. `5a70787fe` 뒤에 커밋 5개가 추가되었습니다.

- `224104a36`, `4408135c0`(Greptile 4차 리뷰 P1 처리), `dcbf09e4f`(fixture 등록 비교 수정)는 `unit_tests/oos`의 테스트 스크립트와 CTest 설정만 바꿨습니다.
- `1e8701b4f`, `d8ed97f77`은 엔진을 바꿨습니다. 시작할 때 첫 볼륨의 저장 형식 번호를 검사해 다른 형식의 DB를 거부하고([호환성](#호환성)), `PAGE_OOS`·`PERF_PAGE_OOS`를 각 enum의 `PAGE_VACUUM_DATA`·`PERF_PAGE_VACUUM_DATA` 뒤로 옮겼습니다. 이 검사의 CTest 항목(`test_oos_storage_format_guard`)과 DB fixture 2개가 추가되어 CTest 항목은 44개입니다.

그 밖의 엔진 설명은 그대로 유효합니다. `path:line`은 계속 `5a70787fe` 기준이며, `1e8701b4f`·`d8ed97f77`이 바꾼 엔진 파일(`boot_sr.c`, `disk_manager.c`, `page_buffer.c`, `storage_common.h`, `perf_monitor.h` 등)의 줄 번호는 현재 head와 다를 수 있습니다. [Test Plan](#test-plan), [호환성](#호환성), [알려진 미해결 사항](#알려진-미해결-사항)은 `dcbf09e4f` 기준으로, [테스트](#12-테스트)는 `4408135c0` 기준으로 갱신했습니다.

## Purpose

### 무엇을 하는 PR인가

OOS(Out-of-row Overflow Storage)는 행(heap record) 안의 큰 가변 길이 값을 테이블마다 하나씩 있는 별도 파일(OOS 파일)로 옮기고, 행에는 그 값의 위치 정보만 남기는 기능입니다. PostgreSQL의 TOAST와 비슷한 생각입니다.

- **AS-IS:** 큰 `VARCHAR`, `BIT VARYING`, LOB locator 같은 값이 행 안에 그대로 들어갑니다. 한 페이지에 들어가는 행 수가 적어지고, 작은 컬럼만 읽어도 큰 값이 있는 페이지를 읽어야 합니다. 페이지보다 큰 행은 여러 페이지에 걸친 overflow 레코드(`REC_BIGONE`)가 됩니다.
- **TO-BE:** 행이 정해진 크기를 넘으면 큰 값부터 하나씩 OOS 파일로 옮깁니다. 행에는 24바이트 stub(위치·길이·식별 정보)만 남습니다. 값이 필요한 컬럼만 그때 OOS 파일에서 읽습니다.

### 이 문서의 독자와 범위

- 엔진 PR 리뷰어가 149개 파일을 어떤 순서로 보면 되는지, 각 부분이 무엇을 하는지 알 수 있게 씁니다.
- 명세(OOS-CONTEXT.md)에서 정한 설계와 이 head의 실제 구현을 구분합니다. 명세에는 있지만 아직 구현되지 않은 부분은 [알려진 미해결 사항](#알려진-미해결-사항)에 적었습니다.
- testcase 변경은 [TC PR 변경 내역](CBRD-26357-tc-pr-changes_5a70787_claude.md)에 따로 설명했습니다.

### 이번 머지에 포함하지 않는 것

- **CDC·flashback의 OOS 이력:** [ADR-0005](https://github.com/vimkim/cubrid-oos-context/blob/c6fc51b/docs/adr/0005-defer-oos-history-from-the-11-5-merge.md)에 따라 미뤘습니다(CBRD-26939). 한 번 추가했다가 되돌린 기록이 있습니다(`e7580f671` → `7008beee0`).
- **UPDATE 체인 재사용(CBRD-27230):** 명세에는 채택되었지만 구현되지 않았습니다. 지금은 UPDATE마다 모든 OOS 값을 새로 씁니다.
- 압축, 행 사이 중복 제거, 페이지 간 compaction은 명세에서도 범위 밖입니다.

## Implementation

### 1. 한눈에 보기

```text
heap 파일                                   OOS 파일 (FILE_OOS, 힙마다 최대 1개)
┌──────────────────────────────────────┐    ┌───────────────────────────────────────┐
│ 행: MVCC 헤더(HAS_OOS 플래그)          │    │ page 0: OOS_HDR_STATS (빈 공간 힌트)    │
│     VOT(각 항목에 IS_OOS 비트)          │    │ data page: slotted page               │
│     고정 길이 컬럼                      │    │   chunk 0 ─next─► chunk 1 ─► chunk 2  │
│     가변 길이 컬럼 / 24B stub ─────────┼───►│   (각 chunk = 24B 헤더 + 값 조각)       │
└──────────────────────────────────────┘    └───────────────────────────────────────┘
힙 헤더(HEAP_HDR_STATS)에 oos_vfid 추가 ──────► OOS 파일의 VFID
```

| 영역 | 주요 파일 | 내용 |
| --- | --- | --- |
| OOS 파일 관리 | `src/storage/oos_file.cpp` (신규, 4,083줄), `oos_file.hpp` | chunk 저장·읽기·삭제, 빈 공간 관리, 빈 페이지 반환 |
| 힙 연동 | `src/storage/heap_file.c` (+2,161), `heap_oos.cpp` (신규), `heap_pending_record.hpp` | 어떤 값을 옮길지 결정, stub 쓰기, 값 읽기 |
| DML | `src/transaction/locator_sr.c` (+817) | INSERT/UPDATE/DELETE, 인덱스, FK, 복제 정보 |
| vacuum | `src/query/vacuum.c`, `vacuum_oos.cpp` (신규) | 오래된 행 버전의 OOS 값 정리 |
| 복구·로그 | `recovery.c/h`, `log_record.hpp` | 새 로그 종류 |
| HA 복제 | `src/transaction/log_applier.c` (+1,118) | replica에서 OOS 값 재구성 |
| SQL·도구 | `csql_grammar.y`, `execute_schema.c`, `show_meta.c`, loaddb, unloaddb | `STORAGE` 옵션, `SHOW HEAP OOS` |
| 테스트 | `unit_tests/oos/` | GoogleTest 34개 바이너리 + 스크립트 |

### 2. 저장 형식

- **stub (24바이트):** head OOS OID 8B + 값 전체 길이 8B + 식별 stamp 8B (`OR_OOS_INLINE_SIZE`, `object_representation.h:528`).
- **행 표시:**
  - VOT(가변 길이 컬럼의 위치 표) 항목의 하위 2비트를 플래그로 씁니다. `OR_VAR_BIT_OOS 0x1`은 "이 값은 stub", `OR_VAR_BIT_LAST_ELEMENT 0x2`는 VOT의 끝 표시입니다(`object_representation.h:511-522`). 그래서 모든 VOT offset은 4바이트 정렬이어야 하고, 이 PR은 정렬하지 않던 catalog·client 쓰기 코드도 정렬하게 바꿨습니다(`catalog_class.c:3303, 3316`, `transform_cl.c`).
  - 행 헤더 플래그 `OR_RECORD_FLAG_HAS_OOS 0x08`은 "이 행에 stub이 있다"는 뜻입니다. MVCC 헤더 크기 계산은 하위 3비트만 봅니다.
- **chunk와 체인:** 한 페이지보다 큰 값은 여러 chunk로 나눠 연결 리스트로 저장합니다. 각 chunk 헤더(24B)는 전체 길이, chunk 번호, 다음 chunk OID, 식별 stamp를 담습니다(`oos_file.hpp:32`). 쓸 때는 꼬리부터, 읽을 때는 머리부터 따라갑니다(`oos_insert_across_pages`, `oos_file.cpp:2343`).
- **식별 stamp(CBRD-26950):** chunk를 쓸 때의 페이지 LSA입니다. 읽기와 삭제 전에 stub의 stamp와 head chunk의 stamp를 비교합니다. 슬롯이 재사용되어 다른 값이 들어 있으면 읽기는 `ER_HEAP_OOS_CORRUPTED_RECORD`로 거부하고, 삭제는 아무것도 하지 않습니다(`oos_check_head_header` `:2753`, `oos_delete_chain` `:3260`).
- **파일과 힙 헤더:** 새 파일 종류 `FILE_OOS`, 새 페이지 종류 `PAGE_OOS`가 생깁니다. 힙 헤더 `HEAP_HDR_STATS`에 `oos_vfid`가 추가됩니다(`heap_file.c:216`). OOS 파일은 첫 큰 값을 쓸 때 만들어집니다(`heap_oos_find_vfid`, `heap_file.c:13242`).

### 3. 어떤 값이 행 밖으로 가는가 (demotion)

`heap_attrinfo_determine_disk_layout` (`heap_file.c:13137`)이 결정합니다.

1. **기준:** 행 크기(헤더 + 값 + MVCC 여유)가 `DB_PAGESIZE / 4`(16KB 페이지에서 약 4,086바이트)를 넘을 때만 옮깁니다(`:13177`).
2. **대상:** 가변 길이이고 24바이트보다 큰 값입니다. BLOB/CLOB은 locator 문자열만 옮기고, 실제 LOB 파일은 그대로 LOB 계층이 관리합니다(ADR-0002).
3. **순서:** 큰 값부터 하나씩 옮기고, 행이 기준 이하가 되면 멈춥니다. 그래서 작은 값은 행 안에 남을 수 있습니다.
4. **컬럼 옵션:**
   - `STORAGE PREFER_INLINE`: 마지막 후보로 미룹니다(CBRD-26912).
   - `STORAGE FORCE_OUTLINE`: 행 크기와 상관없이 24바이트보다 크면 옮깁니다.
   - `STORAGE DEFAULT`, `STORAGE PREFER_OUTLINE`(DEFAULT와 같음).
5. **거부:** 옮긴 뒤에도 행이 overflow 레코드 크기(약 16KB)를 넘으면 OOS와 `REC_BIGONE`을 함께 쓰지 않고 `ER_HEAP_OOS_OVERPASS_MAXOBJ_SIZE`(-1388)로 거부합니다. OOS 값을 쓰기 전에 검사하므로 고아 체인이 생기지 않습니다(`heap_file.c:14229-14238`).

### 4. 읽기: Resolve와 Expand

- **Resolve(컬럼 단위, 기본):** `heap_attrinfo_read_dbvalues` → `heap_attrvalue_read_oos_inline` → `oos_read`. 실제로 읽는 컬럼의 값만 OOS 파일에서 가져옵니다. 같은 페이지의 값은 묶어서 읽습니다(`oos_read_many`).
- **Expand(행 단위, 필요할 때만):** `heap_record_replace_oos_oids` (`heap_oos.cpp:580`)가 모든 stub을 실제 값으로 바꾼 행을 만듭니다. 행 바이트를 클라이언트로 보내거나, 다른 힙에 다시 넣거나, 바이트 단위로 파싱하는 경우에만 씁니다.
- **API 변경:** 힙 조회 함수(`heap_get_visible_version`, `heap_scan_get_visible_version`, `heap_next`, `heap_prev`, `heap_init_get_context`)에 `HEAP_RECDES_CONSUMPTION_POLICY` 인자가 필수로 추가되었습니다(`heap_file.h:374-384`).
  - `HEAP_RECDES_CONSUME_RAW_BYTES`: 행 바이트를 attribute 계층 밖에서 쓰므로 Expand합니다. catalog 갱신, `xlocator_fetch_all`(unloaddb), 객체 반환 경로 등.
  - `HEAP_RECDES_DONT_CONSUME_RAW_BYTES`: attribute 계층으로 읽으므로 Expand하지 않습니다. 대부분의 호출자입니다.
  - 이 때문에 OOS와 무관한 파일(`serial.c`, `lock_manager.c`, `btree_load.c` 등)에도 인자 추가 변경이 있습니다.
- **인덱스 키:** `heap_midxkey_get_value` (`heap_file.c:11719`)가 OOS 값을 읽어 키를 만듭니다. 읽기 오류는 NULL 키로 바뀌지 않고 그대로 반환됩니다.

### 5. 쓰기와 삭제

- **INSERT (지연 쓰기, CBRD-27089·CBRD-27424):** 값을 먼저 메모리(`heap_pending_record`)에 준비하고, 파티션 등으로 실제 저장할 힙이 정해진 뒤에 OOS 파일에 씁니다(`locator_finalize_oos_record`, `locator_sr.c:4924`). 그래서 OOS 값은 항상 행이 실제로 들어가는 힙의 OOS 파일에 들어갑니다. loaddb와 bulk insert도 같은 방식입니다.
- **UPDATE:** 바꾸지 않은 컬럼까지 포함해 모든 OOS 값을 읽고 새 체인으로 다시 씁니다(`heap_attrinfo_set_uninitialized`, `heap_file.c:12933`). 이전 행 버전의 체인은 MVCC 독자를 위해 남겨 두고 vacuum이 정리합니다.
- **DELETE:** MVCC 모드에서는 삭제 표시만 하고 stub과 체인을 남깁니다. vacuum이 행의 마지막 버전을 지울 때(REMOVE) 체인도 지웁니다.
- **SA(standalone)·non-MVCC 모드:** 삭제·변경 즉시 더 이상 참조되지 않는 체인을 지웁니다(`heap_oos_delete_unreferenced`, `heap_oos.cpp:953`). 이미 사라진 체인은 건너뛰고 알림(-1391)만 남깁니다. 인덱스·파티션 키를 다 읽은 뒤에 행을 지우도록 순서를 바꿨습니다(`a967e1041`).
- **FK 연쇄 갱신:** 자식 행 갱신이 부모 행의 복제 정보를 덮어쓰지 않도록 보존·복원합니다(`7e7303b0e`).

### 6. OOS 파일의 공간 관리

- **빈 공간 찾기(3단계, CBRD-26658):** 전역 캐시 → page 0의 `best[10]` 힌트 → 페이지 표본 조사(최대 20%, 100페이지) 순서로 찾습니다(`oos_find_best_page`, `oos_file.cpp:3018`). 후보 페이지는 기다리지 않는 latch로 잡습니다. 힌트는 로그를 남기지 않으므로, 잃어버려도 표본 조사로 다시 찾습니다.
- **페이지 나열(ADR-0001):** OOS 파일은 페이지 순서를 관리하지 않는 파일(non-numerable)입니다. 표본 조사는 sector bitmap을 훑어 페이지를 찾습니다.
- **빈 페이지 반환(CBRD-26786):** 완전히 빈 OOS 페이지는 결국 파일 관리자에게 돌려줍니다.
  - vacuum이 비운 페이지는 바로 반환을 시도합니다(`oos_reclaim_empty_pages`, `:1730`).
  - 아직 끝나지 않은 트랜잭션이 rollback으로 되돌릴 수 있는 페이지는 미룹니다(LSA 검사, `:1454`).
  - 새 페이지가 필요할 때 먼저 반환 가능한 빈 페이지를 찾아 씁니다(growth-gate sweep, `oos_alloc_page_with_reclaim` `:2019`).
- **파일 생성·삭제와 TDE:** DROP TABLE 때 OOS 파일도 지웁니다(`oos_remove_file`, `:1250`). 암호화(TDE) 테이블이면 OOS 파일의 VFID를 힙 헤더에 기록하기 전에 같은 암호화를 적용합니다.

### 7. vacuum

- **REMOVE:** 행의 마지막 버전을 지울 때 같은 system operation 안에서 OOS 체인도 지웁니다(`vacuum_heap_record`, `vacuum.c:2464`; `vacuum_heap_oos_delete_within_sysop`, `vacuum_oos.cpp:447`).
- **UPDATE 이전 값 정리(forward walk):** UPDATE 로그의 undo 이미지에 있는 stub을 보고 이전 체인을 지웁니다(`vacuum.c:3616`, `:3757`; `vacuum_forward_walk_reclaim_oos`). 명세는 이 방식을 커밋 시점 알림으로 바꾸도록 정했지만 아직 바뀌지 않았습니다([미해결 사항](#알려진-미해결-사항) 참고).
- **모든 테이블에 영향을 주는 변경:** 메모리 부족 시 vacuum 블록을 실패로 끝내지 않고 다시 시도하게 했고, standalone vacuum이 종료 시 끝나지 않은 작업을 보존하게 했습니다(`16c5a148a`, `9c60e09ee`, `ff4dc0691`).

### 8. 복구와 로그

develop의 마지막 번호(135) 뒤에 새 recovery index를 붙였습니다(`recovery.h:197-217`).

| rcvindex | 번호 | 용도 |
| --- | --- | --- |
| `RVOOS_INSERT` | 136 | chunk 쓰기. redo는 chunk 이미지와 stamp를 복원 |
| `RVOOS_DELETE` | 137 | chunk 삭제. undo는 chunk와 stamp를 복원 |
| `RVREPL_OOS_INSERT` | 138 | 복제용 OOS 값 |
| `RVREPL_OOS_DELETE` | 139 | 예약(사용하지 않음) |
| `RVOOS_NOTIFY_VACUUM` | 140 | 예약(CBRD-27230용, 사용하지 않음) |
| `RVREPL_DUMMY_OOS_RECORD` | 141 | 여러 chunk 값의 복제 경계 표시 |
| `RVHF_DELETE_NEWHOME_NOTIFY_VACUUM` | 142 | 이동된 행 삭제를 vacuum에 알림 |

로그 레코드 종류 `LOG_DUMMY_OOS_RECORD`(53)도 추가되었습니다. 로깅이 켜져 있으면 모든 OOS 쓰기·삭제가 로그에 남습니다. `loaddb --no-logging`처럼 로깅을 끈 경우에는 stamp가 겹칠 수 있다는 것이 명세에서 받아들인 제약입니다.

### 9. HA 복제

- **master:** 행에 OOS 값이 있으면 그 값마다 복제 항목(`RVREPL_OOS_INSERT`)을 남기고, 항목은 master의 `RVOOS_INSERT` 로그를 가리킵니다(`locator_sr.c:8350-8371`, `:9160-9195`).
- **replica:** applier가 로그에서 값을 다시 만들고(`la_apply_oos_insert_log`, `log_applier.c:6235`), 같은 copy area로 서버에 보냅니다. 서버는 replica 자신의 OOS 파일에 값을 쓰고, 행의 stub을 replica의 OID와 stamp로 고칩니다(`locator_fixup_oos_oids_in_recdes`, `locator_sr.c:14423`). master와 replica의 OOS OID는 다르고, 같은 것은 값입니다.
- SQL 로그 출력을 위한 OOS 값 캐시는 행 처리가 끝나면 해제합니다(`792c54e50`).

### 10. 사용자에게 보이는 변경

- **SQL 문법:** 컬럼 정의에 `STORAGE PREFER_INLINE | FORCE_OUTLINE | DEFAULT | PREFER_OUTLINE`(`csql_grammar.y:10684-10706`). 새 키워드는 모두 비예약어입니다. 고정 길이 타입과 CLASS/SHARED 컬럼에는 쓸 수 없습니다. `SHOW CREATE TABLE`과 unloaddb 스키마에 출력됩니다.
- **조회:** `SHOW [ALL] HEAP OOS OF <table>`(DBA 전용)로 OOS 파일 페이지 수, 레코드 수, 사용 바이트를 볼 수 있습니다.
- **오류 코드:** -1387 `ER_HEAP_OOS_BAD_INLINE_HEADER`, -1388 `ER_HEAP_OOS_OVERPASS_MAXOBJ_SIZE`, -1389 `ER_HEAP_OOS_CORRUPTED_RECORD`, -1390 `ER_HEAP_OOS_INVALID_ARGUMENT`, -1391 `ER_HEAP_OOS_EAGER_CLEANUP_SKIPPED`(알림). 손상 관련 3개는 `call_stack_dump_activation_list` 기본값에 들어갑니다.
- **client API:** `db_attribute_is_oos_prefer_inline`, `db_attribute_is_oos_force_outline` 추가.
- **도구:**
  - unloaddb는 OOS 값을 펼쳐서 내보냅니다.
  - loaddb는 지연 쓰기를 쓰고, 파티션 테이블을 행 단위로 라우팅합니다.
  - diagdb는 `OUT_OF_LINE_OVERFLOW_STORAGE` 파일과 소유 클래스를 보여 줍니다.
  - spacedb는 OOS 파일을 힙 파일에 합쳐 셉니다(별도 항목은 CBRD-27350).
  - checkdb에는 OOS 검사가 추가되지 않았습니다.
- **시스템 파라미터:** 추가되지 않았습니다.

### 11. OOS와 직접 관계없는 변경

리뷰할 때 따로 보면 좋은 변경입니다.

- 힙 조회 함수의 `HEAP_RECDES_CONSUMPTION_POLICY` 인자 추가(§4). develop의 새 CDC 권한 확인 코드도 이번 develop 머지에서 맞췄습니다(`5a70787fe`).
- vacuum 재시도와 standalone 종료 처리(§7).
- loaddb의 파티션 행 단위 라우팅과 `TT_LOADDB` 스레드의 MVCCID 잠금 생략(`log_tran_table.c:4153-4163`).
- 공용 도우미 `byte_span_writer.hpp`, `page_buffer_util.hpp`, `LOG_LSA_QUEUE`.
- 테스트용 코드(`CUBRID_UNIT_TEST_ENABLED`) 약 39곳. 일반 빌드에는 들어가지 않습니다.

### 12. 테스트

- `unit_tests/oos/`: GoogleTest 바이너리 34개(SA 13, SERVER 6, CS 1, SQL 14)와 스크립트 7개, CTest 항목 41개, 약 386개 케이스입니다.
- 범위: 파일 API와 여러 chunk 값, 삭제와 식별 stamp, 빈 공간과 빈 페이지 반환, vacuum, 즉시 정리, 로그 없음과 crash 복구, TDE, SQL 동작(CRUD, DDL, 트랜잭션, `STORAGE` 옵션, `SHOW`, 지연 쓰기), loaddb와 workspace.
- `UNIT_TEST_OOS` 옵션을 켜야 빌드됩니다(`unit_tests/CMakeLists.txt:43`). gha-ci는 이 테스트를 실행하지 않습니다. GoogleTest는 FetchContent로 받으므로 configure에 네트워크가 필요합니다.
- 없는 테스트: rollback 후 vacuum(CBRD-27237), UPDATE 체인 재사용, 삭제 rollback과 슬롯 재사용 충돌(CBRD-27781. 재현 테스트는 수정 전까지 실패하므로 티켓에 첨부).

## Remarks

### Test Plan

| 검증 | 리비전 | 결과 |
| --- | --- | --- |
| gha-ci [run 40349442612](https://github.com/CUBRID/cubrid/actions/runs/40349442612) | 엔진 `5a70787fe`, TC public `70db22a1c` / private `75a02020e` | build release·debug 성공. `test_medium` 975/975, `test_shell` 3,460 PASS / 0 FAIL / 30 SKIP, `test_sql` 실패 0건(17,628건 실행). 테스트는 debug 빌드로만 실행됩니다. |
| 정적 검사 | `5a70787fe` | code-style, cppcheck, license, pr-style, memory-monitor-check 통과 |
| OOS CTest (로컬, `debug_gcc`) | `5a70787fe` | 33/33 통과. crash_recovery, no_logging, real_vacuum, workspace 4개 대상은 이 실행에서 빠졌습니다. |
| OOS CTest (로컬, `debug_gcc`) | `4408135c0` | 39/39 통과. crash_recovery, no_logging과 각 전용 DB fixture를 포함하고 real_vacuum, workspace 2개 대상만 뺐습니다. 테스트 스크립트 수명주기 회귀 11개 케이스 포함. 이 갱신 시점(2026-10-27)에 `4408135c0`의 gha-ci [run 40450836569](https://github.com/CUBRID/cubrid/actions/runs/40450836569)는 대기 중이었습니다. |
| OOS CTest (로컬, `debug_gcc`) | `dcbf09e4f` 내용 | 42/42 통과. 새 `test_oos_storage_format_guard`(자기 DB의 형식 번호를 0으로 바꾸고 csql·checkdb·emergency_patchlog가 거부하는지 확인)와 그 DB fixture 2개를 포함하고, real_vacuum, workspace 2개 대상만 뺐습니다(등록 항목 44개). 이 갱신에는 `dcbf09e4f`의 gha-ci 결과가 없습니다. |
| 다른 빌드의 DB 거부 (로컬, debug) | develop 빌드 `11.5.0.2635`로 만든 DB, 엔진 `1e8701b4f`·`d8ed97f77` 내용 | csql `-S`, checkdb `-S`, upgradedb, 서버 시작이 모두 -1392 메시지(형식 0, 현재 빌드 1)로 거부했고, deletedb는 성공했습니다. 검사가 없는 이전 PR 엔진은 같은 DB에서 `pgbuf_check_page_ptype_internal` assert로 중단되었습니다. |
| 이전 full CI | `52987c654` | shell 3개 실패, 같은 빌드 재실행에서 모두 통과(간헐 실패로 분류, [보고서](ci_analysis_report_52987c6_claude.md)) |
| 수동 QA | `1ec35f8` (2026-09-29) | 139개 실패 중 확인된 OOS 엔진 결함 0개([요약](../feature-oos-merge/merge-readiness/team-lead-summary_20260929_codex.md)). 이후 변경이 많아 참고용입니다. |
| 성능 | — | 이 head에서 측정한 OOS 성능 결과는 없습니다. 지연 쓰기(CBRD-27089)의 이전 측정에서 작은 행 CPU 영향은 판단 보류였습니다([측정](../cbrd-27089/design/ticket06-measurements-b871ea386-codex.md)). |

Greptile 1·2차 리뷰의 7개 지적은 모두 고쳤고 스레드에 답했습니다(`a967e1041`, `16c5a148a`, `793db7881`, `003de820e`, `cecb5ad0d`, `792c54e50`, `7e7303b0e`).

Greptile 4차 리뷰의 P1 3건은 모두 확인했고 스레드에 답했습니다.

- 테스트 준비 스크립트가 같은 이름의 기존 DB를 지운다는 지적([r4380243555](https://github.com/CUBRID/cubrid/pull/7990#discussion_r4380243555))은 `224104a36`, `4408135c0`에서 고쳤습니다. 이제 스크립트는 자기가 만든 DB만 다시 만들거나 지웁니다.
- 힙 헤더 형식 변경으로 develop에서 만든 DB를 잘못 읽는다는 지적([r4380243545](https://github.com/CUBRID/cubrid/pull/7990#discussion_r4380243545))은 [호환성](#호환성)의 재생성 정책대로 형식을 유지한다고 답했고, Greptile이 지적을 철회했습니다. develop도 11.5 개발 중에 같은 힙 헤더(`e84a7f6dc`)와 B-tree overflow 헤더(`10a1df3e6`)를 버전 변경 없이 바꿨습니다.
- 삭제 rollback과 슬롯 재사용이 충돌한다는 지적([r4380243533](https://github.com/CUBRID/cubrid/pull/7990#discussion_r4380243533))은 확인된 결함이며, CBRD-27781로 분리했습니다([알려진 미해결 사항](#알려진-미해결-사항)).

### 호환성

- 디스크 호환성 버전은 11.5 그대로입니다(`release_string.c` 변경 없음). ADR-0005의 결정입니다.
- 하지만 저장 형식이 바뀌어 **이 PR 이전 엔진(develop 포함)으로 만든 DB는 이 엔진에서 올바르게 읽을 수 없습니다.** `1e8701b4f`부터는 시작할 때 이런 DB를 거부합니다(아래).
  - `HEAP_HDR_STATS` 중간에 `oos_vfid`가 들어갑니다(`heap_file.c:216`).
  - VOT offset의 하위 2비트를 플래그로 씁니다.
  - `PAGE_OOS`는 `1e8701b4f`부터 `PAGE_TYPE`의 끝(`PAGE_VACUUM_DATA` 뒤)에 붙으므로, 기존 페이지 종류의 번호는 develop과 같습니다(`dcbf09e4f` 기준 `storage_common.h:166`). `5a70787fe`에서는 `PAGE_OOS`가 중간(`storage_common.h:159`)에 들어가 이후 값의 번호가 바뀌었습니다.
- **시작할 때 거부(`1e8701b4f`, `d8ed97f77`, [ADR-0006](https://github.com/vimkim/cubrid-oos-context/blob/3462a7f/docs/adr/0006-reject-pre-stamp-databases-at-boot.md)):** `disk_format()`이 첫 볼륨 헤더의 예약 필드 `reserved0`(이제 `storage_format`)에 `DISK_STORAGE_FORMAT_REVISION`(1)을 기록합니다. 이전 11.x 빌드는 이 필드에 0을 썼습니다. `boot_restart_server`와 `xboot_emergency_patch`는 볼륨 0을 마운트한 직후, 다른 페이지 읽기와 DWB·로그 복구 전에 이 값을 검사하고, 다르면 새 오류 `ER_BO_INCOMPATIBLE_STORAGE_FORMAT`(-1392)로 거부합니다. deletedb는 검사하지 않으므로 거부된 DB도 지울 수 있습니다. diagdb는 이 값을 출력합니다.
  - 출시된 11.4 이하 버전의 DB는 이보다 먼저 실행되는 디스크 호환성 검사에서 `ER_LOG_INCOMPATIBLE_DATABASE`(-86)로 거부됩니다.
  - 한계: 한 방향 검사입니다. 이전 빌드는 이 필드를 보지 않으므로 새 DB를 열 수 있습니다. 이전 형식의 백업은 restoredb가 파일을 복원한 뒤, 시작할 때 거부됩니다.
- 그래서 develop·QA·daily 환경의 DB는 이 PR 머지 후 다시 만들어야 합니다. 11.5는 아직 출시되지 않았습니다(최신 태그 `v11.4.6.1963`).
- 내부 enum(`LC_FLUSH_INSERT_OOS`, `SHOWSTMT_HEAP_OOS`, `PERF_PAGE_OOS`)이 중간에 추가되어, client(CAS 포함)와 server는 같은 빌드여야 합니다.

### 알려진 미해결 사항

| 항목 | 내용 | 상태 |
| --- | --- | --- |
| [CBRD-27781](http://jira.cubrid.org/browse/CBRD-27781) (Greptile [r4380243533](https://github.com/CUBRID/cubrid/pull/7990#discussion_r4380243533)) | OOS 페이지는 지운 슬롯과 공간을 바로 재사용합니다(`oos_file.cpp:3174`, rollback용 공간 예약 없음). 삭제가 끝나기 전에 다른 트랜잭션이 그 자리에 값을 넣고 commit한 뒤 삭제가 rollback되면, undo가 같은 슬롯에 이전 chunk를 되돌리다 충돌합니다. 현실적인 경우는 오류로 중단된 vacuum의 OOS 삭제 시스템 작업입니다. SERVER_MODE의 즉시 정리 경로는 대상 시스템 클래스 행이 OOS 기준을 넘지 않아 실제로는 도달하지 않습니다. | 확인된 결함. SERVER_MODE 단위 테스트로 재현했고 이 PR에서 분리. 수정 방안은 티켓에서 결정 |
| CBRD-27237 | UPDATE를 rollback한 뒤 vacuum이 undo 이미지를 보고 현재 행의 체인을 지울 수 있는 문제. 명세는 undo 이미지를 삭제 근거로 쓰지 말라고 정했습니다. | 코드상 아직 가능해 보임. 이 head에서 재현하지 않음. 회귀 테스트 없음 |
| CBRD-27230 | UPDATE에서 바꾸지 않은 컬럼의 체인 재사용과 커밋 시점 vacuum 알림 | 구현 안 됨 |
| CBRD-27057 | demotion 기준을 페이지 1/4(약 4,086B) 대신 행 4개가 확실히 들어가는 크기(16KB 페이지에서 4,060B)로 | 구현 안 됨(draft PR #7462) |
| CDC 테스트 `cbrd_27064`, `cbrd_27075` | OOS 엔진에서 실패(CDC·flashback의 OOS 이력이 없음). QA팀과 협의해 [#4210](https://github.com/CUBRID/cubrid-testcases-private-ex/pull/4210)에서 `_25_unstable`로 옮겨 develop CI(gha-ci `test_shell`)에서는 실행하지 않고, QA 회귀 테스트에서는 계속 실행합니다. OOS + CDC는 CBRD-26939에서 따로 구현합니다([리뷰 답변](https://github.com/CUBRID/cubrid/pull/7990#issuecomment-6435671972)) | QA팀과 합의해 이 상태로 머지. [ADR-0007](https://github.com/vimkim/cubrid-oos-context/blob/3462a7f/docs/adr/0007-run-deferred-cdc-regressions-in-qa-regression-only.md)이 ADR-0005의 테스트 정책("실패를 보이게 둔다")을 대체. 복원 조건은 readme에 기록 |
| `cbrd_23136` shell 테스트 | `1a8c705`의 CI에서 csql allocator abort 1회 | 원인 미확인. 로컬 재현 안 됨, 이후 full shell 3회에서 재발 없음 |
| 명세와 다른 구현 | `FORCE_OUTLINE`/`PREFER_OUTLINE`은 명세에 없는 옵션. 조회 API는 명세의 `_expand_oos` 함수 대신 정책 인자 방식 | 리뷰 판단 필요 |

### 머지 순서

1. testcase PR [cubrid-testcases#3551](https://github.com/CUBRID/cubrid-testcases/pull/3551)과 [cubrid-testcases-private-ex#4210](https://github.com/CUBRID/cubrid-testcases-private-ex/pull/4210)을 testcase `develop`에 머지합니다.
2. `Check TC PRs`(TC Merge Gate)를 다시 실행합니다.
3. 이 PR을 머지합니다.

1과 3 사이에는 develop CI에서 OOS 기대값 테스트가 실패하므로 간격을 짧게 둡니다. testcase answer에는 오류 번호(-1387~-1390)가 들어 있어서, 머지 전에 develop에 오류 코드가 추가되면 answer도 다시 맞춰야 합니다.

### 관련 문서와 PR

- [TC PR 변경 내역과 근거](CBRD-26357-tc-pr-changes_5a70787_claude.md)
- [OOS 명세 OOS-CONTEXT.md](https://github.com/vimkim/cubrid-oos-context/blob/c6fc51b/OOS-CONTEXT.md), [구현 관찰 기록](https://github.com/vimkim/cubrid-oos-context/blob/c6fc51b/docs/reference/implementation-observations.md)
- 이전 단계 PR: #6864(`feat/oos` 추적, 닫힘), #7803(정리 후 `feature/oos-merge`로 squash, `2c792b423`), #7927(CBRD-27089), #7925(CBRD-27424)
- 겹치는 PR: #8275(CBRD-27441, develop의 partition loaddb 수정. `partition_tbls` testcase 변경과 관련)
