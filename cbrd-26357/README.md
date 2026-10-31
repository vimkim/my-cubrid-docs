# CBRD-26357: out-of-row overflow storage

Analysis and CI reports for [PR 7990](https://github.com/CUBRID/cubrid/pull/7990) and earlier OOS PR revisions. Each report applies to its stated source revision.

Last modified: 2026-10-31, Asia/Seoul.

| File | What it contains | Created | Last modified | Why it was created |
| --- | --- | --- | --- | --- |
| [PR-7990-hornetmj-review-checklist_20261029_codex.md](PR-7990-hornetmj-review-checklist_20261029_codex.md) | 리뷰 6개의 체크리스트, R6 CI 경고와 CTP 생성기 수정·별도 회사 PR 793 게시 | 2026-10-29 | 2026-10-31 | 팀장님 리뷰를 하나씩 이해하고 근거와 진행 상태를 보존 |
| [PR-7990-R6-recovery-index-cleanup_dcbf09e_codex.md](PR-7990-R6-recovery-index-cleanup_dcbf09e_codex.md) | 미사용 인덱스 제거, 형식 2의 근거, 수정 전후 CTest와 데이터 보존 검증·한계 | 2026-10-30 | 2026-10-30 | R6 수정의 호환성과 실행 근거를 독립 리뷰 단위로 보존 |
| [PR-7990-R2-vacuum-heap-header-deadlock_dcbf09e_codex.md](PR-7990-R2-vacuum-heap-header-deadlock_dcbf09e_codex.md) | PR 8235 비교, OOS vacuum과 힙 할당의 래치 순환, 실제 vacuum 재현, 조건부 조회와 재시작 수정, 검증과 한계 | 2026-10-31 | 2026-10-31 | R2를 기존 수정과 구분하고 재현·수정·결정 근거를 보존 |
| [CBRD-XXXXX-oos-vacuum-heap-header-wait-pr-body_b5d5310_claude.md](CBRD-XXXXX-oos-vacuum-heap-header-wait-pr-body_b5d5310_claude.md) | R2 회사 PR 본문의 티켓 발급 전 초안. [cbrd-27860](../cbrd-27860/README.md)의 본문으로 대체됨 | 2026-10-31 | 2026-10-31 | 티켓 발급과 게시 전에 본문을 검토 |
| [CBRD-XXXXX-oos-vacuum-heap-header-wait-pr-context_b5d5310_claude.md](CBRD-XXXXX-oos-vacuum-heap-header-wait-pr-context_b5d5310_claude.md) | R2의 티켓 발급 전 게시 제안. [cbrd-27860](../cbrd-27860/README.md)의 게시 맥락으로 대체됨 | 2026-10-31 | 2026-10-31 | 승인 범위와 티켓 발급 뒤의 재개 절차를 보존 |
| [CBRD-XXXXX-oos-relocation-forward-slot-pr-body_c05abc8_claude.md](CBRD-XXXXX-oos-relocation-forward-slot-pr-body_c05abc8_claude.md) | R5 회사 PR 본문의 티켓 발급 전 초안. [cbrd-27858](../cbrd-27858/README.md)의 본문으로 대체됨 | 2026-10-30 | 2026-10-30 | 티켓 발급과 게시 전에 본문을 검토 |
| [CBRD-XXXXX-oos-relocation-forward-slot-pr-context_c05abc8_claude.md](CBRD-XXXXX-oos-relocation-forward-slot-pr-context_c05abc8_claude.md) | R5의 티켓 발급 전 게시 제안. [cbrd-27858](../cbrd-27858/README.md)의 게시 맥락으로 대체됨 | 2026-10-30 | 2026-10-30 | 승인 범위와 티켓 발급 뒤의 재개 절차를 보존 |
| [CBRD-26357-oos-engine_5a70787_claude.md](CBRD-26357-oos-engine_5a70787_claude.md) | 엔진 PR #7990(`5a70787`)의 구조, 저장 형식, 읽기·쓰기·vacuum·복제, 호환성, 검증, 알려진 미해결 사항. 검증, 호환성, 미해결 사항은 head `dcbf09e` 기준으로 갱신(시작 시 저장 형식 거부 -1392, CDC 테스트의 QA 합의, Greptile 4차 P1 결과) | 2026-10-27 | 2026-10-27 | 리뷰어가 149개 파일을 이해하고 머지 위험을 판단하도록 설명 |
| [CBRD-26357-oos-engine-pr-body_5a70787_claude.md](CBRD-26357-oos-engine-pr-body_5a70787_claude.md) | 엔진 PR #7990 본문: 목적, 구현 요약, 검증, 호환성, 미해결 사항 | 2026-10-27 | 2026-10-27 | 준비 중이던 PR 본문을 실제 내용으로 교체 |
| [CBRD-26357-oos-engine-pr-context_5a70787_claude.md](CBRD-26357-oos-engine-pr-context_5a70787_claude.md) | #7990 본문 게시용 리비전, 원본 본문과 지문, 게시 단계 | 2026-10-27 | 2026-10-27 | 게시 전 검토 범위와 재개 조건을 보존 |
| [CBRD-26357-oos-engine-pr-body_4408135_claude.md](CBRD-26357-oos-engine-pr-body_4408135_claude.md) | 엔진 PR #7990 본문 `4408135` 개정: Greptile P1 3건의 결과(수정, 형식 유지, CBRD-27781 분리)와 새 head 검증 | 2026-10-27 | 2026-10-27 | Greptile 4차 리뷰 P1 처리 결과를 본문의 미해결 사항에 반영 |
| [CBRD-26357-oos-engine-pr-context_4408135_claude.md](CBRD-26357-oos-engine-pr-context_4408135_claude.md) | #7990 본문 `4408135` 개정의 범위, 원본 본문 지문, 게시 단계와 기록 | 2026-10-27 | 2026-10-27 | 개정 범위와 게시 결과를 보존 |
| [CBRD-26357-oos-engine-pr-body_dcbf09e_claude.md](CBRD-26357-oos-engine-pr-body_dcbf09e_claude.md) | 엔진 PR #7990 본문 `dcbf09e` 개정: 시작 시 저장 형식 거부(-1392)와 한계, CDC 테스트의 QA 합의, 새 head 검증, 리뷰 대응 현황 링크 | 2026-10-27 | 2026-10-27 | 리뷰 5662427700 대응과 저장 형식 검사 커밋을 본문에 반영 |
| [CBRD-26357-oos-engine-pr-context_dcbf09e_claude.md](CBRD-26357-oos-engine-pr-context_dcbf09e_claude.md) | #7990 본문 `dcbf09e` 개정의 범위, 근거, 원본 본문 지문, 게시 단계와 기록 | 2026-10-27 | 2026-10-27 | 개정 범위와 게시 결과를 보존 |
| [CBRD-26357-tc-pr-changes_5a70787_claude.md](CBRD-26357-tc-pr-changes_5a70787_claude.md) | 엔진 `5a70787`과 짝인 TC PR 두 개(#3551, #4210)의 모든 테스트 변경, 이유, 근거 커밋, 머지 시 주의점 | 2026-10-27 | 2026-10-27 | TC PR 본문의 상세 근거와 리뷰어용 변경 이력을 남김 |
| [CBRD-26357-public-tc-changes-pr-body_70db22a_claude.md](CBRD-26357-public-tc-changes-pr-body_70db22a_claude.md) | cubrid-testcases#3551 본문: SQL·medium 테스트 3개의 변경과 이유 | 2026-10-27 | 2026-10-27 | public TC PR 본문을 실제 변경 내용으로 교체 |
| [CBRD-26357-public-tc-changes-pr-context_70db22a_claude.md](CBRD-26357-public-tc-changes-pr-context_70db22a_claude.md) | #3551 본문 게시용 리비전, 원본 지문, 게시 단계 | 2026-10-27 | 2026-10-27 | 게시 전 검토 범위와 재개 조건을 보존 |
| [CBRD-26357-private-tc-changes-pr-body_75a0202_claude.md](CBRD-26357-private-tc-changes-pr-body_75a0202_claude.md) | cubrid-testcases-private-ex#4210 본문: shell 테스트 17개의 변경과 이유 | 2026-10-27 | 2026-10-27 | private TC PR 본문을 실제 변경 내용으로 교체 |
| [CBRD-26357-private-tc-changes-pr-context_75a0202_claude.md](CBRD-26357-private-tc-changes-pr-context_75a0202_claude.md) | #4210 본문 게시용 리비전, 원본 지문, 게시 단계 | 2026-10-27 | 2026-10-27 | 게시 전 검토 범위와 재개 조건을 보존 |
| [CBRD-26357-oos-index-capacity-pr-body_3252fcf_codex.md](CBRD-26357-oos-index-capacity-pr-body_3252fcf_codex.md) | PR 7990 본문에 추가할 인덱스 TC 변경 이유와 검증 결과 | 2026-10-22 | 2026-10-22 | 페이지 수 기대값 조정을 리뷰어에게 설명 |
| [CBRD-26357-oos-index-capacity-pr-context_3252fcf_codex.md](CBRD-26357-oos-index-capacity-pr-context_3252fcf_codex.md) | 본문 원본 지문, 소스·TC 커밋 및 게시 결과 | 2026-10-22 | 2026-10-23 | 게시 전 검토 범위와 재개 조건을 보존 |
| [CBRD-26357-oos-index-capacity_3252fcf_codex.md](CBRD-26357-oos-index-capacity_3252fcf_codex.md) | OOS 페이지 배치 근거와 현재 head의 TC 수정 전후 검증 | 2026-10-22 | 2026-10-22 | 최소 답지 수정의 근거와 검증 한계를 기록 |
| [non_cdc_followup_1a8c705_codex.md](non_cdc_followup_1a8c705_codex.md) | Crash attempts, default repair, controlled experiments, and merge/ticket attribution | 2026-10-22 | 2026-10-22 | Explain non-CDC failures and prepare the confirmed repair |
| [ci_analysis_report_52987c6_claude.md](ci_analysis_report_52987c6_claude.md) | Warning snapshot at `52987c6` (rerun running), with validated run 40323508581 shell evidence, merge-base comparison, history, and provisional hypotheses for three shell failures | 2026-10-26 | 2026-10-26 | Classify the three shell failures before the rerun result is collected |
| [ci_analysis_report_1a8c705_codex.md](ci_analysis_report_1a8c705_codex.md) | Four non-CDC shell failures, inline evidence inventory and original CI run, unavailable baseline, history, and focused reproduction | 2026-10-21 | 2026-10-28 | Explain failures after the develop merge at `1a8c705` |
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
