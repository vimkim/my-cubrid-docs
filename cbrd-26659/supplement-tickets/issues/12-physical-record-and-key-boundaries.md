# 12: 물리 target·잔여 record·bigone·키 overflow 경계

**What to build:** 허용/거부 최대 경계와 원자성을 검증하고 accepted physical target 차이 및 B-tree overflow 전환을 구분.

**Blocked by:** [01: 기준 리비전·커버리지 확정과 HAS_OOS 관측 tracer](01-baseline-and-record-observer.md)

**Status:** ready-for-agent

기준일: 2026-10-21, Asia/Seoul. 기존 work: Work460, Work459, Work458. Spec user stories: 33, 34, 35, 37, 38, 39.

실행 전 [지도와 공통 완료 규칙](../map.md)을 읽는다. 현행 권한·자원 격리·native 검증 규칙은 모든 사례에 적용한다.

## Acceptance criteria

- [ ] 승인된 physical demotion target, 여러 stub 뒤 잔여 record, bigone 및 key-overflow 경계의 단위·공식을 요구사항별로 명시한다.
- [ ] 가능한 정확한 최대 허용값과 다음 거부값을 실행한다. 넓은 간격의 성공/실패 대조만으로 최대값/+1을 완료 처리하지 않는다.
- [ ] physical target의 현재 구현과 승인 기대가 다르면 승인된 oracle의 FAIL을 유지하고 정확한 리비전·재현·수정 링크를 기록한다.
- [ ] 여러 stub·offset·잔여 record와 bigone 전환에서 전체 값, 실제 HAS_OOS 상태와 물리 표현의 근거를 확인한다.
- [ ] B-tree in-page 한계 뒤의 overflow 전환과 hard rejection을 구분한다. 관련 큰 키 fixture는 heap OOS 여부를 별도로 증명한다.
- [ ] 거부된 oversized write 뒤 이전 값·메타데이터·소유권 및 orphan chain 여부를 확인한다. 오류 기대는 해당 리비전의 승인된 오류 identity를 사용한다.
- [ ] 필수 native SQL/shell/C++ 실행 및 중복 판정을 남긴다. 이 티켓은 엔진 threshold나 production 경로를 수정하지 않는다.

## Evidence and handoff

전체 값·상태에 대한 독립 oracle, 정확한 환경 식별자, selected/executed case와 verdict artifact, 관련 C++ disposition 및 다음 티켓이 재사용할 fixture·제약을 남긴다.
필수 실행의 공백은 해결 전까지 완료 조건을 충족하지 않는다. 재현된 엔진 FAIL은 별도 수정에 연결하고 passing coverage에서 제외한다.

## Comments

2026-10-21: 사용자가 승인한 16개 티켓 중 하나로 게시했다. 구현과 테스트 실행은 시작하지 않았다.
