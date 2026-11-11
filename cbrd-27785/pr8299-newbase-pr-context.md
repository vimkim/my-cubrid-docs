# PR #8299 본문의 새 base 반영 context

작성일은 2026-11-10, Asia/Seoul이다. 이 문서는 게시 제안과 실행 기록이며 승인 토큰이 아니다.

목표는 base `feature/oos-merge`를 merge한 새 head에 맞춰 PR #8299 본문의 Remarks를 고치는 것이다. 사용자는 2026-11-10에 "PR 본문 Remarks를 고칠지"라는 질문에 "고치자."라고 답했다. 이 답은 본문 수정을 시작하라는 뜻이다. 본문 검토와 게시 확인은 아직 남아 있다.

## 대상과 변경 전 상태

- Ticket은 CBRD-27785, agent는 claude다.
- Source commit은 `855f220d532e222f2a266a0883c94a40bed3a388`다. 2026-11-10에 확인한 원격 PR head와 같다. 부모는 `4c3c8d791`(이전 head)와 `50619ce53`(base)다. source push는 제안하지 않는다.
- Source repository와 PR head는 `vimkim/cubrid:CBRD-27785-oos-read-performance`다. Base는 `CUBRID/cubrid:feature/oos-merge`다.
- Target은 [CUBRID/cubrid PR #8299](https://github.com/CUBRID/cubrid/pull/8299)의 기존 본문 갱신이다. 상태는 OPEN, ready for review다.
- 기존 title `[CBRD-27785] Reduce heap read and UPDATE CPU overhead`, base, ready 상태를 유지한다.
- 기존 GitHub body SHA-256은 `06a8e150791150b2ff1c2d705ab06651ad8d497190a6d4a6aaf3c90778ed5c95`다. JSON에서 decode한 UTF-8 bytes에 추가 newline 없이 계산했다. [이전 판](pr8299-sign-rule-pr-body.md)과 bytes가 같다.

## 검토할 파일

Docs task branch는 `docs/CBRD-27785-pr8299-newbase`, integration branch는 `main`이다.

| 파일 | 보존 이유 |
| --- | --- |
| [PR 본문](pr8299-newbase-pr-body.md) | 확인 후 GitHub에 올릴 정확한 본문이다. |
| 이 context | 대상, 변경 전 fingerprint, 확인할 조치와 게시 결과를 추적한다. |
| [새 base 성능 재측정](pr8299-newbase-perf.md) | 본문이 새로 링크하는 측정 보고서다. 본문 게시 전에 `main`에 있어야 한다. |
| [집계](pr8299-newbase-20261110/analysis.txt), `pr8299-newbase-20261110/analyze.py` | 보고서 수치의 start별 근거와 집계 방법이다. |

## 본문 변경

Purpose와 Implementation은 바꾸지 않는다. Remarks만 바꾼다.

- head를 `855f220d5`로 바꾸고, base merge와 충돌 해소를 적는다.
- CI를 새 run 42801815682로 바꾼다. run이 끝나면 이 줄만 결과로 바꾸고, 그 차이를 다시 검토받는다.
- 로컬 검증에 release CTest 50/50을 더하고, 이전 head의 검증은 이전 head 것으로 표시한다.
- 새 base 대비 서버 명령어 수를 더한다. 이전 base의 stack·명령어 수·cycles 문장 네 개는 한 문장으로 줄이고, merge 전 값임을 밝힌다. 세부는 기존 링크에 남는다.
- develop 대비 문장에 merge 전 측정임을 밝힌다.
- TC 문장에 TC 브랜치 갱신(각 레포의 `feature/oos-merge` merge)을 더한다.
- 새 성능 보고서 링크를 마지막에 더한다.

## 확인할 조치

1. docs task branch를 `origin/main`에 rebase하고 `main`에 fast-forward merge한 뒤 `origin main`에 push한다. 대상 파일은 위 표의 네 파일과 `cbrd-27785/README.md` 색인이다.
2. GitHub의 PR #8299 본문이 위 fingerprint와 같은지 다시 확인한다. 같으면 `pr8299-newbase-pr-body.md`의 내용을 그대로 본문으로 올린다. 다르면 멈추고 다시 검토받는다.
3. title, base, ready 상태는 바꾸지 않는다. source push는 하지 않는다.

## 게시 확인

2026-11-10에 사용자가 위 조치 목록을 보고 "끝나면 게시해줘."라고 답했다. 이 답은 CI run 42801815682가 끝난 뒤 위 1~3번을 실행하라는 확인이다. 그때 본문에서 바꾸는 것은 CI 줄 하나뿐이다. CI가 모두 성공하면 그 줄을 "release·debug 빌드, SQL, SQL(CCI), shell, medium이 모두 성공했습니다."로 바꿔 게시한다. 실패하거나 결과가 불완전하면 게시하지 않고 결과를 보고한 뒤 다시 검토받는다.

## 실행 기록

- 2026-11-11: CI run 42801815682가 failure로 끝났다. test_shell, test_sql, test_sql_by_cci, code-style이 실패했고, build 두 개와 test_medium은 성공했다. 게시 확인의 조건에 따라 docs integration과 PR 본문 갱신을 하지 않았다. GitHub 본문은 바꾸지 않았다.
- 2026-11-11: head가 `cd24a212aa81e2a11d72d1ac57bb10113727a4d8`로 바뀌었다(`heap_file.h`에 빈 줄 하나 추가, code-style 수정). source commit을 이 값으로 바꾸고 본문의 head·CTest·CI 줄을 고쳤다(`a0a1af0`). 원격 PR head도 같은 값이다. 두 TC 레포의 `feature/oos-merge`에 develop의 TC revert를 가져오고 `tc/pr-8299`에 반영했다.
- 2026-11-11: CI run 42968315485에서 build 두 개, SQL, medium, code-style이 성공했다. shell `cbrd_25894.sh` 1건은 재실행 run 42990122676에서 성공했다. SQL(CCI)만 develop 공통 실패로 남았다.

## 게시 확인 (cd24a212a 판)

2026-11-11에 사용자가 고친 본문과 조치 목록(docs를 `main`에 merge·push, PR 본문 갱신)을 보고 "1 진행해줘."라고 답했다. 위 "확인할 조치" 1~3번을 이 판으로 실행한다.
