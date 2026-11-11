https://jira.cubrid.org/browse/CBRD-28037

## Purpose

- OOS 단위 테스트 유지보수자가 페이지의 남은 공간을 조회하는 helper를 한 곳에서 관리하도록 R-16을 정리합니다.
- AS-IS: 단독 실행(SA) 테스트 2개 파일과 서버(SERVER) 테스트 3개 파일에 같은 helper가 각각 있습니다.
- TO-BE: 기존 공용 헤더의 helper를 5개 파일에서 함께 사용합니다.

## Implementation

- `test_oos_utils.hpp`에 `get_free_space_of_oid_page(THREAD_ENTRY *, const OID &)`를 추가하고 `slotted_page.h`를 직접 포함합니다.
- 파일별 중복 정의 5개를 제거하고 호출 26곳에 namespace와 기존 thread pointer를 명시합니다.
- 페이지 조회 조건, 읽기 잠금, 조회 실패 시 `-1` 반환과 페이지 반환 시점을 보존합니다.

## Remarks

- 테스트 코드 6개 파일만 변경합니다. 기존 assertion을 유지합니다.
- 리모트 `feature/oos-merge` 기준 GCC Debug 빌드·설치와 프로젝트 코드스타일 검사를 통과했습니다.
- 관련 CTest 5개와 DB 준비·정리 fixture 2개가 모두 통과했습니다. 전체 SQL·medium·shell 회귀는 실행하지 않았습니다.
