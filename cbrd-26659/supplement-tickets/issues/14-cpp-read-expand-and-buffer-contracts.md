# 14: C++ 읽기·Expand·버퍼·dispatch 증명 보완

**What to build:** 외부 SQL만으로 증명할 수 없는 stored/expanded fetch, batching, 버퍼 수명 및 해당 오류 경로의 보완·실행 증거.

**Blocked by:** [01: 기준 리비전·커버리지 확정과 HAS_OOS 관측 tracer](01-baseline-and-record-observer.md)

**Status:** ready-for-agent

기준일: 2026-10-21, Asia/Seoul. 기존 work: Work459, Work458. Spec user stories: 3, 4, 5, 26, 27, 28, 31, 32.

실행 전 [지도와 공통 완료 규칙](../map.md)을 읽는다. 현행 권한·자원 격리·native 검증 규칙은 모든 사례에 적용한다.

## Acceptance criteria

- [ ] 01의 전체 C++ 목록에서 stored/expanded fetch, read_many·batching, dispatch, buffer ownership/lifetime 및 관련 오류 계약을 assertion 단위로 대조한다.
- [ ] SQL에서 같은 값이 나오는 사례와 내부 호출 경로·batch 수·Expand 회피를 직접 증명하는 사례를 구분한다.
- [ ] 충분한 기존 사례를 유지하고 식별된 공백에만 결정적인 사례를 보완한다. 새 production 관측 API를 전제로 삼지 않는다.
- [ ] 저장된 형태를 확인하는 시점과 materialization 뒤 형태를 구분하며, 필요한 내부 bounds/fault 처리도 계약 근거에 따라 실행한다.
- [ ] 유지·신규·이관 사례의 등록 identity와 실제 native C++ 실행 identity·verdict를 대조한다. 목록의 사례 수를 PASS로 보고하지 않는다.
- [ ] 외부 동등성에 따른 삭제 후보는 담당 동작 티켓과 조율하고 검증된 대체 assertion·모드·실행 근거를 기록한다.

## Evidence and handoff

전체 값·상태에 대한 독립 oracle, 정확한 환경 식별자, selected/executed case와 verdict artifact, 관련 C++ disposition 및 다음 티켓이 재사용할 fixture·제약을 남긴다.
필수 실행의 공백은 해결 전까지 완료 조건을 충족하지 않는다. 재현된 엔진 FAIL은 별도 수정에 연결하고 passing coverage에서 제외한다.

## Comments

2026-10-21: 사용자가 승인한 16개 티켓 중 하나로 게시했다. 구현과 테스트 실행은 시작하지 않았다.
