# T4 — 최소 재빌드 예산과 generated artifact 의미 잠금

- label: `wayfinder:grilling`
- status: open
- assignee: (none)
- blocked-by: [Git 커밋 갱신 계약 잠금](./T1-lock-git-revision-refresh-contract.md), [변동 버전 의존성 경계 잠금](./T2-lock-volatile-version-dependency-boundary.md), [런타임·패키지 버전 정체성 계약 잠금](./T3-lock-version-identity-consistency-contract.md)
- map: [CBRD-27124 CMake build version refresh](../map.md)

## Question

CBRD-27124가 생산성 문제를 해결했다고 판정할 수 있는 정량적 증분 빌드 예산은 무엇인가?

다음 build 유형별 허용 작업을 확정한다.

| Build 유형 | 확정할 항목 |
|---|---|
| source와 revision 모두 동일한 no-op | C/C++ compile, generated-file timestamp 변경, relink, reinstall의 허용 개수 |
| 빈 commit 등 revision만 변경 | 직접 version consumer compile 목록과 최대 개수, 허용 relink 목록 |
| version과 무관한 일반 source 변경 | 기존 증분 dependency 동작을 침해하지 않는 기준 |
| branch switch이지만 결과 revision 문자열 동일 | 내용 동일 산출물의 timestamp 보존 여부 |
| package 또는 install target 후속 실행 | runtime/package identity를 맞추기 위해 허용하는 regeneration 범위 |

generated artifact는 임시 파일과 내용 비교 후 교체하는 방식 등으로 내용이 같으면 timestamp를 보존해야 하는지도 결정한다. Ninja의 explain/log, Make dry-run 또는 compile command trace 중 어떤 관측값을 acceptance oracle로 사용할지도 명시한다.

완료 조건은 no-op과 revision-only 시나리오의 숫자 또는 명시적 파일 목록, 허용 relink/reinstall 대상, 실패 판정 방법이 확정되는 것이다. 구현은 하지 않는다.
