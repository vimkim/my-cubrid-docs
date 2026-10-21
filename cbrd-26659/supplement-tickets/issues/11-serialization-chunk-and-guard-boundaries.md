# 11: 직렬화 floor·청크·VOT·길이 guard 경계

**What to build:** 바이트/직렬화 단위를 명시한 limit/+1 또는 다음 표현 가능 값, 내부 길이·쓰기 범위 guard와 오류 처리.

**Blocked by:** [01: 기준 리비전·커버리지 확정과 HAS_OOS 관측 tracer](01-baseline-and-record-observer.md)

**Status:** ready-for-agent

기준일: 2026-10-21, Asia/Seoul. 기존 work: Work460, Work459, Work458. Spec user stories: 28, 33, 34, 36, 37, 40.

실행 전 [지도와 공통 완료 규칙](../map.md)을 읽는다. 현행 권한·자원 격리·native 검증 규칙은 모든 사례에 적용한다.

## Acceptance criteria

- [ ] 도입된 floor·profitability·chunk·VOT/offset-width·길이 guard 한계의 단위와 독립적인 기대 근거를 01 목록에 정리한다.
- [ ] 가능한 곳은 정확한 limit와 limit+1을 실행한다. 정렬로 +1을 표현할 수 없으면 바로 다음 표현 가능한 직렬화 크기와 그 이유를 적는다.
- [ ] 입력 값 길이, helper가 더한 terminator, 직렬화 길이, chunk/record 수용량을 구분한다. 기존 정확한 경계 사례가 충분하면 재사용한다.
- [ ] 허용 경계에서 전체 값과 실제 저장 경로를 검증하고, 거부 또는 표현 전환에서는 승인된 오류/전환과 이전 상태 보존을 확인한다.
- [ ] VOT/offset 및 내부 쓰기 범위·길이 오류는 해당 module contract와 결정적 fault/bounds seam으로 검증한다.
- [ ] 실제 저장이 비현실적인 최대값의 C++ guard 검증은 guard-only로 명시한다. 실제 최대 크기 저장 성공으로 합산하지 않는다.
- [ ] 필수 native SQL/shell/C++ 선택과 verdict를 대조하고, 관련 기존 사례의 retain/add/migrate/remove 근거를 남긴다.

## Evidence and handoff

전체 값·상태에 대한 독립 oracle, 정확한 환경 식별자, selected/executed case와 verdict artifact, 관련 C++ disposition 및 다음 티켓이 재사용할 fixture·제약을 남긴다.
필수 실행의 공백은 해결 전까지 완료 조건을 충족하지 않는다. 재현된 엔진 FAIL은 별도 수정에 연결하고 passing coverage에서 제외한다.

## Comments

2026-10-21: 사용자가 승인한 16개 티켓 중 하나로 게시했다. 구현과 테스트 실행은 시작하지 않았다.
