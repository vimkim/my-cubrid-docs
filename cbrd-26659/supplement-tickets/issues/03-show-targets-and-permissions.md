# 03: SHOW 대상·인자·권한·관측 결과

**What to build:** HAS_OOS 유무에 따른 SHOW 결과, 잘못된 대상·인자, DBA/일반 사용자 및 적용 가능한 ALL/filter 의미의 검증.

**Blocked by:** [01: 기준 리비전·커버리지 확정과 HAS_OOS 관측 tracer](01-baseline-and-record-observer.md)

**Status:** ready-for-agent

기준일: 2026-10-21, Asia/Seoul. 기존 work: Work457, Work458, Work459. Spec user stories: 3, 8, 14.

실행 전 [지도와 공통 완료 규칙](../map.md)을 읽는다. 현행 권한·자원 격리·native 검증 규칙은 모든 사례에 적용한다.

## Acceptance criteria

- [ ] 01 목록에 있는 OOS 관련 SHOW 종류마다 유효한 대상과 인자, 잘못된 대상·타입·인자를 대조한다. 적용 가능한 ALL/filter 및 계층·파티션 대상의 의미를 확정한다.
- [ ] DBA와 일반 사용자의 허용·거부 결과를 승인된 권한 계약에 따라 실행한다. 지원되지 않는 조합과 검증하지 않은 조합을 구분한다.
- [ ] 혼합 레코드 heap에서 개별 저장 플래그와 SHOW 합계를 별도로 수집하고 각각의 주장 범위를 적는다.
- [ ] 정확한 통계 비교는 쓰기와 회수가 안정된 fixture에서 수행한다. 변동 가능한 관측은 고정 수치의 성공 증거로 사용하지 않는다.
- [ ] 오류·권한 거부 뒤에도 데이터와 메타데이터가 보존됨을 확인하고 native verdict artifact를 남긴다.
- [ ] 기존 SA 전용 동작과 내부 관측 assertion의 의미를 유지한다. SQL 결과가 같다는 이유만으로 C++ 사례를 삭제하지 않는다.

## Evidence and handoff

전체 값·상태에 대한 독립 oracle, 정확한 환경 식별자, selected/executed case와 verdict artifact, 관련 C++ disposition 및 다음 티켓이 재사용할 fixture·제약을 남긴다.
필수 실행의 공백은 해결 전까지 완료 조건을 충족하지 않는다. 재현된 엔진 FAIL은 별도 수정에 연결하고 passing coverage에서 제외한다.

## Comments

2026-10-21: 사용자가 승인한 16개 티켓 중 하나로 게시했다. 구현과 테스트 실행은 시작하지 않았다.
