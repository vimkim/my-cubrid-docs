# CBRD-27151 — Bulk file destroy와 복구 검토

[엔진 PR #7785](https://github.com/CUBRID/cubrid/pull/7785)와 [private testcase PR #4089](https://github.com/CUBRID/cubrid-testcases-private-ex/pull/4089)의 관련 문서다. 각 문서의 결론은 명시된 소스 리비전을 기준으로 읽는다.

| File | What it contains | Created | Last modified | Why it was created |
| --- | --- | --- | --- | --- |
| [tc_pr4089_review_70af47187982_ko.md](tc_pr4089_review_70af47187982_ko.md) | TC `70af47187982`의 P2 두 건, 검증 범위, 셸 모의실험 결과를 정리한 한국어 요약 | 2026-10-22 | 2026-10-22 | TC 리뷰의 수정 필요 사항과 실제 DB 검증 공백을 공유 |
| [code_review_6da4c473_codex.md](code_review_6da4c473_codex.md) | 엔진 `6da4c473` 기준의 코딩 규칙·요구사항 검토와 당시 리뷰 결과 | 2026-09-23 | 2026-09-23 | bulk destroy의 동시성·정합성 위험 검토 |
| [CBRD-27151-bulk-destroy-recovery-metadata_93f11fb3f_claude.md](CBRD-27151-bulk-destroy-recovery-metadata_93f11fb3f_claude.md) | 엔진 `93f11fb3f` 기준의 파일 메타데이터 discard와 복구 재실행 분석 | 2026-09-10 | 2026-09-10 | 체크포인트와 파일 메타데이터 내구성의 관계 확인 |
