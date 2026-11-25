# CBRD-28378

OOS 동시 INSERT가 latch를 쥔 OOS 페이지를 bestspace hint로 공개해, 조건부 latch 거절이 버퍼 프레임을 LRU 밖(VOID 영역)에 남기던 문제의 OOS 쪽 수정.

- JIRA: https://jira.cubrid.org/browse/CBRD-28378
- PR: 아직 없음 (draft body 준비됨, 엔진 브랜치 `CBRD-28378` 커밋 `d9d641fbac`)
- 관련: CBRD-28379 (page buffer 쪽 결함), CBRD-28377 (같은 고갈 상태의 vacuum fail-stop)

| File | What it contains | Created | Last modified | Why it was created |
| --- | --- | --- | --- | --- |
| [verification.md](verification.md) | 원인, 수정 내용, 수정 전·후 재현 결과, 단위 테스트, 독립 리뷰 처리, 제한 사항 | 2026-11-25 | 2026-11-25 | Record verification evidence for the fix |
| [pr-body.md](pr-body.md) | 엔진 PR 본문 초안 | 2026-11-25 | 2026-11-25 | Draft the PR description for review |
| [pr-context.md](pr-context.md) | PR 초안의 소스 커밋, 대상, 제안한 게시 작업, 정적 검사 결과 | 2026-11-25 | 2026-11-25 | Keep resume metadata separate from the body |
