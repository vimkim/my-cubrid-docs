# CBRD-26972 SHOW HEAP OOS 진단 SQL

## Purpose

CBRD-26972는 OOS (큰 가변 길이 컬럼 값을 heap 레코드 밖의 별도 OOS 파일에 저장하는 기능) 상태를 SQL 진단 명령으로 확인하기 위한 작업이다. 기존에는 개발자용 `;oos_stats` 세션 명령으로 OOS 통계를 볼 수 있었지만, `SHOW HEAP ...` 계열의 DBA 진단 SQL에서는 heap과 연결된 OOS 파일 존재 여부와 크기를 함께 볼 방법이 없었다.

이 변경은 `SHOW HEAP OOS OF <class>`와 `SHOW ALL HEAP OOS OF <class>`를 추가한다. DBA가 특정 테이블의 heap 파일과 OOS 파일을 한 행 단위로 확인하고, 파티션 테이블은 기존 `SHOW ALL HEAP HEADER/CAPACITY`처럼 여러 heap row로 볼 수 있게 하는 것이 목적이다.

논의 결과, 이 PR의 범위는 신규 `SHOW HEAP OOS` 진단 SQL로 한정한다. 기존 `SHOW HEAP CAPACITY`의 결과 컬럼과 의미는 변경하지 않으며, 공유 OOS 통계 수집 구조에 free-space 구간별 page 수 같은 상세 지표도 추가하지 않는다. 두 변경은 기존 진단 인터페이스의 스펙 변경이므로 별도 합의 후 다룬다.

## Implementation

`src/storage/storage_common.h`에 `SHOWSTMT_HEAP_OOS`, `SHOWSTMT_ALL_HEAP_OOS`를 추가했다. `src/parser/csql_grammar.y`, `src/parser/csql_lexer.l`, `src/parser/keyword.c`에는 `OOS` 토큰과 `HEAP OOS`, `ALL HEAP OOS` 문법을 추가했다. `OOS`는 identifier 대안에도 넣어서 일반 식별자 호환성을 유지한다.

`src/parser/show_meta.c`에는 `metadata_of_heap_oos()`를 추가했다. 출력 컬럼은 table/class/heap 식별자, OOS VFID, page/record 통계, `Oos_physical_bytes`, `Oos_unused_bytes`로 구성했다. 기존 heap 진단과 같은 `pt_check_table_in_show_heap()` semantic check를 사용하고, DBA 전용 정책도 유지한다.

`src/query/show_scan.c`는 새 SHOW type을 `heap_header_capacity_start_scan()`, `heap_oos_next_scan()`, `heap_header_capacity_end_scan()`에 연결한다. `src/storage/heap_file.c`의 시작 scan은 `SHOWSTMT_ALL_HEAP_OOS`도 partition expansion 대상으로 처리한다.

`src/storage/heap_oos.cpp`는 OOS expansion/cleanup 코드와 함께 SHOW OOS row를 만드는 `heap_oos_next_scan()`도 담당한다. `heap_oos_find_vfid()`는 heap header layout (`HEAP_HDR_STATS`)을 직접 읽고 쓰므로 `src/storage/heap_file.c`에 남겨 heap header/statistics 구조의 소유권을 유지했다. `src/storage/heap_show_scan_context.hpp`에는 `heap_header_capacity_start_scan()`과 OOS SHOW scan이 공유하는 작은 scan context만 분리했다.

`heap_oos_next_scan()`은 heap HFID의 file descriptor에서 class OID를 확인하고, `heap_oos_find_vfid(..., false)`로 OOS VFID를 찾는다. `false`를 넘기므로 SHOW 실행만으로 OOS 파일을 새로 만들지 않는다. OOS 파일이 있으면 `oos_get_stats_by_vfid()`를 호출하고, 없으면 성공 row로 반환하되 OOS VFID 컬럼은 `NULL`, count/byte 컬럼은 0으로 둔다.

통계 계산은 다음 규칙을 사용한다.

- `Has_oos_file`: OOS VFID가 있고 통계 수집이 성공하면 1, 없으면 0
- `Oos_physical_bytes`: `Oos_num_user_pages * Oos_page_size`
- `Oos_unused_bytes`: `max(Oos_physical_bytes - Oos_recs_sumlen, 0)`

`unit_tests/oos/sql/test_oos_sql_show.cpp`를 추가하고 `unit_tests/oos/sql/CMakeLists.txt`에 등록했다. 테스트는 OOS 파일이 없는 테이블, OOS 파일이 생기는 테이블, non-partitioned class의 `SHOW ALL`, partitioned class의 `SHOW ALL` row expansion을 확인한다.

## Remarks

이 명령은 storage 동작을 바꾸지 않는 진단 기능이다. OOS demotion 기준, OOS record format, MVCC, vacuum, recovery 동작은 변경하지 않는다.

기존 `SHOW HEAP CAPACITY`와 개발자용 `;oos_stats`의 출력 스펙도 변경하지 않는다. 이 PR에서 추가되는 공개 진단 결과는 `SHOW HEAP OOS`와 `SHOW ALL HEAP OOS`뿐이다.

`oos_get_stats_by_vfid()`는 OOS page를 순회하면서 live record 통계를 모은다. `Oos_recs_sumlen`은 OOS slot에 저장된 record 길이의 합이며, SQL 컬럼의 논리 payload 길이만을 뜻하지 않는다. 이 helper는 busy page를 만나면 일부 page를 건너뛸 수 있으므로, SHOW 결과는 DBA 진단용 현재 통계로 보아야 한다. 이 PR은 그 helper의 통계 수집 정책을 바꾸지 않는다.

`SHOW ALL HEAP OOS OF <class>`는 기존 heap 진단 명령과 같은 partition metadata를 사용한다. partitioned class에서는 partitioned table heap과 partition heap들이 여러 row로 반환될 수 있고, 각 row는 해당 heap에 연결된 OOS 파일 상태를 보여준다.

실제 `csql -S` 확인 결과는 다음과 같다.

```sql
CREATE TABLE t_show_oos (id INT PRIMARY KEY, data_col BIT VARYING);
INSERT INTO t_show_oos VALUES (1, REPEAT(X'AA', 8192));
SHOW HEAP OOS OF t_show_oos;
```

```text
Table_name='dba.t_show_oos', Class_oid='(0|204|6)', Heap_volume_id=1, Heap_file_id=640,
Heap_header_page_id=641, Has_oos_file=1, Oos_volume_id=1, Oos_file_id=704,
Oos_num_user_pages=2, Oos_page_size=16344, Oos_num_recs=1, Oos_recs_sumlen=8216,
Oos_physical_bytes=32688, Oos_unused_bytes=24472
```

### Test Plan

- `cmake --build build_preset_debug_gcc --target test_oos_sql_show -j 8`
- `ctest --test-dir build_preset_debug_gcc -R test_oos_sql_show --output-on-failure`
- `ctest --test-dir build_preset_debug_gcc --output-on-failure --verbose`
