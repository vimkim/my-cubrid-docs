http://jira.cubrid.org/browse/CBRD-26831

## Purpose

OOS(Out-of-row Overflow Storage) 파일은 페이지의 논리적 순번을 조회하거나 파일을 N번째 페이지 기준으로 자르는 numerable API를 사용하지 않는다. 기존 numerable 설정은 OOS 초기 POC에서 전체 페이지 순회를 빠르게 구현하기 위해 선택한 임시 설계였으며, 현재 OOS의 영구 계약으로 유지할 이유가 없다.

| 구분 | AS-IS | TO-BE |
|---|---|---|
| 파일 생성 | 모든 `FILE_OOS`를 numerable 파일로 생성 | 모든 `FILE_OOS`를 non-numerable 파일로 생성 |
| 페이지 할당/해제 | sector allocation bitmap과 별도로 numerable user-page table도 관리 | sector allocation bitmap만 관리 |
| best-space 동기화 | `file_numerable_find_nth()`로 페이지 순회 | `file_get_all_data_sectors()` snapshot의 sector bitmap 순회 |
| OOS 통계 수집 | `file_numerable_find_nth()`로 전체 페이지 순회 | 동일한 sector-bitmap snapshot 순회 |
| 호환성 | POC numerable OOS 파일을 전제로 동작 | 기존 POC DB 호환 경로 없이 OOS 파일은 항상 non-numerable이며 DB를 재생성 |

이 변경의 목적은 OOS에 불필요한 numerable user-page table 유지 비용과 의존성을 제거하는 것이다. 특히 페이지 해제 시 allocation bitmap 갱신 외에 numerable 순번 테이블의 항목을 탐색·삭제하는 작업이 사라진다. OOS의 전체 순회는 INSERT/DELETE의 일반 hot path가 아니라 best-space hint 재구축과 진단용 통계 수집에 한정되므로, sector bitmap을 사용해도 비용 특성이 적절하다.

비용 모델은 다음과 같다.

- snapshot 수집은 파일의 partial/full sector table 크기에 비례한다.
- bitmap 전개는 할당된 data page 수에 선형이며, 파일 table page와 sticky OOS header page는 제외한다.
- best-space partial scan은 기존과 같이 전체 data page의 20%를 대상으로 하되 최소 10페이지, 최대 100페이지로 제한한다.
- 통계 수집은 본래 전체 페이지 scan이므로 `O(number of allocated data pages)` 특성이 유지된다.
- snapshot의 sector 목록과 정렬된 임시 VPID 목록을 사용하므로 메모리는 `O(number of sectors + number of allocated data pages)`이다.

따라서 page delete는 numerable 유지 작업이 제거되어 더 단순해지고, 전체 scan은 sector bitmap 전개 비용이 추가되지만 기존 페이지별 fix 및 slotted-page 조사 비용에 비해 같은 선형 차수이며 OOS 사용 방식에서 허용 가능한 범위다.

## Implementation

### 실행 계획

1. OOS 파일 생성 시 `is_numerable=false`를 강제하고 POC 파일을 위한 분기나 자동 변환 코드는 두지 않는다.
2. `file_get_all_data_sectors()` 결과의 각 `FILE_PARTIAL_SECTOR.page_bitmap`을 전개해 OOS data VPID를 모으는 내부 helper를 추가한다.
3. helper 결과에서 sticky header VPID를 제외하고 VPID를 정렬해 best-space partial scan의 안정적인 resume/wrap-around 순서를 만든다.
4. best-space 동기화와 `oos_get_stats_by_vfid()`의 `file_numerable_find_nth()` 호출을 helper 기반 순회로 교체한다.
5. bitmap snapshot 이후 페이지가 해제될 수 있으므로 read-only scan은 `OLD_PAGE_MAYBE_DEALLOCATED`로 fix한다. `ER_PB_BAD_PAGEID`와 conditional-latch miss는 skip하고, 그 외 오류는 호출자에게 전달한다.
6. fix에 성공한 페이지는 `PAGE_OOS`인지 확인한다. 다른 page type으로 재사용된 VPID는 skip한다.
7. deallocation/reuse 때문에 snapshot 항목을 건너뛴 횟수를 `Num_oos_bitmap_snapshot_skips` 성능 통계로 노출한다.
8. 한 sector를 넘는 OOS 파일에서 best-space 재구축과 전체 통계 수집을 함께 검증하고, 기존 OOS 회귀 테스트 전체를 실행한다.

### 구현 결과

`src/storage/oos_file.cpp`에 `oos_collect_data_page_vpids()`를 추가했다. 이 helper는 file manager가 제공하는 data-sector snapshot을 가져온 뒤 allocation bit가 설정된 page만 VPID로 전개한다. file-table page는 `file_get_all_data_sectors()`가 제거하며, helper는 sticky OOS header page를 추가로 제외한다. 수집된 VPID는 `VPID_LT` 순서로 정렬한다.

best-space 순회 흐름은 다음과 같다.

```text
file_get_all_data_sectors
  -> sector bitmap 전개
  -> OOS header 제외
  -> VPID 정렬
  -> full_search_vpid 다음 위치부터 시작
  -> 최대 scan 수만큼 순환
  -> MAYBE_DEALLOCATED read fix
       -> busy: skip
       -> ER_PB_BAD_PAGEID: counter 증가 후 skip
       -> 다른 page type: counter 증가 후 skip
       -> PAGE_OOS: free-space/statistics 수집
```

partial scan은 각 후보를 시도할 때 `full_search_vpid`를 전진시켜 busy/reclaimed page 때문에 다음 scan이 같은 위치에 고정되지 않도록 했다. 실제 INSERT 경로는 header latch를 해제한 상태에서 임시 stats 구조로 scan한 후 resume VPID만 OOS header에 non-logged hint로 반영한다. snapshot 수집이나 page fix에서 실제 오류가 발생하면 새 페이지 할당으로 숨기지 않고 INSERT 호출자에게 전달하며, 이 경우 null page를 역참조하지 않도록 `oos_insert_within_page()`도 방어한다.

`oos_get_stats_by_vfid()`도 같은 helper를 사용한다. 통계는 기존 계약대로 conditional latch를 얻지 못한 busy page는 건너뛰어 일시적인 undercount를 허용하고, snapshot 이후 해제된 page도 건너뛴다. 실제 오류는 더 이상 `er_clear()`로 숨기지 않는다.

`src/base/perf_monitor.h`와 `src/base/perf_monitor.c`에는 `PSTAT_OOS_NUM_BITMAP_SNAPSHOT_SKIPS` / `Num_oos_bitmap_snapshot_skips`를 추가했다. 이 값은 bitmap snapshot에는 있었지만 fix 시점에 이미 해제되었거나 다른 page type으로 재사용된 항목 수를 나타낸다.

`unit_tests/oos/test_oos_bestspace.cpp`의 기존 cache refill 테스트는 `DISK_SECTOR_NPAGES + 5`개의 한-page OOS record를 생성하도록 확장했다. 여러 위치의 record를 삭제하고 cache/header hint를 비운 뒤 다음을 검증한다.

- 두 개 이상의 sector bitmap을 거쳐 reusable page를 다시 찾는다.
- 반환된 best page가 실제로 space를 비운 page 중 하나다.
- 같은 non-numerable OOS 파일의 전체 통계 scan이 삭제 후 live record 수를 정확히 계산한다.

### 검증 결과

- Debug GCC server/standalone 전체 빌드 및 설치 성공
- 구성된 OOS CTest suite 25개 중 25개 통과
- 신규 `OosBestspaceTest.BestspaceSectorBitmapSyncAcrossSectors` 통과
- OOS SQL storage/show 통계 테스트 통과
- `git diff --check` 통과
- pre-commit code-style 검사에서 변경된 C++ 파일 모두 `Unchanged`

## Remarks

- Source commit: `bb5e61d8bd13079c03ff78d724e743317d6f08f7`
- PR base: `feat/oos`
- 이번 변경은 POC database와의 disk compatibility를 제공하지 않는다. 변경 후 OOS 테스트 및 개발 DB는 재생성한다.
- sector bitmap은 snapshot이므로 scan 중 동시 page deallocation/reuse 가능성을 제거하지 않는다. `OLD_PAGE_MAYBE_DEALLOCATED`, `ER_PB_BAD_PAGEID` 처리, page type 검증 및 skip counter가 이 read-only scan의 방어선이다. page type 검증은 파일 소유권 증명이 아니므로, 같은 type의 page로 즉시 재사용되는 극단적인 경쟁은 hint/진단 scan의 근사성 범위에 남는다.
- OOS write/read/delete의 실제 record 접근 경로는 기존처럼 `OLD_PAGE`를 사용하며 이번 snapshot scan 규칙을 적용하지 않는다.
