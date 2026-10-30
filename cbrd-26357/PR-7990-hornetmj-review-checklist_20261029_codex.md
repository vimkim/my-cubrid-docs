# PR 7990 hornetmj 리뷰 대응 체크리스트

팀장님 리뷰를 하나씩 이해하고 결정한 뒤, 필요한 수정과 검증을 마친다. 이 문서는 OOS 작성자와 리뷰어가 다음 작업을 이어갈 수 있도록 진행 상태와 근거를 보존한다.

R1은 실제 동시 INSERT로 같은 assertion을 재현한 뒤 7줄을 삭제해 수정했다. 수정 후 CS 10회와 집중 CTest가 통과했고, [회사 draft PR 8330](https://github.com/CUBRID/cubrid/pull/8330)으로 게시했다. R5는 수정 전 debug·release와 재시작 복구의 손상을 재현했고, forward 페이지를 sysop commit 뒤까지 고정하는 로컬 수정으로 같은 주입을 통과했다. R5는 중복 검색 뒤 [CBRD-27858](https://jira.cubrid.org/browse/CBRD-27858)을 발급하고 [회사 draft PR 8348](https://github.com/CUBRID/cubrid/pull/8348)로 게시했다. R6도 독립 브랜치에서 수정·로컬 검증을 마치고 [회사 draft PR 8347](https://github.com/CUBRID/cubrid/pull/8347)으로 게시했다. R2·R3·R4는 대기 중이다.

분석일은 2026-10-29, Asia/Seoul이다. 대상은 [CUBRID/cubrid PR 7990](https://github.com/CUBRID/cubrid/pull/7990)이다. 검토 기준 소스는 `dcbf09e4f7fd02ff9c8fc6493ec8887fc2919d67`, 브랜치는 `feature/oos-merge`이다. 수집 당시 hornetmj님의 inline 리뷰 6개는 모두 미해결이며 outdated가 아니다. 빈 COMMENTED 리뷰 요약은 별도 작업으로 세지 않는다.

리뷰 원문의 재현 결과는 리뷰어의 관찰이다. 이 작업에서 직접 실행한 결과와 구분한다. 아래의 각 완료 표시는 해당 단계의 근거를 확보한 경우에만 바꾼다.

## 작업 범위와 재개 위치

- 기존 Work Item `508`에 이 체크리스트와 단계별 결과를 연결한다. 전체 PR 머지 완료를 이 문서의 초기 작성 완료와 혼동하지 않는다.
- 엔진 수정 작업은 `/home/vimkim/gh/cb/pr7990-hornet-r1`, `CBRD-27827-oos-insert-header-wait`에서 진행한다. 초기 브랜치 이름은 `review/pr7990-hornet-r1`이었다. 각 독립 수정 PR의 base는 `CUBRID/cubrid:feature/oos-merge`이다. 팀 리뷰와 해당 PR head 검증을 받은 뒤 GitHub PR로 반영한다.
- 문서는 `my-cubrid-docs`의 `main`에 통합·게시한다. 초기 task worktree는 `/home/vimkim/gh/my-cubrid-docs-pr7990-hornet-review`, 브랜치는 `docs/pr7990-hornet-review-20261029`이다. 통합 후 정리되면 `main`의 이 문서에서 재개한다.
- 각 항목의 순서는 검토, 이해, 결정, 수정, 검증, 기록이다. 하나의 수정과 검증을 마친 뒤 다음 수정을 시작한다.
- R1은 회사 draft PR 8330의 팀 리뷰 대기이다. [gha-ci 40853451200](https://github.com/CUBRID/cubrid/actions/runs/40853451200)는 release/debug 빌드와 SQL·medium이 통과했고 shell은 `temp_enc_06` 한 건이 실패했다. 사용자는 이 케이스가 알려진 flaky라고 확인했다. 실패 목록이 일치하므로 이를 R1 회귀 의심으로 별도 조사하느라 다른 리뷰를 미루지 않는다. CI의 실제 shell 실패 상태는 그대로 기록한다. 2026-10-30 사용자가 R5는 다른 서브에이전트가 진행한다고 알렸다. root의 R6은 회사 draft PR 8347로 게시했고 [전체 CI 41048233875](https://github.com/CUBRID/cubrid/actions/runs/41048233875)의 다섯 상태 등록을 확인했다. R6의 CI 완료와 팀 리뷰가 남아 있다. R2·R3·R4의 수정은 아직 시작하지 않았다.
- R5는 별도 담당자가 2026-10-30 재현·수정·검증을 로컬에서 마치고 [CBRD-27858](https://jira.cubrid.org/browse/CBRD-27858)을 CBRD-26583의 Sub-task로 발급했다. source 브랜치는 `CBRD-27858-oos-relocation-forward-slot`, 커밋은 접두어만 고친 `628857607`이며 검증한 `c05abc8b4`와 트리가 같다. [회사 draft PR 8348](https://github.com/CUBRID/cubrid/pull/8348)로 게시했고, 회사 CI 실행과 팀 리뷰가 남아 있다. 해당 담당자의 게시 승인 절차를 따르고 R6과 함께 묶지 않는다.
- R1에 이어 R6도 저장한 본문과 게시 작업에 대해 별도 승인을 받았다. 승인 범위는 해당 문서·JIRA 노트 통합 및 게시, 해당 source의 fork push, 회사 draft PR 생성·담당자 지정, 사전 조건 통과 후 전체 CI 한 번이다. 리뷰 답글 게시, thread resolve, reviewer 요청과 source PR 머지는 포함하지 않는다. R5 게시 승인과 혼동하지 않는다.

## 처리 순서

R1은 사용자가 지정한 링크이므로 먼저 다룬다. 이후에는 커밋된 행을 손상시킬 수 있는 R5, 교착 R2, 미사용 복구 인덱스 R6, 스윕 비용 R3 순서로 검토한다. R4는 리뷰어가 명시한 bestspace redesign 안정화 후 적용 계획을 먼저 확인한다. 이 순서는 작업 제안이며 아직 각 항목의 수정안을 승인한 것은 아니다.

| 순서 | 항목 | 사용자 영향 | 첫 확인 사항 | 상태 |
| --- | --- | --- | --- | --- |
| 1 | [R1. 동시 INSERT의 파일 소유 확인 실패](#r1-동시-insert의-파일-소유-확인-실패) | INSERT 실패, debug abort | zero-wait 범위와 파일 헤더 경합 | 회사 PR 8330 리뷰 대기. shell은 알려진 flaky `temp_enc_06` 한 건 실패 |
| 2 | [R5. relocation undo가 재사용 슬롯을 덮어씀](#r5-relocation-undo가-재사용-슬롯을-덮어씀) | 커밋 행 손실, 힙 손상 | forward 페이지 공개와 sysop 경계 | CBRD-27858, 회사 draft PR 8348 게시(`628857607`, 검증한 `c05abc8b4`와 같은 트리). gha-ci 41050496911 실행 중, 팀 리뷰 대기 |
| 3 | [R2. vacuum과 새 힙 페이지 할당의 교착](#r2-vacuum과-새-힙-페이지-할당의-교착) | INSERT 장시간 대기와 abort | PR 8235의 처리 범위와 미통합 변경 | 대기 |
| 4 | [R6. 미사용 복구 인덱스 제거](#r6-미사용-복구-인덱스-제거) | 불필요한 로그 형식 번호 고정 | 로그 생산자 존재 여부 | CBRD-27841, 회사 draft PR 8347 게시, CI·팀 리뷰 대기 |
| 5 | [R3. 페이지 할당 시 전체 파일 스윕](#r3-페이지-할당-시-전체-파일-스윕) | 큰 파일의 INSERT 지연 | 스윕 발동 조건과 진행 위치 | 대기 |
| 6 | [R4. 재시작 후 bestspace 복원](#r4-재시작-후-bestspace-복원) | 빈 공간 미사용, 파일 증가 | redesign 후 적용 계획과 R3 의존성 | 후속 계획 확인 대기 |

## PR 방식 검토 이력과 의존 관계

2026-10-29 사용자는 빠른 순차 리뷰를 위해 하나의 stacked PR 구성을 선택했다. 수정끼리 필수 의존성이 없는 경우에도 이 전달 순서를 사용한다. 수정량이 작더라도 독립된 결함의 티켓, 검증 근거와 리뷰를 유지한다. 기존 티켓이 같은 문제를 다루면 새 티켓을 중복 생성하지 않는다.

스택의 trunk는 `feature/oos-merge`이다. 작업 순서는 R1, R5, R2, R6, R3으로 둔다. 각 PR의 base는 바로 아래 작업 브랜치다. 이 순서는 리뷰와 전달을 위한 순서이며, 모든 수정 사이에 기술적 필수 의존성이 있다는 뜻은 아니다. R4는 bestspace redesign 후속 계획과 CBRD-27213의 범위를 확인한 뒤 포함 여부를 결정한다.

| 관계 | 현재 확인한 내용 | 처리 |
| --- | --- | --- |
| R1 | 다른 수정 없이 원래 기준에서 수정 전후 검증 완료 | 첫 PR로 준비 |
| R2와 R5 | 준비 단계의 VFID 조회와 실행 단계의 forward 슬롯 공개 문제다. 같은 vacuum 흐름과 래치 계약을 공유하지만 필수 선행 관계는 확인하지 못했다. | 서로의 수정 후 통합 검증. 스택 순서 자체를 기술적 의존성으로 설명하지 않음 |
| R3와 R4 | R4의 힌트 복원을 R3의 회수 스윕에 넣으면 구현 의존성이 생길 수 있다. redesign으로 처리하는 경우는 별도 범위다. | R4 구현 방향을 정할 때 의존 관계 확정 |
| R6 | 미사용 복구 인덱스와 후속 번호 조정은 다른 수정과 직접 의존하지 않는다. | 독립 검증 단위를 유지하고 번호 변경 후에는 새 테스트 DB 사용 |

GitHub 기본 stacked PR은 모든 브랜치가 같은 저장소에 있어야 하며 cross-fork 스택을 지원하지 않는다. [공식 요구 사항](https://docs.github.com/en/pull-requests/reference/stacked-pull-requests). 당시에는 `CUBRID/cubrid`의 `origin`에 스택 브랜치를 게시하는 방향을 기록했으나, 이후 사용자가 조직 저장소의 브랜치 증가를 우려하며 `vimkim/cubrid` 구성을 재검토하도록 요청했다. 이후 최종 합의는 아래의 "확정한 전달 방식"을 따른다. 조회 당시 조직 저장소 권한은 `WRITE`, 개인 fork 권한은 `ADMIN`이었다.

같은 `vimkim/cubrid` 안에 trunk와 모든 작업 브랜치, PR을 두는 스택은 같은 저장소 조건을 만족한다. 제한되는 것은 `CUBRID/cubrid`와 fork를 가로지르는 native stack이다. fork 안에서 PR을 리뷰·머지하면 조직 저장소에 자동 반영되지 않으므로, 이후 upstream 반영 절차가 별도로 필요하다. 조직 저장소의 PR마다 리뷰 이력을 남기려면 fork의 독립 브랜치에서 `CUBRID/cubrid:feature/oos-merge`로 각각 일반 PR을 열 수도 있다. [Fork의 upstream PR](https://docs.github.com/en/pull-requests/how-tos/create-pull-requests/creating-a-pull-request-from-a-fork).

현재 소스 검토만으로 변경이 많이 겹친다고 볼 근거는 없다. R2와 R5는 같은 vacuum 흐름이지만 준비와 실행의 수정 지점이 다르고, R1과 R3은 같은 파일의 다른 함수다. R3과 R4는 스윕을 공유하는 수정안을 택할 때 결합될 수 있다. 실제 수정은 R1만 작성했으므로 나머지 패치 사이의 충돌 수를 측정한 것은 아니다.

이 기록 시점에는 스택을 초기화하거나 원격에 게시하지 않았다. R1 티켓을 확정한 뒤 ticket 이름의 브랜치와 PR 본문을 준비한다. PR 게시와 머지의 권한은 각 단계에서 현재 지시와 저장소 정책에 따라 확인한다.

## 회사 리뷰 기록과 CI의 필수 조건

2026-10-29 사용자는 리뷰 기록이 회사 자산이므로 회사 저장소에서 관리·보존돼야 하며, 회사 CI로 검증받아야 한다고 명시했다. 개인 fork 내부 PR을 공식 리뷰 장소로 쓰는 안은 이 조건을 충족하지 않는다. fork 내부 PR을 나중에 upstream PR로 변경해 원본 리뷰 이력을 이전하는 일반 기능은 없다. PR의 base는 같은 저장소 안의 브랜치로만 변경할 수 있다. [GitHub PR 수정 API](https://docs.github.com/en/rest/pulls/pulls#update-a-pull-request).

브랜치의 저장소와 PR의 저장소는 별개다. `vimkim/cubrid` 브랜치에서 `CUBRID/cubrid:feature/oos-merge`를 대상으로 PR을 열면 리뷰는 처음부터 회사 PR에 기록된다. GitHub는 fork에서 upstream으로 연 PR의 이벤트를 upstream 저장소에 전달한다. [Fork PR의 Actions 이벤트](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#pull-request-events-for-forked-repositories).

실제 [CUBRID PR 8235](https://github.com/CUBRID/cubrid/pull/8235)는 `xmilex-git/cubrid`의 head `c2d8e24ff6a74ac11044910f0038ea0c155abbc1`에서 열린 회사 PR이다. 조회 시 해당 PR의 release/debug build와 SQL·medium·shell gha-ci 상태가 모두 SUCCESS였으며 [회사 CI 실행 40784946595](https://github.com/CUBRID/cubrid/actions/runs/40784946595)으로 연결됐다. 따라서 fork 브랜치라는 이유만으로 회사 CI를 사용할 수 없는 것은 아니다. 이 관찰은 새 PR에서 자동 실행되거나 별도 권한·테스트 브랜치 준비 없이 실행된다는 보장은 아니다.

현재 회사 `gha-ci`는 PR head SHA와 실제 base ref를 읽고 `develop` 또는 `feature/*` base만 허용한다. 기본 stacked PR의 Actions 지원과 별도로 회사의 사용자 정의 base 검사를 확인해야 한다. [조회한 develop 리비전의 gate](https://github.com/CUBRID/cubrid/blob/4f1a68c1ebec12f29bc8ba98b5ce8cacb1fc8735/.github/workflows/gha-ci.yml#L294-L305).

조직 브랜치를 늘리지 않으면서 회사 리뷰 기록과 기존 CI 경로를 유지하는 제안은 fork의 독립 브랜치마다 회사의 `feature/oos-merge`를 대상으로 일반 PR을 여는 것이다. native stack을 반드시 유지하는 경우에는 조직 저장소의 작업 브랜치와 회사 CI의 base 처리에 대한 별도 합의가 필요하다. 이 두 구성을 아직 게시하거나 실행하지 않았다.

## 확정한 전달 방식

2026-10-29 사용자는 조직 브랜치를 사용하는 native stack을 별도로 합의하기 전에는 기존 fork 기여 방식으로 진행하기로 확인했다. 이 절이 앞선 스택 검토 이력보다 우선한다.

- 각 독립 수정은 `feature/oos-merge`를 기반으로 ticket별 작업 브랜치를 만든다.
- 브랜치는 `vimkim/cubrid`의 `vk` remote에 게시한다.
- 각 브랜치에서 `CUBRID/cubrid:feature/oos-merge`를 대상으로 개별 PR을 연다. 앞선 수정 PR의 브랜치를 다음 PR의 base로 삼지 않는다.
- 리뷰, 승인과 회사 CI 결과는 처음부터 회사 PR에 남긴다. 개인 fork 내부 PR을 공식 리뷰 장소로 사용하지 않는다.
- 이 작업에서는 native stack을 초기화하거나 조직 저장소에 작업 브랜치를 게시하지 않는다. 스택 도입은 조직 브랜치 운영과 층별 CI 처리를 별도로 합의할 때 재검토한다.
- 실제 수정안에서 필수 선행 관계가 생기면 해당 항목에 근거를 기록하고 전달 순서를 다시 검토한다. 같은 파일을 수정한다는 이유만으로 의존성을 가정하지 않는다.

R1은 기존 티켓의 중복 검색을 마치고 [CBRD-27827](https://jira.cubrid.org/browse/CBRD-27827)을 Correct Error로 발급했다. [검토한 PR 본문](../cbrd-27827/CBRD-27827-oos-insert-header-wait-pr-body_4db11c5_codex.md) 그대로 [회사 draft PR 8330](https://github.com/CUBRID/cubrid/pull/8330)을 만들고 `vimkim`을 담당자로 지정했다. source head는 `4db11c5f12f9c67134aad7f547df8704d1e5c591`이며, 소스는 `vimkim/cubrid`에만 push했다. 실제 게시 결과는 [게시 맥락](../cbrd-27827/CBRD-27827-oos-insert-header-wait-pr-context_4db11c5_codex.md)에 기록한다.

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

이슈는 [CBRD-27827](https://jira.cubrid.org/browse/CBRD-27827)이다. 2026-10-30 사용자 승인 후 [OOS M2, CBRD-26583](https://jira.cubrid.org/browse/CBRD-26583)의 Sub-task로 전환했다. 초기 생성 유형은 Correct Error였다.

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
- [x] 기존 이슈와 PR을 검색하고 CBRD-27827을 발급해 재조회한다.
- [x] 새 ticket 이름으로 브랜치를 정리하고 회사 PR 본문을 저장한다.
- [x] 검토한 본문의 게시 승인을 받은 뒤 fork에 push하고 회사 draft PR을 만든다.
- [x] 사용자 승인 후 CBRD-27827을 OOS M2의 Sub-task로 전환하고 부모·본문·기존 상태 보존을 재조회한다.
- [x] 두 testcase baseline을 확인하고 전체 CI 한 번을 요청해 다섯 gha-ci 상태의 시작을 확인한다.
- [x] CI 완료 결과와 실패 목록을 확인한다. shell의 유일한 실패는 `temp_enc_06`이며, 사용자가 알려진 flaky로 확인했다. 다음 기술 검토는 R5로 유지한다.
- [ ] 회사 CI와 팀 리뷰를 받은 뒤 PR을 반영한다.

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
- [x] forward 슬롯을 비우는 시점, bestpage 공개, 래치 해제, OOS 삭제, sysop abort 순서를 확인한다.
- [x] 기존 CBRD-27781의 OOS 슬롯 충돌과 이번 힙 forward 슬롯 충돌의 차이를 확인한다.
- [x] OOS 삭제 실패를 주입하고 동시 INSERT로 슬롯 재사용을 재현한다.
- [x] 슬롯을 공개해도 되는 복구 경계를 결정하고 최소 수정한다.
- [x] debug와 release의 오류 경로, 행 보존, 인덱스와 힙 일치, `checkdb`를 확인한다.
- [x] 결과와 답글 초안을 기록한다.
- [x] 중복 이슈를 검색한다. 2026-10-30 검색에서 이 heap forward 슬롯 결함의 별도 티켓은 없었다.
- [x] JIRA 초안과 회사 PR 본문 초안을 준비한다. [PR 본문 초안](CBRD-XXXXX-oos-relocation-forward-slot-pr-body_c05abc8_claude.md)과 [게시 맥락](CBRD-XXXXX-oos-relocation-forward-slot-pr-context_c05abc8_claude.md)을 참조한다.
- [x] 초안 검토 뒤 R5 티켓을 발급하고, 브랜치와 커밋 접두어를 새 키로 바꾼다. [CBRD-27858](https://jira.cubrid.org/browse/CBRD-27858)을 CBRD-26583의 Sub-task로 발급했다.
- [x] 회사 draft PR의 게시 승인을 받는다. 승인 후 [회사 draft PR 8348](https://github.com/CUBRID/cubrid/pull/8348)를 만들었다. [PR 본문](../cbrd-27858/CBRD-27858-oos-relocation-forward-slot-pr-body_6288576_claude.md)과 [게시 맥락](../cbrd-27858/CBRD-27858-oos-relocation-forward-slot-pr-context_6288576_claude.md)을 참조한다.
- [x] 회사 CI 실행은 별도 승인을 받는다. 승인 후 testcase 기준 확인을 통과하고 `/run all`을 한 번 올려 [gha-ci 41050496911](https://github.com/CUBRID/cubrid/actions/runs/41050496911)의 다섯 상태 등록을 확인했다.
- [ ] CI 결과와 팀 리뷰를 받은 뒤 source PR을 반영한다.

분석일은 2026-10-30, Asia/Seoul이다. 기준 소스는 `feature/oos-merge`의 `dcbf09e4f7fd02ff9c8fc6493ec8887fc2919d67`이다. 수정 커밋은 `/home/vimkim/gh/cb/pr7990-hornet-r5`의 로컬 task branch `pr7990-hornet-r5`에 있는 `c05abc8b4`였다. 티켓 발급 뒤 브랜치 이름을 `CBRD-27858-oos-relocation-forward-slot`으로 바꾸고 커밋 메시지 접두어만 고쳐 `628857607`이 됐다. 트리와 부모가 같으므로 아래 검증 결과가 그대로 적용된다. 아직 게시하지 않았다. release 실험은 별도 워크트리 `/home/vimkim/gh/cb/pr7990-hornet-r5-release`에서 실행했다. 결론은 리뷰어의 지적을 수용한다는 것이다. 수정 전 코드에서 debug assertion, release 페이지 손상, 재시작 복구 실패를 직접 재현했다. forward 페이지를 sysop commit 뒤까지 고정하는 수정 후에는 같은 주입에서 커밋된 행이 보존됐다.

### R5에서 이해한 실패 경로

vacuum은 삭제가 확정된 relocation 행을 지울 때 home 페이지의 `REC_RELOCATION` 슬롯과 forward 페이지의 `REC_NEWHOME` 슬롯을 하나의 sysop으로 지운다. 행에 OOS 값이 있으면 같은 sysop 안에서 OOS chunk도 지운다. sysop이 끝나기 전에는 abort나 재시작 복구가 이 변경을 undo할 수 있다. forward 슬롯의 undo는 옛 `REC_NEWHOME`을 같은 슬롯 번호에 다시 넣는다.

기준 소스의 [REC_RELOCATION 처리](https://github.com/CUBRID/cubrid/blob/dcbf09e4f7fd02ff9c8fc6493ec8887fc2919d67/src/query/vacuum.c#L2532-L2577) 순서는 다음과 같다.

1. `spage_vacuum_slot`이 forward 슬롯을 재사용 가능한 빈 슬롯으로 만든다.
2. `heap_add_bestpage`가 그 페이지의 빈 공간을 INSERT 후보로 알린다.
3. forward 페이지의 undo 로그를 남기고 `pgbuf_set_dirty (..., FREE)`로 래치를 놓는다.
4. OOS 삭제가 성공하면 `log_sysop_commit`, 실패하면 `log_sysop_abort`를 호출한다.

3과 4 사이에 다른 트랜잭션이 그 페이지에 INSERT해 같은 슬롯 번호를 받고 commit할 수 있다. 그 뒤 4가 abort하면 undo는 [`vacuum_rv_undo_vacuum_heap_record`](https://github.com/CUBRID/cubrid/blob/dcbf09e4f7fd02ff9c8fc6493ec8887fc2919d67/src/query/vacuum.c#L7771-L7776)에서 `heap_rv_redo_insert`를 거쳐 `spage_insert_for_recovery`로 옛 레코드를 같은 슬롯에 넣는다. 이 함수는 [슬롯이 비어 있다고 가정](https://github.com/CUBRID/cubrid/blob/dcbf09e4f7fd02ff9c8fc6493ec8887fc2919d67/src/storage/slotted_page.c#L1964-L1970)한다. debug는 이 assertion으로 종료한다. release는 슬롯 형식을 바꾸고 다시 할당해 옛 레코드를 쓰므로, 커밋된 행의 레코드는 슬롯에서 떨어져 페이지 레코드 수가 맞지 않게 된다.

develop `4f1a68c1e`의 같은 경로도 [FREE 뒤에 sysop을 commit](https://github.com/CUBRID/cubrid/blob/4f1a68c1ebec12f29bc8ba98b5ce8cacb1fc8735/src/query/vacuum.c#L2428-L2442)하지만, 그 사이에 실패할 수 있는 처리가 없다. PR 7990이 그 사이에 OOS 삭제를 넣으면서 abort 경로가 생겼다. 재시작 복구도 끝나지 않은 sysop을 같은 undo 함수로 되돌리므로, commit 전에 서버가 죽어도 같은 손상이 생긴다. develop에도 FREE와 commit 사이의 매우 짧은 창은 있다. OOS 삭제가 이 창을 페이지 고정과 I/O가 있는 구간으로 넓혔다는 점은 소스에서 추론한 것이다.

`REC_HOME`의 OOS 경로는 home 페이지를 sysop이 끝난 뒤까지 고정하므로 이 문제가 없다. `REC_BIGONE`도 vacuum한 home 슬롯의 페이지를 고정한 채 실패를 처리한다.

[CBRD-27781](https://jira.cubrid.org/browse/CBRD-27781)은 같은 부류의 결함이지만 대상이 다르다. CBRD-27781은 OOS 파일의 chunk 슬롯이고, R5는 heap 파일의 forward 슬롯이다. R5의 수정은 OOS chunk 슬롯의 재사용을 막지 않는다. 이번 재현은 OOS chunk를 지우기 전에 실패를 주입하므로 CBRD-27781의 경로를 실행하지 않는다.

### R5 재현 방법

재현 전용 hook을 기준 소스에 더한 로컬 커밋 `dd9f052c0`(`pr7990-hornet-r5-repro`)을 사용했다. 게시하지 않는다. 서버 환경에 `CUBRID_R5_REPRO_DIR`이 있고 그 아래 `arm` 파일이 있을 때만 한 번 동작한다. forward 페이지를 놓은 직후, OOS 삭제 helper를 호출하는 자리에서 forward OID를 파일에 쓰고 `go` 파일을 최대 120초 기다린다. 그 뒤 helper가 메모리 부족으로 실패한 것처럼 `ER_OUT_OF_VIRTUAL_MEMORY`를 반환한다. 이 오류는 호출자가 블록을 미완료로 남겨 다시 시도하는 [기존 경로](https://github.com/CUBRID/cubrid/blob/dcbf09e4f7fd02ff9c8fc6493ec8887fc2919d67/src/query/vacuum.c#L1829-L1833)를 탄다.

드라이버 `r5_repro.py`는 CS 모드 csql로 다음을 수행한다. 각 실행은 새 테이블을 만들고, 테이블과 출력은 지우지 않는다.

1. `id INT PRIMARY KEY, pad VARCHAR(16000), big VARCHAR(8000) STORAGE FORCE_OUTLINE`인 기본 테이블에 피해 행 하나와 filler 40행을 넣는다. 피해 행의 `pad`를 100자에서 3,400자로 늘려 relocation을 만들고, `SHOW HEAP CAPACITY`의 `Num_relocated_recs`가 1인지 확인한다.
2. `arm` 파일을 만들고 피해 행을 DELETE한다. 다른 테이블에 로그를 써서 vacuum이 hook에 도달하게 한다.
3. hook이 기록한 forward 슬롯을 `SET TRANSACTION LOCK TIMEOUT 0`과 `SHOW SLOTTED PAGE SLOTS`로 관찰한다. 행마다 commit하는 INSERT를 그 슬롯이 `HOME`이 될 때까지 반복한다.
4. abort 모드는 `go`를 만들어 실패를 주입한다. crash 모드는 `go` 대신 서버를 `kill -9`한다. 그 뒤 인덱스 경로(`id >= 1000`)와 힙 경로(`id + 0 >= 1000`)의 결과를 커밋된 id와 비교한다. 행이 맞으면 vacuum 재시도로 피해 행의 OOS 레코드 수가 0이 되는지 확인한다.

준비 중 확인한 조건이 있다. 반복 문자열은 압축돼 relocation이 생기지 않으므로 난수 hex 값을 쓴다. 레코드가 `DB_PAGESIZE/4`를 넘으면 큰 열이 OOS로 이동하므로 커진 피해 행을 4KB 미만으로 둔다. 기본 테이블은 REUSE_OID여서 OID를 조회할 수 없으므로 슬롯을 직접 본다. 페이지 래치 대기는 lock timeout이 아니라 300초 고정값을 쓰며, zero-wait만 조건부 고정으로 바뀐다.

각 빌드는 별도 workenv와 이 작업에서 만든 DB만 사용했다. hook, 드라이버, 실행별 결과는 로컬 증거 경로 `/home/vimkim/temp/pr7990-hornet-review-20261029/r5/`에 보존하고 이 저장소에 커밋하지 않는다.

### R5 수정 전 결과

| 빌드와 모드 | 관찰 |
| --- | --- |
| debug, abort | forward `1|1603|6`이 `DELETED_WILL_REUSE`인 동안 커밋된 INSERT id 1000이 그 슬롯에 `HOME` 3,344바이트로 들어갔다. 실패를 주입하자 `slotted_page.c:1969`의 `offset_to_record == SPAGE_EMPTY_OFFSET` assertion으로 서버가 종료했다. master의 자동 재시작과 SA `checkdb`의 복구 모두 UNDO에서 같은 assertion으로 실패했다. 이 DB는 다시 열 수 없다. |
| release, abort | `1|707|6`에 id 1000이 들어간 뒤 실패를 주입했다. abort 중 "page 707 ... may be corrupted"가 기록됐고, 이어서 `spage_compact`가 "6 records was found when 7 was expected" FATAL로 서버를 종료했다. master가 다시 시작한 서버에서 재시작 UNDO가 같은 손상을 다시 기록했고, 복구를 마친 서버도 같은 FATAL로 종료했다. |
| release, crash | OOS 실패 없이 같은 구간에서 `kill -9`했다. 재시작 UNDO가 page 707 손상을 기록했고 이어서 `spage_compact` FATAL이 났다. |

리뷰어의 release 관찰은 서버 유지, 커밋 행 1건 유실, `checkdb`의 레코드 수 불일치였다. 이번 실행도 같은 페이지 레코드 수 불일치이며, 손상 직후 compaction이 일어나 FATAL로 이어졌다.

### R5 결정과 최소 수정

슬롯을 공개해도 되는 경계는 sysop의 끝이다. 그 전에는 abort나 재시작 undo가 슬롯에 옛 레코드를 다시 넣을 수 있다. 따라서 forward 페이지를 `log_sysop_commit` 뒤까지 고정한다.

커밋 `c05abc8b4`는 forward 페이지의 `pgbuf_set_dirty`를 `FREE`에서 `DONT_FREE`로 바꾸고, commit 뒤에 `pgbuf_unfix_and_init`을 호출한다. 실패 경로는 abort 후 반환한다. 호출자는 이미 [반환 뒤 forward 페이지를 unfix](https://github.com/CUBRID/cubrid/blob/dcbf09e4f7fd02ff9c8fc6493ec8887fc2919d67/src/query/vacuum.c#L1820-L1823)한다. `heap_add_bestpage`의 위치는 바꾸지 않았다. 페이지를 고정한 동안 후보 페이지의 조건부 래치는 실패하므로 INSERT가 그 공간을 쓰지 못한다. 새 재시도 계층이나 대기 모드는 추가하지 않았다.

수정 후 vacuum은 home과 forward 페이지를 쓰기 래치로 쥔 채 OOS 페이지를 고정한다. `REC_HOME`의 OOS 경로가 이미 home 페이지를 쥔 채 OOS를 지우므로 heap 다음 OOS의 순서는 같다. `oos_delete`는 OOS 데이터 페이지와 OOS 내부 상태만 다루며 heap 페이지나 heap 헤더를 고정하지 않는다. abort의 undo는 같은 스레드가 쓰기 래치를 가진 페이지를 다시 고정하며, `REC_HOME`의 OOS abort가 home 페이지에서 이미 같은 방식을 쓴다. 비용은 OOS 삭제 동안 forward 페이지 래치를 더 쥐는 것이다. 수정 후 실험에서 INSERT가 이 페이지를 기다렸고, 인위적 정지 때문에 약 100초가 걸렸다.

R2는 준비 단계에서 heap 헤더를 기다리는 교착이다. 이 수정은 실행 단계에서 heap 헤더를 고정하지 않으므로 R2의 순환을 새로 만들지 않는다. R2를 수정할 때 forward 페이지의 고정 범위를 함께 확인한다.

### R5 수정 후 검증

수정과 hook을 함께 담은 로컬 테스트 브랜치 `pr7990-hornet-r5-fixed-repro`(`74f82fabb`)로 같은 드라이버를 실행했다.

| 검증 | 관찰 결과 |
| --- | --- |
| debug, abort | hook 정지 중 forward `1|963`의 zero-wait 조회가 페이지 래치 대기로 실패했다. 첫 INSERT는 105초를 기다린 뒤 진행했다. hook이 120초 뒤 실패를 주입해 abort한 뒤, vacuum 재시도가 OOS 레코드를 0으로 정리했다. id 1000과 1001이 인덱스와 힙에서 모두 조회됐고 assertion은 없었다. |
| debug, crash | hook 정지 중 INSERT가 30초 동안 막힌 상태에서 `kill -9`했다. 재시작이 정상 완료됐고, 재시도 후 forward 슬롯이 `DELETED_WILL_REUSE`, OOS 레코드가 0이 됐다. |
| release, abort | debug와 같은 순서와 결과. id 1000과 1001이 보존됐고 서버 오류 로그에 FATAL과 손상 메시지가 없다. |
| release, crash | debug와 같은 결과. 재시작 후 서버 오류 로그에 FATAL과 손상 메시지가 없다. |
| SA `checkdb` | 수정 후 DB `r5fix1`, `r5fix2`, `r5relfix1`, `r5relfix2` 모두 rc 0 |
| CTest | hook 없는 수정 커밋 `c05abc8b4`의 debug 빌드에서 구성된 44개 전체 통과(OOS fixture, `test_oos_vacuum_server`, `test_oos_real_vacuum_server`, `test_oos_sql_crash_recovery` 포함). 504초 |
| 빌드와 스타일 | debug·release 빌드와 설치, pre-commit codestyle 통과 |

수정 후 첫 두 abort 시도는 드라이버 문제로 결론 없이 끝났다. 하나는 zero-wait로 바꾸기 전 관찰 쿼리가 60초 타임아웃에 걸렸고, 다른 하나는 일시적인 접속 실패였다. 서버는 살아 있었고 assertion도 없었으므로 엔진 실패로 세지 않는다.

남은 한계가 있다. hook으로 창을 넓힌 결정적 재현이며 실제 발생 빈도는 측정하지 않았다. hook은 서버 코드에 환경 변수 검사를 넣으므로 게시하지 않고, 회귀 테스트로도 남기지 않았다. 여러 chunk의 OOS 삭제 도중 실패, DONT_REUSE_OID 테이블, HA 복제는 확인하지 않았다. OOS chunk 슬롯의 같은 부류 문제는 CBRD-27781에 남는다.

### R5 답글 초안

> 지적하신 경로를 재현했습니다. forward 페이지를 놓은 직후 OOS 삭제 실패를 주입했고, 그 사이 커밋된 INSERT가 바로 그 forward 슬롯에 들어간 것을 `SHOW SLOTTED PAGE SLOTS`로 확인했습니다. debug는 `spage_insert_for_recovery`의 assertion으로 종료했고 재시작 복구도 같은 assertion에서 실패했습니다. release는 abort 중 페이지 손상 후 `spage_compact`의 레코드 수 불일치 FATAL로 종료했습니다. OOS 실패 없이 같은 구간에서 서버를 강제 종료해도 재시작 undo가 같은 손상을 냈습니다. forward 페이지를 sysop commit 뒤에 놓도록 수정했고, 같은 주입에서 INSERT가 페이지를 기다린 뒤 진행하며 행 보존, 인덱스와 힙 일치, `checkdb`를 debug와 release에서 확인했습니다. OOS chunk 슬롯의 같은 부류 문제는 CBRD-27781에서 따로 다룹니다.

초안은 아직 게시하지 않았다. GitHub thread도 미해결 상태로 유지한다.

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
- [x] 전체 소스에서 해당 로그의 생산자와 소비자를 검색한다. 선언, 빈 테이블 항목과 두 분류 조건 외에 생산자는 없다.
- [x] `recovery.h`, `recovery.c`, `mvcc.h`의 네 참조와 후속 번호를 확인한다.
- [x] 현재 저장 형식 정책과 번호 재배치의 영향을 판단한다. ADR-0006에 따라 형식 번호도 1에서 2로 올려 기존 개발 DB를 복구 전에 거부한다.
- [x] 불필요한 참조를 제거하고 후속 인덱스를 조정한다.
- [x] `rv_check_rvfuns`, OOS 변경 중 강제 종료와 복구, `checkdb`를 확인한다. 직접 관측한 crash redo는 SA 테스트이며 두 변경 번호의 producer별 통합 검증은 별도 한계로 기록한다.
- [x] 결과와 답글 초안을 기록한다.
- [x] CBRD-27841을 OOS M2의 Sub-task로 발급·재조회하고 독립 회사 PR 본문을 저장한다.
- [x] PR 게시 승인 후 fork push, 회사 draft PR, 회사 CI를 진행한다. PR 8347과 전체 CI 한 번의 다섯 상태 등록을 확인했다.
- [ ] CI 결과와 팀 리뷰를 받은 뒤 source PR을 반영한다.

R6은 `CBRD-27841-remove-unused-oos-recovery-index`의 독립 worktree에서 진행하며 R5 worktree를 수정하지 않는다. [상세 판단·검증 기록](PR-7990-R6-recovery-index-cleanup_dcbf09e_codex.md)을 함께 갱신한다. 현재의 빈 예약 항목을 제거하는 작업은 CBRD-27230의 실제 commit 알림 구현 완료를 의미하지 않는다.

### R6 답글 초안

> 생산자가 없는 예약 항목과 두 분류 조건을 제거하고 뒤의 실제 복구 번호를 140·141로 정리했습니다. 기존 개발 로그가 새 번호로 해석되지 않도록 저장 형식 번호도 2로 올렸습니다. 수정 전후 집중 CTest가 각각 10/10 통과했고, 실제 빌드의 시작 검사와 복구 테이블, 별도 DB의 commit·rollback·재개방 후 값과 checkdb를 확인했습니다. SA crash redo는 검증했지만 별도 HA replica 재생과 두 producer를 직접 발생시키는 MVCC relocation 통합 실행은 아직 하지 않았습니다. CBRD-27841과 별도 회사 PR로 검토받겠습니다.

이 초안은 아직 게시하지 않았고 원래 thread도 해결 처리하지 않았다.

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
| 2026-10-29 | R1 게시 | fork push, 회사 draft PR 8330 생성, 담당자 지정과 본문 재조회를 완료했다. 전체 CI 한 번의 시작을 확인했다. | [PR 8330](https://github.com/CUBRID/cubrid/pull/8330), [CI 실행](https://github.com/CUBRID/cubrid/actions/runs/40853451200), 게시 맥락 | CI 완료와 팀 리뷰, 이후 별도 머지 판단 |
| 2026-10-29 | JIRA 도구 | Python의 `{code}`가 블록을 끝내는 변환기 결함을 서브에이전트로 분석·수정했다. 원본 Markdown을 보존해 실제 본문을 복구하고 서버 렌더 결과를 검증했다. | `cubrid-jira` 후보 `3f282aa`, 전체 테스트 297개, 독립 검토 112개 | 2026-10-30 승인 후 아래와 같이 통합·설치 완료 |
| 2026-10-30 | JIRA 도구 완료 | 승인받은 `3f282aa`를 main에 fast-forward로 통합·push하고 `just sync`로 설치했다. 재검증 297개와 설치된 CLI의 실제 변환·readback 검사가 통과했고, 현재 JIRA 웹 본문도 정상이다. | 설치본과 main의 변환기 바이트 일치, 원본 issue payload 일치, Work 617 | 완료. 병합된 임시 worktree·브랜치 정리, main clean |
| 2026-10-30 | R1 부모 연결 | 사용자 승인 후 CBRD-27827을 Correct Error에서 Sub-task로 전환하고 부모를 OOS M2 CBRD-26583으로 지정했다. API 재조회로 이슈 번호·제목·본문·Open 상태·우선순위·담당자·링크 보존과 웹 렌더 결과를 확인했다. | Convert wizard 결과와 전후 issue 스냅샷, 게시 맥락 | 부모 연결 완료. 독립 회사 PR 8330의 리뷰·검증 방식 유지 |
| 2026-10-30 | R1 CI 분류 | release/debug 빌드와 SQL·medium이 통과했다. shell 실패는 `_36_damson/cbrd_23608_tde/temp_enc_06` 한 건으로 로그에서 확인했다. 사용자가 알려진 flaky라고 확인했으므로 별도 R1 회귀 조사를 다음 작업의 선행 조건으로 두지 않는다. | shell 05의 NOK 항목, collect의 `shell: 1 failed`, 사용자 확인 | 다음은 R5 검토. CI 실패 상태와 팀 리뷰 대기는 유지 |
| 2026-10-30 | R5 | 수용. 수정 전 debug assertion, release 페이지 손상 FATAL, 재시작 복구 실패를 재현했다. forward 페이지를 `log_sysop_commit` 뒤에 놓도록 수정하고 같은 주입의 abort·crash 모드를 debug·release에서 통과했다. | 재현 hook `dd9f052c0`(게시하지 않음), 수정 `c05abc8b4`, 위 R5 검증 결과 | 중복 검색, 티켓 발급, 회사 PR 본문과 게시 승인 |
| 2026-10-30 | R5 게시 준비 | `REC_NEWHOME`, `REC_RELOCATION`, `spage_insert_for_recovery`, `vacuum_heap_oos_delete`, `spage_compact`, sysop과 vacuum의 조합으로 JIRA를 검색해 별도 티켓이 없음을 확인했다. R1과 같이 CBRD-26583의 Sub-task로 발급하는 JIRA 초안과 회사 PR 본문 초안을 준비했다. 생성 명령의 dry-run 변환은 오류가 없었다. | JIRA 노트 task 커밋 `cd1bd26`, 이 문서의 PR 본문·게시 맥락 | 초안 검토, 티켓 발급, 브랜치 이름 변경, fork push와 draft PR 생성 승인 |
| 2026-10-30 | R5 티켓 발급 | 사용자 승인 후 [CBRD-27858](https://jira.cubrid.org/browse/CBRD-27858)을 CBRD-26583의 Sub-task로 만들고 `vimkim`에게 배정했다. 재조회한 본문이 dry-run 변환과 같고 계측·드라이버 코드 블록이 온전했다. 소스 브랜치를 `CBRD-27858-oos-relocation-forward-slot`으로 바꾸고 커밋 접두어만 고쳤다. | 생성 결과와 재조회, 소스 `628857607`(트리 동일) | PR 본문 검토, 문서 통합, fork push와 draft PR 생성 승인 |
| 2026-10-30 | R5 PR 게시 | 사용자 승인 후 문서와 JIRA 노트를 `main`에 통합·push했다. 동시에 진행된 R6 기록과 공유 문서가 충돌해 두 저장소 모두 squash로 병합했다. 수정 브랜치만 `vk`에 push하고 [회사 draft PR 8348](https://github.com/CUBRID/cubrid/pull/8348)를 `feature/oos-merge` 대상으로 만들어 `vimkim`을 지정했다. | PR 재조회: head `628857607`, draft, 본문 SHA256이 승인 파일과 같음 | 회사 CI 승인, 팀 리뷰 |

수집 원본은 `/home/vimkim/temp/pr7990-hornet-review-20261029/review-snapshot.json`에 보관한다. 원본 JSON, 빌드 로그, 중간 산출물은 문서 저장소에 커밋하지 않는다.

2026-10-29 진행 방식 변경은 위의 "합의한 PR 방식과 의존 관계"를 따른다. 앞선 실행 결과와 당시 결정 기록은 보존한다.
