# 10: 큰 OOS 키의 FK·cascade와 제약 실패 처리

**What to build:** 검증된 큰 키 조합에서 일반 FK 및 cascade, 제약 실패의 값·상태·원자성 검증.

**Blocked by:** [09: 큰 OOS PK·UNIQUE 기능](09-large-oos-pk-unique.md)

**Status:** ready-for-agent

기준일: 2026-10-21, Asia/Seoul. 기존 work: Work458, Work459. Spec user stories: 20, 22, 38, 53, 54.

실행 전 [지도와 공통 완료 규칙](../map.md)을 읽는다. 현행 권한·자원 격리·native 검증 규칙은 모든 사례에 적용한다.

## Acceptance criteria

- [ ] 09에서 검증한 지원 referenced-key fixture를 사용하여 일반 단일 노드 FK와 적용 가능한 cascade 동작을 구성한다.
- [ ] 참조 생성·부모/자식 변경·삭제·거부 조합마다 전체 값과 관계 무결성을 독립 모델로 확인한다.
- [ ] 영향받는 부모·자식 행의 필요한 HAS_OOS 상태와 상태 전환을 관측한다.
- [ ] FK/cascade 실패, 다중 행 및 rollback 뒤의 원자성·이전 값·OOS 소유권 보존을 검증한다.
- [ ] 지원 기능을 도달·관측할 수 없으면 해당 required case를 capability gap으로 남긴다. 이를 적용 불가나 암묵적 제외로 바꾸지 않는다.
- [ ] native SQL/shell 실행과 관련 C++ assertion·대체 근거를 기록한다. HA·복제·failover 시나리오는 보류된 Work463에 유지한다.

## Evidence and handoff

전체 값·상태에 대한 독립 oracle, 정확한 환경 식별자, selected/executed case와 verdict artifact, 관련 C++ disposition 및 다음 티켓이 재사용할 fixture·제약을 남긴다.
필수 실행의 공백은 해결 전까지 완료 조건을 충족하지 않는다. 재현된 엔진 FAIL은 별도 수정에 연결하고 passing coverage에서 제외한다.

## Comments

2026-10-21: 사용자가 승인한 16개 티켓 중 하나로 게시했다. 구현과 테스트 실행은 시작하지 않았다.
