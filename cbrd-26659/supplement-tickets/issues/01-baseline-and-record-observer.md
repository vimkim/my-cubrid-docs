# 01: 기준 리비전·커버리지 확정과 HAS_OOS 관측 tracer

**What to build:** 일치하는 실행 환경, 전체 연산/기존 테스트 목록, HAS_OOS set/clear 혼합 레코드의 실제 관측 및 native verdict를 확인한 최소 회귀 사례.

**Blocked by:** None (can start immediately)

**Status:** ready-for-agent

기준일: 2026-10-21, Asia/Seoul. 기존 work: Work458, Work459. Spec user stories: 1, 2, 3, 4, 5, 6, 7, 8, 26, 55, 57.

실행 전 [지도와 공통 완료 규칙](../map.md)을 읽는다. 현행 권한·자원 격리·native 검증 규칙은 모든 사례에 적용한다.

## Acceptance criteria

- [ ] 구현 시작 시 source, 설치 산출물, 공개·비공개 TC, 의존성, runner, 설정과 작업 트리 변경의 정확한 식별자를 기록한다. handover·SA-loaddb·deferred-write 결과는 각각의 리비전으로 유지한다.
- [ ] Work109·Work401의 기존 요구사항, SQL/shell 사례 및 관련 C++ 전체 목록을 재사용하여 연산 모집단을 확정한다. 선언된 C++ 사례 수와 실제 실행 결과를 구분한다.
- [ ] 연산마다 지원 근거, 독립적인 기대 동작, 적용 가능한 입력·출력 HAS_OOS 상태와 전환, 기존 assertion, 증거, 남은 의무를 기록한다. 적용 불가인 조합에는 이유를 남긴다.
- [ ] 읽기, 기본·대체 쓰기, 제약·트리거, 집합 연산, 스키마·파티션, 유틸리티, 경계, 저장 공간, 큰 키 경로를 빠짐없이 후속 티켓에 배정한다. 크기는 HAS_OOS 분류의 대용으로 사용하지 않는다.
- [ ] 동일 heap에 HAS_OOS record와 Record without HAS_OOS를 함께 두고, 저장된 형태의 실제 플래그를 관측한다. 논리 행, 물리 슬롯, 레코드 타입 및 트랜잭션 가시성의 관계를 검증한다.
- [ ] Expand 후 복사본, 다른 fixture 또는 테이블 합계만으로 개별 행의 상태를 판정하지 않는다. DELETE 후 행 부재는 clear 상태와 구분한다.
- [ ] 최소 혼합 레코드 회귀 사례를 유지되는 native 경로로 실행하여 전체 값과 실제 상태를 검증하고, 선택 사례와 verdict artifact를 대조한다.
- [ ] 일회성 잘못된 기대값을 사용하여 중요한 판정기가 오류를 탐지함을 확인한다. 이 negative control은 정식 expected answer와 분리한다.
- [ ] 관측이나 환경의 필수 의무를 충족하지 못하면 capability/delivery/specification gap을 명시한다. 통과하지 못한 관측 경로에 의존하는 후속 티켓은 시작하지 않는다.

## Evidence and handoff

전체 값·상태에 대한 독립 oracle, 정확한 환경 식별자, selected/executed case와 verdict artifact, 관련 C++ disposition 및 다음 티켓이 재사용할 fixture·제약을 남긴다.
필수 실행의 공백은 해결 전까지 완료 조건을 충족하지 않는다. 재현된 엔진 FAIL은 별도 수정에 연결하고 passing coverage에서 제외한다.

## Comments

2026-10-21: 사용자가 승인한 16개 티켓 중 하나로 게시했다. 구현과 테스트 실행은 시작하지 않았다.
