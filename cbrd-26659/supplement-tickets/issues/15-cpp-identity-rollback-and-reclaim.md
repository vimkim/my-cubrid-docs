# 15: C++ identity·소유권·rollback·reclaim 증명 보완

**What to build:** 동일성 검사, 해제 자격, undo/borrowed 참조, abort·재시도·힌트 유실 등 내부 계약의 실행 증거.

**Blocked by:** [01: 기준 리비전·커버리지 확정과 HAS_OOS 관측 tracer](01-baseline-and-record-observer.md)

**Status:** ready-for-agent

기준일: 2026-10-21, Asia/Seoul. 기존 work: Work459, Work461, Work458. Spec user stories: 26, 28, 29, 31, 32, 44, 45, 46, 48.

실행 전 [지도와 공통 완료 규칙](../map.md)을 읽는다. 현행 권한·자원 격리·native 검증 규칙은 모든 사례에 적용한다.

## Acceptance criteria

- [ ] 01의 전체 C++ 목록에서 chain identity와 reclaim eligibility를 별개 계약으로 매핑한다. identity 일치만으로 삭제 자격을 증명하지 않는다.
- [ ] 소유권 이전, undo·borrowed 참조, rollback·abort, retry 및 적용 가능한 lost-hint/reclaim 계약을 기존 결정적 seam으로 검증한다.
- [ ] SA/CS의 서로 다른 정리·가시성 계약과 승인된 prepared-row 의미를 유지한다. 기존 정확한 oracle을 실제 defective output에 맞추지 않는다.
- [ ] 필요한 reader·트랜잭션·회수 완료 조건을 assertion에 연결하고, 13의 외부 수명·공간 시나리오와 중복되는 주장 범위를 명시한다.
- [ ] 충분한 기존 사례를 유지하고 실제 공백만 보완한다. production reclaim/ownership 동작의 별도 수정은 이 테스트 티켓에 합치지 않는다.
- [ ] 필수 native C++ 선택·등록·실행 identity·verdict를 대조한다. 필수 사례의 미실행을 gap으로 유지한다.
- [ ] 삭제·이관 후보는 검증된 대체 계약과 실행 모드의 근거를 남기고, 최종 전체 disposition audit를 16에 전달한다.

## Evidence and handoff

전체 값·상태에 대한 독립 oracle, 정확한 환경 식별자, selected/executed case와 verdict artifact, 관련 C++ disposition 및 다음 티켓이 재사용할 fixture·제약을 남긴다.
필수 실행의 공백은 해결 전까지 완료 조건을 충족하지 않는다. 재현된 엔진 FAIL은 별도 수정에 연결하고 passing coverage에서 제외한다.

## Comments

2026-10-21: 사용자가 승인한 16개 티켓 중 하나로 게시했다. 구현과 테스트 실행은 시작하지 않았다.
