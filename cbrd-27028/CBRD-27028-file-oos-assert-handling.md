# CBRD-27028 FILE_OOS Assert Handling

https://jira.cubrid.org/browse/CBRD-27028

## Purpose

OOS (큰 가변 컬럼 값을 heap record 밖의 OOS file 에 따로 저장하는 방식)가 `FILE_OOS` 파일을 만들면, 기존 파일 관리자 유틸리티 경로 일부는 아직 이 파일 타입을 일반 파일처럼 다루지 못한다. 이 변경은 `diagdb`, `spacedb`, `checkdb` 류의 읽기 전용 진단 경로가 OOS 파일을 만났을 때 단순 assertion 으로 중단되지 않게 하는 회귀 안정화 패치다.

- AS-IS: OOS 파일이 있는 DB 에서 `src/storage/file_manager.c` 의 descriptor dump, file tracker iteration, `spacedb` 집계 경로가 `FILE_OOS` 를 만나면 debug 빌드에서 assertion 으로 중단될 수 있었다.
- TO-BE: `FILE_OOS` 는 간단한 descriptor 로 출력되고, file tracker 는 읽기 전용 순회에서 OOS 항목을 반환하며, `spacedb` 는 OOS 페이지를 기존 heap totals 에 포함해 유틸리티가 정상 종료된다.

이 PR 은 CBRD-27028 의 "FILE_OOS 단순 assert 오류"만 다룬다. 별도 `SPACEDB_OOS_FILE` 출력 행 추가, OOS 파일 owner descriptor 저장, OOS 공간의 테이블별 귀속 표시는 후속 변경으로 남긴다.

## Implementation

`src/storage/file_manager.c` 한 파일만 수정한다.

- `file_header_dump_descriptor()` 의 `FILE_OOS` case 에서 `assert (false)` 를 제거하고 `OOS file` 한 줄을 출력한다. generic file dump 와 capacity dump 는 이미 VFID, page count, file type 을 출력하므로, 현재 OOS file header 에 없는 class owner 정보를 꾸며내지 않는다.
- `file_tracker_get_and_protect()` 의 desired type 필터에서 `FILE_OOS` 를 명시적으로 허용한다. `FILE_UNKNOWN_TYPE` 순회 중 OOS 항목을 만나도 assertion 하지 않고 해당 VFID 를 caller 에 반환한다.
- 같은 함수의 보호 단계에서 OOS 는 class-lock 보호 없이 `*stop = true` 로 반환한다. 현재 `FILE_OOS` descriptor 에는 owner class OID 가 없어서 heap/btree 처럼 class lock 을 잡을 근거가 없다.
- 방어적 분기로 남은 class OID extraction switch 의 `FILE_OOS` case 는 `class_oid` 를 null 로 유지한다.
- `file_tracker_item_spacedb()` 의 `assert_release (false)` 를 제거하고 `FILE_OOS` 를 `SPACEDB_HEAP_FILE` 에 집계한다. OOS 는 table-owned storage 이지만 현재 `SPACEDB_FILE_TYPE` 에 OOS 카테고리가 없고, 새 카테고리는 `SPACEDB_FILE_COUNT` packing, `util_cs.c` 출력 라벨, message catalog, QA answer 를 함께 바꾸는 별도 protocol/output 변경이다.

범위를 좁히기 위해 heap-only dump helpers 는 건드리지 않았다. `file_tracker_dump_all_heap()` 와 `file_tracker_dump_all_heap_capacities()` 는 heap 전용 helper 를 호출하므로 OOS 를 끼워 넣지 않는 편이 맞다.

## Remarks

리뷰 초점은 세 가지다.

- `FILE_OOS` 를 heap 으로 가장하지 않고, 각 utility path 에서 명시적으로 다루는지 확인한다.
- class owner descriptor 가 없는 현재 형식에서 OOS file tracker 항목을 lock 없이 반환하는 것이 읽기 전용 utility path 에 한정되어 있는지 확인한다.
- `spacedb` 에 새 출력 카테고리를 만들지 않고 heap totals 에 임시 포함하는 판단이 protocol/output churn 을 피하려는 안정화 범위와 맞는지 확인한다.

### Test Plan

커밋 기록 기준으로 다음 검증을 완료했다.

- `git diff --check` 통과.
- debug GCC preset 빌드 성공.
- OOS 행이 있는 DB 를 만들고 `diagdb` file table/capacity 출력, `spacedb` file accounting, `checkdb` file tracker iteration 이 `FILE_OOS` assertion 없이 완료되는 것을 확인.
- targeted CTP `utility_19` 성공.
- `cbrd_26527`, `tbl_enc_14` 는 아직 실패하지만 실패 원인은 `FILE_OOS` assertion/fatal 이 아니라 별도 expected-output 가정 차이로 분류.

남은 제한 사항은 의도한 범위 밖이다. `spacedb` 에 OOS 전용 행을 추가하려면 `SPACEDB_FILE_TYPE`, network packing, 출력 라벨, message catalog, QA answer 를 함께 갱신해야 한다. OOS 파일을 어느 table 에 귀속할지 보려면 `FILE_OOS` descriptor 에 owner heap/class metadata 를 저장하는 별도 설계가 필요하다.
