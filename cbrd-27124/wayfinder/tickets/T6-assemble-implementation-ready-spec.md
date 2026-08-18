# T6 — 구현 가능한 명세와 JIRA handoff 조립

- label: `wayfinder:task`
- status: open
- assignee: (none)
- blocked-by: [Git 커밋 갱신 계약 잠금](./T1-lock-git-revision-refresh-contract.md), [변동 버전 의존성 경계 잠금](./T2-lock-volatile-version-dependency-boundary.md), [런타임·패키지 버전 정체성 계약 잠금](./T3-lock-version-identity-consistency-contract.md), [최소 재빌드 예산과 generated artifact 의미 잠금](./T4-lock-minimal-rebuild-budget.md), [검증 및 CI 행렬 잠금](./T5-lock-validation-and-ci-matrix.md)
- map: [CBRD-27124 CMake build version refresh](../map.md)

## Question

해결된 모든 결정 티켓을 구현자가 순서대로 실행할 수 있는 하나의 명세로 어떻게 조립하고 JIRA에 handoff할 것인가?

최종 명세에는 다음이 포함되어야 한다.

- 문제와 목표를 두 사용자 관점의 acceptance outcome으로 재확인
- 채택한 Git revision refresh flow와 source-distribution fallback
- 파일별 생성물, ownership, dependency 및 consumer 변경 계획
- 독립적으로 review 가능한 구현 slice와 각 slice의 완료 조건
- no-op, revision-only, runtime/package consistency 검증 절차
- generator, checkout 형태, platform별 test matrix
- race, timestamp, stale artifact, package identity 위험과 rollback 전략
- 변경하지 않을 영역과 향후 별도 이슈로 남길 항목

조립된 명세가 이전 티켓의 결정을 임의로 다시 열거나 모순되게 바꾸지 않는지 검토한다. 승인 후 canonical map의 결정 상태와 JIRA의 Wayfinder 링크 및 요약을 갱신한다. 실제 구현은 별도 작업으로 남긴다.
