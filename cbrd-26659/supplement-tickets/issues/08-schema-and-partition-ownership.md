# 08: 스키마 재작성·파티션 목적지 소유권

**What to build:** 컬럼/타입/default 등 재작성과 적용 가능한 파티션 동작 후 값·정책·HAS_OOS 상태·실제 owning heap 검증.

**Blocked by:** [01: 기준 리비전·커버리지 확정과 HAS_OOS 관측 tracer](01-baseline-and-record-observer.md)

**Status:** ready-for-agent

기준일: 2026-10-21, Asia/Seoul. 기존 work: Work458, Work459. Spec user stories: 12, 13, 23, 24, 31, 55.

실행 전 [지도와 공통 완료 규칙](../map.md)을 읽는다. 현행 권한·자원 격리·native 검증 규칙은 모든 사례에 적용한다.

## Acceptance criteria

- [ ] 컬럼 추가·제거·순서·타입·default 등 01에서 식별한 지원 스키마 재작성의 기존 사례를 대조하고 빠진 계약을 보완한다.
- [ ] 성공과 거부 뒤의 전체 생존 값, 정책 및 관련 메타데이터를 확인한다. 정책 복사·초기화 계약은 02와 같은 승인 근거를 사용한다.
- [ ] 적용 가능한 파티션 생성·변경·행 이동에서 입력 root와 실제 destination heap을 구분하여 물리 소유권 및 HAS_OOS 상태를 확인한다.
- [ ] SA prepared-row의 승인된 값·의미 있는 header/CHN·정책·소유권·트랜잭션·buffer 수명 계약을 유지한다. superseded padding byte 동일성을 다시 요구하지 않는다.
- [ ] handover·SA-loaddb·deferred-write의 정확한 별도 리비전을 기록한다. 실제 통합과 재검증 없이 다른 브랜치의 성공을 현재 기준에 합산하지 않는다.
- [ ] 현재 partition-owner 및 SA 물리 회귀의 올바른 실패 기대를 유지하고 재현 증거·별도 수정 링크를 기록한다. 이 티켓에서 엔진 수정을 합치지 않는다.
- [ ] 필수 native 실행과 관련 C++ assertion·중복 판정을 함께 남긴다.

## Evidence and handoff

전체 값·상태에 대한 독립 oracle, 정확한 환경 식별자, selected/executed case와 verdict artifact, 관련 C++ disposition 및 다음 티켓이 재사용할 fixture·제약을 남긴다.
필수 실행의 공백은 해결 전까지 완료 조건을 충족하지 않는다. 재현된 엔진 FAIL은 별도 수정에 연결하고 passing coverage에서 제외한다.

## Comments

2026-10-21: 사용자가 승인한 16개 티켓 중 하나로 게시했다. 구현과 테스트 실행은 시작하지 않았다.
