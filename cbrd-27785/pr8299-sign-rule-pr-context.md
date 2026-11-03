# PR #8299 본문의 부호 규칙 정리 context

작성일은 2026-11-04, Asia/Seoul이다. 이 문서는 게시 제안과 실행 기록이며 승인 토큰이 아니다.

목표는 PR #8299 본문의 성능 수치를 JIRA CBRD-27785·CBRD-27816과 같은 규칙으로 맞추는 것이다. 규칙에서 성능 변화는 (기준 − 비교 대상) ÷ 기준이며, 좋아지면 +, 나빠지면 −다. 이전 `fd8624c` 측정만 남아 있던 develop 대비 문장은 `4c3c8d791`의 11-03 측정으로 바꾼다.

사용자 요청은 2026-11-04이다. 사용자가 "PR #8299 본문과 my-cubrid-docs 보고서들도 맞출지"라는 제안에 "yes"라고 답했다. 이 답은 본문을 고치는 작업을 시작하라는 뜻이다. 아래 본문을 검토하고 게시를 확인하는 단계는 아직 남아 있다.

## 대상과 변경 전 상태

- Ticket은 CBRD-27785, agent는 claude다.
- Source commit은 `4c3c8d791ee619ad61701eff9555bc9ef27d9994`다. 2026-11-04에 확인한 원격 PR head와 같다. source push는 제안하지 않는다.
- Source repository와 PR head는 `vimkim/cubrid:CBRD-27785-oos-read-performance`다. Base는 `CUBRID/cubrid:feature/oos-merge`다.
- Target은 [CUBRID/cubrid PR #8299](https://github.com/CUBRID/cubrid/pull/8299)의 기존 본문 갱신이다. 상태는 OPEN, ready for review다. 2026-11-03 17:51(KST)에 draft에서 ready로 바뀌었다.
- 기존 title `[CBRD-27785] Reduce heap read and UPDATE CPU overhead`, base, ready 상태를 유지한다.
- 기존 GitHub body SHA-256은 `34e4875903dc1ee7091b3845c4a3e34cb99df11f9c3cbc77d42d405ad3d7875a`다. JSON에서 decode한 UTF-8 bytes에 추가 newline 없이 계산했다. [이전 판](CBRD-27785-final-head-pr-body_4c3c8d7_claude.md)과 bytes가 같다.

## 검토할 파일

Docs task branch는 `docs/CBRD-27785-sign-convention`, integration branch는 `main`이다.

| 파일 | 보존 이유 |
| --- | --- |
| [PR 본문](pr8299-sign-rule-pr-body.md) | 확인 후 GitHub에 올릴 정확한 본문이다. |
| 이 context | 대상, 변경 전 fingerprint, 확인할 조치와 게시 결과를 추적한다. |

같은 task branch가 JIRA에서 링크하는 docs 보고서 10개의 부호도 바꾼다. 본문은 그 보고서를 새로 인용하지 않는다.

## 본문 변경

- cycles 회귀 기준 "+2% 초과"를 "2% 넘게 나빠짐"으로 바꾼다. 기준을 "충족하지 않았다"를 "해당하지 않았다"로 바꿔, 회귀가 없었다는 뜻이 바로 읽히게 한다.
- "stack, 명령어 수, cycles는 `5837393ff`에서 잰 값" 문장이 `f8114e432` 대비 측정을 가리킨다고 밝힌다. 새 develop 대비 측정은 `4c3c8d791`에서 했기 때문이다.
- "base 대비 성능은 이전 `fd8624c` 측정을 유지" 문장을 두 줄로 바꾼다.
  - 첫 줄은 [CBRD-27816](https://jira.cubrid.org/browse/CBRD-27816)의 11-03 측정이다. develop `4781495` 대비 서버 명령어 수로 풀 스캔 +0.79%, 조건 스캔 −0.83%, UPDATE −1.34%(중앙값)이다. 측정 조건은 DB locale `en_US.utf8`이며, 테이블 문자셋은 기록하지 않았다.
  - 둘째 줄은 vacuum이 측정 구간에 들어온 UPDATE 표본이다. 계산상 최악은 약 −7.9%이며, 그래서 성능 저하 2% 이내 기준을 모든 표본에서 충족하지는 않는다.
- 작성자 수용 문장을 바꾼다. 이전 문장은 "관측된 약 +5% 수준을 수용"이었다. 새 문장은 "남은 저하를 수용"이다. 수용하는 수치가 `fd8624c`의 약 5%에서 지금 측정으로 바뀌므로 작성자인 사용자의 확인이 필요하다.

나머지 줄은 그대로 둔다. "0.47~1.82% 적었습니다"와 "약 14% 느렸고"는 부호 없이 방향을 말로 적었으므로 규칙과 충돌하지 않는다.

## 확인 후 수행할 조치

1. 이 task의 docs commit을 최신 로컬 docs `main`에 rebase하고 fast-forward 병합한 뒤 `origin/main`에 push한다.
2. PR head, 본문 fingerprint, title, base, ready 상태를 다시 확인한다. 하나라도 바뀌었으면 게시를 멈추고 다시 검토를 받는다. 다른 세션이 이 PR의 본문을 맡고 있으므로 이 확인을 생략하지 않는다.
3. 저장한 본문의 bytes를 그대로 PR #8299의 body에 올린다.
4. GitHub body와 저장 파일의 SHA-256이 같은지 확인한다. 게시 결과를 이 context에 기록하고 docs `main`에 병합·push한다.
5. 이 task의 docs worktree와 branch만 강제 없이 정리한다.

engine source push, PR 병합, CI 실행, title 변경, TC PR 조치는 제안하지 않는다.

## 준비 단계의 확인

- PR material 검사(`--existing-body`)와 공유 링크 검사가 통과했다.
- 새 수치는 my-cubrid-jira의 CBRD-27816 본문(main `1e8b364`, JIRA에 게시됨)과 같다.
- 게시 확인은 아직 받지 않았다.

검토할 본문 SHA-256은 `06a8e150791150b2ff1c2d705ab06651ad8d497190a6d4a6aaf3c90778ed5c95`다.

## 승인 후 게시 결과

아직 없다.
