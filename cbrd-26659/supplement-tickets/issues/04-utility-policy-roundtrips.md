# 04: 정책·값·소유권의 유틸리티 왕복

**What to build:** unload/load·compact 등 해당 유틸리티의 SA/CS 왕복 후 정책, 전체 값, 실제 레코드 상태와 목적지 소유권 확인.

**Blocked by:** [01: 기준 리비전·커버리지 확정과 HAS_OOS 관측 tracer](01-baseline-and-record-observer.md)

**Status:** ready-for-agent

기준일: 2026-10-21, Asia/Seoul. 기존 work: Work457, Work458, Work459. Spec user stories: 8, 13, 15, 25, 31.

실행 전 [지도와 공통 완료 규칙](../map.md)을 읽는다. 현행 권한·자원 격리·native 검증 규칙은 모든 사례에 적용한다.

## Acceptance criteria

- [ ] 01 목록의 unload/load·compact 및 다른 적용 가능한 유틸리티 의무를 기존 사례와 대조한다. 충분한 backup/LOB 증거는 원래 리비전과 범위 안에서 재사용한다.
- [ ] 왕복 전후의 정책 기본값·명시값·생략값과 관련 스키마 메타데이터를 승인된 계약에 따라 확인한다.
- [ ] 구별 가능한 전체 값과 생존 행 모델을 비교하고, 필요한 개별 HAS_OOS 상태와 실제 목적지 heap의 소유권을 증명한다.
- [ ] SA와 CS의 필요한 왕복을 독립 fixture로 실행한다. 알려진 SA 물리 실패가 CS나 다른 필수 유틸리티 실행을 막지 않게 한다.
- [ ] 값이 읽히는 결과, OOS 소유권, 외부 LOB payload 수명을 구분한다. companion fixture가 실제 왕복 실행을 대신 증명하지 않게 한다.
- [ ] 실패한 유틸리티의 부분 변경·오류 처리·정리와 관련 내부 buffer/ownership 계약을 보존한다. 재현된 엔진 결함은 올바른 FAIL로 남긴다.
- [ ] native shell/SQL 실행의 입력·출력·선택 사례·verdict를 기록하고, 관련 C++ 유지·이관·삭제 판정에 검증된 대체 근거를 연결한다.

## Evidence and handoff

전체 값·상태에 대한 독립 oracle, 정확한 환경 식별자, selected/executed case와 verdict artifact, 관련 C++ disposition 및 다음 티켓이 재사용할 fixture·제약을 남긴다.
필수 실행의 공백은 해결 전까지 완료 조건을 충족하지 않는다. 재현된 엔진 FAIL은 별도 수정에 연결하고 passing coverage에서 제외한다.

## Comments

2026-10-21: 사용자가 승인한 16개 티켓 중 하나로 게시했다. 구현과 테스트 실행은 시작하지 않았다.
