# 06: 기본 DML·트리거·트랜잭션과 HAS_OOS 상태 전환

**What to build:** INSERT/UPDATE/DELETE와 트리거 쓰기의 두 레코드 상태·전환, 다중 행, commit/rollback/savepoint 및 실패 원자성 검증.

**Blocked by:** [01: 기준 리비전·커버리지 확정과 HAS_OOS 관측 tracer](01-baseline-and-record-observer.md)

**Status:** ready-for-agent

기준일: 2026-10-21, Asia/Seoul. 기존 work: Work458, Work459. Spec user stories: 6, 7, 18, 20, 22, 38, 43.

실행 전 [지도와 공통 완료 규칙](../map.md)을 읽는다. 현행 권한·자원 격리·native 검증 규칙은 모든 사례에 적용한다.

## Acceptance criteria

- [ ] INSERT 결과, UPDATE의 적용 가능한 set→set·set→clear·clear→set·clear→clear 전환과 DELETE의 행 부재를 개별 저장 플래그에 연결한다.
- [ ] 단일·다중 행 쓰기와 적용 가능한 트리거 쓰기에 독립적인 전체 값 모델을 사용한다. 트리거가 변경한 대상 행도 관측한다.
- [ ] 기본 제약의 허용·거부 동작을 확인하고, 제약·트리거 실패 후 문장 원자성과 이전 데이터·소유권의 보존을 검사한다.
- [ ] commit, rollback 및 savepoint 복구 뒤의 값·존재·OOS 상태를 실행으로 검증한다.
- [ ] 즉시 rollback과 vacuum 이후 rollback을 구분한다. 후자의 필수 실행은 13의 수명·회수 사례에 연결하며 즉시 rollback 결과로 대체하지 않는다.
- [ ] SA의 eager cleanup과 CS의 가시성·회수 계약이 다르면 각각의 의미 있는 assertion을 유지한다.
- [ ] native SQL/shell 결과, 관련 내부 C++ 보완 및 중복 판정을 함께 기록한다. 삭제는 검증된 동일 계약의 대체 증거가 있을 때만 수행한다.

## Evidence and handoff

전체 값·상태에 대한 독립 oracle, 정확한 환경 식별자, selected/executed case와 verdict artifact, 관련 C++ disposition 및 다음 티켓이 재사용할 fixture·제약을 남긴다.
필수 실행의 공백은 해결 전까지 완료 조건을 충족하지 않는다. 재현된 엔진 FAIL은 별도 수정에 연결하고 passing coverage에서 제외한다.

## Comments

2026-10-21: 사용자가 승인한 16개 티켓 중 하나로 게시했다. 구현과 테스트 실행은 시작하지 않았다.
