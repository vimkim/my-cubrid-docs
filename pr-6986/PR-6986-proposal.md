# OOS Vacuum L1 누수 — 옵션 제안서 (이력 보존판)

**작성자:** Daehyun Kim (vimkim)
**최초 작성일:** 2026-04-17
**재작성일:** 2026-04-20
**관련 PR:** [CUBRID/cubrid#6986](https://github.com/CUBRID/cubrid/pull/6986) — [CBRD-26668] Wire vacuum to clean up OOS records after DELETE/UPDATE
**HEAD commit:** `31e6e9dc6`
**관련 JIRA:** CBRD-26668 (본 PR), CBRD-26517 (OOS 메인)
**이전 버전과의 관계:** 2026-04-17 원 제안서의 Option B가 추천 방향이었으나, 2026-04-20에 더 근본적인 재설계(Option A-lite)가 채택되었다. 본 문서는 그 경과와 미채택 옵션의 평가를 보존한다.

---

## 1. 현재 상태 고지

본 제안서는 **이미 결정된 설계의 대안 기록물**이다. 네 개의 원 옵션(A/B/C/D) 중 어느 것도 채택되지 않았으며, 커밋 `f912b720c`가 도입한 **Option A-lite — 백워드 체인 워커 제거 + 포워드 워크 inline 정리**가 실제 구현이다. 본 제안서의 원 내용은 당시 팀 의사결정의 컨텍스트를 기록하기 위해 보존되며, 장 3 이하에서 현재 구현과 각 옵션을 대조한다.

---

## 2. 역사적 맥락 — 원 제안 4개 옵션 요약

2026-04-17자 원 제안서에서는 `899d5b633`의 VFID 가드로 인해 수용된 **L1 누수**(UPDATE가 OOS 컬럼을 non-OOS 값으로 교체한 뒤 DELETE되면 구버전 OOS가 영구 고아로 남음)를 해소하기 위한 네 가지 옵션을 검토했다.

| 옵션 | 요지 | 추정 공수 | 포맷 변경 |
|---|---|---|---|
| A | 가드 제거, 모든 MVCC UPDATE에서 체인 순회 | 1인일 | 없음 |
| B | 페이지 단위 `has_oos_file` 캐싱, heap 헤더 1회 조회 후 재사용 | 2–3인일 | 없음 |
| C | MVCC 헤더에 `HAS_PREV_OOS` 플래그 비트 추가 | 5–8인일 | 헤더 포맷 |
| D | 구버전 OOS OID를 현재 heap 레코드에 embed | 15–25인일 | 레코드 포맷 |

원 제안서의 추천은 Option B였다. 성능 회귀를 피하면서 L1을 해결하고, 포맷 변경 없이 recovery/replication 영향이 없다는 이유였다.

---

## 3. 채택된 해결책 — Option A-lite

### 3.1 개요

`f912b720c`에 의해 다음이 동시에 이루어졌다.

1. `vacuum_cleanup_prev_version_oos()` 함수 본체 제거 (약 250줄).
2. `vacuum_heap_record` REMOVE 경로의 트리거 블록 및 `need_prev_version_oos_cleanup` 전체 삭제.
3. 포워드 선언 제거.
4. `vacuum_process_log_block`의 기존 MVCC 로그 순회(`src/query/vacuum.c:3621-3725`) 내부에 inline OOS 정리 블록 추가.
5. 블록당 16-엔트리 stack-local VFID 캐시 도입(`src/query/vacuum.c:3336-3410`).

정리 책임이 "REMOVE 경로의 백워드 체인 순회"에서 "forward log walk가 이미 방문하는 MVCC 힙 연산 로그 레코드에서의 inline 디코드"로 이동했다. 각 과거 버전은 자기 자신이 생성한 MVCC 힙 로그 레코드가 vacuum 블록 순회 중 만날 때 자동으로 정리된다.

### 3.2 Option A-lite가 B/C/D 대비 우수한 이유

#### Option B 대비

- B는 `VACUUM_HEAP_HELPER`에 tri-state 캐시를 두고 `vacuum_heap_page` 진입 시 heap 헤더 페이지에 **READ latch**를 걸어 OOS 파일 존재 여부를 조회하는 방식이었다.
- A-lite의 블록 VFID 캐시는 `file_descriptor_get` + `heap_oos_find_vfid`만 사용하며 heap 헤더 latch가 필요 없다. 더 가볍다.
- B는 `vacuum_heap_record` 경로 안에 있어 여전히 현재 레코드의 `prev_version_lsa` 체인 순회 I/O가 발생할 여지가 있었다. A-lite는 체인 순회 자체를 제거했다.

#### Option C 대비

- C는 MVCC 헤더 플래그 비트 추가가 필요했다. `HAS_PREV_OOS`는 UPDATE 체인을 따라 전파되어야 하므로 `heap_update_adjust_recdes_header`, `or_mvcc_get_header` 등 여러 지점 수정이 불가피했다.
- 헤더 포맷 변경은 replication log, CDC, flashback 모두에 파급 효과가 있었다.
- A-lite는 기존 헤더를 그대로 쓰며, 과거 버전의 OOS 여부는 해당 undo 레코드에 이미 존재하는 HAS_OOS 비트를 읽는 것으로 충분하다.

#### Option D 대비

- D는 heap 레코드 포맷에 pending-delete 섹션을 신설하는 대변경이었다. VOT 확장, recovery/replication/serialization 전면 수정, 기존 DB migration이 필요했다.
- 구현 범위가 PR 단위를 초과해 M3/M4로 연기돼야 했다.
- A-lite는 기존 포맷 그대로, `vacuum.c` 범위 내 수정으로 완결된다.

### 3.3 네 옵션 공통점과 A-lite의 차이

네 옵션 모두 L1 누수 해결을 목표했다. 그러나 A/B/C/D는 공통적으로 "백워드 체인 순회를 유지하면서 어떻게 더 싸게 만들거나 어떻게 중간 힌트를 심을 것인가"를 묻는 접근이었다. A-lite는 질문 자체를 바꾼다. "정리 지점을 옮겨 체인 순회를 아예 없앨 수 있는가"에 대한 답이 forward-walk inline 정리다.

---

## 4. A-lite가 추가로 제거하는 부담

L1 해결과 성능 회귀 해소 외에 다음도 동시에 제거된다.

### 4.1 체인 워커 자체의 유지보수 부담

`vacuum_cleanup_prev_version_oos()`는 약 250줄의 복잡한 로직이었다. 버전당 `LOG_CS_ENTER/EXIT`, `logpb_prior_lsa_append_all_list`, `logpb_fetch_page`, `log_get_undo_record` 호출 순서 정합성, `or_mvcc_get_header`로부터 `prev_version_lsa` 재추출, 에러 경로마다 sysop abort 보장 등 유지해야 할 불변식이 많았다. 이 전체가 사라졌다.

### 4.2 Per-record 로그 I/O 제거

과거 설계는 MVCC-updated 레코드당 `logpb_fetch_page`를 N회(체인 길이) 수행했다. A-lite는 forward walk가 이미 `vacuum_fetch_log_page`로 해당 페이지를 한 번 메모리에 올려두므로 중복 fetch가 없다.

### 4.3 `vacuum_cleanup_prev_version_oos`의 lazy VFID lookup 제거

과거에는 체인 워커 내부에서도 OOS VFID를 지연 조회하는 로직이 있었다. A-lite는 블록 진입 시 한 번 초기화되는 stack-local 캐시에서 처리하므로 관련 분기가 단순해졌다. 캐시 미스는 `file_descriptor_get` + `heap_oos_find_vfid`로 수렴하고, 일시 실패 시 캐시에 기록하지 않아 false-negative를 방지한다(`src/query/vacuum.c:3374-3392`).

### 4.4 `need_prev_version_oos_cleanup` 조건식 복잡도 제거

`MVCC_IS_HEADER_PREV_VERSION_VALID` + `record_type IN (REC_HOME, REC_RELOCATION)` + `!VFID_ISNULL(&helper->oos_vfid)`의 3-term 조건식과 그 주석이 모두 제거됐다. 현재 `vacuum_heap_record`의 `has_oos` 계산(`src/query/vacuum.c:2460-2462`)은 현재 레코드에 한정된 단순한 단일 명제다.

---

## 5. 머지 후 후속 검토 항목

| # | 항목 | 비고 |
|---|------|------|
| T0.5 | 포워드 워크 비용 마이크로벤치마크 | MVCC 힙 연산당 undo 디코드 + HAS_OOS 체크의 실제 ns 측정 |
| T3.2 | 긴 UPDATE 체인 통합 테스트 | 10만 rows, 5회 UPDATE → DELETE 후 vacuum 처리 시간 |
| T3.3 | OOS-less OLTP 회귀 통합 테스트 | partition churn 벤치 재실행 |
| D1 | `bridge_vacuum_cleanup_prev_version_oos` 스텁 제거 | Phase 3에서 `DISABLED_` 테스트 재작성과 함께 |
| D2 | VFID 캐시 크기 재검토 | 16 엔트리가 현실 heap 수와 일치하는지 확인 |

---

## 6. 결정 기록 (팀 논의 결과 요지)

- Option B를 M2 내 채택하자는 초기 추천 대신, 체인 워커 제거라는 더 근본적 방향이 리뷰 과정에서 제시되었다.
- A-lite의 공수는 B와 비슷한 수준(2–3인일)이었지만 정리 범위가 더 컸다(기존 코드 삭제 + 새 블록 추가).
- 3-way 리뷰(Architect / Security / Code review)에서 네 개의 수정 요구가 제기되어 반영되었다. 상세는 `PR-6986-response.md` 장 3 참조.

---

## Appendix A — 관련 문서 및 커밋

- **원인 커밋:** `0748432eb` — P1 수정에서 가드 누락
- **임시 수정:** `899d5b633` — 현재 가드 도입 (L1 누수 수용)
- **근본 재설계:** `f912b720c` — 포워드 워크 inline 정리
- **스타일 정합:** `31e6e9dc6` — range-for / joined if 포맷
- 관련 문서
  - `PR-6986-report.md` — 코드 리뷰 보고서 (L1–L4 누수 경로 분석)
  - `PR-6986-perf-regression-report.md` — 성능 회귀 재설계 경과
  - `PR-6986-response.md` — 누적 리뷰 대응 기록
- 관련 JIRA: CBRD-26668 (M2 vacuum 연동), CBRD-26517 (OOS 메인)

---

## Appendix B — 원 옵션별 비교 매트릭스 (2026-04-17 시점 기준 보존)

| 기준 | A. 가드 제거 | B. Page 캐싱 | C. HAS_PREV_OOS 비트 | D. Embed | A-lite (실제) |
|---|---|---|---|---|---|
| L1 누수 해결 | 예 | 예 | 예 | 예 | 예 |
| 성능 회귀 없음 | 아니오 | 예 | 예 | 예 | 예 |
| 포맷 변경 없음 | 예 | 예 | 아니오 | 아니오 | 예 |
| heap 헤더 latch | 불필요 | 필요 | 불필요 | 불필요 | 불필요 |
| 체인 순회 존재 | 예 | 예 | 예 | 아니오 | 아니오 |
| 구현 공수 | 1인일 | 2–3인일 | 5–8인일 | 15–25인일 | 2–3인일 |
| Replication 영향 | 없음 | 없음 | 있음 | 크게 있음 | 없음 |
| 기존 코드 순증 | 0 | +중간 | +중간 | +대 | **순감 (체인 워커 제거 우세)** |
