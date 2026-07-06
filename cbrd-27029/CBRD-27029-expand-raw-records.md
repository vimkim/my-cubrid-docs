## Purpose

CBRD-27029 는 OOS (큰 컬럼 값을 heap record 밖의 OOS file 에 따로 저장하는 방식) 적용 후
raw `RECDES` 바이트를 직접 쓰는 경로에서 inline OOS OID 가 그대로 보일 수 있는 회귀를 막는 작업이다.

- `AS-IS:` 기본 heap fetch 는 OOS Expand 를 하지 않았고, 호출자가 직접 `_expand_oos` API 를 골라야 raw record 안의
  OOS OID 가 실제 값으로 바뀌었다.
- `TO-BE:` 기본 heap fetch 는 OOS Expand 를 수행하고, attribute layer 에서 필요한 컬럼만 lazy OOS Resolve 하는 경로만
  명시적으로 `*_skip_oos_expand` API 를 사용한다.

여기서 OOS Expand 는 record-level eager 동작이다. 즉, `RECDES` 안의 모든 inline OOS OID 를 실제 값으로 바꾸어
record 전체를 다시 만든다. OOS Resolve 는 column-level lazy 동작이다. 즉, `heap_attrinfo_read_dbvalues` 가 필요한
컬럼 하나를 읽을 때 `oos_read` 로 실제 값을 가져온다.

이 변경은 "raw record bytes 를 소비하면 기본 Expand, attribute reader 를 바로 거치면 skip" 이라는 기준을 API 이름으로
드러낸다. unload/load, compact/copy, log-oriented path 처럼 `RECDES.data` 를 직접 직렬화하거나 파싱하는 경로는
호출자가 빠뜨려도 기본적으로 안전한 값을 받는다.

## Implementation

`src/storage/heap_file.c` 와 `src/storage/heap_file.h` 에서 `HEAP_GET_CONTEXT.expand_oos` 기본값을 `true` 로 바꾸었다.
이에 따라 `heap_next`, `heap_prev`, `heap_next_sampling`, `heap_get_visible_version`,
`heap_scan_get_visible_version` 계열의 기본 동작은 inline OOS OID 를 실제 값으로 바꾸는 쪽이 된다.

기존 `_expand_oos` API 는 compatibility alias 로 남겼다. 이미 `_expand_oos` 를 호출하던 raw-byte 소비자는 소스 호환을
유지하면서 같은 동작을 계속 얻는다.

대신 attribute layer 가 곧바로 lazy OOS Resolve 를 수행하는 경로에는 명시적인 skip API 를 추가했다.

- `heap_next_skip_oos_expand`
- `heap_next_sampling_skip_oos_expand`
- `heap_prev_skip_oos_expand`
- `heap_get_visible_version_skip_oos_expand`
- `heap_scan_get_visible_version_skip_oos_expand`

`src/query/scan_manager.c` 의 normal heap scan, sampling scan, reverse scan, index heap lookup 은 새 skip API 로
전환했다. 이 경로들은 fetch 직후 `heap_attrinfo_read_dbvalues` 로 requested attribute 를 읽으므로 record-level Expand 를
먼저 하면 OOS 값을 불필요하게 모두 읽을 수 있다.

`src/query/query_executor.c` 의 update/delete LOB attribute read 와 duplicate-key update read 도 skip API 로 전환했다.
이 경로들도 `heap_attrinfo_read_dbvalues` 를 통해 필요한 attribute 를 읽는다.

`src/query/parallel/px_scan/index/px_scan_index_leaf_slot_walker.cpp` 의 parallel non-covering index heap fetch 역시
skip API 로 바꾸었다. heap record 를 가져온 뒤 `heap_attrinfo_read_dbvalues` 로 rest attribute 를 읽는 구조이기 때문이다.

## Remarks

가장 중요한 선택 기준은 `RECDES.data` 를 raw bytes 로 소비하는지 여부다. raw bytes 를 외부로 보내거나 다른 heap 에
재삽입하거나 `OR_BUF` 로 직접 파싱하는 경로는 Expand 된 record 가 필요하다. attribute layer 를 통해 `DB_VALUE` 로 읽는
경로는 OOS Resolve 가 이미 준비되어 있으므로 skip API 를 쓰는 편이 맞다.

이 PR 은 API 기본값을 안전한 쪽으로 되돌리고, 비용을 아끼려는 경로를 명시적으로 표시한다. 따라서 새 호출 지점을 추가할 때
`*_skip_oos_expand` 를 쓰려면 바로 뒤에서 `heap_attrinfo_read_dbvalues` 처럼 attribute-level OOS Resolve 를 수행한다는
근거가 있어야 한다.

이 변경은 `OOS expansion is opt-in, and raw-record consumers are still easy to miss` 로 분류된 CI 회귀를 대상으로
한다. 특히 load/unload/compact/copy-style shell test 처럼 unresolved OOS OID 를 raw record 로 받을 수 있는 영역이
영향 범위다.

### Test Plan

- `git diff --check` 통과.
- Debug build 와 OOS 관련 test target 실행 완료.
- 23개 테스트가 모두 통과했고, 최종 SQL check 는 `TEST passed!` 를 출력했다.
