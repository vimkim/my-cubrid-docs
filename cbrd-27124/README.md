# CBRD-27124: 빌드 버전 갱신과 재빌드 범위

[CBRD-27124](https://jira.cubrid.org/browse/CBRD-27124)의 분석, 설계 결정 준비, 캐시 실측을 모은다. 2026-10-27 구현 `0d2a76e`를 [Draft PR #8298](https://github.com/CUBRID/cubrid/pull/8298)로 발행했다. 빌드별 통계 기반은 [PR #8254](https://github.com/CUBRID/cubrid/pull/8254)로 머지되었다.

| File | What it contains | Created | Last modified | Why it was created |
| --- | --- | --- | --- | --- |
| [CBRD-27124-build-version-pr-body_0d2a76e_codex.md](CBRD-27124-build-version-pr-body_0d2a76e_codex.md) | 버전 헤더 분리 draft PR 본문 | 2026-10-27 | 2026-10-27 | PR 발행 전 본문 검토 |
| [CBRD-27124-build-version-pr-context_0d2a76e_codex.md](CBRD-27124-build-version-pr-context_0d2a76e_codex.md) | 소스 revision, 발행 대상·작업, 검증 및 재개 정보 | 2026-10-27 | 2026-10-27 | 동일 자료로 PR 발행과 CI를 재개 |
| [CBRD-27124-build-version-verification_0d2a76e_codex.md](CBRD-27124-build-version-verification_0d2a76e_codex.md) | 재컴파일 11개·로컬 hit 99.07%, 실제 CI 수치와 clean/3rdparty·캐시 비교 조건 | 2026-10-27 | 2026-10-27 | 로컬 실측과 실제 CI 결론의 범위 구분 |
| [ccache-commit-change-measurement_2026-10-21.md](ccache-commit-change-measurement_2026-10-21.md) | 같은 커밋, 빈 커밋 후 재구성, 원래 커밋 복귀의 Debug 빌드 실측과 한계 | 2026-10-21 | 2026-10-21 | 버전 변경이 실제 CUBRID 재빌드와 캐시 hit에 미치는 영향 확인 |
| [wayfinder/map.md](wayfinder/map.md) | 버전 갱신 계약과 구현 명세를 결정하는 분석 지도 | 2026-08-18 | 2026-08-18 | 구현 전 결정할 계약과 순서 정리 |
| [wayfinder/tickets/T1-lock-git-revision-refresh-contract.md](wayfinder/tickets/T1-lock-git-revision-refresh-contract.md) | Git revision 변경 감지 계약 | 2026-08-18 | 2026-08-18 | 일반 빌드의 버전 갱신 계약 결정 |
| [wayfinder/tickets/T2-lock-volatile-version-dependency-boundary.md](wayfinder/tickets/T2-lock-volatile-version-dependency-boundary.md) | 변동 버전 값의 의존성 경계 | 2026-08-18 | 2026-08-18 | 버전 변경의 재컴파일 전파 범위 결정 |
| [wayfinder/tickets/T3-lock-version-identity-consistency-contract.md](wayfinder/tickets/T3-lock-version-identity-consistency-contract.md) | 실행 파일과 패키지의 버전 일관성 계약 | 2026-08-18 | 2026-08-18 | 산출물 사이의 revision 정합성 결정 |
| [wayfinder/tickets/T4-lock-minimal-rebuild-budget.md](wayfinder/tickets/T4-lock-minimal-rebuild-budget.md) | 버전 변경 시 허용할 최소 재빌드 작업량 | 2026-08-18 | 2026-08-18 | 재빌드 절감의 판정 기준 결정 |
| [wayfinder/tickets/T5-lock-validation-and-ci-matrix.md](wayfinder/tickets/T5-lock-validation-and-ci-matrix.md) | 로컬 검증과 CI 행렬 | 2026-08-18 | 2026-08-18 | 계약을 확인할 환경과 검증 범위 결정 |
| [wayfinder/tickets/T6-assemble-implementation-ready-spec.md](wayfinder/tickets/T6-assemble-implementation-ready-spec.md) | 구현 명세와 JIRA handoff 조립 | 2026-08-18 | 2026-08-18 | 앞선 결정들을 구현 가능한 문서로 연결 |
