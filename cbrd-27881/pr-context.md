# R-16 draft PR 게시 기록

2026-11-11 Asia/Seoul 기준이다. OOS 단위 테스트 유지보수자가 페이지의 남은 공간을 조회하는 중복 helper를 한 곳에서 관리하도록 한다. 이 문서는 검토 당시 제안과 실제 게시 결과를 보존한다. 승인 근거는 사용자의 대화이며, 이 문서가 후속 작업의 승인을 대신하지 않는다.

## 소스와 대상

| 항목 | 값 |
| --- | --- |
| Ticket | CBRD-27881, R-16 |
| Operation | `create`, 새 draft PR |
| Target repository | `CUBRID/cubrid` |
| Base branch | `feature/oos-merge` |
| Observed remote base | `50619ce53ef7b0e6bc8b468b2065ae7da4ef592f` |
| Source repository | `vimkim/cubrid` |
| Source branch | `CBRD-27881-r16-free-space-pr` |
| SOURCE_COMMIT | `b8d6d6d606daaf301d42269c67b0bc83b4bddcc7` |
| Observed remote head | 없음. `git ls-remote vk refs/heads/CBRD-27881-r16-free-space-pr` 결과가 비어 있다. |
| Existing matching PR | 정확한 head와 base를 검색한 결과 없음. 생성 직전에 다시 확인한다. |
| Proposed title | `[CBRD-27881] Share the OOS test page free-space helper` |
| Proposed assignee | `vimkim` |
| Draft status | 사용자가 요청한 draft를 유지한다. |

이전 구현 커밋 `f1f5e0cbb4ac66d0efc197b0f9a62a669552d737`은 로컬 base `0034bc2fbca55c90a86ad48f43412d4616f5dc5f` 위에 있다. 그 base에는 관계없는 미게시 postpone 커밋 7개가 있다. 새 PR 브랜치는 실제 리모트 base에서 R-16 커밋 하나만 cherry-pick했다. 원래 구현 브랜치와 로컬 `feature/oos-merge`는 보존한다.

`git log BASE..HEAD`에는 R-16 한 커밋만 있다. diff는 `unit_tests/oos/`의 6개 파일이며 +41/-108이다. 기존 구현과 새 PR 커밋의 stable patch ID는 모두 `2baae436a4471b4cbbf2e8ad5ca7c4c17871935f`이다.

## 동작과 검증

데이터는 기존 `THREAD_ENTRY *`, 페이지를 식별하는 `OID`, 반환할 `int`이다. helper는 `OLD_PAGE_IF_IN_BUFFER`, `PGBUF_LATCH_READ`, `PGBUF_UNCONDITIONAL_LATCH`로 페이지를 고정한다. 실패하면 `-1`을 반환한다. 성공하면 `spage_get_free_space`로 남은 공간을 읽고 기존 `auto_unfixed_page_ptr`가 함수 종료 때 페이지를 반환한다.

- 새 base와 비교한 소스 token 검사는 통과했다. helper 본문, 26개 호출의 나머지 코드와 assertion, 공용 헤더의 나머지 코드가 같다.
- 프로젝트 `.github/workflows/codestyle.sh`를 변경 파일 6개에 적용해 추가 변경이 없음을 확인했다.
- 기존 독립 코드·주석 검토는 이전 구현 커밋에 대한 결과다. 새 PR의 patch ID가 같음을 확인했다. 새 base의 전체 코드에 대한 독립 리뷰 결과로 확대하지 않는다.
- 새 base의 `debug_gcc` 빌드·설치가 통과했다. 실제 CMake cache의 `CMAKE_BUILD_TYPE=Debug`, `UNIT_TEST_OOS=ON`과 관련 실행 파일 5개의 존재를 확인했다.
- 새 설치에 독립된 work environment를 `--no-db`로 초기화한 뒤 CMake를 다시 configure했다. CTest가 사용하는 DB registry도 이 환경을 가리킨다.
- `test_oos_delete`, `test_oos_bestspace`, `test_oos_delete_server`, `test_oos_mock_vacuum_server`, `test_oos_vacuum_server`와 DB 준비·정리 fixture 2개가 통과했다. 결과는 7/7, 실패 0이다.
- 이전 로컬 base의 빌드·설치와 CTest 7/7 결과는 새 base의 실행 결과와 구분한다.
- 이번 범위에서 전체 SQL·medium·shell 회귀, release 또는 sanitizer 실행은 하지 않았다.

관련 CTest의 선택 범위는 다음과 같다. 테스트용 설치와 DB 환경을 설정한 상태에서 실행한다. CTest는 필요한 DB 준비·정리 fixture도 함께 선택한다.

```sh
ctest --test-dir <build-dir> --output-on-failure --parallel 1 \
  -R '^(test_oos_delete|test_oos_bestspace|test_oos_delete_server|test_oos_mock_vacuum_server|test_oos_vacuum_server)$'
```

다음 명령으로 변경 범위를 확인한다.

```sh
git log --oneline 50619ce53ef7b0e6bc8b468b2065ae7da4ef592f..b8d6d6d606daaf301d42269c67b0bc83b4bddcc7
git diff --stat 50619ce53ef7b0e6bc8b468b2065ae7da4ef592f...b8d6d6d606daaf301d42269c67b0bc83b4bddcc7
git diff --check 50619ce53ef7b0e6bc8b468b2065ae7da4ef592f...b8d6d6d606daaf301d42269c67b0bc83b4bddcc7
```

## 문서와 게시 제안

| 항목 | 값 |
| --- | --- |
| Docs repository | `vimkim/my-cubrid-docs` |
| Docs task branch | `docs/r16-pr-prep` |
| Integration branch | `main` |
| body_file | `cbrd-27881/pr-body.md` |
| context_file | `cbrd-27881/pr-context.md` |
| Index | `cbrd-27881/README.md` |
| Additional explanation | 없음. 이 변경은 짧은 본문으로 설명한다. |

사용자는 2026-11-11에 "Work894를 이어서 R-16 draft PR 준비를 진행해줘"라고 요청했다. 준비 단계에서는 구체적인 본문과 아래 게시 작업에 대한 승인이 없었다. 이후 사용자는 본문과 게시 작업을 제시한 최종 응답에 "yes"라고 답해 승인했다. 게시 직전에 본문과 source revision을 다시 확인하고 fingerprint를 기록했다.

검토 시 제안한 작업은 다음과 같다.

1. 위 문서 3개를 담은 docs task 커밋을 최신 로컬 `main` 위로 rebase한다. 검증 후 fast-forward 병합하고 `origin/main`으로 push한다. 게시 결과를 context에 기록하는 후속 문서 커밋에도 같은 절차를 적용한다.
2. 정확한 `SOURCE_COMMIT`을 `vk`의 `refs/heads/CBRD-27881-r16-free-space-pr`로 일반 push한다.
3. 위 제목과 `body_file`의 내용을 사용해 `CUBRID/cubrid`의 `feature/oos-merge` 대상 draft PR을 생성하고 `vimkim`을 배정한다. 일치하는 PR이 생겼으면 중복 생성을 중단하고 현재 상태를 확인한다.
4. 실제 PR의 draft 상태, base, head SHA, 본문과 변경 파일을 읽어 확인하고 게시 결과를 기록한다. docs task worktree는 문서 병합과 결과 기록까지 끝난 뒤 비강제로 정리한다.

feature 브랜치의 직접 병합, 엔진 PR 병합과 CI 수동 실행은 제안에 포함하지 않는다. source PR 브랜치는 draft PR이 열려 있는 동안 유지한다. 게시 직전에 base나 source revision이 바뀌면 변경 범위와 검증을 조정하고 다시 검토를 받는다.

## 게시 결과

2026-11-11 15:41 Asia/Seoul에 실제 GitHub 내용을 읽어 확인했다.

| 항목 | 확인한 결과 |
| --- | --- |
| PR | [CUBRID/cubrid #8485](https://github.com/CUBRID/cubrid/pull/8485) |
| 상태 | Open, draft |
| 제목 | `[CBRD-27881] Share the OOS test page free-space helper` |
| Base | `feature/oos-merge`, `50619ce53ef7b0e6bc8b468b2065ae7da4ef592f` |
| Head | `vimkim/cubrid:CBRD-27881-r16-free-space-pr`, `b8d6d6d606daaf301d42269c67b0bc83b4bddcc7` |
| Assignee | `vimkim` |
| 변경 범위 | 1커밋, 테스트 코드 6개 파일, +41/-108 |
| 본문 SHA-256 | `7ad2cf8b1dfb1678612a1c9cdff330d7be6f0e09cc596d03d35be8b12a1dff3a` |
| GitHub diff stable patch ID | `2baae436a4471b4cbbf2e8ad5ca7c4c17871935f` |
| 최초 문서 게시 커밋 | `85cf9943c453e893c5b4aeb22be761df3e7f8467`, `origin/main`에서 확인 |

검토한 본문 파일과 GitHub에서 다시 읽은 본문은 개행까지 같다. GitHub에서 읽은 6개 파일의 patch도 검토한 source commit과 같은 stable patch ID다. source branch의 일반 push 결과는 `SOURCE_COMMIT`과 같다. 문서 작업 브랜치는 당시 최신 로컬 `main`으로 충돌 없이 rebase한 뒤 fast-forward 병합·push했다.

게시 과정에서 source code를 바꾸지 않았으므로 위 Debug 빌드·설치와 CTest 7/7 결과의 source identity도 유지된다. 이 기록은 draft PR 게시 완료를 뜻하며 엔진 병합이나 전체 회귀 통과를 뜻하지 않는다.
