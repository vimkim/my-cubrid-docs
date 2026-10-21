# 09: 큰 OOS PK·UNIQUE 기능

**What to build:** 키 속성 자체의 OOS 저장을 입증하고 인덱스 생성·구축·조회·변경·삭제와 중복/NULL/rollback 동작 확인.

**Blocked by:** [01: 기준 리비전·커버리지 확정과 HAS_OOS 관측 tracer](01-baseline-and-record-observer.md)

**Status:** ready-for-agent

기준일: 2026-10-21, Asia/Seoul. 기존 work: Work462, Work458, Work459. Spec user stories: 39, 50, 51, 52, 53, 54.

실행 전 [지도와 공통 완료 규칙](../map.md)을 읽는다. 현행 권한·자원 격리·native 검증 규칙은 모든 사례에 적용한다.

## Acceptance criteria

- [ ] 지원되는 키 도메인·정책·조합의 근거와 거부 조합을 기록한다. 인접 payload나 B-tree overflow 대신 인덱스 대상 속성 자체가 OOS-backed임을 증명한다.
- [ ] PK와 UNIQUE를 데이터 적재 전 생성하는 유지 경로와 적재 후 생성하는 build 경로에서 각각 검증한다.
- [ ] 적용 가능한 전체 키 lookup·정렬·범위 조회와 INSERT/UPDATE/DELETE를 구별 가능한 전체 키 값으로 검사한다.
- [ ] 중복 키, PK/UNIQUE의 해당 NULL 규칙, 실패 원자성 및 rollback 뒤의 값·키·소유권 보존을 검사한다.
- [ ] 일반 FK 후속 검증에 사용할 유효한 referenced-key fixture와 지원 근거를 10에 전달한다. 필수 조합이 불가능하면 gap을 남긴다.
- [ ] 관련 native SQL/shell 및 필요한 C++ 실행의 증거와 중복 판정을 남긴다. heap OOS 저장과 B-tree 표현 전환의 근거를 구분한다.
- [ ] 결론은 기능 동작으로 한정한다. 성능 baseline·throughput·latency·회귀 임계값의 통과 주장을 만들지 않는다.

## Evidence and handoff

전체 값·상태에 대한 독립 oracle, 정확한 환경 식별자, selected/executed case와 verdict artifact, 관련 C++ disposition 및 다음 티켓이 재사용할 fixture·제약을 남긴다.
필수 실행의 공백은 해결 전까지 완료 조건을 충족하지 않는다. 재현된 엔진 FAIL은 별도 수정에 연결하고 passing coverage에서 제외한다.

## Comments

2026-10-21: 사용자가 승인한 16개 티켓 중 하나로 게시했다. 구현과 테스트 실행은 시작하지 않았다.
