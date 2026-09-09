https://jira.cubrid.org/browse/CBRD-27400

## Purpose

- AS-IS: `feat/oos`의 JDBC 동시 갱신·조회 테스트 `bug_bts_4633`에서 로그 위치의 페이지 번호와 오프셋을 서로 다른 시점에 읽어 서버가 종료됐다.
- TO-BE: 페이지 전환 시 로그 위치를 한 번에 게시하고, 관련 조회 경로도 한 번에 읽어 이 잘못된 조합을 방지한다.

PR #6864의 GitHub Actions run `34207150213`, shard 34에서 `log_get_undo_record`의 assert를 확인했다. 이 변경은 develop 대상 PR #7904의 `a59029274`를 `feat/oos`의 `f4299ac0c` 위에 적용한 별도 backport다. 소스 커밋은 `1efcabd2f`다.

## Implementation

`LOG_LSA`는 페이지 번호와 페이지 안 오프셋으로 구성된 8바이트 로그 위치다. `logpb_next_append_page`가 두 필드를 따로 바꾸고 조회 스레드도 따로 읽으면, 이전 페이지 번호와 새 오프셋이 합쳐질 수 있다.

원래 수정의 네 파일을 그대로 적용했다.

- `log_lsa.hpp`: 플랫폼별 8바이트 원자 복사 함수 `lsa_atomic_load`와 `lsa_atomic_store`를 제공한다. OOS 브랜치의 기존 `LOG_LSA_QUEUE`는 유지한다.
- `log_page_buffer.c`: 다음 페이지 위치를 지역 변수로 완성한 뒤 한 번에 게시한다. `logpb_fetch_page`도 원자 복사로 읽는다.
- `log_manager.c`: `log_get_undo_record`의 위치 조회를 원자 복사로 바꾼다. 기존 assert는 유지한다.
- `heap_file.c`: 이전 버전을 찾는 두 위치 조회를 같은 함수로 바꾼다.

원래 PR의 알고리즘을 바꾸거나 오류를 숨기는 조건을 추가하지 않았다. CDC의 과거 값 보존은 CBRD-26939 / PR #7897에서 다룬다.

## Remarks

### Verification

GCC debug 구성으로 컴파일·설치했다. 별도 Linux PID, IPC, mount, network namespace와 private `/tmp`에서 검증하여 다른 데이터베이스 서비스와 분리했다.

| 검증 | 결과 |
| --- | --- |
| 원래 `bug_bts_4633.sh` 전체 실행 | `bug_bts_4633-1 : OK`, 168초; 서버 로그에 assert/abort 없음 |
| testcase revision | `777b97745076ba2c48cf7e103857f0abbc765b5d` |
| 구성된 CTest 전체 | 27/27 통과, 141.65초 |
| Standards / Spec 독립 리뷰 | 각각 지적 0개 |
| 저장소 형식 검사 | 통과; 들여쓰기만 바뀐 부분 없음 |

위 테스트는 커밋 직전 동일한 패치로 빌드했다. 빌드의 버전 문자열은 기본 커밋 `f4299ac`를 표시하므로 소스 패치와 바이너리 해시를 별도 검증 기록에 남겼다. 최초 namespace 빌드는 Gradle이 namespace의 root 사용자 캐시를 찾는 설정 문제로 실패했고, 실제 Gradle 캐시를 지정한 재실행에서 빌드와 27개 테스트가 통과했다. 커밋 후 형식 검사로 소스가 바뀌지 않았음을 확인했다.

원래 결함의 강제 스케줄링 재현과 최적화 바이너리의 단일 load/store 검증은 [기존 수리 보고서](https://github.com/vimkim/my-cubrid-docs/blob/main/cbrd-27400/CBRD-27400-append-lsa-atomic-torn-read_a590292_claude.md)에 있다. 이번 debug 실행 한 번으로 간헐적 결함의 모든 스케줄을 검증했다고 주장하지 않는다. Windows 실행은 검증하지 않았다.

`oos_file.cpp`의 공간 회수 기준을 계산하는 별도 위치 조회는 원래 PR 범위 밖의 후속 작업이다. 이 backport가 모든 OOS 위치 조회를 원자화한다고 주장하지 않는다. 원격 CI 검증은 별도로 진행한다.
