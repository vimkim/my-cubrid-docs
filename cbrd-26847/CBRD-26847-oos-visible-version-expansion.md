## Purpose

CBRD-26847 은 OOS (큰 컬럼 값을 heap record 밖의 OOS file 에 따로 저장하는 방식) 적용 후
`heap_get_visible_version_expand_oos` 사용 지점을 다시 조사하는 작업이다. OOS 는 큰 값을 필요할 때만
읽어야 효과가 있는데, 기계적으로 바뀐 호출 지점들이 모든 OOS 컬럼을 먼저 읽는 `Expand` 경로를 타고 있었다.

- `AS-IS:` 많은 visible-version 호출 지점이 실제로는 attribute layer 를 통해 컬럼을 읽거나 존재 여부만 확인하면서도
  `heap_get_visible_version_expand_oos` 를 호출해 모든 OOS OID 를 실제 값으로 먼저 바꾸었다.
- `TO-BE:` raw `RECDES` 바이트를 그대로 소비하는 지점만 `Expand` 를 유지하고, 나머지는
  `heap_get_visible_version` 으로 되돌려 attribute layer 의 lazy `Resolve` 경로를 사용한다.

여기서 `Expand` 는 record 전체의 OOS OID 를 실제 값으로 한 번에 바꾸는 동작이고,
`Resolve` 는 필요한 컬럼 하나만 attribute layer 에서 `oos_read` 로 읽는 동작이다. 이 PR 은 두 동작의 선택 기준을
"raw record bytes 를 소비하면 Expand, 아니면 Resolve" 로 고정한다.

## Implementation

`src/storage/heap_file.c` 에서 `heap_get_visible_version_expand_oos` 주석을 TODO 에서 선택 규칙으로 바꾸었다.
주석은 `LC_COPYAREA` 로 클라이언트에 보내기, 다른 heap 에 raw 재삽입, byte 비교, `OR_BUF` 파싱처럼
raw `RECDES` 바이트가 필요한 경우에만 `_expand_oos` 를 쓰라고 설명한다.

다음 호출 지점은 `heap_get_visible_version` 으로 되돌렸다. 이 경로들은 attribute layer 가 OOS 컬럼을 필요할 때
읽거나, fixed/header/CHN/existence 정보만 사용한다.

- `src/executables/compactdb.c`
- `src/loaddb/load_server_loader.cpp`
- `src/query/serial.c`
- `src/sp/sp_code.cpp`
- `src/storage/compactdb_sr.c`
- `src/storage/heap_file.c` 의 `heap_scanrange_to_following`, `heap_scanrange_to_prior`, `heap_scanrange_next`
- `src/transaction/locator_sr.c` 의 `locator_all_reference_lockset`, `locator_update_force`,
  `locator_delete_lob_force`, `locator_repl_prepare_force`, `locator_mvcc_reeval_scan_filters`
- `src/transaction/lock_manager.c` 의 `lock_dump_resource`

반대로 다음 5개 호출 지점은 raw byte 소비자라서 `heap_get_visible_version_expand_oos` 를 유지했다. 각 호출 지점에는
왜 Expand 가 필요한지 짧은 주석을 붙였다.

- `src/transaction/locator_sr.c` 의 `xlocator_lock_and_fetch_all`: raw `RECDES` 를 client copy area 로 보낸다.
- `src/transaction/locator_sr.c` 의 `redistribute_partition_data`: raw `RECDES` 를 대상 partition heap 에 다시 넣는다.
- `src/storage/catalog_class.c` 의 `catcls_delete_instance`, `catcls_update_instance`,
  `catcls_update_class_stats`: record 를 `OR_BUF` 로 직접 파싱한다.

설계 결정은 엔진 저장소의 `docs/adr/0001-oos-expansion-is-opt-in.md` 에도 남겼다. 새 코드는 `_expand_oos` 이름 자체를
"raw byte 소비를 정당화해야 한다"는 신호로 보게 된다.

회귀 테스트는 `unit_tests/oos/sql/test_oos_sql_visible_version.cpp` 를 추가하고
`unit_tests/oos/sql/CMakeLists.txt` 에 등록했다. 테스트는 `BIT VARYING` 값을 10KB 이상으로 만들어 OOS demotion 을
강제하고, 길이 비교가 아니라 값 동등성을 확인한다.

- `UpdateOosValueEquality`: OOS 컬럼 UPDATE 후 변경 컬럼과 미변경 OOS 컬럼이 모두 정확히 읽히는지 확인한다.
- `UpdateNonOosColumnPreservesOosValue`: non-OOS 컬럼 UPDATE 후 OOS 컬럼 값이 byte-for-byte 보존되는지 확인한다.
- `MergeJoinOosValueEquality`: `USE_MERGE` hint 로 join 경로를 유도하면서 OOS 컬럼 값 비교가 정상인지 확인한다.

## Remarks

가장 큰 위험은 선택 기준을 반대로 잘못 적용하는 것이다. attribute layer 를 거치는 경로에 Expand 를 남기면 성능만
낭비되지만, raw byte 소비자에서 Expand 를 빼면 OOS OID 가 그대로 외부 소비자에게 노출될 수 있다. 이 PR 은
현재 census 로 확인한 5개 raw byte 소비자를 유지하고, 그 이유를 코드 주석과 ADR 에 남긴다.

이 PR 은 visible-version fetch 선택 기준과 회귀 테스트를 다룬다. 새 merge-join 테스트는 `USE_MERGE` hint 로
관련 경로를 유도하지만 최종 실행 계획을 assert 하지는 않는다. OOS OID reuse, OOS PEEK mode, raw byte path 의 별도
누락 사례 분석은 포함하지 않는다.

### Test Plan

- CMake configure 를 다시 수행해 새 OOS SQL test target 을 등록했다.
- `test_oos_sql_visible_version` target 빌드가 성공했다.
- `ctest -R '^test_oos_sql_visible_version$'` 가 통과했다. fixture 를 포함해
  `oos_setup_db`, `test_oos_sql_visible_version`, `oos_cleanup_db` 3개 테스트가 모두 성공했다.
