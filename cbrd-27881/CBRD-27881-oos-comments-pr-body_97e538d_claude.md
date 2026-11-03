https://jira.cubrid.org/browse/CBRD-27888

## Purpose

- 상위 작업 CBRD-27881은 `feature/oos-merge`의 OOS 코드에서 정리할 부분을 찾아, 동작을 바꾸지 않는 작은 PR로 나누어 정리하는 작업입니다.
- 이 PR은 지금의 코드와 다른 사실을 말하는 OOS 주석을 바로잡습니다. 실행 코드는 바뀌지 않습니다.
- AS-IS: 일부 주석이 존재하지 않는 검사, 이미 없어진 구현, 위치가 틀린 줄 번호, commit hash를 근거로 듭니다. heap 삭제와 갱신 경로의 주석은 OOS를 즉시 지우는 조건을 "SA_MODE"라고 적지만, 실제 조건은 `!is_mvcc_op`입니다.
- TO-BE: 각 주석은 지금의 코드가 하는 일을 설명합니다.

## Implementation

- `vacuum.c`, `vacuum_oos.cpp`: 없는 검사와 commit hash 대신 실제 조건과 이유를 적습니다. 중복된 성능 TODO를 줄입니다.
- `heap_file.c`: 즉시 삭제 조건을 `!is_mvcc_op`(SA_MODE, MVCC를 쓰지 않는 클래스, in-place update)로 적고, 줄 번호 참조를 블록 이름으로 바꿉니다.
- `oos_file.cpp`, `oos_file.hpp`: 없어진 `upper_bound`와 정렬 벡터 설명, 끝난 header TODO, 통계 필드 설명을 고칩니다.
- `locator.h`: `LC_IS_FLUSH_INSERT`의 오래된 TODO를, `LC_FLUSH_INSERT_OOS`를 포함하는 이유로 바꿉니다.
- `log_manager.c`: 주석만 담은 빈 `if` 블록을 같은 내용의 주석으로 바꿉니다.

## Remarks

- 변경 규모는 7개 파일, 38줄 추가, 44줄 삭제입니다.
- 주석을 제거하고 token을 비교하면, 빈 `if` 블록 하나 외에는 차이가 없습니다. 이 `if`는 지역 포인터의 필드를 비교할 뿐이고 본문이 비어 있습니다.
- 독립 리뷰가 새 주석을 하나씩 코드와 대조했습니다. 리뷰에서 같은 함수에 남아 있던 "SA_MODE" 표현 세 곳을 찾아 함께 고쳤습니다.
- 진행 중인 PR들의 변경 위치와 겹치지 않습니다.
