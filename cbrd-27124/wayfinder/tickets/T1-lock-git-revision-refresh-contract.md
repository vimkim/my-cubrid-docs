# T1 — Git 커밋 갱신 계약 잠금

- label: `wayfinder:grilling`
- status: open
- assignee: (none)
- blocked-by: (none)
- map: [CBRD-27124 CMake build version refresh](../map.md)

## Question

일반적인 CMake build가 별도 수동 configure 없이 현재 Git revision을 정확히 감지하도록 어떤 계약을 채택할 것인가?

결정은 다음 후보와 조합을 비교해야 한다.

- 현재 branch ref 또는 resolved Git path를 CMake configure dependency로 등록
- reflog 또는 worktree별 Git metadata를 감시
- build 단계의 always-run probe가 revision을 계산하고 내용이 바뀔 때만 산출물을 갱신
- configure dependency와 build-time probe를 결합한 hybrid

다음 상황별로 무엇이 truth source이고, 어떤 변화가 configure 또는 generated-file update를 일으키는지 명시해야 한다.

- 일반 clone에서 같은 branch에 새 commit 생성
- branch switch 또는 ref 이동
- linked worktree
- detached `HEAD`
- packed refs, 향후 reftable, reflog 비활성 환경
- Git metadata가 없는 source distribution과 `VERSION-DIST`
- 같은 hash를 가리키는 이름만 바뀐 경우
- 아무 변화가 없는 no-op build
- CMake 3.21 최소 버전과 Ninja/Make generator

완료 조건은 선택한 메커니즘, fallback 및 오류 정책, configure/build/package 단계의 실행 순서, revision 값을 소유하는 단일 truth source가 문장과 간단한 flow로 확정되는 것이다. 구현은 하지 않는다.
