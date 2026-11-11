# OOS 리팩토링 후보 목록

OOS 유지보수자가 다음 sub-task를 고를 때 쓰는 목록이다. 기존 R 항목 68개와 2026-11-11 추가된 N 항목 2개를 ID별로 정리했다. 먼저 R-16과 N-20261111-02의 작은 테스트 helper 정리를 검토하고, 각 절의 선행조건과 검증 부담을 함께 판단한다. [CBRD-27881](https://jira.cubrid.org/browse/CBRD-27881)

## 이름과 날짜

후보 제목은 `[YYYY-MM-DD] ID 구체적인 변경 내용` 형식이다. 날짜는 현재 보존된 조사 자료에서 확인할 수 있는 최초 기록일이다. 기존 R 항목은 2026-11-03 보고서, 신규 N 항목은 2026-11-11 기록을 근거로 삼았다. 실제 최초 발견 시각이 더 이른지는 확인되지 않았다. 재검토 날짜와 소스 revision은 각 절과 아래 분석 기준에서 구분한다. 기존 ID와 `#r-16` 같은 링크는 후속 수정에서도 유지한다.

이 문서는 현재 선정 판단을 갱신하는 곳이다. 과거 보고서는 해당 날짜의 조사와 실험을 인용할 때 사용한다. 기각·보류와 병합 기록을 포함한 누적 70개이며, 다음 sub-task의 범위는 선택 시 결정한다.

## 분석 기준과 확인한 상태

- 기존 분석의 기준은 CUBRID/cubrid `dcbf09e4f7fd02ff9c8fc6493ec8887fc2919d67`다. [기존 조사 보고서](CBRD-27881-oos-refactoring-candidates_dcbf09e_claude.md)
- 2026-11-11 후속 소스 조사는 PR #7990 head `50619ce53ef7b0e6bc8b468b2065ae7da4ef592f`, base 및 merge-base `2dd94e32ab86a756b0f1ea2123ad7d2ac913321b`에서 수행했다. 사양은 `OOS-CONTEXT.md` SHA-256 `426f294420285381835a0e733b12bde9ed2ffa14dfdd6264db5e3c33894f533d`를 기준으로 삼았다. 후속 분석은 정적 조사이며 실제 파서·SQL·HA·복구 실행 비교는 구현 단계에 남아 있다. [후속 조사와 결정 기록](survey-2026-11-11.md)
- 2026-11-11 13:45 KST에 관련 PR의 공개 상태를 다시 확인했다. 기존 sub-task PR 중 #8367·#8368·#8370·#8371·#8372·#8373은 병합됐고 #8369는 열린 draft다. 과거 선행 작업 #8330과 #8350도 병합됐다. #8347은 미병합 종료됐으며 #8128·#8299·#8434는 열려 있다. PR 상태 확인은 후보별 구현 검증과 구분해 읽는다.
- 후속 확인 절이 없는 후보는 기존 revision의 분석을 유지한다. 실제 통합 revision에서 동작·소유권·의존 코드를 다시 확인한 뒤 선택한다.

## 후보 인덱스

| ID | 최초 기록일 | 변경 내용 | 선정 판단 |
| --- | --- | --- | --- |
| [R-01](#r-01) | 2026-11-03 | 미사용 bestspace 통계 요소 제거 | PR 병합 확인 |
| [R-02](#r-02) | 2026-11-03 | 정적 함수 전방 선언 정리 검토 | 기각 |
| [R-03](#r-03) | 2026-11-03 | FILE_OOS fallthrough 정리 검토 | 기각 |
| [R-04](#r-04) | 2026-11-03 | OOS 로그 함수군 정리 검토 | 기각 |
| [R-05](#r-05) | 2026-11-03 | OOS 조회 probe의 공개 범위 결정 | 담당자 결정 대기 |
| [R-06](#r-06) | 2026-11-03 | SQL·단위 테스트 helper 정리 | PR 병합 확인 |
| [R-07](#r-07) | 2026-11-03 | SQL·단위 테스트 helper 정리 | PR 병합 확인 |
| [R-08](#r-08) | 2026-11-03 | heap 속성 writer의 LOB 복사 통합 | 기존 draft PR |
| [R-09](#r-09) | 2026-11-03 | 속성 flag 변경 판정 통합 | PR 병합 확인 |
| [R-10](#r-10) | 2026-11-03 | 로그 없는 header dirty 처리 통합 | PR 병합 확인 |
| [R-11](#r-11) | 2026-11-03 | OOS 테스트 seam 정리 재검토 | 과거 보고 유지 |
| [R-12](#r-12) | 2026-11-03 | 코드와 다른 OOS 주석 수정 | PR 병합 확인 |
| [R-13](#r-13) | 2026-11-03 | bestspace 내부 정의 분리 | 판단 보류 |
| [R-14](#r-14) | 2026-11-03 | heap 삭제의 OOS 파일 정리 통합 | PR 병합 확인 |
| [R-15](#r-15) | 2026-11-03 | class repr 해제와 오류 helper 재검토 | 과거 보고 유지 |
| [R-16](#r-16) | 2026-11-03 | 테스트의 page free-space 조회 중복 제거 | 먼저 검토 |
| [R-17](#r-17) | 2026-11-03 | prefetch 조건과 OOS 사전 검사 정리 | 과거 보고 유지 |
| [R-18](#r-18) | 2026-11-03 | 잠금 상태의 bestspace entry 제거 공유 | 조건 확인 후 |
| [R-19](#r-19) | 2026-11-03 | 테스트 bridge 선언 공유 | 이어서 검토 |
| [R-20](#r-20) | 2026-11-03 | 일회성 fault hook 타입 통합 | 판단 보류 |
| [R-21](#r-21) | 2026-11-03 | bestspace 페이지 검색 함수 분해 | 판단 보류 |
| [R-22](#r-22) | 2026-11-03 | 페이지 검색의 header 소유와 fallback 정리 | 결함 수정 선행 |
| [R-23](#r-23) | 2026-11-03 | OOS 읽기의 chain 끝 처리 공유 | 기존 보류 |
| [R-24](#r-24) | 2026-11-03 | OOS 복제 로그 emitter 통합 | 기존 보류 |
| [R-25](#r-25) | 2026-11-03 | 24바이트 inline stub codec 통합 | 조건 확인 후 |
| [R-26](#r-26) | 2026-11-03 | RECDES OOS helper 분리 | 통합 revision 재검토 |
| [R-27](#r-27) | 2026-11-03 | demotion planner 분리 | 조건 확인 후 |
| [R-28](#r-28) | 2026-11-03 | OOS 파일 구현 분리 | 판단 보류 |
| [R-29](#r-29) | 2026-11-03 | 미사용 복구 인덱스 삭제 제안 | 통합 설계 확인 |
| [R-30](#r-30) | 2026-11-03 | SQL 테스트 등록 목록 공유 | 이어서 검토 |
| [R-31](#r-31) | 2026-11-03 | SQL 테스트 fixture 공통화 | 기존 보류 |
| [R-32](#r-32) | 2026-11-03 | 큰 OOS 테스트 파일 분리 | 기존 보류 |
| [R-33](#r-33) | 2026-11-03 | 복제 LSA 상태와 suppression guard 정리 | 통합 설계 확인 |
| [R-34](#r-34) | 2026-11-03 | tier-3 bestspace sync 처리 결정 | CBRD-27213 이관 |
| [R-35](#r-35) | 2026-11-03 | flush insert 매크로 분리 여부 결정 | 담당자 결정 대기 |
| [R-36](#r-36) | 2026-11-03 | 손상 오류 반환 매크로 도입 결정 | 담당자 결정 대기 |
| [R-37](#r-37) | 2026-11-03 | 중복 또는 무검증 테스트 삭제 여부 결정 | 담당자 결정 대기 |
| [R-38](#r-38) | 2026-11-03 | 테스트 로그 계층 유지 범위 결정 | 담당자 결정 대기 |
| [R-39](#r-39) | 2026-11-03 | FILE_OOS 진단 문자열 변경 여부 결정 | CBRD-28023 이관 |
| [R-40](#r-40) | 2026-11-03 | 셸 DB 수명 helper와 도구 정리 | 과거 보고 유지 |
| [R-41](#r-41) | 2026-11-03 | 파일 수집기와 bitmap 순회 정리 | 과거 보고 유지 |
| [R-42](#r-42) | 2026-11-03 | reclaim 페이지 처리 단계 분리 | 과거 보고 유지 |
| [R-43](#r-43) | 2026-11-03 | reclaim sweep 단계와 registry 분리 | 과거 보고 유지 |
| [R-44](#r-44) | 2026-11-03 | cache API 계약 정리 | 과거 보고 유지 |
| [R-45](#r-45) | 2026-11-03 | sysop guard 도입 검토 | 과거 보고 유지 |
| [R-46](#r-46) | 2026-11-03 | chunk header peek helper 도입 검토 | 과거 보고 유지 |
| [R-47](#r-47) | 2026-11-03 | insert API 배관 정리 | 과거 보고 유지 |
| [R-48](#r-48) | 2026-11-03 | 페이지 간 삽입 복제 guard 정리 | 과거 보고 유지 |
| [R-49](#r-49) | 2026-11-03 | chain 삭제의 head 검증 분리 검토 | 과거 보고 유지 |
| [R-50](#r-50) | 2026-11-03 | physical log helper의 const_cast 정리 | 과거 보고 유지 |
| [R-51](#r-51) | 2026-11-03 | 작은 코드 정리 항목 검토 | 과거 보고 유지 |
| [R-52](#r-52) | 2026-11-03 | 페이지 초기화 callback 반환값 정리 검토 | 기각 |
| [R-53](#r-53) | 2026-11-03 | VOT decoder 공용 accessor 사용 검토 | 과거 보고 유지 |
| [R-54](#r-54) | 2026-11-03 | OOS payload 소유권 타입 검토 | 과거 보고 유지 |
| [R-55](#r-55) | 2026-11-03 | eager cleanup gate helper 검토 | 과거 보고 유지 |
| [R-56](#r-56) | 2026-11-03 | 복제 OOS 레코드 재구성 정리 | 과거 보고 유지 |
| [R-57](#r-57) | 2026-11-03 | 현재 로그 정보 구조체 배열 검토 | 과거 보고 유지 |
| [R-58](#r-58) | 2026-11-03 | sql.log OOS cache 클래스 분리 검토 | 과거 보고 유지 |
| [R-59](#r-59) | 2026-11-03 | 파일 header class OID helper 검토 | 과거 보고 유지 |
| [R-60](#r-60) | 2026-11-03 | OOS 저장 속성 mask 검토 | 과거 보고 유지 |
| [R-61](#r-61) | 2026-11-03 | 복제 적용 prologue helper 검토 | 과거 보고 유지 |
| [R-62](#r-62) | 2026-11-03 | overflow 목록 해제와 header 분리 검토 | 과거 보고 유지 |
| [R-63](#r-63) | 2026-11-03 | SA와 SERVER 테스트 본문 공유 검토 | 과거 보고 유지 |
| [R-64](#r-64) | 2026-11-03 | OOS 파일 테스트 fixture 정리 검토 | 과거 보고 유지 |
| [R-65](#r-65) | 2026-11-03 | OOS 테스트 main 연결 정리 검토 | 과거 보고 유지 |
| [R-66](#r-66) | 2026-11-03 | 통계 조회 함수 이동 검토 | 과거 보고 유지 |
| [R-70](#r-70) | 2026-11-03 | 형태만 바꾸는 변경 제외 | 기각 |
| [R-71](#r-71) | 2026-11-03 | 여러 sector의 OOS 통계 테스트 보강 | 과거 보고 유지 |
| [N-20261111-01](#n-20261111-01) | 2026-11-11 | STORAGE 거부 검사 재사용 | 조건 확인 후 |
| [N-20261111-02](#n-20261111-02) | 2026-11-11 | SQL 테스트 정수 변환 공유 | 먼저 검토 |

## 담당자 결정과 결함 근거

R-34는 CBRD-27213 재설계에서 legacy tier-3 sync와 관련 구조를 함께 제거하는 방향으로 결정됐다. R-39의 진단 문자열 변경은 CBRD-28023이 추적한다. 나머지 다섯 NEEDS-DECISION 항목은 이 조사에서 새로운 담당자 결정을 확정하지 않았다. DF-03의 commit 후 postpone 결정과 #8347의 과거 보류 해제 이력도 후속 조사 기록에 보존했다. [결정과 후속 조사](survey-2026-11-11.md) · [담당자 결정 자료](CBRD-27881-owner-decisions_dcbf09e_claude.md)

DF 결함 후보의 관찰·재현 결과와 한계는 기존 보고서에서 확인한다. R-24 조사에서 나온 old-key 정리 우려와 BIGONE 기대값·사양 차이는 검증이 남은 관찰로 기록했다. [기존 결함 후보](CBRD-27881-oos-refactoring-candidates_dcbf09e_claude.md#defect-candidates)

## 후보별 상세

<a id="r-01"></a>

### [2026-11-03] R-01 미사용 bestspace 통계 요소 제거

선정 판단은 **PR 병합 확인**이다.

2026-11-03 기록에서는 `draft PR`로 분류했다. 원래 범위는 다음과 같다. 미사용 OOS_STATS_PREV_BEST_INDEX, bridge_oos_vpid_init_new, 항상 0인 prev_freespace 인자와 중복 NULL 대입 제거. 당시 판단과 선행조건도 함께 기록했다. 조사 당시 draft PR.

2026-11-11 확인한 [PR #8367](https://github.com/CUBRID/cubrid/pull/8367)은 병합된 상태였다. 당시 빌드·실행 결과와 동작 차이는 [해당 PR의 문서 목록](README.md)에서 확인한다.

근거는 `dcbf09e4f7fd02ff9c8fc6493ec8887fc2919d67`의 [기존 조사](CBRD-27881-oos-refactoring-candidates_dcbf09e_claude.md#candidates-turned-into-draft-prs)다.

<a id="r-02"></a>

### [2026-11-03] R-02 정적 함수 전방 선언 정리 검토

선정 판단은 **기각**이다.

2026-11-03 기록의 분류는 `REJECTED`였다. 원래 범위는 다음과 같다. 전방 선언 9개 삭제 제안. 당시 판단과 선행조건도 함께 기록했다. static 함수 prototype 블록을 빠짐없이 두는 CUBRID 관례와 충돌.

근거는 `dcbf09e4f7fd02ff9c8fc6493ec8887fc2919d67`의 [기존 조사](CBRD-27881-oos-refactoring-candidates_dcbf09e_claude.md#candidates-left-out-of-prs)다.

<a id="r-03"></a>

### [2026-11-03] R-03 FILE_OOS fallthrough 정리 검토

선정 판단은 **기각**이다.

2026-11-03 기록의 분류는 `REJECTED`였다. 원래 범위는 다음과 같다. case FILE_OOS fallthrough 변경 제안. 당시 판단과 선행조건도 함께 기록했다. 문서화된 의도적 fallthrough.

근거는 `dcbf09e4f7fd02ff9c8fc6493ec8887fc2919d67`의 [기존 조사](CBRD-27881-oos-refactoring-candidates_dcbf09e_claude.md#candidates-left-out-of-prs)다.

<a id="r-04"></a>

### [2026-11-03] R-04 OOS 로그 함수군 정리 검토

선정 판단은 **기각**이다.

2026-11-03 기록의 분류는 `REJECTED`였다. 원래 범위는 다음과 같다. oos_info와 FATAL 삭제 제안. 당시 판단과 선행조건도 함께 기록했다. 대칭 로그 함수군의 일부.

근거는 `dcbf09e4f7fd02ff9c8fc6493ec8887fc2919d67`의 [기존 조사](CBRD-27881-oos-refactoring-candidates_dcbf09e_claude.md#candidates-left-out-of-prs)다.

<a id="r-05"></a>

### [2026-11-03] R-05 OOS 조회 probe의 공개 범위 결정

선정 판단은 **담당자 결정 대기**이다.

2026-11-03 기록의 분류는 `NEEDS-DECISION`였다. 원래 범위는 다음과 같다. oos_chunk_exists, oos_get_identity_stamp, oos_get_length를 진단 API로 유지하거나 단위 테스트 빌드 전용으로 제한. 당시 판단과 선행조건도 함께 기록했다. 운영 호출은 없지만 header에 tests and diagnostics 용도 명시.

근거는 `dcbf09e4f7fd02ff9c8fc6493ec8887fc2919d67`의 [기존 조사](CBRD-27881-oos-refactoring-candidates_dcbf09e_claude.md#needs-decision)다.

<a id="r-06"></a>

### [2026-11-03] R-06 SQL·단위 테스트 helper 정리

선정 판단은 **PR 병합 확인**이다.

2026-11-03 기록에서는 `draft PR`로 분류했다. 원래 범위는 다음과 같다. 미사용 SQL helper 두 개를 제거하고 중복 test_oos_utils helper를 공용 header로 모으는 묶음 정리. 당시 판단과 선행조건도 함께 기록했다. #8368에서 두 ID를 묶어 처리했으며 개별 ID의 작업 배정은 확인되지 않음.

원자료는 R-06과 R-07을 하나의 #8368 행으로 묶어 미사용 SQL helper 제거와 중복 helper 공유를 설명한다. 각 ID에 두 작업을 개별 배정한 원기록은 확인되지 않아 묶음의 범위를 함께 보존한다.

2026-11-11 확인한 [PR #8368](https://github.com/CUBRID/cubrid/pull/8368)은 병합된 상태였다. 당시 빌드·실행 결과와 동작 차이는 [해당 PR의 문서 목록](README.md)에서 확인한다.

근거는 `dcbf09e4f7fd02ff9c8fc6493ec8887fc2919d67`의 [기존 조사](CBRD-27881-oos-refactoring-candidates_dcbf09e_claude.md#candidates-turned-into-draft-prs)다.

<a id="r-07"></a>

### [2026-11-03] R-07 SQL·단위 테스트 helper 정리

선정 판단은 **PR 병합 확인**이다.

2026-11-03 기록에서는 `draft PR`로 분류했다. 원래 범위는 다음과 같다. 미사용 SQL helper 두 개를 제거하고 중복 test_oos_utils helper를 공용 header로 모으는 묶음 정리. 당시 판단과 선행조건도 함께 기록했다. #8368에서 두 ID를 묶어 처리했으며 개별 ID의 작업 배정은 확인되지 않음.

원자료는 R-06과 R-07을 하나의 #8368 행으로 묶어 미사용 SQL helper 제거와 중복 helper 공유를 설명한다. 각 ID에 두 작업을 개별 배정한 원기록은 확인되지 않아 묶음의 범위를 함께 보존한다.

2026-11-11 확인한 [PR #8368](https://github.com/CUBRID/cubrid/pull/8368)은 병합된 상태였다. 당시 빌드·실행 결과와 동작 차이는 [해당 PR의 문서 목록](README.md)에서 확인한다.

근거는 `dcbf09e4f7fd02ff9c8fc6493ec8887fc2919d67`의 [기존 조사](CBRD-27881-oos-refactoring-candidates_dcbf09e_claude.md#candidates-turned-into-draft-prs)다.

<a id="r-08"></a>

### [2026-11-03] R-08 heap 속성 writer의 LOB 복사 통합

선정 판단은 **기존 draft PR**이다.

2026-11-03 기록에서는 `draft PR`로 분류했다. 원래 범위는 다음과 같다. 두 heap 속성 writer의 LOB 복사 코드를 heap_attrvalue_copy_lob으로 통합. 당시 판단과 선행조건도 함께 기록했다. 조사 당시 draft PR.

2026-11-11 확인한 [PR #8369](https://github.com/CUBRID/cubrid/pull/8369)은 열린 draft였다. 당시 빌드·실행 결과와 동작 차이는 [해당 PR의 문서 목록](README.md)에서 확인한다.

근거는 `dcbf09e4f7fd02ff9c8fc6493ec8887fc2919d67`의 [기존 조사](CBRD-27881-oos-refactoring-candidates_dcbf09e_claude.md#candidates-turned-into-draft-prs)다.

<a id="r-09"></a>

### [2026-11-03] R-09 속성 flag 변경 판정 통합

선정 판단은 **PR 병합 확인**이다.

2026-11-03 기록에서는 `draft PR`로 분류했다. 원래 범위는 다음과 같다. INVISIBLE, PREFER_INLINE, FORCE_OUTLINE 판정 블록을 build_attr_flag_change_property로 통합. 당시 판단과 선행조건도 함께 기록했다. 조사 당시 draft PR.

2026-11-11 확인한 [PR #8372](https://github.com/CUBRID/cubrid/pull/8372)은 병합된 상태였다. 당시 빌드·실행 결과와 동작 차이는 [해당 PR의 문서 목록](README.md)에서 확인한다.

근거는 `dcbf09e4f7fd02ff9c8fc6493ec8887fc2919d67`의 [기존 조사](CBRD-27881-oos-refactoring-candidates_dcbf09e_claude.md#candidates-turned-into-draft-prs)다.

<a id="r-10"></a>

### [2026-11-03] R-10 로그 없는 header dirty 처리 통합

선정 판단은 **PR 병합 확인**이다.

2026-11-03 기록에서는 `draft PR`로 분류했다. 원래 범위는 다음과 같다. 반복된 header 페이지 dirty 처리를 oos_hdr_page_set_dirty_unlogged로 통합. 당시 판단과 선행조건도 함께 기록했다. 조사 당시 draft PR.

2026-11-11 확인한 [PR #8370](https://github.com/CUBRID/cubrid/pull/8370)은 병합된 상태였다. 당시 빌드·실행 결과와 동작 차이는 [해당 PR의 문서 목록](README.md)에서 확인한다.

근거는 `dcbf09e4f7fd02ff9c8fc6493ec8887fc2919d67`의 [기존 조사](CBRD-27881-oos-refactoring-candidates_dcbf09e_claude.md#candidates-turned-into-draft-prs)다.

<a id="r-11"></a>

### [2026-11-03] R-11 OOS 테스트 seam 정리 재검토

선정 판단은 **과거 보고 유지**이다.

2026-11-03 기록의 분류는 `REPORT-ONLY`였다. 원래 범위는 다음과 같다. 운영 제어 흐름 사이의 #if 테스트 seam을 이름 있는 no-op helper로 변경. 당시 판단과 선행조건도 함께 기록했다. 시험 diff가 seam 함수 10개를 추가해 읽기 이득보다 커져 폐기. publication_count는 두 publish 경로에서 pos와 함께 증가해 항상 같음.

근거는 `dcbf09e4f7fd02ff9c8fc6493ec8887fc2919d67`의 [기존 조사](CBRD-27881-oos-refactoring-candidates_dcbf09e_claude.md#dropped-trials)다.

<a id="r-12"></a>

### [2026-11-03] R-12 코드와 다른 OOS 주석 수정

선정 판단은 **PR 병합 확인**이다.

2026-11-03 기록에서는 `draft PR`로 분류했다. 원래 범위는 다음과 같다. 사실과 다른 OOS 주석을 고치고 주석만 담은 빈 if 제거. 당시 판단과 선행조건도 함께 기록했다. 조사 당시 draft PR.

2026-11-11 확인한 [PR #8373](https://github.com/CUBRID/cubrid/pull/8373)은 병합된 상태였다. 당시 빌드·실행 결과와 동작 차이는 [해당 PR의 문서 목록](README.md)에서 확인한다.

근거는 `dcbf09e4f7fd02ff9c8fc6493ec8887fc2919d67`의 [기존 조사](CBRD-27881-oos-refactoring-candidates_dcbf09e_claude.md#candidates-turned-into-draft-prs)다.

<a id="r-13"></a>

### [2026-11-03] R-13 bestspace 내부 정의 분리

선정 판단은 **판단 보류**이다.

2026-11-03 기록의 분류는 `DEFERRED`였다. 원래 범위는 다음과 같다. bestspace와 header 힌트 내부 정의를 내부 header로 옮기고 layout을 static_assert로 고정. 당시 판단과 선행조건도 함께 기록했다. #8367 병합 후. 같은 oos_file.hpp 영역 변경.

2026-11-11 후속 판단은 다음과 같다. 정의만 옮겨서는 결합 감소 근거가 없어 단독 이동 보류. production 1곳과 test bridge 소비 2곳 확인. #8367 merge가 조사 head의 ancestor. ADR-0008 chunk 변경과 별개.

보존할 계약은 raw header의 field·padding·크기·정렬·초기 bytes, WAL 및 latch 수명.

구현 전 확인과 검증은 실제 revision 사용자 census 및 지원 ABI layout, DB 재개방·복구·bestspace 테스트.

상세 근거와 원문의 제한은 [후속 조사 기록](survey-2026-11-11.md)에 있다.

근거는 `dcbf09e4f7fd02ff9c8fc6493ec8887fc2919d67`의 [기존 조사](CBRD-27881-oos-refactoring-candidates_dcbf09e_claude.md#deferred)다.

<a id="r-14"></a>

### [2026-11-03] R-14 heap 삭제의 OOS 파일 정리 통합

선정 판단은 **PR 병합 확인**이다.

2026-11-03 기록에서는 `draft PR`로 분류했다. 원래 범위는 다음과 같다. xheap_destroy와 xheap_destroy_newly_created의 OOS 파일 정리를 heap_oos_remove_file로 통합. 당시 판단과 선행조건도 함께 기록했다. 조사 당시 draft PR.

2026-11-11 확인한 [PR #8371](https://github.com/CUBRID/cubrid/pull/8371)은 병합된 상태였다. 당시 빌드·실행 결과와 동작 차이는 [해당 PR의 문서 목록](README.md)에서 확인한다.

근거는 `dcbf09e4f7fd02ff9c8fc6493ec8887fc2919d67`의 [기존 조사](CBRD-27881-oos-refactoring-candidates_dcbf09e_claude.md#candidates-turned-into-draft-prs)다.

<a id="r-15"></a>

### [2026-11-03] R-15 class repr 해제와 오류 helper 재검토

선정 판단은 **과거 보고 유지**이다.

2026-11-03 기록의 분류는 `REPORT-ONLY`였다. 원래 범위는 다음과 같다. heap_oos.cpp의 class representation 획득·해제와 last-error 관용구를 helper로 정리. 당시 판단과 선행조건도 함께 기록했다. 시험 결과 이른 반환이 없고 세 쌍 중 둘, 오류 관용구 10곳 중 5곳만 덮으며 들여쓰기가 늘어 폐기.

근거는 `dcbf09e4f7fd02ff9c8fc6493ec8887fc2919d67`의 [기존 조사](CBRD-27881-oos-refactoring-candidates_dcbf09e_claude.md#dropped-trials)다.

<a id="r-16"></a>

### [2026-11-03] R-16 테스트의 page free-space 조회 중복 제거

선정 판단은 **먼저 검토**이다.

2026-11-03 기록의 분류는 `DEFERRED`였다. 원래 범위는 다음과 같다. 테스트 파일마다 복사된 page와 chunk helper를 공용 header로 이동. 당시 판단과 선행조건도 함께 기록했다. #8368 병합 후 새 header 위에 작업.

2026-11-11 후속 판단은 다음과 같다. 다섯 동일 free-space helper, SA 2파일·SERVER 3파일의 호출 26곳을 기존 test_oos_utils.hpp로 모으는 작은 범위. #8368 merge가 조사 head의 ancestor이고 공용 header 존재. peek helper 등 다른 계약은 제외.

보존할 계약은 thread pointer, OLD_PAGE_IF_IN_BUFFER, READ/unconditional latch, 실패 -1, caller assertion 및 unfix 수명.

구현 전 확인과 검증은 실제 revision 대조, SA·SERVER 소비자 빌드와 delete·bestspace·vacuum 실행.

상세 근거와 원문의 제한은 [후속 조사 기록](survey-2026-11-11.md)에 있다.

근거는 `dcbf09e4f7fd02ff9c8fc6493ec8887fc2919d67`의 [기존 조사](CBRD-27881-oos-refactoring-candidates_dcbf09e_claude.md#deferred)다.

<a id="r-17"></a>

### [2026-11-03] R-17 prefetch 조건과 OOS 사전 검사 정리

선정 판단은 **과거 보고 유지**이다.

2026-11-03 기록의 분류는 `REPORT-ONLY`였다. 원래 범위는 다음과 같다. prefetch 조건에 이름을 붙이고 midxkey OOS pre-scan 공유. 당시 판단과 선행조건도 함께 기록했다. 효과가 작음.

근거는 `dcbf09e4f7fd02ff9c8fc6493ec8887fc2919d67`의 [기존 조사](CBRD-27881-oos-refactoring-candidates_dcbf09e_claude.md#report-only)다.

<a id="r-18"></a>

### [2026-11-03] R-18 잠금 상태의 bestspace entry 제거 공유

선정 판단은 **조건 확인 후**이다.

2026-11-03 기록의 분류는 `DEFERRED`였다. 원래 범위는 다음과 같다. bestspace entry 해제 helper와 mutex guard 도입. 당시 판단과 선행조건도 함께 기록했다. #8330 병합 후.

2026-11-11 후속 판단은 다음과 같다. VFID 우선 hash 제거 3곳의 locked entry 제거만 공유하는 선택지. #8330 merge가 조사 head의 ancestor. 반대 순서의 파일 전체 제거와 부분 삽입 정리는 제외. 재설계 완료를 일괄 선행조건으로 두지 않는다.

보존할 계약은 mutex 및 두 hash 제거 순서, free callback·count, recovery growth 재무장, latch와 호출자 제어 흐름.

구현 전 확인과 검증은 실제 revision과 CBRD-27213 진행 재확인, SA·SERVER 빌드와 cache·recovery·reclaim 비교.

상세 근거와 원문의 제한은 [후속 조사 기록](survey-2026-11-11.md)에 있다.

근거는 `dcbf09e4f7fd02ff9c8fc6493ec8887fc2919d67`의 [기존 조사](CBRD-27881-oos-refactoring-candidates_dcbf09e_claude.md#deferred)다.

<a id="r-19"></a>

### [2026-11-03] R-19 테스트 bridge 선언 공유

선정 판단은 **이어서 검토**이다.

2026-11-03 기록의 분류는 `DEFERRED`였다. 원래 범위는 다음과 같다. bridge_* seam 선언을 한 곳에 이동. 당시 판단과 선행조건도 함께 기록했다. #8128과 #8299 모두 병합 후 한 번에 이동.

2026-11-11 후속 판단은 다음과 같다. 기존 private test header에 두 bridge 전역 C++ 선언만 모으는 소규모 선택지. 전체 이동을 #8128·#8299 뒤로 미룬 이력은 보존. 작은 범위는 두 PR 전체 종료를 일괄 선행조건으로 삼지 않는다.

보존할 계약은 정확한 signature·guard·SA/SERVER 가시성. 새 wrapper나 extern C 없음. 호출자 선언 일관성만 검증하며 엔진 정의 타입 검증을 보장하지 않는다.

구현 전 확인과 검증은 실제 revision의 선언과 include 확인, 영향 SA·SERVER target 빌드·링크 및 테스트.

상세 근거와 원문의 제한은 [후속 조사 기록](survey-2026-11-11.md)에 있다.

근거는 `dcbf09e4f7fd02ff9c8fc6493ec8887fc2919d67`의 [기존 조사](CBRD-27881-oos-refactoring-candidates_dcbf09e_claude.md#deferred)다.

<a id="r-20"></a>

### [2026-11-03] R-20 일회성 fault hook 타입 통합

선정 판단은 **판단 보류**이다.

2026-11-03 기록의 분류는 `DEFERRED`였다. 원래 범위는 다음과 같다. 일회성 fault hook 7개를 한 타입으로 통합. 당시 판단과 선행조건도 함께 기록했다. #8299 병합 후.

2026-11-11 후속 판단은 다음과 같다. hook의 소비 시점, memory order, 실패·skip·reset이 달라 arm/exchange 문법만 숨기는 공통 타입은 권하지 않는다. 일괄 추출 보류. DF-26 disarm과 자동 reset은 별도 동작 변경.

보존할 계약은 각 hook의 조건·원자 순서·임계값·오류·skip 및 기존 정리 수명.

구현 전 확인과 검증은 실제 revision 재검토와 test-enabled 및 일반 SA/SERVER 빌드, fault 경로 비교.

상세 근거와 원문의 제한은 [후속 조사 기록](survey-2026-11-11.md)에 있다.

근거는 `dcbf09e4f7fd02ff9c8fc6493ec8887fc2919d67`의 [기존 조사](CBRD-27881-oos-refactoring-candidates_dcbf09e_claude.md#deferred)다.

<a id="r-21"></a>

### [2026-11-03] R-21 bestspace 페이지 검색 함수 분해

선정 판단은 **판단 보류**이다.

2026-11-03 기록의 분류는 `DEFERRED`였다. 원래 범위는 다음과 같다. oos_stats_find_page_in_bestspace 분해. 당시 판단과 선행조건도 함께 기록했다. #8330 병합 후.

2026-11-11 후속 판단은 다음과 같다. 검색 단계 분리는 retry·오류·후보 출처·고정 page 등 전달 상태를 줄인다는 근거가 없어 지역 제어 흐름 유지 권고. #8330 merge가 조사 head의 ancestor. R-18은 별도.

보존할 계약은 hash 우선, 후보 순서, 오류와 stale hint 처리, 출력 index와 WRITE latch 인계.

구현 전 확인과 검증은 CBRD-27213 및 실제 revision에서 인터페이스 이득 재평가, SA·SERVER 및 bestspace·경합 테스트.

상세 근거와 원문의 제한은 [후속 조사 기록](survey-2026-11-11.md)에 있다.

근거는 `dcbf09e4f7fd02ff9c8fc6493ec8887fc2919d67`의 [기존 조사](CBRD-27881-oos-refactoring-candidates_dcbf09e_claude.md#deferred)다.

<a id="r-22"></a>

### [2026-11-03] R-22 페이지 검색의 header 소유와 fallback 정리

선정 판단은 **결함 수정 선행**이다.

2026-11-03 기록의 분류는 `DEFERRED`였다. 원래 범위는 다음과 같다. oos_find_best_page의 header 소유와 fallback 정리. 당시 판단과 선행조건도 함께 기록했다. #8330 병합 및 DF-04 수정 후. fallback 통합이 버려지는 에러를 굳힐 수 있음. DF-04는 2026-11-10 CBRD-28017에 등록.

2026-11-11 후속 판단은 다음과 같다. #8330 포함에도 이른 header-fix fallback이 오류를 버리는 구조. 과거 이슈 없음 기록은 2026-11-03 시점이며 DF-04는 CBRD-28017이 추적.

보존할 계약은 오류 소실을 동작 보존 refactor로 숨기지 않는다.

구현 전 확인과 검증은 CBRD-28017의 DF-04 수정 및 실제 통합 revision 확인.

상세 근거와 원문의 제한은 [후속 조사 기록](survey-2026-11-11.md)에 있다.

근거는 `dcbf09e4f7fd02ff9c8fc6493ec8887fc2919d67`의 [기존 조사](CBRD-27881-oos-refactoring-candidates_dcbf09e_claude.md#deferred)다.

<a id="r-23"></a>

### [2026-11-03] R-23 OOS 읽기의 chain 끝 처리 공유

선정 판단은 **기존 보류**이다.

2026-11-03 기록의 분류는 `DEFERRED`였다. 원래 범위는 다음과 같다. oos_read와 oos_read_many의 chain 끝 helper와 RAII page fix. 당시 판단과 선행조건도 함께 기록했다. #8299 병합 후.

근거는 `dcbf09e4f7fd02ff9c8fc6493ec8887fc2919d67`의 [기존 조사](CBRD-27881-oos-refactoring-candidates_dcbf09e_claude.md#deferred)다.

<a id="r-24"></a>

### [2026-11-03] R-24 OOS 복제 로그 emitter 통합

선정 판단은 **기존 보류**이다.

2026-11-03 기록의 분류는 `DEFERRED`였다. 원래 범위는 다음과 같다. OOS 복제 로그 emitter 하나로 통합. 당시 판단과 선행조건도 함께 기록했다. #8128 병합 후.

근거는 `dcbf09e4f7fd02ff9c8fc6493ec8887fc2919d67`의 [기존 조사](CBRD-27881-oos-refactoring-candidates_dcbf09e_claude.md#deferred)다.

<a id="r-25"></a>

### [2026-11-03] R-25 24바이트 inline stub codec 통합

선정 판단은 **조건 확인 후**이다.

2026-11-03 기록의 분류는 `DEFERRED`였다. 원래 범위는 다음과 같다. 24 B inline stub codec 하나로 통합. 당시 판단과 선행조건도 함께 기록했다. #8299 병합 후.

2026-11-11 후속 판단은 다음과 같다. 24바이트 stub 필드 배치만 공유하는 작은 연산을 검토하되 위치·인터페이스 미정. disk stamp, pending owner index, replica fixup은 별도 계약. #8299 기존 DEFERRED 이력 유지.

보존할 계약은 디스크·pending 검증, replica 길이 보존, capacity·retry, 오류와 이미 쓴 출력 및 소유권.

구현 전 확인과 검증은 실제 통합 revision 확인, byte·오류·출력·복제·SA/SERVER 비교.

상세 근거와 원문의 제한은 [후속 조사 기록](survey-2026-11-11.md)에 있다.

근거는 `dcbf09e4f7fd02ff9c8fc6493ec8887fc2919d67`의 [기존 조사](CBRD-27881-oos-refactoring-candidates_dcbf09e_claude.md#deferred)다.

<a id="r-26"></a>

### [2026-11-03] R-26 RECDES OOS helper 분리

선정 판단은 **통합 revision 재검토**이다.

2026-11-03 기록의 분류는 `DEFERRED`였다. 원래 범위는 다음과 같다. RECDES 수준 OOS helper를 heap_file.c 밖으로 이동. 당시 판단과 선행조건도 함께 기록했다. #8299와 #8350 모두 병합 후.

2026-11-11 후속 판단은 다음과 같다. #8350 merge가 조사 head의 ancestor로 기존 두 선행 PR 중 하나의 소스가 포함됨. 즉시 착수 가능하다는 뜻이 아니다.

보존할 계약은 RECDES helper의 기존 동작 및 소유 경계.

구현 전 확인과 검증은 #8299 의존과 실제 helper 이동 범위를 통합 revision에서 재확인.

상세 근거와 원문의 제한은 [후속 조사 기록](survey-2026-11-11.md)에 있다.

근거는 `dcbf09e4f7fd02ff9c8fc6493ec8887fc2919d67`의 [기존 조사](CBRD-27881-oos-refactoring-candidates_dcbf09e_claude.md#deferred)다.

<a id="r-27"></a>

### [2026-11-03] R-27 demotion planner 분리

선정 판단은 **조건 확인 후**이다.

2026-11-03 기록의 분류는 `DEFERRED`였다. 원래 범위는 다음과 같다. 순수 demotion planner 도입. 당시 판단과 선행조건도 함께 기록했다. #8299 병합 후 DF-02와 함께 결정.

2026-11-11 후속 판단은 다음과 같다. production 직접 호출 1곳. 새 planner 모듈이나 descriptor 복사의 이점은 미입증. 기존 comparator를 쓰는 작은 선택 연산만 조건부 검토. #8299 DEFERRED 이력 유지.

보존할 계약은 강제 선택·24B 조건·우선순위와 동률, header 계산, offset·flag, 할당 및 오류 순서.

구현 전 확인과 검증은 실제 통합 revision에서 복사 없는 경계 이득과 지연 할당을 재검토하고 SA/SERVER 경계 사례 비교.

상세 근거와 원문의 제한은 [후속 조사 기록](survey-2026-11-11.md)에 있다.

근거는 `dcbf09e4f7fd02ff9c8fc6493ec8887fc2919d67`의 [기존 조사](CBRD-27881-oos-refactoring-candidates_dcbf09e_claude.md#deferred)다.

<a id="r-28"></a>

### [2026-11-03] R-28 OOS 파일 구현 분리

선정 판단은 **판단 보류**이다.

2026-11-03 기록의 분류는 `DEFERRED`였다. 원래 범위는 다음과 같다. oos_file.cpp를 bestspace와 reclaim으로 분리. 당시 판단과 선행조건도 함께 기록했다. #8330 병합 후, R-13·R-42·R-43 뒤에 수행.

2026-11-11 후속 판단은 다음과 같다. #8330 소스가 조사 head에 포함됐지만 파일 분리만으로 공유 mutex의 책임이 분리되지 않는다. bestspace와 reclaim을 함께 검토한다.

보존할 계약은 공유 mutex 및 기존 bestspace·reclaim 계약.

구현 전 확인과 검증은 R-13·R-42·R-43 및 accepted reclaim 변경과 실제 revision 확인.

상세 근거와 원문의 제한은 [후속 조사 기록](survey-2026-11-11.md)에 있다.

근거는 `dcbf09e4f7fd02ff9c8fc6493ec8887fc2919d67`의 [기존 조사](CBRD-27881-oos-refactoring-candidates_dcbf09e_claude.md#deferred)다.

<a id="r-29"></a>

### [2026-11-03] R-29 미사용 복구 인덱스 삭제 제안

선정 판단은 **통합 설계 확인**이다.

2026-11-03 기록의 분류는 `DEFERRED`였다. 원래 범위는 다음과 같다. 기록하는 곳이 없는 RVREPL_OOS_DELETE 삭제와 복구 주석 및 rv handler 이름 정리. 당시 판단과 선행조건도 함께 기록했다. 별도 PR 대신 같은 종류의 인덱스를 제거하고 번호를 다시 매기는 #8347에 합치기 제안.

2026-11-11 후속 판단은 다음과 같다. #8347은 당시 미병합 종료. 과거 합치기 제안은 그대로 실행할 수 없다. 당시 미병합 #8434는 RVOOS_NOTIFY_VACUUM을 기록하고 소비한다. 이름 검색에서 RVREPL_OOS_DELETE emitter가 발견되지 않았으나 과거·외부·숫자 참조의 미사용 증명이 아니다. 인덱스 삭제·재번호를 기계적으로 합치지 않는다.

보존할 계약은 살아 있는 알림·postpone, 위치 기반 RV_fun 및 MVCC·logical·TDE 분류와 이전 로그 정책.

구현 전 확인과 검증은 실제 통합 복구 형식·기록자·소비자·이전 로그 정책 결정, SERVER·SA 및 rollback·restart·HA 검증.

상세 근거와 원문의 제한은 [후속 조사 기록](survey-2026-11-11.md)에 있다.

근거는 `dcbf09e4f7fd02ff9c8fc6493ec8887fc2919d67`의 [기존 조사](CBRD-27881-oos-refactoring-candidates_dcbf09e_claude.md#deferred)다.

<a id="r-30"></a>

### [2026-11-03] R-30 SQL 테스트 등록 목록 공유

선정 판단은 **이어서 검토**이다.

2026-11-03 기록의 분류는 `DEFERRED`였다. 원래 범위는 다음과 같다. 테스트 등록 CMake helper 도입. 당시 판단과 선행조건도 함께 기록했다. #8128 병합 후.

2026-11-11 후속 판단은 다음과 같다. 공유 DB 테스트 13개의 명시 목록을 등록과 공통 속성에 재사용하는 작은 범위. source glob은 target 생성만 맡고 recovery fixture와 deferred timeout override를 유지. #8128 DEFERRED 이력 유지.

보존할 계약은 target·명령·fixture·lock·serial·환경·timeout 및 속성 부재. pending boundaries 병렬 안전성은 별도 미확인.

구현 전 확인과 검증은 실제 통합 revision 확인, 전후 CTest JSON·target 비교 및 영향 빌드와 fixture별 실행.

상세 근거와 원문의 제한은 [후속 조사 기록](survey-2026-11-11.md)에 있다.

근거는 `dcbf09e4f7fd02ff9c8fc6493ec8887fc2919d67`의 [기존 조사](CBRD-27881-oos-refactoring-candidates_dcbf09e_claude.md#deferred)다.

<a id="r-31"></a>

### [2026-11-03] R-31 SQL 테스트 fixture 공통화

선정 판단은 **기존 보류**이다.

2026-11-03 기록의 분류는 `DEFERRED`였다. 원래 범위는 다음과 같다. SQL 테스트 fixture 기반 클래스 도입. 당시 판단과 선행조건도 함께 기록했다. #8128과 #8299 모두 병합 후 한 번에 이동.

근거는 `dcbf09e4f7fd02ff9c8fc6493ec8887fc2919d67`의 [기존 조사](CBRD-27881-oos-refactoring-candidates_dcbf09e_claude.md#deferred)다.

<a id="r-32"></a>

### [2026-11-03] R-32 큰 OOS 테스트 파일 분리

선정 판단은 **기존 보류**이다.

2026-11-03 기록의 분류는 `DEFERRED`였다. 원래 범위는 다음과 같다. 큰 테스트 파일 분리. 당시 판단과 선행조건도 함께 기록했다. #8299 병합 후.

근거는 `dcbf09e4f7fd02ff9c8fc6493ec8887fc2919d67`의 [기존 조사](CBRD-27881-oos-refactoring-candidates_dcbf09e_claude.md#deferred)다.

<a id="r-33"></a>

### [2026-11-03] R-33 복제 LSA 상태와 suppression guard 정리

선정 판단은 **통합 설계 확인**이다.

2026-11-03 기록의 분류는 `DEFERRED`였다. 원래 범위는 다음과 같다. tdes의 OOS 복제 LSA 상태 타입과 중첩 suppression guard 도입. 당시 판단과 선행조건도 함께 기록했다. #8299와 #8330 병합 후. WAL 경로이므로 별도 리뷰.

2026-11-11 후속 판단은 다음과 같다. FIFO 큐와 thread 참조 vector의 서로 다른 수명, 일반 억제와 OOS 자동 enqueue 억제는 합치지 않는다. 기존 flag 복원 guard의 동작 변경 가능성 및 간접 재진입 도달성은 미확인. R-48 중복 추가 없음.

보존할 계약은 FK 전체 컨테이너 swap 및 복원, dummy·tail LSA와 참조 순서, 오류 cleanup과 transaction undo 경계.

구현 전 확인과 검증은 실제 통합 revision의 #8299·#8434 영향 재확인, 실패·rollback·restart·HA 검증.

상세 근거와 원문의 제한은 [후속 조사 기록](survey-2026-11-11.md)에 있다.

근거는 `dcbf09e4f7fd02ff9c8fc6493ec8887fc2919d67`의 [기존 조사](CBRD-27881-oos-refactoring-candidates_dcbf09e_claude.md#deferred)다.

<a id="r-34"></a>

### [2026-11-03] R-34 tier-3 bestspace sync 처리 결정

선정 판단은 **CBRD-27213 이관**이다.

2026-11-03 기록의 분류는 `NEEDS-DECISION`였다. 원래 범위는 다음과 같다. 운영 경로에서 쓰이지 않는 tier-3 sync 추정치, second_best ring, idx_badspace와 sync 상수를 고치거나 삭제. 당시 판단과 선행조건도 함께 기록했다. DF-01. 사양 §2대로 고치면 결함 수정이며 삭제 시 사양도 변경. CBRD-27213은 삭제 후 heap bestspace 재설계 방향.

2026-11-11 후속 판단은 다음과 같다. 담당자는 tier-3 sync를 별도 수리하지 않고 CBRD-27213 재설계에서 legacy 구조와 함께 제거하기로 결정. 별도 refactor가 아닌 재설계로 이관. 제거 완료를 뜻하지 않는다.

보존할 계약은 사양과 재설계의 정합성은 해당 작업에서 처리.

구현 전 확인과 검증은 CBRD-27213 실제 구현 및 사양 변경 확인.

상세 근거와 원문의 제한은 [후속 조사 기록](survey-2026-11-11.md)에 있다.

근거는 `dcbf09e4f7fd02ff9c8fc6493ec8887fc2919d67`의 [기존 조사](CBRD-27881-oos-refactoring-candidates_dcbf09e_claude.md#needs-decision)다.

<a id="r-35"></a>

### [2026-11-03] R-35 flush insert 매크로 분리 여부 결정

선정 판단은 **담당자 결정 대기**이다.

2026-11-03 기록의 분류는 `NEEDS-DECISION`였다. 원래 범위는 다음과 같다. LC_IS_FLUSH_INSERT를 일반용과 OOS용으로 나누거나 유지. 당시 판단과 선행조건도 함께 기록했다. 현재 일반 insert와 LC_FLUSH_INSERT_OOS를 함께 참으로 판정. 오래된 TODO는 PR7에서 설명으로 변경.

근거는 `dcbf09e4f7fd02ff9c8fc6493ec8887fc2919d67`의 [기존 조사](CBRD-27881-oos-refactoring-candidates_dcbf09e_claude.md#needs-decision)다.

<a id="r-36"></a>

### [2026-11-03] R-36 손상 오류 반환 매크로 도입 결정

선정 판단은 **담당자 결정 대기**이다.

2026-11-03 기록의 분류는 `NEEDS-DECISION`였다. 원래 범위는 다음과 같다. 반복되는 손상 검출 exit 16곳에 OOS_RETURN_ERROR 같은 매크로 사용 여부 결정. 당시 판단과 선행조건도 함께 기록했다. CUBRID 관례로 매크로를 받아들일지 판단 필요.

근거는 `dcbf09e4f7fd02ff9c8fc6493ec8887fc2919d67`의 [기존 조사](CBRD-27881-oos-refactoring-candidates_dcbf09e_claude.md#needs-decision)다.

<a id="r-37"></a>

### [2026-11-03] R-37 중복 또는 무검증 테스트 삭제 여부 결정

선정 판단은 **담당자 결정 대기**이다.

2026-11-03 기록의 분류는 `NEEDS-DECISION`였다. 원래 범위는 다음과 같다. test_oos_mock_vacuum_server.cpp와 test_oos.cpp의 중복 또는 검증 없는 케이스 삭제 여부 결정. 당시 판단과 선행조건도 함께 기록했다. 읽기만으로 판정했으며 CBRD-26659 테스트 유지 정책 판단 필요.

근거는 `dcbf09e4f7fd02ff9c8fc6493ec8887fc2919d67`의 [기존 조사](CBRD-27881-oos-refactoring-candidates_dcbf09e_claude.md#needs-decision)다.

<a id="r-38"></a>

### [2026-11-03] R-38 테스트 로그 계층 유지 범위 결정

선정 판단은 **담당자 결정 대기**이다.

2026-11-03 기록의 분류는 `NEEDS-DECISION`였다. 원래 범위는 다음과 같다. test_oos_log.hpp 계층을 삭제하거나 test_oos_debug만 유지. 당시 판단과 선행조건도 함께 기록했다. 호출 45곳의 계층이 기본값에서 출력하지 않음.

근거는 `dcbf09e4f7fd02ff9c8fc6493ec8887fc2919d67`의 [기존 조사](CBRD-27881-oos-refactoring-candidates_dcbf09e_claude.md#needs-decision)다.

<a id="r-39"></a>

### [2026-11-03] R-39 FILE_OOS 진단 문자열 변경 여부 결정

선정 판단은 **CBRD-28023 이관**이다.

2026-11-03 기록의 분류는 `NEEDS-DECISION`였다. 원래 범위는 다음과 같다. OUT_OF_LINE_OVERFLOW_STORAGE 진단 문자열을 기능 이름 Out-of-row Overflow Storage에 맞출지 결정. 당시 판단과 선행조건도 함께 기록했다. 사용자에게 보이는 출력. 변경 시 diagdb 답안 변경 가능성은 추론.

2026-11-11 후속 판단은 다음과 같다. 기능 이름에 맞게 develop 병합 전에 진단 문자열 변경 결정. CBRD-28023이 추적. 사용자 출력 변경이므로 동작 보존 정리와 구분. 당시 fixed head 문자열은 OUT_OF_LINE_OVERFLOW_STORAGE.

보존할 계약은 정확한 새 문자열과 테스트 변경 범위는 미정.

구현 전 확인과 검증은 CBRD-28023 ANALYSIS에서 문자열과 테스트 범위 결정 및 구현 확인.

상세 근거와 원문의 제한은 [후속 조사 기록](survey-2026-11-11.md)에 있다.

근거는 `dcbf09e4f7fd02ff9c8fc6493ec8887fc2919d67`의 [기존 조사](CBRD-27881-oos-refactoring-candidates_dcbf09e_claude.md#needs-decision)다.

<a id="r-40"></a>

### [2026-11-03] R-40 셸 DB 수명 helper와 도구 정리

선정 판단은 **과거 보고 유지**이다.

2026-11-03 기록의 분류는 `REPORT-ONLY`였다. 원래 범위는 다음과 같다. 셸 DB 수명 helper 도입과 일회성 도구 이동. 당시 판단과 선행조건도 함께 기록했다. CBRD-26659 스크립트 작업 및 #8347과 겹침.

근거는 `dcbf09e4f7fd02ff9c8fc6493ec8887fc2919d67`의 [기존 조사](CBRD-27881-oos-refactoring-candidates_dcbf09e_claude.md#report-only)다.

<a id="r-41"></a>

### [2026-11-03] R-41 파일 수집기와 bitmap 순회 정리

선정 판단은 **과거 보고 유지**이다.

2026-11-03 기록의 분류는 `REPORT-ONLY`였다. 원래 범위는 다음과 같다. FILE_FTAB_COLLECTOR RAII와 bitmap 순회 helper. 당시 판단과 선행조건도 함께 기록했다. lambda와 stop flag가 sweep 루프에 상태 추가.

근거는 `dcbf09e4f7fd02ff9c8fc6493ec8887fc2919d67`의 [기존 조사](CBRD-27881-oos-refactoring-candidates_dcbf09e_claude.md#report-only)다.

<a id="r-42"></a>

### [2026-11-03] R-42 reclaim 페이지 처리 단계 분리

선정 판단은 **과거 보고 유지**이다.

2026-11-03 기록의 분류는 `REPORT-ONLY`였다. 원래 범위는 다음과 같다. oos_try_reclaim_page_internal 단계 분리. 당시 판단과 선행조건도 함께 기록했다. 래치, WAL, LSA gate 순서를 건드림.

근거는 `dcbf09e4f7fd02ff9c8fc6493ec8887fc2919d67`의 [기존 조사](CBRD-27881-oos-refactoring-candidates_dcbf09e_claude.md#report-only)다.

<a id="r-43"></a>

### [2026-11-03] R-43 reclaim sweep 단계와 registry 분리

선정 판단은 **과거 보고 유지**이다.

2026-11-03 기록의 분류는 `REPORT-ONLY`였다. 원래 범위는 다음과 같다. reclaim sweep 단계 분리와 side map registry 클래스. 당시 판단과 선행조건도 함께 기록했다. single-flight와 condvar 동작을 건드림.

근거는 `dcbf09e4f7fd02ff9c8fc6493ec8887fc2919d67`의 [기존 조사](CBRD-27881-oos-refactoring-candidates_dcbf09e_claude.md#report-only)다.

<a id="r-44"></a>

### [2026-11-03] R-44 cache API 계약 정리

선정 판단은 **과거 보고 유지**이다.

2026-11-03 기록의 분류는 `REPORT-ONLY`였다. 원래 범위는 다음과 같다. cache API 계약 정리. 당시 판단과 선행조건도 함께 기록했다. redo 경로를 건드림.

근거는 `dcbf09e4f7fd02ff9c8fc6493ec8887fc2919d67`의 [기존 조사](CBRD-27881-oos-refactoring-candidates_dcbf09e_claude.md#report-only)다.

<a id="r-45"></a>

### [2026-11-03] R-45 sysop guard 도입 검토

선정 판단은 **과거 보고 유지**이다.

2026-11-03 기록의 분류는 `REPORT-ONLY`였다. 원래 범위는 다음과 같다. sysop RAII guard 도입. 당시 판단과 선행조건도 함께 기록했다. 소멸 순서 오류가 복구 버그가 될 수 있음.

근거는 `dcbf09e4f7fd02ff9c8fc6493ec8887fc2919d67`의 [기존 조사](CBRD-27881-oos-refactoring-candidates_dcbf09e_claude.md#report-only)다.

<a id="r-46"></a>

### [2026-11-03] R-46 chunk header peek helper 도입 검토

선정 판단은 **과거 보고 유지**이다.

2026-11-03 기록의 분류는 `REPORT-ONLY`였다. 원래 범위는 다음과 같다. chunk header peek helper 도입. 당시 판단과 선행조건도 함께 기록했다. 운영 복사본이 두 개뿐이며 에러 매핑이 다름.

근거는 `dcbf09e4f7fd02ff9c8fc6493ec8887fc2919d67`의 [기존 조사](CBRD-27881-oos-refactoring-candidates_dcbf09e_claude.md#report-only)다.

<a id="r-47"></a>

### [2026-11-03] R-47 insert API 배관 정리

선정 판단은 **과거 보고 유지**이다.

2026-11-03 기록의 분류는 `REPORT-ONLY`였다. 원래 범위는 다음과 같다. insert API 배관 정리. 당시 판단과 선행조건도 함께 기록했다. 작은 단계만 떼면 효과가 작음.

근거는 `dcbf09e4f7fd02ff9c8fc6493ec8887fc2919d67`의 [기존 조사](CBRD-27881-oos-refactoring-candidates_dcbf09e_claude.md#report-only)다.

<a id="r-48"></a>

### [2026-11-03] R-48 페이지 간 삽입 복제 guard 정리

선정 판단은 **과거 보고 유지**이다.

2026-11-03 기록의 분류는 `REPORT-ONLY`였다. 원래 범위는 다음과 같다. oos_insert_across_pages의 복제 guard 타입 도입. 당시 판단과 선행조건도 함께 기록했다. HA 확인 수단이 거의 없음.

근거는 `dcbf09e4f7fd02ff9c8fc6493ec8887fc2919d67`의 [기존 조사](CBRD-27881-oos-refactoring-candidates_dcbf09e_claude.md#report-only)다.

<a id="r-49"></a>

### [2026-11-03] R-49 chain 삭제의 head 검증 분리 검토

선정 판단은 **과거 보고 유지**이다.

2026-11-03 기록의 분류는 `REPORT-ONLY`였다. 원래 범위는 다음과 같다. oos_delete_chain에서 head 검증 분리. 당시 판단과 선행조건도 함께 기록했다. CBRD-26950 안전장치를 건드림.

근거는 `dcbf09e4f7fd02ff9c8fc6493ec8887fc2919d67`의 [기존 조사](CBRD-27881-oos-refactoring-candidates_dcbf09e_claude.md#report-only)다.

<a id="r-50"></a>

### [2026-11-03] R-50 physical log helper의 const_cast 정리

선정 판단은 **과거 보고 유지**이다.

2026-11-03 기록의 분류는 `REPORT-ONLY`였다. 원래 범위는 다음과 같다. const_cast 없는 physical log helper. 당시 판단과 선행조건도 함께 기록했다. heap_file.c의 LOG_DATA_ADDR 관용구와 달라짐.

근거는 `dcbf09e4f7fd02ff9c8fc6493ec8887fc2919d67`의 [기존 조사](CBRD-27881-oos-refactoring-candidates_dcbf09e_claude.md#report-only)다.

<a id="r-51"></a>

### [2026-11-03] R-51 작은 코드 정리 항목 검토

선정 판단은 **과거 보고 유지**이다.

2026-11-03 기록의 분류는 `REPORT-ONLY`였다. 원래 범위는 다음과 같다. 작은 코드 nit 모음. 당시 판단과 선행조건도 함께 기록했다. 효과가 작음.

근거는 `dcbf09e4f7fd02ff9c8fc6493ec8887fc2919d67`의 [기존 조사](CBRD-27881-oos-refactoring-candidates_dcbf09e_claude.md#report-only)다.

<a id="r-52"></a>

### [2026-11-03] R-52 페이지 초기화 callback 반환값 정리 검토

선정 판단은 **기각**이다.

2026-11-03 기록의 분류는 `REJECTED`였다. 원래 범위는 다음과 같다. oos_vpid_init_new 반환값 변경 제안. 당시 판단과 선행조건도 함께 기록했다. FILE_INIT_PAGE_FUNC callback이므로 signature 변경 불가.

근거는 `dcbf09e4f7fd02ff9c8fc6493ec8887fc2919d67`의 [기존 조사](CBRD-27881-oos-refactoring-candidates_dcbf09e_claude.md#candidates-left-out-of-prs)다.

<a id="r-53"></a>

### [2026-11-03] R-53 VOT decoder 공용 accessor 사용 검토

선정 판단은 **과거 보고 유지**이다.

2026-11-03 기록의 분류는 `REPORT-ONLY`였다. 원래 범위는 다음과 같다. VOT entry decoder가 공용 accessor 사용. 당시 판단과 선행조건도 함께 기록했다. INT와 부호 처리 동작이 바뀌므로 DF-07로 보냄.

근거는 `dcbf09e4f7fd02ff9c8fc6493ec8887fc2919d67`의 [기존 조사](CBRD-27881-oos-refactoring-candidates_dcbf09e_claude.md#report-only)다.

<a id="r-54"></a>

### [2026-11-03] R-54 OOS payload 소유권 타입 검토

선정 판단은 **과거 보고 유지**이다.

2026-11-03 기록의 분류는 `REPORT-ONLY`였다. 원래 범위는 다음과 같다. 소유권을 가진 OOS payload 타입 도입. 당시 판단과 선행조건도 함께 기록했다. 여러 파일과 allocator 변경 필요.

근거는 `dcbf09e4f7fd02ff9c8fc6493ec8887fc2919d67`의 [기존 조사](CBRD-27881-oos-refactoring-candidates_dcbf09e_claude.md#report-only)다.

<a id="r-55"></a>

### [2026-11-03] R-55 eager cleanup gate helper 검토

선정 판단은 **과거 보고 유지**이다.

2026-11-03 기록의 분류는 `REPORT-ONLY`였다. 원래 범위는 다음과 같다. eager cleanup gate helper 도입. 당시 판단과 선행조건도 함께 기록했다. 줄어드는 양이 적음. 주석 부분은 PR7에 반영.

근거는 `dcbf09e4f7fd02ff9c8fc6493ec8887fc2919d67`의 [기존 조사](CBRD-27881-oos-refactoring-candidates_dcbf09e_claude.md#report-only)다.

<a id="r-56"></a>

### [2026-11-03] R-56 복제 OOS 레코드 재구성 정리

선정 판단은 **과거 보고 유지**이다.

2026-11-03 기록의 분류는 `REPORT-ONLY`였다. 원래 범위는 다음과 같다. la_rebuild_oos_recdes 정리. 당시 판단과 선행조건도 함께 기록했다. HA 경로로 단위 테스트와 /run all로 확인 불가.

근거는 `dcbf09e4f7fd02ff9c8fc6493ec8887fc2919d67`의 [기존 조사](CBRD-27881-oos-refactoring-candidates_dcbf09e_claude.md#report-only)다.

<a id="r-57"></a>

### [2026-11-03] R-57 현재 로그 정보 구조체 배열 검토

선정 판단은 **과거 보고 유지**이다.

2026-11-03 기록의 분류는 `REPORT-ONLY`였다. 원래 범위는 다음과 같다. la_get_current를 구조체 배열로 변경. 당시 판단과 선행조건도 함께 기록했다. 빌드 외 확인 수단이 없음.

근거는 `dcbf09e4f7fd02ff9c8fc6493ec8887fc2919d67`의 [기존 조사](CBRD-27881-oos-refactoring-candidates_dcbf09e_claude.md#report-only)다.

<a id="r-58"></a>

### [2026-11-03] R-58 sql.log OOS cache 클래스 분리 검토

선정 판단은 **과거 보고 유지**이다.

2026-11-03 기록의 분류는 `REPORT-ONLY`였다. 원래 범위는 다음과 같다. sql.log OOS cache를 별도 TU 클래스로 분리. 당시 판단과 선행조건도 함께 기록했다. 300줄 넘는 변경.

근거는 `dcbf09e4f7fd02ff9c8fc6493ec8887fc2919d67`의 [기존 조사](CBRD-27881-oos-refactoring-candidates_dcbf09e_claude.md#report-only)다.

<a id="r-59"></a>

### [2026-11-03] R-59 파일 header class OID helper 검토

선정 판단은 **과거 보고 유지**이다.

2026-11-03 기록의 분류는 `REPORT-ONLY`였다. 원래 범위는 다음과 같다. file_header_get_class_oid helper 도입. 당시 판단과 선행조건도 함께 기록했다. OOS 이전부터 있던 중복.

근거는 `dcbf09e4f7fd02ff9c8fc6493ec8887fc2919d67`의 [기존 조사](CBRD-27881-oos-refactoring-candidates_dcbf09e_claude.md#report-only)다.

<a id="r-60"></a>

### [2026-11-03] R-60 OOS 저장 속성 mask 검토

선정 판단은 **과거 보고 유지**이다.

2026-11-03 기록의 분류는 `REPORT-ONLY`였다. 원래 범위는 다음과 같다. SM_ATTFLAG_OOS_STORAGE_MASK 도입. 당시 판단과 선행조건도 함께 기록했다. 재빌드 범위가 넓고 효과가 작음.

근거는 `dcbf09e4f7fd02ff9c8fc6493ec8887fc2919d67`의 [기존 조사](CBRD-27881-oos-refactoring-candidates_dcbf09e_claude.md#report-only)다.

<a id="r-61"></a>

### [2026-11-03] R-61 복제 적용 prologue helper 검토

선정 판단은 **과거 보고 유지**이다.

2026-11-03 기록의 분류는 `REPORT-ONLY`였다. 원래 범위는 다음과 같다. la_apply_* prologue helper 도입. 당시 판단과 선행조건도 함께 기록했다. flush 묶음 처리를 건드리고 단위 테스트가 없음.

근거는 `dcbf09e4f7fd02ff9c8fc6493ec8887fc2919d67`의 [기존 조사](CBRD-27881-oos-refactoring-candidates_dcbf09e_claude.md#report-only)다.

<a id="r-62"></a>

### [2026-11-03] R-62 overflow 목록 해제와 header 분리 검토

선정 판단은 **과거 보고 유지**이다.

2026-11-03 기록의 분류는 `REPORT-ONLY`였다. 원래 범위는 다음과 같다. ovf_list 해제 helper 및 oos_record_header.hpp 분리. 당시 판단과 선행조건도 함께 기록했다. 효과가 작음.

근거는 `dcbf09e4f7fd02ff9c8fc6493ec8887fc2919d67`의 [기존 조사](CBRD-27881-oos-refactoring-candidates_dcbf09e_claude.md#report-only)다.

<a id="r-63"></a>

### [2026-11-03] R-63 SA와 SERVER 테스트 본문 공유 검토

선정 판단은 **과거 보고 유지**이다.

2026-11-03 기록의 분류는 `REPORT-ONLY`였다. 원래 범위는 다음과 같다. 대칭 테스트 본문을 .inc로 공유. 당시 판단과 선행조건도 함께 기록했다. macro로 펼쳐지는 TEST 본문은 읽기 어려움.

근거는 `dcbf09e4f7fd02ff9c8fc6493ec8887fc2919d67`의 [기존 조사](CBRD-27881-oos-refactoring-candidates_dcbf09e_claude.md#report-only)다.

<a id="r-64"></a>

### [2026-11-03] R-64 OOS 파일 테스트 fixture 정리 검토

선정 판단은 **과거 보고 유지**이다.

2026-11-03 기록의 분류는 `REPORT-ONLY`였다. 원래 범위는 다음과 같다. OosFileTest fixture와 insert_string helper 정리. 당시 판단과 선행조건도 함께 기록했다. 범위가 크며 R-07과 R-16 뒤에 검토.

근거는 `dcbf09e4f7fd02ff9c8fc6493ec8887fc2919d67`의 [기존 조사](CBRD-27881-oos-refactoring-candidates_dcbf09e_claude.md#report-only)다.

<a id="r-65"></a>

### [2026-11-03] R-65 OOS 테스트 main 연결 정리 검토

선정 판단은 **과거 보고 유지**이다.

2026-11-03 기록의 분류는 `REPORT-ONLY`였다. 원래 범위는 다음과 같다. OOS_TEST_MAIN과 gtest_main 연결 정리. 당시 판단과 선행조건도 함께 기록했다. 효과가 작음.

근거는 `dcbf09e4f7fd02ff9c8fc6493ec8887fc2919d67`의 [기존 조사](CBRD-27881-oos-refactoring-candidates_dcbf09e_claude.md#report-only)다.

<a id="r-66"></a>

### [2026-11-03] R-66 통계 조회 함수 이동 검토

선정 판단은 **과거 보고 유지**이다.

2026-11-03 기록의 분류는 `REPORT-ONLY`였다. 원래 범위는 다음과 같다. xoos_get_stats_by_class_oid를 heap_oos.cpp로 이동. 당시 판단과 선행조건도 함께 기록했다. 이미 테스트 빌드 전용.

근거는 `dcbf09e4f7fd02ff9c8fc6493ec8887fc2919d67`의 [기존 조사](CBRD-27881-oos-refactoring-candidates_dcbf09e_claude.md#report-only)다.

<a id="r-70"></a>

### [2026-11-03] R-70 형태만 바꾸는 변경 제외

선정 판단은 **기각**이다.

2026-11-03 기록의 분류는 `REJECTED`였다. 원래 범위는 다음과 같다. 형태만 바꾸는 변경 모음. 당시 판단과 선행조건도 함께 기록했다. 리뷰어에게 잡음이 됨. 개별 변경 내용은 보고서에 기록되지 않음.

근거는 `dcbf09e4f7fd02ff9c8fc6493ec8887fc2919d67`의 [기존 조사](CBRD-27881-oos-refactoring-candidates_dcbf09e_claude.md#candidates-left-out-of-prs)다.

<a id="r-71"></a>

### [2026-11-03] R-71 여러 sector의 OOS 통계 테스트 보강

선정 판단은 **과거 보고 유지**이다.

2026-11-03 기록의 분류는 `REPORT-ONLY`였다. 원래 범위는 다음과 같다. sector 하나보다 큰 파일에서 SHOW HEAP OOS 경로의 num_recs와 recs_sumlen 확인. 당시 판단과 선행조건도 함께 기록했다. 결함은 발견하지 못함. 기존 sweep cursor 테스트는 통계를 확인하지 않음. #7614 테스트는 API와 성장 게이트 변경으로 그대로 이식 불가. sync 검증은 CBRD-27213에서 sync 삭제 시 불필요.

근거는 `dcbf09e4f7fd02ff9c8fc6493ec8887fc2919d67`의 [기존 조사](CBRD-27881-oos-refactoring-candidates_dcbf09e_claude.md#report-only)다.

<a id="n-20261111-01"></a>

### [2026-11-11] N-20261111-01 STORAGE 거부 검사 재사용

선정 판단은 **조건 확인 후**이다.

attr_def_one의 CLASS·SHARED STORAGE 거부 중복을 기존 위치에서 parser_reject_non_normal_attr_storage 호출로 교체한다. namespace 거부 규칙의 중복을 줄인다.

보존할 동작은 다음과 같다. 진입점에서만 mask와 non-UNSET 조건이 동치다. 거부 후 reset, 오류 내용·위치·순서, visibility 및 중복 진단과 늦은 ALTER 검사를 유지한다. 호출을 reset 뒤로 옮기지 않는다.

구현 시 남은 검증은 다음과 같다. parser 재생성 및 conflict 비교, test_oos_sql_storage와 SA·CS에서 정상·오류 SQL 진단 비교. 유한 모델과 생성 table 확인은 실제 parser 실행이 아니다.

근거 소스는 `50619ce53ef7b0e6bc8b468b2065ae7da4ef592f`다. 기존 항목과의 중복 판정, source anchor와 정적 확인 범위는 [2026-11-11 조사](survey-2026-11-11.md)에 있다.

<a id="n-20261111-02"></a>

### [2026-11-11] N-20261111-02 SQL 테스트 정수 변환 공유

선정 판단은 **먼저 검토**이다.

get_int_column을 기존 SQL 공용 header로 옮겨 cursor 위치 선정에 성공한 fetch_single_int가 column 0 변환에 재사용한다. 중복 정수 변환 규칙을 한 곳에서 관리한다.

보존할 동작은 다음과 같다. INTEGER·BIGINT·SHORT cast, NULL·다른 타입, fetch 실패, out_val 대입 및 DB_VALUE clear 분기 유지. cursor와 result 종료는 호출자 책임이며 db_query_end 결과는 기존처럼 무시한다. SHOW 호출자의 반복 열 조회를 유지한다.

구현 시 남은 검증은 다음과 같다. 모든 OOS SQL target 빌드 및 SHOW·deferred-write·transaction 실행. 오류와 빈 결과, 큰 BIGINT는 동일 compiler/platform의 기존 결과와 비교한다.

근거 소스는 `50619ce53ef7b0e6bc8b468b2065ae7da4ef592f`다. 기존 항목과의 중복 판정, source anchor와 정적 확인 범위는 [2026-11-11 조사](survey-2026-11-11.md)에 있다.

## 목록 검증

문서 디렉터리에서 `python3 check-candidate-index.py`를 실행한다. 기존 68개와 신규 2개의 ID, 제목의 날짜 형식, 고정 앵커와 인덱스 연결, 원문 보존 및 로컬 문서 링크를 대조한다.
