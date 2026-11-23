# CBRD-28281 조사·PR 기록

Last modified: 2026-11-23 (Asia/Seoul).

[CBRD-28281](https://jira.cubrid.org/browse/CBRD-28281)는 ADR-0011(빈 OOS 페이지를 반환하지 않고 제자리에서 재사용, vacuum fast path 제거)의 채택 여부를 판단하는 이슈다. 관련 PR은 [PR #8493](https://github.com/CUBRID/cubrid/pull/8493)(Draft)이다.

| File | What it contains | Created | Last modified | Why it was created |
| --- | --- | --- | --- | --- |
| [pr-body-8493.md](pr-body-8493.md) | Draft PR #8493의 한국어 본문(목적, 구현 요약, 검증 및 남은 점) | 2026-11-23 | 2026-11-23 | PR #8493을 CBRD-28281 기준으로 갱신해 리뷰·triage에 공유하기 위해 |
| [pr-context-8493.md](pr-context-8493.md) | PR #8493 개정 이력, 기준 커밋, 기존 본문 SHA-256, 발행 절차 기록 | 2026-11-23 | 2026-11-23 | PR #8493 본문 갱신·검토 추적성을 남기기 위해 |
| [adr-0011-technical-verification.md](adr-0011-technical-verification.md) | vacuum drain 지연(`0.34 s → 2.4 s`) 원인 규명, 연속 churn 3종 측정, 빈 OOS 페이지 undo 전수 감사, 재초기화~INSERT 사이 crash 복구 테스트 검증 보고서 | 2026-11-23 | 2026-11-23 | CBRD-28281 채택 판단에 남아 있던 기술적 미검증 항목 2건을 닫기 위해 |
