https://jira.cubrid.org/browse/CBRD-27400

## Purpose

- AS-IS: 동시 갱신·조회 중 로그 위치를 잘못 읽으면 `bug_bts_4633`에서 서버가 종료됐습니다.
- TO-BE: 페이지 전환 시 로그 위치를 한 번에 쓰고 읽어 잘못된 위치 조합을 방지합니다.

## Implementation

- develop 대상 PR #7904의 `a59029274`를 `feat/oos`에 적용했습니다.
- 페이지 전환과 관련 조회 경로에 8바이트 원자 복사를 적용했습니다.
- 기존 assert와 OOS 브랜치의 로그 위치 큐를 유지했습니다.

## Remarks

- 원래 JDBC 테스트와 구성된 CTest 27개가 격리 환경에서 통과했습니다.
- Standards와 Spec 리뷰에 지적이 없었으며 코드 형식 검사를 통과했습니다.
- 별도 OOS 공간 회수 경로의 위치 조회는 후속 작업입니다.
- 자세한 설명: https://github.com/vimkim/my-cubrid-docs/blob/main/cbrd-27400/CBRD-27400-oos-append-lsa-backport_1efcabd_codex.md
