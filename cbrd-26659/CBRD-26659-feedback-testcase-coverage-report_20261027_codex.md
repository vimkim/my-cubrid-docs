# CBRD-26659 — TC 여섯 항목 보완 내용 검토

작성·대조: **2026-10-27, Asia/Seoul**. 보고 대상: **2팀 민준 팀장님**.

민준 팀장님이 요청하신 여섯 카테고리의 TC 추가·보완과 PR 반영을 완료했습니다. 이 문서는 각 항목이 어떤 검사로 보완됐고, 통과·실패·비활성 상태와 남은 검토가 무엇인지 설명합니다. **TC 보완 완료와 전체 동작 검증 완료는 구분합니다.**

- **Engine PR:** [#8128](https://github.com/CUBRID/cubrid/pull/8128)
- **TC Public PR:** [#3688](https://github.com/CUBRID/cubrid-testcases/pull/3688)
- **TC Private PR:** [#4365](https://github.com/CUBRID/cubrid-testcases-private-ex/pull/4365)

**목차:** [전체 결과](#전체-결과) · [여섯 항목](#여섯-항목-한눈에-보기) · [TC별 목록](#현재-tc별-목록) · [이전 기록](#이전-리비전-기록)

<br>

## 전체 결과

**TC 추가·보완과 PR 반영은 완료했으나, 여섯 항목의 전체 검증 완료를 뜻하지는 않습니다.** 현재 PR의 파일과 비활성 목록을 대조하고, [최신 CI 40472072791](https://github.com/CUBRID/cubrid/actions/runs/40472072791)의 개별 TC 로그를 확인했습니다.

| 종류 | 전체 | 활성 | disabled | 최신 CI의 활성 TC 결과 |
| --- | ---: | ---: | ---: | --- |
| SQL | 28 | 25 | 3 | 25 PASS · 0 FAIL |
| shell | 133 | 69 | 64 | 66 PASS · **3 FAIL** |
| **합계** | **161** | **94** | **67** | **91 PASS · 3 FAIL · SKIP/미실행 0** |

C++ 보완 함수 **14개는 별도**입니다. 14개 모두 PR에 있으나 현재 리비전의 개별 실행 결과는 아직 대조하지 않았습니다. 위 161개는 기존 TC를 포함한 **이번 OOS 보완 목록**이며, 새로 만든 TC 수나 전체 CUBRID 회귀 TC 수가 아닙니다.

**PR 반영 확인:** public #3688의 SQL 28개·answer 28개, private #4365의 shell 진입점 133개와 관련 파일, engine #8128의 C++ 보완 함수 14개가 모두 포함되어 있습니다. disabled TC의 보존 파일도 목록의 해시와 일치합니다. 최신 CI 입력은 Engine `e3589ae42`, public `45e21ad79`, private `98723aa47`로 2026-10-27 19:40 확인 당시 PR head와 같습니다.

[현재 TC별 목록·개별 비활성 사유](#현재-tc별-목록)에서 TC 원문과 SQL answer를 볼 수 있습니다. 아래 `SQL-`·`SH-`·`UT-` 번호는 이 목록의 조회 번호입니다.

<br>

## 비활성 67개 — 기능 실패와 장시간을 구분

아래 사유는 **비활성화 당시 관측**을 유지한 것입니다. 최신 CI에서는 이 TC들을 재실행하지 않았습니다.

| 비활성 사유 | SQL | shell | 합계 | 보고 시 해석 |
| --- | ---: | ---: | ---: | --- |
| **기능·정합성 검사 FAIL만** | 3 | 56 | **59** | 기대값·상태·오류 검사에서 실패를 관측했습니다. 엔진 결함인지 TC 기대값 문제인지 개별 원인 분석이 필요합니다. |
| **장시간만** | 0 | 3 | **3** | 당시 기능 검사는 PASS했으나 개별 실행이 60초를 넘었습니다. |
| **FAIL + 장시간** | 0 | 5 | **5** | 실패와 60초 초과가 모두 기록되어 있습니다. 실행 시간만 줄여도 해결되지 않습니다. |
| **합계 — 중복 제외** | **3** | **64** | **67** | 최신 CI에서는 이 67개를 실행하지 않았습니다. |

즉, **실패 사유가 있는 TC는 64개**, **장시간 사유가 있는 TC는 8개**이며 5개가 겹칩니다. 60초는 TC 선택에 적용한 실행 시간 기준입니다. **장시간 8개를 제품 성능 회귀 8건으로 보고하지 않습니다.** 비활성 FAIL도 원인 확인 전 데이터 손상 결함으로 단정하지 않습니다.

장시간만으로 제외된 3개는 `dml_transitions` **101.085초**, `schema_sa` **81.389초**, `large_keys` **381.773초**입니다. 별도 회귀로 운영할지, TC를 나눠 정규 CI에 넣을지 검토가 필요합니다.

<br><br>

## 여섯 항목 한눈에 보기

| 요청 항목 | SQL·shell 전체 / 활성 / disabled | 최신 활성 PASS / FAIL | disabled 사유 | 검토 핵심 |
| --- | --- | --- | --- | --- |
| [① 구문·의미·SHOW·유틸리티](#tc-1) | **29 / 11 / 18** | 11 / 0 | 실패만 18 | 확장 SHOW와 정책별 load/unload·compact는 미완료 |
| [② 사용자 연산·OOS 유무](#tc-2) | **136 / 84 / 52** | 84 / 0 | 실패만 49 · 장시간만 2 · 둘 다 1 | 연산별 TC는 있으나 모든 연산×저장 상태 조합의 독립 검증은 남음 |
| [③ C++ 내부 검증·중복 정리](#tc-3) | 별도 **14함수** | 최신 결과 미대조 | 위 비활성 집계와 별도 | 반영 14/14 확인, 현재 실행 결과·대체 가능성 검토 필요 |
| [④ 경계값·limit+1](#tc-4) | **15 / 9 / 6** | 6 / **3** | 실패만 6 | 활성 3개도 현재 실패. 경계 기대값·저장 경로부터 확인 |
| [⑤ 저장 효율·회수·단편화](#tc-5) | **17 / 5 / 12** | 5 / 0 | 실패만 8 · 둘 다 4 | 핵심 반복 작업·회수 TC가 비활성. 효율 검증 완료로 볼 수 없음 |
| [⑥ 큰 OOS PK/UNIQUE](#tc-6) | **20 / 18 / 2** | 17 / **1** | 실패만 1 · 장시간만 1 | 큰 키 종합 TC는 장시간 제외, key-overflow 경계는 현재 실패 |

한 TC가 여러 항목을 검사하므로 **이 표의 행을 합산하면 중복**됩니다. ④의 `record_keys` 실패 1개는 ⑥에도 표시했습니다. C++ 14개 중 10개는 경계, 2개는 회수 항목에도 연결됩니다.

<br><br>

<a id="tc-1"></a>

## ① SQL 구문·의미·SHOW·유틸리티 — CBRD-26659

**SQL 2개·shell 27개 중 11개 활성 PASS, 18개는 기능 검사 FAIL로 disabled**입니다.

| 검토할 내용 | 반영한 검사와 현재 상태 | 특이사항·남은 확인 |
| --- | --- | --- |
| STORAGE 정책의 정상·오류 입력 | SQL-08·27, SH-097·110: 정책 구문, 잘못된 절·도메인·문맥, 오류 후 값·정책 보존 | 기본 SQL과 SH-110은 PASS. 확장 정책 SH-097은 FAIL로 비활성이어서 전체 의미 검사 완료는 아님 |
| SHOW 대상·권한·파티션 | SH-072·115·116: 정상/잘못된 대상, DBA·일반 사용자, 객체·파티션 귀속 | SH-072는 PASS. 확장 SHOW 2개는 FAIL로 비활성 |
| load/unload·backup/restore·compact | 일반 경로 4개와 compact 3개는 PASS. 정책별 CS/SA load/unload 12개, compact 전환·정책 보존 3개는 비활성 | 값만 복원됐는지 외에 **정책·실제 OOS 저장 상태까지 보존되는지** 확인 필요 |

**검토 요청:** 기본 경로의 통과를 인정하는 범위와, 확장 SHOW·정책별 유틸리티 실패 18개의 분석·수정 우선순위를 확인 부탁드립니다.

<br><br>

<a id="tc-2"></a>

## ② 사용자 연산·OOS 유무 — CBRD-26659

**SQL 19개·shell 117개 중 84개 활성 PASS, 52개 disabled**입니다. 비활성 사유는 실패만 49개, 장시간만 2개, 실패+장시간 1개입니다.

| 검토할 내용 | 반영한 검사와 현재 상태 | 특이사항·남은 확인 |
| --- | --- | --- |
| 읽기·복사·DML·제약·트랜잭션·트리거·FK | 연산별 SQL·shell TC 반영. `alt_duplicate`·`alt_replace`는 덮어쓰기 전 `note=111`과 **큰 값 전체의 정확한 일치**를 추가했고 최신 CI 두 개 모두 PASS | 최종 값만 맞아 중간 오류를 놓치는 문제를 보완함. SQL 결과 통과만으로 물리 OOS 상태를 입증하지는 않음 |
| 실제 OOS 유무와 상태 전환 | SH-100의 실제 레코드 `HAS_OOS` 검사, INSERT와 UPDATE의 clear/set 전환 검사 | **clear는 존재하는 레코드의 OOS 플래그 해제 상태**임. 삭제된 행을 clear로 세지 않으며, 다른 실행의 물리 검사로 해당 SQL의 상태 검증을 대신하지 않음 |
| 스키마·CTAS·파티션·소유권 | 해당 연산 TC를 포함했지만 파티션 shell 18개 중 17개, CTAS 교차 상태 2개 등은 실패로 비활성 | **지원 연산×적용 가능한 clear/set 상태**의 요구 조합을 모두 독립 대조한 상태는 아님 |
| 장시간 사례 | `dml_transitions`·`schema_sa`는 당시 PASS지만 60초 초과. `schema_rewrites_sa`는 FAIL이면서 94.311초 | 장시간 PASS 2개와 기능 실패 1개를 같은 사유로 취급하지 않음 |

**검토 요청:** TC 추가 자체의 누락과 실행·증명 부족을 구분해 검토 부탁드립니다. 특히 파티션·스키마·소유권 실패와 아직 대조되지 않은 연산×상태 조합의 처리 순서를 확인 부탁드립니다.

<br><br>

<a id="tc-3"></a>

## ③ C++ 내부 검증·중복 정리 — CBRD-26659

**보완 함수 14개 모두 engine #8128에 반영되어 있습니다.** 최신 리비전에서 14개가 각각 실행·PASS했는지는 이번 대조에서 확인하지 못했습니다. 이 14개를 위 SQL·shell 비활성 67개에 더하지 않습니다.

| 검토할 내용 | 반영·유지한 검사 | 특이사항·남은 확인 |
| --- | --- | --- |
| SQL로 관찰하기 어려운 내부 동작 | chunk·VOT·stub 경계, 읽기·Expand 재시도, 호출자 버퍼, system-worker undo, 소유권·기존 파일 TDE | 결과값 외에 **버퍼·참조·수명과 내부 상태**를 검사하므로 SQL TC와 겹친다는 이유만으로 삭제할 수 없음 |
| 중복 TC 정리 | 동등한 대체 assertion을 입증하지 못한 기존 내부 검증은 유지 | “C++ 중복 정리 완료”나 “최신 C++ 전체 PASS”로 보고하지 않음. 현재 source의 discovery·실행·결과 대조가 필요 |
| 후속 UPDATE 계약 | UT-13은 할당하지 않은 OOS 값의 stub 보존 검사 | [CBRD-27230](https://jira.cubrid.org/browse/CBRD-27230)는 **develop 병합 이후 TODO로 확정**. 이 관련 항목을 새 병합 전 요청으로 올리지 않음 |

**검토 요청:** 최신 source에서 필요한 C++ 선택을 재실행·대조할 범위와, 동등한 검증을 확인한 뒤 정리할 중복 TC를 확인 부탁드립니다. 과거 리비전의 302개 GTest PASS는 현재 14개의 통과 근거로 옮겨 쓰지 않았습니다.

<br><br>

<a id="tc-4"></a>

## ④ 경계값·limit+1 — CBRD-26659

**SQL 7개·shell 8개 중 9개 활성, 6개 disabled**입니다. 최신 활성 결과는 **6 PASS·3 FAIL**이며, 비활성 6개도 모두 기능 검사 FAIL 사유입니다. C++ 경계 보완 10개는 별도입니다.

| 검토할 내용 | 반영한 검사와 현재 상태 | 특이사항·남은 확인 |
| --- | --- | --- |
| 직렬화·chunk·VOT·stub/버퍼 | 24B stub와 다음 가능한 직렬화 크기, chunk 용량 전후, VOT 폭, exact/한 byte 부족 버퍼 | 문자 수와 실제 저장 byte 수를 구분해야 함. 큰 길이의 parser/정수 변환 guard TC는 **실제 최대 크기 저장 시험을 대신하지 않음** |
| record target·큰 행·잔여 고정 부분 | `record_target0/10`, `serialized_chunks`, SQL `record_boundaries`·`sql05_bigone`·`sql09_lob_maxcols`는 비활성 | 페이지 내 목표 크기와 실제 저장 한계를 혼동하지 않는지, unfill과 독립적인 target인지 기대값부터 확인 필요 |
| 현재 활성 실패 | `record_keys`·`record_layout`·`record_residual` | 과거 PASS와 달리 현재 CI에서 실패. 엔진·fixture·기대값 중 원인은 아직 미확정 |
| overflow 구분 | develop의 **heap 큰 행 overflow**, OOS, **B-tree key overflow**를 별도 관찰 | 키가 커져 B-tree overflow에 정상 저장되는 경로를 오류로 기대하지 않는지 확인 필요. OOS+REC_BIGONE 미지원 조건도 구분 |

현재 실패 로그: [record_residual](https://github.com/CUBRID/cubrid/actions/runs/40472072791/job/122086744588) · [record_layout](https://github.com/CUBRID/cubrid/actions/runs/40472072791/job/122086744633) · [record_keys](https://github.com/CUBRID/cubrid/actions/runs/40472072791/job/122086744964).

**검토 요청:** 활성 FAIL 3개의 원인·기대값 대조를 우선 진행하고, 비활성 경계 6개의 수정·재활성화 순서를 확인 부탁드립니다. “경계 TC를 넣었다”와 “경계 동작이 검증됐다”를 구분할 필요가 있습니다.

<br><br>

<a id="tc-5"></a>

## ⑤ 저장 효율·공간 회수·단편화 — CBRD-26659

**shell 17개 중 5개 활성 PASS, 12개 disabled**입니다. 비활성은 실패만 8개, 실패+장시간 4개이며 **장시간만으로 제외된 TC는 없습니다.** C++ 관련 보완 2개는 별도입니다.

| 검토할 내용 | 반영한 검사와 현재 상태 | 특이사항·남은 확인 |
| --- | --- | --- |
| 반복 INSERT/DELETE·INSERT/UPDATE/DELETE, abort/retry·restart | `churn_*` 4개는 FAIL이면서 약84~95초로 비활성 | 반복 뒤 survivor 값, chunk/page 수, 회수·재사용과 불필요한 volume 증가를 검증 완료로 볼 수 없음 |
| snapshot 이후 회수·소유권·알림·rollback/vacuum | `snapshots_reclaim`, `notify_*`, `qualified_reuse`, `alt_stub_*`, `rollback_vacuum` 등 8개 비활성 | **값 읽기 성공과 페이지 반환 성공은 다른 검사**임. chunk 삭제와 비어 있는 페이지 회수도 구분해야 함 |
| 현재 PASS 범위 | snapshot 가시성, committed/undo crash, DROP/recreate 후 독립 survivor 등 5개 | 특정 가시성·복구·파일 수명 검증임. 반복 작업의 공간 효율·단편화 전체를 대체하지 못함 |

**검토 요청:** 이 항목을 “저장 효율 검증 완료”로 수용하지 않고, 핵심 반복·회수 실패를 우선 추적할지 확인 부탁드립니다. `rollback_vacuum`은 [CBRD-27237](https://jira.cubrid.org/browse/CBRD-27237)과 연결해 스펙 회귀 판단에도 반영해야 합니다.

<br><br>

<a id="tc-6"></a>

## ⑥ 큰 OOS PK/UNIQUE — CBRD-26659

**SQL 3개·shell 17개 중 18개 활성, 2개 disabled**입니다. 최신 활성 결과는 **17 PASS·1 FAIL**입니다. 비활성은 기능 실패 1개와 장시간만 1개입니다.

| 검토할 내용 | 반영한 검사와 현재 상태 | 특이사항·남은 확인 |
| --- | --- | --- |
| 단일·복합 PK/UNIQUE, 생성·변경·중복·NULL·rollback | SQL-25·26, SH-004와 OOS key FK 14개 등 활성 PASS | 일반 key+OOS payload 대조군과 **indexed attribute 자체가 OOS인 경우**를 구분. SQL의 값 통과만으로 indexed attribute의 물리 OOS 상태까지 입증하지 않음 |
| 타입·정책·키·생성/유지 조합의 종합 검사 | `large_keys`는 당시 기능 PASS, **381.773초**로 disabled | 정합성 FAIL로 제외한 TC가 아님. 현재 정규 CI가 이 종합 조합을 실행·통과한 것으로 계산하지 않음 |
| key-overflow·물리 귀속 경계 | `record_keys`는 최신 FAIL, SQL `record_boundaries`는 실패로 disabled | ④와 공유하는 실패임. 별도 실패 1건을 추가해 총 4건으로 세지 않음 |

**검토 요청:** 큰 키 종합 TC를 분할하거나 별도 회귀로 실행할 방식, 실제 OOS 인덱스 키의 물리 상태 검증, key-overflow 경계 실패의 처리를 확인 부탁드립니다. 이 항목은 기능 검증이며 성능 비교·HA 검증 완료를 뜻하지 않습니다.

<br>


## 실행 입력과 대조 방법

| 저장소 | 검토 커밋 |
| --- | --- |
| CUBRID/cubrid | `e3589ae42d42b04eb020e1ae43e165b01d31b12a` |
| CUBRID/cubrid-testcases | `45e21ad799d82ebadc04a93c7d2f69517d53bf39` |
| CUBRID/cubrid-testcases-private-ex | `98723aa473cde722abbc729799cf489b7f3f732f` |

기존 피드백 대응표의 요구 영역·TC 매핑을 기준으로 현재 Git 객체의 파일 존재와 보존 해시를 대조했습니다. SQL·answer 56/56개, shell 진입점·관련 파일 204/204개, C++ 파일 4/4개와 보완 함수 14/14개를 확인했습니다. SQL `alt_duplicate`·`alt_replace`와 answer 두 개에 추가한 중간값 검사를 제외하면 해당 대상의 내용은 기존 검토본과 같습니다.

[CI 40472072791](https://github.com/CUBRID/cubrid/actions/runs/40472072791)의 checkout/build 입력을 위 커밋과 대조하고, 전체 job 로그에서 활성 TC의 실제 경로와 개별 `[OK]`/`[NOK]`를 확인했습니다. SQL 25개·shell 69개 모두 경로가 일치했고 비활성 67개는 실행되지 않았습니다. 이 문서 정리를 위해 엔진·TC를 수정하거나 새 CI를 실행하지 않았습니다.

비활성 사유는 [SQL manifest](https://github.com/CUBRID/cubrid-testcases/blob/45e21ad799d82ebadc04a93c7d2f69517d53bf39/disabled/oos-pr8128.tsv)와 [shell inventory](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/98723aa473cde722abbc729799cf489b7f3f732f/disabled/oos-pr8128-inventory.tsv)의 당시 관측을 유지했습니다. FAIL의 개별 원인 분석과 최신 C++ 실행 대조는 이번 검토에 포함하지 않았습니다.

<br><br>

## 현재 TC별 목록

아래 대응표는 각 TC의 요구 영역·PR 원문·현재 선택·최신 실행 결과와 비활성 사유를 연결합니다. **① 구문·유틸리티 / ② 사용자 연산 / ③ C++ 내부 / ④ 경계 / ⑤ 효율·회수 / ⑥ 큰 키**를 뜻하며 항목 간 중복이 있습니다. `SQL-`·`SH-`·`UT-`는 조회 번호입니다.

### SQL TC 28개

| 번호 | 대응 항목 | TC 원문 | 선택 | 최신 CI 결과 | 비활성 사유·당시 시간 |
| --- | --- | --- | --- | --- | --- |
| SQL-01 | 2 | [oos_alt_duplicate](https://github.com/CUBRID/cubrid-testcases/blob/45e21ad799d82ebadc04a93c7d2f69517d53bf39/sql/_36_guava/cbrd_26659/cases/cbrd_26659_oos_alt_duplicate.sql) · [answer](https://github.com/CUBRID/cubrid-testcases/blob/45e21ad799d82ebadc04a93c7d2f69517d53bf39/sql/_36_guava/cbrd_26659/answers/cbrd_26659_oos_alt_duplicate.answer) | 활성 | PASS | — |
| SQL-02 | 2 | [oos_alt_merge](https://github.com/CUBRID/cubrid-testcases/blob/45e21ad799d82ebadc04a93c7d2f69517d53bf39/sql/_36_guava/cbrd_26659/cases/cbrd_26659_oos_alt_merge.sql) · [answer](https://github.com/CUBRID/cubrid-testcases/blob/45e21ad799d82ebadc04a93c7d2f69517d53bf39/sql/_36_guava/cbrd_26659/answers/cbrd_26659_oos_alt_merge.answer) | 활성 | PASS | — |
| SQL-03 | 2 | [oos_alt_replace](https://github.com/CUBRID/cubrid-testcases/blob/45e21ad799d82ebadc04a93c7d2f69517d53bf39/sql/_36_guava/cbrd_26659/cases/cbrd_26659_oos_alt_replace.sql) · [answer](https://github.com/CUBRID/cubrid-testcases/blob/45e21ad799d82ebadc04a93c7d2f69517d53bf39/sql/_36_guava/cbrd_26659/answers/cbrd_26659_oos_alt_replace.answer) | 활성 | PASS | — |
| SQL-04 | 4 | [oos_chunk_boundaries](https://github.com/CUBRID/cubrid-testcases/blob/45e21ad799d82ebadc04a93c7d2f69517d53bf39/sql/_36_guava/cbrd_26659/cases/cbrd_26659_oos_chunk_boundaries.sql) · [answer](https://github.com/CUBRID/cubrid-testcases/blob/45e21ad799d82ebadc04a93c7d2f69517d53bf39/sql/_36_guava/cbrd_26659/answers/cbrd_26659_oos_chunk_boundaries.answer) | 활성 | PASS | — |
| SQL-05 | 2 | [oos_dml_forms](https://github.com/CUBRID/cubrid-testcases/blob/45e21ad799d82ebadc04a93c7d2f69517d53bf39/sql/_36_guava/cbrd_26659/cases/cbrd_26659_oos_dml_forms.sql) · [answer](https://github.com/CUBRID/cubrid-testcases/blob/45e21ad799d82ebadc04a93c7d2f69517d53bf39/sql/_36_guava/cbrd_26659/answers/cbrd_26659_oos_dml_forms.answer) | 활성 | PASS | — |
| SQL-06 | 2 | [oos_partition](https://github.com/CUBRID/cubrid-testcases/blob/45e21ad799d82ebadc04a93c7d2f69517d53bf39/sql/_36_guava/cbrd_26659/cases/cbrd_26659_oos_partition.sql) · [answer](https://github.com/CUBRID/cubrid-testcases/blob/45e21ad799d82ebadc04a93c7d2f69517d53bf39/sql/_36_guava/cbrd_26659/answers/cbrd_26659_oos_partition.answer) | 활성 | PASS | — |
| SQL-07 | 2 | [oos_partition_routing](https://github.com/CUBRID/cubrid-testcases/blob/45e21ad799d82ebadc04a93c7d2f69517d53bf39/sql/_36_guava/cbrd_26659/cases/cbrd_26659_oos_partition_routing.sql) · [answer](https://github.com/CUBRID/cubrid-testcases/blob/45e21ad799d82ebadc04a93c7d2f69517d53bf39/sql/_36_guava/cbrd_26659/answers/cbrd_26659_oos_partition_routing.answer) | 활성 | PASS | — |
| SQL-08 | 1 | [oos_policy_syntax](https://github.com/CUBRID/cubrid-testcases/blob/45e21ad799d82ebadc04a93c7d2f69517d53bf39/sql/_36_guava/cbrd_26659/cases/cbrd_26659_oos_policy_syntax.sql) · [answer](https://github.com/CUBRID/cubrid-testcases/blob/45e21ad799d82ebadc04a93c7d2f69517d53bf39/sql/_36_guava/cbrd_26659/answers/cbrd_26659_oos_policy_syntax.answer) | 활성 | PASS | — |
| SQL-09 | 2 | [oos_read_relations](https://github.com/CUBRID/cubrid-testcases/blob/45e21ad799d82ebadc04a93c7d2f69517d53bf39/sql/_36_guava/cbrd_26659/cases/cbrd_26659_oos_read_relations.sql) · [answer](https://github.com/CUBRID/cubrid-testcases/blob/45e21ad799d82ebadc04a93c7d2f69517d53bf39/sql/_36_guava/cbrd_26659/answers/cbrd_26659_oos_read_relations.answer) | 활성 | PASS | — |
| SQL-10 | 4·6 | [oos_record_boundaries](https://github.com/CUBRID/cubrid-testcases/blob/45e21ad799d82ebadc04a93c7d2f69517d53bf39/disabled/failing/sql/_36_guava/cbrd_26659/cases/cbrd_26659_oos_record_boundaries.sql.disabled) · [answer](https://github.com/CUBRID/cubrid-testcases/blob/45e21ad799d82ebadc04a93c7d2f69517d53bf39/disabled/failing/sql/_36_guava/cbrd_26659/answers/cbrd_26659_oos_record_boundaries.answer) | **disabled** | 미실행 | 기능 검사 FAIL · 0.040초 |
| SQL-11 | 4 | [oos_representation](https://github.com/CUBRID/cubrid-testcases/blob/45e21ad799d82ebadc04a93c7d2f69517d53bf39/sql/_36_guava/cbrd_26659/cases/cbrd_26659_oos_representation.sql) · [answer](https://github.com/CUBRID/cubrid-testcases/blob/45e21ad799d82ebadc04a93c7d2f69517d53bf39/sql/_36_guava/cbrd_26659/answers/cbrd_26659_oos_representation.answer) | 활성 | PASS | — |
| SQL-12 | 2 | [oos_schema](https://github.com/CUBRID/cubrid-testcases/blob/45e21ad799d82ebadc04a93c7d2f69517d53bf39/sql/_36_guava/cbrd_26659/cases/cbrd_26659_oos_schema.sql) · [answer](https://github.com/CUBRID/cubrid-testcases/blob/45e21ad799d82ebadc04a93c7d2f69517d53bf39/sql/_36_guava/cbrd_26659/answers/cbrd_26659_oos_schema.answer) | 활성 | PASS | — |
| SQL-13 | 2 | [oos_schema_materialize](https://github.com/CUBRID/cubrid-testcases/blob/45e21ad799d82ebadc04a93c7d2f69517d53bf39/sql/_36_guava/cbrd_26659/cases/cbrd_26659_oos_schema_materialize.sql) · [answer](https://github.com/CUBRID/cubrid-testcases/blob/45e21ad799d82ebadc04a93c7d2f69517d53bf39/sql/_36_guava/cbrd_26659/answers/cbrd_26659_oos_schema_materialize.answer) | 활성 | PASS | — |
| SQL-14 | 2 | [oos_schema_rewrites](https://github.com/CUBRID/cubrid-testcases/blob/45e21ad799d82ebadc04a93c7d2f69517d53bf39/sql/_36_guava/cbrd_26659/cases/cbrd_26659_oos_schema_rewrites.sql) · [answer](https://github.com/CUBRID/cubrid-testcases/blob/45e21ad799d82ebadc04a93c7d2f69517d53bf39/sql/_36_guava/cbrd_26659/answers/cbrd_26659_oos_schema_rewrites.answer) | 활성 | PASS | — |
| SQL-15 | 2 | [oos_sql01_insert_select](https://github.com/CUBRID/cubrid-testcases/blob/45e21ad799d82ebadc04a93c7d2f69517d53bf39/sql/_36_guava/cbrd_26659/cases/cbrd_26659_oos_sql01_insert_select.sql) · [answer](https://github.com/CUBRID/cubrid-testcases/blob/45e21ad799d82ebadc04a93c7d2f69517d53bf39/sql/_36_guava/cbrd_26659/answers/cbrd_26659_oos_sql01_insert_select.answer) | 활성 | PASS | — |
| SQL-16 | 2 | [oos_sql04_delete](https://github.com/CUBRID/cubrid-testcases/blob/45e21ad799d82ebadc04a93c7d2f69517d53bf39/sql/_36_guava/cbrd_26659/cases/cbrd_26659_oos_sql04_delete.sql) · [answer](https://github.com/CUBRID/cubrid-testcases/blob/45e21ad799d82ebadc04a93c7d2f69517d53bf39/sql/_36_guava/cbrd_26659/answers/cbrd_26659_oos_sql04_delete.answer) | 활성 | PASS | — |
| SQL-17 | 2 | [oos_sql04_update](https://github.com/CUBRID/cubrid-testcases/blob/45e21ad799d82ebadc04a93c7d2f69517d53bf39/sql/_36_guava/cbrd_26659/cases/cbrd_26659_oos_sql04_update.sql) · [answer](https://github.com/CUBRID/cubrid-testcases/blob/45e21ad799d82ebadc04a93c7d2f69517d53bf39/sql/_36_guava/cbrd_26659/answers/cbrd_26659_oos_sql04_update.answer) | 활성 | PASS | — |
| SQL-18 | 4 | [oos_sql05_bigone](https://github.com/CUBRID/cubrid-testcases/blob/45e21ad799d82ebadc04a93c7d2f69517d53bf39/disabled/failing/sql/_36_guava/cbrd_26659/cases/cbrd_26659_oos_sql05_bigone.sql.disabled) · [answer](https://github.com/CUBRID/cubrid-testcases/blob/45e21ad799d82ebadc04a93c7d2f69517d53bf39/disabled/failing/sql/_36_guava/cbrd_26659/answers/cbrd_26659_oos_sql05_bigone.answer) | **disabled** | 미실행 | 기능 검사 FAIL · 0.048초 |
| SQL-19 | 2 | [oos_sql05_constraints](https://github.com/CUBRID/cubrid-testcases/blob/45e21ad799d82ebadc04a93c7d2f69517d53bf39/sql/_36_guava/cbrd_26659/cases/cbrd_26659_oos_sql05_constraints.sql) · [answer](https://github.com/CUBRID/cubrid-testcases/blob/45e21ad799d82ebadc04a93c7d2f69517d53bf39/sql/_36_guava/cbrd_26659/answers/cbrd_26659_oos_sql05_constraints.answer) | 활성 | PASS | — |
| SQL-20 | 2 | [oos_sql05_transactions](https://github.com/CUBRID/cubrid-testcases/blob/45e21ad799d82ebadc04a93c7d2f69517d53bf39/sql/_36_guava/cbrd_26659/cases/cbrd_26659_oos_sql05_transactions.sql) · [answer](https://github.com/CUBRID/cubrid-testcases/blob/45e21ad799d82ebadc04a93c7d2f69517d53bf39/sql/_36_guava/cbrd_26659/answers/cbrd_26659_oos_sql05_transactions.answer) | 활성 | PASS | — |
| SQL-21 | 2 | [oos_sql06_triggers](https://github.com/CUBRID/cubrid-testcases/blob/45e21ad799d82ebadc04a93c7d2f69517d53bf39/sql/_36_guava/cbrd_26659/cases/cbrd_26659_oos_sql06_triggers.sql) · [answer](https://github.com/CUBRID/cubrid-testcases/blob/45e21ad799d82ebadc04a93c7d2f69517d53bf39/sql/_36_guava/cbrd_26659/answers/cbrd_26659_oos_sql06_triggers.answer) | 활성 | PASS | — |
| SQL-22 | 2 | [oos_sql07_read_paths](https://github.com/CUBRID/cubrid-testcases/blob/45e21ad799d82ebadc04a93c7d2f69517d53bf39/sql/_36_guava/cbrd_26659/cases/cbrd_26659_oos_sql07_read_paths.sql) · [answer](https://github.com/CUBRID/cubrid-testcases/blob/45e21ad799d82ebadc04a93c7d2f69517d53bf39/sql/_36_guava/cbrd_26659/answers/cbrd_26659_oos_sql07_read_paths.answer) | 활성 | PASS | — |
| SQL-23 | 2 | [oos_sql09_lob_copy](https://github.com/CUBRID/cubrid-testcases/blob/45e21ad799d82ebadc04a93c7d2f69517d53bf39/sql/_36_guava/cbrd_26659/cases/cbrd_26659_oos_sql09_lob_copy.sql) · [answer](https://github.com/CUBRID/cubrid-testcases/blob/45e21ad799d82ebadc04a93c7d2f69517d53bf39/sql/_36_guava/cbrd_26659/answers/cbrd_26659_oos_sql09_lob_copy.answer) | 활성 | PASS | — |
| SQL-24 | 4 | [oos_sql09_lob_maxcols](https://github.com/CUBRID/cubrid-testcases/blob/45e21ad799d82ebadc04a93c7d2f69517d53bf39/disabled/failing/sql/_36_guava/cbrd_26659/cases/cbrd_26659_oos_sql09_lob_maxcols.sql.disabled) · [answer](https://github.com/CUBRID/cubrid-testcases/blob/45e21ad799d82ebadc04a93c7d2f69517d53bf39/disabled/failing/sql/_36_guava/cbrd_26659/answers/cbrd_26659_oos_sql09_lob_maxcols.answer) | **disabled** | 미실행 | 기능 검사 FAIL · 0.797초 |
| SQL-25 | 6 | [oos_sql18_large_keys](https://github.com/CUBRID/cubrid-testcases/blob/45e21ad799d82ebadc04a93c7d2f69517d53bf39/sql/_36_guava/cbrd_26659/cases/cbrd_26659_oos_sql18_large_keys.sql) · [answer](https://github.com/CUBRID/cubrid-testcases/blob/45e21ad799d82ebadc04a93c7d2f69517d53bf39/sql/_36_guava/cbrd_26659/answers/cbrd_26659_oos_sql18_large_keys.answer) | 활성 | PASS | — |
| SQL-26 | 2·6 | [oos_sql19_fk_actions](https://github.com/CUBRID/cubrid-testcases/blob/45e21ad799d82ebadc04a93c7d2f69517d53bf39/sql/_36_guava/cbrd_26659/cases/cbrd_26659_oos_sql19_fk_actions.sql) · [answer](https://github.com/CUBRID/cubrid-testcases/blob/45e21ad799d82ebadc04a93c7d2f69517d53bf39/sql/_36_guava/cbrd_26659/answers/cbrd_26659_oos_sql19_fk_actions.answer) | 활성 | PASS | — |
| SQL-27 | 1·4 | [oos_storage_policy](https://github.com/CUBRID/cubrid-testcases/blob/45e21ad799d82ebadc04a93c7d2f69517d53bf39/sql/_36_guava/cbrd_26659/cases/cbrd_26659_oos_storage_policy.sql) · [answer](https://github.com/CUBRID/cubrid-testcases/blob/45e21ad799d82ebadc04a93c7d2f69517d53bf39/sql/_36_guava/cbrd_26659/answers/cbrd_26659_oos_storage_policy.answer) | 활성 | PASS | — |
| SQL-28 | 4 | [oos_vot_many_attributes](https://github.com/CUBRID/cubrid-testcases/blob/45e21ad799d82ebadc04a93c7d2f69517d53bf39/sql/_36_guava/cbrd_26659/cases/cbrd_26659_oos_vot_many_attributes.sql) · [answer](https://github.com/CUBRID/cubrid-testcases/blob/45e21ad799d82ebadc04a93c7d2f69517d53bf39/sql/_36_guava/cbrd_26659/answers/cbrd_26659_oos_vot_many_attributes.answer) | 활성 | PASS | — |

<br>

### shell TC 133개

| 번호 | 대응 항목 | TC 원문 | 선택 | 최신 CI 결과 | 비활성 사유·당시 시간 |
| --- | --- | --- | --- | --- | --- |
| SH-001 | 2 | [alt_duplicate_select](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/98723aa473cde722abbc729799cf489b7f3f732f/shell/_40_guava/cbrd_26659_alt_duplicate_select/cases/cbrd_26659_alt_duplicate_select.sh) | 활성 | PASS | — |
| SH-002 | 2 | [alt_duplicate_set](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/98723aa473cde722abbc729799cf489b7f3f732f/shell/_40_guava/cbrd_26659_alt_duplicate_set/cases/cbrd_26659_alt_duplicate_set.sh) | 활성 | PASS | — |
| SH-003 | 2 | [alt_duplicate_values](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/98723aa473cde722abbc729799cf489b7f3f732f/shell/_40_guava/cbrd_26659_alt_duplicate_values/cases/cbrd_26659_alt_duplicate_values.sh) | 활성 | PASS | — |
| SH-004 | 2·6 | [alt_indexed](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/98723aa473cde722abbc729799cf489b7f3f732f/shell/_40_guava/cbrd_26659_alt_indexed/cases/cbrd_26659_alt_indexed.sh) | 활성 | PASS | — |
| SH-005 | 2 | [alt_merge](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/98723aa473cde722abbc729799cf489b7f3f732f/shell/_40_guava/cbrd_26659_alt_merge/cases/cbrd_26659_alt_merge.sh) | 활성 | PASS | — |
| SH-006 | 2 | [alt_replace_select](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/98723aa473cde722abbc729799cf489b7f3f732f/shell/_40_guava/cbrd_26659_alt_replace_select/cases/cbrd_26659_alt_replace_select.sh) | 활성 | PASS | — |
| SH-007 | 2 | [alt_replace_set](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/98723aa473cde722abbc729799cf489b7f3f732f/shell/_40_guava/cbrd_26659_alt_replace_set/cases/cbrd_26659_alt_replace_set.sh) | 활성 | PASS | — |
| SH-008 | 2 | [alt_replace_values](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/98723aa473cde722abbc729799cf489b7f3f732f/shell/_40_guava/cbrd_26659_alt_replace_values/cases/cbrd_26659_alt_replace_values.sh) | 활성 | PASS | — |
| SH-009 | 2·5 | [alt_stub_duplicate](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/98723aa473cde722abbc729799cf489b7f3f732f/disabled/failing/shell/_40_guava/cbrd_26659_alt_stub_duplicate/cases/cbrd_26659_alt_stub_duplicate.sh.disabled) | **disabled** | 미실행 | 기능 검사 FAIL · 15.505초 |
| SH-010 | 2·5 | [alt_stub_merge](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/98723aa473cde722abbc729799cf489b7f3f732f/disabled/failing/shell/_40_guava/cbrd_26659_alt_stub_merge/cases/cbrd_26659_alt_stub_merge.sh.disabled) | **disabled** | 미실행 | 기능 검사 FAIL · 16.267초 |
| SH-011 | 1·2 | [backup_restore](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/98723aa473cde722abbc729799cf489b7f3f732f/shell/_40_guava/cbrd_26659_backup_restore/cases/cbrd_26659_backup_restore.sh) | 활성 | PASS | — |
| SH-012 | 5 | [churn_abort_retry](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/98723aa473cde722abbc729799cf489b7f3f732f/disabled/long_running/shell/_40_guava/cbrd_26659_churn_abort_retry/cases/cbrd_26659_churn_abort_retry.sh.disabled) | **disabled** | 미실행 | 기능 검사 FAIL + 60초 초과 · 83.614초 |
| SH-013 | 5 | [churn_insert_delete](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/98723aa473cde722abbc729799cf489b7f3f732f/disabled/long_running/shell/_40_guava/cbrd_26659_churn_insert_delete/cases/cbrd_26659_churn_insert_delete.sh.disabled) | **disabled** | 미실행 | 기능 검사 FAIL + 60초 초과 · 83.570초 |
| SH-014 | 5 | [churn_insert_update_delete](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/98723aa473cde722abbc729799cf489b7f3f732f/disabled/long_running/shell/_40_guava/cbrd_26659_churn_insert_update_delete/cases/cbrd_26659_churn_insert_update_delete.sh.disabled) | **disabled** | 미실행 | 기능 검사 FAIL + 60초 초과 · 90.506초 |
| SH-015 | 5 | [churn_restart](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/98723aa473cde722abbc729799cf489b7f3f732f/disabled/long_running/shell/_40_guava/cbrd_26659_churn_restart/cases/cbrd_26659_churn_restart.sh.disabled) | **disabled** | 미실행 | 기능 검사 FAIL + 60초 초과 · 94.797초 |
| SH-016 | 2·5 | [crash_committed](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/98723aa473cde722abbc729799cf489b7f3f732f/shell/_40_guava/cbrd_26659_crash_committed/cases/cbrd_26659_crash_committed.sh) | 활성 | PASS | — |
| SH-017 | 2·5 | [crash_undo](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/98723aa473cde722abbc729799cf489b7f3f732f/shell/_40_guava/cbrd_26659_crash_undo/cases/cbrd_26659_crash_undo.sh) | 활성 | PASS | — |
| SH-018 | 2 | [dml_atomicity](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/98723aa473cde722abbc729799cf489b7f3f732f/shell/_40_guava/cbrd_26659_dml_atomicity/cases/cbrd_26659_dml_atomicity.sh) | 활성 | PASS | — |
| SH-019 | 2 | [dml_forms](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/98723aa473cde722abbc729799cf489b7f3f732f/shell/_40_guava/cbrd_26659_dml_forms/cases/cbrd_26659_dml_forms.sh) | 활성 | PASS | — |
| SH-020 | 2 | [dml_states](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/98723aa473cde722abbc729799cf489b7f3f732f/shell/_40_guava/cbrd_26659_dml_states/cases/cbrd_26659_dml_states.sh) | 활성 | PASS | — |
| SH-021 | 2 | [dml_transactions](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/98723aa473cde722abbc729799cf489b7f3f732f/shell/_40_guava/cbrd_26659_dml_transactions/cases/cbrd_26659_dml_transactions.sh) | 활성 | PASS | — |
| SH-022 | 2 | [dml_transitions](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/98723aa473cde722abbc729799cf489b7f3f732f/disabled/long_running/shell/_40_guava/cbrd_26659_dml_transitions/cases/cbrd_26659_dml_transitions.sh.disabled) | **disabled** | 미실행 | 60초 초과만 · 당시 PASS · 101.085초 |
| SH-023 | 2 | [dml_triggers_delete](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/98723aa473cde722abbc729799cf489b7f3f732f/shell/_40_guava/cbrd_26659_dml_triggers_delete/cases/cbrd_26659_dml_triggers_delete.sh) | 활성 | PASS | — |
| SH-024 | 2 | [dml_triggers_insert](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/98723aa473cde722abbc729799cf489b7f3f732f/shell/_40_guava/cbrd_26659_dml_triggers_insert/cases/cbrd_26659_dml_triggers_insert.sh) | 활성 | PASS | — |
| SH-025 | 2 | [dml_triggers_reject](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/98723aa473cde722abbc729799cf489b7f3f732f/shell/_40_guava/cbrd_26659_dml_triggers_reject/cases/cbrd_26659_dml_triggers_reject.sh) | 활성 | PASS | — |
| SH-026 | 2 | [dml_triggers_update](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/98723aa473cde722abbc729799cf489b7f3f732f/shell/_40_guava/cbrd_26659_dml_triggers_update/cases/cbrd_26659_dml_triggers_update.sh) | 활성 | PASS | — |
| SH-027 | 2·6 | [fk_key_composite_cascade](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/98723aa473cde722abbc729799cf489b7f3f732f/shell/_40_guava/cbrd_26659_fk_key_composite_cascade/cases/cbrd_26659_fk_key_composite_cascade.sh) | 활성 | PASS | — |
| SH-028 | 2·6 | [fk_key_composite_cascade_block](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/98723aa473cde722abbc729799cf489b7f3f732f/shell/_40_guava/cbrd_26659_fk_key_composite_cascade_block/cases/cbrd_26659_fk_key_composite_cascade_block.sh) | 활성 | PASS | — |
| SH-029 | 2·6 | [fk_key_composite_default](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/98723aa473cde722abbc729799cf489b7f3f732f/shell/_40_guava/cbrd_26659_fk_key_composite_default/cases/cbrd_26659_fk_key_composite_default.sh) | 활성 | PASS | — |
| SH-030 | 2·6 | [fk_key_composite_delete_null](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/98723aa473cde722abbc729799cf489b7f3f732f/shell/_40_guava/cbrd_26659_fk_key_composite_delete_null/cases/cbrd_26659_fk_key_composite_delete_null.sh) | 활성 | PASS | — |
| SH-031 | 2·6 | [fk_key_composite_noaction](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/98723aa473cde722abbc729799cf489b7f3f732f/shell/_40_guava/cbrd_26659_fk_key_composite_noaction/cases/cbrd_26659_fk_key_composite_noaction.sh) | 활성 | PASS | — |
| SH-032 | 2·6 | [fk_key_composite_restrict](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/98723aa473cde722abbc729799cf489b7f3f732f/shell/_40_guava/cbrd_26659_fk_key_composite_restrict/cases/cbrd_26659_fk_key_composite_restrict.sh) | 활성 | PASS | — |
| SH-033 | 2·6 | [fk_key_composite_update_null](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/98723aa473cde722abbc729799cf489b7f3f732f/shell/_40_guava/cbrd_26659_fk_key_composite_update_null/cases/cbrd_26659_fk_key_composite_update_null.sh) | 활성 | PASS | — |
| SH-034 | 2·6 | [fk_key_single_cascade](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/98723aa473cde722abbc729799cf489b7f3f732f/shell/_40_guava/cbrd_26659_fk_key_single_cascade/cases/cbrd_26659_fk_key_single_cascade.sh) | 활성 | PASS | — |
| SH-035 | 2·6 | [fk_key_single_cascade_block](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/98723aa473cde722abbc729799cf489b7f3f732f/shell/_40_guava/cbrd_26659_fk_key_single_cascade_block/cases/cbrd_26659_fk_key_single_cascade_block.sh) | 활성 | PASS | — |
| SH-036 | 2·6 | [fk_key_single_default](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/98723aa473cde722abbc729799cf489b7f3f732f/shell/_40_guava/cbrd_26659_fk_key_single_default/cases/cbrd_26659_fk_key_single_default.sh) | 활성 | PASS | — |
| SH-037 | 2·6 | [fk_key_single_delete_null](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/98723aa473cde722abbc729799cf489b7f3f732f/shell/_40_guava/cbrd_26659_fk_key_single_delete_null/cases/cbrd_26659_fk_key_single_delete_null.sh) | 활성 | PASS | — |
| SH-038 | 2·6 | [fk_key_single_noaction](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/98723aa473cde722abbc729799cf489b7f3f732f/shell/_40_guava/cbrd_26659_fk_key_single_noaction/cases/cbrd_26659_fk_key_single_noaction.sh) | 활성 | PASS | — |
| SH-039 | 2·6 | [fk_key_single_restrict](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/98723aa473cde722abbc729799cf489b7f3f732f/shell/_40_guava/cbrd_26659_fk_key_single_restrict/cases/cbrd_26659_fk_key_single_restrict.sh) | 활성 | PASS | — |
| SH-040 | 2·6 | [fk_key_single_update_null](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/98723aa473cde722abbc729799cf489b7f3f732f/shell/_40_guava/cbrd_26659_fk_key_single_update_null/cases/cbrd_26659_fk_key_single_update_null.sh) | 활성 | PASS | — |
| SH-041 | 2 | [fk_payload_composite_cascade](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/98723aa473cde722abbc729799cf489b7f3f732f/shell/_40_guava/cbrd_26659_fk_payload_composite_cascade/cases/cbrd_26659_fk_payload_composite_cascade.sh) | 활성 | PASS | — |
| SH-042 | 2 | [fk_payload_composite_cascade_block](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/98723aa473cde722abbc729799cf489b7f3f732f/shell/_40_guava/cbrd_26659_fk_payload_composite_cascade_block/cases/cbrd_26659_fk_payload_composite_cascade_block.sh) | 활성 | PASS | — |
| SH-043 | 2 | [fk_payload_composite_default](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/98723aa473cde722abbc729799cf489b7f3f732f/shell/_40_guava/cbrd_26659_fk_payload_composite_default/cases/cbrd_26659_fk_payload_composite_default.sh) | 활성 | PASS | — |
| SH-044 | 2 | [fk_payload_composite_delete_null](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/98723aa473cde722abbc729799cf489b7f3f732f/shell/_40_guava/cbrd_26659_fk_payload_composite_delete_null/cases/cbrd_26659_fk_payload_composite_delete_null.sh) | 활성 | PASS | — |
| SH-045 | 2 | [fk_payload_composite_noaction](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/98723aa473cde722abbc729799cf489b7f3f732f/shell/_40_guava/cbrd_26659_fk_payload_composite_noaction/cases/cbrd_26659_fk_payload_composite_noaction.sh) | 활성 | PASS | — |
| SH-046 | 2 | [fk_payload_composite_restrict](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/98723aa473cde722abbc729799cf489b7f3f732f/shell/_40_guava/cbrd_26659_fk_payload_composite_restrict/cases/cbrd_26659_fk_payload_composite_restrict.sh) | 활성 | PASS | — |
| SH-047 | 2 | [fk_payload_composite_update_null](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/98723aa473cde722abbc729799cf489b7f3f732f/shell/_40_guava/cbrd_26659_fk_payload_composite_update_null/cases/cbrd_26659_fk_payload_composite_update_null.sh) | 활성 | PASS | — |
| SH-048 | 2 | [fk_payload_single_cascade](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/98723aa473cde722abbc729799cf489b7f3f732f/shell/_40_guava/cbrd_26659_fk_payload_single_cascade/cases/cbrd_26659_fk_payload_single_cascade.sh) | 활성 | PASS | — |
| SH-049 | 2 | [fk_payload_single_cascade_block](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/98723aa473cde722abbc729799cf489b7f3f732f/shell/_40_guava/cbrd_26659_fk_payload_single_cascade_block/cases/cbrd_26659_fk_payload_single_cascade_block.sh) | 활성 | PASS | — |
| SH-050 | 2 | [fk_payload_single_default](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/98723aa473cde722abbc729799cf489b7f3f732f/shell/_40_guava/cbrd_26659_fk_payload_single_default/cases/cbrd_26659_fk_payload_single_default.sh) | 활성 | PASS | — |
| SH-051 | 2 | [fk_payload_single_delete_null](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/98723aa473cde722abbc729799cf489b7f3f732f/shell/_40_guava/cbrd_26659_fk_payload_single_delete_null/cases/cbrd_26659_fk_payload_single_delete_null.sh) | 활성 | PASS | — |
| SH-052 | 2 | [fk_payload_single_noaction](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/98723aa473cde722abbc729799cf489b7f3f732f/shell/_40_guava/cbrd_26659_fk_payload_single_noaction/cases/cbrd_26659_fk_payload_single_noaction.sh) | 활성 | PASS | — |
| SH-053 | 2 | [fk_payload_single_restrict](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/98723aa473cde722abbc729799cf489b7f3f732f/shell/_40_guava/cbrd_26659_fk_payload_single_restrict/cases/cbrd_26659_fk_payload_single_restrict.sh) | 활성 | PASS | — |
| SH-054 | 2 | [fk_payload_single_update_null](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/98723aa473cde722abbc729799cf489b7f3f732f/shell/_40_guava/cbrd_26659_fk_payload_single_update_null/cases/cbrd_26659_fk_payload_single_update_null.sh) | 활성 | PASS | — |
| SH-055 | 1·2 | [gap_compact_cs_cs](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/98723aa473cde722abbc729799cf489b7f3f732f/shell/_40_guava/cbrd_26659_gap_compact_cs_cs/cases/cbrd_26659_gap_compact_cs_cs.sh) | 활성 | PASS | — |
| SH-056 | 1·2 | [gap_compact_cs_sc](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/98723aa473cde722abbc729799cf489b7f3f732f/shell/_40_guava/cbrd_26659_gap_compact_cs_sc/cases/cbrd_26659_gap_compact_cs_sc.sh) | 활성 | PASS | — |
| SH-057 | 1·2 | [gap_compact_sa_cs](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/98723aa473cde722abbc729799cf489b7f3f732f/disabled/failing/shell/_40_guava/cbrd_26659_gap_compact_sa_cs/cases/cbrd_26659_gap_compact_sa_cs.sh.disabled) | **disabled** | 미실행 | 기능 검사 FAIL · 28.774초 |
| SH-058 | 1·2 | [gap_compact_sa_sc](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/98723aa473cde722abbc729799cf489b7f3f732f/shell/_40_guava/cbrd_26659_gap_compact_sa_sc/cases/cbrd_26659_gap_compact_sa_sc.sh) | 활성 | PASS | — |
| SH-059 | 2 | [gap_ctas_cs](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/98723aa473cde722abbc729799cf489b7f3f732f/disabled/failing/shell/_40_guava/cbrd_26659_gap_ctas_cs/cases/cbrd_26659_gap_ctas_cs.sh.disabled) | **disabled** | 미실행 | 기능 검사 FAIL · 35.715초 |
| SH-060 | 2 | [gap_ctas_sc](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/98723aa473cde722abbc729799cf489b7f3f732f/disabled/failing/shell/_40_guava/cbrd_26659_gap_ctas_sc/cases/cbrd_26659_gap_ctas_sc.sh.disabled) | **disabled** | 미실행 | 기능 검사 FAIL · 19.610초 |
| SH-061 | 1·2 | [gap_load_cs_cs](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/98723aa473cde722abbc729799cf489b7f3f732f/disabled/failing/shell/_40_guava/cbrd_26659_gap_load_cs_cs/cases/cbrd_26659_gap_load_cs_cs.sh.disabled) | **disabled** | 미실행 | 기능 검사 FAIL · 37.429초 |
| SH-062 | 1·2 | [gap_load_cs_sc](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/98723aa473cde722abbc729799cf489b7f3f732f/disabled/failing/shell/_40_guava/cbrd_26659_gap_load_cs_sc/cases/cbrd_26659_gap_load_cs_sc.sh.disabled) | **disabled** | 미실행 | 기능 검사 FAIL · 24.320초 |
| SH-063 | 1·2 | [gap_load_sa_cs](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/98723aa473cde722abbc729799cf489b7f3f732f/disabled/failing/shell/_40_guava/cbrd_26659_gap_load_sa_cs/cases/cbrd_26659_gap_load_sa_cs.sh.disabled) | **disabled** | 미실행 | 기능 검사 FAIL · 44.750초 |
| SH-064 | 1·2 | [gap_load_sa_nolog_cs](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/98723aa473cde722abbc729799cf489b7f3f732f/disabled/failing/shell/_40_guava/cbrd_26659_gap_load_sa_nolog_cs/cases/cbrd_26659_gap_load_sa_nolog_cs.sh.disabled) | **disabled** | 미실행 | 기능 검사 FAIL · 28.089초 |
| SH-065 | 1·2 | [gap_load_sa_nolog_sc](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/98723aa473cde722abbc729799cf489b7f3f732f/disabled/failing/shell/_40_guava/cbrd_26659_gap_load_sa_nolog_sc/cases/cbrd_26659_gap_load_sa_nolog_sc.sh.disabled) | **disabled** | 미실행 | 기능 검사 FAIL · 43.871초 |
| SH-066 | 1·2 | [gap_load_sa_sc](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/98723aa473cde722abbc729799cf489b7f3f732f/disabled/failing/shell/_40_guava/cbrd_26659_gap_load_sa_sc/cases/cbrd_26659_gap_load_sa_sc.sh.disabled) | **disabled** | 미실행 | 기능 검사 FAIL · 27.929초 |
| SH-067 | 2·5 | [gap_recreate](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/98723aa473cde722abbc729799cf489b7f3f732f/shell/_40_guava/cbrd_26659_gap_recreate/cases/cbrd_26659_gap_recreate.sh) | 활성 | PASS | — |
| SH-068 | 2 | [gap_replace_select_cs](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/98723aa473cde722abbc729799cf489b7f3f732f/disabled/failing/shell/_40_guava/cbrd_26659_gap_replace_select_cs/cases/cbrd_26659_gap_replace_select_cs.sh.disabled) | **disabled** | 미실행 | 기능 검사 FAIL · 20.137초 |
| SH-069 | 2 | [gap_replace_select_sc](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/98723aa473cde722abbc729799cf489b7f3f732f/disabled/failing/shell/_40_guava/cbrd_26659_gap_replace_select_sc/cases/cbrd_26659_gap_replace_select_sc.sh.disabled) | **disabled** | 미실행 | 기능 검사 FAIL · 19.754초 |
| SH-070 | 1·2 | [gap_unload_sa_cs](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/98723aa473cde722abbc729799cf489b7f3f732f/disabled/failing/shell/_40_guava/cbrd_26659_gap_unload_sa_cs/cases/cbrd_26659_gap_unload_sa_cs.sh.disabled) | **disabled** | 미실행 | 기능 검사 FAIL · 26.275초 |
| SH-071 | 1·2 | [gap_unload_sa_sc](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/98723aa473cde722abbc729799cf489b7f3f732f/disabled/failing/shell/_40_guava/cbrd_26659_gap_unload_sa_sc/cases/cbrd_26659_gap_unload_sa_sc.sh.disabled) | **disabled** | 미실행 | 기능 검사 FAIL · 26.372초 |
| SH-072 | 1·2 | [jdbc_storage](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/98723aa473cde722abbc729799cf489b7f3f732f/shell/_40_guava/cbrd_26659_jdbc_storage/cases/cbrd_26659_jdbc_storage.sh) | 활성 | PASS | — |
| SH-073 | 6 | [large_keys](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/98723aa473cde722abbc729799cf489b7f3f732f/disabled/long_running/shell/_40_guava/cbrd_26659_large_keys/cases/cbrd_26659_large_keys.sh.disabled) | **disabled** | 미실행 | 60초 초과만 · 당시 PASS · 381.773초 |
| SH-074 | 2 | [lob_locators](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/98723aa473cde722abbc729799cf489b7f3f732f/shell/_40_guava/cbrd_26659_lob_locators/cases/cbrd_26659_lob_locators.sh) | 활성 | PASS | — |
| SH-075 | 2·5 | [notify_abort](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/98723aa473cde722abbc729799cf489b7f3f732f/disabled/failing/shell/_40_guava/cbrd_26659_notify_abort/cases/cbrd_26659_notify_abort.sh.disabled) | **disabled** | 미실행 | 기능 검사 FAIL · 1.615초 |
| SH-076 | 2·5 | [notify_commit](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/98723aa473cde722abbc729799cf489b7f3f732f/disabled/failing/shell/_40_guava/cbrd_26659_notify_commit/cases/cbrd_26659_notify_commit.sh.disabled) | **disabled** | 미실행 | 기능 검사 FAIL · 17.025초 |
| SH-077 | 2·5 | [notify_nodrop](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/98723aa473cde722abbc729799cf489b7f3f732f/disabled/failing/shell/_40_guava/cbrd_26659_notify_nodrop/cases/cbrd_26659_notify_nodrop.sh.disabled) | **disabled** | 미실행 | 기능 검사 FAIL · 1.603초 |
| SH-078 | 2·5 | [owner_drop](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/98723aa473cde722abbc729799cf489b7f3f732f/shell/_40_guava/cbrd_26659_owner_drop/cases/cbrd_26659_owner_drop.sh) | 활성 | PASS | — |
| SH-079 | 2 | [partition_add_drop_list](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/98723aa473cde722abbc729799cf489b7f3f732f/disabled/failing/shell/_40_guava/cbrd_26659_partition_add_drop_list/cases/cbrd_26659_partition_add_drop_list.sh.disabled) | **disabled** | 미실행 | 기능 검사 FAIL · 39.417초 |
| SH-080 | 2 | [partition_add_drop_range](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/98723aa473cde722abbc729799cf489b7f3f732f/disabled/failing/shell/_40_guava/cbrd_26659_partition_add_drop_range/cases/cbrd_26659_partition_add_drop_range.sh.disabled) | **disabled** | 미실행 | 기능 검사 FAIL · 55.311초 |
| SH-081 | 2 | [partition_hash_coalesce](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/98723aa473cde722abbc729799cf489b7f3f732f/disabled/failing/shell/_40_guava/cbrd_26659_partition_hash_coalesce/cases/cbrd_26659_partition_hash_coalesce.sh.disabled) | **disabled** | 미실행 | 기능 검사 FAIL · 24.926초 |
| SH-082 | 2 | [partition_hash_resize](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/98723aa473cde722abbc729799cf489b7f3f732f/disabled/failing/shell/_40_guava/cbrd_26659_partition_hash_resize/cases/cbrd_26659_partition_hash_resize.sh.disabled) | **disabled** | 미실행 | 기능 검사 FAIL · 9.035초 |
| SH-083 | 2 | [partition_move](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/98723aa473cde722abbc729799cf489b7f3f732f/disabled/failing/shell/_40_guava/cbrd_26659_partition_move/cases/cbrd_26659_partition_move.sh.disabled) | **disabled** | 미실행 | 기능 검사 FAIL · 25.063초 |
| SH-084 | 2 | [partition_owner](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/98723aa473cde722abbc729799cf489b7f3f732f/shell/_40_guava/cbrd_26659_partition_owner/cases/cbrd_26659_partition_owner.sh) | 활성 | PASS | — |
| SH-085 | 2 | [partition_partition_rejection](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/98723aa473cde722abbc729799cf489b7f3f732f/disabled/failing/shell/_40_guava/cbrd_26659_partition_partition_rejection/cases/cbrd_26659_partition_partition_rejection.sh.disabled) | **disabled** | 미실행 | 기능 검사 FAIL · 25.677초 |
| SH-086 | 2 | [partition_promote_list](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/98723aa473cde722abbc729799cf489b7f3f732f/disabled/failing/shell/_40_guava/cbrd_26659_partition_promote_list/cases/cbrd_26659_partition_promote_list.sh.disabled) | **disabled** | 미실행 | 기능 검사 FAIL · 56.639초 |
| SH-087 | 2 | [partition_promote_range](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/98723aa473cde722abbc729799cf489b7f3f732f/disabled/failing/shell/_40_guava/cbrd_26659_partition_promote_range/cases/cbrd_26659_partition_promote_range.sh.disabled) | **disabled** | 미실행 | 기능 검사 FAIL · 56.241초 |
| SH-088 | 2 | [partition_remove](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/98723aa473cde722abbc729799cf489b7f3f732f/disabled/failing/shell/_40_guava/cbrd_26659_partition_remove/cases/cbrd_26659_partition_remove.sh.disabled) | **disabled** | 미실행 | 기능 검사 FAIL · 8.960초 |
| SH-089 | 2 | [partition_reorganize_list](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/98723aa473cde722abbc729799cf489b7f3f732f/disabled/failing/shell/_40_guava/cbrd_26659_partition_reorganize_list/cases/cbrd_26659_partition_reorganize_list.sh.disabled) | **disabled** | 미실행 | 기능 검사 FAIL · 8.556초 |
| SH-090 | 2 | [partition_reorganize_list_merge](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/98723aa473cde722abbc729799cf489b7f3f732f/disabled/failing/shell/_40_guava/cbrd_26659_partition_reorganize_list_merge/cases/cbrd_26659_partition_reorganize_list_merge.sh.disabled) | **disabled** | 미실행 | 기능 검사 FAIL · 9.358초 |
| SH-091 | 2 | [partition_reorganize_range](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/98723aa473cde722abbc729799cf489b7f3f732f/disabled/failing/shell/_40_guava/cbrd_26659_partition_reorganize_range/cases/cbrd_26659_partition_reorganize_range.sh.disabled) | **disabled** | 미실행 | 기능 검사 FAIL · 25.887초 |
| SH-092 | 2 | [partition_reorganize_range_merge](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/98723aa473cde722abbc729799cf489b7f3f732f/disabled/failing/shell/_40_guava/cbrd_26659_partition_reorganize_range_merge/cases/cbrd_26659_partition_reorganize_range_merge.sh.disabled) | **disabled** | 미실행 | 기능 검사 FAIL · 24.727초 |
| SH-093 | 2 | [partition_repartition](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/98723aa473cde722abbc729799cf489b7f3f732f/disabled/failing/shell/_40_guava/cbrd_26659_partition_repartition/cases/cbrd_26659_partition_repartition.sh.disabled) | **disabled** | 미실행 | 기능 검사 FAIL · 24.690초 |
| SH-094 | 2 | [partition_route_hash](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/98723aa473cde722abbc729799cf489b7f3f732f/disabled/failing/shell/_40_guava/cbrd_26659_partition_route_hash/cases/cbrd_26659_partition_route_hash.sh.disabled) | **disabled** | 미실행 | 기능 검사 FAIL · 26.230초 |
| SH-095 | 2 | [partition_route_list](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/98723aa473cde722abbc729799cf489b7f3f732f/disabled/failing/shell/_40_guava/cbrd_26659_partition_route_list/cases/cbrd_26659_partition_route_list.sh.disabled) | **disabled** | 미실행 | 기능 검사 FAIL · 24.538초 |
| SH-096 | 2 | [partition_route_range](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/98723aa473cde722abbc729799cf489b7f3f732f/disabled/failing/shell/_40_guava/cbrd_26659_partition_route_range/cases/cbrd_26659_partition_route_range.sh.disabled) | **disabled** | 미실행 | 기능 검사 FAIL · 23.872초 |
| SH-097 | 1 | [policy_contract](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/98723aa473cde722abbc729799cf489b7f3f732f/disabled/failing/shell/_40_guava/cbrd_26659_policy_contract/cases/cbrd_26659_policy_contract.sh.disabled) | **disabled** | 미실행 | 기능 검사 FAIL · 17.357초 |
| SH-098 | 5 | [qualified_reuse](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/98723aa473cde722abbc729799cf489b7f3f732f/disabled/failing/shell/_40_guava/cbrd_26659_qualified_reuse/cases/cbrd_26659_qualified_reuse.sh.disabled) | **disabled** | 미실행 | 기능 검사 FAIL · 22.482초 |
| SH-099 | 2 | [read_paths](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/98723aa473cde722abbc729799cf489b7f3f732f/shell/_40_guava/cbrd_26659_read_paths/cases/cbrd_26659_read_paths.sh) | 활성 | PASS | — |
| SH-100 | 2 | [record_flags](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/98723aa473cde722abbc729799cf489b7f3f732f/shell/_40_guava/cbrd_26659_record_flags/cases/cbrd_26659_record_flags.sh) | 활성 | PASS | — |
| SH-101 | 4·6 | [record_keys](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/98723aa473cde722abbc729799cf489b7f3f732f/shell/_40_guava/cbrd_26659_record_keys/cases/cbrd_26659_record_keys.sh) | 활성 | **FAIL** | — |
| SH-102 | 4 | [record_layout](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/98723aa473cde722abbc729799cf489b7f3f732f/shell/_40_guava/cbrd_26659_record_layout/cases/cbrd_26659_record_layout.sh) | 활성 | **FAIL** | — |
| SH-103 | 4 | [record_residual](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/98723aa473cde722abbc729799cf489b7f3f732f/shell/_40_guava/cbrd_26659_record_residual/cases/cbrd_26659_record_residual.sh) | 활성 | **FAIL** | — |
| SH-104 | 4 | [record_target0](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/98723aa473cde722abbc729799cf489b7f3f732f/disabled/failing/shell/_40_guava/cbrd_26659_record_target0/cases/cbrd_26659_record_target0.sh.disabled) | **disabled** | 미실행 | 기능 검사 FAIL · 7.867초 |
| SH-105 | 4 | [record_target10](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/98723aa473cde722abbc729799cf489b7f3f732f/disabled/failing/shell/_40_guava/cbrd_26659_record_target10/cases/cbrd_26659_record_target10.sh.disabled) | **disabled** | 미실행 | 기능 검사 FAIL · 22.644초 |
| SH-106 | 4 | [representation_chunks](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/98723aa473cde722abbc729799cf489b7f3f732f/shell/_40_guava/cbrd_26659_representation_chunks/cases/cbrd_26659_representation_chunks.sh) | 활성 | PASS | — |
| SH-107 | 2 | [schema_attributes_cs](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/98723aa473cde722abbc729799cf489b7f3f732f/disabled/failing/shell/_40_guava/cbrd_26659_schema_attributes_cs/cases/cbrd_26659_schema_attributes_cs.sh.disabled) | **disabled** | 미실행 | 기능 검사 FAIL · 20.820초 |
| SH-108 | 2 | [schema_attributes_sa](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/98723aa473cde722abbc729799cf489b7f3f732f/disabled/failing/shell/_40_guava/cbrd_26659_schema_attributes_sa/cases/cbrd_26659_schema_attributes_sa.sh.disabled) | **disabled** | 미실행 | 기능 검사 FAIL · 21.308초 |
| SH-109 | 2 | [schema_cs](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/98723aa473cde722abbc729799cf489b7f3f732f/shell/_40_guava/cbrd_26659_schema_cs/cases/cbrd_26659_schema_cs.sh) | 활성 | PASS | — |
| SH-110 | 1·2·4 | [schema_policy](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/98723aa473cde722abbc729799cf489b7f3f732f/shell/_40_guava/cbrd_26659_schema_policy/cases/cbrd_26659_schema_policy.sh) | 활성 | PASS | — |
| SH-111 | 2 | [schema_rewrites_cs](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/98723aa473cde722abbc729799cf489b7f3f732f/disabled/failing/shell/_40_guava/cbrd_26659_schema_rewrites_cs/cases/cbrd_26659_schema_rewrites_cs.sh.disabled) | **disabled** | 미실행 | 기능 검사 FAIL · 20.186초 |
| SH-112 | 2 | [schema_rewrites_sa](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/98723aa473cde722abbc729799cf489b7f3f732f/disabled/long_running/shell/_40_guava/cbrd_26659_schema_rewrites_sa/cases/cbrd_26659_schema_rewrites_sa.sh.disabled) | **disabled** | 미실행 | 기능 검사 FAIL + 60초 초과 · 94.311초 |
| SH-113 | 2 | [schema_sa](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/98723aa473cde722abbc729799cf489b7f3f732f/disabled/long_running/shell/_40_guava/cbrd_26659_schema_sa/cases/cbrd_26659_schema_sa.sh.disabled) | **disabled** | 미실행 | 60초 초과만 · 당시 PASS · 81.389초 |
| SH-114 | 4 | [serialized_chunks](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/98723aa473cde722abbc729799cf489b7f3f732f/disabled/failing/shell/_40_guava/cbrd_26659_serialized_chunks/cases/cbrd_26659_serialized_chunks.sh.disabled) | **disabled** | 미실행 | 기능 검사 FAIL · 21.250초 |
| SH-115 | 1 | [show_contract](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/98723aa473cde722abbc729799cf489b7f3f732f/disabled/failing/shell/_40_guava/cbrd_26659_show_contract/cases/cbrd_26659_show_contract.sh.disabled) | **disabled** | 미실행 | 기능 검사 FAIL · 1.482초 |
| SH-116 | 1·2 | [show_partitions](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/98723aa473cde722abbc729799cf489b7f3f732f/disabled/failing/shell/_40_guava/cbrd_26659_show_partitions/cases/cbrd_26659_show_partitions.sh.disabled) | **disabled** | 미실행 | 기능 검사 FAIL · 1.480초 |
| SH-117 | 2·5 | [snapshot_visibility](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/98723aa473cde722abbc729799cf489b7f3f732f/shell/_40_guava/cbrd_26659_snapshot_visibility/cases/cbrd_26659_snapshot_visibility.sh) | 활성 | PASS | — |
| SH-118 | 5 | [snapshots_reclaim](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/98723aa473cde722abbc729799cf489b7f3f732f/disabled/failing/shell/_40_guava/cbrd_26659_snapshots_reclaim/cases/cbrd_26659_snapshots_reclaim.sh.disabled) | **disabled** | 미실행 | 기능 검사 FAIL · 18.640초 |
| SH-119 | 2 | [tde_crash_committed](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/98723aa473cde722abbc729799cf489b7f3f732f/disabled/failing/shell/_40_guava/cbrd_26659_tde_crash_committed/cases/cbrd_26659_tde_crash_committed.sh.disabled) | **disabled** | 미실행 | 기능 검사 FAIL · 6.079초 |
| SH-120 | 2 | [tde_crash_undo](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/98723aa473cde722abbc729799cf489b7f3f732f/disabled/failing/shell/_40_guava/cbrd_26659_tde_crash_undo/cases/cbrd_26659_tde_crash_undo.sh.disabled) | **disabled** | 미실행 | 기능 검사 FAIL · 6.076초 |
| SH-121 | 2 | [tde_storage](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/98723aa473cde722abbc729799cf489b7f3f732f/disabled/failing/shell/_40_guava/cbrd_26659_tde_storage/cases/cbrd_26659_tde_storage.sh.disabled) | **disabled** | 미실행 | 기능 검사 FAIL · 7.274초 |
| SH-122 | 2 | [tde_wal](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/98723aa473cde722abbc729799cf489b7f3f732f/shell/_40_guava/cbrd_26659_tde_wal/cases/cbrd_26659_tde_wal.sh) | 활성 | PASS | — |
| SH-123 | 2 | [transactions](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/98723aa473cde722abbc729799cf489b7f3f732f/shell/_40_guava/cbrd_26659_transactions/cases/cbrd_26659_transactions.sh) | 활성 | PASS | — |
| SH-124 | 1·2 | [utility_compact_cs](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/98723aa473cde722abbc729799cf489b7f3f732f/disabled/failing/shell/_40_guava/cbrd_26659_utility_compact_cs/cases/cbrd_26659_utility_compact_cs.sh.disabled) | **disabled** | 미실행 | 기능 검사 FAIL · 21.124초 |
| SH-125 | 1·2 | [utility_compact_sa](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/98723aa473cde722abbc729799cf489b7f3f732f/disabled/failing/shell/_40_guava/cbrd_26659_utility_compact_sa/cases/cbrd_26659_utility_compact_sa.sh.disabled) | **disabled** | 미실행 | 기능 검사 FAIL · 21.659초 |
| SH-126 | 1·2 | [utility_cs](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/98723aa473cde722abbc729799cf489b7f3f732f/shell/_40_guava/cbrd_26659_utility_cs/cases/cbrd_26659_utility_cs.sh) | 활성 | PASS | — |
| SH-127 | 1·2 | [utility_policy_cs](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/98723aa473cde722abbc729799cf489b7f3f732f/disabled/failing/shell/_40_guava/cbrd_26659_utility_policy_cs/cases/cbrd_26659_utility_policy_cs.sh.disabled) | **disabled** | 미실행 | 기능 검사 FAIL · 22.137초 |
| SH-128 | 1·2 | [utility_policy_sa](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/98723aa473cde722abbc729799cf489b7f3f732f/disabled/failing/shell/_40_guava/cbrd_26659_utility_policy_sa/cases/cbrd_26659_utility_policy_sa.sh.disabled) | **disabled** | 미실행 | 기능 검사 FAIL · 22.454초 |
| SH-129 | 1·2 | [utility_policy_sa_nolog](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/98723aa473cde722abbc729799cf489b7f3f732f/disabled/failing/shell/_40_guava/cbrd_26659_utility_policy_sa_nolog/cases/cbrd_26659_utility_policy_sa_nolog.sh.disabled) | **disabled** | 미실행 | 기능 검사 FAIL · 20.604초 |
| SH-130 | 1·2 | [utility_policy_unload_sa](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/98723aa473cde722abbc729799cf489b7f3f732f/disabled/failing/shell/_40_guava/cbrd_26659_utility_policy_unload_sa/cases/cbrd_26659_utility_policy_unload_sa.sh.disabled) | **disabled** | 미실행 | 기능 검사 FAIL · 20.858초 |
| SH-131 | 1·2 | [utility_sa](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/98723aa473cde722abbc729799cf489b7f3f732f/shell/_40_guava/cbrd_26659_utility_sa/cases/cbrd_26659_utility_sa.sh) | 활성 | PASS | — |
| SH-132 | 1·2 | [utility_sa_physical](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/98723aa473cde722abbc729799cf489b7f3f732f/shell/_40_guava/cbrd_26659_utility_sa_physical/cases/cbrd_26659_utility_sa_physical.sh) | 활성 | PASS | — |
| SH-133 | 2·5 | [cbrd_27237_rollback_vacuum](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/98723aa473cde722abbc729799cf489b7f3f732f/disabled/failing/shell/_40_guava/cbrd_27237_rollback_vacuum/cases/cbrd_27237_rollback_vacuum.sh.disabled) | **disabled** | 미실행 | 기능 검사 FAIL · 11.066초 |

<br>

### C++ 보완 14함수

보완 함수 14개가 현재 PR에 정확히 보존된 것을 확인했습니다. 아래는 함수 존재와 검사 의도의 목록이며 최신 PASS 목록이 아닙니다. SQL·shell 비활성 수와 합산하지 않습니다.

| 번호 | 대응 항목 | 함수 원문 | 검사 내용 | 현재 실행 결과 |
| --- | --- | --- | --- | --- |
| UT-01 | 3·4 | [OosBoundaries.ExactChunkCapacityAndOneByteOverStoreOneAndTwoChunks](https://github.com/CUBRID/cubrid/blob/e3589ae42d42b04eb020e1ae43e165b01d31b12a/unit_tests/oos/test_oos_boundaries.cpp#L68) | raw chunk 용량과 +1B·실제 chunk 수·전체 재구성 | 미대조 |
| UT-02 | 3·4 | [OosBoundaries.CallerLengthOneByteEitherSideRejectsAndPreservesStoredBytes](https://github.com/CUBRID/cubrid/blob/e3589ae42d42b04eb020e1ae43e165b01d31b12a/unit_tests/oos/test_oos_boundaries.cpp#L122) | 호출 길이 ±1B 거부·기존 저장 값 보존 | 미대조 |
| UT-03 | 3·4 | [OosBoundaries.InsertLengthNarrowingGuardOnlyRejectsWithoutTouchingExistingChain](https://github.com/CUBRID/cubrid/blob/e3589ae42d42b04eb020e1ae43e165b01d31b12a/unit_tests/oos/test_oos_boundaries.cpp#L156) | INT_MAX 초과 길이 guard·기존 chain 보존 | 미대조 |
| UT-04 | 3·4 | [OosBoundaries.InlineLengthEndpointsAreParserGuardsOnly](https://github.com/CUBRID/cubrid/blob/e3589ae42d42b04eb020e1ae43e165b01d31b12a/unit_tests/oos/test_oos_boundaries.cpp#L185) | stub 길이 endpoint parser guard만 검증 | 미대조 |
| UT-05 | 3·4 | [OosBoundaries.EveryVotWidthRequiresExactlyOneStubWithinFieldAndRecord](https://github.com/CUBRID/cubrid/blob/e3589ae42d42b04eb020e1ae43e165b01d31b12a/unit_tests/oos/test_oos_boundaries.cpp#L217) | VOT 폭별 field/record 범위와 정확한 stub | 미대조 |
| UT-06 | 3·4 | [OosBoundaries.StubWriterUsesValueCursorAndRetriesAtExactCapacity](https://github.com/CUBRID/cubrid/blob/e3589ae42d42b04eb020e1ae43e165b01d31b12a/unit_tests/oos/test_oos_boundaries.cpp#L251) | 실제 value cursor·exact capacity·재시도 | 미대조 |
| UT-07 | 3·4 | [OosBoundaries.StubWriterOffsetEntryOneByteShortChangesNothing](https://github.com/CUBRID/cubrid/blob/e3589ae42d42b04eb020e1ae43e165b01d31b12a/unit_tests/oos/test_oos_boundaries.cpp#L288) | offset entry 한 byte 부족·무변경 | 미대조 |
| UT-08 | 3·4 | [OosBoundaries.StoredVotBoundariesAndExpandedValuesPreserveMixedRows](https://github.com/CUBRID/cubrid/blob/e3589ae42d42b04eb020e1ae43e165b01d31b12a/unit_tests/oos/test_oos_boundaries.cpp#L303) | 실제 저장 VOT·Expand 뒤 혼합 row 보존 | 미대조 |
| UT-09 | 3·4 | [OosBoundaries.NonOosShortIntVotBoundaryPreservesCompleteValues](https://github.com/CUBRID/cubrid/blob/e3589ae42d42b04eb020e1ae43e165b01d31b12a/unit_tests/oos/test_oos_boundaries.cpp#L393) | non-OOS SHORT/INT VOT·전체 값 | 미대조 |
| UT-10 | 3 | [OosSqlVisibleVersion.StoredAndExpandedFetchPreserveMixedRowsAndCallerOwnedBytes](https://github.com/CUBRID/cubrid/blob/e3589ae42d42b04eb020e1ae43e165b01d31b12a/unit_tests/oos/sql/test_oos_sql_visible_version.cpp#L196) | stored/expanded fetch·호출자 소유 byte 수명 | 미대조 |
| UT-11 | 3·4 | [OosSqlVisibleVersion.ExpandRetryPreservesCallerBufferAndStoredReference](https://github.com/CUBRID/cubrid/blob/e3589ae42d42b04eb020e1ae43e165b01d31b12a/unit_tests/oos/sql/test_oos_sql_visible_version.cpp#L305) | Expand 재시도·호출자 버퍼·저장 참조 | 미대조 |
| UT-12 | 3·5 | [OosFileDestroyServerTest.SystemWorkerUndoDefersPageReturnAndAbortRestoresTheChain](https://github.com/CUBRID/cubrid/blob/e3589ae42d42b04eb020e1ae43e165b01d31b12a/unit_tests/oos/test_oos_remove_file_server.cpp#L292) | system-worker undo horizon·abort 후 chain 복원 | 미대조 |
| UT-13 | 3·5 | [OosSqlOwnership.UnassignedUpdateRetainsWholeStubAcrossCommitAndAbort](https://github.com/CUBRID/cubrid/blob/e3589ae42d42b04eb020e1ae43e165b01d31b12a/unit_tests/oos/sql/test_oos_sql_ownership.cpp#L128) | 미할당 stub 전체 identity·commit/abort 소유권 | 미대조 |
| UT-14 | 3 | [OosSqlOwnership.ExistingOosFileReceivesClassAesAndPreservesIdentityAndValues](https://github.com/CUBRID/cubrid/blob/e3589ae42d42b04eb020e1ae43e165b01d31b12a/unit_tests/oos/sql/test_oos_sql_ownership.cpp#L163) | 기존 파일의 class AES 적용·identity/값 보존 | 미대조 |

UT-13의 할당하지 않은 OOS 값 보존은 [CBRD-27230](https://jira.cubrid.org/browse/CBRD-27230)과 관련되며 **develop 병합 이후 TODO로 확정**했습니다. 이번 병합 전 새 검토 요청으로 추가하지 않습니다.


<br><br>

## 이전 리비전 기록

아래 기록은 이전 Engine `c4c4f5c5`, public `4f6557f`, private `8486abd`와 과거 실행에 한정됩니다. **당시 shell 69개 PASS를 현재 결과로 해석하지 않습니다.** 현재 판정은 위의 66 PASS·3 FAIL입니다. 기존 원문·실험 경로·참고 문서와 결론을 보존했습니다.

<details>
<summary>이전 보완 과정과 실행 기록 펼치기</summary>

# OOS 테스트 보완 결과와 피드백별 TC 대응표

작성일: 2026-10-27, Asia/Seoul. 보고 대상: 팀장 및 OOS TC 검토자.
대상: [Engine PR #8128](https://github.com/CUBRID/cubrid/pull/8128), [SQL TC PR #3688](https://github.com/CUBRID/cubrid-testcases/pull/3688), [Shell TC PR #4365](https://github.com/CUBRID/cubrid-testcases-private-ex/pull/4365).

기존 OOS TC에 대한 피드백을 여섯 검증 영역으로 정리하고, 각 영역에 대응하는 TC와 현재 실행 상태를 연결했다. SQL 28개와 shell 133개의 전체 목록을 부록에 수록했다. 이 수는 기존 TC를 포함한 현재 보유 수이며, 이번 보완으로 새로 추가한 수가 아니다. C++는 기존 내부 계약의 유지 범위와 보완한 개별 테스트를 별도로 설명한다.

**현재 활성 SQL 25개가 포함된 SQL CI job과 활성 OOS shell 69개의 실행은 PASS다. SQL 3개와 shell 64개는 실패 또는 60초 초과 실행으로 비활성화되어 있다. 따라서 활성 선택의 CI 통과와 피드백 전체의 검증 완료는 구분해야 한다.** 비활성 FAIL은 통과 커버리지에 포함하지 않으며, 필수 항목별 독립 검증이 남아 있어 전체 Work456은 미완료다.

[대화형 OOS TC 탐색기](https://dev2.baboon-rudd.ts.net:8443/home/vimkim/.agent/diagrams/cbrd-26659-oos-tc-explorer.html)에서 피드백·종류·기능 분류·결과·활성/비활성·관측 run·실행 시간·텍스트로 목록을 필터링하고 정렬할 수 있다. 행을 선택하면 TC 원문, SQL answer, 관련 controller/fixture와 실행 리비전을 읽을 수 있으며, 필터 결과를 CSV로 내보낼 수 있다. SQL 28개·shell 133개와 별도의 C++ 보완 함수 14개를 수록했다. 비공개 TC 원본을 내장한 약 2 MB의 내부 공유용 HTML이며, 파일을 내려받아 오프라인으로도 사용할 수 있다. HTML과 내장 소스는 공개 Git 저장소 밖에서 보관한다.

## 1. 피드백별 대응 요약

| 항목 | 피드백과 보완 내용 | TC를 찾을 위치 | 현재 판단 |
| --- | --- | --- | --- |
| ① 구문·의미·SHOW·유틸리티 | STORAGE 정책의 정상·오류 구문, 의미/문맥 오류, SHOW 대상·권한, load/unload/compact 시 정책·값 보존 | SQL-08·27; SH-097·110·115·116 및 3절 유틸리티 표 | 기본 SQL과 일부 유틸리티는 활성. 확장 정책·SHOW·정책 roundtrip의 실패 사례가 남아 있음 |
| ② 사용자 연산과 OOS 유무 | 실제 저장 레코드의 `HAS_OOS` set/clear, 읽기·복사·DML·트리거·트랜잭션·스키마·파티션·FK | SQL-01–03·05–07·09·12–17·19–23·26; SH-100을 포함한 4절 연산별 표 | 다수 활성 PASS. 파티션·복사·소유권 등의 비활성 사례와 요구 셀별 검증이 남아 있음 |
| ③ C++ 내부 검증과 중복 정리 | SQL 결과만으로 확인할 수 없는 Expand, 버퍼 경계, identity, 소유권, fault, SA/SERVER 계약 보존·보완 | UT-01–14 및 5절의 기존 C++ 모듈 표 | 기존 실행 증거와 신규 계약을 구분해 유지. 최신 CI의 C++ 전체 검증 완료는 주장하지 않음 |
| ④ 경계·limit+1 | 직렬화 크기, chunk, VOT, stub/buffer, record target·bigone, key-overflow 경계 | SQL-04·10·11·18·24·27·28; SH-101–106·110·114; UT-01–09·11 | 활성 검증과 별도로 target·직렬화·오류 경계의 비활성 사례가 있음. guard-only 한계를 명시 |
| ⑤ 저장 효율·회수·불리한 시나리오 | 반복 INSERT/DELETE·INSERT/UPDATE/DELETE, abort/retry, snapshot, restart, 페이지 회수·재사용·단편화 | SH-009·010·012–017·067·075–078·098·117·118·133; UT-12·13 및 reclaim 모듈 | 핵심 churn·reclaim·notification 회귀가 비활성. 저장 효율·단편화 검증 완료로 보고할 수 없음 |
| ⑥ 큰 OOS PK/UNIQUE | 실제 indexed attribute의 OOS 여부, 단일·복합 키, build/maintenance, 중복·NULL·FK·rollback | SQL-10·25·26; SH-004·027–040·073·101 | 기능 TC를 제공함. 종합 shell TC SH-073은 관측 PASS지만 381.773초로 비활성. 성능 비교는 보류 |

위 표의 번호는 다음 부록의 실제 파일과 연결된다. `SQL-01`–`SQL-28`, `SH-001`–`SH-133`, `UT-01`–`UT-14`는 **이 보고서의 조회용 번호**다. CI가 발급한 전역 TC 번호나 구현 티켓 번호가 아니다. SQL과 shell은 원래 진입점 경로를 정렬해 번호를 부여했고, 링크는 검토한 커밋의 실제 파일을 가리킨다. 같은 TC가 여러 항목에 대응할 수 있으므로 항목별 수는 합산하지 않는다.

| 항목 | 대응 SQL 수 | 대응 shell 수 | shell 활성 PASS / 비활성 | C++ 보완 함수 수 |
| --- | ---: | ---: | --- | ---: |
| ① 구문·의미·SHOW·유틸리티 | 2 | 27 | 9 / 18 | 0 |
| ② 사용자 연산·상태 | 19 | 117 | 65 / 52 | 0 |
| ③ C++ 내부 계약 | 0 | 0 | 해당 없음 | 14 |
| ④ 경계 | 7 | 8 | 5 / 3 | 10 |
| ⑤ 저장 효율·회수 | 0 | 17 | 5 / 12 | 2 |
| ⑥ 큰 PK/UNIQUE | 3 | 17 | 16 / 1 | 0 |

수는 부록의 항목 표시를 집계한 대응 TC 수다. C++ 열은 새로 보완한 14개 중 해당 항목에 배정한 수이며, 기존 유지 모듈 수나 최신 PASS 수가 아니다. 0은 그 종류에 새 TC를 배정하지 않았다는 뜻이며 요구사항이 없다는 뜻이 아니다.

## 2. 검토 리비전과 실행 결과

| 구분 | 검토 기준 |
| --- | --- |
| Engine | `c4c4f5c5ed55fb0130c72bb261061ec441662554` |
| Public TC | `4f6557f7f96ac789e1697ef8b27dd8bf2807802e`, `tc/pr-8128` |
| Private TC | `8486abdac52ffc1ea4cae3c8a28fad888014caea`, `tc/pr-8128` |
| CI runner/CTP | `7dc9f4192bb96988d1bab78df3e45df88628b814` |
| 보완 범위 | [승인된 보완 spec](supplement-spec-work456-20261021.md), [연산·상태 요구 목록](supplement-operation-inventory-work456-20261021.md) |
| 분류 기준 | 값의 크기 대신 실제 저장 레코드의 `HAS_OOS` set/clear 사용. 크기는 경계 시험에서만 별도 사용 |
| PR 상태 | 2026-10-27 확인 시 두 TC PR 모두 OPEN, Ready for review, base `feature/oos-merge` |

| 실행 | 입력과 결과 | 이 보고서에서 인정하는 범위 |
| --- | --- | --- |
| [Full CI 40324320840](https://github.com/CUBRID/cubrid/actions/runs/40324320840) | Engine `c4c4f5c5`, public `4f6557f`, private `10fb4b63f`. Build·SQL·medium PASS, shell FAIL 2건으로 run 전체 FAIL | 현재 public TC의 SQL job PASS. SQL 25개 각각의 독립 oracle·물리 상태 완료 판정은 이 job 상태로 대체하지 않음 |
| [Shell-only CI 40335925801](https://github.com/CUBRID/cubrid/actions/runs/40335925801) | Engine `c4c4f5c5`, private `8486abd`, build·shell PASS. 41분 49초, 50개 shell shard PASS | 전체 shell 3,523 PASS / 0 FAIL / 30 SKIP / 미실행 0. 활성 OOS 69개는 모두 실행·PASS, skip 0. 비활성 OOS 64개는 실행 목록에 없음. 활성 OOS 최대 45.180초 |

최신 실행은 shell만 재실행했다. SQL·medium PASS는 앞선 full run의 결과로 유지되며, 하나의 동일 입력 full run이 모두 PASS한 것으로 합치지 않는다. 별도의 handover native 실행, SA-loaddb 및 deferred-write 결과도 합산하지 않는다. 최신 shell은 해당 source의 기존 release/debug build artifact를 재사용했고, actual input은 workflow plan/build 증거에서 확인했다.

대화형 목록을 위한 추가 대조(2026-10-27)에서는 run `40324320840`의 SQL shard 09 전체 462개에 대해 summary/JUnit의 identity·결과·시간, `tc.read`의 public `4f6557f`, `build.read`의 Engine `c4c4f5c5`, 실행 완료 기록을 확인했다. 이 범위에서 활성 OOS SQL 25개는 각각 PASS이며 개별 실행 시간도 HTML에 표시한다. SQL 전체 collector는 다른 shard 01의 결과/JUnit 수 불일치로 여전히 미완료다. 이 한정 대조는 전체 SQL 수집 완료나 필수 독립 oracle·물리 상태 검증 완료를 뜻하지 않는다.

현재 [SQL 비활성 목록](https://github.com/CUBRID/cubrid-testcases/blob/4f6557f7f96ac789e1697ef8b27dd8bf2807802e/disabled/README.md)은 실패 3개다. [Shell 비활성 목록](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/8486abdac52ffc1ea4cae3c8a28fad888014caea/disabled/README.md)은 관측 FAIL 61개와 60초 초과 8개, 중복 5개를 제외한 64개다. 이 중 FAIL 없이 장시간만으로 제외된 것은 3개다. 비활성화 시 TC 본문·assertion·expected answer를 바꾸지 않았다. Shell 실행 helper는 C++17·Bash/jq를 사용하며 Python helper를 요구하지 않는다.

## 3. 항목 ① 구문·의미·SHOW·유틸리티

기존 `storage_policy` SQL에 추가 구문·오류 사례를 보완했다. SQL 오류 결과와 shell의 오류 메시지·스키마·저장 상태 보존을 나누어 검사하도록 구성했다. shell 확장 계약의 현재 FAIL은 원인 분석 전 엔진 결함으로 일괄 분류하지 않는다.

| 세부 요구 | 대응 TC | 검사 내용과 현재 상태 |
| --- | --- | --- |
| 정책 구문·식별자·위치·정상/오류 DDL | SQL-08·27, SH-097·110 | DEFAULT/PREFER_INLINE/FORCE_OUTLINE 등 정책, 잘못된·반복된 절, 부적합 도메인·class/shared 문맥, ALTER·복사 정책. SQL 2개와 SH-110 활성, SH-097 FAIL로 비활성 |
| 오류 단계와 변경 방지 | SQL-08, SH-097 | grammar/semantic/context 오류 구분, 실패 후 정확한 DDL·기존 값·저장 레코드 유지. SH-097의 전체 계약은 현재 통과 증거 없음 |
| SHOW 대상·권한·파티션 | SH-072·115·116 | SHOW HEAP OOS/ALL, 유효·잘못된 대상, 일반 사용자 거부와 DBA 허용, 객체/파티션 귀속. SH-072 활성 PASS; 확장 계약 SH-115·116은 FAIL로 비활성 |
| 일반 unload/load·backup/restore | SH-011·126·131·132 | 소유한 DB의 값·스키마·파일 귀속, 복사 후 source 제거 및 복원. 4개 활성 PASS; 이 결과가 모든 정책·모드 조합을 대체하지는 않음 |
| 정책별 CS/SA load/unload | SH-061–066·070·071·127–130 | ALTER 후 정책과 기존 저장 상태가 다른 source를 unload/load하고 목적지 정책·값·상태를 확인. 12개 모두 FAIL로 비활성 |
| compactdb와 상태 전환 | SH-055–058·124·125 | CS/SA compact의 clear→set/set→clear 및 정책 roundtrip. SH-055·056·058 활성 PASS; SH-057·124·125 FAIL로 비활성 |

현재 보고할 수 있는 결론은 “구문·의미 검사 및 유틸리티별 보완 TC를 제공했고 기본 활성 선택을 통과했다”이다. SHOW 확장 계약과 정책별 유틸리티의 전체 통과는 남은 작업이다. 기존 상세 근거는 [정책](ticket02-policy-contract-20261021.md), [SHOW](ticket03-show-contract-20261021.md), [유틸리티](ticket04-utility-policy-roundtrips-20261021.md) 보고서의 각 리비전에 한정된다.

## 4. 항목 ② 사용자 연산과 HAS_OOS set/clear

clear는 **저장 레코드가 존재하면서 `HAS_OOS`가 해제된 상태**이고, set은 플래그가 설정된 상태다. 삭제된 행이나 아직 저장되지 않은 결과는 clear로 계산하지 않는다. INSERT는 ∅→clear/set, UPDATE는 적용 가능한 clear→clear·clear→set·set→clear·set→set, 복사는 source와 destination 상태를 각각 검사하도록 요구한다.

| 연산군 | 대응 TC | 검사 내용과 현재 상태 |
| --- | --- | --- |
| 실제 레코드 관찰·가시성 | SH-100, SQL-09 | 물리 슬롯과 값·행 ID를 연결하고 실제 flag와 일반 SELECT의 가시성을 구분. SH-100 활성 PASS; SQL-09는 해당 JDBC invocation의 레코드 검사도 포함 |
| 읽기·관계 연산·JDBC·LOB | SQL-09·22·23, SH-072·074·099 | 전체 값과 서로 다른 tail, JOIN/subquery/CTE, 집합 연산·중복·정렬, client bytes, 복사 후 source 제거. 모두 활성. LOB payload와 OOS locator 저장은 분리 |
| INSERT/UPDATE/DELETE·제약·트랜잭션·트리거 | SQL-05·15–17·19–21, SH-018–026·123 | 전체 row model, 상태 전환, 실패 원자성, COMMIT/ROLLBACK/SAVEPOINT와 trigger side effect. shell 9개 활성 PASS; SH-022는 관측 PASS이나 101.085초로 비활성 |
| MERGE/REPLACE/중복 키 UPDATE | SQL-01–03, SH-001–010·068·069 | hit/miss, VALUES/SET/SELECT, survivor·error·rollback, 할당하지 않은 stub의 유지. SH-001–008 활성 PASS; SH-009·010·068·069 FAIL로 비활성 |
| 스키마 변경·물질화 | SQL-12–14, SH-107–113 | ADD/DROP/MODIFY/CHANGE/재작성 후 값·정책·상태와 파일 귀속. SH-109·110 활성 PASS; 4개 FAIL, SH-113은 PASS이나 81.389초로 비활성 |
| CTAS·재생성 | SH-059·060·067 | source/destination 상태를 따로 확인하고 source 제거 뒤 survivor 검증. SH-067 활성 PASS; CTAS 교차 상태 SH-059·060 FAIL로 비활성 |
| 파티션 routing/movement/reorganization | SQL-06·07, SH-079–096 | 논리 routing과 실제 child heap의 소유권을 구분. SQL 2개 활성, SH-084만 활성 PASS. 나머지 shell 17개 FAIL로 비활성 |
| 일반 FK와 OOS 키 FK | SQL-26, SH-027–054 | 단일·복합, 기본 동작/RESTRICT/NO ACTION/CASCADE/SET NULL 및 차단된 cascade, 부모·자식의 정확한 값·상태. shell 28개 모두 활성 PASS |
| snapshot·복구·TDE·소유권 | SH-011·016·017·075–078·117–122·133 | old/new reader, committed/undo crash, notification·borrowed chain, TDE 파일/WAL, rollback 후 vacuum. 활성·비활성은 부록에 개별 표시 |

위 대응표는 연산별 TC의 검사 범위를 나타낸다. **모든 지원 연산 × 모든 적용 가능한 상태 셀을 독립 증거로 대조 완료했다는 뜻은 아니다.** SQL 값 비교만 있는 TC에 별도 shell fixture의 물리 증거를 붙여 같은 실행의 OOS 검증으로 계산하지 않는다. 미실행 phase와 불명확한 기대는 완료를 막는다. [연산 요구 목록](supplement-operation-inventory-work456-20261021.md)의 O01 이하 행은 요구사항 지도이며, 과거 PASS 상태표로 재해석하지 않는다.

## 5. 항목 ③ C++ 내부 검증과 중복 정리

기존 인벤토리는 source `1ef86a7`의 29개 binary·302개 GTest 선언을 대상으로 했다. [C++ read/Expand 검증 보고서](ticket14-cpp-read-expand-buffer-20261021.md)의 native baseline에서 302개가 discovery·started·XML과 일치해 PASS했다. 이는 해당 source의 과거 증거다. 최신 Engine `c4c4f5c5`와 별도 SA-loaddb/deferred-write 실행 결과를 여기에 더하지 않는다.

SQL의 반환값이 같아도 내부 Expand 회피, 그룹 읽기, 버퍼 수명, 잘못된 참조, allocation fault 및 SA/SERVER별 계약은 남는다. 기존 보완 단계에서는 동등한 대체 assertion이 검증되지 않은 테스트를 유지했다. 따라서 “SQL과 겹쳐 보이는 C++ 테스트를 모두 삭제했다”고 보고하지 않는다.

| 유지하는 계약 | 실제 C++ 모듈 | SQL만으로 대체할 수 없는 부분 |
| --- | --- | --- |
| 값 읽기와 Expand | `test_oos_sql_crud`, `test_oos_sql_visible_version`, `test_oos`, `test_oos_server` | grouped Resolve·cheap fetch·whole-record Expand 회피, 호출자 버퍼 |
| 정책·DDL·오류·SA 실행 | `test_oos_sql_storage`, `test_oos_sql_show`, `test_oos_sql_ddl`, `test_oos_sql_bigone`, `test_oos_sql_boundary` | 내부 배치·오류 시점과 SA 실행 계약 |
| 버퍼·직렬화·stale reference | `test_byte_span_writer`, `test_oos_boundaries`, `test_oos_identity_stamp`, `test_oos_record_flags` | byte 단위 범위, parser guard, 슬롯 재사용, identity와 metadata flag |
| DELETE·rollback·eager cleanup | `test_oos_sql_delete`, `test_oos_sql_update_delete`, `test_oos_sql_txn`, `test_oos_sql_eager_cleanup`, `test_oos_eager_diagnostics`, `test_oos_delete`, `test_oos_delete_server`, `test_oos_sql_ownership` | 동기 정리, 오류 stack·진단, 실제 chain/stub 보존 |
| 회수·힌트·horizon | `test_oos_bestspace`, `test_oos_growth_sweep`, `test_oos_remove_file`, `test_oos_remove_file_server`, `test_oos_mock_vacuum_server`, `test_oos_vacuum_server`, `test_oos_real_vacuum_server` | cache/cursor, active writer, page return과 chunk delete의 구별. mock은 실제 vacuum 완료를 대체하지 않음 |
| 복구·logging·TDE 분류 | `test_oos_sql_crash_recovery`, `test_oos_no_logging`, `test_oos_tde_gate` | 실제 모드·복구, no-logging의 보장 범위, recovery index 분류. TDE 분류만으로 암호문 검증을 대체하지 않음 |

Work456의 C++ 보완 14개는 [부록 C](#부록-c-c-보완-tc-14개)에 함수 이름까지 제시했다. UT-01–09는 경계 9개, UT-10·11은 read/Expand 버퍼 2개, UT-12–14는 system-worker undo·소유권·기존 파일 TDE 3개다. 이 14개는 보완 테스트의 수이며 PASS 수가 아니다. 특히 unassigned UPDATE의 stub 보존 실패는 [별도 소유권 검증 보고서](ticket15-identity-ownership-rollback-reclaim-20261021.md)에 보존되어 있다.

최신 CI가 SQL/shell/medium을 통과했다는 사실로 현재 C++ 필수 선택 전체의 완료를 선언하지 않는다. [기존 C++ 인벤토리](supplement-cpp-inventory-work456-20261021.md)와 각 티켓의 정확한 실행 리비전을 기준으로 최종 대조가 필요하다.

## 6. 항목 ④ 경계와 limit+1

| 경계 | 대응 TC | 기대와 증거의 한계 |
| --- | --- | --- |
| 24B stub 대비 직렬화 이득 | SQL-11·27, SH-106·110 | 직렬화 24B와 다음 가능한 28B, NULL/empty·정책을 비교. 입력 문자 수와 직렬화 byte 수를 구분 |
| 단일·다중 chunk 용량 | SQL-04, SH-106·114, UT-01·02 | 16KiB 구성의 payload 16,280B와 raw +1B. SQL encoding은 정렬 때문에 다음 직렬화 크기가 16,284B. SH-114 FAIL로 비활성 |
| BYTE/SHORT/INT VOT | SQL-28, SH-106, UT-05·08·09 | 숫자 상한과 정렬된 전후 layout을 구분하고 모든 값 보존. 큰 입력만으로 저장 VOT 폭을 추정하지 않음 |
| stub·버퍼 exact/short capacity | UT-04–07·11, 기존 `test_byte_span_writer` | 유효 field/record 범위, exact capacity, 한 byte 부족·overflow 및 재시도 시 원본 보존 |
| 길이 parser·narrowing guard | UT-03·04 | 최대 표현 길이와 초과 입력의 거부. 실제 최대 크기 저장·할당 시험이 아닌 guard-only 검증 |
| 물리 record target와 unfill 독립성 | SH-104·105, UT-08·09 | 승인된 four-record target와 정렬된 이웃을 검사. SH-104·105는 FAIL로 비활성이므로 target 준수 완료 증거 없음 |
| residual record·OOS+bigone·최대 LOB 열 | SQL-10·18·24, SH-102·103 | 경계 이웃·거부·기존 row/stub/WAL 보존. shell 2개는 활성 PASS, SQL 3개는 FAIL로 비활성 |
| B-tree key-overflow 경계 | SQL-10, SH-101 | heap OOS와 B-tree overflow를 분리. 경계를 넘을 때 overflow로 저장되는 정상 경로를 무조건 오류로 기대하지 않음. SH-101 활성 PASS |

경계의 기대는 [승인 spec](supplement-spec-work456-20261021.md)과 [직렬화·chunk·guard 보고서](ticket11-serialization-chunk-guard-boundaries-20261021.md), [record/key 경계 보고서](ticket12-physical-record-key-boundaries-20261021.md)에 연결한다. 현재 비활성 경계의 과거 PASS로 최신 실패를 덮지 않는다.

## 7. 항목 ⑤ 저장 효율·회수·불리한 시나리오

| 시나리오 | 대응 TC | 현재 상태와 보고 범위 |
| --- | --- | --- |
| INSERT/DELETE 반복 | SH-013 | 83.570초, FAIL·장시간 비활성 |
| INSERT/UPDATE/DELETE 반복 | SH-014 | 90.506초, FAIL·장시간 비활성 |
| abort/retry 후 survivor | SH-012 | 83.614초, FAIL·장시간 비활성 |
| restart와 재사용 | SH-015·098 | 각각 FAIL로 비활성. SH-015는 94.797초로 장시간 조건도 해당 |
| old/new reader·page return | SH-117·118 | 가시성 SH-117 활성 PASS. 회수 SH-118 FAIL로 비활성. 읽기 성공을 page return 성공으로 계산하지 않음 |
| commit/abort notification과 whole-stub 유지 | SH-009·010·075–077·133, UT-12·13 | shell 모두 FAIL로 비활성. rollback 후 실제 vacuum survivor와 소유권을 분리해서 추적 |
| DROP/recreate·독립 survivor | SH-067·078 | 활성 PASS. 특정 파일 수명·생존 값 증거이며 churn·단편화 전체를 대체하지 않음 |
| committed/undo crash | SH-016·017 | 활성 PASS. 복구의 특정 시나리오이며 반복 회수 성능·HA 증거로 확대하지 않음 |

TC는 같은 live data 상태의 survivor 값, OOS chunk/page·소유 파일, 회수 후 재사용 및 fresh-equivalent 비교를 검사하도록 구성했다. **핵심 반복 workload와 회수 회귀가 현재 비활성 상태이므로 불필요한 volume 증가가 없거나 단편화 문제가 해결됐다고 결론내릴 수 없다.** 기존 [churn·reclaim 보고서](ticket13-churn-reclaim-reuse-20261021.md)의 실행된 cycle과 실패·미실행 phase를 원래 리비전에서 유지한다. 성능 비교나 속도 기준은 이번 항목의 완료 판정에 추가하지 않는다.

## 8. 항목 ⑥ 큰 OOS PK/UNIQUE 기능

| 세부 범위 | 대응 TC | 현재 상태 |
| --- | --- | --- |
| 큰 key의 PK maintenance·UNIQUE build·tail 구분·중복/NULL 오류 | SQL-25 | 활성 SQL job PASS. 해당 SQL 실행의 indexed attribute 물리 증거는 별도로 대조해야 함 |
| 실제 OOS PK에서 MERGE/REPLACE/중복 키 UPDATE·rollback·index plan | SH-004 | 활성 PASS. 전체 값·clear/set와 실제 index 경로를 검사 |
| OOS key FK 단일·복합 및 action/차단 | SQL-26, SH-027–040 | shell 14개 활성 PASS. SH-041–054의 14개는 일반 key+OOS payload 대조군이며 OOS key 자체의 검증과 구분 |
| type×policy×PK/UNIQUE×build/maintain×단일/복합 종합 선택 | SH-073 | 관측 PASS, 381.773초로 비활성. 현재 정규 CI가 이 종합 선택을 실행했다고 보고하지 않음 |
| key-overflow 경계·물리 귀속 | SQL-10, SH-101 | SH-101 활성 PASS, SQL-10 FAIL로 비활성. heap OOS·B-tree key overflow를 따로 관찰 |

SH-073의 상세 phase 목록은 [required_phases.json](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/8486abdac52ffc1ea4cae3c8a28fad888014caea/shell/_40_guava/cbrd_26659_large_keys/cases/required_phases.json)에 있다. [기존 큰 키 보고서](ticket09-large-indexed-oos-keys-20261021.md)와 [FK 보고서](ticket10-fk-actions-and-large-keys-20261021.md)는 각 native 실행의 source·TC·oracle에 한정한다. **기능 결과로 성능 저하가 없다고 결론내리지 않는다. 성능 비교와 HA Work463은 계속 보류한다.**

## 9. 남은 작업과 보고 판단

팀장에게 보고할 현재 상태는 “피드백별 TC를 보완·분류해 PR에 게시했고, 활성 SQL CI job 및 OOS shell 69개가 통과해 리뷰를 요청한 단계”다. 최종 수용 판단에는 비활성 FAIL의 원인·별도 수정 연결, 장시간 TC의 실행 경로, 요구사항별 독립 oracle 및 필수 phase 실행 대조가 남아 있다. 현재 실패를 일괄 엔진 결함으로 확정하거나, 미실행을 PASS로 분류하지 않는다.

두 TC PR은 Ready for review다. 현재 base `feature/oos-merge`에는 자동 TC Merge Gate check가 보고되지 않는다. 이 상태를 gate PASS로 해석하지 않으며, TC PR의 검토·병합·closure·branch 삭제는 사람이 진행한다.

아래 부록은 현재 파일을 찾기 위한 전체 대응 목록이다. 상태가 **비활성 FAIL**인 TC는 검사 의도를 보존한 회귀 자산이고, 현재 정상 동작을 입증하는 커버리지는 아니다. 비활성 PASS는 시간 초과 기준으로 정규 선택에서 빠진 과거 관측이다.

## 부록 A SQL TC 28개

TC 이름은 공통 접두사 `cbrd_26659_oos_` 와 `.sql` 을 생략했다. 각 이름은 실제 파일에, `answer` 는 같은 선택의 기대값 파일에 연결된다. 활성 25개는 SQL job PASS 선택에 포함된 목록이며, 이 표에서 개별 독립 검증 완료로 승격하지 않는다. 비활성 3개의 FAIL 관측은 run A에 해당한다.

| 번호 | TC 이름과 기대값 | 대응 항목 | 현재 선택 | 검사 내용 |
| --- | --- | --- | --- | --- |
| SQL-01 | [alt_duplicate](https://github.com/CUBRID/cubrid-testcases/blob/4f6557f7f96ac789e1697ef8b27dd8bf2807802e/sql/_36_guava/cbrd_26659/cases/cbrd_26659_oos_alt_duplicate.sql) · [answer](https://github.com/CUBRID/cubrid-testcases/blob/4f6557f7f96ac789e1697ef8b27dd8bf2807802e/sql/_36_guava/cbrd_26659/answers/cbrd_26659_oos_alt_duplicate.answer) | ② | 활성 | 중복 키 hit/miss·할당 값·오류 후 모델 |
| SQL-02 | [alt_merge](https://github.com/CUBRID/cubrid-testcases/blob/4f6557f7f96ac789e1697ef8b27dd8bf2807802e/sql/_36_guava/cbrd_26659/cases/cbrd_26659_oos_alt_merge.sql) · [answer](https://github.com/CUBRID/cubrid-testcases/blob/4f6557f7f96ac789e1697ef8b27dd8bf2807802e/sql/_36_guava/cbrd_26659/answers/cbrd_26659_oos_alt_merge.answer) | ② | 활성 | MERGE match/update·unmatched/insert 모델 |
| SQL-03 | [alt_replace](https://github.com/CUBRID/cubrid-testcases/blob/4f6557f7f96ac789e1697ef8b27dd8bf2807802e/sql/_36_guava/cbrd_26659/cases/cbrd_26659_oos_alt_replace.sql) · [answer](https://github.com/CUBRID/cubrid-testcases/blob/4f6557f7f96ac789e1697ef8b27dd8bf2807802e/sql/_36_guava/cbrd_26659/answers/cbrd_26659_oos_alt_replace.answer) | ② | 활성 | REPLACE VALUES/SET/SELECT와 survivor |
| SQL-04 | [chunk_boundaries](https://github.com/CUBRID/cubrid-testcases/blob/4f6557f7f96ac789e1697ef8b27dd8bf2807802e/sql/_36_guava/cbrd_26659/cases/cbrd_26659_oos_chunk_boundaries.sql) · [answer](https://github.com/CUBRID/cubrid-testcases/blob/4f6557f7f96ac789e1697ef8b27dd8bf2807802e/sql/_36_guava/cbrd_26659/answers/cbrd_26659_oos_chunk_boundaries.answer) | ④ | 활성 | 직렬화 chunk 전후 이웃과 전체 값 |
| SQL-05 | [dml_forms](https://github.com/CUBRID/cubrid-testcases/blob/4f6557f7f96ac789e1697ef8b27dd8bf2807802e/sql/_36_guava/cbrd_26659/cases/cbrd_26659_oos_dml_forms.sql) · [answer](https://github.com/CUBRID/cubrid-testcases/blob/4f6557f7f96ac789e1697ef8b27dd8bf2807802e/sql/_36_guava/cbrd_26659/answers/cbrd_26659_oos_dml_forms.answer) | ② | 활성 | INSERT SET/default/식/subquery·joined UPDATE |
| SQL-06 | [partition](https://github.com/CUBRID/cubrid-testcases/blob/4f6557f7f96ac789e1697ef8b27dd8bf2807802e/sql/_36_guava/cbrd_26659/cases/cbrd_26659_oos_partition.sql) · [answer](https://github.com/CUBRID/cubrid-testcases/blob/4f6557f7f96ac789e1697ef8b27dd8bf2807802e/sql/_36_guava/cbrd_26659/answers/cbrd_26659_oos_partition.answer) | ② | 활성 | 논리 이동·재구성·행과 전체 값 |
| SQL-07 | [partition_routing](https://github.com/CUBRID/cubrid-testcases/blob/4f6557f7f96ac789e1697ef8b27dd8bf2807802e/sql/_36_guava/cbrd_26659/cases/cbrd_26659_oos_partition_routing.sql) · [answer](https://github.com/CUBRID/cubrid-testcases/blob/4f6557f7f96ac789e1697ef8b27dd8bf2807802e/sql/_36_guava/cbrd_26659/answers/cbrd_26659_oos_partition_routing.answer) | ② | 활성 | 초기 routing·읽기·중복 거부 |
| SQL-08 | [policy_syntax](https://github.com/CUBRID/cubrid-testcases/blob/4f6557f7f96ac789e1697ef8b27dd8bf2807802e/sql/_36_guava/cbrd_26659/cases/cbrd_26659_oos_policy_syntax.sql) · [answer](https://github.com/CUBRID/cubrid-testcases/blob/4f6557f7f96ac789e1697ef8b27dd8bf2807802e/sql/_36_guava/cbrd_26659/answers/cbrd_26659_oos_policy_syntax.answer) | ① | 활성 | 정책 구문·문맥·도메인·식별자 오류 |
| SQL-09 | [read_relations](https://github.com/CUBRID/cubrid-testcases/blob/4f6557f7f96ac789e1697ef8b27dd8bf2807802e/sql/_36_guava/cbrd_26659/cases/cbrd_26659_oos_read_relations.sql) · [answer](https://github.com/CUBRID/cubrid-testcases/blob/4f6557f7f96ac789e1697ef8b27dd8bf2807802e/sql/_36_guava/cbrd_26659/answers/cbrd_26659_oos_read_relations.answer) | ② | 활성 | 전체 값·집합/중복·복사·해당 실행의 레코드 flag |
| SQL-10 | [record_boundaries](https://github.com/CUBRID/cubrid-testcases/blob/4f6557f7f96ac789e1697ef8b27dd8bf2807802e/disabled/failing/sql/_36_guava/cbrd_26659/cases/cbrd_26659_oos_record_boundaries.sql.disabled) · [answer](https://github.com/CUBRID/cubrid-testcases/blob/4f6557f7f96ac789e1697ef8b27dd8bf2807802e/disabled/failing/sql/_36_guava/cbrd_26659/answers/cbrd_26659_oos_record_boundaries.answer) | ④·⑥ | 비활성 FAIL | 잔여 record·거부·key-overflow 경계 |
| SQL-11 | [representation](https://github.com/CUBRID/cubrid-testcases/blob/4f6557f7f96ac789e1697ef8b27dd8bf2807802e/sql/_36_guava/cbrd_26659/cases/cbrd_26659_oos_representation.sql) · [answer](https://github.com/CUBRID/cubrid-testcases/blob/4f6557f7f96ac789e1697ef8b27dd8bf2807802e/sql/_36_guava/cbrd_26659/answers/cbrd_26659_oos_representation.answer) | ④ | 활성 | 정책·NULL/empty·직렬화 표현 |
| SQL-12 | [schema](https://github.com/CUBRID/cubrid-testcases/blob/4f6557f7f96ac789e1697ef8b27dd8bf2807802e/sql/_36_guava/cbrd_26659/cases/cbrd_26659_oos_schema.sql) · [answer](https://github.com/CUBRID/cubrid-testcases/blob/4f6557f7f96ac789e1697ef8b27dd8bf2807802e/sql/_36_guava/cbrd_26659/answers/cbrd_26659_oos_schema.answer) | ② | 활성 | 스키마 변경 뒤 값·메타데이터 |
| SQL-13 | [schema_materialize](https://github.com/CUBRID/cubrid-testcases/blob/4f6557f7f96ac789e1697ef8b27dd8bf2807802e/sql/_36_guava/cbrd_26659/cases/cbrd_26659_oos_schema_materialize.sql) · [answer](https://github.com/CUBRID/cubrid-testcases/blob/4f6557f7f96ac789e1697ef8b27dd8bf2807802e/sql/_36_guava/cbrd_26659/answers/cbrd_26659_oos_schema_materialize.answer) | ② | 활성 | ALTER hard-default 물질화·실패 보존 |
| SQL-14 | [schema_rewrites](https://github.com/CUBRID/cubrid-testcases/blob/4f6557f7f96ac789e1697ef8b27dd8bf2807802e/sql/_36_guava/cbrd_26659/cases/cbrd_26659_oos_schema_rewrites.sql) · [answer](https://github.com/CUBRID/cubrid-testcases/blob/4f6557f7f96ac789e1697ef8b27dd8bf2807802e/sql/_36_guava/cbrd_26659/answers/cbrd_26659_oos_schema_rewrites.answer) | ② | 활성 | 혼합 레코드의 스키마 재작성 값 |
| SQL-15 | [sql01_insert_select](https://github.com/CUBRID/cubrid-testcases/blob/4f6557f7f96ac789e1697ef8b27dd8bf2807802e/sql/_36_guava/cbrd_26659/cases/cbrd_26659_oos_sql01_insert_select.sql) · [answer](https://github.com/CUBRID/cubrid-testcases/blob/4f6557f7f96ac789e1697ef8b27dd8bf2807802e/sql/_36_guava/cbrd_26659/answers/cbrd_26659_oos_sql01_insert_select.answer) | ② | 활성 | INSERT·bulk/source-copy의 독립 값 모델 |
| SQL-16 | [sql04_delete](https://github.com/CUBRID/cubrid-testcases/blob/4f6557f7f96ac789e1697ef8b27dd8bf2807802e/sql/_36_guava/cbrd_26659/cases/cbrd_26659_oos_sql04_delete.sql) · [answer](https://github.com/CUBRID/cubrid-testcases/blob/4f6557f7f96ac789e1697ef8b27dd8bf2807802e/sql/_36_guava/cbrd_26659/answers/cbrd_26659_oos_sql04_delete.answer) | ② | 활성 | 선택/전체 DELETE·survivor·재삽입 |
| SQL-17 | [sql04_update](https://github.com/CUBRID/cubrid-testcases/blob/4f6557f7f96ac789e1697ef8b27dd8bf2807802e/sql/_36_guava/cbrd_26659/cases/cbrd_26659_oos_sql04_update.sql) · [answer](https://github.com/CUBRID/cubrid-testcases/blob/4f6557f7f96ac789e1697ef8b27dd8bf2807802e/sql/_36_guava/cbrd_26659/answers/cbrd_26659_oos_sql04_update.answer) | ② | 활성 | 할당/미할당 UPDATE·전체 post-image |
| SQL-18 | [sql05_bigone](https://github.com/CUBRID/cubrid-testcases/blob/4f6557f7f96ac789e1697ef8b27dd8bf2807802e/disabled/failing/sql/_36_guava/cbrd_26659/cases/cbrd_26659_oos_sql05_bigone.sql.disabled) · [answer](https://github.com/CUBRID/cubrid-testcases/blob/4f6557f7f96ac789e1697ef8b27dd8bf2807802e/disabled/failing/sql/_36_guava/cbrd_26659/answers/cbrd_26659_oos_sql05_bigone.answer) | ④ | 비활성 FAIL | OOS+bigone 거부·ordinary bigone 대조 |
| SQL-19 | [sql05_constraints](https://github.com/CUBRID/cubrid-testcases/blob/4f6557f7f96ac789e1697ef8b27dd8bf2807802e/sql/_36_guava/cbrd_26659/cases/cbrd_26659_oos_sql05_constraints.sql) · [answer](https://github.com/CUBRID/cubrid-testcases/blob/4f6557f7f96ac789e1697ef8b27dd8bf2807802e/sql/_36_guava/cbrd_26659/answers/cbrd_26659_oos_sql05_constraints.answer) | ② | 활성 | NOT NULL·PK/UNIQUE·실패 원자성·view check |
| SQL-20 | [sql05_transactions](https://github.com/CUBRID/cubrid-testcases/blob/4f6557f7f96ac789e1697ef8b27dd8bf2807802e/sql/_36_guava/cbrd_26659/cases/cbrd_26659_oos_sql05_transactions.sql) · [answer](https://github.com/CUBRID/cubrid-testcases/blob/4f6557f7f96ac789e1697ef8b27dd8bf2807802e/sql/_36_guava/cbrd_26659/answers/cbrd_26659_oos_sql05_transactions.answer) | ② | 활성 | commit/rollback/savepoint·오류 후 정상 DML |
| SQL-21 | [sql06_triggers](https://github.com/CUBRID/cubrid-testcases/blob/4f6557f7f96ac789e1697ef8b27dd8bf2807802e/sql/_36_guava/cbrd_26659/cases/cbrd_26659_oos_sql06_triggers.sql) · [answer](https://github.com/CUBRID/cubrid-testcases/blob/4f6557f7f96ac789e1697ef8b27dd8bf2807802e/sql/_36_guava/cbrd_26659/answers/cbrd_26659_oos_sql06_triggers.answer) | ② | 활성 | trigger 로그/mirror·거부·정확한 값 |
| SQL-22 | [sql07_read_paths](https://github.com/CUBRID/cubrid-testcases/blob/4f6557f7f96ac789e1697ef8b27dd8bf2807802e/sql/_36_guava/cbrd_26659/cases/cbrd_26659_oos_sql07_read_paths.sql) · [answer](https://github.com/CUBRID/cubrid-testcases/blob/4f6557f7f96ac789e1697ef8b27dd8bf2807802e/sql/_36_guava/cbrd_26659/answers/cbrd_26659_oos_sql07_read_paths.answer) | ② | 활성 | heap/index·관계 연산·복사 전체 값 |
| SQL-23 | [sql09_lob_copy](https://github.com/CUBRID/cubrid-testcases/blob/4f6557f7f96ac789e1697ef8b27dd8bf2807802e/sql/_36_guava/cbrd_26659/cases/cbrd_26659_oos_sql09_lob_copy.sql) · [answer](https://github.com/CUBRID/cubrid-testcases/blob/4f6557f7f96ac789e1697ef8b27dd8bf2807802e/sql/_36_guava/cbrd_26659/answers/cbrd_26659_oos_sql09_lob_copy.answer) | ② | 활성 | LOB 내용·locator·source 제거 후 독립성 |
| SQL-24 | [sql09_lob_maxcols](https://github.com/CUBRID/cubrid-testcases/blob/4f6557f7f96ac789e1697ef8b27dd8bf2807802e/disabled/failing/sql/_36_guava/cbrd_26659/cases/cbrd_26659_oos_sql09_lob_maxcols.sql.disabled) · [answer](https://github.com/CUBRID/cubrid-testcases/blob/4f6557f7f96ac789e1697ef8b27dd8bf2807802e/disabled/failing/sql/_36_guava/cbrd_26659/answers/cbrd_26659_oos_sql09_lob_maxcols.answer) | ④ | 비활성 FAIL | 최대 열 LOB 잔여 record 거부·양성 대조 |
| SQL-25 | [sql18_large_keys](https://github.com/CUBRID/cubrid-testcases/blob/4f6557f7f96ac789e1697ef8b27dd8bf2807802e/sql/_36_guava/cbrd_26659/cases/cbrd_26659_oos_sql18_large_keys.sql) · [answer](https://github.com/CUBRID/cubrid-testcases/blob/4f6557f7f96ac789e1697ef8b27dd8bf2807802e/sql/_36_guava/cbrd_26659/answers/cbrd_26659_oos_sql18_large_keys.answer) | ⑥ | 활성 | 큰 PK 유지·UNIQUE build·tail/오류 모델 |
| SQL-26 | [sql19_fk_actions](https://github.com/CUBRID/cubrid-testcases/blob/4f6557f7f96ac789e1697ef8b27dd8bf2807802e/sql/_36_guava/cbrd_26659/cases/cbrd_26659_oos_sql19_fk_actions.sql) · [answer](https://github.com/CUBRID/cubrid-testcases/blob/4f6557f7f96ac789e1697ef8b27dd8bf2807802e/sql/_36_guava/cbrd_26659/answers/cbrd_26659_oos_sql19_fk_actions.answer) | ②·⑥ | 활성 | 일반/OOS 키 FK action·전체 값 |
| SQL-27 | [storage_policy](https://github.com/CUBRID/cubrid-testcases/blob/4f6557f7f96ac789e1697ef8b27dd8bf2807802e/sql/_36_guava/cbrd_26659/cases/cbrd_26659_oos_storage_policy.sql) · [answer](https://github.com/CUBRID/cubrid-testcases/blob/4f6557f7f96ac789e1697ef8b27dd8bf2807802e/sql/_36_guava/cbrd_26659/answers/cbrd_26659_oos_storage_policy.answer) | ①·④ | 활성 | 정책 metadata·eligibility·이득 경계 |
| SQL-28 | [vot_many_attributes](https://github.com/CUBRID/cubrid-testcases/blob/4f6557f7f96ac789e1697ef8b27dd8bf2807802e/sql/_36_guava/cbrd_26659/cases/cbrd_26659_oos_vot_many_attributes.sql) · [answer](https://github.com/CUBRID/cubrid-testcases/blob/4f6557f7f96ac789e1697ef8b27dd8bf2807802e/sql/_36_guava/cbrd_26659/answers/cbrd_26659_oos_vot_many_attributes.answer) | ④ | 활성 | VOT 이웃·다수 속성·독립 전체 값 |

## 부록 B Shell TC 133개

TC 이름은 공통 접두사 `cbrd_26659_` 와 `.sh` 를 생략했다. 다른 티켓의 `cbrd_27237_rollback_vacuum` 은 이름을 그대로 표시했다. 링크는 비활성화 이동까지 반영한 현재 경로다. 교차 상태 TC 이름의 마지막 `_cs` / `_sc` 는 clear→set/set→clear를 뜻한다. 예를 들어 `gap_compact_cs_sc` 는 CS 모드 compact의 set→clear 검사다.

활성 PASS와 시간은 shell-only run **40335925801** 의 JUnit 실행 관측이다. 비활성 행은 [A: 40311481032](https://github.com/CUBRID/cubrid/actions/runs/40311481032) 또는 [B: 40324320840](https://github.com/CUBRID/cubrid/actions/runs/40324320840)의 개별 관측이다. 각 행의 정확한 당시 TC revision·원본 hash는 [전체 inventory](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/8486abdac52ffc1ea4cae3c8a28fad888014caea/disabled/oos-pr8128-inventory.tsv)에 기록되어 있다. A/B의 결과를 최신 실행의 결과에 합산하지 않는다.

| 번호 | TC 이름 | 대응 항목 | 상태와 개별 실행 시간 | 검사 내용 |
| --- | --- | --- | --- | --- |
| SH-001 | [alt_duplicate_select](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/8486abdac52ffc1ea4cae3c8a28fad888014caea/shell/_40_guava/cbrd_26659_alt_duplicate_select/cases/cbrd_26659_alt_duplicate_select.sh) | ② | 활성 PASS · 17.596초 | MERGE/REPLACE/중복 UPDATE의 독립 모델·상태 |
| SH-002 | [alt_duplicate_set](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/8486abdac52ffc1ea4cae3c8a28fad888014caea/shell/_40_guava/cbrd_26659_alt_duplicate_set/cases/cbrd_26659_alt_duplicate_set.sh) | ② | 활성 PASS · 14.818초 | MERGE/REPLACE/중복 UPDATE의 독립 모델·상태 |
| SH-003 | [alt_duplicate_values](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/8486abdac52ffc1ea4cae3c8a28fad888014caea/shell/_40_guava/cbrd_26659_alt_duplicate_values/cases/cbrd_26659_alt_duplicate_values.sh) | ② | 활성 PASS · 15.126초 | MERGE/REPLACE/중복 UPDATE의 독립 모델·상태 |
| SH-004 | [alt_indexed](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/8486abdac52ffc1ea4cae3c8a28fad888014caea/shell/_40_guava/cbrd_26659_alt_indexed/cases/cbrd_26659_alt_indexed.sh) | ②·⑥ | 활성 PASS · 11.052초 | MERGE/REPLACE/중복 UPDATE의 독립 모델·상태 |
| SH-005 | [alt_merge](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/8486abdac52ffc1ea4cae3c8a28fad888014caea/shell/_40_guava/cbrd_26659_alt_merge/cases/cbrd_26659_alt_merge.sh) | ② | 활성 PASS · 17.953초 | MERGE/REPLACE/중복 UPDATE의 독립 모델·상태 |
| SH-006 | [alt_replace_select](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/8486abdac52ffc1ea4cae3c8a28fad888014caea/shell/_40_guava/cbrd_26659_alt_replace_select/cases/cbrd_26659_alt_replace_select.sh) | ② | 활성 PASS · 28.351초 | MERGE/REPLACE/중복 UPDATE의 독립 모델·상태 |
| SH-007 | [alt_replace_set](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/8486abdac52ffc1ea4cae3c8a28fad888014caea/shell/_40_guava/cbrd_26659_alt_replace_set/cases/cbrd_26659_alt_replace_set.sh) | ② | 활성 PASS · 14.297초 | MERGE/REPLACE/중복 UPDATE의 독립 모델·상태 |
| SH-008 | [alt_replace_values](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/8486abdac52ffc1ea4cae3c8a28fad888014caea/shell/_40_guava/cbrd_26659_alt_replace_values/cases/cbrd_26659_alt_replace_values.sh) | ② | 활성 PASS · 27.039초 | MERGE/REPLACE/중복 UPDATE의 독립 모델·상태 |
| SH-009 | [alt_stub_duplicate](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/8486abdac52ffc1ea4cae3c8a28fad888014caea/disabled/failing/shell/_40_guava/cbrd_26659_alt_stub_duplicate/cases/cbrd_26659_alt_stub_duplicate.sh.disabled) | ②·⑤ | 비활성 FAIL · A 15.505초 | 미할당 전체 24B stub·소유권 보존 |
| SH-010 | [alt_stub_merge](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/8486abdac52ffc1ea4cae3c8a28fad888014caea/disabled/failing/shell/_40_guava/cbrd_26659_alt_stub_merge/cases/cbrd_26659_alt_stub_merge.sh.disabled) | ②·⑤ | 비활성 FAIL · A 16.267초 | 미할당 전체 24B stub·소유권 보존 |
| SH-011 | [backup_restore](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/8486abdac52ffc1ea4cae3c8a28fad888014caea/shell/_40_guava/cbrd_26659_backup_restore/cases/cbrd_26659_backup_restore.sh) | ①·② | 활성 PASS · 18.559초 | backup/restore 후 값·스키마·파일 귀속 |
| SH-012 | [churn_abort_retry](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/8486abdac52ffc1ea4cae3c8a28fad888014caea/disabled/long_running/shell/_40_guava/cbrd_26659_churn_abort_retry/cases/cbrd_26659_churn_abort_retry.sh.disabled) | ⑤ | 비활성 FAIL · A 83.614초 · 장시간 | 독립 반복 workload·survivor·회수·fresh 비교 |
| SH-013 | [churn_insert_delete](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/8486abdac52ffc1ea4cae3c8a28fad888014caea/disabled/long_running/shell/_40_guava/cbrd_26659_churn_insert_delete/cases/cbrd_26659_churn_insert_delete.sh.disabled) | ⑤ | 비활성 FAIL · A 83.570초 · 장시간 | 독립 반복 workload·survivor·회수·fresh 비교 |
| SH-014 | [churn_insert_update_delete](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/8486abdac52ffc1ea4cae3c8a28fad888014caea/disabled/long_running/shell/_40_guava/cbrd_26659_churn_insert_update_delete/cases/cbrd_26659_churn_insert_update_delete.sh.disabled) | ⑤ | 비활성 FAIL · A 90.506초 · 장시간 | 독립 반복 workload·survivor·회수·fresh 비교 |
| SH-015 | [churn_restart](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/8486abdac52ffc1ea4cae3c8a28fad888014caea/disabled/long_running/shell/_40_guava/cbrd_26659_churn_restart/cases/cbrd_26659_churn_restart.sh.disabled) | ⑤ | 비활성 FAIL · A 94.797초 · 장시간 | 독립 반복 workload·survivor·회수·fresh 비교 |
| SH-016 | [crash_committed](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/8486abdac52ffc1ea4cae3c8a28fad888014caea/shell/_40_guava/cbrd_26659_crash_committed/cases/cbrd_26659_crash_committed.sh) | ②·⑤ | 활성 PASS · 22.071초 | acknowledged commit 뒤 crash/redo |
| SH-017 | [crash_undo](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/8486abdac52ffc1ea4cae3c8a28fad888014caea/shell/_40_guava/cbrd_26659_crash_undo/cases/cbrd_26659_crash_undo.sh) | ②·⑤ | 활성 PASS · 11.284초 | 미커밋 writer crash/undo·pre-image |
| SH-018 | [dml_atomicity](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/8486abdac52ffc1ea4cae3c8a28fad888014caea/shell/_40_guava/cbrd_26659_dml_atomicity/cases/cbrd_26659_dml_atomicity.sh) | ② | 활성 PASS · 7.003초 | 실패 원자성·이전 전체 모델 보존 |
| SH-019 | [dml_forms](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/8486abdac52ffc1ea4cae3c8a28fad888014caea/shell/_40_guava/cbrd_26659_dml_forms/cases/cbrd_26659_dml_forms.sh) | ② | 활성 PASS · 21.050초 | INSERT SET/default/식·joined UPDATE |
| SH-020 | [dml_states](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/8486abdac52ffc1ea4cae3c8a28fad888014caea/shell/_40_guava/cbrd_26659_dml_states/cases/cbrd_26659_dml_states.sh) | ② | 활성 PASS · 8.949초 | clear/set 실제 pre/post 전환 |
| SH-021 | [dml_transactions](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/8486abdac52ffc1ea4cae3c8a28fad888014caea/shell/_40_guava/cbrd_26659_dml_transactions/cases/cbrd_26659_dml_transactions.sh) | ② | 활성 PASS · 20.262초 | commit/rollback/savepoint 실제 상태 |
| SH-022 | [dml_transitions](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/8486abdac52ffc1ea4cae3c8a28fad888014caea/disabled/long_running/shell/_40_guava/cbrd_26659_dml_transitions/cases/cbrd_26659_dml_transitions.sh.disabled) | ② | 비활성 PASS · A 101.085초 · 장시간 | SA DML 전체 값·물리 전환 |
| SH-023 | [dml_triggers_delete](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/8486abdac52ffc1ea4cae3c8a28fad888014caea/shell/_40_guava/cbrd_26659_dml_triggers_delete/cases/cbrd_26659_dml_triggers_delete.sh) | ② | 활성 PASS · 17.569초 | DELETE trigger와 mirror/survivor |
| SH-024 | [dml_triggers_insert](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/8486abdac52ffc1ea4cae3c8a28fad888014caea/shell/_40_guava/cbrd_26659_dml_triggers_insert/cases/cbrd_26659_dml_triggers_insert.sh) | ② | 활성 PASS · 5.613초 | INSERT trigger·실제 배치와 값 |
| SH-025 | [dml_triggers_reject](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/8486abdac52ffc1ea4cae3c8a28fad888014caea/shell/_40_guava/cbrd_26659_dml_triggers_reject/cases/cbrd_26659_dml_triggers_reject.sh) | ② | 활성 PASS · 18.318초 | 거부 trigger·변경 방지·후속 성공 |
| SH-026 | [dml_triggers_update](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/8486abdac52ffc1ea4cae3c8a28fad888014caea/shell/_40_guava/cbrd_26659_dml_triggers_update/cases/cbrd_26659_dml_triggers_update.sh) | ② | 활성 PASS · 27.025초 | UPDATE trigger·target/mirror 실제 상태 |
| SH-027 | [fk_key_composite_cascade](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/8486abdac52ffc1ea4cae3c8a28fad888014caea/shell/_40_guava/cbrd_26659_fk_key_composite_cascade/cases/cbrd_26659_fk_key_composite_cascade.sh) | ②·⑥ | 활성 PASS · 16.897초 | OOS key · composite · cascade |
| SH-028 | [fk_key_composite_cascade_block](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/8486abdac52ffc1ea4cae3c8a28fad888014caea/shell/_40_guava/cbrd_26659_fk_key_composite_cascade_block/cases/cbrd_26659_fk_key_composite_cascade_block.sh) | ②·⑥ | 활성 PASS · 23.767초 | OOS key · composite · cascade_block |
| SH-029 | [fk_key_composite_default](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/8486abdac52ffc1ea4cae3c8a28fad888014caea/shell/_40_guava/cbrd_26659_fk_key_composite_default/cases/cbrd_26659_fk_key_composite_default.sh) | ②·⑥ | 활성 PASS · 28.243초 | OOS key · composite · default |
| SH-030 | [fk_key_composite_delete_null](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/8486abdac52ffc1ea4cae3c8a28fad888014caea/shell/_40_guava/cbrd_26659_fk_key_composite_delete_null/cases/cbrd_26659_fk_key_composite_delete_null.sh) | ②·⑥ | 활성 PASS · 28.757초 | OOS key · composite · delete_null |
| SH-031 | [fk_key_composite_noaction](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/8486abdac52ffc1ea4cae3c8a28fad888014caea/shell/_40_guava/cbrd_26659_fk_key_composite_noaction/cases/cbrd_26659_fk_key_composite_noaction.sh) | ②·⑥ | 활성 PASS · 28.466초 | OOS key · composite · noaction |
| SH-032 | [fk_key_composite_restrict](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/8486abdac52ffc1ea4cae3c8a28fad888014caea/shell/_40_guava/cbrd_26659_fk_key_composite_restrict/cases/cbrd_26659_fk_key_composite_restrict.sh) | ②·⑥ | 활성 PASS · 28.555초 | OOS key · composite · restrict |
| SH-033 | [fk_key_composite_update_null](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/8486abdac52ffc1ea4cae3c8a28fad888014caea/shell/_40_guava/cbrd_26659_fk_key_composite_update_null/cases/cbrd_26659_fk_key_composite_update_null.sh) | ②·⑥ | 활성 PASS · 30.198초 | OOS key · composite · update_null |
| SH-034 | [fk_key_single_cascade](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/8486abdac52ffc1ea4cae3c8a28fad888014caea/shell/_40_guava/cbrd_26659_fk_key_single_cascade/cases/cbrd_26659_fk_key_single_cascade.sh) | ②·⑥ | 활성 PASS · 15.849초 | OOS key · single · cascade |
| SH-035 | [fk_key_single_cascade_block](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/8486abdac52ffc1ea4cae3c8a28fad888014caea/shell/_40_guava/cbrd_26659_fk_key_single_cascade_block/cases/cbrd_26659_fk_key_single_cascade_block.sh) | ②·⑥ | 활성 PASS · 25.434초 | OOS key · single · cascade_block |
| SH-036 | [fk_key_single_default](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/8486abdac52ffc1ea4cae3c8a28fad888014caea/shell/_40_guava/cbrd_26659_fk_key_single_default/cases/cbrd_26659_fk_key_single_default.sh) | ②·⑥ | 활성 PASS · 28.787초 | OOS key · single · default |
| SH-037 | [fk_key_single_delete_null](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/8486abdac52ffc1ea4cae3c8a28fad888014caea/shell/_40_guava/cbrd_26659_fk_key_single_delete_null/cases/cbrd_26659_fk_key_single_delete_null.sh) | ②·⑥ | 활성 PASS · 28.915초 | OOS key · single · delete_null |
| SH-038 | [fk_key_single_noaction](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/8486abdac52ffc1ea4cae3c8a28fad888014caea/shell/_40_guava/cbrd_26659_fk_key_single_noaction/cases/cbrd_26659_fk_key_single_noaction.sh) | ②·⑥ | 활성 PASS · 27.507초 | OOS key · single · noaction |
| SH-039 | [fk_key_single_restrict](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/8486abdac52ffc1ea4cae3c8a28fad888014caea/shell/_40_guava/cbrd_26659_fk_key_single_restrict/cases/cbrd_26659_fk_key_single_restrict.sh) | ②·⑥ | 활성 PASS · 27.146초 | OOS key · single · restrict |
| SH-040 | [fk_key_single_update_null](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/8486abdac52ffc1ea4cae3c8a28fad888014caea/shell/_40_guava/cbrd_26659_fk_key_single_update_null/cases/cbrd_26659_fk_key_single_update_null.sh) | ②·⑥ | 활성 PASS · 16.426초 | OOS key · single · update_null |
| SH-041 | [fk_payload_composite_cascade](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/8486abdac52ffc1ea4cae3c8a28fad888014caea/shell/_40_guava/cbrd_26659_fk_payload_composite_cascade/cases/cbrd_26659_fk_payload_composite_cascade.sh) | ② | 활성 PASS · 16.748초 | 일반 key+OOS payload · composite · cascade |
| SH-042 | [fk_payload_composite_cascade_block](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/8486abdac52ffc1ea4cae3c8a28fad888014caea/shell/_40_guava/cbrd_26659_fk_payload_composite_cascade_block/cases/cbrd_26659_fk_payload_composite_cascade_block.sh) | ② | 활성 PASS · 11.564초 | 일반 key+OOS payload · composite · cascade_block |
| SH-043 | [fk_payload_composite_default](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/8486abdac52ffc1ea4cae3c8a28fad888014caea/shell/_40_guava/cbrd_26659_fk_payload_composite_default/cases/cbrd_26659_fk_payload_composite_default.sh) | ② | 활성 PASS · 16.774초 | 일반 key+OOS payload · composite · default |
| SH-044 | [fk_payload_composite_delete_null](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/8486abdac52ffc1ea4cae3c8a28fad888014caea/shell/_40_guava/cbrd_26659_fk_payload_composite_delete_null/cases/cbrd_26659_fk_payload_composite_delete_null.sh) | ② | 활성 PASS · 30.135초 | 일반 key+OOS payload · composite · delete_null |
| SH-045 | [fk_payload_composite_noaction](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/8486abdac52ffc1ea4cae3c8a28fad888014caea/shell/_40_guava/cbrd_26659_fk_payload_composite_noaction/cases/cbrd_26659_fk_payload_composite_noaction.sh) | ② | 활성 PASS · 16.519초 | 일반 key+OOS payload · composite · noaction |
| SH-046 | [fk_payload_composite_restrict](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/8486abdac52ffc1ea4cae3c8a28fad888014caea/shell/_40_guava/cbrd_26659_fk_payload_composite_restrict/cases/cbrd_26659_fk_payload_composite_restrict.sh) | ② | 활성 PASS · 16.865초 | 일반 key+OOS payload · composite · restrict |
| SH-047 | [fk_payload_composite_update_null](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/8486abdac52ffc1ea4cae3c8a28fad888014caea/shell/_40_guava/cbrd_26659_fk_payload_composite_update_null/cases/cbrd_26659_fk_payload_composite_update_null.sh) | ② | 활성 PASS · 29.302초 | 일반 key+OOS payload · composite · update_null |
| SH-048 | [fk_payload_single_cascade](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/8486abdac52ffc1ea4cae3c8a28fad888014caea/shell/_40_guava/cbrd_26659_fk_payload_single_cascade/cases/cbrd_26659_fk_payload_single_cascade.sh) | ② | 활성 PASS · 27.879초 | 일반 key+OOS payload · single · cascade |
| SH-049 | [fk_payload_single_cascade_block](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/8486abdac52ffc1ea4cae3c8a28fad888014caea/shell/_40_guava/cbrd_26659_fk_payload_single_cascade_block/cases/cbrd_26659_fk_payload_single_cascade_block.sh) | ② | 활성 PASS · 11.621초 | 일반 key+OOS payload · single · cascade_block |
| SH-050 | [fk_payload_single_default](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/8486abdac52ffc1ea4cae3c8a28fad888014caea/shell/_40_guava/cbrd_26659_fk_payload_single_default/cases/cbrd_26659_fk_payload_single_default.sh) | ② | 활성 PASS · 28.726초 | 일반 key+OOS payload · single · default |
| SH-051 | [fk_payload_single_delete_null](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/8486abdac52ffc1ea4cae3c8a28fad888014caea/shell/_40_guava/cbrd_26659_fk_payload_single_delete_null/cases/cbrd_26659_fk_payload_single_delete_null.sh) | ② | 활성 PASS · 29.048초 | 일반 key+OOS payload · single · delete_null |
| SH-052 | [fk_payload_single_noaction](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/8486abdac52ffc1ea4cae3c8a28fad888014caea/shell/_40_guava/cbrd_26659_fk_payload_single_noaction/cases/cbrd_26659_fk_payload_single_noaction.sh) | ② | 활성 PASS · 28.665초 | 일반 key+OOS payload · single · noaction |
| SH-053 | [fk_payload_single_restrict](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/8486abdac52ffc1ea4cae3c8a28fad888014caea/shell/_40_guava/cbrd_26659_fk_payload_single_restrict/cases/cbrd_26659_fk_payload_single_restrict.sh) | ② | 활성 PASS · 28.397초 | 일반 key+OOS payload · single · restrict |
| SH-054 | [fk_payload_single_update_null](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/8486abdac52ffc1ea4cae3c8a28fad888014caea/shell/_40_guava/cbrd_26659_fk_payload_single_update_null/cases/cbrd_26659_fk_payload_single_update_null.sh) | ② | 활성 PASS · 16.634초 | 일반 key+OOS payload · single · update_null |
| SH-055 | [gap_compact_cs_cs](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/8486abdac52ffc1ea4cae3c8a28fad888014caea/shell/_40_guava/cbrd_26659_gap_compact_cs_cs/cases/cbrd_26659_gap_compact_cs_cs.sh) | ①·② | 활성 PASS · 21.146초 | compact cs_cs · 전후 실제 상태 |
| SH-056 | [gap_compact_cs_sc](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/8486abdac52ffc1ea4cae3c8a28fad888014caea/shell/_40_guava/cbrd_26659_gap_compact_cs_sc/cases/cbrd_26659_gap_compact_cs_sc.sh) | ①·② | 활성 PASS · 21.478초 | compact cs_sc · 전후 실제 상태 |
| SH-057 | [gap_compact_sa_cs](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/8486abdac52ffc1ea4cae3c8a28fad888014caea/disabled/failing/shell/_40_guava/cbrd_26659_gap_compact_sa_cs/cases/cbrd_26659_gap_compact_sa_cs.sh.disabled) | ①·② | 비활성 FAIL · A 28.774초 | compact sa_cs · 전후 실제 상태 |
| SH-058 | [gap_compact_sa_sc](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/8486abdac52ffc1ea4cae3c8a28fad888014caea/shell/_40_guava/cbrd_26659_gap_compact_sa_sc/cases/cbrd_26659_gap_compact_sa_sc.sh) | ①·② | 활성 PASS · 24.472초 | compact sa_sc · 전후 실제 상태 |
| SH-059 | [gap_ctas_cs](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/8486abdac52ffc1ea4cae3c8a28fad888014caea/disabled/failing/shell/_40_guava/cbrd_26659_gap_ctas_cs/cases/cbrd_26659_gap_ctas_cs.sh.disabled) | ② | 비활성 FAIL · A 35.715초 | CTAS cs · source/destination 별도 상태 |
| SH-060 | [gap_ctas_sc](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/8486abdac52ffc1ea4cae3c8a28fad888014caea/disabled/failing/shell/_40_guava/cbrd_26659_gap_ctas_sc/cases/cbrd_26659_gap_ctas_sc.sh.disabled) | ② | 비활성 FAIL · A 19.610초 | CTAS sc · source/destination 별도 상태 |
| SH-061 | [gap_load_cs_cs](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/8486abdac52ffc1ea4cae3c8a28fad888014caea/disabled/failing/shell/_40_guava/cbrd_26659_gap_load_cs_cs/cases/cbrd_26659_gap_load_cs_cs.sh.disabled) | ①·② | 비활성 FAIL · A 37.429초 | load_cs_cs · 정책·값·목적지 owner |
| SH-062 | [gap_load_cs_sc](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/8486abdac52ffc1ea4cae3c8a28fad888014caea/disabled/failing/shell/_40_guava/cbrd_26659_gap_load_cs_sc/cases/cbrd_26659_gap_load_cs_sc.sh.disabled) | ①·② | 비활성 FAIL · A 24.320초 | load_cs_sc · 정책·값·목적지 owner |
| SH-063 | [gap_load_sa_cs](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/8486abdac52ffc1ea4cae3c8a28fad888014caea/disabled/failing/shell/_40_guava/cbrd_26659_gap_load_sa_cs/cases/cbrd_26659_gap_load_sa_cs.sh.disabled) | ①·② | 비활성 FAIL · A 44.750초 | load_sa_cs · 정책·값·목적지 owner |
| SH-064 | [gap_load_sa_nolog_cs](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/8486abdac52ffc1ea4cae3c8a28fad888014caea/disabled/failing/shell/_40_guava/cbrd_26659_gap_load_sa_nolog_cs/cases/cbrd_26659_gap_load_sa_nolog_cs.sh.disabled) | ①·② | 비활성 FAIL · A 28.089초 | load_sa_nolog_cs · 정책·값·목적지 owner |
| SH-065 | [gap_load_sa_nolog_sc](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/8486abdac52ffc1ea4cae3c8a28fad888014caea/disabled/failing/shell/_40_guava/cbrd_26659_gap_load_sa_nolog_sc/cases/cbrd_26659_gap_load_sa_nolog_sc.sh.disabled) | ①·② | 비활성 FAIL · A 43.871초 | load_sa_nolog_sc · 정책·값·목적지 owner |
| SH-066 | [gap_load_sa_sc](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/8486abdac52ffc1ea4cae3c8a28fad888014caea/disabled/failing/shell/_40_guava/cbrd_26659_gap_load_sa_sc/cases/cbrd_26659_gap_load_sa_sc.sh.disabled) | ①·② | 비활성 FAIL · A 27.929초 | load_sa_sc · 정책·값·목적지 owner |
| SH-067 | [gap_recreate](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/8486abdac52ffc1ea4cae3c8a28fad888014caea/shell/_40_guava/cbrd_26659_gap_recreate/cases/cbrd_26659_gap_recreate.sh) | ②·⑤ | 활성 PASS · 34.196초 | DROP/recreate·새 identity·독립 survivor |
| SH-068 | [gap_replace_select_cs](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/8486abdac52ffc1ea4cae3c8a28fad888014caea/disabled/failing/shell/_40_guava/cbrd_26659_gap_replace_select_cs/cases/cbrd_26659_gap_replace_select_cs.sh.disabled) | ② | 비활성 FAIL · A 20.137초 | REPLACE SELECT · source/destination 교차 상태 |
| SH-069 | [gap_replace_select_sc](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/8486abdac52ffc1ea4cae3c8a28fad888014caea/disabled/failing/shell/_40_guava/cbrd_26659_gap_replace_select_sc/cases/cbrd_26659_gap_replace_select_sc.sh.disabled) | ② | 비활성 FAIL · A 19.754초 | REPLACE SELECT · source/destination 교차 상태 |
| SH-070 | [gap_unload_sa_cs](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/8486abdac52ffc1ea4cae3c8a28fad888014caea/disabled/failing/shell/_40_guava/cbrd_26659_gap_unload_sa_cs/cases/cbrd_26659_gap_unload_sa_cs.sh.disabled) | ①·② | 비활성 FAIL · A 26.275초 | unload_sa_cs · 정책·값·목적지 owner |
| SH-071 | [gap_unload_sa_sc](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/8486abdac52ffc1ea4cae3c8a28fad888014caea/disabled/failing/shell/_40_guava/cbrd_26659_gap_unload_sa_sc/cases/cbrd_26659_gap_unload_sa_sc.sh.disabled) | ①·② | 비활성 FAIL · A 26.372초 | unload_sa_sc · 정책·값·목적지 owner |
| SH-072 | [jdbc_storage](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/8486abdac52ffc1ea4cae3c8a28fad888014caea/shell/_40_guava/cbrd_26659_jdbc_storage/cases/cbrd_26659_jdbc_storage.sh) | ①·② | 활성 PASS · 21.885초 | prepared bytes·SHOW 권한·복사 survivor |
| SH-073 | [large_keys](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/8486abdac52ffc1ea4cae3c8a28fad888014caea/disabled/long_running/shell/_40_guava/cbrd_26659_large_keys/cases/cbrd_26659_large_keys.sh.disabled) | ⑥ | 비활성 PASS · A 381.773초 · 장시간 | type/policy/PK/UNIQUE/build/maintain 종합 |
| SH-074 | [lob_locators](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/8486abdac52ffc1ea4cae3c8a28fad888014caea/shell/_40_guava/cbrd_26659_lob_locators/cases/cbrd_26659_lob_locators.sh) | ② | 활성 PASS · 12.801초 | locator OOS와 외부 LOB 파일 수명 분리 |
| SH-075 | [notify_abort](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/8486abdac52ffc1ea4cae3c8a28fad888014caea/disabled/failing/shell/_40_guava/cbrd_26659_notify_abort/cases/cbrd_26659_notify_abort.sh.disabled) | ②·⑤ | 비활성 FAIL · A 1.615초 | commit/abort·borrowed chain·whole-stub·release |
| SH-076 | [notify_commit](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/8486abdac52ffc1ea4cae3c8a28fad888014caea/disabled/failing/shell/_40_guava/cbrd_26659_notify_commit/cases/cbrd_26659_notify_commit.sh.disabled) | ②·⑤ | 비활성 FAIL · A 17.025초 | commit/abort·borrowed chain·whole-stub·release |
| SH-077 | [notify_nodrop](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/8486abdac52ffc1ea4cae3c8a28fad888014caea/disabled/failing/shell/_40_guava/cbrd_26659_notify_nodrop/cases/cbrd_26659_notify_nodrop.sh.disabled) | ②·⑤ | 비활성 FAIL · A 1.603초 | commit/abort·borrowed chain·whole-stub·release |
| SH-078 | [owner_drop](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/8486abdac52ffc1ea4cae3c8a28fad888014caea/shell/_40_guava/cbrd_26659_owner_drop/cases/cbrd_26659_owner_drop.sh) | ②·⑤ | 활성 PASS · 11.414초 | 소유 OOS 파일 제거와 독립 survivor |
| SH-079 | [partition_add_drop_list](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/8486abdac52ffc1ea4cae3c8a28fad888014caea/disabled/failing/shell/_40_guava/cbrd_26659_partition_add_drop_list/cases/cbrd_26659_partition_add_drop_list.sh.disabled) | ② | 비활성 FAIL · A 39.417초 | 파티션 add_drop_list · 값·child owner |
| SH-080 | [partition_add_drop_range](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/8486abdac52ffc1ea4cae3c8a28fad888014caea/disabled/failing/shell/_40_guava/cbrd_26659_partition_add_drop_range/cases/cbrd_26659_partition_add_drop_range.sh.disabled) | ② | 비활성 FAIL · A 55.311초 | 파티션 add_drop_range · 값·child owner |
| SH-081 | [partition_hash_coalesce](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/8486abdac52ffc1ea4cae3c8a28fad888014caea/disabled/failing/shell/_40_guava/cbrd_26659_partition_hash_coalesce/cases/cbrd_26659_partition_hash_coalesce.sh.disabled) | ② | 비활성 FAIL · A 24.926초 | 파티션 hash_coalesce · 값·child owner |
| SH-082 | [partition_hash_resize](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/8486abdac52ffc1ea4cae3c8a28fad888014caea/disabled/failing/shell/_40_guava/cbrd_26659_partition_hash_resize/cases/cbrd_26659_partition_hash_resize.sh.disabled) | ② | 비활성 FAIL · A 9.035초 | 파티션 hash_resize · 값·child owner |
| SH-083 | [partition_move](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/8486abdac52ffc1ea4cae3c8a28fad888014caea/disabled/failing/shell/_40_guava/cbrd_26659_partition_move/cases/cbrd_26659_partition_move.sh.disabled) | ② | 비활성 FAIL · A 25.063초 | 파티션 move · 값·child owner |
| SH-084 | [partition_owner](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/8486abdac52ffc1ea4cae3c8a28fad888014caea/shell/_40_guava/cbrd_26659_partition_owner/cases/cbrd_26659_partition_owner.sh) | ② | 활성 PASS · 7.666초 | 파티션 owner · 값·child owner |
| SH-085 | [partition_partition_rejection](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/8486abdac52ffc1ea4cae3c8a28fad888014caea/disabled/failing/shell/_40_guava/cbrd_26659_partition_partition_rejection/cases/cbrd_26659_partition_partition_rejection.sh.disabled) | ② | 비활성 FAIL · A 25.677초 | 파티션 partition_rejection · 값·child owner |
| SH-086 | [partition_promote_list](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/8486abdac52ffc1ea4cae3c8a28fad888014caea/disabled/failing/shell/_40_guava/cbrd_26659_partition_promote_list/cases/cbrd_26659_partition_promote_list.sh.disabled) | ② | 비활성 FAIL · A 56.639초 | 파티션 promote_list · 값·child owner |
| SH-087 | [partition_promote_range](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/8486abdac52ffc1ea4cae3c8a28fad888014caea/disabled/failing/shell/_40_guava/cbrd_26659_partition_promote_range/cases/cbrd_26659_partition_promote_range.sh.disabled) | ② | 비활성 FAIL · A 56.241초 | 파티션 promote_range · 값·child owner |
| SH-088 | [partition_remove](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/8486abdac52ffc1ea4cae3c8a28fad888014caea/disabled/failing/shell/_40_guava/cbrd_26659_partition_remove/cases/cbrd_26659_partition_remove.sh.disabled) | ② | 비활성 FAIL · A 8.960초 | 파티션 remove · 값·child owner |
| SH-089 | [partition_reorganize_list](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/8486abdac52ffc1ea4cae3c8a28fad888014caea/disabled/failing/shell/_40_guava/cbrd_26659_partition_reorganize_list/cases/cbrd_26659_partition_reorganize_list.sh.disabled) | ② | 비활성 FAIL · A 8.556초 | 파티션 reorganize_list · 값·child owner |
| SH-090 | [partition_reorganize_list_merge](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/8486abdac52ffc1ea4cae3c8a28fad888014caea/disabled/failing/shell/_40_guava/cbrd_26659_partition_reorganize_list_merge/cases/cbrd_26659_partition_reorganize_list_merge.sh.disabled) | ② | 비활성 FAIL · A 9.358초 | 파티션 reorganize_list_merge · 값·child owner |
| SH-091 | [partition_reorganize_range](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/8486abdac52ffc1ea4cae3c8a28fad888014caea/disabled/failing/shell/_40_guava/cbrd_26659_partition_reorganize_range/cases/cbrd_26659_partition_reorganize_range.sh.disabled) | ② | 비활성 FAIL · A 25.887초 | 파티션 reorganize_range · 값·child owner |
| SH-092 | [partition_reorganize_range_merge](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/8486abdac52ffc1ea4cae3c8a28fad888014caea/disabled/failing/shell/_40_guava/cbrd_26659_partition_reorganize_range_merge/cases/cbrd_26659_partition_reorganize_range_merge.sh.disabled) | ② | 비활성 FAIL · A 24.727초 | 파티션 reorganize_range_merge · 값·child owner |
| SH-093 | [partition_repartition](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/8486abdac52ffc1ea4cae3c8a28fad888014caea/disabled/failing/shell/_40_guava/cbrd_26659_partition_repartition/cases/cbrd_26659_partition_repartition.sh.disabled) | ② | 비활성 FAIL · A 24.690초 | 파티션 repartition · 값·child owner |
| SH-094 | [partition_route_hash](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/8486abdac52ffc1ea4cae3c8a28fad888014caea/disabled/failing/shell/_40_guava/cbrd_26659_partition_route_hash/cases/cbrd_26659_partition_route_hash.sh.disabled) | ② | 비활성 FAIL · A 26.230초 | 파티션 route_hash · 값·child owner |
| SH-095 | [partition_route_list](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/8486abdac52ffc1ea4cae3c8a28fad888014caea/disabled/failing/shell/_40_guava/cbrd_26659_partition_route_list/cases/cbrd_26659_partition_route_list.sh.disabled) | ② | 비활성 FAIL · A 24.538초 | 파티션 route_list · 값·child owner |
| SH-096 | [partition_route_range](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/8486abdac52ffc1ea4cae3c8a28fad888014caea/disabled/failing/shell/_40_guava/cbrd_26659_partition_route_range/cases/cbrd_26659_partition_route_range.sh.disabled) | ② | 비활성 FAIL · A 23.872초 | 파티션 route_range · 값·child owner |
| SH-097 | [policy_contract](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/8486abdac52ffc1ea4cae3c8a28fad888014caea/disabled/failing/shell/_40_guava/cbrd_26659_policy_contract/cases/cbrd_26659_policy_contract.sh.disabled) | ① | 비활성 FAIL · A 17.357초 | 오류 단계·DDL/값/물리 레코드 보존 |
| SH-098 | [qualified_reuse](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/8486abdac52ffc1ea4cae3c8a28fad888014caea/disabled/failing/shell/_40_guava/cbrd_26659_qualified_reuse/cases/cbrd_26659_qualified_reuse.sh.disabled) | ⑤ | 비활성 FAIL · B 22.482초 | product page census·restart 후 재사용 |
| SH-099 | [read_paths](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/8486abdac52ffc1ea4cae3c8a28fad888014caea/shell/_40_guava/cbrd_26659_read_paths/cases/cbrd_26659_read_paths.sh) | ② | 활성 PASS · 11.993초 | 실제 경로와 전체 값·복사 survivor |
| SH-100 | [record_flags](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/8486abdac52ffc1ea4cae3c8a28fad888014caea/shell/_40_guava/cbrd_26659_record_flags/cases/cbrd_26659_record_flags.sh) | ② | 활성 PASS · 5.608초 | 같은 heap의 clear/set·슬롯·가시성 |
| SH-101 | [record_keys](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/8486abdac52ffc1ea4cae3c8a28fad888014caea/shell/_40_guava/cbrd_26659_record_keys/cases/cbrd_26659_record_keys.sh) | ④·⑥ | 활성 PASS · 20.169초 | 실제 OOS key·B-tree overflow 경계 |
| SH-102 | [record_layout](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/8486abdac52ffc1ea4cae3c8a28fad888014caea/shell/_40_guava/cbrd_26659_record_layout/cases/cbrd_26659_record_layout.sh) | ④ | 활성 PASS · 14.332초 | 실제 record layout·정렬된 경계 |
| SH-103 | [record_residual](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/8486abdac52ffc1ea4cae3c8a28fad888014caea/shell/_40_guava/cbrd_26659_record_residual/cases/cbrd_26659_record_residual.sh) | ④ | 활성 PASS · 24.593초 | 잔여 fixed record·거부 원자성·stub/WAL |
| SH-104 | [record_target0](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/8486abdac52ffc1ea4cae3c8a28fad888014caea/disabled/failing/shell/_40_guava/cbrd_26659_record_target0/cases/cbrd_26659_record_target0.sh.disabled) | ④ | 비활성 FAIL · A 7.867초 | unfill 0에서 four-record target |
| SH-105 | [record_target10](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/8486abdac52ffc1ea4cae3c8a28fad888014caea/disabled/failing/shell/_40_guava/cbrd_26659_record_target10/cases/cbrd_26659_record_target10.sh.disabled) | ④ | 비활성 FAIL · A 22.644초 | unfill 10에서 같은 physical target |
| SH-106 | [representation_chunks](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/8486abdac52ffc1ea4cae3c8a28fad888014caea/shell/_40_guava/cbrd_26659_representation_chunks/cases/cbrd_26659_representation_chunks.sh) | ④ | 활성 PASS · 9.497초 | 정책/직렬화·다중 chunk·전체 값 |
| SH-107 | [schema_attributes_cs](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/8486abdac52ffc1ea4cae3c8a28fad888014caea/disabled/failing/shell/_40_guava/cbrd_26659_schema_attributes_cs/cases/cbrd_26659_schema_attributes_cs.sh.disabled) | ② | 비활성 FAIL · A 20.820초 | SA/CS ADD/DROP/CHANGE/MODIFY · 실제 상태 |
| SH-108 | [schema_attributes_sa](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/8486abdac52ffc1ea4cae3c8a28fad888014caea/disabled/failing/shell/_40_guava/cbrd_26659_schema_attributes_sa/cases/cbrd_26659_schema_attributes_sa.sh.disabled) | ② | 비활성 FAIL · A 21.308초 | SA/CS ADD/DROP/CHANGE/MODIFY · 실제 상태 |
| SH-109 | [schema_cs](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/8486abdac52ffc1ea4cae3c8a28fad888014caea/shell/_40_guava/cbrd_26659_schema_cs/cases/cbrd_26659_schema_cs.sh) | ② | 활성 PASS · 12.566초 | CS 스키마·물질화·값/소유권 |
| SH-110 | [schema_policy](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/8486abdac52ffc1ea4cae3c8a28fad888014caea/shell/_40_guava/cbrd_26659_schema_policy/cases/cbrd_26659_schema_policy.sh) | ①·②·④ | 활성 PASS · 9.987초 | 정책 우선순위·이득 경계·ALTER 비소급 |
| SH-111 | [schema_rewrites_cs](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/8486abdac52ffc1ea4cae3c8a28fad888014caea/disabled/failing/shell/_40_guava/cbrd_26659_schema_rewrites_cs/cases/cbrd_26659_schema_rewrites_cs.sh.disabled) | ② | 비활성 FAIL · A 20.186초 | SA/CS schema 재작성·값·owner |
| SH-112 | [schema_rewrites_sa](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/8486abdac52ffc1ea4cae3c8a28fad888014caea/disabled/long_running/shell/_40_guava/cbrd_26659_schema_rewrites_sa/cases/cbrd_26659_schema_rewrites_sa.sh.disabled) | ② | 비활성 FAIL · A 94.311초 · 장시간 | SA/CS schema 재작성·값·owner |
| SH-113 | [schema_sa](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/8486abdac52ffc1ea4cae3c8a28fad888014caea/disabled/long_running/shell/_40_guava/cbrd_26659_schema_sa/cases/cbrd_26659_schema_sa.sh.disabled) | ② | 비활성 PASS · A 81.389초 · 장시간 | SA 스키마·물질화·값/소유권 |
| SH-114 | [serialized_chunks](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/8486abdac52ffc1ea4cae3c8a28fad888014caea/disabled/failing/shell/_40_guava/cbrd_26659_serialized_chunks/cases/cbrd_26659_serialized_chunks.sh.disabled) | ④ | 비활성 FAIL · A 21.250초 | 정확한 직렬화 chunk 이웃·저장 flag |
| SH-115 | [show_contract](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/8486abdac52ffc1ea4cae3c8a28fad888014caea/disabled/failing/shell/_40_guava/cbrd_26659_show_contract/cases/cbrd_26659_show_contract.sh.disabled) | ① | 비활성 FAIL · A 1.482초 | SHOW 대상·오류·권한·preservation |
| SH-116 | [show_partitions](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/8486abdac52ffc1ea4cae3c8a28fad888014caea/disabled/failing/shell/_40_guava/cbrd_26659_show_partitions/cases/cbrd_26659_show_partitions.sh.disabled) | ①·② | 비활성 FAIL · A 1.480초 | SHOW 파티션 귀속·실제 child owner |
| SH-117 | [snapshot_visibility](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/8486abdac52ffc1ea4cae3c8a28fad888014caea/shell/_40_guava/cbrd_26659_snapshot_visibility/cases/cbrd_26659_snapshot_visibility.sh) | ②·⑤ | 활성 PASS · 9.705초 | old/new reader의 정확한 버전 값 |
| SH-118 | [snapshots_reclaim](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/8486abdac52ffc1ea4cae3c8a28fad888014caea/disabled/failing/shell/_40_guava/cbrd_26659_snapshots_reclaim/cases/cbrd_26659_snapshots_reclaim.sh.disabled) | ⑤ | 비활성 FAIL · A 18.640초 | snapshot horizon 뒤 chunk/page 회수 |
| SH-119 | [tde_crash_committed](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/8486abdac52ffc1ea4cae3c8a28fad888014caea/disabled/failing/shell/_40_guava/cbrd_26659_tde_crash_committed/cases/cbrd_26659_tde_crash_committed.sh.disabled) | ② | 비활성 FAIL · A 6.079초 | AES commit/crash/redo·값과 header |
| SH-120 | [tde_crash_undo](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/8486abdac52ffc1ea4cae3c8a28fad888014caea/disabled/failing/shell/_40_guava/cbrd_26659_tde_crash_undo/cases/cbrd_26659_tde_crash_undo.sh.disabled) | ② | 비활성 FAIL · A 6.076초 | AES crash/undo·pre-image와 header |
| SH-121 | [tde_storage](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/8486abdac52ffc1ea4cae3c8a28fad888014caea/disabled/failing/shell/_40_guava/cbrd_26659_tde_storage/cases/cbrd_26659_tde_storage.sh.disabled) | ② | 비활성 FAIL · A 7.274초 | 소유 volume/log의 plaintext sentinel 대조 |
| SH-122 | [tde_wal](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/8486abdac52ffc1ea4cae3c8a28fad888014caea/shell/_40_guava/cbrd_26659_tde_wal/cases/cbrd_26659_tde_wal.sh) | ② | 활성 PASS · 28.415초 | lazy AES·파일 metadata·WAL 분류 |
| SH-123 | [transactions](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/8486abdac52ffc1ea4cae3c8a28fad888014caea/shell/_40_guava/cbrd_26659_transactions/cases/cbrd_26659_transactions.sh) | ② | 활성 PASS · 6.727초 | SA/CS 트랜잭션·원자성·전체 값 |
| SH-124 | [utility_compact_cs](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/8486abdac52ffc1ea4cae3c8a28fad888014caea/disabled/failing/shell/_40_guava/cbrd_26659_utility_compact_cs/cases/cbrd_26659_utility_compact_cs.sh.disabled) | ①·② | 비활성 FAIL · A 21.124초 | 정책별 compact_cs roundtrip |
| SH-125 | [utility_compact_sa](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/8486abdac52ffc1ea4cae3c8a28fad888014caea/disabled/failing/shell/_40_guava/cbrd_26659_utility_compact_sa/cases/cbrd_26659_utility_compact_sa.sh.disabled) | ①·② | 비활성 FAIL · A 21.659초 | 정책별 compact_sa roundtrip |
| SH-126 | [utility_cs](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/8486abdac52ffc1ea4cae3c8a28fad888014caea/shell/_40_guava/cbrd_26659_utility_cs/cases/cbrd_26659_utility_cs.sh) | ①·② | 활성 PASS · 41.473초 | 일반 CS unload/load/compact·정확한 값 |
| SH-127 | [utility_policy_cs](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/8486abdac52ffc1ea4cae3c8a28fad888014caea/disabled/failing/shell/_40_guava/cbrd_26659_utility_policy_cs/cases/cbrd_26659_utility_policy_cs.sh.disabled) | ①·② | 비활성 FAIL · A 22.137초 | policy_cs · 정책/값/상태 보존 |
| SH-128 | [utility_policy_sa](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/8486abdac52ffc1ea4cae3c8a28fad888014caea/disabled/failing/shell/_40_guava/cbrd_26659_utility_policy_sa/cases/cbrd_26659_utility_policy_sa.sh.disabled) | ①·② | 비활성 FAIL · A 22.454초 | policy_sa · 정책/값/상태 보존 |
| SH-129 | [utility_policy_sa_nolog](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/8486abdac52ffc1ea4cae3c8a28fad888014caea/disabled/failing/shell/_40_guava/cbrd_26659_utility_policy_sa_nolog/cases/cbrd_26659_utility_policy_sa_nolog.sh.disabled) | ①·② | 비활성 FAIL · A 20.604초 | policy_sa_nolog · 정책/값/상태 보존 |
| SH-130 | [utility_policy_unload_sa](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/8486abdac52ffc1ea4cae3c8a28fad888014caea/disabled/failing/shell/_40_guava/cbrd_26659_utility_policy_unload_sa/cases/cbrd_26659_utility_policy_unload_sa.sh.disabled) | ①·② | 비활성 FAIL · A 20.858초 | policy_unload_sa · 정책/값/상태 보존 |
| SH-131 | [utility_sa](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/8486abdac52ffc1ea4cae3c8a28fad888014caea/shell/_40_guava/cbrd_26659_utility_sa/cases/cbrd_26659_utility_sa.sh) | ①·② | 활성 PASS · 45.180초 | 일반 SA load와 후속 값 검사 |
| SH-132 | [utility_sa_physical](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/8486abdac52ffc1ea4cae3c8a28fad888014caea/shell/_40_guava/cbrd_26659_utility_sa_physical/cases/cbrd_26659_utility_sa_physical.sh) | ①·② | 활성 PASS · 43.129초 | SA no-logging load·후속 물리 상태 |
| SH-133 | [cbrd_27237_rollback_vacuum](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/8486abdac52ffc1ea4cae3c8a28fad888014caea/disabled/failing/shell/_40_guava/cbrd_27237_rollback_vacuum/cases/cbrd_27237_rollback_vacuum.sh.disabled) | ②·⑤ | 비활성 FAIL · B 11.066초 | aborted UPDATE 뒤 vacuum·survivor |

## 부록 C C++ 보완 TC 14개

아래는 Work456에서 추가한 개별 GTest 함수다. 링크와 줄 번호는 현재 Engine `c4c4f5c5` 의 선언을 확인한 위치다. 과거 실행 근거는 UT-01–09의 [ticket11](ticket11-serialization-chunk-guard-boundaries-20261021.md), UT-10·11의 [ticket14](ticket14-cpp-read-expand-buffer-20261021.md), UT-12–14의 [ticket15](ticket15-identity-ownership-rollback-reclaim-20261021.md)에 각각 기록되어 있다. 이 표는 최신 리비전에서 14개 모두 재실행·PASS했다는 표가 아니다.

| 번호 | 실제 GTest 이름 | 대응 항목 | 보완 계약 |
| --- | --- | --- | --- |
| UT-01 | [OosBoundaries.ExactChunkCapacityAndOneByteOverStoreOneAndTwoChunks](https://github.com/CUBRID/cubrid/blob/c4c4f5c5ed55fb0130c72bb261061ec441662554/unit_tests/oos/test_oos_boundaries.cpp#L68) | ③·④ | raw chunk 용량과 +1B·실제 chunk 수·전체 재구성 |
| UT-02 | [OosBoundaries.CallerLengthOneByteEitherSideRejectsAndPreservesStoredBytes](https://github.com/CUBRID/cubrid/blob/c4c4f5c5ed55fb0130c72bb261061ec441662554/unit_tests/oos/test_oos_boundaries.cpp#L122) | ③·④ | 호출 길이 ±1B 거부·기존 저장 값 보존 |
| UT-03 | [OosBoundaries.InsertLengthNarrowingGuardOnlyRejectsWithoutTouchingExistingChain](https://github.com/CUBRID/cubrid/blob/c4c4f5c5ed55fb0130c72bb261061ec441662554/unit_tests/oos/test_oos_boundaries.cpp#L156) | ③·④ | INT_MAX 초과 길이 guard·기존 chain 보존 |
| UT-04 | [OosBoundaries.InlineLengthEndpointsAreParserGuardsOnly](https://github.com/CUBRID/cubrid/blob/c4c4f5c5ed55fb0130c72bb261061ec441662554/unit_tests/oos/test_oos_boundaries.cpp#L185) | ③·④ | stub 길이 endpoint parser guard만 검증 |
| UT-05 | [OosBoundaries.EveryVotWidthRequiresExactlyOneStubWithinFieldAndRecord](https://github.com/CUBRID/cubrid/blob/c4c4f5c5ed55fb0130c72bb261061ec441662554/unit_tests/oos/test_oos_boundaries.cpp#L217) | ③·④ | VOT 폭별 field/record 범위와 정확한 stub |
| UT-06 | [OosBoundaries.StubWriterUsesValueCursorAndRetriesAtExactCapacity](https://github.com/CUBRID/cubrid/blob/c4c4f5c5ed55fb0130c72bb261061ec441662554/unit_tests/oos/test_oos_boundaries.cpp#L251) | ③·④ | 실제 value cursor·exact capacity·재시도 |
| UT-07 | [OosBoundaries.StubWriterOffsetEntryOneByteShortChangesNothing](https://github.com/CUBRID/cubrid/blob/c4c4f5c5ed55fb0130c72bb261061ec441662554/unit_tests/oos/test_oos_boundaries.cpp#L288) | ③·④ | offset entry 한 byte 부족·무변경 |
| UT-08 | [OosBoundaries.StoredVotBoundariesAndExpandedValuesPreserveMixedRows](https://github.com/CUBRID/cubrid/blob/c4c4f5c5ed55fb0130c72bb261061ec441662554/unit_tests/oos/test_oos_boundaries.cpp#L303) | ③·④ | 실제 저장 VOT·Expand 뒤 혼합 row 보존 |
| UT-09 | [OosBoundaries.NonOosShortIntVotBoundaryPreservesCompleteValues](https://github.com/CUBRID/cubrid/blob/c4c4f5c5ed55fb0130c72bb261061ec441662554/unit_tests/oos/test_oos_boundaries.cpp#L393) | ③·④ | non-OOS SHORT/INT VOT·전체 값 |
| UT-10 | [OosSqlVisibleVersion.StoredAndExpandedFetchPreserveMixedRowsAndCallerOwnedBytes](https://github.com/CUBRID/cubrid/blob/c4c4f5c5ed55fb0130c72bb261061ec441662554/unit_tests/oos/sql/test_oos_sql_visible_version.cpp#L196) | ③ | stored/expanded fetch·호출자 소유 byte 수명 |
| UT-11 | [OosSqlVisibleVersion.ExpandRetryPreservesCallerBufferAndStoredReference](https://github.com/CUBRID/cubrid/blob/c4c4f5c5ed55fb0130c72bb261061ec441662554/unit_tests/oos/sql/test_oos_sql_visible_version.cpp#L305) | ③·④ | Expand 재시도·호출자 버퍼·저장 참조 |
| UT-12 | [OosFileDestroyServerTest.SystemWorkerUndoDefersPageReturnAndAbortRestoresTheChain](https://github.com/CUBRID/cubrid/blob/c4c4f5c5ed55fb0130c72bb261061ec441662554/unit_tests/oos/test_oos_remove_file_server.cpp#L292) | ③·⑤ | system-worker undo horizon·abort 후 chain 복원 |
| UT-13 | [OosSqlOwnership.UnassignedUpdateRetainsWholeStubAcrossCommitAndAbort](https://github.com/CUBRID/cubrid/blob/c4c4f5c5ed55fb0130c72bb261061ec441662554/unit_tests/oos/sql/test_oos_sql_ownership.cpp#L128) | ③·⑤ | 미할당 stub 전체 identity·commit/abort 소유권 |
| UT-14 | [OosSqlOwnership.ExistingOosFileReceivesClassAesAndPreservesIdentityAndValues](https://github.com/CUBRID/cubrid/blob/c4c4f5c5ed55fb0130c72bb261061ec441662554/unit_tests/oos/sql/test_oos_sql_ownership.cpp#L163) | ③ | 기존 파일의 class AES 적용·identity/값 보존 |

## 부록 D 집계와 검토 근거

| 목록 | 총수 | 활성 | 비활성 |
| --- | ---: | ---: | ---: |
| SQL/answer 쌍 | 28 | 25 | 3 |
| OOS shell 진입점 | 133 | 69 | 64 |

Shell 133개는 티켓 접두사만으로 선별하지 않고 PR의 OOS 진입점 전체와 공통 helper 참조를 기준으로 확인했다. `cbrd_27237_rollback_vacuum` 을 포함하며 helper 자체를 추가 TC로 세지 않았다. report 생성 시 모든 133개 진입점의 hash를 inventory와 대조하고, 최신 JUnit에서 활성 69개의 유일한 실행·PASS 및 비활성 64개의 부재를 확인했다. SQL 28개는 실제 SQL/answer 짝을 확인했고 비활성 3개의 원본 hash를 대조했다. C++ 보완 함수 14개는 해당 선언·파일·줄 번호를 확인했다. 이 보고서를 작성하면서 테스트를 새로 실행하거나 source/TC를 변경하지 않았다.

연산별 완료 판단에는 [승인 spec](supplement-spec-work456-20261021.md)과 [기존 요구사항 지도](supplement-operation-inventory-work456-20261021.md)를 사용한다. 과거 개별 티켓의 완료 문구는 그 문서의 리비전과 범위에 한정한다. 최신 CI의 실행 선택과 실패 제외는 [SQL manifest](https://github.com/CUBRID/cubrid-testcases/blob/4f6557f7f96ac789e1697ef8b27dd8bf2807802e/disabled/oos-pr8128.tsv), [shell inventory](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/8486abdac52ffc1ea4cae3c8a28fad888014caea/disabled/oos-pr8128-inventory.tsv) 및 각 run URL로 재확인할 수 있다.

</details>
