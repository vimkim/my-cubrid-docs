# PR #8299 본문·문서 정합성 게시 context

작성일은 2026-10-31, Asia/Seoul이다. 이 문서는 게시 제안과 실행 기록이며 승인 토큰이 아니다.
목표는 PR #8299의 구현·CI 설명을 현재 head와 맞추고 과거 성능 측정의 revision과 한계를 유지하는 것이다.

## 대상과 변경 전 상태

- Ticket은 CBRD-27785, agent는 codex다.
- Source commit은 `067aae4e4e91fec8c71c914a4c7fc3c4b13dcd65`다.
- Source repository와 PR head는 `vimkim/cubrid:CBRD-27785-oos-read-performance`다.
- 로컬 확인 source branch는 `CBRD-27785-unified-reader`이며 원격 PR과 같은 commit이고 tracked 변경이 없다.
- Target은 [CUBRID/cubrid PR #8299](https://github.com/CUBRID/cubrid/pull/8299)의 기존 본문 갱신이다.
- Base는 `CUBRID/cubrid:feature/oos-merge`, 확인한 commit은 `dcbf09e4f7fd02ff9c8fc6493ec8887fc2919d67`다.
- 확인한 원격 head는 위 source commit과 같다. source push는 제안하지 않는다.
- 기존 title은 `[CBRD-27785] Reduce heap read and UPDATE CPU overhead`다. title·base·OPEN draft 상태를 유지한다.
- 기존 GitHub body SHA-256은 `06ddbda7bd2e49945babe1576383e74d7dfc4d02c322bdf683a2e055e18f66e7`이다. JSON에서 decode한 UTF-8 bytes에 추가 newline 없이 계산했다.
- 현재 body는 `408d135`를 HEAD로 표시하고 전체 CI 미실행 문구를 유지하고 있었다.
- 현재 head의 CI 10개는 모두 성공이며 gha-ci 5개는 [run 40827634555](https://github.com/CUBRID/cubrid/actions/runs/40827634555)에 연결된다.
- TC [#3898](https://github.com/CUBRID/cubrid-testcases/pull/3898)과 [#4589](https://github.com/CUBRID/cubrid-testcases-private-ex/pull/4589)는 OPEN draft이고 diff가 없다. 사람의 종료 처리를 기다린다.

## 검토할 파일과 보존 이유

Docs task branch는 `docs/CBRD-27785-pr8299-reconcile`, integration branch는 `main`이다.
Docs repository는 `vimkim/my-cubrid-docs`다.

| 파일 | 보존 이유 |
| --- | --- |
| [PR 본문](CBRD-27785-common-reader-pr-body_067aae4_codex.md) | 승인 후 GitHub에 올릴 정확한 본문이다. |
| [현재 구현·CI와 과거 측정 보고서](CBRD-27785-common-reader_067aae4_codex.md) | 현재 source·CI와 과거 성능의 revision, 조건, 남은 한계를 구분한다. |
| 이 context | 대상, 변경 전 fingerprint, 승인할 조치와 게시 결과를 추적한다. |
| [TODO 체크리스트](CBRD-27785-todo-checklist.md) | 준비 완료와 게시·TC·리뷰·성능 수락 미완료를 구분한다. |
| [ticket README](README.md) | 본문·보고서·context를 색인한다. |
| [ordinary-results.json](common-reader-20261029/ordinary-results.json) | 과거 일반 쿼리 표의 12개 표본 집합, source·binary·빌드 정보를 보존해 산술을 확인한다. |
| [oos-results.json](common-reader-20261029/oos-results.json) | 과거 grouped 표의 12개 표본 집합과 범위를 확인한다. |

보고서의 계획 공개 URL은 다음과 같다. docs 게시를 마친 뒤 PR 본문을 갱신한다.

https://github.com/vimkim/my-cubrid-docs/blob/main/cbrd-27785/CBRD-27785-common-reader_067aae4_codex.md

두 JSON은 기존 공통 reader 작업의 선택 자료를 bytes 변경 없이 가져왔다.
과거 source·compiler 경고 정책을 현재 성공 상태로 고쳐 쓰지 않는다.

| 선택 자료 | SHA-256 |
| --- | --- |
| ordinary-results.json | `2c28c0fbbba8fe0c00046236d93c27383d46f68f766bdd10ae77e3e40978e307` |
| oos-results.json | `8cced11ab68e8cedec5ba2e92342cda0a620025b3e7ae5661ca4890bd7eb0d0a` |

## 확인 후 수행할 조치

1. 승인받은 위 7개 파일의 task commit을 최신 로컬 docs `main`에 rebase한다. 전체 incoming 파일·링크·diff와 문서 검사를 다시 확인하고 fast-forward 병합한다.
2. docs `origin/main`에 push하고 공개 보고서의 경로·내용과 원격 commit을 확인한다.
3. PR head·본문 fingerprint·대상·title·base·draft 상태를 다시 확인한다. 변경되었으면 먼저 정합성을 확인하고 필요한 새 검토를 받는다.
4. 저장한 본문의 bytes를 그대로 PR #8299의 body에 올린다. title·base·draft 상태는 바꾸지 않는다.
5. 실제 GitHub body와 저장 파일의 일치를 확인한다. 게시 결과와 체크리스트를 같은 task의 실행 기록으로 commit하고 docs `main`에 병합·push한다.
6. 결과를 확인한 뒤 이 task의 docs worktree와 branch만 강제 없이 정리한다. 다른 docs·source worktree와 원시 DB·실험 자료는 보존한다.

위 조치는 새 본문과 문서를 검토한 뒤 사용자가 확인해야 실행한다.
engine source push, engine PR 병합, CI 재실행, TC PR merge·close·branch 삭제, JIRA 갱신은 제안하지 않는다.

## 준비 단계의 확인

- GitHub plugin과 `watch-pr --status-only`로 현재 PR·CI·thread와 두 TC PR을 확인했다.
- 현재 source의 공통 reader·offset helper와 직전 revision 대비 세 줄의 차이를 직접 읽었다.
- 과거 선택 JSON의 표본 수, 중앙값, 최솟값·최댓값, spread와 비교율을 재계산했다. 24개 표본 집합이 저장 값과 일치했다.
- 이번 작업에서 build·기능 테스트·benchmark·CI를 새로 실행하지 않았다. 과거 실행 기록의 범위와 조건을 유지했다.
- JIRA 실시간 조회는 `Name or service not known` 오류로 실패했다. 로컬 issue draft를 참고했으며 현재 상태를 추정하지 않았다.
- 게시 승인은 아직 받지 않았고 docs main 병합·push와 GitHub body 갱신은 수행하지 않았다.

검토할 본문 SHA-256은 `f2209fa2de23279d33b2c7885115618a45483de10844e2b58448bb412d3f1270`이다.
보고서 SHA-256은 `8bc7d66de5af118e75f976262c16df6b4cee33460a4fb687e70261be10ff0435`다.
둘 다 파일의 실제 UTF-8 bytes로 계산했다.

본문·보고서의 PR material 검사, 공유 링크 검사와 Markdown 5개 검사가 통과했다.
상대 링크 36개가 보존할 Git 파일을 가리키며 내부 anchor 2개도 확인했다.
주석 검토 대상인 code comment나 suppression은 없었다. 독립 내용·코드 리뷰를 수행한 것으로 기록하지 않는다.
승인 후 실제 게시 결과는 수행하고 확인할 때 기록한다.

## 승인 후 게시 결과

2026-10-31에 사용자가 위 파일과 조치의 게시를 확인했다. 권한 근거는 해당 대화의 확인이며 이 context를 승인 토큰으로 사용하지 않는다.

- 승인한 본문·보고서의 fingerprint, source HEAD, 원격 PR head·branch·base·OPEN draft 상태와 기존 body fingerprint를 다시 확인했다. 준비 당시 값과 일치했다.
- 승인한 7개 파일을 포함한 `db28c48199770c4e6455e9cb4aad54259b5ec803`을 docs `main`에 fast-forward 병합하고 `origin/main`에 push했다. 당시 `ls-remote`의 main SHA와 로컬 HEAD가 일치했다.
- `vimkim/my-cubrid-docs`가 PUBLIC인 것을 확인했다. 계획한 공개 URL에서 보고서를 다시 받아 승인한 보고서의 bytes와 SHA-256이 같음을 확인했다.
- 본문 게시 직전에 material 검사, 본문·보고서 fingerprint와 PR freshness 검사를 다시 통과했다.
- 저장한 본문을 `--body-file`로 [PR #8299](https://github.com/CUBRID/cubrid/pull/8299)에 게시했다. 다시 읽은 GitHub body는 파일의 bytes와 같고 SHA-256은 `f2209fa2de23279d33b2c7885115618a45483de10844e2b58448bb412d3f1270`이다.
- 제목, source head `067aae4e4e91fec8c71c914a4c7fc3c4b13dcd65`, head repository·branch, base `feature/oos-merge`, OPEN draft 상태가 유지됐음을 확인했다.
- 게시 후 status-only 조회에서도 CI 10개 성공, 미해결 review thread 0개, MERGEABLE/CLEAN이었다. 이것을 draft 해제나 리뷰어 승인으로 해석하지 않는다.
- TC #3898과 #4589는 게시 후 재조회에서도 OPEN draft다. source push, CI 요청, TC PR 변경이나 engine PR 병합은 수행하지 않았다.

본문·문서 게시 단위는 완료했다. 사람의 TC PR 종료와 리뷰·병합 판단은 별도로 남는다.
이 실행 기록과 체크리스트를 같은 승인 범위에서 docs `main`에 통합·push한 뒤 이 task의 worktree와 branch만 정리한다.
