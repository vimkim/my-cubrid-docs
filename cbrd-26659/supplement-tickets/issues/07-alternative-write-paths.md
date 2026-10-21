# 07: MERGE·REPLACE·중복 키 UPDATE

**What to build:** 대체 쓰기 경로마다 HAS_OOS 유무, 전환, 충돌·실패 후 모델 보존을 실행으로 확인.

**Blocked by:** [01: 기준 리비전·커버리지 확정과 HAS_OOS 관측 tracer](01-baseline-and-record-observer.md)

**Status:** ready-for-agent

기준일: 2026-10-21, Asia/Seoul. 기존 work: Work458, Work459. Spec user stories: 6, 19, 22, 38.

실행 전 [지도와 공통 완료 규칙](../map.md)을 읽는다. 현행 권한·자원 격리·native 검증 규칙은 모든 사례에 적용한다.

## Acceptance criteria

- [ ] MERGE, REPLACE, duplicate-key UPDATE 각각의 실제 지원 범위와 승인된 정상·충돌·오류 기대를 01 목록에 명시한다.
- [ ] 각 경로의 적용 가능한 HAS_OOS 입력·출력 상태와 UPDATE 전환을 독립적으로 실행한다. 일반 UPDATE의 성공만으로 이 경로들을 완료 처리하지 않는다.
- [ ] 신규·기존 키, 다중 행 및 관련 분기에서 구별 가능한 전체 값과 생존 행 모델을 검증한다.
- [ ] 중복·제약·크기 오류 뒤의 문장 원자성, 이전 값, 관련 정책·OOS 소유권을 확인한다.
- [ ] commit·rollback·savepoint가 적용되는 경로는 해당 동작을 실행한다. 선언된 미지원과 미실행 의무를 별도 disposition으로 남긴다.
- [ ] native SQL/shell 증거와 관련 C++ retain/add/migrate/remove 판정을 연결한다. 올바른 엔진 실패를 passing selection에서 숨기지 않는다.

## Evidence and handoff

전체 값·상태에 대한 독립 oracle, 정확한 환경 식별자, selected/executed case와 verdict artifact, 관련 C++ disposition 및 다음 티켓이 재사용할 fixture·제약을 남긴다.
필수 실행의 공백은 해결 전까지 완료 조건을 충족하지 않는다. 재현된 엔진 FAIL은 별도 수정에 연결하고 passing coverage에서 제외한다.

## Comments

2026-10-21: 사용자가 승인한 16개 티켓 중 하나로 게시했다. 구현과 테스트 실행은 시작하지 않았다.
