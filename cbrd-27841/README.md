# CBRD-27841 unused OOS recovery index

Remove the unused recovery index `RVREPL_OOS_DELETE` (140) before [PR 7990](https://github.com/CUBRID/cubrid/pull/7990) merges, and keep `RVOOS_NOTIFY_VACUUM`, which [#8434](https://github.com/CUBRID/cubrid/pull/8434) made live. Tracked as [CBRD-27841](https://jira.cubrid.org/browse/CBRD-27841). Current source is `1d86f1d31b` on `feature/oos-merge` `d25c9e8d20`. The scope came from review [r4409612618](https://github.com/CUBRID/cubrid/pull/7990#discussion_r4409612618).

History: the first attempt, [PR 8347](https://github.com/CUBRID/cubrid/pull/8347) (sources `eac70c7` and `e523d4f`), removed `RVOOS_NOTIFY_VACUUM` and closed unmerged on 2026-11-05. Its files below are kept as a record and are not reused.

Last modified: 2026-11-19, Asia/Seoul.

| File | What it contains | Created | Last modified | Why it was created |
| --- | --- | --- | --- | --- |
| [pr-body.md](pr-body.md) | `RVREPL_OOS_DELETE` 제거 PR 본문 | 2026-11-19 | 2026-11-19 | 새 범위의 draft PR을 만들기 전에 본문을 검토 |
| [pr-context.md](pr-context.md) | source·base, 게시 작업과 승인 범위, 게시 결과 | 2026-11-19 | 2026-11-19 | 이전 #8347 초안과 이번 PR의 작업을 구분 |
| [verification.md](verification.md) | `RV_fun[]` 순서, CTest, 강제 종료 후 복구와 vacuum 회수의 절차와 결과 | 2026-11-19 | 2026-11-19 | 리뷰어가 검증을 다시 실행할 수 있게 절차와 스크립트를 보존 |
| [CBRD-27841-recovery-index-cleanup-pr-body_e523d4f_codex.md](CBRD-27841-recovery-index-cleanup-pr-body_e523d4f_codex.md) | revision 1 유지와 현재 검증을 반영한 PR 본문 수정안 | 2026-11-02 | 2026-11-02 | 원격 본문을 바꾸기 전에 변경 범위를 검토 |
| [CBRD-27841-recovery-index-cleanup-pr-context_e523d4f_codex.md](CBRD-27841-recovery-index-cleanup-pr-context_e523d4f_codex.md) | source·설명 게시 완료와 현재 CI 검증 경계 | 2026-11-02 | 2026-11-02 | 현재 지시와 이전 승인·검증 이력을 구분 |
| [CBRD-27841-recovery-index-cleanup-pr-body_eac70c7_codex.md](CBRD-27841-recovery-index-cleanup-pr-body_eac70c7_codex.md) | 회사 PR의 변경·호환성·검증과 한계 | 2026-10-30 | 2026-10-30 | 실제 게시 전에 본문을 검토하도록 보존 |
| [CBRD-27841-recovery-index-cleanup-pr-context_eac70c7_codex.md](CBRD-27841-recovery-index-cleanup-pr-context_eac70c7_codex.md) | source/base, 검증·승인 범위와 실제 게시 결과 | 2026-10-30 | 2026-10-30 | 다른 에이전트의 작업과 승인 범위를 구분 |
| [ci_analysis_report_eac70c7_codex.md](ci_analysis_report_eac70c7_codex.md) | CI 종료, shell 두 실패의 관찰과 SQL 수집 무결성 경고 | 2026-10-30 | 2026-10-30 | R6 회귀 여부를 단정하지 않고 다음 검증에 필요한 증거를 보존 |
| [SQL-summary-nested-category_1c6b224_codex.md](SQL-summary-nested-category_1c6b224_codex.md) | CTP 중첩 범주 누락의 원인, 수정과 실제 3,533개 경로의 오프라인 보고서 재생 | 2026-10-30 | 2026-10-30 | SQL 증거 수집을 막은 생성기 결함의 수정·적용 경계를 보존 |
| [CTP-nested-summary-pr-body_4f720bd_codex.md](CTP-nested-summary-pr-body_4f720bd_codex.md) | CTP 생성기 수정의 회사 PR 793 본문 승인본 | 2026-10-30 | 2026-10-30 | 별도 회사 리뷰 전에 변경과 검증을 검토 |
| [CTP-nested-summary-publication_4f720bd_codex.md](CTP-nested-summary-publication_4f720bd_codex.md) | CUBRIDQA-1693·회사 draft PR 793, 게시 검증과 링크 보정, 남은 runtime·CI 검증 | 2026-10-31 | 2026-10-31 | 승인한 게시 결과와 후속 검증 경계를 보존 |

See the [R6 analysis and evidence](../cbrd-26357/PR-7990-R6-recovery-index-cleanup_dcbf09e_codex.md) and [shared checklist](../cbrd-26357/PR-7990-hornetmj-review-checklist_20261029_codex.md).
