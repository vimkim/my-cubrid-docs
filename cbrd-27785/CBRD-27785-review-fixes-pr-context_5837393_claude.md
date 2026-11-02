# PR #8299 최종 head 본문 게시 context

작성일은 2026-11-02, Asia/Seoul이다. 이 문서는 게시 제안과 실행 기록이며 승인 토큰이 아니다.
목표는 PR #8299 본문을 리뷰 수정 후 최종 head와 그 CI·측정 결과에 맞추는 것이다.

## 대상과 변경 전 상태

- Ticket은 CBRD-27785, agent는 claude다.
- Source commit은 `5837393ffb9d69bccb93271d63b0e38b884e0ed4`다.
- Source repository와 PR head는 `vimkim/cubrid:CBRD-27785-oos-read-performance`다. 로컬 source branch도 같은 이름이며 같은 commit이고 tracked 변경이 없다.
- 확인한 원격 PR head는 source commit과 같다. source push는 제안하지 않는다.
- Target은 [CUBRID/cubrid PR #8299](https://github.com/CUBRID/cubrid/pull/8299)의 기존 본문 갱신이다.
- Base는 `CUBRID/cubrid:feature/oos-merge`다.
- 기존 title은 `[CBRD-27785] Reduce heap read and UPDATE CPU overhead`다. title·base·OPEN draft 상태를 유지한다.
- 기존 GitHub body SHA-256은 `f2209fa2de23279d33b2c7885115618a45483de10844e2b58448bb412d3f1270`이다. JSON에서 decode한 UTF-8 bytes에 추가 newline 없이 계산했다. 2026-10-31 게시본과 같다.
- 기존 body는 head를 `067aae4e4`로 표시한다. 그 뒤 commit 10개가 들어왔다.
- `5837393ff`의 [run 41435647083](https://github.com/CUBRID/cubrid/actions/runs/41435647083)은 shell 1건 실패로 끝났다. 실패 case만 다시 돌리는 [run 41459706876](https://github.com/CUBRID/cubrid/actions/runs/41459706876)을 사용자 지시로 시작했고 성공했다. gha-ci status 5개가 모두 이 run을 가리키며 성공이다.
- TC [#3898](https://github.com/CUBRID/cubrid-testcases/pull/3898)과 [#4589](https://github.com/CUBRID/cubrid-testcases-private-ex/pull/4589)는 OPEN이다. TC 변경은 필요 없고 사람의 종료 처리를 기다린다.

## 검토할 파일

Docs task branch는 `docs/CBRD-27785-pr8299-final`, integration branch는 `main`이다.
Docs repository는 `vimkim/my-cubrid-docs`다.

| 파일 | 보존 이유 |
| --- | --- |
| [PR 본문](CBRD-27785-review-fixes-pr-body_5837393_claude.md) | 승인 후 GitHub에 올릴 정확한 본문이다. |
| [검증·측정 근거](CBRD-27785-review-fixes_5837393_claude.md) | 본문이 인용하는 frame, 벤치마크, CI 판정의 근거다. |
| 이 context | 대상, 변경 전 fingerprint, 승인할 조치와 게시 결과를 추적한다. |
| [TODO 체크리스트](CBRD-27785-todo-checklist.md) | 최종 head와 남은 사람의 작업을 반영한다. |
| [ticket README](README.md) | 새 문서를 색인한다. |
| [pr8299-final-20261102/](pr8299-final-20261102/) | 벤치마크 표의 원래 비교 출력 4개다. |

근거 문서의 계획 공개 URL은 다음과 같다. docs 게시를 마친 뒤 PR 본문을 갱신한다.

https://github.com/vimkim/my-cubrid-docs/blob/main/cbrd-27785/CBRD-27785-review-fixes_5837393_claude.md

## 확인 후 수행할 조치

1. 이 task의 docs commit을 최신 로컬 docs `main`에 rebase하고 fast-forward 병합한다.
2. docs `origin/main`에 push하고 공개 URL의 근거 문서 bytes를 확인한다.
3. PR head·본문 fingerprint·title·base·draft 상태를 다시 확인한다. 바뀌었으면 게시를 멈추고 다시 검토를 받는다.
4. 저장한 본문의 bytes를 그대로 PR #8299의 body에 올린다. title·base·draft 상태는 바꾸지 않는다.
5. GitHub body와 저장 파일이 같은지 확인한다. 게시 결과를 이 context에 기록하고 docs `main`에 병합·push한다.
6. 이 task의 docs worktree와 branch만 강제 없이 정리한다.

engine source push, engine PR 병합, 추가 CI 실행, TC PR merge·close·branch 삭제, JIRA 갱신은 제안하지 않는다.

## 준비 단계의 확인

- 최종 head의 `heap_file.c`를 release SERVER_MODE 명령에 `-fstack-usage`만 더해 다시 컴파일했다. frame 표가 `eec338aaa` 측정과 같았다.
- `eec338aaa`와 `5837393ff`의 `heap_file.o` disassembly가 같음을 확인했다.
- 본문의 CTest 44/44 기록은 `5837393ff`에서 실행한 로그다.
- run 41435647083의 shard 47 결과 XML과 PR #8235 run 39701778475의 결과 XML을 직접 비교했다.
- PR material 검사와 공유 링크 검사가 통과했다. 근거 문서의 상대 링크 4개가 파일을 가리킨다.
- 게시 승인은 아직 받지 않았다. docs main 병합·push와 GitHub body 갱신은 수행하지 않았다.

검토할 본문 SHA-256은 `03db19346dff6d7ac5578f30f5a66cd4d14365d4797431a93c5ced1d87b12499`이다.
근거 문서 SHA-256은 `6f2fb5537bdec9538a66225908390a56b5711b054902fab771b2205038c18a10`다.
둘 다 파일의 실제 UTF-8 bytes로 계산했다.
