# PR #8299 본문의 cycles 재측정 반영 context

작성일은 2026-11-03, Asia/Seoul이다. 이 문서는 게시 제안과 실행 기록이며 승인 토큰이 아니다.
목표는 PR #8299 본문에 2026-11-03 cycles 재측정 결과와 근거 링크를 더하는 것이다.

## 대상과 변경 전 상태

- Ticket은 CBRD-27785, agent는 claude다.
- Source commit은 `4c3c8d791ee619ad61701eff9555bc9ef27d9994`다. 확인한 원격 PR head와 같다. source push는 제안하지 않는다.
- Source repository와 PR head는 `vimkim/cubrid:CBRD-27785-oos-read-performance`다. Base는 `CUBRID/cubrid:feature/oos-merge`다.
- Target은 [CUBRID/cubrid PR #8299](https://github.com/CUBRID/cubrid/pull/8299)의 기존 본문 갱신이다. 상태는 OPEN draft다.
- 기존 title `[CBRD-27785] Reduce heap read and UPDATE CPU overhead`, base, draft 상태를 유지한다.
- 기존 GitHub body SHA-256은 `054a003803466619d651a93a0ab79e46c0eb447cbd52e1bcd93fbef1f07b584a`다. JSON에서 decode한 UTF-8 bytes에 추가 newline 없이 계산했다.
- 이 body는 2026-11-03 15:07(KST)에 다른 세션이 `4c3c8d791`, CI run 41485345491, 4,060B 기준, CTest 44/44를 반영한 판이다. 이번 수정은 그 내용을 그대로 두고 cycles 재측정만 더한다.

## 검토할 파일

Docs task branch는 `docs/CBRD-27785-cycles-layout`, integration branch는 `main`이다.

| 파일 | 보존 이유 |
| --- | --- |
| [PR 본문](CBRD-27785-final-head-pr-body_4c3c8d7_claude.md) | 승인 후 GitHub에 올릴 정확한 본문이다. |
| [cycles 재측정 근거](CBRD-27785-pr8299-cycles-layout_5837393_claude.md) | 본문이 새로 인용하는 근거다. JIRA 본문도 링크한다. |
| 이 context | 대상, 변경 전 fingerprint, 승인할 조치와 게시 결과를 추적한다. |
| [ticket README](README.md) | 새 문서를 색인한다. |
| [pr8299-quiet-20261103/](pr8299-quiet-20261103/) | 근거 문서의 표를 만든 요약 출력 4개다. |

근거 문서의 계획 공개 URL은 다음과 같다. docs 게시를 마친 뒤 PR 본문을 갱신한다.

https://github.com/vimkim/my-cubrid-docs/blob/main/cbrd-27785/CBRD-27785-pr8299-cycles-layout_5837393_claude.md

## 본문 변경

- 명령어 수 문장에 11-03 재측정 결과(0.46~1.81% 적음)를 더하고, "cycles는 판정 기준으로 쓰지 않았다"는 문장을 뺀다.
- cycles 재측정 결과 한 줄과 분기 예측 실패 위치 한 줄을 더한다.
- "stack과 명령어 수는" 문장에 cycles를 더한다.
- 근거 링크 한 줄을 더한다.

## 확인 후 수행할 조치

1. 이 task의 docs commit을 최신 로컬 docs `main`에 rebase하고 fast-forward 병합한다.
2. docs `origin/main`에 push하고 공개 URL의 근거 문서 bytes를 확인한다.
3. PR head, 본문 fingerprint, title, base, draft 상태를 다시 확인한다. 바뀌었으면 게시를 멈추고 다시 검토를 받는다.
4. 저장한 본문의 bytes를 그대로 PR #8299의 body에 올린다.
5. GitHub body와 저장 파일이 같은지 확인한다. 게시 결과를 이 context에 기록하고 docs `main`에 병합·push한다.
6. 이 task의 docs worktree와 branch만 강제 없이 정리한다.

engine source push, engine PR 병합, 추가 CI 실행, TC PR merge·close·branch 삭제는 제안하지 않는다. JIRA 갱신은 my-cubrid-jira의 별도 조치로 함께 제안한다.

## 준비 단계의 확인

- PR material 검사와 공유 링크 검사가 통과했다.
- 본문의 숫자는 근거 문서와 `pr8299-quiet-20261103/`의 출력에서 가져왔다.
- 이 세션의 로컬 `4c3c8d791` debug CTest 시도는 테스트 DB 환경 변수(`CUBRID_DATABASES`)가 debug preset에 준비되지 않아 테스트를 실행하지 못했다. 본문의 CTest 44/44 문장은 다른 세션이 쓴 것이며 이 세션에서 다시 확인하지 않았다.
- 게시 승인은 아직 받지 않았다.

검토할 본문 SHA-256은 `34e4875903dc1ee7091b3845c4a3e34cb99df11f9c3cbc77d42d405ad3d7875a`이다.
근거 문서 SHA-256은 `c12177f4158f54923e5f74271d0d3cc871c47aa89355ac40a65c56450cf8f663`이다.

## 승인 후 게시 결과

사용자가 2026-11-03에 docs·JIRA·PR 본문 게시를 승인했다. 결과는 다음과 같다.

- docs task commit 2개를 `main`에 rebase했다. 그사이 `main`에 다른 세션의 commit 6개가 들어와 `cbrd-27785/README.md` 색인이 충돌했다. 양쪽 행을 모두 남겨 풀었고 검토 파일의 fingerprint는 바뀌지 않았다. fast-forward 병합 후 `origin/main`에 push했다(`33551e3`).
- 공개 URL의 근거 문서와 PR 본문 bytes가 위 SHA-256과 같았다.
- my-cubrid-jira `main`에 JIRA 본문 commit `d006fb9`를 병합·push했다. 게시 직전 CBRD-27785 본문이 11-02 이후 바뀌지 않았음을 확인했다. `cubrid-jira update`의 dry-run 뒤 live update가 description 필드만 바꿨다. 다시 읽은 결과 상태는 Develop, 담당자는 그대로였다.
- 게시 직전 PR head `4c3c8d791`, title, base, draft 상태, 본문 fingerprint `054a0038…`가 준비 때와 같았다.
- 2026-11-03 15:49(KST)에 본문을 올렸다. GitHub body의 SHA-256이 `34e4875903dc1ee7091b3845c4a3e34cb99df11f9c3cbc77d42d405ad3d7875a`로 저장 파일과 같다. title·base·draft 상태는 바뀌지 않았다.
