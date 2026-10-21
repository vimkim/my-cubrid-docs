# 16: 전체 커버리지 대조·최종 native 검증·CI 전달

**What to build:** 전 요구사항·기존 C++ 유지/삭제·실행 artifact를 대조하고, 단일 기준의 최종 검증 및 허용된 게시 후 CI 1회 결과 보고.

**Blocked by:** [02: 스토리지 정책 문법·의미·DDL 오류 보존](02-policy-syntax-and-semantics.md), [03: SHOW 대상·인자·권한·관측 결과](03-show-targets-and-permissions.md), [04: 정책·값·소유권의 유틸리티 왕복](04-utility-policy-roundtrips.md), [05: 읽기·복사·집합 연산과 LOB 값 보존](05-reads-copies-and-set-operations.md), [06: 기본 DML·트리거·트랜잭션과 HAS_OOS 상태 전환](06-dml-triggers-and-transactions.md), [07: MERGE·REPLACE·중복 키 UPDATE](07-alternative-write-paths.md), [08: 스키마 재작성·파티션 목적지 소유권](08-schema-and-partition-ownership.md), [09: 큰 OOS PK·UNIQUE 기능](09-large-oos-pk-unique.md), [10: 큰 OOS 키의 FK·cascade와 제약 실패 처리](10-large-key-fk-and-cascade.md), [11: 직렬화 floor·청크·VOT·길이 guard 경계](11-serialization-chunk-and-guard-boundaries.md), [12: 물리 target·잔여 record·bigone·키 overflow 경계](12-physical-record-and-key-boundaries.md), [13: 반복 쓰기·회수·재사용·단편화 추세](13-churn-reclaim-reuse-and-fragmentation.md), [14: C++ 읽기·Expand·버퍼·dispatch 증명 보완](14-cpp-read-expand-and-buffer-contracts.md), [15: C++ identity·소유권·rollback·reclaim 증명 보완](15-cpp-identity-rollback-and-reclaim.md)

**Status:** ready-for-agent

기준일: 2026-10-21, Asia/Seoul. 기존 work: Work456, Work457, Work458, Work459, Work460, Work461, Work462. Spec user stories: 1, 2, 8, 26, 30, 32, 49, 55, 56, 57, 58, 59, 60.

실행 전 [지도와 공통 완료 규칙](../map.md)을 읽는다. 현행 권한·자원 격리·native 검증 규칙은 모든 사례에 적용한다.

## Acceptance criteria

- [ ] 02–15의 산출물과 01 목록을 대조하여 승인 spec의 60개 user story 및 기존 Work457–462의 모든 required cell을 요구사항·사례·oracle·실행 증거로 연결한다.
- [ ] 전체 관련 C++ 사례에 retain/add/migrate/remove disposition을 확정한다. 모든 삭제·이관은 검증된 대체 assertion·실행 모드·receipt로 설명된다.
- [ ] 최종 source·설치·의존성·공개/비공개 TC·runner·설정·expected-case identity를 동결한다. 이전 또는 다른 브랜치 receipt가 현재 기준을 대신하지 않게 한다.
- [ ] 필요한 native SQL·shell·C++ 최종 선택을 실행하고 expected/discovered/executed case 및 verdict artifact를 각각 대조한다. 중요한 판정기의 일회성 negative-control 증거도 확인한다.
- [ ] 올바른 oracle로 재현된 엔진 결함은 정확한 scenario·리비전·별도 수정 링크와 FAIL로 유지한다. passing coverage와 테스트 전달·실행 완료를 별도로 집계한다.
- [ ] missing·unexecuted·skip·capability/specification gap과 미해결 attribution을 명시한다. required case의 공백 또는 불명확한 기대가 있으면 Work456을 완료 처리하지 않는다.
- [ ] 완료 보고는 각 milestone의 근거와 한계를 명시하며, 성능 비교 및 HA Work463은 보류 상태로 유지한다.
- [ ] 게시 전에 live PR head repository·headRefName·TC head와 현재 권한·선행 검사 조건을 확인한다. 필요한 TC 변경은 대응 TC PR head에 check·commit·push하고 source 변경이 있을 때는 그 PR head에 게시한다.
- [ ] 허용된 source/TC 게시와 선행 조건을 충족한 뒤 CUBRID CI를 한 번 실행하고 완료까지 기다린다. run URL·결과·TC Merge Gate를 보고한 뒤 사람의 지시를 기다린다.
- [ ] TC 변경이 불필요하면 사람에게 닫을 TC PR을 알린다. TC PR merge·closure와 branch 삭제는 사람이 담당하며, terminal CI 보고 뒤 추가 fix/push/rerun을 자동으로 이어가지 않는다.

## Evidence and handoff

전체 값·상태에 대한 독립 oracle, 정확한 환경 식별자, selected/executed case와 verdict artifact, 관련 C++ disposition 및 다음 티켓이 재사용할 fixture·제약을 남긴다.
필수 실행의 공백은 해결 전까지 완료 조건을 충족하지 않는다. 재현된 엔진 FAIL은 별도 수정에 연결하고 passing coverage에서 제외한다.

## Comments

2026-10-21: 사용자가 승인한 16개 티켓 중 하나로 게시했다. 구현과 테스트 실행은 시작하지 않았다.
