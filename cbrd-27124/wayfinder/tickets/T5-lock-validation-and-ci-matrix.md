# T5 — 검증 및 CI 행렬 잠금

- label: `wayfinder:grilling`
- status: open
- assignee: (none)
- blocked-by: [Git 커밋 갱신 계약 잠금](./T1-lock-git-revision-refresh-contract.md), [변동 버전 의존성 경계 잠금](./T2-lock-volatile-version-dependency-boundary.md), [런타임·패키지 버전 정체성 계약 잠금](./T3-lock-version-identity-consistency-contract.md), [최소 재빌드 예산과 generated artifact 의미 잠금](./T4-lock-minimal-rebuild-budget.md)
- map: [CBRD-27124 CMake build version refresh](../map.md)

## Question

정합성 회귀와 광범위한 재컴파일 회귀를 자동으로 잡는 최소 검증 행렬을 어떻게 구성할 것인가?

다음 축의 필수 조합과 선택 조합을 정한다.

- checkout: 일반 clone, linked worktree, detached `HEAD`, Git 없는 source distribution
- revision event: no-op, 빈 commit, source commit, branch switch, ref 이동
- generator: Ninja, Unix Makefiles
- CMake: 최소 지원 버전 3.21과 주력 CI 버전
- platform: Linux 필수 범위, Windows/version resource 검증 범위
- consumer: `cubrid_rel`, broker build number, CPack/package metadata
- performance oracle: compile 수, generated-file timestamp, relink 목록

테스트가 개발 branch를 직접 변형하지 않도록 임시 clone/worktree를 사용할지, CMake script test 또는 shell integration test로 둘지, CI에서 어느 빈도로 실행할지 결정한다. 실패 시 실제 값, 기대 값, 실행된 compile/relink 목록을 진단 정보로 남기는 방법도 포함한다.

완료 조건은 각 행의 사전 조건, 동작, expected result, 자동화 위치, 필수 CI gate 여부가 명시된 실행 가능한 test matrix가 확정되는 것이다. 구현은 하지 않는다.
