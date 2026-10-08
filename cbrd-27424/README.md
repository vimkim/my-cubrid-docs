# CBRD-27424: standalone workspace OOS

[PR #7925](https://github.com/CUBRID/cubrid/pull/7925) supports OOS storage in
standalone object loading and CSQL workspace writes.

Start with the Korean reviewer guide. Its **2026-10-07 snapshot** explains locally
integrated `28b65d18a`, published head `1c660d22e`, the pinned PR7927 dependency,
and pending shared integration. Historical reports retain their original revision
scope and do not establish later-head CI readiness.

Index updated: **2026-10-08 (Asia/Seoul)**. Document dates below preserve the existing
index metadata, with older dates taken from Git history.

## Reviewer documents

The guide explains the integrated implementation; the review records the preceding published-head assessment.

| File | What it contains | Created | Last modified | Why it was created |
| --- | --- | --- | --- | --- |
| [Korean reviewer guide (28b65d18a)](review-guide-pr7925-28b65d18a-ko.md) | Workspace OOS flow, buffer ownership and both completed simplifications | 2026-10-07 | 2026-10-07 | Help reviewers follow workspace OOS behavior and both simplifications |
| [Published-head review (1c660d22e)](code_review_1c660d22e_codex.md) | Correctness, standards and the proposed ownership simplification | 2026-10-07 | 2026-10-07 | Separate preserved behavior from optional ownership cleanup |

## Background and implementation decisions

Read these for the original defect, the first repair, and the measured restoration decision.

| File | What it contains | Created | Last modified | Why it was created |
| --- | --- | --- | --- | --- |
| [Standalone loader diagnosis (f4299ac)](CBRD-27424-sa-loaddb-diagnosis_f4299ac_codex.md) | Reproduction and debugger evidence for the missing OOS conversion path | 2026-09-15 | 2026-09-15 | Explain the original missing OOS conversion path |
| [Original implementation (e24b458)](CBRD-27424-sa-workspace-oos_e24b458_codex.md) | Workspace background, conversion boundary, reproduction and regression checks | 2026-09-11 | 2026-09-11 | Document standalone workspace OOS implementation |
| [Attrinfo restoration rationale (a142503dc)](CBRD-27424-workspace-oos-revert-rationale_a142503dc_codex.md) | Direct-byte benchmark, restoration decision and measurement limits | 2026-10-07 | 2026-10-07 | Explain the measured decision to restore attrinfo conversion |

## Historical review and CI reports

Each report applies only to the revision in its title; unresolved checks and attribution limits remain part of that record.

| File | What it contains | Created | Last modified | Why it was created |
| --- | --- | --- | --- | --- |
| [Implementation review (39d5e5e)](code_review_39d5e5e_fable.md) | Standards/Spec review after fixes and OOS dependency integration | 2026-09-18 | 2026-09-18 | Review merged OOS dependency compatibility |
| [CI build failure (e24b458)](ci_analysis_report_e24b458_codex.md) | Unconditional Python dependency failure during release configuration | 2026-09-15 | 2026-09-15 | Preserve CI evidence for the original implementation |
| [CI after Python repair (fe1a918)](ci_analysis_report_fe1a918_codex.md) | Verified build repair, SQL/medium results and pending shell coverage | 2026-09-15 | 2026-09-15 | Assess CI after the Python dependency change |
