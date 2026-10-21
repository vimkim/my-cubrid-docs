# 05: 읽기·복사·집합 연산과 LOB 값 보존

**What to build:** heap/index 읽기, join·정렬·집계·집합 연산, 복사와 원본 제거 후 전체 값 및 적용 가능한 OOS 상태 검증.

**Blocked by:** [01: 기준 리비전·커버리지 확정과 HAS_OOS 관측 tracer](01-baseline-and-record-observer.md)

**Status:** ready-for-agent

기준일: 2026-10-21, Asia/Seoul. 기존 work: Work458, Work459. Spec user stories: 8, 17, 18, 21, 25.

실행 전 [지도와 공통 완료 규칙](../map.md)을 읽는다. 현행 권한·자원 격리·native 검증 규칙은 모든 사례에 적용한다.

## Acceptance criteria

- [ ] heap 및 index 읽기, join, 정렬·집계와 지원되는 집합 연산을 01 목록의 모든 적용 가능한 레코드 상태에 대조한다.
- [ ] 구별 가능한 전체 값과 독립적인 기대 결과로 비교·중복 제거·순서 의미를 검증한다. 길이·개수만으로 정확성을 판정하지 않는다.
- [ ] 복사·다중 행 전송 후 목적지의 값과 필요한 HAS_OOS 상태를 확인한다. 원본을 제거한 뒤에도 목적지의 값과 소유권이 유효함을 확인한다.
- [ ] LOB locator를 담는 레코드와 외부 LOB payload의 저장·수명을 구분하여 실제로 실행한 계약만 주장한다.
- [ ] 오류 및 트랜잭션 경계가 해당하는 읽기·복사 경로에서는 이전 데이터와 목적지 상태의 보존을 확인한다.
- [ ] 필수 SQL/native shell 사례를 실행하고 실제 invocation의 논리 결과와 물리 증거를 연결한다.
- [ ] 내부 dispatch·batching·Expand 회피 assertion은 14와 연계하여 유지한다. 외부 동등성을 실제로 증명한 C++ 중복만 이관·삭제한다.

## Evidence and handoff

전체 값·상태에 대한 독립 oracle, 정확한 환경 식별자, selected/executed case와 verdict artifact, 관련 C++ disposition 및 다음 티켓이 재사용할 fixture·제약을 남긴다.
필수 실행의 공백은 해결 전까지 완료 조건을 충족하지 않는다. 재현된 엔진 FAIL은 별도 수정에 연결하고 passing coverage에서 제외한다.

## Comments

2026-10-21: 사용자가 승인한 16개 티켓 중 하나로 게시했다. 구현과 테스트 실행은 시작하지 않았다.
