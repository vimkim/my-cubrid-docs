# PR 7990 hornetmj 리뷰 대응 체크리스트

팀장님 리뷰를 하나씩 이해하고 결정한 뒤, 필요한 수정과 검증을 마친다. 이 문서는 OOS 작성자와 리뷰어가 다음 작업을 이어갈 수 있도록 진행 상태와 근거를 보존한다.

R1은 실제 동시 INSERT로 같은 assertion을 재현한 뒤 7줄을 삭제해 수정했다. 수정 후 CS 10회와 집중 CTest가 통과했다. 나머지 다섯 항목은 아직 수정하지 않았다.

분석일은 2026-10-29, Asia/Seoul이다. 대상은 [CUBRID/cubrid PR 7990](https://github.com/CUBRID/cubrid/pull/7990)이다. 검토 기준 소스는 `dcbf09e4f7fd02ff9c8fc6493ec8887fc2919d67`, 브랜치는 `feature/oos-merge`이다. 수집 당시 hornetmj님의 inline 리뷰 6개는 모두 미해결이며 outdated가 아니다. 빈 COMMENTED 리뷰 요약은 별도 작업으로 세지 않는다.

리뷰 원문의 재현 결과는 리뷰어의 관찰이다. 이 작업에서 직접 실행한 결과와 구분한다. 아래의 각 완료 표시는 해당 단계의 근거를 확보한 경우에만 바꾼다.

## 작업 범위와 재개 위치

- 기존 Work Item `508`에 이 체크리스트와 단계별 결과를 연결한다. 전체 PR 머지 완료를 이 문서의 초기 작성 완료와 혼동하지 않는다.
- 엔진 수정 작업은 `/home/vimkim/gh/cb/pr7990-hornet-r1`, `review/pr7990-hornet-r1`에서 시작한다. 수정 PR 스택의 trunk는 `feature/oos-merge`이다. 팀 리뷰와 해당 PR head 검증을 받은 뒤 GitHub PR로 반영한다.
- 문서 작업은 `/home/vimkim/gh/my-cubrid-docs-pr7990-hornet-review`, `docs/pr7990-hornet-review-20261029`에서 진행한다. 로컬 통합 대상은 문서 저장소 `main`이다.
- 각 항목의 순서는 검토, 이해, 결정, 수정, 검증, 기록이다. 하나의 수정과 검증을 마친 뒤 다음 수정을 시작한다.
- 현재 단계는 R1의 로컬 수정·검증 완료와 독립 JIRA·PR 준비이다. 앞선 직접 로컬 통합 승인 요청은 철회했다. 다음 기술 검토는 R5이다. R2부터 R6까지의 수정은 아직 시작하지 않았다.
- 현재 실행 모드는 `Babysit / threads-only`이다. 기존 PR의 충돌 해결, CI 재실행, 원격 push, 리뷰 답글 게시, thread resolve, PR 머지는 이 단계의 작업에 포함하지 않는다.

## 처리 순서

R1은 사용자가 지정한 링크이므로 먼저 다룬다. 이후에는 커밋된 행을 손상시킬 수 있는 R5, 교착 R2, 미사용 복구 인덱스 R6, 스윕 비용 R3 순서로 검토한다. R4는 리뷰어가 명시한 bestspace redesign 안정화 후 적용 계획을 먼저 확인한다. 이 순서는 작업 제안이며 아직 각 항목의 수정안을 승인한 것은 아니다.

| 순서 | 항목 | 사용자 영향 | 첫 확인 사항 | 상태 |
| --- | --- | --- | --- | --- |
| 1 | [R1. 동시 INSERT의 파일 소유 확인 실패](#r1-동시-insert의-파일-소유-확인-실패) | INSERT 실패, debug abort | zero-wait 범위와 파일 헤더 경합 | 로컬 검증 완료, 티켓·PR 준비 |
| 2 | [R5. relocation undo가 재사용 슬롯을 덮어씀](#r5-relocation-undo가-재사용-슬롯을-덮어씀) | 커밋 행 손실, 힙 손상 | forward 페이지 공개와 sysop 경계 | 대기 |
| 3 | [R2. vacuum과 새 힙 페이지 할당의 교착](#r2-vacuum과-새-힙-페이지-할당의-교착) | INSERT 장시간 대기와 abort | PR 8235의 처리 범위와 미통합 변경 | 대기 |
| 4 | [R6. 미사용 복구 인덱스 제거](#r6-미사용-복구-인덱스-제거) | 불필요한 로그 형식 번호 고정 | 로그 생산자 존재 여부 | 대기 |
| 5 | [R3. 페이지 할당 시 전체 파일 스윕](#r3-페이지-할당-시-전체-파일-스윕) | 큰 파일의 INSERT 지연 | 스윕 발동 조건과 진행 위치 | 대기 |
| 6 | [R4. 재시작 후 bestspace 복원](#r4-재시작-후-bestspace-복원) | 빈 공간 미사용, 파일 증가 | redesign 후 적용 계획과 R3 의존성 | 후속 계획 확인 대기 |

## 합의한 PR 방식과 의존 관계

2026-10-29 사용자는 빠른 순차 리뷰를 위해 하나의 stacked PR 구성을 선택했다. 수정끼리 필수 의존성이 없는 경우에도 이 전달 순서를 사용한다. 수정량이 작더라도 독립된 결함의 티켓, 검증 근거와 리뷰를 유지한다. 기존 티켓이 같은 문제를 다루면 새 티켓을 중복 생성하지 않는다.

스택의 trunk는 `feature/oos-merge`이다. 작업 순서는 R1, R5, R2, R6, R3으로 둔다. 각 PR의 base는 바로 아래 작업 브랜치다. 이 순서는 리뷰와 전달을 위한 순서이며, 모든 수정 사이에 기술적 필수 의존성이 있다는 뜻은 아니다. R4는 bestspace redesign 후속 계획과 CBRD-27213의 범위를 확인한 뒤 포함 여부를 결정한다.

| 관계 | 현재 확인한 내용 | 처리 |
| --- | --- | --- |
| R1 | 다른 수정 없이 원래 기준에서 수정 전후 검증 완료 | 첫 PR로 준비 |
| R2와 R5 | 준비 단계의 VFID 조회와 실행 단계의 forward 슬롯 공개 문제다. 같은 vacuum 흐름과 래치 계약을 공유하지만 필수 선행 관계는 확인하지 못했다. | 서로의 수정 후 통합 검증. 스택 순서 자체를 기술적 의존성으로 설명하지 않음 |
| R3와 R4 | R4의 힌트 복원을 R3의 회수 스윕에 넣으면 구현 의존성이 생길 수 있다. redesign으로 처리하는 경우는 별도 범위다. | R4 구현 방향을 정할 때 의존 관계 확정 |
| R6 | 미사용 복구 인덱스와 후속 번호 조정은 다른 수정과 직접 의존하지 않는다. | 독립 검증 단위를 유지하고 번호 변경 후에는 새 테스트 DB 사용 |

GitHub 기본 stacked PR은 모든 브랜치가 같은 저장소에 있어야 하며 cross-fork 스택을 지원하지 않는다. [공식 요구 사항](https://docs.github.com/en/pull-requests/reference/stacked-pull-requests). 당시에는 `CUBRID/cubrid`의 `origin`에 스택 브랜치를 게시하는 방향을 기록했으나, 이후 사용자가 조직 저장소의 브랜치 증가를 우려하며 `vimkim/cubrid` 구성을 재검토하도록 요청했다. 현재 게시 위치는 확정 전이다. 조회 당시 조직 저장소 권한은 `WRITE`, 개인 fork 권한은 `ADMIN`이었다.

같은 `vimkim/cubrid` 안에 trunk와 모든 작업 브랜치, PR을 두는 스택은 같은 저장소 조건을 만족한다. 제한되는 것은 `CUBRID/cubrid`와 fork를 가로지르는 native stack이다. fork 안에서 PR을 리뷰·머지하면 조직 저장소에 자동 반영되지 않으므로, 이후 upstream 반영 절차가 별도로 필요하다. 조직 저장소의 PR마다 리뷰 이력을 남기려면 fork의 독립 브랜치에서 `CUBRID/cubrid:feature/oos-merge`로 각각 일반 PR을 열 수도 있다. [Fork의 upstream PR](https://docs.github.com/en/pull-requests/how-tos/create-pull-requests/creating-a-pull-request-from-a-fork).

현재 소스 검토만으로 변경이 많이 겹친다고 볼 근거는 없다. R2와 R5는 같은 vacuum 흐름이지만 준비와 실행의 수정 지점이 다르고, R1과 R3은 같은 파일의 다른 함수다. R3과 R4는 스윕을 공유하는 수정안을 택할 때 결합될 수 있다. 실제 수정은 R1만 작성했으므로 나머지 패치 사이의 충돌 수를 측정한 것은 아니다.

이 기록 시점에는 스택을 초기화하거나 원격에 게시하지 않았다. R1 티켓을 확정한 뒤 ticket 이름의 브랜치와 PR 본문을 준비한다. PR 게시와 머지의 권한은 각 단계에서 현재 지시와 저장소 정책에 따라 확인한다.

## 진행 점검

- [x] **Blocking first steps.** 개인 정책, 두 저장소의 작업 상태, PR head, 세 종류의 댓글과 thread 상태를 확인한다.
- [x] **Independent workstreams.** 수정은 R1부터 순서대로 진행한다. R1의 호출 흐름 설명만 읽기 전용으로 독립 검토한다.
- [x] **Shared mutable state.** 원래 source와 docs checkout을 보존한다. 각 task worktree의 작성자는 한 명으로 유지한다.
- [x] **Smallest safe decomposition.** R1의 최소 수정과 동시성 검증을 한 단위로 한다. R2와 R5는 같은 vacuum 경로를 다루므로 이후 순서를 조정할 때 기존 변경을 다시 확인한다.

## 공통 완료 조건

1. 원문과 현재 코드가 같은 문제를 가리키는지 확인한다.
2. 호출자 계약, 보유 래치, 대기 순서, 실패 처리와 복구 경계를 설명한다.
3. 수용, 대안, 후속 작업, 반박 중 하나를 근거와 함께 결정한다.
4. 필요한 최소 수정을 task branch에 작성한다.
5. 문제를 보여 주는 실행과 수정 후 실행을 남긴다. 실행하지 못했으면 검증 미완료로 표시한다.
6. diff를 검토하고 task 파일만 커밋한다. 결과와 다음 단계를 이 문서에 갱신한다.
7. 소스 수정은 해당 JIRA와 독립 PR로 팀 리뷰와 head 검증을 받은 뒤 머지한다. 로컬 검증 완료만으로 feature 브랜치에 직접 통합하지 않는다. 문서 저장소의 통합은 기존 로컬 승인 절차를 따른다.

## R1. 동시 INSERT의 파일 소유 확인 실패

[리뷰 원문](https://github.com/CUBRID/cubrid/pull/7990#discussion_r4398825716). 대상은 `src/storage/oos_file.cpp`의 `oos_stats_find_page_in_bestspace`이다.

- [x] 원문을 수집한다.
- [x] 현재 함수에 `old_wait_msecs`, `LK_FORCE_ZERO_WAIT` 설정, 종료 시 복원이 있음을 확인한다.
- [x] 후보 페이지는 이미 `PGBUF_CONDITIONAL_LATCH`로 고정함을 확인한다.
- [x] `file_is_vpid_in_file`의 헤더 읽기와 zero-wait 실패 전파를 확인한다.
- [x] 할당 및 회수 경로의 래치 순서를 비교하고 수정 시 교착 가능성을 판단한다.
- [x] 동일 테이블에 여러 세션이 OOS 값을 넣는 회귀 테스트를 준비하고 수정 전 실패를 확인한다.
- [x] 함수 전체의 대기 시간 변경을 제거하는 안을 결정하고 수정한다.
- [x] 수정 후 테스트, 빌드, 관련 bestspace 검증을 통과한다.
- [x] 근거, 커밋, 검증 한계와 답글 초안을 기록한다.

소스에서 확인한 사실은 [대기 시간 변경](https://github.com/CUBRID/cubrid/blob/dcbf09e4f7fd02ff9c8fc6493ec8887fc2919d67/src/storage/oos_file.cpp#L560-L582), [조건부 후보 래치와 소유 확인](https://github.com/CUBRID/cubrid/blob/dcbf09e4f7fd02ff9c8fc6493ec8887fc2919d67/src/storage/oos_file.cpp#L654-L706), [대기 시간 복원](https://github.com/CUBRID/cubrid/blob/dcbf09e4f7fd02ff9c8fc6493ec8887fc2919d67/src/storage/oos_file.cpp#L768-L772)이다. 오류 코드를 추가하는 것만으로는 경합으로 인한 INSERT 실패가 없어지지 않는다는 판단은 이 호출 흐름에 근거한다. 수정 전 debug 실행에서 아래와 같이 같은 위치의 assertion을 직접 재현했다.

채택한 최소 수정은 `old_wait_msecs`와 설정·복원 호출을 제거하는 것이다. 후보 페이지의 조건부 래치는 유지한다. 새 대기 모드나 재시도 계층은 추가하지 않는다.


### R1에서 이해한 실패 경로

여기서 OOS 통계 헤더와 파일 관리자 헤더는 서로 다른 페이지다. 후보 검색은 OOS 통계 헤더를 쥔 상태로 후보 데이터 페이지를 조건부 고정한다. 그다음 소유 확인은 파일 관리자 헤더를 읽는다.

문제는 조건부 정책의 범위다. `PGBUF_CONDITIONAL_LATCH`는 후보 페이지 한 번에만 적용된다. `xlogtb_reset_wait_msecs`는 트랜잭션의 `wait_msecs`를 바꾸므로 뒤따르는 파일 헤더 읽기에도 영향을 준다. 버퍼 관리자는 `LK_FORCE_ZERO_WAIT`를 보면 무조건 요청을 조건부 요청으로 바꾼다. 다른 세션의 할당이 파일 헤더를 잡고 있으면 이 읽기는 오류 설정 없이 실패할 수 있다. [버퍼 관리자의 조건 변경](https://github.com/CUBRID/cubrid/blob/dcbf09e4f7fd02ff9c8fc6493ec8887fc2919d67/src/storage/page_buffer.c#L2247-L2255), [소유 확인의 assertion](https://github.com/CUBRID/cubrid/blob/dcbf09e4f7fd02ff9c8fc6493ec8887fc2919d67/src/storage/file_manager.c#L6906-L6926).

삭제 후에는 바쁜 후보를 건너뛰는 정책이 그대로이고, 소유 확인만 원래 트랜잭션의 대기 정책을 따른다. 정상적인 동시 할당을 INSERT 오류로 바꾸던 원인을 없앤다.

확인한 할당 경로는 OOS 통계 헤더를 먼저 놓고 파일 헤더와 새 페이지를 잡는다. 회수 경로는 같은 OOS 통계 헤더로 후보 검색과 직렬화된다. 이 두 경로와 파일 순회의 조건부 데이터 래치를 확인한 범위에서 새 교착 순환을 찾지 못했다. [할당 전 통계 헤더 해제](https://github.com/CUBRID/cubrid/blob/dcbf09e4f7fd02ff9c8fc6493ec8887fc2919d67/src/storage/oos_file.cpp#L3144-L3152), [회수의 헤더와 후보 래치](https://github.com/CUBRID/cubrid/blob/dcbf09e4f7fd02ff9c8fc6493ec8887fc2919d67/src/storage/oos_file.cpp#L1610-L1629), [파일 순회의 조건부 고정](https://github.com/CUBRID/cubrid/blob/dcbf09e4f7fd02ff9c8fc6493ec8887fc2919d67/src/storage/file_manager.c#L7430-L7435). 모든 가능한 동시 동작에 대한 형식적 증명은 아니다.

### R1의 실행과 최소 수정

새 task worktree에 `debug_gcc`를 구성하고 별도 설치 및 workenv를 만들었다. 이 작업에서 만든 `testdb`만 사용한다. 소스에는 계측이나 스케줄링 훅을 넣지 않았다. 엔진의 baseline은 `dcbf09e`이며 Python 스크립트만 추가한 상태에서 재현했다.

테스트 입력은 8개 CS 세션, 세션당 1,500행, 행마다 6,000자 값이다. 세션별 ID 범위는 겹치지 않으며, seed가 고정된 난수로 세션별 payload를 만든다. 열에는 `STORAGE FORCE_OUTLINE`을 지정한다. 각 INSERT는 autocommit이다. 스크립트는 행 수와 모든 payload의 일치 여부 및 `SHOW HEAP OOS`의 레코드 수를 검사한다. 서버와 DB를 생성하거나 삭제하지 않는다. 생성한 테이블과 로그를 보존한다.

기본 실행 방법은 다음과 같다. 기존 CS 서버와 passwordless DBA 접속이 필요하며 출력 디렉터리는 새 경로여야 한다.

```sh
python3 unit_tests/oos/scripts/test_oos_concurrent_insert.py testdb /new/output/path --rounds 10 --timeout 120
```

수정 전 첫 회차에서 서버가 다음 메시지로 abort했다. 클라이언트도 exit 1과 서버 실패 오류를 반환했다. 10회 요청이었으나 첫 회차 실패에서 중단했으므로 10회 실패라고 세지 않는다.

```text
cub_server: /home/vimkim/gh/cb/pr7990-hornet-r1/src/storage/file_manager.c:6924: DISK_ISVALID file_is_vpid_in_file(THREAD_ENTRY*, const VFID*, const VPID*): Assertion `er_errid () != NO_ERROR' failed.
ERROR: Your transaction has been aborted by the system due to server failure or mode change.
```

원본 증거는 `/home/vimkim/temp/pr7990-hornet-review-20261029/baseline/summary.json`과 `server-start.err`이다. 앞선 2세션·20행 smoke는 csql 출력 파서를 확인했다. 첫 필드의 `<00001>` 표기를 반영한 뒤 smoke가 통과했다. 이를 R1 결함 재현으로 세지 않는다.

수정은 `old_wait_msecs` 선언, 강제 zero-wait 설정, 복원 및 두 설명 주석의 삭제다. 함수 시그니처와 후보 래치는 바꾸지 않았다. 기존 SA_MODE `test_oos_bestspace`만으로는 이 경합을 확인할 수 없으므로 실제 CS 실행을 함께 사용한다. CS 스크립트는 타이밍에 의존하는 경합 회귀 테스트이며 매번 같은 인터리빙을 강제하지 않는다. release 빌드 및 DELETE·vacuum 혼합 부하는 아직 실행하지 않았다.

### R1의 검증 결과와 커밋

| 검증 | 입력과 범위 | 관찰 결과 |
| --- | --- | --- |
| 수정 전 CS 재현 | debug, 8세션 × 1,500행, 6KB payload | 첫 회차에서 `file_manager.c:6924` assertion으로 서버 abort, 클라이언트 exit 1 |
| 수정 후 CS 회귀 | 동일 입력으로 새 테이블을 만들어 10회 | 10회 모두 통과. 총 120,000행의 개수와 payload 일치. 각 테이블의 OOS 레코드 12,000개 확인. 클라이언트 ERROR와 서버 assertion 미관찰 |
| 기존 bestspace | `test_oos_bestspace` | GoogleTest 23개 통과 |
| 기존 성장·회수 | `test_oos_growth_sweep` | GoogleTest 11개 통과 |
| CTest fixture 포함 | 두 테스트와 setup, cleanup | 4/4 통과 |
| 빌드와 스타일 | debug 빌드·설치, pre-commit codestyle, `git diff --check` | 통과. formatter의 추가 변경 없음 |

기존 CTest의 첫 시도에서는 fixture setup이 실패해 두 엔진 테스트가 실행되지 않았다. 최초 CMake 구성은 workenv 초기화 전이어서 `CUBRID_DATABASES`가 빈 값으로 CTest에 저장돼 있었다. 초기화된 환경에서 CMake를 다시 구성한 뒤 같은 두 테스트와 fixture가 모두 통과했다. 이 실패를 엔진 테스트 실패나 불안정 테스트로 분류하지 않는다. 원래 실패 로그도 보존한다.

집중 검증의 CTest 선택식은 다음과 같다. 구성 때 선택한 설치와 DB registry가 유효해야 한다.

```sh
ctest --test-dir "$CUBRID_BUILD_DIR" -R '^(test_oos_bestspace|test_oos_growth_sweep)$' --output-on-failure --verbose
```

소스 커밋은 다음 순서다. 스택의 trunk에는 아직 반영하지 않았다.

1. `3c39a813a`는 재현·회귀 스크립트를 추가한다. 이 커밋의 엔진은 수정 전이다.
2. `4db11c5f1`은 함수 전체의 zero-wait 설정·복원 등 7줄을 제거한다.

검증 원본은 `/home/vimkim/temp/pr7990-hornet-review-20261029/` 아래에 보존한다. `fixed/summary.json`은 회차별 행 수와 payload 일치 수, OOS 레코드 수를 담는다. `fixed-provenance.json`은 검증 당시 엔진 diff, 바이너리 경로와 SHA-256을 담는다. `focused-ctest.log`는 첫 fixture 실패이며 `focused-ctest-reconfigured.log`는 재구성 후 통과 로그다. 실험용 서버와 이 workenv의 서비스는 종료했다. 테스트 DB와 생성 테이블은 남겨 두었다.

남은 검증 한계는 release 빌드, DELETE·vacuum 혼합 부하, 임의의 상위 호출자가 원래 zero-wait인 경우다. 새 스크립트는 수동 실행하는 CS 회귀 도구이며 CTest에 자동 등록하지 않았다. 수정 후 10회 통과는 가능한 모든 인터리빙의 안전성을 증명하지 않는다.

### R1 답글 초안

> 지적하신 경합을 debug 빌드에서 재현했습니다. 8개 세션의 동시 INSERT 첫 회차에 `file_is_vpid_in_file`의 동일한 assertion으로 서버가 abort했습니다. 후보 검색 전체의 `LK_FORCE_ZERO_WAIT` 설정과 복원을 제거하고 후보 페이지의 조건부 래치는 유지했습니다. 실제 CS 세션으로 행 수와 payload, OOS 레코드를 확인하는 회귀 스크립트를 추가했습니다. 수정 후 같은 입력으로 10회, 총 120,000행이 모두 통과했고 bestspace 23개와 성장·회수 11개 테스트도 통과했습니다. release와 DELETE·vacuum 혼합 부하는 이번에 실행하지 않았습니다.

초안은 아직 게시하지 않았다. GitHub thread도 미해결 상태로 유지한다.

## R5. relocation undo가 재사용 슬롯을 덮어씀

[리뷰 원문](https://github.com/CUBRID/cubrid/pull/7990#discussion_r4409499688). 대상은 `vacuum_heap_record`의 `REC_RELOCATION` 경로이다.

- [x] 원문을 수집한다.
- [ ] forward 슬롯을 비우는 시점, bestpage 공개, 래치 해제, OOS 삭제, sysop abort 순서를 확인한다.
- [ ] 기존 CBRD-27781의 OOS 슬롯 충돌과 이번 힙 forward 슬롯 충돌의 차이를 확인한다.
- [ ] OOS 삭제 실패를 주입하고 동시 INSERT로 슬롯 재사용을 재현한다.
- [ ] 슬롯을 공개해도 되는 복구 경계를 결정하고 최소 수정한다.
- [ ] debug와 release의 오류 경로, 행 보존, 인덱스와 힙 일치, `checkdb`를 확인한다.
- [ ] 결과와 답글 초안을 기록한다.

리뷰어는 debug abort와 release의 커밋 행 손실을 보고했다. 이 작업에서 독립 재현하거나 기존 티켓과 동일한 결함이라고 판단한 상태는 아니다.

## R2. vacuum과 새 힙 페이지 할당의 교착

[리뷰 원문](https://github.com/CUBRID/cubrid/pull/7990#discussion_r4399323155). 대상은 `vacuum_heap_oos_delete_within_sysop`과 `REC_RELOCATION` 호출자이다.

- [x] 원문을 수집한다.
- [ ] PR 8235의 현재 변경과 PR 7990에 포함된 범위를 확인한다.
- [ ] `REC_HOME`, `REC_BIGONE`, `REC_RELOCATION`의 래치 순서와 재시작 처리를 비교한다.
- [ ] 마지막 힙 페이지를 vacuum이 보유하고 INSERT가 새 페이지를 할당하는 실행을 재현한다.
- [ ] 조건부 헤더 조회, 페이지 해제, 대기, 레코드 재확인 구조를 결정한다.
- [ ] R5의 sysop 경계를 보존하면서 필요한 수정을 적용한다.
- [ ] 교착 재현과 일반 INSERT·DELETE·vacuum 실행을 검증하고 결과를 기록한다.

PR 8235가 고쳤을 수 있다는 원문의 설명은 확인할 대상이다. 이미 해결된 항목으로 표시하지 않는다.

## R6. 미사용 복구 인덱스 제거

[리뷰 원문](https://github.com/CUBRID/cubrid/pull/7990#discussion_r4409612618). 대상은 `RVOOS_NOTIFY_VACUUM`이다.

- [x] 원문을 수집한다.
- [ ] 전체 소스에서 해당 로그의 생산자와 소비자를 검색한다.
- [ ] `recovery.h`, `recovery.c`, `mvcc.h`의 네 참조와 후속 번호를 확인한다.
- [ ] 현재 저장 형식 정책과 번호 재배치의 영향을 판단한다.
- [ ] 불필요한 참조를 제거하고 후속 인덱스를 조정한다.
- [ ] `rv_check_rvfuns`, OOS 변경 중 강제 종료와 복구, `checkdb`를 확인한다.
- [ ] 결과와 답글 초안을 기록한다.

## R3. 페이지 할당 시 전체 파일 스윕

[리뷰 원문](https://github.com/CUBRID/cubrid/pull/7990#discussion_r4399899312). 대상은 `oos_alloc_page_with_reclaim`과 `oos_reclaim_sweep_step`이다.

- [x] 원문을 수집한다.
- [ ] `pending_deletes`, `swept_this_boot`, sweep cursor의 실제 상태 전이를 확인한다.
- [ ] vacuum 즉시 회수와 LSA 지연, non-MVCC 삭제, SA 즉시 삭제를 구분한다.
- [ ] 스윕 발동 조건 개선과 할당당 검사 상한을 각각 검토한다.
- [ ] 할당당 검사 페이지 수와 빈 페이지 회수의 진행 보장을 검증할 방법을 정한다.
- [ ] R4의 힌트 복원 계획과 충돌하지 않는 최소 수정을 결정한다.
- [ ] 실제 부하로 지연과 재사용을 검증한다. 리뷰어 수치를 자신의 측정으로 쓰지 않는다.
- [ ] 결과와 답글 초안을 기록한다.

## R4. 재시작 후 bestspace 복원

[리뷰 원문](https://github.com/CUBRID/cubrid/pull/7990#discussion_r4409283403). 원문은 bestspace redesign 안정화 후 OOS에 적용할 계획을 먼저 밝힌다.

- [x] 원문과 후속 적용 계획을 수집한다.
- [ ] redesign의 소유 작업과 적용 시점을 확인한다.
- [ ] `num_pages`와 `num_other_high_best`의 기록 위치, 임시 헤더 갱신, scan cursor를 확인한다.
- [ ] 재시작 전후 동일한 빈 공간과 입력으로 페이지 재사용을 비교한다.
- [ ] 지금 수정할 부분과 redesign에서 처리할 부분을 결정한다.
- [ ] 지금 수정하는 경우 R3의 bounded sweep과 함께 회수·힌트 등록을 검증한다.
- [ ] 후속 처리라면 추적 위치와 완료 조건을 기록하고 원문을 해결 처리하지 않는다.

## 적용한 원칙과 달라진 선택

| 원칙 | 이번 작업에서 바꾼 선택 |
| --- | --- |
| Sequence Work into Verifiable Units | 여섯 수정을 한 번에 묶지 않고 R1의 재현, 수정, 검증을 첫 단위로 삼았다. |
| Fix Root Causes | `DISK_ERROR`에 오류 코드만 추가하지 않고 파일 헤더 읽기를 강제 무대기로 바꾸던 설정을 제거했다. |
| Laziness Protocol | 새 래퍼나 재시도 코드를 만들지 않고 기존 함수의 대기 시간 변경만 삭제했다. |
| Model the Domain | 테스트 세션을 겹치지 않는 ID 범위, payload, 입력 파일, 결과 파일의 목록으로 표현했다. |
| Build the Lever | 일회성 수동 부하 대신 같은 입력을 다시 실행하고 저장 결과를 검사하는 Python 스크립트를 남겼다. |
| Prove It Works | 소스 검토와 빌드에 더해 실제 CS 서버에서 수정 전 장애와 수정 후 저장 결과를 확인한다. |

## 결정과 검증 기록

| 날짜 | 항목 | 결정 또는 결과 | 근거 | 남은 일 |
| --- | --- | --- | --- | --- |
| 2026-10-29 | 전체 | R1부터 한 항목씩 수정하고 검증한다. R5는 그다음 우선 검토 대상으로 둔다. | 사용자의 단계별 진행 요청, R5의 커밋 행 손실 보고 | R1 통합 승인, 이후 R5 검토 |
| 2026-10-29 | R4 | 후속 적용 계획을 보존하고 즉시 수정 대상으로 확정하지 않는다. | 리뷰 원문의 redesign 안정화 후 적용 설명 | 소유 작업과 적용 시점 확인 |
| 2026-10-29 | R1 | 원인을 재현하고 zero-wait 설정을 제거했다. CS 10회와 집중 CTest 4개가 통과했다. | `3c39a813a`, `4db11c5f1`, 위 검증 결과 | 독립 PR 리뷰·검증. release와 혼합 부하는 미검증 |

수집 원본은 `/home/vimkim/temp/pr7990-hornet-review-20261029/review-snapshot.json`에 보관한다. 원본 JSON, 빌드 로그, 중간 산출물은 문서 저장소에 커밋하지 않는다.

2026-10-29 진행 방식 변경은 위의 "합의한 PR 방식과 의존 관계"를 따른다. 앞선 실행 결과와 당시 결정 기록은 보존한다.
