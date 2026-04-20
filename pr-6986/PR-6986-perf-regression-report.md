# PR #6986 — Vacuum Prev-Version 체인 순회 성능 회귀 분석 및 해소 경과

**PR:** [CUBRID/cubrid#6986](https://github.com/CUBRID/cubrid/pull/6986)
**HEAD commit:** `31e6e9dc6` — style(vacuum): match indent formatter on range-for and joined if
**원인 커밋:** `0748432eb` — fix(oos): prevent dangling OOS on UPDATE→DELETE and chain-walk livelock
**임시 수정 커밋:** `899d5b633` — fix(oos): guard REMOVE-path prev_version chain walk on oos_vfid being set
**근본 재설계 커밋:** `f912b720c` — refactor(oos): replace prev_version chain walker with forward-walk OOS cleanup
**리포트 작성일:** 2026-04-20 (재작성)
**기존 버전과의 관계:** 본 문서는 2026-04-17자 동일 제목 보고서의 후속이며, 당시 핵심 처방이었던 `!VFID_ISNULL(&helper->oos_vfid)` 가드가 `f912b720c`에서 전체 아키텍처 재설계로 제거되었음을 반영해 내용을 전면 갱신했다.

---

## 0. 개요

본 문서는 현재 PR 상태 기준으로는 **역사적 기록물**이다. 2026-04-17 시점의 "가드 한 줄 추가" 방식 회귀 수정과, 그 수정이 엣지 케이스 누수(이하 L1)를 남긴 채 채택되었던 맥락을 남긴다. 그 후 2026-04-20에 `vacuum_cleanup_prev_version_oos` 함수 자체를 제거하고 포워드 로그 워크 내 inline 정리로 전환하면서, 본 보고서의 원 처방은 물리적으로 의미가 없어졌다. 현재 진실은 `src/query/vacuum.c:3642-3724`의 forward-walk OOS 정리 블록과 `src/query/vacuum.c:3336-3410`의 per-block VFID 캐시다.

---

## 1. 역사적 요약 — 회귀가 어떻게 발생했고 어떻게 임시 수습했나

### 1.1 P1 버그 (dangling OOS on UPDATE→DELETE)

MVCC 환경에서 `INSERT(OOS_A) → UPDATE(OOS_B) → DELETE → vacuum REMOVE` 시퀀스가 발생하면, `vacuum_heap_record()`가 현재 레코드(OOS_B)만 정리하고 `prev_version_lsa` 체인을 따라 OOS_A를 회수하지 않아 구버전 OOS가 영구 고아로 남는 버그가 보고되었다. `vacuum_heap_record_insid_and_prev_version()`만 체인 순회를 수행했고 `VACUUM_RECORD_DELETE_INSID_PREV_VER` 경로에서만 발동했다.

### 1.2 원인 커밋 `0748432eb`의 수정과 가드 누락

REMOVE 경로에도 체인 순회를 추가하면서 `vacuum_cleanup_prev_version_oos()`를 호출하도록 했지만, 이때 INSID 경로 쪽에 이미 존재하던 `!VFID_ISNULL(&helper->oos_vfid)` 가드를 빠뜨렸다. 결과적으로 OOS 파일이 없는 일반 heap의 모든 MVCC-updated 레코드가 체인 순회 I/O를 지불하게 되었다.

### 1.3 임시 수정 커밋 `899d5b633`

`need_prev_version_oos_cleanup` 계산식에 `!VFID_ISNULL(&helper->oos_vfid)` 조건을 한 줄 추가하여 OOS 파일이 없는 heap은 체인 순회 자체를 건너뛰도록 했다. CI에서 partition 테스트 timeout이 즉시 해소되었지만, 현재 레코드에 OOS 플래그가 없으면서 과거 버전에는 OOS가 있는 "UPDATE drops all OOS → DELETE" 패턴에서 구버전 OOS가 누수되는 엣지 케이스를 의식적으로 수용했다.

### 1.4 임시 수정의 비용 모델 (재검토)

임시 수정은 `vacuum_cleanup_prev_version_oos()` 내부 루프의 버전당 비용을 회피하는 데 초점이 있었다. 그 비용은 다음과 같았다.

- `LOG_CS_ENTER/EXIT` — 전역 critical section, 버전당 1회.
- `logpb_prior_lsa_append_all_list` — prior list flush.
- `logpb_fetch_page` — 로그 페이지 I/O (버퍼 miss 시 디스크 읽기).
- `log_get_undo_record` — undo 레코드 파싱.
- `or_mvcc_get_header` — MVCC 헤더 재파싱 후 `prev_version_lsa` 추출.

즉 체인 길이 N이면 N회의 실제 로그 I/O + 전역 락 경합이 발생했다. 카탈로그 churn이 많은 파티션 테스트가 CI에서 timeout된 직접 원인이다.

---

## 2. Forward-walk 재설계에 의한 가드 소멸

### 2.1 함수 자체가 사라졌다

`f912b720c`는 다음을 한 번에 제거했다.

- 함수 본체: `vacuum_cleanup_prev_version_oos()` (약 250줄).
- 호출부: `vacuum_heap_record` REMOVE 경로의 트리거 블록(`need_prev_version_oos_cleanup` 계산 + sysop 진입 + 본문 호출).
- 포워드 선언: `src/query/vacuum.c` 상단의 `static` 프로토타입.

결과적으로 `!VFID_ISNULL(&helper->oos_vfid)` 가드 역시 `need_prev_version_oos_cleanup`과 함께 사라졌다. 그 가드가 보호하던 코드 경로가 물리적으로 존재하지 않는다.

참고로 현재도 `vacuum_heap_record`는 **현재 레코드**(REC_HOME/REC_RELOCATION)의 OOS 정리를 수행한다(`src/query/vacuum.c:2460-2462`의 `has_oos` 계산, `src/query/vacuum.c:2540-2548`와 `src/query/vacuum.c:2602-2610`의 `vacuum_heap_oos_delete` 호출). 가드 없이도 이 경로는 현재 레코드가 실제로 OOS 플래그를 가진 경우에만 발동하므로, non-OOS 테이블에서는 원래부터 무관하다.

### 2.2 새 설계가 추가하는 비용

포워드 워크의 정리 코드는 `vacuum_process_log_block`의 기존 MVCC 로그 순회 루프 내부(`src/query/vacuum.c:3621-3725`)에 inline으로 들어간다. 비용 구조는 다음과 같다.

1. **Per-log-record 단계**: `LOG_IS_MVCC_HEAP_OPERATION`이 참인 레코드마다:
   - `undo_data != NULL && undo_data_size > 0` 분기(`src/query/vacuum.c:3648`): 이미 `vacuum_process_log_record`가 디코드해 메모리에 올려둔 바이트에 대한 포인터 비교 + 크기 비교.
   - `heap_recdes_contains_oos(&undo_recdes)` 호출(`src/query/vacuum.c:3656`): VOT 스캔이지만 재귀적 로그 I/O 없음.
   - HAS_OOS가 false면 즉시 종료. 이 경로가 OOS-less 테이블의 기본 비용이며, `logpb_fetch_page`/`LOG_CS` 없음.

2. **HAS_OOS가 true일 때의 비용**:
   - `undo_data_size > 2 * IO_MAX_PAGE_SIZE` 상한 가드.
   - 스택 버퍼(`IO_MAX_PAGE_SIZE`) 또는 `db_private_alloc`을 통한 undo payload 방어적 복사(`src/query/vacuum.c:3672-3690`).
   - `vacuum_oos_vfid_cache_lookup` 호출 — 캐시 히트 시 O(cache_size=16) 선형 탐색만으로 완료.
   - `log_sysop_start` → `vacuum_forward_walk_delete_oos` → `log_sysop_commit|abort`.

3. **VFID 캐시 미스 비용**: `file_descriptor_get` + `heap_oos_find_vfid`. 실패 시 캐시에 기록하지 않아 재시도 가능(`src/query/vacuum.c:3374-3392`).

### 2.3 파티션 워크로드에 대한 순 효과

카탈로그 테이블은 OOS 파일이 없으므로 `heap_recdes_contains_oos`가 false를 반환하여 모든 비용 분기가 즉시 종료된다. 이전 설계에서 버전당 지불하던 `LOG_CS + logpb_fetch_page`가 0이 되고, 대신 MVCC 힙 연산당 HAS_OOS 비트 체크 한 번만 추가된다. 이는 이미 버퍼에 있는 undo 바이트를 읽는 연산이므로 상대적 비용은 무시 가능 수준이다.

OOS 파일이 있는 테이블의 경우 과거 설계와 새 설계 모두 per-record 로그 I/O가 발생하지만, 새 설계는 포워드 워크 내에서 이미 로드된 로그 페이지를 재사용하므로 중복 fetch 비용이 감소한다.

---

## 3. 새 설계의 성능 특성 상세

### 3.1 제거된 비용

| 경로 | 과거 비용 | 현재 비용 |
|------|-----------|-----------|
| Non-OOS 테이블의 MVCC UPDATE 레코드 | 버전당 `LOG_CS` + `logpb_fetch_page` | HAS_OOS 비트 체크 1회 (이미 로드된 바이트) |
| OOS 테이블의 현재 레코드 정리 | 동일 (유지) | 동일 (유지) |
| OOS 테이블의 체인 순회 | 버전당 `logpb_fetch_page` | 포워드 워크 내 재사용 페이지에서 처리 |

### 3.2 추가된 비용

- MVCC 힙 연산 로그 레코드당 `heap_recdes_contains_oos` 호출. 이 함수는 repid/flag 비트 검사와 OOS 컬럼 존재 여부 판정이며 상수 시간.
- `vacuum_oos_vfid_cache_lookup` 호출. 캐시 히트일 때 O(16) 선형 탐색(실전상 몇 개 엔트리). 미스 시 `file_descriptor_get` 1회 + `heap_oos_find_vfid` 1회.
- HAS_OOS가 참인 경우에 한해 방어적 undo 복사. 대부분 스택 버퍼(`IO_MAX_PAGE_SIZE`) 내에 수용되므로 heap alloc 없음.

### 3.3 정량 측정 계획 (후속)

현재 문서 작성 시점에 새 설계에 대한 재현 가능한 측정치는 없다. 후속 작업으로 다음을 제안한다.

| 시나리오 | 측정 지표 | 우선순위 |
|---|---|---|
| partition 테스트 세트 재실행 | CI 벽시계 시간 | 높음 (머지 조건) |
| 대용량 OOS UPDATE 체인 (10만 rows, 5회 UPDATE) | vacuum 블록당 평균 처리 시간 | 중간 |
| OOS-less OLTP 워크로드 | vacuum 처리 중 CPU 프로파일 | 중간 |
| `PR-6986-T0.5` 마이크로벤치마크 | 체인 길이별 ns/record | 낮음 (세밀 분석용) |

---

## 4. 과거 옵션 A/B/C 재평가

2026-04-17 시점 제안서(`PR-6986-proposal.md`)에서 검토된 옵션을 현재 구현과 대조한다.

| 옵션 | 설명 | 현재 평가 |
|---|---|---|
| A | 가드 없이 체인 순회 유지 | 거부됨. 운영 워크로드 수용 불가. |
| B | 페이지 단위 `has_oos_file` 캐싱 + heap 헤더 latch | 실제 채택되지 않음. 유사한 목적을 **블록 단위 VFID 캐시**(Option A-lite)로 달성. heap 헤더 read latch조차 불필요. |
| C | MVCC 헤더에 `HAS_PREV_OOS` 플래그 추가 | 미채택. 포맷 변경 회피. |
| D | 구버전 OOS OID를 현재 레코드에 embed | 미채택. 힙 레코드 포맷 대변경 회피. |

실제 채택된 것은 네 옵션 어디에도 없던 **Option A-lite** — 백워드 체인 순회를 제거하고, 정리 책임을 forward log walk로 옮기는 근본 재설계다. 이는 B가 목표했던 "OOS-less 테이블 제로 비용"을 달성하면서 heap 헤더 접근조차 없앴다.

---

## 5. 교훈

### 5.1 단일 가드 vs. 재설계

2026-04-17 시점에는 CI unblock이 시급해 "한 줄 가드"로 회귀를 차단했다. 이 수정은 성능 문제는 해결했으나 L1 누수라는 정확성 결함을 남겼다. 이후 3일 만에 forward-walk 재설계로 두 문제(성능 + L1)를 동시에 해소했다. 즉 "회귀를 막기 위한 가드"와 "정확성을 복원하는 아키텍처"는 별개이며, 둘 다 필요했다.

### 5.2 PR 리뷰에서의 상위 수준 대안 조기 탐색

최초 설계는 "INSID 경로의 체인 워커를 REMOVE 경로로 복붙"이라는 **지역적 확장**이었다. 포워드 워크 내 inline 정리라는 **전역 재배치** 대안은 초기 리뷰에서 언급되지 않았다. 성능 회귀가 터지고 나서야 아키텍처 전환이 논의됐다. 향후 유사한 per-record 로그 I/O 추가 제안이 있을 때는 이 사례를 참조해 "MVCC 힙 연산을 이미 순회 중인 상위 루프가 없는가"를 리뷰 단계에서 먼저 질문해야 한다.

### 5.3 WAL 레코드 신설 유혹의 회피

재설계 초안에는 `RVVAC_OOS_DELETE`라는 새 WAL 레코드 타입 도입 안이 있었다. 구체적으로 "REMOVE 타이밍에 prev-version OOS 삭제를 기록하고 redo 핸들러에서 재생"하는 패턴이었다. 이 안은 redo 핸들러에서 `log_append`를 재귀 호출해야 했으므로 double-replay hazard가 있어 거부됐다. 대신 `oos_delete_chain` 자체가 이미 per-chunk `RVOOS_DELETE` undoredo를 기록하므로, forward-walk 내 sysop으로 묶기만 하면 기존 복구 경로가 그대로 동작한다. 신규 WAL 타입을 추가하지 않은 것이 재설계의 안전성 담보 핵심이다.

---

## 6. 현 상태 요약

- `!VFID_ISNULL(&helper->oos_vfid)` 가드는 이제 코드에 존재하지 않는다.
- `vacuum_cleanup_prev_version_oos` 함수도 존재하지 않는다 (관련 테스트 링크 호환을 위한 `bridge_vacuum_cleanup_prev_version_oos` 스텁만 `src/query/vacuum.c:8325-8334`에 남아있고, 본체는 `assert_release(false)`).
- OOS 정리는 두 곳에서 일어난다.
  - 현재 레코드: `vacuum_heap_record` (REC_HOME + 현재 OOS, REC_RELOCATION + OOS 경로).
  - 과거 버전: `vacuum_process_log_block`의 MVCC 힙 연산 loop 내 forward-walk inline 블록.
- 블록당 stack-local VFID 캐시(16 엔트리)가 `file_descriptor_get` + `heap_oos_find_vfid` 중복 호출을 차단한다.

---

## 7. Follow-up

| # | 항목 | 우선순위 | 설명 |
|---|------|----------|------|
| 1 | partition 테스트 CI 재검증 | 높음 | forward-walk 전환 후 `sql/_01_object/_09_partition` 통과 확인 |
| 2 | OOS-heavy 워크로드 실측 | 중간 | 긴 UPDATE 체인에 대한 vacuum 처리 시간 벤치마크 |
| 3 | `bridge_vacuum_cleanup_prev_version_oos` 스텁 제거 | 낮음 | 관련 `DISABLED_` 유닛 테스트 전면 재작성 후 |
| 4 | 블록 VFID 캐시 크기 튜닝 | 낮음 | 실 측정 기반. 현재 16 엔트리가 heap 당 여러 개 공존하는 시나리오 커버 |

---

## 8. 커밋 참조

- `0748432eb` — P1 수정 (성능 회귀 유발).
- `899d5b633` — 임시 VFID 가드 (L1 누수 수용).
- `f912b720c` — 백워드 체인 워커 제거, forward-walk inline 정리로 전환, L1 해소.
- `31e6e9dc6` — 포맷터 정합 (range-for, joined if).
