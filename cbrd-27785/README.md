# CBRD-27785: 일반 행과 OOS 읽기 성능

관련 이슈: [CBRD-27785](https://jira.cubrid.org/browse/CBRD-27785).
관련 PR: [OOS 통합 PR #7990](https://github.com/CUBRID/cubrid/pull/7990).
성능 수정: [draft PR #8299](https://github.com/CUBRID/cubrid/pull/8299).
대상은 `feature/oos-merge`다.
작성일: 2026-10-27. 수정일: 2026-10-28, Asia/Seoul.

| File | What it contains | Created | Last modified | Why it was created |
| --- | --- | --- | --- | --- |
| [리뷰어 SQL과 잠정 +2% 검증](CBRD-27785-reviewer-reproduction_dcbf09e_codex.md) | 일반 UPDATE 구현·검증, 작성자의 약 +5% 수용과 PR #8299 통합 결정, 미충족 +2% 후속 CBRD-27816·Work 571 | 2026-10-28 | 2026-10-28 | PR #7990 새 재현 정보로 현재 우선 기준 1·3을 검증하기 위해 |
| [공통 읽기 경로와 실제 OOS 비용 조사](CBRD-27785-shared-read-path_f1b9903_codex.md) | production A/B/C callstack, allocator tree-key 폭 결함의 수명 추적·재현·통제와 공통 reader 비용 | 2026-10-28 | 2026-10-28 | 같은 reader를 유지하면서 두 경로를 함께 개선할 수 있는지 판단하기 위해 |
| [분석과 검증](CBRD-27785-oos-read-performance_bcb900d_codex.md) | 원인, 읽기 계약, 세 저장 경로 구분과 최종 측정·검증 | 2026-10-27 | 2026-10-27 | 일반 heap 읽기 수정의 근거와 범위를 검토하기 위해 |
| [PR 본문](CBRD-27785-oos-read-performance-pr-body_bcb900d_codex.md) | 게시할 한국어 PR 설명 | 2026-10-27 | 2026-10-27 | GitHub 게시 전 본문을 검토하기 위해 |
| [게시 context](CBRD-27785-oos-read-performance-pr-context_bcb900d_codex.md) | source SHA, branch, 승인 범위와 검증한 게시 결과 | 2026-10-27 | 2026-10-27 | 승인 후 정확한 revision과 작업으로 이어가기 위해 |
