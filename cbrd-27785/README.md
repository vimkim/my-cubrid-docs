# CBRD-27785: OOS 통합 후 일반 행 읽기 성능

관련 이슈: [CBRD-27785](https://jira.cubrid.org/browse/CBRD-27785).
관련 PR: [OOS 통합 PR #7990](https://github.com/CUBRID/cubrid/pull/7990).
이번 성능 수정의 별도 PR은 아직 게시하지 않았다. 대상은 `feature/oos-merge`다.
작성·수정일: 2026-10-27, Asia/Seoul.

| File | What it contains | Created | Last modified | Why it was created |
| --- | --- | --- | --- | --- |
| [분석과 검증](CBRD-27785-oos-read-performance_bcb900d_codex.md) | 원인, 읽기 계약, 세 저장 경로 구분과 최종 측정·검증 | 2026-10-27 | 2026-10-27 | 일반 heap 읽기 수정의 근거와 범위를 검토하기 위해 |
| [PR 본문](CBRD-27785-oos-read-performance-pr-body_bcb900d_codex.md) | 게시할 한국어 PR 설명 | 2026-10-27 | 2026-10-27 | GitHub 게시 전 본문을 검토하기 위해 |
| [게시 context](CBRD-27785-oos-read-performance-pr-context_bcb900d_codex.md) | source SHA, branch, 대상과 제안된 게시 작업 | 2026-10-27 | 2026-10-27 | 승인 후 정확한 revision과 작업으로 이어가기 위해 |
