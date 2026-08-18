# T3 — 런타임·패키지 버전 정체성 계약 잠금

- label: `wayfinder:grilling`
- status: open
- assignee: (none)
- blocked-by: [Git 커밋 갱신 계약 잠금](./T1-lock-git-revision-refresh-contract.md), [변동 버전 의존성 경계 잠금](./T2-lock-volatile-version-dependency-boundary.md)
- map: [CBRD-27124 CMake build version refresh](../map.md)

## Question

한 번의 build/package 흐름에서 모든 사용자 노출 버전 값이 같은 source revision을 나타낸다는 계약을 어떻게 정의할 것인가?

다음 소비자가 동일한 revision snapshot을 사용해야 하는지, 각 값이 언제 확정되는지를 명시한다.

- `cubrid_rel`의 release string과 commit hash
- `CUBRID_EXTRA_VERSION`, `CUBRID_VERSION`, `CUBRID_BUILD_NUMBER`
- broker가 표시하거나 보고하는 build number
- CPack metadata, archive/package filename, 설치 산출물
- Git metadata가 없는 source distribution의 `VERSION-DIST` 값

configure 도중과 build 도중 `HEAD`가 바뀌는 경우, package target만 나중에 실행하는 경우, incremental install을 수행하는 경우도 포함한다. 값 불일치를 허용하지 않는다면 실패, 재생성 또는 snapshot 고정 중 어떤 정책을 적용할지 결정한다.

완료 조건은 “같은 commit의 산출물”이라는 의미, 각 단계의 snapshot 시점, consumer별 기대 값과 불일치 처리 방식이 표 또는 flow로 확정되는 것이다. 구현은 하지 않는다.
