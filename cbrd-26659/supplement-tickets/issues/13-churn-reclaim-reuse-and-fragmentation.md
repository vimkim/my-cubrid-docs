# 13: 반복 쓰기·회수·재사용·단편화 추세

**What to build:** 독립적인 churn/reader/abort/restart 사례로 survivor, chunk 삭제·페이지 반환, 재사용·성장과 fresh heap 대비 공간 추세 확인.

**Blocked by:** [01: 기준 리비전·커버리지 확정과 HAS_OOS 관측 tracer](01-baseline-and-record-observer.md)

**Status:** ready-for-agent

기준일: 2026-10-21, Asia/Seoul. 기존 work: Work461, Work458, Work459. Spec user stories: 22, 41, 42, 43, 44, 45, 46, 47, 48, 49.

실행 전 [지도와 공통 완료 규칙](../map.md)을 읽는다. 현행 권한·자원 격리·native 검증 규칙은 모든 사례에 적용한다.

## Acceptance criteria

- [ ] 반복 INSERT/DELETE와 INSERT/UPDATE/DELETE를 독립적인 owned fixture에서 실행한다. 이전 known failure 때문에 다른 필수 workload가 미실행되지 않게 한다.
- [ ] 각 단계의 정확한 생존 행과 전체 값을 독립 모델로 검사한다. 오래된 reader·abort·rollback-after-vacuum 동안 필요한 이전 버전도 보호되는지 확인한다.
- [ ] 트랜잭션 완료·reader release·확인 가능한 vacuum 진행을 완료 조건으로 사용한다. 고정 sleep만으로 eventual return을 판정하지 않는다.
- [ ] chunk 삭제와 반환 자격이 있는 빈 page의 반환을 별도로 검증한다. 값 보존 또는 chunk 감소만으로 page-return 성공을 주장하지 않는다.
- [ ] 안전한 reclaim과 재사용이 불필요한 sector 성장보다 먼저 이루어지는지 확인한다. 적용 가능한 restart·lost-hint·abort/retry 경로를 독립 실행한다.
- [ ] 동일한 live data 시점에서 OOS page/chunk, heap, index 및 volume 관측을 분리한다. 동등한 fresh heap과 공간 추세를 비교한다.
- [ ] aggregate unused bytes는 slack 지표로 기술한다. 완전 packing·across-page compaction·OS volume-file shrink를 완료 조건으로 추가하지 않는다.
- [ ] 결정적인 내부 eligibility·hint-loss assertion은 15와 공유하고, 관련 C++ 중복 판정은 해당 계약의 검증된 대체 근거로만 수행한다.
- [ ] bounded timeout, attempt-owned 자원과 안전한 정리를 유지하며 native 결과를 기록한다. FAIL·timeout·미실행 후속 단계를 각각 구분하고 benchmark 통과 주장은 만들지 않는다.

## Evidence and handoff

전체 값·상태에 대한 독립 oracle, 정확한 환경 식별자, selected/executed case와 verdict artifact, 관련 C++ disposition 및 다음 티켓이 재사용할 fixture·제약을 남긴다.
필수 실행의 공백은 해결 전까지 완료 조건을 충족하지 않는다. 재현된 엔진 FAIL은 별도 수정에 연결하고 passing coverage에서 제외한다.

## Comments

2026-10-21: 사용자가 승인한 16개 티켓 중 하나로 게시했다. 구현과 테스트 실행은 시작하지 않았다.
