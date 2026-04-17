# PR #6986 리뷰 대응 보고서

**PR:** [CUBRID/cubrid#6986](https://github.com/CUBRID/cubrid/pull/6986)
**제목:** [CBRD-26668] Wire vacuum to clean up OOS records after DELETE/UPDATE
**대응 일시:** 2026-04-15
**리뷰 보고서:** PR-6986-report.md (2026-04-15)

---

## 1. 대응 요약

| # | 이슈 | 심각도 | 대응 | 상태 |
|---|------|--------|------|------|
| G-1 | OOS 이중 삭제 (eager + vacuum) | **P1** | `locator_delete_oos_force()` 완전 제거 | **해결** |
| G-2 | `(void) heap_oos_find_vfid()` → OOS 누수 | **P1** | 에러 처리 추가 (assert + return ER_FAILED) | **해결** |
| NEW-6 | WAL 위반 + sysop abort 복합 위험 | P1 | 기존 패턴과 동일 확인 → 변경 불필요 | **해당 없음** |
| G-5 | WAL 로깅 순서 | P2 | NEW-6과 동일 분석 → 변경 불필요 | **해당 없음** |
| NEW-7 | `locator_delete_oos_force` crash-recovery 원자성 | P2 | 함수 자체 제거로 해결 | **해결** |
| R-1 | OOS OID 경계/null 검사 누락 | P2 | 함수 자체 제거로 해결 | **해결** |
| R-2 | `ER_HEAP_UNKNOWN_OBJECT` 오용 + 반환값 불일치 | P2 | 함수 자체 제거로 해결 | **해결** |
| NEW-8 | `attrepr->location` 범위 검증 누락 | P3 | 함수 자체 제거로 해결 | **해결** |

**해결: 6건 / 해당 없음(분석 완료): 2건 / 미해결: 0건**

---

## 2. 변경 사항 상세

### 2.1 `locator_delete_oos_force()` 완전 제거

**해결 이슈:** G-1, NEW-7, R-1, R-2, NEW-8 (5건 일괄 해결)

**변경 파일:** `src/transaction/locator_sr.c`

**변경 내용:**
1. `locator_delete_oos_force()` 전방 선언 제거
2. `locator_delete_force_internal()` 내 호출부 제거 (lines 6374-6382)
3. `locator_delete_oos_force()` 함수 정의 제거 (~110줄)

**근거:**

JIRA CBRD-26668 설계에 명시된 대로, OOS 레코드의 정리는 **vacuum이 전담**해야 한다:

- **MVCC 정합성:** `locator_delete_oos_force()`는 heap 레코드의 MVCC delete 이전에 OOS 데이터를 삭제하므로, 동시 읽기 트랜잭션이 heap 레코드를 통해 이미 삭제된 OOS OID에 접근할 수 있다.
- **이중 삭제 방지:** eager 삭제 후 vacuum이 동일 OOS 레코드를 재삭제하면 `spage_get_record()`에서 `S_DOESNT_EXIST` 반환 → assert 실패.
- **crash-recovery 원자성:** OOS 삭제와 heap 레코드 삭제가 sysop으로 감싸져 있지 않아, crash 시 dangling OOS reference 생성 가능.

함수를 제거하면 이 함수 내부에 존재했던 R-1 (경계 검사 누락), R-2 (에러 코드 오용), NEW-8 (location 검증 누락) 이슈도 함께 해소된다.

---

### 2.2 `heap_oos_find_vfid()` 에러 처리 추가

**해결 이슈:** G-2

**변경 파일:** `src/query/vacuum.c`

**변경 위치:** `vacuum_heap_prepare_record()` 내 2개소
- REC_RELOCATION 경로 (line ~2051)
- REC_HOME 경로 (line ~2166)

**Before:**
```c
if (heap_recdes_contains_oos (&helper->record) && VFID_ISNULL (&helper->oos_vfid))
  {
    (void) heap_oos_find_vfid (thread_p, &helper->hfid, &helper->oos_vfid, false);
  }
```

**After:**
```c
if (heap_recdes_contains_oos (&helper->record) && VFID_ISNULL (&helper->oos_vfid))
  {
    if (!heap_oos_find_vfid (thread_p, &helper->hfid, &helper->oos_vfid, false))
      {
        vacuum_er_log_error (VACUUM_ER_LOG_HEAP,
                             "Failed to find OOS VFID for hfid %d|%d.",
                             VFID_AS_ARGS (&helper->hfid.vfid));
        assert_release (false);
        return ER_FAILED;
      }
  }
```

**근거:**

기존 `(void)` 캐스트는 VFID 조회 실패를 무시하여 `oos_vfid`가 NULL로 남고, 이후 `has_oos`가 false로 평가되어 OOS 레코드 정리가 영구적으로 건너뛰어졌다. 이는 이 PR의 핵심 목적(vacuum에서 OOS 정리)을 무력화한다.

수정 패턴은 동일 함수 내 `overflow_vfid` 조회 실패 처리(line 2082-2083: `assert_release(false); return ER_FAILED;`)와 일치한다.

---

### 2.3 TC-12 테스트 수정

**변경 파일:** `unit_tests/oos/sql/test_oos_sql_vacuum.cpp`

**변경 내용:** `TruncateTableCleansOos` 테스트에 `run_vacuum()` 호출 추가. TRUNCATE 후 OOS 정리가 vacuum을 통해 이루어지도록 테스트 시나리오 변경.

**Before:** TRUNCATE → 즉시 검증 (eager 삭제에 의존)
**After:** TRUNCATE → `run_vacuum()` → 검증 (vacuum 경로에 의존)

---

## 3. WAL 순서 분석 (NEW-6, G-5 — 변경 불필요)

리뷰에서 지적된 `spage_vacuum_slot → pgbuf_set_dirty → vacuum_log_redoundo_vacuum_record` 순서가 WAL 위반이라는 우려에 대해 심층 분석을 수행했다.

### 분석 결과: 기존 vacuum 패턴과 동일하며, 안전하다.

**REC_RELOCATION의 home page도 동일한 순서를 사용한다:**

```
Line 2443: spage_vacuum_slot(home_page)       // 물리적 변경
Line 2454: pgbuf_set_dirty(home_page)          // dirty 마킹
Line 2468: vacuum_log_redoundo_vacuum_record() // 로그 기록
```

**REC_HOME+OOS (이 PR에서 추가):**

```
Line 2443: spage_vacuum_slot(home_page)        // 물리적 변경
Line 2555: pgbuf_set_dirty(home_page)           // dirty 마킹
Line 2556: vacuum_log_redoundo_vacuum_record()  // 로그 기록
```

**안전한 이유:**

1. **Undo 데이터의 독립성:** `vacuum_log_redoundo_vacuum_record()`의 undo 데이터(`helper->record`)는 `helper->rec_buf`에 COPY된 데이터로, 페이지 변경 이후에도 유효하다.
2. **Buffer pool의 WAL 강제:** CUBRID의 `pgbuf_flush_page()`는 페이지를 디스크에 쓰기 전 해당 페이지의 LSN까지 로그가 flush되었는지 확인한다. `pgbuf_set_dirty()`는 in-memory 마킹일 뿐, 실제 디스크 쓰기 시점에 WAL이 보장된다.
3. **Sysop abort의 정확성:** Sysop 내 로그 레코드가 기록된 후 abort가 호출되므로, undo 작업이 정상 수행된다. 이는 REC_BIGONE의 abort 패턴(line 2525)과 동일하다.

**결론:** REC_HOME+OOS 경로의 순서 변경은 기존 vacuum 코드와의 일관성을 깨뜨리므로 수행하지 않는다. 이 패턴은 vacuum의 의도적 설계이다.

---

## 4. 변경 파일 요약

| 파일 | 변경 유형 | 변경량 |
|------|-----------|--------|
| `src/transaction/locator_sr.c` | 함수/호출부/선언 제거 | -120줄 |
| `src/query/vacuum.c` | 에러 처리 추가 | +12줄 |
| `unit_tests/oos/sql/test_oos_sql_vacuum.cpp` | TC-12 수정 | +5줄, -3줄 |
