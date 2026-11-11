# CBRD-27788: OOS 성능 측정

[PR #7990](https://github.com/CUBRID/cubrid/pull/7990)의 최신 OOS SELECT 실측과 최종 통합 성능 측정 준비를 정리한다.
수정일: 2026-11-11, Asia/Seoul.
일반 행 CPU 회귀 수정은 [CBRD-27785](../cbrd-27785/README.md)에서 별도로 다룬다.

| File | What it contains | Created | Last modified | Why it was created |
| --- | --- | --- | --- | --- |
| [OOS SELECT 성능 실측](CBRD-27788-oos-select-performance_dcbf09e_codex.md) | 정확한 revision, heap/overflow/OOS 저장 진단, 200개 기본 표본과 24개 저장장치 읽기 보조 표본 | 2026-10-27 | 2026-11-04 | 최신 PR의 작은 값 조회 이득과 큰 값 조회 비용을 검토하기 위해 작성 |
| [OOS 큰 값 조회 지연: 원인과 개선 방향](CBRD-27788-oos-cold-read-diagnosis_dcbf09e_codex.md) | 논문 형식의 원인·해결 후보·결론·한계. 파일 읽기 재생의 페이지 예시, 요청 수와 측정 구간 및 상세 재현 부록 | 2026-10-28 | 2026-10-28 | OOS Q4의 추가 지연 원인을 검증하기 위해 작성 |
| [최종 통합 성능 보고: 측정 준비와 인계](final-perf-handoff.md) | 2026-11-11 PR·도구 상태, 측정 시작 조건 R1~R7과 필요한 사건, 시나리오별 기존 명령, 반복·순서·산출물 요구, 빠진 근거 M1~M10, 최종 보고서 틀 | 2026-11-11 | 2026-11-11 | 최종 head가 정해지면 바로 AC-P1·AC-P3를 재고 보고할 수 있도록 준비하기 위해 |
