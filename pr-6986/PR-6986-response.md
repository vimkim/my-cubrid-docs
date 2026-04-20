# PR #6986 리뷰 누적 대응 보고서

**PR:** [CUBRID/cubrid#6986](https://github.com/CUBRID/cubrid/pull/6986)
**제목:** [CBRD-26668] Wire vacuum to clean up OOS records after DELETE/UPDATE
**HEAD commit:** `31e6e9dc6`
**최초 작성:** 2026-04-15
**최신 갱신:** 2026-04-20
**이전 버전과의 관계:** 2026-04-15 초판은 Greptile 리뷰(G-1 ~ R-2) 대응 기록이었다. 본 갱신은 이후 성능 회귀 수정(`899d5b633`)과 포워드 워크 재설계(`f912b720c`, `31e6e9dc6`)까지 누적해 포괄한다.

---

## 0. 누적 이슈 대응 표

| # | 이슈 | 심각도 | 최초 대응 | 최종 상태 |
|---|------|--------|------|------|
| G-1 | OOS 이중 삭제 (eager + vacuum) | P1 | `locator_delete_oos_force()` 제거 | 해결 |
| G-2 | `(void) heap_oos_find_vfid()` → OOS 누수 | P1 | 에러 처리 추가 (assert + return ER_FAILED) | 해결 |
| NEW-6 | WAL 위반 + sysop abort 복합 위험 | P1 | 기존 패턴과 동일 확인 | 해당 없음 |
| G-5 | WAL 로깅 순서 | P2 | NEW-6과 동일 분석 | 해당 없음 |
| NEW-7 | `locator_delete_oos_force` crash-recovery 원자성 | P2 | 함수 자체 제거로 해결 | 해결 |
| R-1 | OOS OID 경계/null 검사 누락 | P2 | 함수 자체 제거로 해결 | 해결 |
| R-2 | `ER_HEAP_UNKNOWN_OBJECT` 오용 + 반환값 불일치 | P2 | 함수 자체 제거로 해결 | 해결 |
| NEW-8 | `attrepr->location` 범위 검증 누락 | P3 | 함수 자체 제거로 해결 | 해결 |
| PERF-1 | OOS-less 테이블에서 per-record 체인 I/O | P1 | `899d5b633` VFID 가드 (임시) → `f912b720c` 체인 워커 제거 (근본) | 해결 |
| LEAK-L1 | UPDATE-drops-all-OOS → DELETE의 구버전 누수 | P1 | 임시 가드 하에서 수용 → forward-walk 재설계로 해소 | 해결 |
| SEC-HIGH | VFID 캐시 일시 실패 시 NULL 캐싱 위험 | P1 | `er_clear()` 후 캐시 미기록, 다음 호출 재시도 | 해결 |
| MEDIUM | undo payload size 상한 검증 부재 | P2 | `2 * IO_MAX_PAGE_SIZE` 상한 가드 추가 | 해결 |
| MAJOR | range-for 및 joined if 스타일 정합 | P3 | `31e6e9dc6`에서 indent 포맷터 기준 맞춤 | 해결 |

---

## 1. 제1기 (2026-04-15) — Greptile 리뷰 대응

### 1.1 대응 요지

Greptile 리뷰에서 제기된 여덟 개 이슈(G-1, G-2, NEW-6, G-5, NEW-7, NEW-8, R-1, R-2) 중 여섯 건을 해결하고 두 건(NEW-6, G-5)은 "기존 vacuum 패턴과 일치하므로 변경 불필요"로 확인했다.

### 1.2 `locator_delete_oos_force()` 완전 제거

- 변경 파일: `src/transaction/locator_sr.c`.
- 전방 선언, 호출부, 함수 본체 약 110줄을 모두 제거.
- 해결 이슈: G-1, NEW-7, R-1, R-2, NEW-8 (5건 일괄).
- 근거: OOS 정리를 vacuum이 전담한다는 CBRD-26668 설계와 부합. MVCC 정합성, 이중 삭제 방지, crash-recovery 원자성 모두 vacuum 경로에서 일관되게 처리됨.

### 1.3 `heap_oos_find_vfid()` 에러 처리 추가

- 변경 파일: `src/query/vacuum.c` (REC_RELOCATION 경로, REC_HOME 경로 2개소).
- `(void)` 캐스트를 제거하고 실패 시 `vacuum_er_log_error` + `assert_release(false)` + `return ER_FAILED`.
- 해결 이슈: G-2.
- 근거: OOS VFID 조회 실패를 조용히 무시하면 `oos_vfid`가 NULL로 남아 OOS 정리가 영구 스킵되어 PR 목적을 무력화한다.

### 1.4 WAL 순서 분석 (NEW-6, G-5)

- REC_RELOCATION의 home page 처리 순서 `spage_vacuum_slot → pgbuf_set_dirty → vacuum_log_redoundo_vacuum_record`는 기존 vacuum 코드에서도 동일하게 사용되며, WAL 규율은 `pgbuf_flush_page()`가 실제 디스크 쓰기 직전에 LSN 경계 검사로 보장한다.
- `pgbuf_set_dirty`는 in-memory 마킹에 불과하므로 로그 append 이전에 호출되어도 문제 없다.
- undo 데이터는 `helper->rec_buf`에 미리 COPY된 것이라 페이지 변경 이후에도 유효하다.
- 결론: 변경 불필요.

### 1.5 TC-12 테스트 수정

- 변경 파일: `unit_tests/oos/sql/test_oos_sql_vacuum.cpp`.
- `TruncateTableCleansOos`에 `run_vacuum()` 호출 추가해 TRUNCATE 후 vacuum을 거쳐 OOS가 정리되도록 시나리오 변경.

---

## 2. 제2기 (2026-04-17) — 성능 회귀 수정 `899d5b633`

### 2.1 증상

CI에서 `sql/_01_object/_09_partition/_001_create/cases/1189.sql` 외 partition 테스트가 타임아웃. 컨테이너 0 지연이 뚜렷.

### 2.2 원인

커밋 `0748432eb`의 P1 수정이 REMOVE 경로에 `vacuum_cleanup_prev_version_oos()` 호출을 추가하면서, INSID 경로에 이미 있던 `!VFID_ISNULL(&helper->oos_vfid)` 가드를 빠뜨렸다. 결과적으로 OOS 파일이 없는 일반 테이블의 모든 MVCC UPDATE 레코드에 대해 체인 순회 I/O(`LOG_CS` + `logpb_fetch_page`)가 발생.

### 2.3 수정

`need_prev_version_oos_cleanup` 조건식에 `!VFID_ISNULL(&helper->oos_vfid)`를 추가해 현재 레코드에 OOS 플래그가 있을 때만 체인 순회하도록 변경.

### 2.4 수용된 한계 (LEAK-L1)

현재 레코드에 OOS 플래그가 없으면서 과거 버전에는 OOS가 있는 "UPDATE drops all OOS → DELETE" 시나리오에서 구버전 OOS가 영구 고아로 남는다. 코드 주석과 PR 설명에 "Known limitation"으로 명기. 당시 팀 논의에서 제2기 머지는 CI unblock을 위한 임시 조치로 합의되었고 L1은 후속 티켓에서 다루기로 했다.

---

## 3. 제3기 (2026-04-20) — Forward-walk 재설계 `f912b720c` + 스타일 `31e6e9dc6`

### 3.1 재설계 개요

제2기의 VFID 가드는 L1이라는 정확성 결함을 남겼다. 이를 해소하면서 동시에 성능 회귀 위험을 더 근본적으로 없애기 위해 다음이 수행됐다.

1. `vacuum_cleanup_prev_version_oos()` 함수 본체 제거 (약 250줄).
2. `vacuum_heap_record` REMOVE 경로의 `need_prev_version_oos_cleanup` 계산 + 트리거 블록 + 호출부 제거.
3. 포워드 선언 제거.
4. `vacuum_process_log_block`의 MVCC 로그 순회(`src/query/vacuum.c:3621-3725`) 내부에 inline OOS 정리 블록 추가. MVCC 힙 로그 레코드(`RVHF_UPDATE_NOTIFY_VACUUM`, `RVHF_MVCC_DELETE_MODIFY_HOME`)의 undo payload를 디코드 → `heap_recdes_contains_oos` 검사 → HAS_OOS가 참이면 `oos_delete` 호출.
5. 블록당 16-엔트리 stack-local VFID 캐시(`src/query/vacuum.c:714-719`, `3336-3410`).
6. `bridge_vacuum_cleanup_prev_version_oos` 스텁만 `src/query/vacuum.c:8315-8334`에 남아있고 본체는 `assert_release(false)` — 관련 `DISABLED_` 테스트 링크 호환용.

### 3.2 왜 신규 WAL 레코드 타입을 도입하지 않았나

재설계 초안에는 `RVVAC_OOS_DELETE`라는 신규 WAL 타입을 두어 redo 핸들러에서 prev-version OOS 삭제를 재생하는 방안이 있었다. 이는 redo 핸들러 내부에서 `log_append`를 재귀 호출해야 했고, CUBRID의 log append 규율상 redo 핸들러 컨텍스트에서 새 로그 레코드를 append하는 것은 허용되지 않으므로 double-replay hazard가 있었다. 기각.

채택된 방식은 `oos_delete_chain`이 이미 per-chunk `RVOOS_DELETE` undoredo를 기록한다는 기존 사실을 활용한다. forward-walk 내부에서 `log_sysop_start → vacuum_forward_walk_delete_oos → log_sysop_commit|abort`로 감싸기만 하면 기존 복구 경로가 그대로 동작한다(`src/query/vacuum.c:3697-3714`).

### 3.3 안전성 근거

#### MVCC 임계값

`threshold_mvccid = log_Gl.mvcc_table.get_global_oldest_visible()` (`src/query/vacuum.c:3477`)이 forward walk 전체에서 유지된다. `src/query/vacuum.c:3611-3618`의 debug assert가 순회 중 만나는 모든 MVCC 힙 로그 레코드의 MVCCID가 임계값 미만임을 보증한다. 즉 처리되는 undo payload는 모두 "더 이상 어떤 가시적 스냅샷도 참조하지 않는 구버전"이다.

#### OID 분리성

`heap_attrinfo_insert_to_oos`가 항상 fresh OID를 할당하므로, pre-image의 OOS OID 집합과 post-image의 OOS OID 집합은 상호 disjoint하다. forward walk가 undo payload에서 추출하는 OOS OID는 pre-image의 것이며, 현재 heap 슬롯(있다면)이 가리키는 post-image OOS OID와 충돌하지 않는다.

#### Sysop 원자성

여러 chunk로 분할 저장된 OOS 레코드의 `oos_delete` 호출이 중간에 실패해도, 감싸고 있는 sysop이 `log_sysop_abort`로 되돌리면 이미 성공한 chunk의 `RVOOS_DELETE`가 전부 undo되어 `oos_rv_redo_insert`로 재삽입된다. 상세는 `sysop-explained.md` 참조.

### 3.4 3-way 리뷰 반영 사항

Architect / Security / Code review 3개 레인에서 다음 4개 수정 요구가 제기되어 전부 반영됐다.

- **Security HIGH**: `vacuum_oos_vfid_cache_lookup`에서 `file_descriptor_get` 또는 `heap_oos_find_vfid`가 일시적으로 실패(예: 파일 트래커 페이지 버퍼 경합)했을 때 VFID_NULL을 캐시에 기록하면 해당 블록 나머지에서 false-negative로 이어져 OOS 누수. 대응: `er_clear()` 후 캐시에 기록하지 않고 반환. 다음 호출에서 재시도. 구현 위치 `src/query/vacuum.c:3374-3392`.
- **Code-review MEDIUM**: undo payload size가 의도치 않게 크면 스택 버퍼 OOB 또는 잘못된 heap alloc 크기로 이어질 위험. 대응: `undo_data_size > 2 * IO_MAX_PAGE_SIZE` 상한 가드 추가. 초과 시 `assert_release(false)` + 해당 레코드만 cleanup 스킵(블록은 계속 진행). 구현 위치 `src/query/vacuum.c:3661-3665`.
- **Code-review MAJOR**: range-for와 joined if 줄이 indent 포맷터 출력과 어긋남. 대응: `31e6e9dc6`이 `src/query/vacuum.c:2430-2439`와 `3436-3443`의 range-for, 그리고 관련 joined if의 스타일을 `indent -l120 -lc120` 출력에 맞춤.
- **Architect**: 방어적 undo 복사. undo payload는 공유 로그 페이지 버퍼를 가리킬 수 있고, `oos_delete` 내부의 `log_append`가 페이지 롤오버를 유발하면 해당 포인터가 무효화된다. 대응: `log_sysop_start` 이전에 `undo_copy_stack` (IO_MAX_PAGE_SIZE 스택 버퍼) 또는 `db_private_alloc` 기반 heap 복사로 defensive copy. 구현 위치 `src/query/vacuum.c:3672-3690`.

### 3.5 VFID 가드 제거와 성능 회귀 재발 방지

제2기의 `!VFID_ISNULL(&helper->oos_vfid)` 가드는 보호할 경로 자체가 사라졌으므로 이번에 명시적으로 제거됐다. 그 가드가 회피하려던 성능 문제(OOS-less 테이블의 per-record `LOG_CS + logpb_fetch_page`)는 forward-walk가 모든 MVCC 힙 연산에 대해 HAS_OOS 비트 체크만 수행(이미 로드된 undo 바이트에서 읽기) → HAS_OOS가 false면 즉시 종료하는 구조로 전환되어 원천적으로 해결됐다. 상세는 `PR-6986-perf-regression-report.md` 참조.

---

## 4. 현재 미해결 리뷰 이슈

**없음.** CI는 재설계 머지 이후 재실행 대기 중이며, 로컬 수준에서는 빌드와 OOS 관련 유닛 테스트가 기존 기준으로 통과한다. partition 테스트 세트 통과 확인이 최종 머지 조건이다.

---

## 5. 변경 파일 요약 (누적)

| 파일 | 변경 유형 | 제1기 | 제2기 | 제3기 |
|------|-----------|-------|-------|-------|
| `src/transaction/locator_sr.c` | 함수/호출부/선언 제거 | −120줄 | — | — |
| `src/query/vacuum.c` | 에러 처리 추가 | +12줄 | +1줄 (가드) | −250줄(워커) / +약 200줄(forward-walk + 캐시) |
| `unit_tests/oos/sql/test_oos_sql_vacuum.cpp` | TC-12 수정 | +5/−3줄 | — | — |

제3기는 net으로는 코드량이 감소한다(워커 본체 250줄 제거 대비 새 블록 200줄).

---

## 6. 후속 JIRA 목록

| # | 항목 | 비고 |
|---|------|------|
| F-1 | `bridge_vacuum_cleanup_prev_version_oos` 스텁 제거 | Phase 3에서 `DISABLED_` 테스트 전면 재작성과 함께 |
| F-2 | T0.5 마이크로벤치마크 | forward-walk 비용 실측 |
| F-3 | T3.2 긴 UPDATE 체인 통합 테스트 | 회귀 방지 자동화 |
| F-4 | T3.3 OOS-less OLTP 회귀 테스트 | partition churn 벤치 |

---

## 7. 커밋 참조

- `0748432eb` — P1 수정 (성능 회귀 유발).
- `899d5b633` — 임시 VFID 가드 (L1 누수 수용).
- `f912b720c` — 백워드 체인 워커 제거, forward-walk inline 정리, L1 해소, 3-way 리뷰 4개 수정 반영.
- `31e6e9dc6` — range-for / joined if 스타일 정합.
