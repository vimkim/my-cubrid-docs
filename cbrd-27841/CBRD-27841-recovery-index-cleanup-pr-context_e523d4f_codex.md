# CBRD-27841 PR 설명 수정안

2026-11-02, Asia/Seoul. PR 작성자와 다음 작업자가 source 변경과 설명 게시 범위를 확인하기 위한 기록이다. 사용자는 진행 중인 미출시 개발 단계에서 이번 정리 때문에 storage revision을 올리지 않기로 결정했다. `eac70c7` 문서는 당시 판단과 검증의 이력으로 보존한다.

## Source와 검증

- Ticket: [CBRD-27841](https://jira.cubrid.org/browse/CBRD-27841).
- Agent: `codex`.
- Source repository: `vimkim/cubrid`.
- Source branch: `CBRD-27841-remove-unused-oos-recovery-index`.
- Source commit와 재조회한 원격 head: `e523d4f51572c0299daba4c14ba92f511a6fc17e`.
- Base: `CUBRID/cubrid:feature/oos-merge`, 관측 commit `dcbf09e4f7fd02ff9c8fc6493ec8887fc2919d67`.
- 이번 source commit은 `src/storage/disk_manager.h`의 revision 2와 해당 이력 한 줄만 원복했다. PR 전체에서 이 헤더의 base 대비 diff는 없다.
- `debug_gcc` 빌드·설치가 성공했다. 기존 `test_oos_storage_format_guard`와 생성·정리 fixture가 3/3 통과했다. `bash -n`과 `git diff --check`, commit 시 codestyle 검사가 통과했다.
- 기존 복구 번호 재배치와 범용 형식 검사 테스트 확장은 유지한다. 이전 번호의 개발 로그를 새 번호로 읽을 수 있다는 뜻은 아니다.
- 이번 예외는 사용자의 현재 지시에 따른다. ADR-0006의 일반적인 bump 규칙이나 다른 작업의 정책을 변경하지 않는다.
- Source는 standing authorization에 따라 commit·일반 push했고 원격 head를 재조회했다. TC 변경은 필요 없다.

## 수정 대상과 검토 파일

- Target: [CUBRID/cubrid PR 8347](https://github.com/CUBRID/cubrid/pull/8347).
- Operation: 기존 body 수정. 현재 PR은 open·draft이며 이를 유지한다.
- 기존 title: `[CBRD-27841] Remove unused OOS recovery index`. title 변경은 제안하지 않는다.
- 관측한 기존 GitHub body의 decoded UTF-8 SHA-256: `769d90fee615ac67452a0b887e999805150ae33a5c5ee85f9264e62ea0d3cffc`.
- Docs branch: `docs/CBRD-27841-revision1`. Integration branch: `main`.
- Body: `cbrd-27841/CBRD-27841-recovery-index-cleanup-pr-body_e523d4f_codex.md`.
- Context: `cbrd-27841/CBRD-27841-recovery-index-cleanup-pr-context_e523d4f_codex.md`.
- Index: `cbrd-27841/README.md`.
- 별도 상세 설명 파일이나 새 공개 설명 링크는 필요하지 않다.

## 승인 후 제안하는 작업

1. 위 body·context·README만 포함한 docs task commit을 현재 local `main`에 rebase하고 fast-forward merge한다. squash는 fast-forward가 불가능할 때의 대안이다. `origin/main`에 push하고 이 task worktree와 branch만 정리한다. 게시 결과 기록에 필요한 같은 파일의 후속 commit도 포함한다.
2. Source head와 기존 GitHub body의 fingerprint를 다시 확인한 뒤 저장한 body를 그대로 PR 8347에 반영한다. title·base·draft 상태는 유지한다. Source push는 이미 완료했으므로 추가 push는 제안하지 않는다.
3. 사용자가 기존 실행 대체까지 명시 승인하는 경우에만, [진행 중인 CI 41431046311](https://github.com/CUBRID/cubrid/actions/runs/41431046311)을 대체하는 `/run all`을 한 번 게시한다. 정확한 새 head를 확인하고 pickup과 최종 결과를 보고한다. 기존 실행이 먼저 끝나면 일반적인 새 head CI 사전 검사를 적용한다.

이 파일은 승인 기록이 아니다. 본문을 저장한 뒤 대화에서 명시 승인을 받아야 한다. source merge, TC PR merge·close, remote branch 삭제는 제안 범위에 없다.

## 현재 CI와 TC 경계

새 source push 전 별도 작업에서 시작한 `/run rerun 41048233875`가 실행 중이었다. 영수증은 [2026-11-02 10:43:09 UTC comment](https://github.com/CUBRID/cubrid/pull/8347#issuecomment-6575144874), 실행은 [41431046311](https://github.com/CUBRID/cubrid/actions/runs/41431046311)이다. 이 실행은 이전 head `eac70c7`의 검증이며 새 head의 검증으로 표시하지 않는다. 실행 중인 같은 PR의 CI를 임의로 취소하지 않았다.

TC baseline 검사는 public·private 모두 PASS였다. [public TC PR 3962](https://github.com/CUBRID/cubrid-testcases/pull/3962)와 [private TC PR 4673](https://github.com/CUBRID/cubrid-testcases-private-ex/pull/4673)는 open·draft다. 이 작업에는 TC 변경이 필요 없으므로 human이 처리한다. Agent는 두 PR을 merge·close하거나 branch를 삭제하지 않는다.
