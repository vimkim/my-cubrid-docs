# Work456: 승인된 OOS 보완 티켓 지도

기준일: 2026-10-21, Asia/Seoul. 사용자가 범위·입도·blocking edge를 승인했다.
이 지도는 구현 순서와 완료 조건을 정의한다. 테스트 실행 또는 엔진 통과 보고가 아니다.

현재 16개 티켓은 모두 `ready-for-agent`이다. 이 label은 명세 준비를 뜻한다.
실제 시작 가능 여부는 **Blocked by**로 판단하며 현재 frontier는 **01만**이다.
기존 Work456·458은 active, 다른 milestone은 기존 상태를 유지한다. 티켓 게시만으로 완료된 work는 없다.

## 승인 근거

- [승인된 Work456 spec](../supplement-spec-work456-20261021.md)
- [기존 커버리지와 handover/SA 증거](../supplement-inventory-work456-20261021.md)
- [프로젝트 용어](../../CONTEXT.md)
- [로컬 tracker 규칙](../../docs/agents/issue-tracker.md)

구현 전에 승인 spec 전체와 해당 기존 증거의 리비전 한계를 읽는다.
필요한 동작의 oracle은 spec이 가리키는 승인 OOS 계약·결정에서 도출한다.
관찰된 결함 출력은 새로운 expected answer의 근거가 될 수 없다.

## 개별 티켓과 의존성

번호는 이 effort의 로컬 티켓 번호다. Work456–463 및 CBRD JIRA 번호와 구분한다.
각 파일은 독립적으로 검증 가능한 사례·증거·관련 C++ 판정을 함께 맡는다.

| 티켓 | 직접 선행 티켓 | 재사용하는 work | Spec user stories |
| --- | --- | --- | --- |
| [01: 기준 리비전·커버리지 확정과 HAS_OOS 관측 tracer](issues/01-baseline-and-record-observer.md) | 없음 | #458, #459 | 1, 2, 3, 4, 5, 6, 7, 8, 26, 55, 57 |
| [02: 스토리지 정책 문법·의미·DDL 오류 보존](issues/02-policy-syntax-and-semantics.md) | 01 | #457, #458, #459 | 9, 10, 11, 12, 13, 16 |
| [03: SHOW 대상·인자·권한·관측 결과](issues/03-show-targets-and-permissions.md) | 01 | #457, #458, #459 | 3, 8, 14 |
| [04: 정책·값·소유권의 유틸리티 왕복](issues/04-utility-policy-roundtrips.md) | 01 | #457, #458, #459 | 8, 13, 15, 25, 31 |
| [05: 읽기·복사·집합 연산과 LOB 값 보존](issues/05-reads-copies-and-set-operations.md) | 01 | #458, #459 | 8, 17, 18, 21, 25 |
| [06: 기본 DML·트리거·트랜잭션과 HAS_OOS 상태 전환](issues/06-dml-triggers-and-transactions.md) | 01 | #458, #459 | 6, 7, 18, 20, 22, 38, 43 |
| [07: MERGE·REPLACE·중복 키 UPDATE](issues/07-alternative-write-paths.md) | 01 | #458, #459 | 6, 19, 22, 38 |
| [08: 스키마 재작성·파티션 목적지 소유권](issues/08-schema-and-partition-ownership.md) | 01 | #458, #459 | 12, 13, 23, 24, 31, 55 |
| [09: 큰 OOS PK·UNIQUE 기능](issues/09-large-oos-pk-unique.md) | 01 | #462, #458, #459 | 39, 50, 51, 52, 53, 54 |
| [10: 큰 OOS 키의 FK·cascade와 제약 실패 처리](issues/10-large-key-fk-and-cascade.md) | 09 | #458, #459 | 20, 22, 38, 53, 54 |
| [11: 직렬화 floor·청크·VOT·길이 guard 경계](issues/11-serialization-chunk-and-guard-boundaries.md) | 01 | #460, #459, #458 | 28, 33, 34, 36, 37, 40 |
| [12: 물리 target·잔여 record·bigone·키 overflow 경계](issues/12-physical-record-and-key-boundaries.md) | 01 | #460, #459, #458 | 33, 34, 35, 37, 38, 39 |
| [13: 반복 쓰기·회수·재사용·단편화 추세](issues/13-churn-reclaim-reuse-and-fragmentation.md) | 01 | #461, #458, #459 | 22, 41, 42, 43, 44, 45, 46, 47, 48, 49 |
| [14: C++ 읽기·Expand·버퍼·dispatch 증명 보완](issues/14-cpp-read-expand-and-buffer-contracts.md) | 01 | #459, #458 | 3, 4, 5, 26, 27, 28, 31, 32 |
| [15: C++ identity·소유권·rollback·reclaim 증명 보완](issues/15-cpp-identity-rollback-and-reclaim.md) | 01 | #459, #461, #458 | 26, 28, 29, 31, 32, 44, 45, 46, 48 |
| [16: 전체 커버리지 대조·최종 native 검증·CI 전달](issues/16-final-coverage-and-ci-handoff.md) | 02, 03, 04, 05, 06, 07, 08, 09, 10, 11, 12, 13, 14, 15 | #456, #457, #458, #459, #460, #461, #462 | 1, 2, 8, 26, 30, 32, 49, 55, 56, 57, 58, 59, 60 |

01 이후 02–09와 11–15가 시작 가능하다. 10은 09의 유효한 referenced-key fixture가 필요하다.
16은 02–15 전부의 결과를 받아 최종 대조한다. 01은 이들 선행 관계에 간접 포함된다.
다른 동작 티켓 간의 fixture 재사용은 선택 사항이며 새 blocking edge가 아니다.

이 그래프는 논리적 의존성이다. DB·설치·registry·process를 공유하는 native 실행의 자원 배정은 별도로 조정한다.
병렬 실행 또는 별도 agent 배정에 필요한 권한과 환경 격리는 실제 실행 시 확인한다.

## 기존 milestone의 수용 조건

| 기존 work | 수용 영역 | 담당 로컬 티켓 |
| --- | --- | --- |
| #457 | 정책 문법·의미·SHOW·유틸리티 | 02, 03, 04, 16 |
| #458 | 전체 연산·HAS_OOS 커버리지 | 01, 02, 03, 04, 05, 06, 07, 08, 09, 10, 11, 12, 13, 14, 15, 16 |
| #459 | C++ 보완·검증된 중복 제거 | 01, 02, 03, 04, 05, 06, 07, 08, 09, 10, 11, 12, 13, 14, 15, 16 |
| #460 | 한계와 다음 경계 | 11, 12, 16 |
| #461 | 회수·재사용·공간 추세 | 13, 15, 16 |
| #462 | 큰 OOS PK·UNIQUE 기능 | 09, 16 |

#458은 01의 초기 목록만으로 완료되지 않는다. 이후 사례와 최종 receipt가 모든 required cell을 채워야 한다.
#459의 동작별 중복 판정은 해당 티켓이 맡고, 14·15가 내부 전용 계약을 보완하며, 16이 전체 목록을 대조한다.
기존 Work109·Work401의 완료 증거는 원래 리비전과 주장 범위로 유지한다.

## 모든 티켓에 적용하는 완료 규칙

1. **기준과 기대:** source·설치·의존성·TC·runner·설정·expected-case identity를 기록한다. 독립적인 intended oracle을 먼저 정한다.
2. **분류와 관측:** 실제 저장된 개별 행의 HAS_OOS set/clear를 사용한다. 같은 heap의 혼합 행과 적용 가능한 전환을 기록한다. 크기·정책·SHOW 합계는 개별 플래그의 대용이 아니다.
3. **검증:** 정상·오류·부분 변경 여부를 전체 값과 해당 소유권으로 검사한다. SQL·shell·C++는 각각 유지되는 native 경로와 verdict artifact로 증명한다.
4. **증거 범위:** 실제 invocation에 필요한 물리 근거를 연결한다. companion fixture·다른 브랜치·다른 모드·정적 사례 수의 증거 범위를 넘겨 합산하지 않는다.
5. **C++ 판정:** 관련 사례에 retain/add/migrate/remove와 assertion 단위의 이유를 남긴다. 삭제·이관에는 검증된 동등 대체와 실행 모드의 근거가 필요하다.
6. **FAIL과 공백:** 재현된 엔진 결함은 정확한 리비전·scenario·수정 링크와 FAIL로 유지한다. 필수 테스트 누락·미실행·skip 및 불명확한 기대는 완료를 막는다. unsupported와 적용 불가는 근거를 갖춰 구분한다.
7. **자원과 산출물:** attempt-owned DB·registry·설정·파일·process를 사용하고 기존 변경과 무관한 자원을 보존한다. 큰 로그는 ignored 경로에 두고 영속 문서에는 재현에 필요한 요약·식별자·링크를 남긴다.

모든 required test가 전달·실행되고 기대가 명확하면, 별도 수정에 연결된 재현 가능한 엔진 FAIL이 남아도 승인된 보완 작업의 완료 조건을 충족할 수 있다.
이 상태와 passing coverage는 별도 주장이다. FAIL을 PASS나 제외로 바꾸지 않는다.
정확한 attribution을 확정하지 못한 실패는 under triage로 유지한다.

## 기존 수정과 회귀의 경계

현재 인벤토리의 관찰 기준은 handover source `1ef86a7efa34002e971b1b30bcf5d451e9db441b`,
공개 TC `df8596dd999e825b1ec9812a735bbe01e50ac715`,
비공개 TC `5c9d8de1a916ae0acbddc8409770b51fd31da13b`다.
이는 구현 시작 시 다시 확인할 과거 snapshot이며 새 실행 receipt가 아니다.

SA-loaddb와 deferred-write 수정은 별도 리비전으로 남긴다. 실제 통합을 이 테스트 작업의 전제로 만들어 합산하지 않는다.
승인된 SA 계약은 값·의미 있는 header/CHN·정책·소유권·트랜잭션·buffer 수명이다.
기존의 unused padding byte 동일성 요구는 superseded 상태를 유지한다.

physical-target 불일치, partition-owner, SA 물리 상태, page-return 및 rollback-after-vacuum의 올바른 회귀를 유지한다.
Work401의 19/19 실행과 별도 sentinel 1/1 receipt를 단일 20-case 실행으로 표현하지 않는다.
앞선 known failure가 다른 필수 workload를 막으면 별도 안전한 fixture로 독립 실행한다.
비실행 후속 단계를 엔진 FAIL이나 coverage로 합산하지 않는다.

## 제외·보류와 게시 경계

크기 의존 경계는 검증하되 small/large RECDES 분류 축은 사용하지 않는다.
큰 OOS PK/UNIQUE는 기능을 검증한다. 성능 비교·baseline 선택·속도 임계값은 보류한다.
HA·복제·failover와 replicated PK/FK는 Work463에 보류한다. 일반 단일 노드 FK는 포함한다.
production 엔진 수정, 경쟁 통합, 새 production 관측 API, perfect packing 또는 OS 파일 축소는 이 티켓들의 완료 조건에 추가하지 않는다.

이번 게시는 로컬 Markdown 티켓만 생성한다. 구현·빌드·테스트 실행·source/TC push·CI trigger·JIRA 수정은 수행하지 않았다.
구현 단계의 source/TC 게시와 최종 CI는 기존 권한과 선행 검사 조건을 적용한다.
필요한 TC 변경은 대응 TC PR head에 게시하고, CI는 허용된 한 번의 실행이 끝나면 URL·결과·TC Merge Gate를 보고한 뒤 멈춘다.
TC PR merge·closure·branch 삭제는 사람이 담당한다.

## 상태와 산출물 유지

로컬 tracker 파일에 진행 상황을 기록하고 durable 사본을 갱신할 때 상대 링크를 확인한다.
`ready-for-agent` label을 dependency 완료의 대용으로 사용하지 않는다.
work-tracker는 기존 ID에 진행·증거·다음 행동을 기록하며 새 상위·하위 work를 중복 생성하지 않는다.
부모 spec이나 JIRA의 범위·상태는 이 티켓 게시로 변경하지 않는다.
