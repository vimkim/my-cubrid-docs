# PR #6986 코드 리뷰 보고서 — "Does this clean up all unreachable OOS values?"

**PR:** [CUBRID/cubrid#6986](https://github.com/CUBRID/cubrid/pull/6986)
**제목:** [CBRD-26668] Wire vacuum to clean up OOS records after DELETE/UPDATE
**작성자:** vimkim
**베이스 브랜치:** `feat/oos`
**HEAD SHA:** `6d41132a76a1e654f2dbc6e9658a177a4657de00`
**리뷰 일시:** 2026-04-17
**리뷰 초점:** 사용자 질문 — "이 PR이 모든 도달 불가능한(unreachable) OOS 값을 정리하는가?"

> 본 보고서는 이전 리뷰(2026-04-15, 2026-04-13) 이후 HEAD 기준으로 **사용자 질문에 집중하여 재분석**한 결과다. 이전 리뷰들과 중복되는 일반 스타일/안전성 지적은 생략하고, "unreachable OOS 정리 완전성" 관점에서 누수 경로를 추적한다.

---

## 1. 결론 요약 (TL;DR)

**아니오 — 완전하지 않다.** 이 PR은 가장 흔한 vacuum 경로(MVCC DELETE/UPDATE → `vacuum_heap_record`)를 커버하지만, OOS 레코드가 영구적으로 누수되는 **경로가 최소 4개** 남아 있다. 그중 하나는 코드 주석이 스스로 인정하는 한계이고, 하나는 (의도된) SA_MODE DELETE 공백이며, **가장 중요한 하나는 설계 의도와 실제 가드의 불일치로 인한 사각지대** — `vacuum_cleanup_prev_version_oos`의 내부 lazy VFID lookup 로직이 **두 호출자 모두에서 gate-out되어 dead code가 되어 있다.**

---

## 2. PR이 커버하는 정리 경로 (What IS covered)

| 시나리오 | 정리 함수 | 판정 |
|---|---|---|
| MVCC DELETE + REC_HOME + OOS → vacuum | `vacuum_heap_oos_delete` | ✅ sysop 내부에서 수행 |
| MVCC DELETE + REC_RELOCATION + OOS → vacuum | `vacuum_heap_oos_delete` | ✅ sysop 내부에서 수행 |
| MVCC UPDATE 체인 (OOS 컬럼 유지) → vacuum prev-version | `vacuum_cleanup_prev_version_oos` | ✅ 단, `oos_vfid`가 current record에서 설정될 때만 |
| SA_MODE UPDATE (OOS 컬럼 교체) | `heap_update_home_delete_replaced_oos` | ✅ heap_update_home 내 eager delete |
| INSERT abort/rollback | `RVOOS_INSERT`의 undo 핸들러 = `oos_rv_redo_delete` | ✅ 기존 WAL 메커니즘 (이 PR 변경 아님) |

전역 grep 결과 `oos_delete`는 위 3개 호출 지점 외에서는 호출되지 않는다. 즉 이 목록에 없는 경로는 **영구 누수**다.

---

## 3. 남아 있는 누수 경로 (Leak Paths)

### 3.1 [L1] prev-version 체인 가드의 dead-code 함정 — **실질적 correctness 버그**

**증거 1 — 호출자 측 가드 (두 곳 모두 `oos_vfid` NULL일 때 호출 자체를 차단):**

`vacuum_heap_record` (`src/query/vacuum.c`, diff 라인 1055-1057):
```c
bool need_prev_version_oos_cleanup = (MVCC_IS_HEADER_PREV_VERSION_VALID (&helper->mvcc_header)
                                      && !VFID_ISNULL (&helper->oos_vfid)     // ← 가드
                                      && (helper->record_type == REC_HOME || helper->record_type == REC_RELOCATION));
```

`vacuum_heap_record_insid_and_prev_version` (diff 라인 742):
```c
if (MVCC_IS_HEADER_PREV_VERSION_VALID (&helper->mvcc_header) && !VFID_ISNULL (&helper->oos_vfid))
  {
    log_sysop_start (thread_p);
    error_code = vacuum_cleanup_prev_version_oos (thread_p, helper);
```

**증거 2 — `oos_vfid`는 current record가 OOS 플래그를 가질 때만 설정됨:**

`vacuum_ensure_oos_vfid_for_heap_record` (diff 라인 783-799):
```c
if (!heap_recdes_contains_oos (&helper->record) || !VFID_ISNULL (&helper->oos_vfid))
  {
    return NO_ERROR;   // current record OOS 플래그 없으면 VFID 조회 안 함
  }
```

**증거 3 — 함수 내부의 lazy lookup은 정확히 이 시나리오를 "처리하려고" 작성됨:**

`vacuum_cleanup_prev_version_oos` (diff 라인 920-935):
```c
/* Check for OOS in the old version and delete if found. */
if (heap_recdes_contains_oos (&old_recdes))
  {
    /* Lazy VFID lookup — the current record may have no OOS (REMOVE path after UPDATE that
     * dropped an OOS column), but old versions do. */
    if (VFID_ISNULL (&helper->oos_vfid))
      {
        if (!heap_oos_find_vfid (thread_p, &helper->hfid, &helper->oos_vfid, false))
        ...
```

그리고 docstring(diff 라인 808-811)은:

> "oos_vfid may be NULL on entry — it is looked up lazily on the first old version that carries OOS. This matters for the REMOVE path, where the current record may have dropped its OOS columns (no current OOS flag) while old versions in the prev_version_lsa chain still carry OOS."

**분석:** 함수 내부는 "current record에 OOS 없고 prev-version에만 OOS 있는 경우"를 명시적으로 다루도록 작성되었는데, 두 호출자가 모두 `!VFID_ISNULL(&helper->oos_vfid)` 로 gate하므로 **함수 진입 자체가 차단**된다. 즉 lazy lookup 코드는 **프로덕션에서 도달 불가능한 dead code**이며, 유일하게 도달 가능한 경로는 `bridge_vacuum_cleanup_prev_version_oos` 테스트 bridge(그리고 그 bridge는 oos_vfid를 미리 채워서 전달).

**결과:** 다음 시나리오에서 OOS 누수:

```sql
CREATE TABLE t (id INT PRIMARY KEY, oos_col BIT VARYING);
INSERT INTO t VALUES (1, REPEAT(X'AA', 4096));   -- OOS 레코드 생성
UPDATE t SET oos_col = NULL WHERE id = 1;        -- 현재 row에 OOS 플래그 없어짐
DELETE FROM t WHERE id = 1;                      -- row 삭제
-- vacuum 실행 → current record에 OOS 없음 → oos_vfid 설정 안 됨
--           → prev_version_oos_cleanup 가드에서 short-circuit
--           → undo log의 구버전 OOS 레코드 영구 누수
```

이 시나리오는 `vacuum_heap_record`의 주석(diff 라인 1050-1053)이 이미 "known limitation"으로 자인한 바 있다:

> "Known limitation: UPDATEs that drop every OOS column and are then DELETEd leave no OOS flag on the current record; their prev-version OOS leak until a full-table rewrite."

그러나 주석은 "limitation"이라 표현하지만, **함수 내부의 lazy lookup 로직이 이를 처리하도록 명시적으로 작성되어 있기 때문에**, 이는 의도된 한계가 아니라 **가드가 함수 의도를 방해하는 버그**로 보는 것이 더 정확하다.

**권장 조치 (택 1):**

| 옵션 | 변경 | 효과 |
|---|---|---|
| A. 정확성 우선 | 두 가드에서 `!VFID_ISNULL (&helper->oos_vfid)` 제거 | lazy lookup 활성화 → L1 해결. 단, `MVCC_IS_HEADER_PREV_VERSION_VALID`만 남으므로 non-OOS 테이블에서도 chain walk 진입 → 성능 저하. |
| B. 정확성 + 성능 | heap header에 `has_oos_file` bool 캐싱 후 가드를 `!has_oos_file_cached`로 교체 | L1 해결 + 성능 유지. 단 heap header 포맷 변경 필요. |
| C. 명시적 한계 인정 | 가드 유지 + 함수 내부 lazy lookup 코드 제거 + docstring 수정 + PR 설명에 한계 명시 + JIRA 후속 티켓 생성 | 코드 정직해짐. 누수는 미해결. |

**블로커 판정:** 본 PR의 **선언적 목적**("vacuum이 OOS 정리")과 **실제 동작**(일부 경로에서 누수)이 괴리되므로 머지 전 결정 필요.

### 3.2 [L2] SA_MODE DELETE — 영구 누수 (범위 외, 문서화 필요)

**증거:**
- `oos_delete` 호출 지점 grep: `heap_file.c:24178` (SA_MODE eager UPDATE 전용), `vacuum.c:2572, 2634` (MVCC vacuum). **SA_MODE DELETE 경로에서의 호출 없음.**
- PR 자체 테스트 주석 (`test_oos_sql_eager_cleanup.cpp` 라인 19-22):

  > "SA_MODE sets is_mvcc_op=false for all DML. DELETE physically removes the heap slot without cleaning OOS data. Vacuum is a no-op in SA_MODE."

**영향:** standalone utility (loaddb/unloaddb/restoredb 등)에서 DELETE를 수행하는 경로가 있다면 OOS 파일 지속 증가. 본 PR 설명은 "DELETE/UPDATE 시 OOS 정리"라고 포괄적으로 기술하고 있으므로 SA_MODE가 제외됨을 **명시해야 한다**.

**권장 조치:** JIRA CBRD-26668 또는 후속 이슈에 "SA_MODE DELETE는 본 범위 외" 명시. M3/M4에서 `heap_delete_logical`의 non-MVCC branch에 eager cleanup 추가.

### 3.3 [L3] REC_BIGONE + OOS 불변식 — release build에서 조용한 누수

**증거:**

`vacuum_heap_record_insid_and_prev_version` (diff 라인 762-763), `vacuum_heap_record` REC_BIGONE (diff 라인 1109-1112):
```c
/* Invariant: OOS does not coexist with REC_BIGONE. ... Until then, fail loud in debug
 * so the regression is visible. */
assert (!heap_recdes_contains_oos (&helper->record));
```

`assert()`는 `NDEBUG`에서 제거된다. 불변식이 release에서 깨지면 조용히 진행하고 OOS 누수. OOS는 heap 레코드를 **작게 유지**하기 위한 기능이므로 설계상 BIGONE과 공존하지 않아야 하지만, 엣지 케이스(예: 추후 CHAR 타입 OOS 지원)에서 위반 가능성 존재.

**권장 조치:** `assert_release`로 교체하여 release에서도 트랩, 또는 `ER_FAILED` 반환 + 에러 로그.

### 3.4 [L4] RELOCATION 누적 시나리오 회귀 테스트 부재

**분석:** `vacuum_heap_record`의 `has_oos` 판정은 `REC_HOME || REC_RELOCATION`만 허용 (diff 라인 1037-1039). UPDATE로 인한 여러 RELOCATION 체인(home 슬롯 → new home 슬롯)을 연속으로 유발하는 워크로드에서, 이전 home/relocation 슬롯이 `REC_MARKDELETED` 또는 `REC_DELETED_WILL_REUSE`로 남고 그것이 OOS를 참조하는 경우를 vacuum이 처리하는지 이 PR 범위에서 직접적으로 검증되지 않는다.

현재 테스트(`test_oos_sql_vacuum.cpp`, `test_oos_sql_eager_cleanup.cpp`)는 INSERT → UPDATE → DELETE 단순 패턴 위주이며, **RELOCATION을 유발하기 위한 heap page fragmentation 유도 시나리오가 없다**.

**권장 조치:** "좁은 heap 페이지에서 UPDATE 반복으로 RELOCATION 강제 → DELETE → vacuum → OOS 파일 page count 확인" 회귀 테스트 추가.

---

## 4. 부수 효과 분석 (Collateral)

### 4.1 transform_cl.c / catalog_class.c의 4-byte 정렬 변경 — **주의 필요**

17개 이상의 catalog 직렬화 함수에서 VOT offset 및 variable area 사이에 `DB_ALIGN(…, 4)` 삽입. 이유는 명시됨: `OR_GET_VAR_OFFSET()`이 하위 2비트를 마스킹하므로 unaligned offset은 `OR_IS_OOS` false positive를 일으킨다.

**우려:** **catalog 레코드의 on-disk 포맷이 변경**된다. feat/oos 브랜치 내부라면 dev 환경 재생성으로 해결 가능하지만, 이 브랜치가 main으로 머지될 때 기존 DB가 unaligned offset을 가진 채 존재할 가능성을 **PR 설명이 다루지 않는다**.

`heap_recdes_check_has_oos`의 sanity check(diff 라인 1539-1544)가 first VOT entry의 offset 범위를 검증하여 파손된 catalog를 감지는 하겠지만, migration path는 없다.

**권장 조치:**
- feat/oos 브랜치 내부 호환성: 모든 테스트 DB 재생성 강제됨을 PR 설명에 명시.
- main 머지 시점: 기존 catalog의 VOT offset이 이미 4의 배수였는지 별도 확인 + migration 가이드.

### 4.2 `heap_recdes_contains_oos`의 debug-only cross-validation

MVCC flag vs VOT scan 불일치를 debug build에서 감지하고 assert (diff 라인 1451-1489, 1499-1506). OOS 플래그 일관성 검증으로 유용하지만, 매 호출마다 VOT 전체 스캔을 수행하므로 debug build 성능 저하 가능. release build에는 무영향.

### 4.3 `heap_recdes_check_has_oos`의 로직 변경 — **미묘한 의미 변경**

기존: LAST_ELEMENT를 만나지 못하면 `assert(false)`. 변경: LAST_ELEMENT를 만나지 못하면 조용히 `return false` (diff 라인 1570-1572).

**주석:** "No LAST_ELEMENT found — old-format VOT without OOS flag support. Odd offsets in old records would false-positive OR_IS_OOS, so return false."

의도는 이해되나, 이 "old-format" fallback 덕분에 **진짜 corruption (LAST_ELEMENT 비트가 손상된 정상 OOS record)가 false negative로 가려진다.** 기존 assert가 이런 corruption을 잡아내던 역할을 잃었다. sanity check(첫 offset 범위 검증) 이후라면 LAST_ELEMENT 부재는 여전히 비정상 신호일 것이다.

**권장 조치:** debug build에서는 `_er_log_debug` 경고를 남기도록 보강 (silent false 대신 diagnostic).

---

## 5. 기존 PR 코멘트 재평가

| 작성자 | 심각도 | 주제 | 현 상태 평가 |
|---|---|---|---|
| greptile-apps | P1 | `locator_delete_oos_force` 이중 삭제 | **grep 결과 이 함수는 현 소스에 존재하지 않음** — greptile 환각 또는 이미 제거됨. 무효 코멘트. |
| greptile-apps | P1 | `heap_oos_find_vfid` 반환값 `(void)` 캐스팅 | 본 PR에서 `vacuum_ensure_oos_vfid_for_heap_record`로 해결 (실패 시 `assert_release(false)` + `ER_FAILED` 반환). **해결됨.** |
| greptile-apps | P1 | `oos_find_best_page` TOCTOU | 본 PR 변경 아닌 `oos_file.cpp` 기존 코드. **범위 외.** |
| greptile-apps | P2 | `oos_stats_add_bestspace` mutex 주석 | 기존 코드. **범위 외.** |
| greptile-apps | P2 | REC_HOME + OOS 로깅 순서 | undo 데이터는 `spage_vacuum_slot` 이전에 COPY 모드로 사전 읽은 `helper->record`이므로 데이터 정합성 OK. WAL 순서도 append → flush 순서 유지. **버그 아님**, 주석 보강만 권장. |
| vimkim | info | sql/medium CI 통과 | 참고. |

---

## 6. 사용자 질문 직답 (Direct Answer)

> "does this clean up all unreachable OOS values?"

**아니오.** 다음 경로에서 unreachable OOS는 누수된다:

1. **[L1, 핵심 버그]** UPDATE가 모든 OOS 컬럼을 일반 컬럼으로 교체한 뒤 DELETE된 row의 prev-version 체인.  
   → `vacuum_cleanup_prev_version_oos` 호출자 가드가 `!VFID_ISNULL(&helper->oos_vfid)`로 gate하지만, 이 조건은 current record에 OOS가 있을 때만 참. 함수 내부의 lazy VFID lookup은 이 시나리오를 **처리하도록 명시적으로 작성되었으나** 호출 자체가 차단되어 dead code가 되어 있다.
2. **[L2, 범위 외지만 중요]** SA_MODE DELETE. `oos_delete` 호출 경로 없음, vacuum도 no-op.
3. **[L3, 방어 부족]** REC_BIGONE + OOS 공존 시 release build에서 조용히 누수 (debug-only `assert`).
4. **[L4, 검증 미흡]** RELOCATION 누적 워크로드에 대한 회귀 테스트 부재.

가장 흔한 경로 — MVCC DELETE, UPDATE 체인에서 OOS 컬럼이 유지되는 케이스 — 는 확실히 커버된다. 그러나 **"모든" unreachable OOS를 정리한다는 목표는 달성되지 않았다.**

---

## 7. 권장 조치 우선순위

| Priority | 조치 | 블로커? |
|---|---|---|
| **P1** | L1 해결 — 가드의 `!VFID_ISNULL` 제거(+성능 보상 캐싱) 또는 dead-code lazy lookup 제거 + 한계 명시 | **머지 전 결정 필요** |
| P2 | L3 — `assert` → `assert_release` 또는 `ER_FAILED` 반환으로 방어 강화 | non-blocker, 권장 |
| P2 | L4 — RELOCATION 누적 회귀 테스트 추가 | non-blocker, 권장 |
| P3 | L2 — SA_MODE DELETE eager cleanup은 후속 JIRA로 분리, 본 PR/이슈에 명시 | 범위 외 |
| P3 | 4.1 — catalog 정렬 변경의 포맷 migration 영향을 PR 설명에 명시 | 머지 전 확인 권장 |
| P3 | 4.3 — `heap_recdes_check_has_oos`의 silent `return false` 경로에 debug warning 추가 | non-blocker |

---

**리뷰어:** Claude Opus 4.7 (1M context)  
**리뷰 방법:** PR 메타/diff/기존 코멘트/JIRA/cubrid-oos-context 스킬 참조 + 전역 grep으로 `oos_delete` 호출 지점 3개만 존재 확인. 이를 기반으로 "호출 지점이 커버하지 않는 OOS 생성 경로"를 역추적하여 L1-L4 도출. 특히 L1은 함수 docstring과 실제 호출 가드의 의도 불일치에서 발견.
