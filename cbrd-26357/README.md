# CBRD-26357: out-of-row overflow storage

Analysis and CI reports for [PR 7990](https://github.com/CUBRID/cubrid/pull/7990) and earlier OOS PR revisions. Each report applies to its stated source revision.

Last modified: 2026-10-22, Asia/Seoul.

| File | What it contains | Created | Last modified | Why it was created |
| --- | --- | --- | --- | --- |
| [CBRD-26357-oos-index-capacity-pr-body_3252fcf_codex.md](CBRD-26357-oos-index-capacity-pr-body_3252fcf_codex.md) | PR 7990 본문에 추가할 인덱스 TC 변경 이유와 검증 결과 | 2026-10-22 | 2026-10-22 | 페이지 수 기대값 조정을 리뷰어에게 설명 |
| [CBRD-26357-oos-index-capacity-pr-context_3252fcf_codex.md](CBRD-26357-oos-index-capacity-pr-context_3252fcf_codex.md) | 본문 원본 지문, 소스·TC 커밋 및 검토할 게시 작업 | 2026-10-22 | 2026-10-22 | 게시 전 검토 범위와 재개 조건을 보존 |
| [CBRD-26357-oos-index-capacity_3252fcf_codex.md](CBRD-26357-oos-index-capacity_3252fcf_codex.md) | OOS 페이지 배치 근거와 현재 head의 TC 수정 전후 검증 | 2026-10-22 | 2026-10-22 | 최소 답지 수정의 근거와 검증 한계를 기록 |
| [non_cdc_followup_1a8c705_codex.md](non_cdc_followup_1a8c705_codex.md) | Crash attempts, default repair, controlled experiments, and merge/ticket attribution | 2026-10-22 | 2026-10-22 | Explain non-CDC failures and prepare the confirmed repair |
| [ci_analysis_report_1a8c705_codex.md](ci_analysis_report_1a8c705_codex.md) | Four non-CDC shell failures, validated evidence, unavailable baseline, history, and focused reproduction | 2026-10-21 | 2026-10-21 | Explain failures after the develop merge at `1a8c705` |
| [ci_analysis_report_07fef9d_claude.md](ci_analysis_report_07fef9d_claude.md) | CI Failure Analysis: PR #6864 at `07fef9d` | 2026-08-05 | 2026-08-05 | Preserve revision-specific analysis and follow-up context |
| [ci_analysis_report_1ec35f8_codex.md](ci_analysis_report_1ec35f8_codex.md) | PR #7990 CI 수집 경고 — 1ec35f8 | 2026-09-29 | 2026-09-29 | Preserve revision-specific analysis and follow-up context |
| [ci_analysis_report_2940b1c_claude.md](ci_analysis_report_2940b1c_claude.md) | CI Failure Analysis: PR #6864 at `2940b1c` | 2026-09-05 | 2026-09-08 | Preserve revision-specific analysis and follow-up context |
| [ci_analysis_report_38093ea_codex.md](ci_analysis_report_38093ea_codex.md) | CI Failure Analysis: PR #6864 at `38093ea` | 2026-09-15 | 2026-09-15 | Preserve revision-specific analysis and follow-up context |
| [ci_analysis_report_7008bee_codex.md](ci_analysis_report_7008bee_codex.md) | CI Snapshot Warning: PR #7990 at `7008bee` | 2026-09-29 | 2026-09-29 | Preserve revision-specific analysis and follow-up context |
| [ci_analysis_report_b8f3c48_codex.md](ci_analysis_report_b8f3c48_codex.md) | CI Snapshot Warning: PR #7990 at `b8f3c48` | 2026-09-29 | 2026-09-29 | Preserve revision-specific analysis and follow-up context |
| [ci_analysis_report_c2cbeaf_claude.md](ci_analysis_report_c2cbeaf_claude.md) | CI Failure Analysis: PR #6864 test_shell at `c2cbeaf` (historical commit) | 2026-08-03 | 2026-08-03 | Preserve revision-specific analysis and follow-up context |
| [ci_analysis_report_f4299ac_codex.md](ci_analysis_report_f4299ac_codex.md) | CI Failure Analysis: PR #6864 at `f4299ac` | 2026-09-09 | 2026-09-09 | Preserve revision-specific analysis and follow-up context |
| [ci_analysis_report_fb567a6_codex.md](ci_analysis_report_fb567a6_codex.md) | PR 7990 analysis of three unexpected CI failures | 2026-10-01 | 2026-10-01 | Preserve revision-specific analysis and follow-up context |
| [ci_deepdive_temp_enc_09_cbrd_25080_38093ea_claude.md](ci_deepdive_temp_enc_09_cbrd_25080_38093ea_claude.md) | CI Deep Dive: `temp_enc_09` and `cbrd_25080` — PR #6864 at `38093ea` | 2026-09-18 | 2026-09-18 | Preserve revision-specific analysis and follow-up context |
| [next_steps_2940b1c_claude.md](next_steps_2940b1c_claude.md) | PR #6864 at `2940b1c` — next steps and recommended skill paths | 2026-09-05 | 2026-09-08 | Preserve revision-specific analysis and follow-up context |
