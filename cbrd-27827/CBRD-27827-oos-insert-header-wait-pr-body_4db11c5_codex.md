https://jira.cubrid.org/browse/CBRD-27827

## Purpose

- 같은 테이블에 여러 세션이 OOS 값을 저장할 때, 정상적인 파일 헤더 경합으로 INSERT가 실패하거나 서버가 종료되는 문제를 고칩니다.
- AS-IS: 후보 페이지 검색의 강제 무대기 설정이 소유 확인에 필요한 파일 헤더 읽기까지 막습니다.
- TO-BE: 바쁜 후보 페이지는 건너뛰고, 파일 헤더의 소유 확인은 원래 트랜잭션의 대기 정책을 따릅니다.

## Implementation

- `oos_stats_find_page_in_bestspace`의 대기 시간 설정·복원과 관련 변수 등 7줄을 제거했습니다. 후보 페이지의 `PGBUF_CONDITIONAL_LATCH`는 유지합니다.
- 실제 CS 서버에 여러 클라이언트가 동시에 INSERT하는 `test_oos_concurrent_insert.py`를 추가했습니다. 행 수와 payload 일치 여부, 실제 OOS 저장을 검사합니다. 생성한 테이블과 로그는 보존합니다.

## Remarks

- PR 7990의 [hornetmj 리뷰 R1](https://github.com/CUBRID/cubrid/pull/7990#discussion_r4398825716)에 대응합니다.
- 수정 전 debug 빌드에서 8세션의 첫 실행이 `file_manager.c:6924`의 assertion으로 서버를 종료시키는 것을 재현했습니다.
- 수정 후 8세션 × 1,500행을 10회 실행했습니다. 총 120,000행의 payload가 일치했고, 각 테이블의 OOS 레코드 12,000개를 확인했습니다.
- 기존 bestspace 23개와 성장·회수 11개 테스트가 통과했습니다. setup·cleanup을 포함한 집중 CTest 결과는 4/4입니다.
- 새 스크립트는 실행 중인 CS DB에 수동으로 실행하는 회귀 도구입니다. CTest에 자동 등록하지 않았습니다. release와 DELETE·vacuum 혼합 부하는 이번 로컬 검증에서 실행하지 않았습니다.
