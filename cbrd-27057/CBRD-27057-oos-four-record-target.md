# CBRD-27057 — OOS four-record physical target

## Purpose

OOS (큰 가변 길이 컬럼 값을 별도 파일에 저장하는 기능)는 heap record가 기준 크기를 넘으면 큰 값을
OOS file로 옮기고 heap에는 16B OOS inline stub을 남긴다. CBRD-27057은 OOS trigger와 demotion stop을
P사의 기본 TOAST 정책과 같은 four-record physical target으로 맞추고, 이 target을 heap page 채움 정책과
분리한다. 여기서 같게 만드는 범위는 target 산식과 책임 분리이며 P사의 TOAST 전체 동작은 아니다.

- **AS-IS (`feat/oos`, `aa629e692`):** trigger와 loop stop에 `DB_PAGESIZE / 4`를 직접 사용한다. Current layout에서는
  4,086B이며 heap 고정 영역, 네 user slot, alignment를 반영하지 않는다.
- **TO-BE:** `heap_nonheader_page_capacity()` 기반 physical target 4,060B를 trigger와 loop stop에 함께
  사용한다. `unfill_factor`는 target에서 제외하고 기존 heap page 선택에만 적용한다.

P사는 `TOAST_TUPLE_THRESHOLD`와 기본 `TOAST_TUPLE_TARGET`을 모두 `MaximumBytesPerTuple(4)`로 정의한다.
이 macro는 다음과 같이 page header와 네 `ItemIdData`를 예약한 뒤 tuple당 크기를 계산하고 alignment를
내림한다.

```text
MAXALIGN_DOWN(
  (BLCKSZ - MAXALIGN(SizeOfPageHeaderData + 4 * sizeof(ItemIdData))) / 4)
```

INSERT/UPDATE의 toaster는 기본적으로 tuple을 이 target 이하로 줄인다. 반면 fillfactor는
`RelationGetBufferForTuple()`에서 `RelationGetTargetPageFreeSpace()`를 통해 page/FSM 선택용 여유 공간으로
계산되며 `MaximumBytesPerTuple(4)`에는 들어가지 않는다. CUBRID도 이 책임 분리를 적용한다.

```text
P사                                               CUBRID
MaximumBytesPerTuple(4)                           heap_oos_inline_target_size()
TOAST_TUPLE_THRESHOLD == default target           OOS trigger == demotion stop
RelationGetBufferForTuple(fillfactor)             heap_stats_find_best_page(unfill_space)
```

## Implementation

`src/storage/heap_file.c`에 `heap_oos_inline_target_size()`를 추가한다. Current 16KB I/O page layout은
40B file-I/O reserved 영역을 제외하므로 `DB_PAGESIZE`가 16,344B이고,
`heap_nonheader_page_capacity()`는 slotted-page header와 heap chain record/slot을 제외한 16,268B다.

```text
records_per_page = 4
page_capacity = 16,268
slot_size = 4
alignment = 4

target = ALIGN_BELOW((16,268 - 4 * 4) / 4, 4)
       = ALIGN_BELOW(4,063, 4)
       = 4,060

4 * (4,060 + 4) = 16,256 <= 16,268
4 * (4,064 + 4) = 16,272 >  16,268
```

Helper는 계산 결과가 최대값인지 `assert`로도 검증한다. 즉 target 네 개와 각 slot은 capacity 안에 들어가고,
다음 aligned record size 네 개는 들어가지 않아야 한다. 이 helper 결과는 다음 두 비교에서 동일하게 사용된다.

1. `header_size + payload_size + mvcc_extra > target`: OOS demotion 시작
2. `header_size + payload_size + mvcc_extra <= target`: largest-first loop 중단

`PRM_ID_HF_UNFILL_FACTOR`와 heap header의 `unfill_space`는 target 계산에 사용하지 않는다.
`heap_stats_find_best_page()`의 기존 bestspace page 선택은 변경하지 않는다. 따라서 4,060B는 물리적
capacity invariant이며 실제 INSERT가 모든 page에 항상 네 row를 배치한다는 보장은 아니다.

다음 기존 정책은 그대로 유지한다.

- Variable value가 `OR_OOS_INLINE_SIZE`(16B)보다 클 때만 profitable candidate로 선택한다.
- `STORAGE PREFER_INLINE` priority 후 largest-first 순서를 유지한다.
- Candidate가 부족하면 target을 넘는 non-bigone record도 허용한다.
- OOS-backed record가 `REC_BIGONE`을 요구하면 기존 오류로 거부한다.

`src/storage/heap_file.h`는 SQL storage test가 production helper 결과를 직접 검증할 수 있도록 이 함수를
내부 storage API로 선언한다. SQL 또는 사용자 API를 추가하는 변경은 아니다.
`unit_tests/oos/sql/test_oos_sql_common.hpp`는 SA_MODE test에서 table의 heap HFID 조회를 재사용하고 lazy OOS
file 생성 여부를 확인하는 helper를 제공한다. `unit_tests/oos/sql/test_oos_sql_boundary.cpp`는 이를 사용하여
다음 coverage를 추가한다.

- Current layout의 exact target이 4,060B인지 확인한다.
- 네 target record는 들어가고 다음 aligned size는 들어가지 않는지 확인한다.
- `unfill_factor=0.0`과 `0.10`에서 target이 같은지 확인한다.
- 임시 작업 branch에서 사용했던 잘못된 unfill-dependent target 3,652B를 넘지만 새 target 이내인 record는
  inline으로 유지되고, physical target을 넘는 record는 OOS를 trigger하는지 확인한다. 3,652B는
  `feat/oos`의 AS-IS가 아니다.
- 100-row bulk logical value round-trip을 확인한다.

실제 heap page 수를 네 rows/page로 강제하는 assertion은 제거한다. Heap page packing은 unfill과 page placement
정책의 결과이므로 OOS target acceptance criterion이 아니다.

## Remarks

- On-disk OOS format, WAL, recovery, replication, SQL syntax은 변경하지 않는다.
- P사의 relation별 `toast_tuple_target`, `TOAST_TUPLE_TARGET_MAIN`, compression/storage strategy는 범위 밖이다.
  따라서 이 변경은 four-record target과 fillfactor/unfill 책임 분리를 맞추는 것이며 TOAST 전체 알고리즘의
  동등성을 주장하지 않는다.
- Current layout에 종속된 4,060B assertion은 page layout 변경 시 의도적인 target 재검토를 요구하는 guard다.
- Reviewer는 `heap_oos_inline_target_size()`의 maximality, outer gate/loop stop의 동일 target 사용,
  `unfill_factor`와 target의 분리를 우선 확인하면 된다.

### Test Plan

- Debug GCC build 성공
- Configured OOS tests 23/23 통과
- `test_oos_sql_boundary` 11/11 통과
- `git diff --check` 통과

관련 이슈: https://jira.cubrid.org/browse/CBRD-27057
