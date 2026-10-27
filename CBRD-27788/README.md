# CBRD-27788: OOS 성능 측정

[PR #7990](https://github.com/CUBRID/cubrid/pull/7990)의 최신 OOS SELECT 실측을 정리한다.
일반 행 CPU 회귀 수정은 [CBRD-27785](../cbrd-27785/README.md)에서 별도로 다룬다.

| File | What it contains | Created | Last modified | Why it was created |
| --- | --- | --- | --- | --- |
| [OOS SELECT 성능 실측](CBRD-27788-oos-select-performance_dcbf09e_codex.md) | 정확한 revision, heap/overflow/OOS 저장 진단, 200개 기본 표본과 24개 저장장치 읽기 보조 표본 | 2026-10-27 | 2026-10-27 | 최신 PR의 작은 값 조회 이득과 큰 값 조회 비용을 검토하기 위해 작성 |
