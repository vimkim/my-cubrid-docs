# PR #8299 4-record 기준 반영 본문 게시 context

작성일은 2026-11-03, Asia/Seoul이다. 이 문서는 게시 제안과 실행 기록이며 승인 토큰이 아니다.
목표는 PR #8299 본문을 CBRD-27057의 4-record 기준을 반영한 head와 그 CI 결과에 맞추는 것이다.

## 대상과 변경 전 상태

- Ticket은 CBRD-27785, agent는 claude다.
- Source commit은 `4c3c8d791ee619ad61701eff9555bc9ef27d9994`다. `5837393ff` 위에 fast-forward로 올린 commit 하나다.
- Source repository와 PR head는 `vimkim/cubrid:CBRD-27785-oos-read-performance`다. 원격 PR head가 source commit과 같다. source push는 이 게시에 포함하지 않는다.
- Target은 [CUBRID/cubrid PR #8299](https://github.com/CUBRID/cubrid/pull/8299)의 기존 본문 갱신이다.
- Base는 `CUBRID/cubrid:feature/oos-merge`다.
- 기존 title은 `[CBRD-27785] Reduce heap read and UPDATE CPU overhead`다. title·base·OPEN draft 상태를 유지한다.
- 기존 GitHub body SHA-256은 `03db19346dff6d7ac5578f30f5a66cd4d14365d4797431a93c5ced1d87b12499`다. JSON에서 decode한 UTF-8 bytes에 추가 newline 없이 계산했다. [이전 게시본](CBRD-27785-review-fixes-pr-body_5837393_claude.md)과 bytes가 같다.
- `4c3c8d791`의 [CI run 41485345491](https://github.com/CUBRID/cubrid/actions/runs/41485345491)에서 gha-ci status 5개가 모두 성공했다.
- TC [#3898](https://github.com/CUBRID/cubrid-testcases/pull/3898)과 [#4589](https://github.com/CUBRID/cubrid-testcases-private-ex/pull/4589)는 OPEN이다. TC 변경은 필요 없고 사람의 종료 처리를 기다린다.

## 검토할 파일

Docs task branch는 `docs/CBRD-27785-four-record-target`, integration branch는 `main`이다.
Docs repository는 `vimkim/my-cubrid-docs`다.

| 파일 | 보존 이유 |
| --- | --- |
| [PR 본문](CBRD-27785-four-record-target-pr-body_4c3c8d7_claude.md) | GitHub에 올릴 정확한 본문이다. |
| 이 context | 대상, 변경 전 fingerprint, 조치와 게시 결과를 추적한다. |

본문은 새 설명 문서를 링크하지 않는다. 마지막 링크는 이미 공개된 `5837393ff` 근거 문서다.

## 수행할 조치

1. PR head·본문 fingerprint·title·base·draft 상태를 다시 확인한다. 바뀌었으면 게시를 멈추고 다시 검토를 받는다.
2. 저장한 본문의 bytes를 그대로 PR #8299의 body에 올린다. title·base·draft 상태는 바꾸지 않는다.
3. GitHub body와 저장 파일이 같은지 확인하고 결과를 이 context에 기록한다.
4. 같은 task의 리뷰 보고서·체크리스트 수정과 함께 docs `main`에 rebase·fast-forward 병합하고 push한다.
5. 이 task의 docs worktree와 branch만 강제 없이 정리한다.

engine source push, engine PR 병합, 추가 CI 실행, TC PR merge·close·branch 삭제는 하지 않는다.

## 준비 단계의 확인

- 본문은 2026-11-02에 사용자에게 보여 준 초안과 bytes가 같다. 2026-11-03에 사용자가 게시를 확인했다.
- PR material 검사와 공유 링크 검사가 통과했다.
- 본문 SHA-256은 `054a003803466619d651a93a0ab79e46c0eb447cbd52e1bcd93fbef1f07b584a`다. 파일의 실제 UTF-8 bytes로 계산했다.

## 게시 결과

2026-11-03에 사용자가 본문 게시를 확인했다. 권한 근거는 해당 대화의 확인이며 이 context를 승인 토큰으로 사용하지 않는다.

- 게시 직전에 본문 fingerprint, material 검사, 원격 PR head·branch·base·OPEN draft 상태와 기존 body fingerprint를 다시 확인했다. 준비 당시 값과 일치했다.
- 저장한 본문을 `--body-file`로 [PR #8299](https://github.com/CUBRID/cubrid/pull/8299)에 게시했다. 다시 읽은 GitHub body는 파일의 bytes와 같고 SHA-256은 `054a003803466619d651a93a0ab79e46c0eb447cbd52e1bcd93fbef1f07b584a`다.
- 제목, source head `4c3c8d791ee619ad61701eff9555bc9ef27d9994`, base `feature/oos-merge`, OPEN draft 상태가 유지됐다.
- source push, CI 요청, TC PR 변경, engine PR 병합은 하지 않았다.
