# CBRD-28377 OOS notification reclaim stops the server on a transient error

[CBRD-28377](https://jira.cubrid.org/browse/CBRD-28377): vacuum이 UPDATE가 버린 OOS chain을 회수하다 -1123(버퍼 프레임 대기 시간 초과)을 만나면 서버를 FATAL로 멈추던 문제. 수정은 `CUBRID/cubrid` `develop` `ca39c2c6a4` 위의 로컬 커밋 `ebdd0f0462` (브랜치 `CBRD-28377`, 아직 push와 PR 없음). 관련: [CBRD-27933](../cbrd-27933/README.md), [CBRD-28276](https://jira.cubrid.org/browse/CBRD-28276).

Last modified: 2026-11-25, Asia/Seoul.

| File | What it contains | Created | Last modified | Why it was created |
| --- | --- | --- | --- | --- |
| [verification.md](verification.md) | 원인, 오류 분류와 안전성 근거, 수정 내용, 수정 전후 재현(단위 시험, debug 서버), 시험 결과, postpone 경로 정책, 사양 개정 제안, 독립 리뷰 처리, 기존 문제, 제한 | 2026-11-25 | 2026-11-25 | 수정 PR을 올리기 전에 재현과 검증 근거, 담당자 결정 사항을 남기도록 작성 |
| [pr-body.md](pr-body.md) | 수정 PR 본문 초안 | 2026-11-25 | 2026-11-25 | PR을 만들기 전에 본문을 검토받도록 작성 |
| [pr-context.md](pr-context.md) | PR 초안의 소스 커밋, 대상, 게시 작업 목록, 정적 검사 처리 | 2026-11-25 | 2026-11-25 | PR 게시를 이어서 하거나 다시 확인할 수 있도록 작성 |
