# [CBRD-26950] PR 재구성 가이드 — 커밋 01d110e8a 를 문서만 보고 다시 만들기

- 대상 PR: https://github.com/CUBRID/cubrid/pull/7695 (`[CBRD-26950] Verify OOS chain identity before vacuum delete`)
- 대상 커밋: `01d110e8a` (25 files, +729 −243)
- 출발점(base): `feat/oos` + `origin/develop` 머지 `07fef9d48`
- JIRA: https://jira.cubrid.org/browse/CBRD-26950 · 배경 설명: [PR 상세 문서](./CBRD-26950-oos-generation-identity-stamp_01d110e_claude.md)

이 문서 하나로 같은 PR 을 재구성할 수 있도록 두 층으로 쓴다. **Part 1** 은 구현 순서와 "여기서 틀리기 쉬운" 설계 불변식 — 처음부터 다시 유도할 때 필요한 판단 전부. **Part 2** 는 파일별 전체 diff 원문 — 바이트 단위로 동일하게 재현하기 위한 최종 근거. Part 1 을 따라 짜다가 막히면 Part 2 의 해당 파일 hunk 를 그대로 적용하면 된다.

## Part 1 — 재구성 절차

### 0. 전제

```bash
git checkout -b CBRD-26950-oos-vacuum-delete-overlap 07fef9d48
./build.sh -m debug -c "-DUNIT_TESTS=ON"   # 이후 각 단계마다 재빌드로 확인
```

변경 요지 한 줄: **모든 OOS 청크에 페이지 카운터가 발급한 4B generation 을 스탬프하고, heap 의 OOS inline stub 에 같은 값을 실어 두었다가, `oos_delete` 가 삭제 직전에 등가 비교한다. 불일치·부재는 에러 없는 no-op.**

### 설계 불변식 — 재구성 시 틀리기 쉬운 지점 9가지

이 9가지를 지키지 않으면 컴파일은 되지만 다른(틀린) PR 이 된다.

1. **카운터 커밋은 insert 성공 뒤에.** `oos_insert_record_in_fixed_page` 는 ① slot 0 헤더를 PEEK 해 `counter+1` 을 *발급만* 하고 청크 헤더에 스탬프 → ② `spage_insert` 성공 → ③ **헤더 포인터를 다시 PEEK** 한 뒤 카운터를 커밋한다. 순서를 바꾸면 실패한 insert 가 값을 태우고, 재-PEEK 를 빼먹으면 `spage_insert` 의 페이지 compaction 이 옮겨 놓은 레코드의 옛 주소에 쓴다.
2. **카운터 갱신에 별도 로그가 없다.** 청크 자신의 `RVOOS_INSERT` 가 카운터까지 커버한다(같은 페이지, 같은 latch 구간, 로그 append 가 page LSA 를 찍는다). redo 는 청크 이미지의 generation 으로 카운터를 재유도한다.
3. **redo 의 카운터 재생은 대입이 아니라 MAX.** `oos_rv_redo_insert` 는 `RVOOS_INSERT` 의 redo *이자* `RVOOS_DELETE` 의 undo(롤백 복원)다. 대입이면 옛 청크 복원이 카운터를 퇴행시켜 살아있는 stub 이 기대하는 generation 을 재발급할 수 있다. `if (counter < chunk_gen) counter = chunk_gen;` 만 허용된다. slot 0 삽입(파일 헤더 페이지의 `OOS_HDR_STATS`, 데이터 페이지의 `OOS_PAGE_HEADER`)은 이 분기에 들어가면 안 된다 — `slotid != OOS_PAGE_HEADER_SLOT` 게이트.
4. **페이지 초기화가 두 갈래로 갈라진다.** sticky first page(파일 헤더)는 기존 `oos_vpid_init_new` 그대로(slot 0 = `OOS_HDR_STATS`), 데이터 페이지만 신설 `oos_vpid_init_new_data_page` 가 slot 0 에 `OOS_PAGE_HEADER`(counter=0) 를 심고 **`RVOOS_NEWPAGE` 하나로** 로깅한다(redo 가 페이지 타입 + spage 초기화 + slot 0 재삽입까지 재현, heap 의 `RVHF_NEWPAGE` 패턴). `oos_file_alloc_new` 의 `file_alloc` 콜백만 교체한다.
5. **페이지 용량이 12B 줄어든다.** `oos_get_data_page_capacity()` = `DB_ALIGN_BELOW (spage_max_record_size () - (DB_ALIGN (OOS_PAGE_HEADER_SIZE, OOS_ALIGNMENT) + SPAGE_SLOT_SIZE), OOS_ALIGNMENT)`. `oos_get_max_chunk_size_within_page`, `oos_insert_many` 의 `page_capacity`, `oos_insert_within_page` 의 assert 가 전부 이 함수를 따라야 한다. 배치 삽입의 "빈 페이지" 판정은 `spage_number_of_records (page_ptr) <= 1` (slot 0 헤더가 상주).
6. **검증은 `oos_delete` 안에서, 단 한 곳.** 시그니처에 `unsigned int expected_generation` 을 추가하고, 내부 probe `oos_chain_head_matches` 가 「페이지 dealloc / 슬롯 부재 / generation 불일치」를 전부 `*out_matches=false` + `NO_ERROR` 로 돌린다. 기존 `oos_chunk_exists` 는 **삭제** 하고 forward-walk 의 사전 probe 도 제거한다(이중 fix 방지). `oos_delete_chain` 루프에는 `current_oid.slotid == OOS_PAGE_HEADER_SLOT` 이면 corruption 에러를 내는 가드를 추가한다(오염된 체인 링크가 헤더 레코드를 지우는 사고 방지).
7. **stub 은 20B, 세 필드 순서 고정.** `OR_OOS_INLINE_SIZE = OR_OID_SIZE + OR_BIGINT_SIZE + OR_INT_SIZE`. 직렬화는 `or_put_oid → or_put_bigint → or_put_int` (network order). 추출(`heap_recdes_get_oos_refs`)은 `OR_GET_INT (ptr + OR_OID_SIZE + OR_BIGINT_SIZE)`. 파싱 측 경계 검사 세 곳(`heap_oos_parse_inline_ref`, `heap_file.c` 의 midxkey 크기 검증, 추출기 bounds)은 `OR_OOS_INLINE_SIZE` 기준으로 통일한다.
8. **HA fixup 은 스토리지를 읽지 않는다.** 발급 결과 publication(`thread_p->oos_oids`)을 `(OID, generation)` 쌍(`oos_published_ref`)으로 확장하고, slave 의 `locator_fixup_oos_oids_in_recdes` 는 publish 된 쌍만으로 stub 의 OID·generation 을 재기록한다(중간 8B full length 는 `or_advance` 로 건너뜀). fixup 에서 `oos_get_generation` 으로 재조회하는 설계는 두 가지로 실패한다 — ① master generation 이 남으면 slave vacuum 이 전부 no-op(영구 누수), ② 합성 OID 를 쓰는 단위 테스트에서 debug 빌드의 disk sector assert 로 프로세스가 죽는다. 멀티청크 경계 마커는 `{oid_Null_oid, 0}`.
9. **demotion 수익성 경계가 16B→20B 로 이동한다.** 코드는 상수를 따라 자동으로 움직이지만 **테스트가 움직이지 않는다**: FORCE_OUTLINE 경계 테스트의 페이로드를 14/15자(packed 16/20B)에서 **18/19자(packed 20/24B)** 로 옮겨야 한다 (`packed(n) = ALIGN(n+2, 4)`).

### 재구성 순서 — 10단계

컴파일 가능 상태를 유지하며 아래 순서로 진행한다. 각 단계의 정확한 코드는 Part 2 의 해당 파일 diff 에 있다.

| 단계 | 파일 | 작업 |
|---|---|---|
| 1 | `src/base/object_representation.h` | `OR_OOS_INLINE_SIZE` 를 `(OR_OID_SIZE + OR_BIGINT_SIZE + OR_INT_SIZE)` 로, 주석에 generation 4B 명시 |
| 2 | `src/storage/oos_file.hpp` | ① `oos_record_header` 에 `unsigned int generation` 추가 ② `OOS_PAGE_HEADER` 구조체 + `OOS_PAGE_HEADER_SIZE` + `OOS_PAGE_HEADER_SLOT 0` ③ `oos_chain_ref { OID head_oid; unsigned int generation; }` ④ `oos_insert_request` 에 `unsigned int *generation_out` ⑤ `oos_insert(..., unsigned int *generation_out = NULL)` — 기본 인자는 선언에만 ⑥ `oos_delete(..., unsigned int expected_generation)` ⑦ `oos_get_generation`, `oos_rv_redo_newpage` 선언, `oos_chunk_exists` 선언 삭제 ⑧ `#include "recovery.h"` 추가 (`LOG_RCV` — oos_util.hpp 가 이 헤더를 물게 되면서 자급자족해야 함) |
| 3 | `src/storage/oos_file.cpp` | 이번 PR 의 본체. (a) 발급: `oos_insert_record_in_fixed_page` 에 불변식 1 의 3단계 시퀀스 + `generation_out` 아웃파라미터, `oos_insert_within_page`/`oos_insert_across_pages`(head=마지막 반복의 값)/`oos_insert_single_page_batch`/`oos_insert_many` 로 전파 (b) 페이지: `oos_vpid_init_new_data_page` + `oos_get_page_header_ptr` 신설, `oos_file_alloc_new` 콜백 교체 (c) 용량: `oos_get_data_page_capacity` 신설 + 3개 사용처 교체 + `page_was_empty <= 1` (d) 삭제: `oos_chain_head_matches` 신설, `oos_delete` 검증 삽입, `oos_chunk_exists` 삭제, chain 루프 slot-0 가드 (e) 복구: `oos_rv_redo_insert` MAX 재생, `oos_rv_redo_newpage` 신설 (f) publication: `oos_publish_oos_oid (thread_p, oid, generation)` 쌍 push (g) 통계: `oos_get_stats_by_vfid` walk 에서 slot 0 skip (h) 진단: `oos_get_generation` 신설 |
| 4 | `src/transaction/recovery.h` / `recovery.c` | `RVOOS_NEWPAGE = 140` 을 enum 끝(139 뒤)에 추가, `RV_LAST_LOGID = RVOOS_NEWPAGE`. `RV_fun[]` 끝에 `{RVOOS_NEWPAGE, "RVOOS_NEWPAGE", pgbuf_rv_new_page_undo, oos_rv_redo_newpage, NULL, NULL}`. 위치를 중간에 넣으면 positional 테이블이 깨진다. 기존 feat/oos 테스트 DB 는 재생성 대상 |
| 5 | `src/thread/thread_entry.hpp` | `entry` 클래스 안에 `struct oos_published_ref { OID oid; unsigned int generation; };` 를 정의하고 `oos_oids` 를 `std::vector<oos_published_ref>` 로 교체 (`.clear()` 호출부는 무변경으로 호환) |
| 6 | `src/storage/heap_file.h` / `heap_file.c` | 헤더: `struct oos_chain_ref;` 전방선언 + `using OOS_REF_VECTOR = std::vector<oos_chain_ref>;` + `heap_recdes_get_oos_refs` 선언(구 `heap_recdes_get_oos_oids` 대체). 소스: ① `heap_oos_column_plan` 에 `unsigned int generation = 0` ② insert request 에 `&plan.generation` ③ stub 직렬화에 `or_put_int (buf, (int) oos_plan->generation)` ④ 추출기 개명·refs 화(bounds 는 `OR_OOS_INLINE_SIZE`) ⑤ midxkey 검증 bound 교체 |
| 7 | `src/storage/heap_oos.cpp` + `src/storage/oos_util.hpp/.cpp` | eager 경로(`heap_oos_delete_unreferenced`)를 refs 로 전환, `oos_delete` 에 generation 전달. `oos_ref_in_vector (refs, &oid)` 헬퍼 추가(oos_util 이 oos_file.hpp 를 include). `heap_oos_parse_inline_ref` bounds 를 `OR_OOS_INLINE_SIZE` 로 |
| 8 | `src/query/vacuum_oos.cpp` | forward-walk: `std::vector<OID>` → `OOS_REF_VECTOR`(값 전달 유지 — 로그 페이지 rotation 방어), head_oid 기준 정렬, **사전 `oos_chunk_exists` probe 삭제** 후 `oos_delete (thread_p, *oos_vfid, ref.head_oid, ref.generation)` 직행. REMOVE 경로(`vacuum_heap_oos_delete_within_sysop`)도 동일 전환 |
| 9 | `src/transaction/locator_sr.c` + `log_applier.c` | repl 루프 2곳: `thread_p->oos_oids[i]` → `.oid`. fixup: `or_put_oid` 뒤에 `or_advance (&buf, OR_BIGINT_SIZE); or_put_int (&buf, (int) thread_p->oos_oids[oos_oid_count].generation);`. applier 의 merged header aggregate 초기화에 4번째 필드 `0` 명시 |
| 10 | `unit_tests/oos/` 10개 파일 | 아래 「테스트 변경 요약」 참조 |

### 테스트 변경 요약 (단계 10)

- **공용 헬퍼** (`test_oos_common.hpp`, `test_oos_server_common.hpp`): `oos_delete_current_generation (thread_p, vfid, oid)` 추가 — `oos_get_generation` 으로 현재 값을 읽어 `oos_delete` 호출. 부재 시 get 단계에서 에러가 나므로 "지워진 것을 또 지우면 에러" 라는 기존 테스트 관측치가 보존된다.
- **직접 `oos_delete` 호출 31곳** (`test_oos_delete*.cpp`, `test_oos_bestspace.cpp`, `test_oos_mock_vacuum_server.cpp`): `= oos_delete (thread_p, X, Y);` → `= test_oos_utils::oos_delete_current_generation (thread_p, X, Y);` 기계적 치환.
- **inline 포맷 테스트** (`test_oos.cpp`, `test_oos_server.cpp`): `ASSERT_EQ (OR_OOS_INLINE_SIZE, 16)` → 20 (+`OR_INT_SIZE` 항), 라운드트립에 `or_put_int`/`or_get_int` 로 generation 추가, 실삽입 변형은 `oos_get_generation` 으로 실제 값을 스탬프.
- **합성 heap recdes 빌더** (`test_oos_vacuum_server.cpp`, `test_oos_real_vacuum_server.cpp`): `OOS_INLINE_SZ = OR_OOS_INLINE_SIZE` 로 교체, stub 에 generation 필드 기록. vacuum_server 빌더에는 `bool synthetic_oids = false` 파라미터 — 삽입된 적 없는 더미 OID 는 **스토리지를 조회하지 않고** 0 스탬프 (debug 빌드에서 미할당 페이지 `pgbuf_fix` 는 assert abort). 더미를 쓰는 유일한 호출부(TC-V1)만 `true` 전달.
- **추출기 테스트** (`test_oos_vacuum_server.cpp` TC-V2/V3): `OID_VECTOR`+`heap_recdes_get_oos_oids` → `OOS_REF_VECTOR`+`heap_recdes_get_oos_refs`, `.head_oid` 필드 비교 + 추출된 generation 이 `oos_get_generation` 값과 같은지 신규 검증.
- **publication 테스트** (`test_oos_server.cpp`): `thread_p->oos_oids` 요소 접근을 `.oid` 로, 시딩은 `{ {oid, 0} }` 쌍으로.
- **경계 SQL 테스트** (`sql/test_oos_sql_storage.cpp`): `ForceOutlineBypassesRecordGateOnlyAboveInlineStubSize` 의 페이로드 14/15자 → 18/19자, `DISK_SIZE` 기대값 16→20 / `>16`→`>20`.
- **free-space 정확치** (`test_oos.cpp` `ShouldInsertIntoDifferentPages`): max 청크 삽입 후 페이지 free space 기대값 `4` → `0` (slot 0 헤더가 옛 정렬 여유를 흡수해 페이지가 정확히 가득 찬다).

### 검증

```bash
ctest --test-dir build_preset_debug_gcc -R oos        # 25/25 통과해야 함
# JIRA 첨부 재현 스크립트 (debug 빌드, $CUBRID/$CUBRID_DATABASES 설정 후):
./cbrd-26950-poc.sh                                   # 기대: exit 1 (미발현)
```

PoC 합격 기준 세 가지를 모두 확인한다: ① 두 pass 재삭제 OOS OID 0건 ② 판독 불가 커밋 행 0건 ③ `SHOW HEAP OOS` 의 살아있는 체인 수가 「UPDATE 후 R1 행 수 + 커밋된 R3 행 수」와 정확히 일치(정당한 회수가 유지됨 — no-op 이 과도하게 넓지 않다는 증거).

## Part 2 — 파일별 전체 diff 원문

아래는 커밋 `01d110e8a` 의 전체 diff 를 파일별로 나눈 것이다. 각 hunk 를 그대로 적용하면 Part 1 의 결과물과 바이트 단위로 동일해진다. 들여쓰기는 원문 그대로(탭 포함)이므로 복사 시 변환하지 않는다.

### 1. `src/base/object_representation.h`

단계 1 — stub 상수 16B → 20B. 이 상수 하나로 demotion 수익성 경계(>16B → >20B)와 파싱 측 경계 검사가 함께 움직인다.

```diff
diff --git a/src/base/object_representation.h b/src/base/object_representation.h
index 7253cdbb4..14dfaebaa 100644
--- a/src/base/object_representation.h
+++ b/src/base/object_representation.h
@@ -455,8 +455,8 @@ OR_PUT_DOUBLE (char *ptr, double val)
 #define OR_IS_OOS(length) (OR_GET_VAR_FLAG (length) & OR_VAR_BIT_OOS)
 #define OR_IS_LAST_ELEMENT(length) (OR_GET_VAR_FLAG (length) & OR_VAR_BIT_LAST_ELEMENT)
 
-/* OOS inline size: OOS OID (8 bytes) + OOS length (8 bytes) */
-#define OR_OOS_INLINE_SIZE (OR_OID_SIZE + OR_BIGINT_SIZE)
+/* OOS inline size: OOS OID (8 bytes) + OOS length (8 bytes) + generation (4 bytes, CBRD-26950) */
+#define OR_OOS_INLINE_SIZE (OR_OID_SIZE + OR_BIGINT_SIZE + OR_INT_SIZE)
 
 /* variable offset */
 
```

### 2. `src/query/vacuum_oos.cpp`

단계 8 — forward-walk 와 REMOVE 경로를 refs 로. 사전 존재 probe 삭제, 검증은 oos_delete 내부 한 곳으로.

```diff
diff --git a/src/query/vacuum_oos.cpp b/src/query/vacuum_oos.cpp
index 515f49afc..f3fecc98c 100644
--- a/src/query/vacuum_oos.cpp
+++ b/src/query/vacuum_oos.cpp
@@ -58,7 +58,7 @@ typedef enum
 static VACUUM_OOS_VFID_LOOKUP_RESULT vacuum_oos_vfid_lookup (THREAD_ENTRY *thread_p,
     VACUUM_OOS_VFID_MEMO *memo, const VFID *heap_vfid, VFID *out_oos_vfid);
 static int vacuum_forward_walk_oos_delete_atomic (THREAD_ENTRY *thread_p, const VFID *oos_vfid,
-    std::vector<OID> oos_oids);
+    OOS_REF_VECTOR oos_refs);
 
 /*
  * vacuum_oos_vfid_lookup () - Find the OOS file that belongs to a given heap file.
@@ -138,9 +138,9 @@ vacuum_oos_vfid_lookup (THREAD_ENTRY *thread_p, VACUUM_OOS_VFID_MEMO *memo, cons
  *   points to. As vacuum walks the undo log, it finds the "pre-image" (how the row looked before an
  *   UPDATE); that old image may still reference OOS records nobody can reach anymore.
  *
- *   The OID list comes in BY VALUE so this helper owns its own copy. That matters: oos_delete can
- *   rotate (swap out) the log page that the caller's original undo_data points into, so we must work
- *   from a copy that does not live in that buffer.
+ *   The reference list comes in BY VALUE so this helper owns its own copy. That matters: oos_delete
+ *   can rotate (swap out) the log page that the caller's original undo_data points into, so we must
+ *   work from a copy that does not live in that buffer.
  *
  *   All the deletes run inside one "sysop" (system operation) - the engine's unit of
  *   all-or-nothing work for crash recovery - so the whole multi-chunk delete either fully happens
@@ -151,41 +151,33 @@ vacuum_oos_vfid_lookup (THREAD_ENTRY *thread_p, VACUUM_OOS_VFID_MEMO *memo, cons
  *   other log record types must be excluded.
  */
 static int
-vacuum_forward_walk_oos_delete_atomic (THREAD_ENTRY *thread_p, const VFID *oos_vfid, std::vector<OID> oos_oids)
+vacuum_forward_walk_oos_delete_atomic (THREAD_ENTRY *thread_p, const VFID *oos_vfid, OOS_REF_VECTOR oos_refs)
 {
   int error_code = NO_ERROR;
 
-  /* Sort the OIDs by (volid, pageid, slotid). Deleting in this order means back-to-back oos_delete
-   * calls touch nearby pages, so a page we just loaded stays in the buffer pool (better locality).
-   * This matches how the heap itself is scanned. We own this vector (passed by value), so we can
-   * sort it in place. */
-  std::sort (oos_oids.begin (), oos_oids.end (),
-	     [] (const OID &a, const OID &b)
+  /* Sort the references by head OID (volid, pageid, slotid). Deleting in this order means
+   * back-to-back oos_delete calls touch nearby pages, so a page we just loaded stays in the buffer
+   * pool (better locality). This matches how the heap itself is scanned. We own this vector
+   * (passed by value), so we can sort it in place. */
+  std::sort (oos_refs.begin (), oos_refs.end (),
+	     [] (const oos_chain_ref &a, const oos_chain_ref &b)
   {
-    return oid_compare (&a, &b) < 0;
+    return oid_compare (&a.head_oid, &b.head_oid) < 0;
   });
 
-  /* TODO(perf): oos_delete fixes and unfixes the OOS page on every call. The OIDs above are already
-   * sorted into page order, so one day we should group the OIDs that share a page and delete them
-   * under a single pgbuf_fix, instead of re-fixing the same page once per OID. */
+  /* TODO(perf): oos_delete fixes and unfixes the OOS page on every call. The references above are
+   * already sorted into page order, so one day we should group the ones that share a page and
+   * delete them under a single pgbuf_fix, instead of re-fixing the same page once per OID. */
   log_sysop_start (thread_p);
-  for (const OID &oid : oos_oids)
+  for (const oos_chain_ref &ref : oos_refs)
     {
       /* This has to be safe to run twice. If the whole block is retried, an earlier forward-walk in
-       * this block may have already committed its deletes, so an OID's chunk can already be gone. In
-       * that case just skip it instead of failing inside oos_delete. We still report a real failure
-       * (I/O error, interrupt, etc.) as an error. */
-      bool exists;
-      error_code = oos_chunk_exists (thread_p, oid, &exists);
-      if (error_code != NO_ERROR)
-	{
-	  break;
-	}
-      if (!exists)
-	{
-	  continue;
-	}
-      error_code = oos_delete (thread_p, *oos_vfid, oid);
+       * this block may have already committed its deletes, so a chunk can already be gone — or its
+       * slot can already hold ANOTHER live chain's data (OOS OIDs are physical addresses and freed
+       * slots are reused). oos_delete tells these apart from the stub's expected generation and
+       * no-ops on both, so a retry can never destroy the reusing chain (CBRD-26950). We still
+       * report a real failure (I/O error, interrupt, etc.) as an error. */
+      error_code = oos_delete (thread_p, *oos_vfid, ref.head_oid, ref.generation);
       if (error_code != NO_ERROR)
 	{
 	  break;
@@ -239,7 +231,7 @@ vacuum_forward_walk_reclaim_oos (THREAD_ENTRY *thread_p, char *undo_data, int un
    * REC_BIGONE / REC_RELOCATION slot, which is only an 8-byte OID. If we handed one of those to
    * heap_recdes_contains_oos, it would read the OID's pageid as if it were an MVCC header. A pageid
    * that happens to have bit 27 set would look like the "has OOS" flag, and then
-   * heap_recdes_get_oos_oids would chase a garbage reference list and hit assert_release. So we
+   * heap_recdes_get_oos_refs would chase a garbage reference list and hit assert_release. So we
    * check the record type first - the same guard the eager-delete paths use (REC_HOME / REC_NEWHOME).
    */
   if (! ((undo_recdes.type == REC_HOME || undo_recdes.type == REC_NEWHOME) && heap_recdes_contains_oos (&undo_recdes)))
@@ -254,7 +246,7 @@ vacuum_forward_walk_reclaim_oos (THREAD_ENTRY *thread_p, char *undo_data, int un
    * there - usually zeros or another page's data - and quietly find nothing. (Seen live: the flags
    * byte at this address changed from 0x69 to 0x00 across the lookup.) The copy also fixes
    * alignment: the image starts at undo_data + sizeof (INT16), and the OR_BUF readers used by
-   * heap_recdes_get_oos_oids would assert on that unaligned pointer in debug builds. */
+   * heap_recdes_get_oos_refs would assert on that unaligned pointer in debug builds. */
   RECDES parse_recdes = undo_recdes;
   char *stable_copy = (char *) db_private_alloc (thread_p, undo_recdes.length);
   if (stable_copy == NULL)
@@ -282,12 +274,12 @@ vacuum_forward_walk_reclaim_oos (THREAD_ENTRY *thread_p, char *undo_data, int un
     }
   else if (lookup_result == VACUUM_OOS_VFID_FOUND)
     {
-      std::vector<OID> oos_oids;
-      int oos_err = heap_recdes_get_oos_oids (&parse_recdes, oos_oids);
+      OOS_REF_VECTOR oos_refs;
+      int oos_err = heap_recdes_get_oos_refs (&parse_recdes, oos_refs);
 
       if (oos_err == NO_ERROR)
 	{
-	  oos_err = vacuum_forward_walk_oos_delete_atomic (thread_p, &oos_vfid, std::move (oos_oids));
+	  oos_err = vacuum_forward_walk_oos_delete_atomic (thread_p, &oos_vfid, std::move (oos_refs));
 	}
 
       if (oos_err != NO_ERROR)
@@ -400,8 +392,8 @@ int
 vacuum_heap_oos_delete_within_sysop (THREAD_ENTRY *thread_p, const VFID *oos_vfid, const RECDES *record)
 {
   assert (!VFID_ISNULL (oos_vfid));
-  std::vector<OID> oos_oids;
-  int error_code = heap_recdes_get_oos_oids (record, oos_oids);
+  OOS_REF_VECTOR oos_refs;
+  int error_code = heap_recdes_get_oos_refs (record, oos_refs);
   if (error_code != NO_ERROR)
     {
       assert_release (false);
@@ -411,13 +403,14 @@ vacuum_heap_oos_delete_within_sysop (THREAD_ENTRY *thread_p, const VFID *oos_vfi
   /* TODO(perf): oos_delete fixes and unfixes the OOS page on every call. When a record references
    * several OOS values on the same page, one day we should sort/group them by page and delete all of
    * a page's values under a single pgbuf_fix, instead of re-fixing the same page once per OID. */
-  for (const OID &oos_oid : oos_oids)
+  for (const oos_chain_ref &oos_ref : oos_refs)
     {
-      error_code = oos_delete (thread_p, *oos_vfid, oos_oid);
+      error_code = oos_delete (thread_p, *oos_vfid, oos_ref.head_oid, oos_ref.generation);
       if (error_code != NO_ERROR)
 	{
 	  vacuum_er_log_error (VACUUM_ER_LOG_HEAP,
-			       "Failed to delete OOS record %d|%d|%d.", oos_oid.volid, oos_oid.pageid, oos_oid.slotid);
+			       "Failed to delete OOS record %d|%d|%d.", oos_ref.head_oid.volid,
+			       oos_ref.head_oid.pageid, oos_ref.head_oid.slotid);
 	  return error_code;
 	}
     }
```

### 3. `src/storage/heap_file.c`

단계 6 — plan.generation, insert request 연결, stub 직렬화 or_put_int, 추출기 refs 화(bounds = OR_OOS_INLINE_SIZE), midxkey 검증 bound.

```diff
diff --git a/src/storage/heap_file.c b/src/storage/heap_file.c
index 392719027..20c751ac6 100644
--- a/src/storage/heap_file.c
+++ b/src/storage/heap_file.c
@@ -692,6 +692,7 @@ struct heap_oos_column_plan
   bool selected = false;
   OID oid = OID_INITIALIZER;
   DB_BIGINT length = 0;
+  unsigned int generation = 0;	/* identity stamp of the inserted value chain (CBRD-26950) */
 };
 static int heap_attrinfo_determine_disk_layout (HEAP_CACHE_ATTRINFO * attr_info, bool is_mvcc_class,
 						size_t * offset_size_ptr,
@@ -10913,7 +10914,7 @@ heap_midxkey_get_oos_extra_size (RECDES * recdes, OR_ATTRIBUTE * att)
       return 0;
     }
 
-  /* Extract OOS length from inline data: [OOS OID (8B) + length (8B)] */
+  /* Extract OOS length from inline data: [OOS OID (8B) + length (8B) + generation (4B)] */
   OR_BUF buf;
   OID oos_oid;
   int rc = NO_ERROR;
@@ -10926,7 +10927,7 @@ heap_midxkey_get_oos_extra_size (RECDES * recdes, OR_ATTRIBUTE * att)
    * would mis-size midxkey.buf and let the legitimate columns overrun it before the read path
    * raises ER_HEAP_OOS_BAD_INLINE_HEADER.  Return 0 so the buffer is sized from recdes->length
    * alone; the corruption is then surfaced when the value is actually read. */
-  if (buf.endptr - buf.ptr < OR_OID_SIZE + OR_BIGINT_SIZE)
+  if (buf.endptr - buf.ptr < OR_OOS_INLINE_SIZE)
     {
       return 0;
     }
@@ -12487,7 +12488,9 @@ heap_attrinfo_prepare_oos_insert_requests (THREAD_ENTRY * thread_p, HEAP_CACHE_A
 	}
 
       plan.length = (DB_BIGINT) payload.length;
-      oos_insert_request request = { oos_buffer (payload.data, (size_t) payload.length), &plan.oid };
+      oos_insert_request request = { oos_buffer (payload.data, (size_t) payload.length), &plan.oid,
+	&plan.generation
+      };
       payloads->push_back (payload);
       requests->push_back (request);
     }
@@ -12891,6 +12894,7 @@ heap_attrinfo_transform_variable_to_disk (THREAD_ENTRY * thread_p, HEAP_CACHE_AT
       buf->ptr = *ptr_varvals;
       or_put_oid (buf, &oos_plan->oid);
       or_put_bigint (buf, oos_plan->length);
+      or_put_int (buf, (int) oos_plan->generation);
       *ptr_varvals = buf->ptr;
     }
   else if (dbvalue != NULL && db_value_is_null (dbvalue) != true)
@@ -28097,11 +28101,11 @@ heap_recdes_contains_oos (const RECDES * record)
 }
 
 int
-heap_recdes_get_oos_oids (const RECDES * recdes, OID_VECTOR & oos_oids)
+heap_recdes_get_oos_refs (const RECDES * recdes, OOS_REF_VECTOR & oos_refs)
 {
   using namespace oos_log;
 
-  oos_oids.clear ();
+  oos_refs.clear ();
 
   if (!heap_recdes_contains_oos (recdes))
     {
@@ -28143,9 +28147,9 @@ heap_recdes_get_oos_oids (const RECDES * recdes, OID_VECTOR & oos_oids)
 	{
 	  OID oid = OID_INITIALIZER;
 	  const char *oid_ptr = (char *) recdes->data + OR_VAR_OFFSET (recdes->data, index);
-	  if (oid_ptr + OR_OID_SIZE > (char *) recdes->data + recdes->length)
+	  if (oid_ptr + OR_OOS_INLINE_SIZE > (char *) recdes->data + recdes->length)
 	    {
-	      assert (false && "OID read would exceed record bounds");
+	      assert (false && "OOS inline stub read would exceed record bounds");
 	      return ER_FAILED;
 	    }
 	  OR_BUF buf;
@@ -28161,14 +28165,19 @@ heap_recdes_get_oos_oids (const RECDES * recdes, OID_VECTOR & oos_oids)
 	      assert (false && "OID read from OOS slot is null — corrupted record?");
 	      return ER_FAILED;
 	    }
-	  oos_debug ("there exists an OOS with OID %hd|%d|%hd at offset %d index %d", OID_AS_ARGS (&oid), offset,
-		     index);
-	  oos_oids.emplace_back (oid);
+	  /* The stub layout is [OID (8B) | full length (8B) | generation (4B)]; the generation is
+	   * the identity oos_delete verifies before reclaiming the chain (CBRD-26950). */
+	  oos_chain_ref ref;
+	  ref.head_oid = oid;
+	  ref.generation = (unsigned int) OR_GET_INT (oid_ptr + OR_OID_SIZE + OR_BIGINT_SIZE);
+	  oos_debug ("there exists an OOS with OID %hd|%d|%hd generation %u at offset %d index %d",
+		     OID_AS_ARGS (&oid), ref.generation, offset, index);
+	  oos_refs.push_back (ref);
 	}
 
       if (OR_IS_LAST_ELEMENT (offset))
 	{
-	  if (oos_oids.empty ())
+	  if (oos_refs.empty ())
 	    {
 	      /* heap_recdes_contains_oos() already confirmed OOS flag is set, so finding no OOS OIDs is inconsistent */
 	      assert (false && "heap_recdes_contains_oos() passed but no OOS OIDs found");
@@ -28177,15 +28186,15 @@ heap_recdes_get_oos_oids (const RECDES * recdes, OID_VECTOR & oos_oids)
 #if !defined (NDEBUG)
 	  {
 	    std::string line = "{";
-	    for (size_t i = 0; i < oos_oids.size (); ++i)
+	    for (size_t i = 0; i < oos_refs.size (); ++i)
 	      {
 		char oid_buf[32];
 		if (i > 0)
 		  line.append (", ");
-		line.append (oid_to_string (oid_buf, sizeof oid_buf, &oos_oids[i]));
+		line.append (oid_to_string (oid_buf, sizeof oid_buf, &oos_refs[i].head_oid));
 	      }
 	    line += '}';
-	    oos_debug ("Total %zu found. OOS OIDs: %s", oos_oids.size (), line.c_str ());
+	    oos_debug ("Total %zu found. OOS OIDs: %s", oos_refs.size (), line.c_str ());
 	  }
 #endif
 	  return NO_ERROR;
```

### 4. `src/storage/heap_file.h`

단계 6 — 추출기 시그니처: OOS_REF_VECTOR(전방선언 기반 alias) + heap_recdes_get_oos_refs.

```diff
diff --git a/src/storage/heap_file.h b/src/storage/heap_file.h
index ac4cd8a58..e56c03f5a 100644
--- a/src/storage/heap_file.h
+++ b/src/storage/heap_file.h
@@ -755,9 +755,12 @@ extern void heap_log_postpone_heap_append_pages (THREAD_ENTRY * thread_p, const
 
 // *INDENT-OFF*
 using OID_VECTOR = std::vector<OID>;
+struct oos_chain_ref;		// defined in oos_file.hpp
+using OOS_REF_VECTOR = std::vector<oos_chain_ref>;
 // *INDENT-ON*
 
-extern int heap_recdes_get_oos_oids (const RECDES * record, OID_VECTOR & oos_oids);
+/* Parses the record's OOS inline stubs into (head OID, generation) references (CBRD-26950). */
+extern int heap_recdes_get_oos_refs (const RECDES * record, OOS_REF_VECTOR & oos_refs);
 
 /* lob */
 extern int heap_rv_lob_remove_dir (THREAD_ENTRY * thread_p, LOG_RCV * rcv);
```

### 5. `src/storage/heap_oos.cpp`

단계 7 — parse_inline_ref bounds 20B, eager 삭제 경로 refs 전환 + generation 전달.

```diff
diff --git a/src/storage/heap_oos.cpp b/src/storage/heap_oos.cpp
index 890e11691..cfedf1476 100644
--- a/src/storage/heap_oos.cpp
+++ b/src/storage/heap_oos.cpp
@@ -418,7 +418,9 @@ heap_record_replace_oos_oids (THREAD_ENTRY *thread_p, HEAP_GET_CONTEXT *context)
 
 /*
  * heap_oos_parse_inline_ref () - Validate and parse the inline OOS reference of an OOS-marked
- *   variable attribute. Inline layout (M2+): [OID (8B) | full_length (8B bigint)].
+ *   variable attribute. Inline layout (M2+): [OID (8B) | full_length (8B bigint) | generation (4B)].
+ *   The generation is consumed by the delete paths through heap_recdes_get_oos_refs; readers only
+ *   need the OID and length parsed here.
  *
  *   return: NO_ERROR, or ER_HEAP_OOS_BAD_INLINE_HEADER when the reference is corrupted.
  *   recdes(in): heap record holding the attribute (only data/length are read)
@@ -439,8 +441,8 @@ heap_oos_parse_inline_ref (RECDES *recdes, const char *inline_ptr, OID *oos_oid,
   buf.ptr = (char *) inline_ptr;
   buf.endptr = recdes->data + recdes->length;
 
-  /* The OOS-marked variable region must start with [OID | bigint]. */
-  if (buf.endptr - buf.ptr < OR_OID_SIZE + OR_BIGINT_SIZE)
+  /* The OOS-marked variable region must hold a complete inline stub. */
+  if (buf.endptr - buf.ptr < OR_OOS_INLINE_SIZE)
     {
       er_set (ER_ERROR_SEVERITY, ARG_FILE_LINE, ER_HEAP_OOS_BAD_INLINE_HEADER, 3, OID_AS_ARGS (oos_oid));
       return ER_HEAP_OOS_BAD_INLINE_HEADER;
@@ -463,7 +465,7 @@ heap_oos_parse_inline_ref (RECDES *recdes, const char *inline_ptr, OID *oos_oid,
  * heap_oos_find_attr_inline_ref () - Find the OOS inline reference stored in a heap record for
  *   a requested variable attribute.
  *
- *   return: pointer to the 16-byte [OOS OID | full length] reference in the variable area, or
+ *   return: pointer to the [OOS OID | full length | generation] reference in the variable area, or
  *           NULL when this requested attribute has no OOS reference in this record. NULL also
  *           covers conditions the per-attribute read path skips or reports itself, including corrupt
  *           offset-size metadata.
@@ -702,37 +704,37 @@ int
 heap_oos_delete_unreferenced (THREAD_ENTRY *thread_p, HEAP_OPERATION_CONTEXT *context,
 			      const RECDES *old_recdes, const RECDES *new_recdes, const char *op_ctx)
 {
-  std::vector<OID> old_oos_oids;
-  std::vector<OID> new_oos_oids;
+  OOS_REF_VECTOR old_oos_refs;
+  OOS_REF_VECTOR new_oos_refs;
   VFID oos_vfid;
   int error_code;
 
-  error_code = heap_recdes_get_oos_oids (old_recdes, old_oos_oids);
+  error_code = heap_recdes_get_oos_refs (old_recdes, old_oos_refs);
   if (error_code != NO_ERROR)
     {
       ASSERT_ERROR ();
       er_log_debug (ARG_FILE_LINE,
-		    "SA_MODE eager OOS cleanup (%s): heap_recdes_get_oos_oids(old) failed"
+		    "SA_MODE eager OOS cleanup (%s): heap_recdes_get_oos_refs(old) failed"
 		    " (hfid=%d|%d, oid=%d|%d|%d, old_rec_len=%d).",
 		    op_ctx, VFID_AS_ARGS (&context->hfid.vfid),
 		    context->oid.volid, context->oid.pageid, context->oid.slotid, old_recdes->length);
       return error_code;
     }
-  if (old_oos_oids.empty ())
+  if (old_oos_refs.empty ())
     {
       return NO_ERROR;
     }
 
   if (new_recdes != NULL)
     {
-      /* heap_recdes_get_oos_oids returns NO_ERROR with an empty vector when the new record has no
+      /* heap_recdes_get_oos_refs returns NO_ERROR with an empty vector when the new record has no
        * OOS — no heap_recdes_contains_oos guard needed. */
-      error_code = heap_recdes_get_oos_oids (new_recdes, new_oos_oids);
+      error_code = heap_recdes_get_oos_refs (new_recdes, new_oos_refs);
       if (error_code != NO_ERROR)
 	{
 	  ASSERT_ERROR ();
 	  er_log_debug (ARG_FILE_LINE,
-			"SA_MODE eager OOS cleanup (%s): heap_recdes_get_oos_oids(new) failed"
+			"SA_MODE eager OOS cleanup (%s): heap_recdes_get_oos_refs(new) failed"
 			" (hfid=%d|%d, oid=%d|%d|%d, new_rec_len=%d).",
 			op_ctx, VFID_AS_ARGS (&context->hfid.vfid),
 			context->oid.volid, context->oid.pageid, context->oid.slotid, new_recdes->length);
@@ -751,22 +753,22 @@ heap_oos_delete_unreferenced (THREAD_ENTRY *thread_p, HEAP_OPERATION_CONTEXT *co
       return ER_FAILED;
     }
 
-  for (const OID &old_oid : old_oos_oids)
+  for (const oos_chain_ref &old_ref : old_oos_refs)
     {
-      if (oos_oid_in_vector (new_oos_oids, &old_oid))
+      if (oos_ref_in_vector (new_oos_refs, &old_ref.head_oid))
 	{
 	  /* Same physical OOS referenced by both old and new recdes; keep it. */
 	  continue;
 	}
-      error_code = oos_delete (thread_p, oos_vfid, old_oid);
+      error_code = oos_delete (thread_p, oos_vfid, old_ref.head_oid, old_ref.generation);
       if (error_code != NO_ERROR)
 	{
 	  ASSERT_ERROR ();
 	  er_log_debug (ARG_FILE_LINE,
 			"SA_MODE eager OOS cleanup (%s): oos_delete(oos_vfid=%d|%d, oid=%d|%d|%d) failed"
 			" (hfid=%d|%d, heap_oid=%d|%d|%d).",
-			op_ctx, VFID_AS_ARGS (&oos_vfid), old_oid.volid, old_oid.pageid, old_oid.slotid,
-			VFID_AS_ARGS (&context->hfid.vfid),
+			op_ctx, VFID_AS_ARGS (&oos_vfid), old_ref.head_oid.volid, old_ref.head_oid.pageid,
+			old_ref.head_oid.slotid, VFID_AS_ARGS (&context->hfid.vfid),
 			context->oid.volid, context->oid.pageid, context->oid.slotid);
 	  return error_code;
 	}
```

### 6. `src/storage/oos_file.cpp`

단계 3 — 본체. 발급(불변식 1·2), 데이터 페이지 초기화 분리(불변식 4), 용량(불변식 5), 검증형 삭제(불변식 6), redo MAX 재생(불변식 3), publication 쌍, 통계 slot-0 skip, oos_get_generation.

```diff
diff --git a/src/storage/oos_file.cpp b/src/storage/oos_file.cpp
index c533f32b7..d347c4c21 100644
--- a/src/storage/oos_file.cpp
+++ b/src/storage/oos_file.cpp
@@ -50,16 +50,22 @@
 
 static int
 oos_vpid_init_new (THREAD_ENTRY *thread_p, PAGE_PTR page, void *args);
+static int
+oos_vpid_init_new_data_page (THREAD_ENTRY *thread_p, PAGE_PTR page, void *args);
+
+static OOS_PAGE_HEADER *
+oos_get_page_header_ptr (THREAD_ENTRY *thread_p, PAGE_PTR page_ptr);
 
 static int
 oos_insert_within_page (THREAD_ENTRY *thread_p, const VFID &oos_vfid, oos_buffer src,
-			const OOS_RECORD_HEADER &header, OID &oid);
+			const OOS_RECORD_HEADER &header, OID &oid, unsigned int &generation_out);
 static int
 oos_insert_record_in_fixed_page (THREAD_ENTRY *thread_p, const VFID &oos_vfid, PAGE_PTR page_ptr,
-				 const VPID &vpid, oos_buffer src, const OOS_RECORD_HEADER &header, OID &oid);
+				 const VPID &vpid, oos_buffer src, const OOS_RECORD_HEADER &header, OID &oid,
+				 unsigned int &generation_out);
 static int
 oos_insert_across_pages (THREAD_ENTRY *thread_p, const VFID &oos_vfid, oos_buffer src,
-			 OID &oid);
+			 OID &oid, unsigned int &generation_out);
 static int
 oos_insert_single_page_batch (THREAD_ENTRY *thread_p, const VFID &oos_vfid,
 			      cubbase::span<oos_insert_request> requests,
@@ -84,12 +90,14 @@ oos_delete_chain (THREAD_ENTRY *thread_p, const VFID &oos_vfid, const OID &oid);
 
 STATIC_INLINE __attribute__ ((ALWAYS_INLINE))
 int oos_get_max_chunk_size_within_page ();
+STATIC_INLINE __attribute__ ((ALWAYS_INLINE))
+int oos_get_data_page_capacity ();
 
 static bool
 oos_needs_repl_tracking (THREAD_ENTRY *thread_p);
 
 static void
-oos_publish_oos_oid (THREAD_ENTRY *thread_p, const OID &oid);
+oos_publish_oos_oid (THREAD_ENTRY *thread_p, const OID &oid, unsigned int generation);
 
 static void
 oos_cleanup_insert_publication_state_on_error (THREAD_ENTRY *thread_p) noexcept;
@@ -1140,7 +1148,7 @@ oos_prepend_header (oos_buffer src, const OOS_RECORD_HEADER &oos_header, OOS_REC
 }
 
 static void
-oos_publish_oos_oid (THREAD_ENTRY *thread_p, const OID &oid)
+oos_publish_oos_oid (THREAD_ENTRY *thread_p, const OID &oid, unsigned int generation)
 {
 #if defined(CUBRID_UNIT_TEST_ENABLED)
   if (oos_Test_throw_bad_alloc_on_next_oid_publication.exchange (false, std::memory_order_relaxed))
@@ -1148,7 +1156,7 @@ oos_publish_oos_oid (THREAD_ENTRY *thread_p, const OID &oid)
       throw std::bad_alloc ();
     }
 #endif
-  thread_p->oos_oids.push_back (oid);
+  thread_p->oos_oids.push_back ({ oid, generation });
 }
 
 static void
@@ -1165,7 +1173,7 @@ oos_cleanup_insert_publication_state_on_error (THREAD_ENTRY *thread_p) noexcept
 }
 
 int
-oos_insert (THREAD_ENTRY *thread_p, const VFID &oos_vfid, oos_buffer src, OID &oid)
+oos_insert (THREAD_ENTRY *thread_p, const VFID &oos_vfid, oos_buffer src, OID &oid, unsigned int *generation_out)
 {
   oos_debug ("arguments: oos_vfid={fileid=%d, volid=%d}, src.size=%zu",
 	     oos_vfid.fileid, oos_vfid.volid, src.size ());
@@ -1189,16 +1197,18 @@ oos_insert (THREAD_ENTRY *thread_p, const VFID &oos_vfid, oos_buffer src, OID &o
   // review whether it is possible to generate the segment headers inside the oos_insert_within_page() and
   // oos_insert_across_pages() functions.
 
+  unsigned int generation = 0;
+
   try
     {
       if (src_len <= oos_get_max_chunk_size_within_page ())
 	{
-	  const OOS_RECORD_HEADER header{src_len, 0, OID_INITIALIZER};
-	  err = oos_insert_within_page (thread_p, oos_vfid, src, header, oid);
+	  const OOS_RECORD_HEADER header{src_len, 0, OID_INITIALIZER, 0};
+	  err = oos_insert_within_page (thread_p, oos_vfid, src, header, oid, generation);
 	}
       else
 	{
-	  err = oos_insert_across_pages (thread_p, oos_vfid, src, oid);
+	  err = oos_insert_across_pages (thread_p, oos_vfid, src, oid, generation);
 	}
 
       if (err != NO_ERROR)
@@ -1206,7 +1216,7 @@ oos_insert (THREAD_ENTRY *thread_p, const VFID &oos_vfid, oos_buffer src, OID &o
 	  return err;
 	}
 
-      oos_publish_oos_oid (thread_p, oid);
+      oos_publish_oos_oid (thread_p, oid, generation);
     }
   catch (const std::bad_alloc &)
     {
@@ -1216,7 +1226,11 @@ oos_insert (THREAD_ENTRY *thread_p, const VFID &oos_vfid, oos_buffer src, OID &o
     }
 
   cleanup_publication_on_error.release ();
-  oos_debug ("inserted to oid={vol=%d,page=%d,slot=%d}", OID_AS_ARGS (&oid));
+  if (generation_out != NULL)
+    {
+      *generation_out = generation;
+    }
+  oos_debug ("inserted to oid={vol=%d,page=%d,slot=%d} generation=%u", OID_AS_ARGS (&oid), generation);
   return NO_ERROR;
 }
 
@@ -1236,24 +1250,31 @@ oos_insert_single_page_batch (THREAD_ENTRY *thread_p, const VFID &oos_vfid,
     }
 
   PAGE_PTR page_ptr = auto_page_ptr.get ();
-  /* Freshly allocated pages and fully emptied reused pages both give the batch a clean page. */
-  const bool page_was_empty = (spage_number_of_records (page_ptr) == 0);
+  /* Freshly allocated pages and fully emptied reused pages both give the batch a clean page.
+   * Every data page permanently holds the slot-0 page header record, so "empty" means only
+   * that record remains (CBRD-26950). */
+  const bool page_was_empty = (spage_number_of_records (page_ptr) <= 1);
 
   for (std::size_t i = 0; i < requests.size (); i++)
     {
       oos_insert_request &request = requests[i];
       const int src_len = static_cast<int> (request.src.size ());
-      const OOS_RECORD_HEADER header{src_len, 0, OID_INITIALIZER};
+      const OOS_RECORD_HEADER header{src_len, 0, OID_INITIALIZER, 0};
       OID oid;
+      unsigned int generation = 0;
 
-      err = oos_insert_record_in_fixed_page (thread_p, oos_vfid, page_ptr, vpid, request.src, header, oid);
+      err = oos_insert_record_in_fixed_page (thread_p, oos_vfid, page_ptr, vpid, request.src, header, oid, generation);
       if (err != NO_ERROR)
 	{
 	  return err;
 	}
 
       *request.oid_out = oid;
-      oos_publish_oos_oid (thread_p, oid);
+      if (request.generation_out != NULL)
+	{
+	  *request.generation_out = generation;
+	}
+      oos_publish_oos_oid (thread_p, oid, generation);
     }
 
   int freespace_after = spage_max_space_for_new_record (thread_p, page_ptr);
@@ -1299,7 +1320,7 @@ oos_insert_many (THREAD_ENTRY *thread_p, const VFID &oos_vfid, cubbase::span<oos
   try
     {
       const int max_chunk_size = oos_get_max_chunk_size_within_page ();
-      const int page_capacity = DB_ALIGN_BELOW (spage_max_record_size (), OOS_ALIGNMENT);
+      const int page_capacity = oos_get_data_page_capacity ();
       const auto required_space = [] (const oos_insert_request &request)
       {
 	return DB_ALIGN (static_cast<int> (request.src.size ()) + OOS_RECORD_HEADER_SIZE, OOS_ALIGNMENT);
@@ -1325,11 +1346,16 @@ oos_insert_many (THREAD_ENTRY *thread_p, const VFID &oos_vfid, cubbase::span<oos
 	  if (requests[pos].src.size () > (std::size_t) max_chunk_size)
 	    {
 	      OID oid;
-	      err = oos_insert_across_pages (thread_p, oos_vfid, requests[pos].src, oid);
+	      unsigned int generation = 0;
+	      err = oos_insert_across_pages (thread_p, oos_vfid, requests[pos].src, oid, generation);
 	      if (err == NO_ERROR)
 		{
 		  *requests[pos].oid_out = oid;
-		  oos_publish_oos_oid (thread_p, oid);
+		  if (requests[pos].generation_out != NULL)
+		    {
+		      *requests[pos].generation_out = generation;
+		    }
+		  oos_publish_oos_oid (thread_p, oid, generation);
 		  pos++;
 		  publication_count++;
 		}
@@ -1400,7 +1426,8 @@ oos_insert_many (THREAD_ENTRY *thread_p, const VFID &oos_vfid, cubbase::span<oos
 //   auto-push in log_append_{undo,}redo_crumbs while this function runs.
 //
 static int
-oos_insert_across_pages (THREAD_ENTRY *thread_p, const VFID &oos_vfid, oos_buffer src, OID &oid)
+oos_insert_across_pages (THREAD_ENTRY *thread_p, const VFID &oos_vfid, oos_buffer src, OID &oid,
+			 unsigned int &generation_out)
 {
   int error_code = NO_ERROR;
   LOG_TDES *tdes = NULL;
@@ -1459,10 +1486,11 @@ oos_insert_across_pages (THREAD_ENTRY *thread_p, const VFID &oos_vfid, oos_buffe
       total_inserted_length += static_cast<int> (chunk.size ());
 
       // Keep total_data_length in each chunk so the log applier can validate all pieces before reassembly.
-      OOS_RECORD_HEADER header{total_data_length, i, next_chunk_oid};
+      OOS_RECORD_HEADER header{total_data_length, i, next_chunk_oid, 0};
 
       OID current_chunk_oid;
-      error_code = oos_insert_within_page (thread_p, oos_vfid, chunk, header, current_chunk_oid);
+      unsigned int chunk_generation = 0;
+      error_code = oos_insert_within_page (thread_p, oos_vfid, chunk, header, current_chunk_oid, chunk_generation);
       if (error_code != NO_ERROR)
 	{
 	  oos_error ("could not insert chunk index=%d of length %zu.", i, chunk.size ());
@@ -1479,6 +1507,7 @@ oos_insert_across_pages (THREAD_ENTRY *thread_p, const VFID &oos_vfid, oos_buffe
 	}
 
       next_chunk_oid = current_chunk_oid;
+      generation_out = chunk_generation;	/* the loop ends at i == 0, the head chunk */
     }
   assert (total_inserted_length == total_data_length);
 
@@ -1486,7 +1515,7 @@ oos_insert_across_pages (THREAD_ENTRY *thread_p, const VFID &oos_vfid, oos_buffe
     {
       tdes->oos_insert_lsa_queue.push (dummy_lsa);
       tdes->oos_insert_lsa_queue.push (tail_chunk_lsa);
-      thread_p->oos_oids.push_back (oid_Null_oid);
+      thread_p->oos_oids.push_back ({ oid_Null_oid, 0 });
     }
 
   // update the out parameter 'oid' to give access to the first slot
@@ -1497,10 +1526,26 @@ oos_insert_across_pages (THREAD_ENTRY *thread_p, const VFID &oos_vfid, oos_buffe
 
 static int
 oos_insert_record_in_fixed_page (THREAD_ENTRY *thread_p, const VFID &oos_vfid, PAGE_PTR page_ptr,
-				 const VPID &vpid, oos_buffer src, const OOS_RECORD_HEADER &header, OID &oid)
+				 const VPID &vpid, oos_buffer src, const OOS_RECORD_HEADER &header, OID &oid,
+				 unsigned int &generation_out)
 {
+  /* Issue the chunk's identity generation from the page counter (CBRD-26950). The W-latch we
+   * already hold makes issue + insert atomic. The counter itself is committed only after the
+   * insert succeeds, so a failed insert never burns the value; durability rides on the chunk's
+   * own RVOOS_INSERT record — oos_rv_redo_insert replays the counter from the stamped image. */
+  OOS_PAGE_HEADER *page_header = oos_get_page_header_ptr (thread_p, page_ptr);
+  if (page_header == NULL)
+    {
+      oos_error ("missing OOS page header record at vpid={vol=%d,page=%d}", vpid.volid, vpid.pageid);
+      er_set (ER_ERROR_SEVERITY, ARG_FILE_LINE, ER_HEAP_OOS_CORRUPTED_RECORD, 0);
+      return ER_HEAP_OOS_CORRUPTED_RECORD;
+    }
+
+  OOS_RECORD_HEADER stamped_header = header;
+  stamped_header.generation = page_header->generation_counter + 1;
+
   OOS_RECDES oos_recdes{};
-  int err = oos_prepend_header (src, header, oos_recdes);
+  int err = oos_prepend_header (src, stamped_header, oos_recdes);
   if (err != NO_ERROR)
     {
       oos_error ("oos_prepend_header failed");
@@ -1522,19 +1567,33 @@ oos_insert_record_in_fixed_page (THREAD_ENTRY *thread_p, const VFID &oos_vfid, P
     }
 
   assert (slotid != NULL_SLOTID);
+  assert (slotid != OOS_PAGE_HEADER_SLOT);
+
+  /* Commit the issued generation. Re-fetch the header pointer: spage_insert may have compacted
+   * the page and moved the header record. The counter update and the chunk insert are covered by
+   * the same RVOOS_INSERT log record appended below. */
+  page_header = oos_get_page_header_ptr (thread_p, page_ptr);
+  if (page_header == NULL)
+    {
+      assert (false);
+      er_set (ER_ERROR_SEVERITY, ARG_FILE_LINE, ER_HEAP_OOS_CORRUPTED_RECORD, 0);
+      return ER_HEAP_OOS_CORRUPTED_RECORD;
+    }
+  page_header->generation_counter = stamped_header.generation;
 
   oid.pageid = vpid.pageid;
   oid.slotid = slotid;
   oid.volid = vpid.volid;
 
   oos_log_insert_physical (thread_p, page_ptr, const_cast<VFID *> (&oos_vfid), &oid, &oos_recdes);
+  generation_out = stamped_header.generation;
   return NO_ERROR;
 }
 
 static int
 oos_insert_within_page (THREAD_ENTRY *thread_p, const VFID &oos_vfid, oos_buffer src,
 			const OOS_RECORD_HEADER &header,
-			OID &oid)
+			OID &oid, unsigned int &generation_out)
 {
   int err = NO_ERROR;
   VPID vpid;
@@ -1544,11 +1603,11 @@ oos_insert_within_page (THREAD_ENTRY *thread_p, const VFID &oos_vfid, oos_buffer
 
   int required_length = src_len + OOS_RECORD_HEADER_SIZE;
 
-  assert (required_length <= DB_ALIGN_BELOW (spage_max_record_size (), OOS_ALIGNMENT));
+  assert (required_length <= oos_get_data_page_capacity ());
 
   auto auto_page_ptr = oos_find_best_page (thread_p, oos_vfid, required_length, vpid);
   PAGE_PTR page_ptr = auto_page_ptr.get ();
-  err = oos_insert_record_in_fixed_page (thread_p, oos_vfid, page_ptr, vpid, src, header, oid);
+  err = oos_insert_record_in_fixed_page (thread_p, oos_vfid, page_ptr, vpid, src, header, oid, generation_out);
   if (err != NO_ERROR)
     {
       return err;
@@ -1884,7 +1943,7 @@ oos_file_alloc_new (THREAD_ENTRY *thread_p, const VFID &oos_vfid,
   PAGE_TYPE page_type = PAGE_OOS;
 
   log_sysop_start (thread_p);
-  err = file_alloc (thread_p, &oos_vfid, oos_vpid_init_new, &page_type, &vpid_out, nullptr);
+  err = file_alloc (thread_p, &oos_vfid, oos_vpid_init_new_data_page, &page_type, &vpid_out, nullptr);
   if (err != NO_ERROR)
     {
       oos_error ("file_alloc failed");
@@ -2094,6 +2153,66 @@ oos_vpid_init_new (THREAD_ENTRY *thread_p, PAGE_PTR page, void *args)
   return err;
 }
 
+/*
+ * oos_vpid_init_new_data_page () - FILE_INIT_PAGE_FUNC for OOS data pages. On top of the plain
+ *   slotted-page initialization it plants the slot-0 OOS_PAGE_HEADER record that carries the
+ *   page's generation counter (CBRD-26950). The whole init is logged as one RVOOS_NEWPAGE record
+ *   so recovery redo rebuilds page type, slotted-page header, and the header record together.
+ *   The file's sticky first page keeps using oos_vpid_init_new: it stores OOS_HDR_STATS at
+ *   slot 0 and never holds chunk records.
+ */
+static int
+oos_vpid_init_new_data_page (THREAD_ENTRY *thread_p, PAGE_PTR page, void *args)
+{
+  PAGE_TYPE ptype = * (PAGE_TYPE *) args;
+  LOG_DATA_ADDR addr = LOG_DATA_ADDR_INITIALIZER;
+  OOS_PAGE_HEADER page_header;
+  RECDES recdes;
+  PGSLOTID slotid;
+
+  addr.pgptr = page;
+  pgbuf_set_page_ptype (thread_p, page, ptype);
+
+  spage_initialize (thread_p, page, ANCHORED, OOS_ALIGNMENT, false);
+
+  page_header.generation_counter = 0;
+
+  recdes.area_size = recdes.length = OOS_PAGE_HEADER_SIZE;
+  recdes.type = REC_HOME;
+  recdes.data = (char *) &page_header;
+
+  int sp_status = spage_insert (thread_p, page, &recdes, &slotid);
+  if (sp_status != SP_SUCCESS || slotid != OOS_PAGE_HEADER_SLOT)
+    {
+      assert (false);
+      oos_error ("could not insert the OOS page header record (status %d, slotid %d)", sp_status, (int) slotid);
+      er_set (ER_FATAL_ERROR_SEVERITY, ARG_FILE_LINE, ER_GENERIC_ERROR, 0);
+      return ER_FAILED;
+    }
+
+  log_append_undoredo_data (thread_p, RVOOS_NEWPAGE, &addr, 0, recdes.length, NULL, recdes.data);
+  pgbuf_set_dirty (thread_p, page, DONT_FREE);
+  return NO_ERROR;
+}
+
+/*
+ * oos_get_page_header_ptr () - PEEK the slot-0 OOS_PAGE_HEADER record of a fixed OOS data page.
+ *   Returns NULL when the record is missing or too short (corruption). The pointer aliases page
+ *   memory: it is invalidated by any slotted-page operation that can compact the page.
+ */
+static OOS_PAGE_HEADER *
+oos_get_page_header_ptr (THREAD_ENTRY *thread_p, PAGE_PTR page_ptr)
+{
+  RECDES recdes;
+  if (spage_get_record (thread_p, page_ptr, OOS_PAGE_HEADER_SLOT, &recdes, PEEK) != S_SUCCESS
+      || recdes.length < OOS_PAGE_HEADER_SIZE)
+    {
+      assert (false);
+      return NULL;
+    }
+  return (OOS_PAGE_HEADER *) recdes.data;
+}
+
 /*
  * oos_log_insert_physical () - add logging information for physical insertion
  *   thread_p(in): thread entry
@@ -2158,6 +2277,16 @@ oos_delete_chain (THREAD_ENTRY *thread_p, const VFID &oos_vfid, const OID &oid)
     {
       VPID vpid = {current_oid.pageid, current_oid.volid};
 
+      /* The page header record is not a chunk; a chain link pointing at it is corruption. */
+      if (current_oid.slotid == OOS_PAGE_HEADER_SLOT)
+	{
+	  assert_release (false);
+	  oos_error ("OOS chain link points at the page header slot: oid={vol=%d,page=%d,slot=%d}",
+		     OID_AS_ARGS (&current_oid));
+	  er_set (ER_ERROR_SEVERITY, ARG_FILE_LINE, ER_HEAP_OOS_CORRUPTED_RECORD, 0);
+	  return ER_HEAP_OOS_CORRUPTED_RECORD;
+	}
+
       PAGE_PTR page_ptr = pgbuf_fix (thread_p, &vpid, OLD_PAGE, PGBUF_LATCH_WRITE, PGBUF_UNCONDITIONAL_LATCH);
       if (page_ptr == nullptr)
 	{
@@ -2219,23 +2348,23 @@ oos_delete_chain (THREAD_ENTRY *thread_p, const VFID &oos_vfid, const OID &oid)
 }
 
 /*
- * oos_chunk_exists () - Probe whether the OOS chunk at oid still exists. Read-only companion to
- *   oos_delete for idempotent callers (e.g. vacuum forward-walk block retry, which must skip OIDs
- *   whose chunks a previously committed sysop already removed instead of tripping the
- *   S_DOESNT_EXIST hard error inside oos_delete_chain).
+ * oos_chain_head_matches () - Probe whether the slot at oid still holds the chunk this reference
+ *   was created for, by comparing the stored generation with the caller's expected one
+ *   (CBRD-26950). Pre-delete companion of oos_delete.
  *
- *   "Already gone" is narrowly defined:
+ *   "Not a match" (out_matches == false with NO_ERROR) covers exactly:
  *     - pgbuf_fix_if_not_deallocated returns NO_ERROR with page_ptr==NULL (page deallocated), OR
- *     - spage_get_record returns S_DOESNT_EXIST (slot removed but page still alive).
+ *     - spage_get_record returns S_DOESNT_EXIST (slot removed but page still alive), OR
+ *     - the slot is occupied but its stored generation differs (slot reused by a younger chain).
  *
- *   Any other failure (real pgbuf_fix error from I/O / interrupt / buffer corruption, or
- *   spage_get_record returning S_ERROR) is propagated as the probe's return value; callers must
- *   treat that as a failure rather than a successful "gone".
+ *   Any other failure (real pgbuf_fix error from I/O / interrupt / buffer corruption, a record
+ *   too short to hold a chunk header, or spage_get_record returning S_ERROR) is propagated as
+ *   the probe's return value; callers must treat that as a failure rather than a "no match".
  */
-int
-oos_chunk_exists (THREAD_ENTRY *thread_p, const OID &oid, bool *out_exists)
+static int
+oos_chain_head_matches (THREAD_ENTRY *thread_p, const OID &oid, unsigned int expected_generation, bool *out_matches)
 {
-  *out_exists = false;
+  *out_matches = false;
 
   VPID vpid;
   vpid.volid = oid.volid;
@@ -2257,13 +2386,33 @@ oos_chunk_exists (THREAD_ENTRY *thread_p, const OID &oid, bool *out_exists)
 
   RECDES probe = RECDES_INITIALIZER;
   SCAN_CODE code = spage_get_record (thread_p, page_ptr, oid.slotid, &probe, PEEK);
-  pgbuf_unfix_and_init (thread_p, page_ptr);
 
   if (code == S_SUCCESS)
     {
-      *out_exists = true;
+      if (probe.length < OOS_RECORD_HEADER_SIZE)
+	{
+	  pgbuf_unfix_and_init (thread_p, page_ptr);
+	  assert_release (false);
+	  oos_error ("OOS record at oid={vol=%d,page=%d,slot=%d} has invalid length %d",
+		     OID_AS_ARGS (&oid), probe.length);
+	  er_set (ER_ERROR_SEVERITY, ARG_FILE_LINE, ER_HEAP_OOS_CORRUPTED_RECORD, 0);
+	  return ER_HEAP_OOS_CORRUPTED_RECORD;
+	}
+
+      OOS_RECORD_HEADER header;
+      std::memcpy (&header, probe.data, OOS_RECORD_HEADER_SIZE);
+      pgbuf_unfix_and_init (thread_p, page_ptr);
+
+      *out_matches = (header.generation == expected_generation);
+      if (!*out_matches)
+	{
+	  oos_debug ("slot reused at oid={vol=%d,page=%d,slot=%d}: expected generation %u, stored %u",
+		     OID_AS_ARGS (&oid), expected_generation, header.generation);
+	}
       return NO_ERROR;
     }
+
+  pgbuf_unfix_and_init (thread_p, page_ptr);
   if (code == S_DOESNT_EXIST)
     {
       /* Slot already removed; chunk is gone. */
@@ -2275,14 +2424,22 @@ oos_chunk_exists (THREAD_ENTRY *thread_p, const OID &oid, bool *out_exists)
 }
 
 /*
- * oos_delete () - delete an OOS record (single-chunk or multi-chunk chain)
+ * oos_delete () - delete an OOS record (single-chunk or multi-chunk chain) after verifying that
+ *   the head chunk is still the one the caller's reference was created for
  *
  *   return: NO_ERROR or error code
  *   thread_p(in): thread entry
  *   oos_vfid(in): OOS file identifier
  *   oid(in): head OID of the OOS record
+ *   expected_generation(in): the generation stored in the caller's OOS inline stub
+ *
+ * NOTE: The delete happens only when the head chunk's stored generation equals
+ *       expected_generation. A gone chunk (a block retry re-deleting what an earlier committed
+ *       sysop already reclaimed) and a generation mismatch (the slot was freed and reused by a
+ *       live chain) are both successful no-ops: OOS OIDs are physical addresses, so without this
+ *       identity check a retried delete would destroy the reusing chain's data (CBRD-26950).
  *
- * NOTE: No sysop is used. Each chunk deletion is logged individually
+ *       No sysop is used. Each chunk deletion is logged individually
  *       (RVOOS_DELETE with full record as undo data).
  *
  *       Why this is safe:
@@ -2305,22 +2462,110 @@ oos_chunk_exists (THREAD_ENTRY *thread_p, const OID &oid, bool *out_exists)
  *       by vacuum after the transaction commits.
  */
 int
-oos_delete (THREAD_ENTRY *thread_p, const VFID &oos_vfid, const OID &oid)
+oos_delete (THREAD_ENTRY *thread_p, const VFID &oos_vfid, const OID &oid, unsigned int expected_generation)
 {
-  oos_debug ("arguments: oid={vol=%d,page=%d,slot=%d}", OID_AS_ARGS (&oid));
+  oos_debug ("arguments: oid={vol=%d,page=%d,slot=%d}, expected_generation=%u",
+	     OID_AS_ARGS (&oid), expected_generation);
+
+  bool matches = false;
+  int error_code = oos_chain_head_matches (thread_p, oid, expected_generation, &matches);
+  if (error_code != NO_ERROR)
+    {
+      return error_code;
+    }
+  if (!matches)
+    {
+      /* Already reclaimed, or the slot now belongs to a younger chain. Either way the chain this
+       * reference described is no longer there; skipping is the correct outcome. */
+      oos_debug ("delete no-op at oid={vol=%d,page=%d,slot=%d}: chain gone or slot reused"
+		 " (expected generation %u)", OID_AS_ARGS (&oid), expected_generation);
+      return NO_ERROR;
+    }
 
   return oos_delete_chain (thread_p, oos_vfid, oid);
 }
 
-// TODO: since this value never changes, we can make it a constant or static variable,
-// and make it initialized only once in something like oos_boot().
+/*
+ * oos_get_generation () - Read the identity generation stamped in the chunk at oid.
+ *
+ *   return: NO_ERROR or error code (missing page/slot is an error here — the caller asks about a
+ *           chunk it just inserted or otherwise knows to exist)
+ *   thread_p(in): thread entry
+ *   oid(in): OID of the chunk
+ *   generation_out(out): the chunk's stored generation
+ *
+ * NOTE: For tests and diagnostics. Not a pre-delete probe — oos_delete verifies identity itself,
+ *       and production callers obtain the expected generation from the owning stub or from the
+ *       insert-time publication, never by reading it back from storage.
+ */
+int
+oos_get_generation (THREAD_ENTRY *thread_p, const OID &oid, unsigned int *generation_out)
+{
+  assert (generation_out != NULL);
+  *generation_out = 0;
+
+  VPID vpid;
+  vpid.volid = oid.volid;
+  vpid.pageid = oid.pageid;
+
+  PAGE_PTR page_ptr = pgbuf_fix (thread_p, &vpid, OLD_PAGE, PGBUF_LATCH_READ, PGBUF_UNCONDITIONAL_LATCH);
+  if (page_ptr == nullptr)
+    {
+      oos_error ("oos_get_generation: pgbuf_fix failed at oid={vol=%d,page=%d,slot=%d}", OID_AS_ARGS (&oid));
+      assert_release_error (er_errid () != NO_ERROR);
+      return er_errid ();
+    }
+  scope_exit page_unfixer ([&]()
+  {
+    pgbuf_unfix_and_init_after_check (thread_p, page_ptr);
+  });
+
+  OOS_RECDES oos_recdes;
+  SCAN_CODE code = spage_get_record (thread_p, page_ptr, oid.slotid, &oos_recdes, PEEK);
+  if (code != S_SUCCESS)
+    {
+      oos_error ("oos_get_generation: spage_get_record failed (code=%d) at oid={vol=%d,page=%d,slot=%d}",
+		 (int) code, OID_AS_ARGS (&oid));
+      if (er_errid () == NO_ERROR)
+	{
+	  er_set (ER_ERROR_SEVERITY, ARG_FILE_LINE, ER_GENERIC_ERROR, 0);
+	}
+      return er_errid ();
+    }
+
+  if (oos_recdes.length < OOS_RECORD_HEADER_SIZE)
+    {
+      oos_error ("oos_get_generation: OOS record smaller than header (len=%d) at oid={vol=%d,page=%d,slot=%d}",
+		 oos_recdes.length, OID_AS_ARGS (&oid));
+      er_set (ER_ERROR_SEVERITY, ARG_FILE_LINE, ER_HEAP_OOS_CORRUPTED_RECORD, 0);
+      return ER_HEAP_OOS_CORRUPTED_RECORD;
+    }
+
+  OOS_RECORD_HEADER header;
+  std::memcpy (&header, oos_recdes.data, OOS_RECORD_HEADER_SIZE);
+  *generation_out = header.generation;
+
+  return NO_ERROR;
+}
+
+// TODO: since these values never change, we can make them constants or static variables,
+// and make them initialized only once in something like oos_boot().
+
+/* Bytes an OOS data page can spend on chunk records: the raw slotted-page capacity minus the
+ * permanent slot-0 OOS_PAGE_HEADER record (aligned record body + its slot entry, CBRD-26950). */
 STATIC_INLINE __attribute__ ((ALWAYS_INLINE)) int
-oos_get_max_chunk_size_within_page ()
+oos_get_data_page_capacity ()
 {
+  const int page_header_footprint = DB_ALIGN (OOS_PAGE_HEADER_SIZE, OOS_ALIGNMENT) + (int) SPAGE_SLOT_SIZE;
+
   // TODO: fix bug for spage_max_record_size returning incorrect size, which is out of scope for OOS project.
-  const int actual_upper_limit = DB_ALIGN_BELOW (spage_max_record_size (), OOS_ALIGNMENT);
+  return DB_ALIGN_BELOW (spage_max_record_size () - page_header_footprint, OOS_ALIGNMENT);
+}
 
-  return actual_upper_limit - (int)sizeof (OOS_RECORD_HEADER);
+STATIC_INLINE __attribute__ ((ALWAYS_INLINE)) int
+oos_get_max_chunk_size_within_page ()
+{
+  return oos_get_data_page_capacity () - (int) sizeof (OOS_RECORD_HEADER);
 }
 
 /*
@@ -2392,6 +2637,64 @@ oos_rv_redo_insert (THREAD_ENTRY *thread_p, LOG_RCV *rcv)
       return er_errid ();
     }
 
+  if (slotid != OOS_PAGE_HEADER_SLOT && recdes.length >= OOS_RECORD_HEADER_SIZE)
+    {
+      /* A chunk insert also advanced the page's generation counter at runtime; replay it from the
+       * generation stamped in the chunk image (CBRD-26950). This function is both the redo of
+       * RVOOS_INSERT and the undo of RVOOS_DELETE (a rollback restoring an old chunk), so the
+       * counter must only move forward — regressing it could re-issue a generation that a stale
+       * stub still expects. Slot-0 inserts never reach this branch: on the file header page that
+       * is the OOS_HDR_STATS record, on data pages the OOS_PAGE_HEADER record. */
+      OOS_RECORD_HEADER chunk_header;
+      std::memcpy (&chunk_header, recdes.data, OOS_RECORD_HEADER_SIZE);
+
+      RECDES hdr_recdes = RECDES_INITIALIZER;
+      if (spage_get_record (thread_p, rcv->pgptr, OOS_PAGE_HEADER_SLOT, &hdr_recdes, PEEK) == S_SUCCESS
+	  && hdr_recdes.length >= OOS_PAGE_HEADER_SIZE)
+	{
+	  OOS_PAGE_HEADER *page_header = (OOS_PAGE_HEADER *) hdr_recdes.data;
+	  if (page_header->generation_counter < chunk_header.generation)
+	    {
+	      page_header->generation_counter = chunk_header.generation;
+	    }
+	}
+      else
+	{
+	  assert (false);
+	}
+    }
+
+  return NO_ERROR;
+}
+
+/*
+ * oos_rv_redo_newpage () - Redo the initialization of an OOS data page: page type, slotted-page
+ *   header, and the slot-0 OOS_PAGE_HEADER record whose image is the redo data (CBRD-26950).
+ */
+int
+oos_rv_redo_newpage (THREAD_ENTRY *thread_p, LOG_RCV *rcv)
+{
+  RECDES recdes;
+  PGSLOTID slotid;
+  int sp_success;
+
+  (void) pgbuf_set_page_ptype (thread_p, rcv->pgptr, PAGE_OOS);
+
+  spage_initialize (thread_p, rcv->pgptr, ANCHORED, OOS_ALIGNMENT, false);
+
+  recdes.area_size = recdes.length = rcv->length;
+  recdes.type = REC_HOME;
+  recdes.data = (char *) rcv->data;
+  sp_success = spage_insert (thread_p, rcv->pgptr, &recdes, &slotid);
+  pgbuf_set_dirty (thread_p, rcv->pgptr, DONT_FREE);
+
+  if (sp_success != SP_SUCCESS || slotid != OOS_PAGE_HEADER_SLOT)
+    {
+      er_set (ER_FATAL_ERROR_SEVERITY, ARG_FILE_LINE, ER_GENERIC_ERROR, 0);
+      assert (false);
+      return er_errid ();
+    }
+
   return NO_ERROR;
 }
 
@@ -2552,13 +2855,17 @@ oos_get_stats_by_vfid (THREAD_ENTRY *thread_p, const VFID &oos_vfid, OOS_STATS_I
 	  continue;		/* page busy — accept a slight undercount */
 	}
 
-      /* Walk slots explicitly: spage_collect_statistics skips slot 0 (a heap-page
-       * assumption where slot 0 holds the header record), but OOS data pages keep
-       * records starting at slot 0, so it undercounts by one record per page. */
+      /* Walk slots explicitly, skipping the slot-0 OOS_PAGE_HEADER record: since CBRD-26950
+       * every data page keeps its generation-counter header there and chunk records occupy the
+       * slots above it (the same convention spage_collect_statistics assumes for heap pages). */
       PGSLOTID slotid = -1;
       RECDES slot_recdes;
       while (spage_next_record (page_ptr, &slotid, &slot_recdes, PEEK) == S_SUCCESS)
 	{
+	  if (slotid == OOS_PAGE_HEADER_SLOT)
+	    {
+	      continue;
+	    }
 	  total_recs++;
 	  total_sumlen += slot_recdes.length;
 	}
```

### 7. `src/storage/oos_file.hpp`

단계 2 — 온디스크 구조체(청크 헤더 +generation, OOS_PAGE_HEADER 신설)와 공개 API(oos_insert 의 generation_out, 검증형 oos_delete, oos_get_generation, oos_rv_redo_newpage). oos_chunk_exists 선언 삭제. recovery.h include 는 LOG_RCV 자급자족용.

```diff
diff --git a/src/storage/oos_file.hpp b/src/storage/oos_file.hpp
index 93b57957f..cc672faeb 100644
--- a/src/storage/oos_file.hpp
+++ b/src/storage/oos_file.hpp
@@ -19,6 +19,7 @@
 #ifndef _OOS_FILE_HPP_
 #define _OOS_FILE_HPP_
 
+#include "recovery.h"		// LOG_RCV
 #include "span.hpp"
 #include "storage_common.h"
 #include "thread_compat.hpp"
@@ -28,11 +29,36 @@ struct oos_record_header
   int total_data_length;	/* total length of user data across all chunks (excluding OOS headers) */
   int chunk_index;		/* 0-based index of this chunk in the chain */
   OID next_chunk_oid;		/* OID of next chunk, or NULL OID if this is the last */
+  unsigned int generation;	/* identity stamp issued from the page's generation counter at insert time;
+				 * oos_delete compares it with the caller's expected value so a reused
+				 * (volid|pageid|slotid) is never mistaken for the chunk a stale reference
+				 * was created for (CBRD-26950) */
 };
 using OOS_RECORD_HEADER = struct oos_record_header;
 
 #define OOS_RECORD_HEADER_SIZE ((int) sizeof (OOS_RECORD_HEADER))
 
+/* Per-page header record stored at slot OOS_PAGE_HEADER_SLOT of every OOS data page. (The file's
+ * sticky first page keeps OOS_HDR_STATS at slot 0 instead and never holds chunk records.)
+ * generation_counter advances by one for every chunk record inserted into the page; the issued
+ * value stamps both the chunk header and the owning heap record's OOS inline stub (CBRD-26950). */
+struct oos_page_header
+{
+  unsigned int generation_counter;
+};
+using OOS_PAGE_HEADER = struct oos_page_header;
+
+#define OOS_PAGE_HEADER_SIZE ((int) sizeof (OOS_PAGE_HEADER))
+#define OOS_PAGE_HEADER_SLOT 0
+
+/* Reference to one OOS value chain: the head chunk's OID plus the generation the chain was created
+ * with. This is the parsed form of a heap record's OOS inline stub (heap_recdes_get_oos_refs). */
+struct oos_chain_ref
+{
+  OID head_oid;
+  unsigned int generation;
+};
+
 /* Alias for a RECDES whose first OOS_RECORD_HEADER_SIZE bytes are the OOS header.
  * Documentation only — no compile-time distinction from RECDES. */
 using OOS_RECDES = RECDES;
@@ -46,6 +72,7 @@ struct oos_insert_request
 {
   oos_buffer src;
   OID *oid_out;
+  unsigned int *generation_out;	/* optional (may be NULL): receives the head chunk's generation */
 };
 
 struct oos_read_request
@@ -100,22 +127,29 @@ extern int oos_create_file (THREAD_ENTRY *thread_p, VFID &oos_vfid);
 #endif /* CUBRID_UNIT_TEST_ENABLED */
 extern int oos_remove_file (THREAD_ENTRY *thread_p, const VFID &oos_vfid);
 extern int oos_remove_page (THREAD_ENTRY *thread_p, const VFID &oos_vfid, const VPID &vpid);
-/* Inserts src.size() bytes; on multi-page payloads, oid is the head-chunk OID. */
-extern int oos_insert (THREAD_ENTRY *thread_p, const VFID &oos_vfid, oos_buffer src, OID &oid);
-/* Inserts requests in logical order; each request receives its head OOS OID. */
+/* Inserts src.size() bytes; on multi-page payloads, oid is the head-chunk OID. generation_out
+ * (optional) receives the head chunk's identity generation for the caller's inline stub. */
+extern int oos_insert (THREAD_ENTRY *thread_p, const VFID &oos_vfid, oos_buffer src, OID &oid,
+		       unsigned int *generation_out = NULL);
+/* Inserts requests in logical order; each request receives its head OOS OID (and generation). */
 extern int oos_insert_many (THREAD_ENTRY *thread_p, const VFID &oos_vfid, cubbase::span<oos_insert_request> requests);
 /* Reads exactly dest.size() bytes; the caller obtains the length from the
  * heap record's inline 8B field (or oos_get_length in tests) and sizes dest. */
 extern int oos_read (THREAD_ENTRY *thread_p, const OID &oid, oos_buffer dest);
 extern int oos_read_many (THREAD_ENTRY *thread_p, cubbase::span<oos_read_request> requests);
-extern int oos_delete (THREAD_ENTRY *thread_p, const VFID &oos_vfid, const OID &oid);
-/* Idempotency probe: *out_exists is true iff the chunk's slot is still present. A deallocated page
- * or a removed slot both report "gone" with NO_ERROR; any other failure is propagated. */
-extern int oos_chunk_exists (THREAD_ENTRY *thread_p, const OID &oid, bool *out_exists);
+/* Deletes the chain at oid only when the head chunk's stored generation equals
+ * expected_generation. A gone chunk (already-reclaimed retry) and a generation mismatch (slot
+ * reused by a younger chain) are both successful no-ops (CBRD-26950). */
+extern int oos_delete (THREAD_ENTRY *thread_p, const VFID &oos_vfid, const OID &oid,
+		       unsigned int expected_generation);
+/* Reads the generation stamped in the chunk at oid. For tests and diagnostics — NOT a pre-delete
+ * probe; oos_delete verifies identity itself. */
+extern int oos_get_generation (THREAD_ENTRY *thread_p, const OID &oid, unsigned int *generation_out);
 extern int oos_get_length (THREAD_ENTRY *thread_p, const OID &oid);
 
 extern int oos_rv_redo_delete (THREAD_ENTRY *thread_p, LOG_RCV *rcv);
 extern int oos_rv_redo_insert (THREAD_ENTRY *thread_p, LOG_RCV *rcv);
+extern int oos_rv_redo_newpage (THREAD_ENTRY *thread_p, LOG_RCV *rcv);
 
 typedef enum
 {
```

### 8. `src/storage/oos_util.cpp`

단계 7 — head OID 기준 선형 탐색 헬퍼.

```diff
diff --git a/src/storage/oos_util.cpp b/src/storage/oos_util.cpp
index 138bcbea3..c6fa269e9 100644
--- a/src/storage/oos_util.cpp
+++ b/src/storage/oos_util.cpp
@@ -44,6 +44,23 @@ oos_oid_in_vector (const std::vector<OID> &oids, const OID *oid)
   return false;
 }
 
+/*
+ * oos_ref_in_vector () - True if oid appears as a head OID in refs (linear scan; vector is small
+ *   by design).
+ */
+bool
+oos_ref_in_vector (const std::vector<oos_chain_ref> &refs, const OID *oid)
+{
+  for (const oos_chain_ref &candidate : refs)
+    {
+      if (OID_EQ (&candidate.head_oid, oid))
+	{
+	  return true;
+	}
+    }
+  return false;
+}
+
 #if !defined (NDEBUG)
 /*
  * heap_recdes_compute_oos_flag_debug - debug-only audit of OR_RECORD_FLAG_HAS_OOS
```

### 9. `src/storage/oos_util.hpp`

단계 7 — oos_ref_in_vector 선언. oos_file.hpp include 추가(이로 인해 oos_file.hpp 의 recovery.h 자급자족이 필요해졌다).

```diff
diff --git a/src/storage/oos_util.hpp b/src/storage/oos_util.hpp
index b5d9965a4..b5603eb68 100644
--- a/src/storage/oos_util.hpp
+++ b/src/storage/oos_util.hpp
@@ -26,11 +26,13 @@
 #define _OOS_UTIL_HPP_
 
 #include "dbtype_def.h"
+#include "oos_file.hpp"		// oos_chain_ref
 #include "storage_common.h"	// RECDES
 
 #include <vector>
 
 extern bool oos_oid_in_vector (const std::vector<OID> &oids, const OID *oid);
+extern bool oos_ref_in_vector (const std::vector<oos_chain_ref> &refs, const OID *oid);
 
 #if !defined (NDEBUG)
 // DO NOT REMOVE THIS. Debug-only VOT auditor; it has no release-build caller, so
```

### 10. `src/thread/thread_entry.hpp`

단계 5 — publication 을 (OID, generation) 쌍으로. NULL-OID 요소는 멀티청크 복제 경계 마커.

```diff
diff --git a/src/thread/thread_entry.hpp b/src/thread/thread_entry.hpp
index 7a94f72b8..c52231103 100644
--- a/src/thread/thread_entry.hpp
+++ b/src/thread/thread_entry.hpp
@@ -319,7 +319,16 @@ namespace cubthread
 
       bool m_skip_end_resource_tracks_in_recycle;
 
-      std::vector<OID> oos_oids;
+      /* Published OOS value-chain references of the current logical heap-record OOS insert:
+       * head chunk OID + its identity generation (CBRD-26950). The generation rides along so the
+       * HA applier's stub fixup can rewrite both stub fields without touching storage. A NULL-OID
+       * entry is the multi-chunk replication boundary marker. */
+      struct oos_published_ref
+      {
+	OID oid;
+	unsigned int generation;
+      };
+      std::vector<oos_published_ref> oos_oids;
 
 
       bool m_is_private_lru_enabled;
```

### 11. `src/transaction/locator_sr.c`

단계 9 — repl 루프 .oid 접근, fixup 이 publish 쌍으로 OID+generation 재기록(스토리지 재조회 없음).

```diff
diff --git a/src/transaction/locator_sr.c b/src/transaction/locator_sr.c
index eb7797d38..cf3d35906 100644
--- a/src/transaction/locator_sr.c
+++ b/src/transaction/locator_sr.c
@@ -8153,10 +8153,10 @@ locator_add_or_remove_index_internal (THREAD_ENTRY * thread_p, RECDES * recdes,
 	      for (int i = 0; i < (int) thread_p->oos_oids.size (); i++)
 		{
 		  LOG_RCVINDEX oos_repl_rcvindex =
-		    OID_ISNULL (&thread_p->oos_oids[i]) ? RVREPL_DUMMY_OOS_RECORD : RVREPL_OOS_INSERT;
+		    OID_ISNULL (&thread_p->oos_oids[i].oid) ? RVREPL_DUMMY_OOS_RECORD : RVREPL_OOS_INSERT;
 		  error_code = repl_log_insert (thread_p,
 						class_oid,
-						&thread_p->oos_oids[i],
+						&thread_p->oos_oids[i].oid,
 						LOG_REPLICATION_DATA,
 						oos_repl_rcvindex, key_dbvalue, REPL_INFO_TYPE_RBR_NORMAL);
 		  if (error_code != NO_ERROR)
@@ -8956,10 +8956,10 @@ locator_update_index (THREAD_ENTRY * thread_p, RECDES * new_recdes, RECDES * old
 	  for (int i = 0; i < (int) thread_p->oos_oids.size (); i++)
 	    {
 	      LOG_RCVINDEX oos_repl_rcvindex =
-		OID_ISNULL (&thread_p->oos_oids[i]) ? RVREPL_DUMMY_OOS_RECORD : RVREPL_OOS_INSERT;
+		OID_ISNULL (&thread_p->oos_oids[i].oid) ? RVREPL_DUMMY_OOS_RECORD : RVREPL_OOS_INSERT;
 	      error_code =
-		repl_log_insert (thread_p, class_oid, &thread_p->oos_oids[i], LOG_REPLICATION_DATA, oos_repl_rcvindex,
-				 new_key, REPL_INFO_TYPE_RBR_NORMAL);
+		repl_log_insert (thread_p, class_oid, &thread_p->oos_oids[i].oid, LOG_REPLICATION_DATA,
+				 oos_repl_rcvindex, new_key, REPL_INFO_TYPE_RBR_NORMAL);
 	      if (error_code != NO_ERROR)
 		{
 		  assert (er_errid () != NO_ERROR);
@@ -14239,7 +14239,7 @@ locator_fixup_oos_oids_in_recdes (THREAD_ENTRY * thread_p, const OID * class_oid
 	  goto end;
 	}
 
-      oos_oid = thread_p->oos_oids[oos_oid_count];
+      oos_oid = thread_p->oos_oids[oos_oid_count].oid;
       oid_ptr = (char *) recdes->data + OR_VAR_OFFSET (recdes->data, attrepr->location);
 
       buf.ptr = oid_ptr;
@@ -14247,6 +14247,12 @@ locator_fixup_oos_oids_in_recdes (THREAD_ENTRY * thread_p, const OID * class_oid
 
       or_put_oid (&buf, &oos_oid);
 
+      /* The stub also stores the chain's identity generation (CBRD-26950). Our own oos_insert
+       * issued and published it together with the OID, so replace the master's stamp with the
+       * local one; the 8-byte full length in between is unchanged. */
+      or_advance (&buf, OR_BIGINT_SIZE);
+      or_put_int (&buf, (int) thread_p->oos_oids[oos_oid_count].generation);
+
       oos_oid_count++;
     }
 
```

### 12. `src/transaction/log_applier.c`

단계 9 — transient merged header 의 4번째 필드(generation) 0 명시.

```diff
diff --git a/src/transaction/log_applier.c b/src/transaction/log_applier.c
index 29e977230..cea71e0a9 100644
--- a/src/transaction/log_applier.c
+++ b/src/transaction/log_applier.c
@@ -5028,8 +5028,10 @@ la_rebuild_oos_recdes (LOG_LSA * lsa, RECDES * recdes, OID * head_oid_out)
 
       if (found_head_chunk)
 	{
+	  /* The merged image is transient applier memory: locator_oos_insert_force strips this
+	   * header and the slave-side oos_insert stamps its own generation, so 0 is fine here. */
 	  int offset = OOS_RECORD_HEADER_SIZE;
-	  OOS_RECORD_HEADER merged_header = { total_data_length, 0, OID_INITIALIZER };
+	  OOS_RECORD_HEADER merged_header = { total_data_length, 0, OID_INITIALIZER, 0 };
 	  int chunk_index;
 
 	  if (total_body_length != total_data_length)
```

### 13. `src/transaction/recovery.c`

단계 4 — RV_fun[] 끝에 RVOOS_NEWPAGE 엔트리. undo 는 heap 의 RVHF_NEWPAGE 와 같은 pgbuf_rv_new_page_undo.

```diff
diff --git a/src/transaction/recovery.c b/src/transaction/recovery.c
index 6274685b3..f3c280824 100644
--- a/src/transaction/recovery.c
+++ b/src/transaction/recovery.c
@@ -905,7 +905,13 @@ struct rvfun RV_fun[] = {
    heap_rv_undo_delete,
    heap_rv_redo_delete,
    log_rv_dump_hexa,
-   log_rv_dump_hexa}
+   log_rv_dump_hexa},
+  {RVOOS_NEWPAGE,
+   "RVOOS_NEWPAGE",
+   pgbuf_rv_new_page_undo,
+   oos_rv_redo_newpage,
+   NULL,
+   NULL}
 };
 
 /*
```

### 14. `src/transaction/recovery.h`

단계 4 — RVOOS_NEWPAGE = 140 을 enum 끝에 추가. RV_LAST_LOGID 갱신. 중간 삽입 금지(positional 테이블).

```diff
diff --git a/src/transaction/recovery.h b/src/transaction/recovery.h
index 19be00d1d..acdd0edb9 100644
--- a/src/transaction/recovery.h
+++ b/src/transaction/recovery.h
@@ -208,7 +208,10 @@ typedef enum
    * its undo is logged as MVCC undo (chained for the forward-walk) yet vacuum must not "collect" the
    * already-deleted slot. Crash recovery replays the delete identically to RVHF_DELETE. */
   RVHF_DELETE_NEWHOME_NOTIFY_VACUUM = 139,
-  RV_LAST_LOGID = RVHF_DELETE_NEWHOME_NOTIFY_VACUUM,
+  /* Initializes an OOS data page: page type, slotted-page header, and the slot-0 OOS_PAGE_HEADER
+   * record that carries the page's generation counter (CBRD-26950). */
+  RVOOS_NEWPAGE = 140,
+  RV_LAST_LOGID = RVOOS_NEWPAGE,
 
   RV_NOT_DEFINED = 999
 } LOG_RCVINDEX;
```

### 15. `unit_tests/oos/sql/test_oos_sql_storage.cpp`

단계 10 — FORCE_OUTLINE 수익성 경계 14/15자 → 18/19자, DISK_SIZE 기대값 16/>16 → 20/>20.

```diff
diff --git a/unit_tests/oos/sql/test_oos_sql_storage.cpp b/unit_tests/oos/sql/test_oos_sql_storage.cpp
index b80c6f7a7..9183b8941 100644
--- a/unit_tests/oos/sql/test_oos_sql_storage.cpp
+++ b/unit_tests/oos/sql/test_oos_sql_storage.cpp
@@ -456,10 +456,11 @@ TEST_F (OosSqlStorage, ForceOutlineBypassesRecordGateOnlyAboveInlineStubSize)
 		     "  payload VARCHAR(4096) STORAGE FORCE_OUTLINE)");
   ASSERT_GE (rc, 0);
 
-  /* Packed VARCHAR includes its length prefix, terminator, and alignment: 14 characters occupy 16 bytes on disk,
-   * while 15 characters occupy 20 bytes. */
+  /* Packed VARCHAR includes its length prefix, terminator, and alignment: 18 characters occupy 20 bytes on disk,
+   * while 19 characters occupy 24 bytes. The profitability boundary is the 20-byte OOS inline stub
+   * (OID + length + generation, CBRD-26950). */
   rc = exec_sql ("INSERT INTO t_oos_stg VALUES "
-		 "(1, REPEAT('x', 3000)), (2, 'y'), (3, REPEAT('z', 14)), (4, REPEAT('w', 15)), (5, NULL)");
+		 "(1, REPEAT('x', 3000)), (2, 'y'), (3, REPEAT('z', 18)), (4, REPEAT('w', 19)), (5, NULL)");
   ASSERT_GE (rc, 0);
   db_commit_transaction ();
 
@@ -480,19 +481,19 @@ TEST_F (OosSqlStorage, ForceOutlineBypassesRecordGateOnlyAboveInlineStubSize)
 
   rc = fetch_single_int ("SELECT LENGTH(payload) FROM t_oos_stg WHERE id = 3", &length);
   ASSERT_EQ (rc, NO_ERROR);
-  EXPECT_EQ (length, 14);
+  EXPECT_EQ (length, 18);
 
   rc = fetch_single_int ("SELECT DISK_SIZE(payload) FROM t_oos_stg WHERE id = 3", &length);
   ASSERT_EQ (rc, NO_ERROR);
-  EXPECT_EQ (length, 16);
+  EXPECT_EQ (length, 20);
 
   rc = fetch_single_int ("SELECT LENGTH(payload) FROM t_oos_stg WHERE id = 4", &length);
   ASSERT_EQ (rc, NO_ERROR);
-  EXPECT_EQ (length, 15);
+  EXPECT_EQ (length, 19);
 
   rc = fetch_single_int ("SELECT DISK_SIZE(payload) FROM t_oos_stg WHERE id = 4", &length);
   ASSERT_EQ (rc, NO_ERROR);
-  EXPECT_GT (length, 16);
+  EXPECT_GT (length, 20);
 
   int null_count = 0;
   rc = fetch_single_int ("SELECT COUNT(*) FROM t_oos_stg WHERE id = 5 AND payload IS NULL", &null_count);
```

### 16. `unit_tests/oos/test_oos.cpp`

단계 10 — inline 포맷 20B 라운드트립 + free-space 기대값 4→0.

```diff
diff --git a/unit_tests/oos/test_oos.cpp b/unit_tests/oos/test_oos.cpp
index 6f2af5365..10addb87e 100644
--- a/unit_tests/oos/test_oos.cpp
+++ b/unit_tests/oos/test_oos.cpp
@@ -564,7 +564,9 @@ TEST (OosTest, ShouldInsertIntoDifferentPages)
   assert (raw_ptr != nullptr);
   {
     test_oos_utils::auto_unfixed_page_ptr page_ptr { raw_ptr, test_oos_utils::page_auto_unfix {thread_p} };
-    ASSERT_EQ (free_space, 4);
+    /* The slot-0 page header record (CBRD-26950) plus a max-size chunk fill the page exactly
+     * under the current 16KB layout; the pre-generation layout left 4 bytes of alignment slack. */
+    ASSERT_EQ (free_space, 0);
     // TODO: this should be something like (max_chunk_size - (large_size - (max_chunk_size - sizeof (OOS_RECORD_HEADER))) + sizeof (OOS_RECORD_HEADER))
     // ASSERT_EQ (free_space, 8000 something for 8k);
   }
@@ -574,11 +576,11 @@ TEST (OosTest, ShouldInsertIntoDifferentPages)
 
 TEST (OosTest, OosInlineFormatWriteAndReadBack)
 {
-  /* Test that OR_OOS_INLINE_SIZE = OR_OID_SIZE + OR_BIGINT_SIZE = 16 bytes */
-  ASSERT_EQ (OR_OOS_INLINE_SIZE, OR_OID_SIZE + OR_BIGINT_SIZE);
-  ASSERT_EQ (OR_OOS_INLINE_SIZE, 16);
+  /* Test that OR_OOS_INLINE_SIZE = OR_OID_SIZE + OR_BIGINT_SIZE + OR_INT_SIZE = 20 bytes */
+  ASSERT_EQ (OR_OOS_INLINE_SIZE, OR_OID_SIZE + OR_BIGINT_SIZE + OR_INT_SIZE);
+  ASSERT_EQ (OR_OOS_INLINE_SIZE, 20);
 
-  /* Simulate writing OOS inline data: [OOS OID (8B) + length (8B)] */
+  /* Simulate writing OOS inline data: [OOS OID (8B) + length (8B) + generation (4B)] */
   char buf_data[OR_OOS_INLINE_SIZE];
   OR_BUF write_buf;
   or_init (&write_buf, buf_data, OR_OOS_INLINE_SIZE);
@@ -588,9 +590,11 @@ TEST (OosTest, OosInlineFormatWriteAndReadBack)
   test_oid.slotid = 7;
   test_oid.volid = 3;
   DB_BIGINT test_length = 160 * 1024; /* 160 KB */
+  unsigned int test_generation = 0xC0FFEEu;
 
   or_put_oid (&write_buf, &test_oid);
   or_put_bigint (&write_buf, test_length);
+  or_put_int (&write_buf, (int) test_generation);
 
   /* Verify we wrote exactly OR_OOS_INLINE_SIZE bytes */
   ASSERT_EQ (write_buf.ptr - buf_data, OR_OOS_INLINE_SIZE);
@@ -609,6 +613,10 @@ TEST (OosTest, OosInlineFormatWriteAndReadBack)
   DB_BIGINT read_length = or_get_bigint (&read_buf, &rc);
   ASSERT_EQ (rc, NO_ERROR);
   ASSERT_EQ (read_length, test_length);
+
+  unsigned int read_generation = (unsigned int) or_get_int (&read_buf, &rc);
+  ASSERT_EQ (rc, NO_ERROR);
+  ASSERT_EQ (read_generation, test_generation);
 }
 
 TEST (OosTest, OosInlineFormatWithRealOosInsert)
@@ -631,12 +639,16 @@ TEST (OosTest, OosInlineFormatWithRealOosInsert)
   err = test_oos_utils::oos_insert_from_recdes (thread_p, oos_vfid, rec_in, oos_oid);
   ASSERT_EQ (err, NO_ERROR);
 
-  /* Build inline OOS data: [OOS OID (8B) + length (8B)] */
+  /* Build inline OOS data: [OOS OID (8B) + length (8B) + generation (4B)] */
+  unsigned int oos_generation = 0;
+  ASSERT_EQ (oos_get_generation (thread_p, oos_oid, &oos_generation), NO_ERROR);
+
   char inline_buf[OR_OOS_INLINE_SIZE];
   OR_BUF write_buf;
   or_init (&write_buf, inline_buf, OR_OOS_INLINE_SIZE);
   or_put_oid (&write_buf, &oos_oid);
   or_put_bigint (&write_buf, (DB_BIGINT) rec_in.length);
+  or_put_int (&write_buf, (int) oos_generation);
 
   /* Read back OID and length from inline data */
   OR_BUF read_buf;
@@ -694,11 +706,15 @@ TEST (OosTest, OosInlineLengthMatchesAcrossPages)
       ASSERT_EQ (err, NO_ERROR);
 
       /* Write inline format */
+      unsigned int oos_generation = 0;
+      ASSERT_EQ (oos_get_generation (thread_p, oos_oid, &oos_generation), NO_ERROR);
+
       char inline_buf[OR_OOS_INLINE_SIZE];
       OR_BUF write_buf;
       or_init (&write_buf, inline_buf, OR_OOS_INLINE_SIZE);
       or_put_oid (&write_buf, &oos_oid);
       or_put_bigint (&write_buf, (DB_BIGINT) rec_in.length);
+      or_put_int (&write_buf, (int) oos_generation);
 
       /* Read back length from inline data */
       OR_BUF read_buf;
```

### 17. `unit_tests/oos/test_oos_bestspace.cpp`

단계 10 — 동일 치환(10곳).

```diff
diff --git a/unit_tests/oos/test_oos_bestspace.cpp b/unit_tests/oos/test_oos_bestspace.cpp
index dc5e9b4fd..abc9e2c7d 100644
--- a/unit_tests/oos/test_oos_bestspace.cpp
+++ b/unit_tests/oos/test_oos_bestspace.cpp
@@ -105,7 +105,7 @@ TEST (OosBestspaceTest, BestspaceReuseAfterDelete)
   PAGEID first_page = oid1.pageid;
 
   // Delete the record — page now has free space
-  err = oos_delete (thread_p, oos_vfid, oid1);
+  err = test_oos_utils::oos_delete_current_generation (thread_p, oos_vfid, oid1);
   ASSERT_EQ (err, NO_ERROR);
 
   // Second insert — bestspace should find the freed page
@@ -228,7 +228,7 @@ TEST (OosBestspaceTest, BestspaceMultipleFilesIsolation)
   ASSERT_EQ (err, NO_ERROR);
 
   // Delete from file 1 — frees space in file 1 only
-  err = oos_delete (thread_p, vfid1, oid1);
+  err = test_oos_utils::oos_delete_current_generation (thread_p, vfid1, oid1);
   ASSERT_EQ (err, NO_ERROR);
 
   // Insert into file 2 again — must NOT land on file 1's page
@@ -365,7 +365,7 @@ TEST (OosBestspaceTest, BestspaceInsertDeleteCycle)
       recdes_free_data_area (&rec_out);
 
       // Delete
-      err = oos_delete (thread_p, oos_vfid, oid);
+      err = test_oos_utils::oos_delete_current_generation (thread_p, oos_vfid, oid);
       ASSERT_EQ (err, NO_ERROR);
     }
 
@@ -503,7 +503,7 @@ TEST (OosBestspaceTest, BestspaceDeleteThenFindReclaimsPage)
   // Delete all records
   for (auto &oid : oids)
     {
-      err = oos_delete (thread_p, oos_vfid, oid);
+      err = test_oos_utils::oos_delete_current_generation (thread_p, oos_vfid, oid);
       ASSERT_EQ (err, NO_ERROR);
     }
 
@@ -553,7 +553,7 @@ TEST (OosBestspaceTest, BestspaceMultiChunkDeleteReuse)
   PAGEID large_page = oid_large.pageid;
 
   // Delete the large record — frees space across multiple pages
-  err = oos_delete (thread_p, oos_vfid, oid_large);
+  err = test_oos_utils::oos_delete_current_generation (thread_p, oos_vfid, oid_large);
   ASSERT_EQ (err, NO_ERROR);
 
   // Insert a small record — should reuse one of the freed pages
@@ -693,7 +693,7 @@ TEST (OosBestspaceTest, BestspaceBulkInsertDeleteReinsert)
   // Delete all records
   for (auto &oid : oids)
     {
-      err = oos_delete (thread_p, oos_vfid, oid);
+      err = test_oos_utils::oos_delete_current_generation (thread_p, oos_vfid, oid);
       ASSERT_EQ (err, NO_ERROR);
     }
   oids.clear ();
@@ -792,7 +792,7 @@ TEST (OosBestspaceTest, BestspaceArrayOverflowEviction)
   // Delete all records — every page now has large free space
   for (auto &oid : oids)
     {
-      err = oos_delete (thread_p, oos_vfid, oid);
+      err = test_oos_utils::oos_delete_current_generation (thread_p, oos_vfid, oid);
       ASSERT_EQ (err, NO_ERROR);
     }
 
@@ -1281,7 +1281,7 @@ TEST (OosBestspaceTest, DeleteUpdatesBestspaceCacheDirectly)
   ASSERT_LT (free_after_insert, 500);  // should be very small
 
   // Delete the record — frees ~16KB.  With the fix, bestspace cache is updated.
-  err = oos_delete (thread_p, oos_vfid, oid_large);
+  err = test_oos_utils::oos_delete_current_generation (thread_p, oos_vfid, oid_large);
   ASSERT_EQ (err, NO_ERROR);
 
   // Now insert a record that needs MORE than the old stale freespace (~100 bytes)
@@ -1358,7 +1358,7 @@ TEST (OosBestspaceTest, DeleteMultipleRecordsUpdatesAllPages)
   // Delete all records — each page now has ~16KB free
   for (auto &oid : oids)
     {
-      err = oos_delete (thread_p, oos_vfid, oid);
+      err = test_oos_utils::oos_delete_current_generation (thread_p, oos_vfid, oid);
       ASSERT_EQ (err, NO_ERROR);
     }
 
@@ -1422,7 +1422,7 @@ TEST (OosBestspaceTest, DeletePartialChainUpdatesBestspace)
   ASSERT_EQ (err, NO_ERROR);
 
   // Delete the multi-chunk record — all 3 pages should have freed space in cache
-  err = oos_delete (thread_p, oos_vfid, oid_large);
+  err = test_oos_utils::oos_delete_current_generation (thread_p, oos_vfid, oid_large);
   ASSERT_EQ (err, NO_ERROR);
 
   // Insert 3 separate large records (each nearly fills a page).
```

### 18. `unit_tests/oos/test_oos_common.hpp`

단계 10 — 테스트 전용 oos_delete_current_generation 헬퍼(SA).

```diff
diff --git a/unit_tests/oos/test_oos_common.hpp b/unit_tests/oos/test_oos_common.hpp
index 3051fb6a5..ad7d5a2e4 100644
--- a/unit_tests/oos/test_oos_common.hpp
+++ b/unit_tests/oos/test_oos_common.hpp
@@ -103,6 +103,21 @@ namespace test_oos_utils
     return oos_insert (thread_p, oos_vfid, oos_buffer (recdes.data, static_cast<std::size_t> (recdes.length)), oid);
   }
 
+  /* Deletes the chain at oid using the generation currently stamped in its head chunk. Test-only
+   * shortcut: production callers pass the expected generation parsed from the owning heap
+   * record's OOS inline stub instead (CBRD-26950). A missing chunk fails inside
+   * oos_get_generation, preserving the old "delete of a gone chunk errors" test observable. */
+  inline int oos_delete_current_generation (THREAD_ENTRY *thread_p, const VFID &oos_vfid, const OID &oid)
+  {
+    unsigned int generation = 0;
+    int err = oos_get_generation (thread_p, oid, &generation);
+    if (err != NO_ERROR)
+      {
+	return err;
+      }
+    return oos_delete (thread_p, oos_vfid, oid, generation);
+  }
+
   /* Reads OID into a fresh RECDES, sized via oos_get_length (tests have no heap-inline length). */
   inline int oos_read_with_alloc (THREAD_ENTRY *thread_p, const OID &oid, RECDES &recdes)
   {
```

### 19. `unit_tests/oos/test_oos_delete.cpp`

단계 10 — 직접 oos_delete 호출을 헬퍼로 치환(7곳).

```diff
diff --git a/unit_tests/oos/test_oos_delete.cpp b/unit_tests/oos/test_oos_delete.cpp
index 7f0e14a7e..fb305aa0b 100644
--- a/unit_tests/oos/test_oos_delete.cpp
+++ b/unit_tests/oos/test_oos_delete.cpp
@@ -110,7 +110,7 @@ TEST (OosDeleteTest, OosDeleteBasic)
   ASSERT_GE (free_before, 0);
   test_oos_debug ("free_before=%d", free_before);
 
-  err = oos_delete (thread_p, oos_vfid, oid);
+  err = test_oos_utils::oos_delete_current_generation (thread_p, oos_vfid, oid);
   ASSERT_EQ (err, NO_ERROR);
 
   int free_after = get_free_space_of_oid_page (oid);
@@ -144,7 +144,7 @@ TEST (OosDeleteTest, OosDeleteThenReadFails)
   err = test_oos_utils::oos_insert_from_recdes (thread_p, oos_vfid, rec_in, oid);
   ASSERT_EQ (err, NO_ERROR);
 
-  err = oos_delete (thread_p, oos_vfid, oid);
+  err = test_oos_utils::oos_delete_current_generation (thread_p, oos_vfid, oid);
   ASSERT_EQ (err, NO_ERROR);
 
   // Reading a deleted slot should fail
@@ -208,7 +208,7 @@ TEST (OosDeleteTest, OosDeleteMultiChunk)
   ASSERT_GE (next_free_before, 0);
   test_oos_debug ("head_free_before=%d, next_free_before=%d", head_free_before, next_free_before);
 
-  err = oos_delete (thread_p, oos_vfid, head_oid);
+  err = test_oos_utils::oos_delete_current_generation (thread_p, oos_vfid, head_oid);
   ASSERT_EQ (err, NO_ERROR);
 
   int head_free_after = get_free_space_of_oid_page (head_oid);
@@ -259,7 +259,7 @@ TEST (OosDeleteTest, OosUpdatePattern)
   ASSERT_NE (old_oid.slotid, new_oid.slotid);
 
   // Delete the old record (UPDATE path: discard previous version)
-  err = oos_delete (thread_p, oos_vfid, old_oid);
+  err = test_oos_utils::oos_delete_current_generation (thread_p, oos_vfid, old_oid);
   ASSERT_EQ (err, NO_ERROR);
 
   // New record must still be readable and unchanged
@@ -325,7 +325,7 @@ TEST (OosDeleteTest, OosDeleteRestoresFreeSpace)
   ASSERT_LT (free_after_second_insert, free_after_first_insert);
 
   // Delete the second record
-  err = oos_delete (thread_p, oos_vfid, target_oid);
+  err = test_oos_utils::oos_delete_current_generation (thread_p, oos_vfid, target_oid);
   ASSERT_EQ (err, NO_ERROR);
 
   int free_after_delete = get_free_space_of_oid_page (target_oid);
@@ -377,7 +377,7 @@ TEST (OosDeleteTest, OosDeleteLarge160KBMultiChunk)
   recdes_free_data_area (&rec_check);
 
   // Delete the full chain
-  err = oos_delete (thread_p, oos_vfid, oid);
+  err = test_oos_utils::oos_delete_current_generation (thread_p, oos_vfid, oid);
   ASSERT_EQ (err, NO_ERROR);
 
   // Reading any chunk from the head OID must now fail
@@ -429,7 +429,7 @@ TEST (OosDeleteTest, OosDeleteSlotBecomesUnknown)
     test_oos_debug ("type_before=%d", type_before);
   }
 
-  err = oos_delete (thread_p, oos_vfid, oid);
+  err = test_oos_utils::oos_delete_current_generation (thread_p, oos_vfid, oid);
   ASSERT_EQ (err, NO_ERROR);
 
   // After deletion: spage_get_record_type returns REC_UNKNOWN for deleted slots
```

### 20. `unit_tests/oos/test_oos_delete_server.cpp`

단계 10 — 동일 치환(7곳).

```diff
diff --git a/unit_tests/oos/test_oos_delete_server.cpp b/unit_tests/oos/test_oos_delete_server.cpp
index eca377381..96e37eaa5 100644
--- a/unit_tests/oos/test_oos_delete_server.cpp
+++ b/unit_tests/oos/test_oos_delete_server.cpp
@@ -97,7 +97,7 @@ TEST (OosDeleteServerTest, OosDeleteBasic)
   int free_before = get_free_space_of_oid_page (oid);
   ASSERT_GE (free_before, 0);
 
-  err = oos_delete (thread_p, oos_vfid, oid);
+  err = test_oos_utils::oos_delete_current_generation (thread_p, oos_vfid, oid);
   ASSERT_EQ (err, NO_ERROR);
 
   int free_after = get_free_space_of_oid_page (oid);
@@ -126,7 +126,7 @@ TEST (OosDeleteServerTest, OosDeleteThenReadFails)
   err = test_oos_utils::oos_insert_from_recdes (thread_p, oos_vfid, rec_in, oid);
   ASSERT_EQ (err, NO_ERROR);
 
-  err = oos_delete (thread_p, oos_vfid, oid);
+  err = test_oos_utils::oos_delete_current_generation (thread_p, oos_vfid, oid);
   ASSERT_EQ (err, NO_ERROR);
 
   RECDES rec_out {};
@@ -177,7 +177,7 @@ TEST (OosDeleteServerTest, OosDeleteMultiChunk)
   ASSERT_GE (head_free_before, 0);
   ASSERT_GE (next_free_before, 0);
 
-  err = oos_delete (thread_p, oos_vfid, head_oid);
+  err = test_oos_utils::oos_delete_current_generation (thread_p, oos_vfid, head_oid);
   ASSERT_EQ (err, NO_ERROR);
 
   int head_free_after = get_free_space_of_oid_page (head_oid);
@@ -220,7 +220,7 @@ TEST (OosDeleteServerTest, OosUpdatePattern)
 
   ASSERT_NE (old_oid.slotid, new_oid.slotid);
 
-  err = oos_delete (thread_p, oos_vfid, old_oid);
+  err = test_oos_utils::oos_delete_current_generation (thread_p, oos_vfid, old_oid);
   ASSERT_EQ (err, NO_ERROR);
 
   /* new record must still be readable and unchanged */
@@ -280,7 +280,7 @@ TEST (OosDeleteServerTest, OosDeleteRestoresFreeSpace)
   int free_after_second_insert = get_free_space_of_oid_page (target_oid);
   ASSERT_LT (free_after_second_insert, free_after_first_insert);
 
-  err = oos_delete (thread_p, oos_vfid, target_oid);
+  err = test_oos_utils::oos_delete_current_generation (thread_p, oos_vfid, target_oid);
   ASSERT_EQ (err, NO_ERROR);
 
   int free_after_delete = get_free_space_of_oid_page (target_oid);
@@ -319,7 +319,7 @@ TEST (OosDeleteServerTest, OosDeleteLarge160KBMultiChunk)
   ASSERT_STREQ (rec_check.data, rec_in.data);
   recdes_free_data_area (&rec_check);
 
-  err = oos_delete (thread_p, oos_vfid, oid);
+  err = test_oos_utils::oos_delete_current_generation (thread_p, oos_vfid, oid);
   ASSERT_EQ (err, NO_ERROR);
 
   RECDES rec_after {};
@@ -364,7 +364,7 @@ TEST (OosDeleteServerTest, OosDeleteSlotBecomesUnknown)
     ASSERT_NE (type_before, REC_UNKNOWN);
   }
 
-  err = oos_delete (thread_p, oos_vfid, oid);
+  err = test_oos_utils::oos_delete_current_generation (thread_p, oos_vfid, oid);
   ASSERT_EQ (err, NO_ERROR);
 
   /* after deletion: slot becomes REC_UNKNOWN */
```

### 21. `unit_tests/oos/test_oos_mock_vacuum_server.cpp`

단계 10 — 동일 치환(6곳) + 주석 개명.

```diff
diff --git a/unit_tests/oos/test_oos_mock_vacuum_server.cpp b/unit_tests/oos/test_oos_mock_vacuum_server.cpp
index 8a5e3a7a1..9754b984b 100644
--- a/unit_tests/oos/test_oos_mock_vacuum_server.cpp
+++ b/unit_tests/oos/test_oos_mock_vacuum_server.cpp
@@ -25,7 +25,7 @@
  * code path.
  *
  * For tests that exercise the real vacuum code path (vacuum_heap_oos_delete_within_sysop,
- * heap_recdes_get_oos_oids), see test_oos_vacuum_server.cpp.
+ * heap_recdes_get_oos_refs), see test_oos_vacuum_server.cpp.
  */
 
 #include "test_oos_server_common.hpp"
@@ -100,7 +100,7 @@ TEST_F (OosVacuumServer, BasicInsertAndDelete)
   recdes_free_data_area (&rec_check);
 
   /* Delete — this is what vacuum_heap_oos_delete_within_sysop does */
-  err = oos_delete (thread_p, oos_vfid, oid);
+  err = test_oos_utils::oos_delete_current_generation (thread_p, oos_vfid, oid);
   ASSERT_EQ (err, NO_ERROR);
 
   /* Must be gone */
@@ -141,7 +141,7 @@ TEST_F (OosVacuumServer, MultiChunkDelete)
   ASSERT_GE (free_before, 0);
 
   /* Vacuum deletes the head OID; oos_delete follows the chain internally */
-  err = oos_delete (thread_p, oos_vfid, head_oid);
+  err = test_oos_utils::oos_delete_current_generation (thread_p, oos_vfid, head_oid);
   ASSERT_EQ (err, NO_ERROR);
 
   int free_after = get_free_space_of_oid_page (head_oid);
@@ -187,7 +187,7 @@ TEST_F (OosVacuumServer, LargeMultiPageDelete)
   recdes_free_data_area (&rec_check);
 
   /* Delete entire chain */
-  err = oos_delete (thread_p, oos_vfid, oid);
+  err = test_oos_utils::oos_delete_current_generation (thread_p, oos_vfid, oid);
   ASSERT_EQ (err, NO_ERROR);
 
   /* Must be gone */
@@ -235,7 +235,7 @@ TEST_F (OosVacuumServer, MvccUpdateVacuumPattern)
   ASSERT_EQ (err, NO_ERROR);
 
   /* Step 3: Vacuum deletes old version's OOS */
-  err = oos_delete (thread_p, oos_vfid, old_oid);
+  err = test_oos_utils::oos_delete_current_generation (thread_p, oos_vfid, old_oid);
   ASSERT_EQ (err, NO_ERROR);
 
   /* Step 4: New version OOS still readable */
@@ -290,7 +290,7 @@ TEST_F (OosVacuumServer, BulkVacuumReclaimAndReuse)
   /* Vacuum: delete all OOS records */
   for (int i = 0; i < N; i++)
     {
-      err = oos_delete (thread_p, oos_vfid, oids[i]);
+      err = test_oos_utils::oos_delete_current_generation (thread_p, oos_vfid, oids[i]);
       ASSERT_EQ (err, NO_ERROR);
     }
 
@@ -380,7 +380,7 @@ TEST_F (OosVacuumServer, MultiUpdateChurnVacuum)
 	  ASSERT_EQ (err, NO_ERROR);
 
 	  /* Vacuum deletes old version */
-	  err = oos_delete (thread_p, oos_vfid, current_oids[i]);
+	  err = test_oos_utils::oos_delete_current_generation (thread_p, oos_vfid, current_oids[i]);
 	  ASSERT_EQ (err, NO_ERROR);
 
 	  current_oids[i] = new_oid;
```

### 22. `unit_tests/oos/test_oos_real_vacuum_server.cpp`

단계 10 — 실 DML 빌더에 generation 스탬프(전 호출부가 실 OID).

```diff
diff --git a/unit_tests/oos/test_oos_real_vacuum_server.cpp b/unit_tests/oos/test_oos_real_vacuum_server.cpp
index 456e4cf39..11e456f55 100644
--- a/unit_tests/oos/test_oos_real_vacuum_server.cpp
+++ b/unit_tests/oos/test_oos_real_vacuum_server.cpp
@@ -77,7 +77,7 @@ int bridge_oos_get_max_chunk_size_within_page ();
 
 static const int HEAP_HDR_SIZE = 8;	/* OR_MVCC_REP_SIZE + OR_CHN_SIZE */
 static const int VOT_ENTRY_SZ = 4;	/* OR_INT_SIZE (4-byte offset mode) */
-static const int OOS_INLINE_SZ = 16;	/* OR_OID_SIZE + OR_BIGINT_SIZE */
+static const int OOS_INLINE_SZ = OR_OOS_INLINE_SIZE;	/* OID + length + generation */
 static const int MVCC_HEADER_SPARE = 2 * OR_MVCCID_SIZE;
 
 static int
@@ -124,7 +124,7 @@ build_heap_recdes_with_oos (const std::vector<OID> &oos_oids,
       OR_PUT_INT (vot + i * VOT_ENTRY_SZ, offset | flags);
     }
 
-  /* 4. OOS inline data: OID (8b) + length (8b) per column */
+  /* 4. OOS inline data: OID (8b) + length (8b) + generation (4b) per column */
   char *oos_data = vot + vot_bytes;
   for (int i = 0; i < n_oos; i++)
     {
@@ -132,6 +132,17 @@ build_heap_recdes_with_oos (const std::vector<OID> &oos_oids,
       OR_PUT_OID (slot, &oos_oids[i]);
       INT64 len = oos_lengths[i];
       OR_PUT_BIGINT (slot + OR_OID_SIZE, &len);
+
+      /* All callers in this file embed OIDs of really inserted chunks, so the true generation is
+       * always readable (CBRD-26950). */
+      unsigned int generation = 0;
+      int gen_err = oos_get_generation (thread_p, oos_oids[i], &generation);
+      if (gen_err != NO_ERROR)
+	{
+	  recdes_free_data_area (&rec_out);
+	  return gen_err;
+	}
+      OR_PUT_INT (slot + OR_OID_SIZE + OR_BIGINT_SIZE, (int) generation);
     }
 
   return NO_ERROR;
```

### 23. `unit_tests/oos/test_oos_server.cpp`

단계 10 — inline 포맷 20B, publication 쌍 접근(.oid / { {oid, 0} }).

```diff
diff --git a/unit_tests/oos/test_oos_server.cpp b/unit_tests/oos/test_oos_server.cpp
index 2532957d0..d12caea6f 100644
--- a/unit_tests/oos/test_oos_server.cpp
+++ b/unit_tests/oos/test_oos_server.cpp
@@ -74,7 +74,7 @@ seed_oos_insert_publication_state (const OID &oid, const LOG_LSA &lsa)
 
   thread_p->oos_oids.clear ();
   tdes->oos_insert_lsa_queue.clear ();
-  thread_p->oos_oids.push_back (oid);
+  thread_p->oos_oids.push_back ({ oid, 0 });
   tdes->oos_insert_lsa_queue.push (lsa);
 }
 
@@ -84,7 +84,7 @@ assert_oos_insert_publication_state (const OID &oid, const LOG_LSA &lsa)
   LOG_TDES *tdes = get_current_tdes ();
   ASSERT_NE (tdes, nullptr);
   ASSERT_EQ (thread_p->oos_oids.size (), 1U);
-  EXPECT_TRUE (OID_EQ (&thread_p->oos_oids[0], &oid));
+  EXPECT_TRUE (OID_EQ (&thread_p->oos_oids[0].oid, &oid));
   ASSERT_EQ (tdes->oos_insert_lsa_queue.size (), 1U);
   EXPECT_TRUE (LSA_EQ (&tdes->oos_insert_lsa_queue.front (), &lsa));
 }
@@ -541,8 +541,8 @@ TEST (OosServerTest, OosSuccessfulPublicationWithoutReplicationTrackingKeepsOidO
   LOG_TDES *tdes = get_current_tdes ();
   ASSERT_NE (tdes, nullptr);
   ASSERT_EQ (thread_p->oos_oids.size (), 2U);
-  EXPECT_TRUE (OID_EQ (&thread_p->oos_oids[0], &oids[0]));
-  EXPECT_TRUE (OID_EQ (&thread_p->oos_oids[1], &oids[1]));
+  EXPECT_TRUE (OID_EQ (&thread_p->oos_oids[0].oid, &oids[0]));
+  EXPECT_TRUE (OID_EQ (&thread_p->oos_oids[1].oid, &oids[1]));
   EXPECT_TRUE (tdes->oos_insert_lsa_queue.is_empty ());
 }
 
@@ -569,8 +569,8 @@ TEST (OosServerTest, OosTrackedSingleChunkBatchKeepsPairedPublication)
   LOG_TDES *tdes = get_current_tdes ();
   ASSERT_NE (tdes, nullptr);
   ASSERT_EQ (thread_p->oos_oids.size (), 2U);
-  EXPECT_TRUE (OID_EQ (&thread_p->oos_oids[0], &oids[0]));
-  EXPECT_TRUE (OID_EQ (&thread_p->oos_oids[1], &oids[1]));
+  EXPECT_TRUE (OID_EQ (&thread_p->oos_oids[0].oid, &oids[0]));
+  EXPECT_TRUE (OID_EQ (&thread_p->oos_oids[1].oid, &oids[1]));
   EXPECT_EQ (tdes->oos_insert_lsa_queue.size (), 2U);
   EXPECT_FALSE (LSA_ISNULL (&tdes->oos_insert_lsa_queue.front ()));
 }
@@ -600,10 +600,10 @@ TEST (OosServerTest, OosTrackedMixedBatchPreservesDummyAndHeadPairing)
   LOG_TDES *tdes = get_current_tdes ();
   ASSERT_NE (tdes, nullptr);
   ASSERT_EQ (thread_p->oos_oids.size (), 4U);
-  EXPECT_TRUE (OID_EQ (&thread_p->oos_oids[0], &oids[0]));
-  EXPECT_TRUE (OID_ISNULL (&thread_p->oos_oids[1]));
-  EXPECT_TRUE (OID_EQ (&thread_p->oos_oids[2], &oids[1]));
-  EXPECT_TRUE (OID_EQ (&thread_p->oos_oids[3], &oids[2]));
+  EXPECT_TRUE (OID_EQ (&thread_p->oos_oids[0].oid, &oids[0]));
+  EXPECT_TRUE (OID_ISNULL (&thread_p->oos_oids[1].oid));
+  EXPECT_TRUE (OID_EQ (&thread_p->oos_oids[2].oid, &oids[1]));
+  EXPECT_TRUE (OID_EQ (&thread_p->oos_oids[3].oid, &oids[2]));
   EXPECT_EQ (tdes->oos_insert_lsa_queue.size (), 4U);
   EXPECT_FALSE (LSA_ISNULL (&tdes->oos_insert_lsa_queue.front ()));
 }
@@ -635,8 +635,8 @@ TEST (OosServerTest, ReplicaOosItemsAccumulateAndFixupConsumesInOrder)
   ASSERT_EQ (locator_oos_insert_force (thread_p, &mutable_class_oid, &oos_recdes1), NO_ERROR);
   ASSERT_EQ (locator_oos_insert_force (thread_p, &mutable_class_oid, &oos_recdes2), NO_ERROR);
   ASSERT_EQ (thread_p->oos_oids.size (), 2U);
-  const OID slave_oid1 = thread_p->oos_oids[0];
-  const OID slave_oid2 = thread_p->oos_oids[1];
+  const OID slave_oid1 = thread_p->oos_oids[0].oid;
+  const OID slave_oid2 = thread_p->oos_oids[1].oid;
 
   const OID placeholder1 = make_test_oid (2, 765431, 31);
   const OID placeholder2 = make_test_oid (2, 765432, 32);
@@ -661,7 +661,7 @@ TEST (OosServerTest, ReplicaFixupRejectsInsufficientOids)
   const OID class_oid = find_db_user_class_oid ();
   ASSERT_FALSE (OID_ISNULL (&class_oid));
   const OID accumulated_oid = make_test_oid (1, 765433, 33);
-  thread_p->oos_oids = { accumulated_oid };
+  thread_p->oos_oids = { { accumulated_oid, 0 } };
 
   const OID placeholder1 = make_test_oid (2, 765434, 34);
   const OID placeholder2 = make_test_oid (2, 765435, 35);
@@ -683,7 +683,7 @@ TEST (OosServerTest, ReplicaFixupRejectsExtraOids)
   ASSERT_FALSE (OID_ISNULL (&class_oid));
   const OID accumulated_oid1 = make_test_oid (1, 765436, 36);
   const OID accumulated_oid2 = make_test_oid (1, 765437, 37);
-  thread_p->oos_oids = { accumulated_oid1, accumulated_oid2 };
+  thread_p->oos_oids = { { accumulated_oid1, 0 }, { accumulated_oid2, 0 } };
 
   const OID placeholder = make_test_oid (2, 765438, 38);
   RECDES recdes = RECDES_INITIALIZER;
@@ -717,7 +717,7 @@ TEST (OosServerTest, ReplicaScalarPublicationAllocationFailureInvalidatesAccumul
     recdes_free_data_area (&recdes);
   });
 
-  thread_p->oos_oids = { make_test_oid (1, 765439, 39) };
+  thread_p->oos_oids = { { make_test_oid (1, 765439, 39), 0 } };
   LOG_TDES *tdes = get_current_tdes ();
   ASSERT_NE (tdes, nullptr);
   tdes->oos_insert_lsa_queue.clear ();
@@ -1043,20 +1043,20 @@ TEST (OosServerTest, OosInsertManyPreservesMixedSingleAndMultiChunkPublicationOr
   ASSERT_FALSE (thread_p->oos_oids.empty ());
   std::size_t pos = 0;
   ASSERT_LT (pos, thread_p->oos_oids.size ());
-  EXPECT_TRUE (OID_EQ (&thread_p->oos_oids[pos], &oids[0]));
+  EXPECT_TRUE (OID_EQ (&thread_p->oos_oids[pos].oid, &oids[0]));
   pos++;
 
   ASSERT_LT (pos, thread_p->oos_oids.size ());
-  if (OID_ISNULL (&thread_p->oos_oids[pos]))
+  if (OID_ISNULL (&thread_p->oos_oids[pos].oid))
     {
       pos++;
       ASSERT_LT (pos, thread_p->oos_oids.size ());
     }
-  EXPECT_TRUE (OID_EQ (&thread_p->oos_oids[pos], &oids[1]));
+  EXPECT_TRUE (OID_EQ (&thread_p->oos_oids[pos].oid, &oids[1]));
   pos++;
 
   ASSERT_LT (pos, thread_p->oos_oids.size ());
-  EXPECT_TRUE (OID_EQ (&thread_p->oos_oids[pos], &oids[2]));
+  EXPECT_TRUE (OID_EQ (&thread_p->oos_oids[pos].oid, &oids[2]));
   pos++;
   EXPECT_EQ (pos, thread_p->oos_oids.size ());
 
@@ -1288,12 +1288,12 @@ TEST (OosServerTest, OosGetLengthAroundMaxChunkSize)
 }
 
 // ============================================================================
-// TC: OOS inline format [OID(8B) + length(8B)]
+// TC: OOS inline format [OID(8B) + length(8B) + generation(4B)]
 // ============================================================================
 TEST (OosServerTest, OosInlineFormatWriteAndReadBack)
 {
-  ASSERT_EQ (OR_OOS_INLINE_SIZE, OR_OID_SIZE + OR_BIGINT_SIZE);
-  ASSERT_EQ (OR_OOS_INLINE_SIZE, 16);
+  ASSERT_EQ (OR_OOS_INLINE_SIZE, OR_OID_SIZE + OR_BIGINT_SIZE + OR_INT_SIZE);
+  ASSERT_EQ (OR_OOS_INLINE_SIZE, 20);
 
   char buf_data[OR_OOS_INLINE_SIZE];
   OR_BUF write_buf;
@@ -1304,9 +1304,11 @@ TEST (OosServerTest, OosInlineFormatWriteAndReadBack)
   test_oid.slotid = 7;
   test_oid.volid = 3;
   DB_BIGINT test_length = 160 * 1024;
+  unsigned int test_generation = 0xC0FFEEu;
 
   or_put_oid (&write_buf, &test_oid);
   or_put_bigint (&write_buf, test_length);
+  or_put_int (&write_buf, (int) test_generation);
 
   ASSERT_EQ (write_buf.ptr - buf_data, OR_OOS_INLINE_SIZE);
 
@@ -1323,6 +1325,10 @@ TEST (OosServerTest, OosInlineFormatWriteAndReadBack)
   DB_BIGINT read_length = or_get_bigint (&read_buf, &rc);
   ASSERT_EQ (rc, NO_ERROR);
   ASSERT_EQ (read_length, test_length);
+
+  unsigned int read_generation = (unsigned int) or_get_int (&read_buf, &rc);
+  ASSERT_EQ (rc, NO_ERROR);
+  ASSERT_EQ (read_generation, test_generation);
 }
 
 TEST (OosServerTest, OosInlineFormatWithRealOosInsert)
@@ -1344,12 +1350,16 @@ TEST (OosServerTest, OosInlineFormatWithRealOosInsert)
   err = test_oos_utils::oos_insert_from_recdes (thread_p, oos_vfid, rec_in, oos_oid);
   ASSERT_EQ (err, NO_ERROR);
 
-  /* Build inline OOS data: [OOS OID (8B) + length (8B)] */
+  /* Build inline OOS data: [OOS OID (8B) + length (8B) + generation (4B)] */
+  unsigned int oos_generation = 0;
+  ASSERT_EQ (oos_get_generation (thread_p, oos_oid, &oos_generation), NO_ERROR);
+
   char inline_buf[OR_OOS_INLINE_SIZE];
   OR_BUF write_buf;
   or_init (&write_buf, inline_buf, OR_OOS_INLINE_SIZE);
   or_put_oid (&write_buf, &oos_oid);
   or_put_bigint (&write_buf, (DB_BIGINT) rec_in.length);
+  or_put_int (&write_buf, (int) oos_generation);
 
   /* Read back OID and length from inline data */
   OR_BUF read_buf;
@@ -1402,11 +1412,15 @@ TEST (OosServerTest, OosInlineLengthMatchesAcrossPages)
       err = test_oos_utils::oos_insert_from_recdes (thread_p, oos_vfid, rec_in, oos_oid);
       ASSERT_EQ (err, NO_ERROR);
 
+      unsigned int oos_generation = 0;
+      ASSERT_EQ (oos_get_generation (thread_p, oos_oid, &oos_generation), NO_ERROR);
+
       char inline_buf[OR_OOS_INLINE_SIZE];
       OR_BUF write_buf;
       or_init (&write_buf, inline_buf, OR_OOS_INLINE_SIZE);
       or_put_oid (&write_buf, &oos_oid);
       or_put_bigint (&write_buf, (DB_BIGINT) rec_in.length);
+      or_put_int (&write_buf, (int) oos_generation);
 
       OR_BUF read_buf;
       or_init (&read_buf, inline_buf, OR_OOS_INLINE_SIZE);
```

### 24. `unit_tests/oos/test_oos_server_common.hpp`

단계 10 — 같은 헬퍼(SERVER_MODE).

```diff
diff --git a/unit_tests/oos/test_oos_server_common.hpp b/unit_tests/oos/test_oos_server_common.hpp
index 5ed498c3f..9b218593a 100644
--- a/unit_tests/oos/test_oos_server_common.hpp
+++ b/unit_tests/oos/test_oos_server_common.hpp
@@ -224,6 +224,21 @@ namespace test_oos_utils
     return oos_insert (thread_p, oos_vfid, oos_buffer (recdes.data, static_cast<std::size_t> (recdes.length)), oid);
   }
 
+  /* Deletes the chain at oid using the generation currently stamped in its head chunk. Test-only
+   * shortcut: production callers pass the expected generation parsed from the owning heap
+   * record's OOS inline stub instead (CBRD-26950). A missing chunk fails inside
+   * oos_get_generation, preserving the old "delete of a gone chunk errors" test observable. */
+  inline int oos_delete_current_generation (THREAD_ENTRY *thread_p, const VFID &oos_vfid, const OID &oid)
+  {
+    unsigned int generation = 0;
+    int err = oos_get_generation (thread_p, oid, &generation);
+    if (err != NO_ERROR)
+      {
+	return err;
+      }
+    return oos_delete (thread_p, oos_vfid, oid, generation);
+  }
+
   /* Reads OID into a fresh RECDES, sized via oos_get_length (tests have no heap-inline length). */
   inline int oos_read_with_alloc (THREAD_ENTRY *thread_p, const OID &oid, RECDES &recdes)
   {
```

### 25. `unit_tests/oos/test_oos_vacuum_server.cpp`

단계 10 — 합성 빌더에 generation 스탬프(synthetic_oids 가드), 추출기 테스트 refs 화 + generation 일치 검증.

```diff
diff --git a/unit_tests/oos/test_oos_vacuum_server.cpp b/unit_tests/oos/test_oos_vacuum_server.cpp
index ea361aba4..f7b983400 100644
--- a/unit_tests/oos/test_oos_vacuum_server.cpp
+++ b/unit_tests/oos/test_oos_vacuum_server.cpp
@@ -19,11 +19,11 @@
 /*
  * test_oos_vacuum_server.cpp - SERVER_MODE tests for actual vacuum OOS code paths
  *
- * Exercises the real vacuum_heap_oos_delete_within_sysop() -> heap_recdes_get_oos_oids() ->
+ * Exercises the real vacuum_heap_oos_delete_within_sysop() -> heap_recdes_get_oos_refs() ->
  * oos_delete() code path by crafting minimal heap RECDES with OOS inline data
  * and calling vacuum_heap_oos_delete_within_sysop() directly.
  *
- * Also tests heap_recdes_get_oos_oids() and heap_recdes_contains_oos()
+ * Also tests heap_recdes_get_oos_refs() and heap_recdes_contains_oos()
  * directly for OOS OID extraction from crafted heap records.
  */
 
@@ -44,20 +44,24 @@ int bridge_oos_get_max_chunk_size_within_page ();
 //   [4..7]         CHN: 0  (cache coherence number)
 //   --- header ends (8 bytes) ---
 //   [8..8+4N-1]    VOT: N int32 entries, each = (offset_from_vot_start | flags)
-//   [8+4N..]       OOS inline data: per column, OID (8b) + length (8b)
-//   --- total: 8 + 20*N bytes ---
+//   [8+4N..]       OOS inline data: per column, OID (8b) + length (8b) + generation (4b)
+//   --- total: 8 + 24*N bytes ---
 //
-// OR_VAR_OFFSET(obj, i) = header_size + (VOT[i] & ~0x3) = 8 + (4N + 16i)
+// OR_VAR_OFFSET(obj, i) = header_size + (VOT[i] & ~0x3) = 8 + (4N + 20i)
 //
 
 static const int HEAP_HDR_SIZE = 8;	/* OR_MVCC_REP_SIZE + OR_CHN_SIZE */
 static const int VOT_ENTRY_SZ = 4;	/* OR_INT_SIZE (4-byte offset mode) */
-static const int OOS_INLINE_SZ = 16;	/* OR_OID_SIZE + OR_BIGINT_SIZE */
+static const int OOS_INLINE_SZ = OR_OOS_INLINE_SIZE;	/* OID + length + generation */
 
+/* Builds the stub of each OID with the generation currently stamped in its head chunk, mirroring
+ * what the real insert path records (CBRD-26950). Pass synthetic_oids = true when the OIDs were
+ * never inserted: their stubs get generation 0 and storage is not probed (a debug-build pgbuf_fix
+ * of an unreserved page aborts the process). */
 static int
 build_heap_recdes_with_oos (const std::vector<OID> &oos_oids,
 			    const std::vector<INT64> &oos_lengths,
-			    RECDES &rec_out)
+			    RECDES &rec_out, bool synthetic_oids = false)
 {
   const int n_oos = (int) oos_oids.size ();
   assert (n_oos > 0);
@@ -98,7 +102,7 @@ build_heap_recdes_with_oos (const std::vector<OID> &oos_oids,
       OR_PUT_INT (vot + i * VOT_ENTRY_SZ, offset | flags);
     }
 
-  /* 4. OOS inline data: OID (8b) + length (8b) per column */
+  /* 4. OOS inline data: OID (8b) + length (8b) + generation (4b) per column */
   char *oos_data = vot + vot_bytes;
   for (int i = 0; i < n_oos; i++)
     {
@@ -106,6 +110,18 @@ build_heap_recdes_with_oos (const std::vector<OID> &oos_oids,
       OR_PUT_OID (slot, &oos_oids[i]);
       INT64 len = oos_lengths[i];
       OR_PUT_BIGINT (slot + OR_OID_SIZE, &len);
+
+      unsigned int generation = 0;
+      if (!synthetic_oids)
+	{
+	  int gen_err = oos_get_generation (thread_p, oos_oids[i], &generation);
+	  if (gen_err != NO_ERROR)
+	    {
+	      recdes_free_data_area (&rec_out);
+	      return gen_err;
+	    }
+	}
+      OR_PUT_INT (slot + OR_OID_SIZE + OR_BIGINT_SIZE, (int) generation);
     }
 
   return NO_ERROR;
@@ -143,7 +159,7 @@ TEST_F (OosVacuumCodePathServer, HeapRecdesContainsOos)
   OID dummy_oid = {1, 2, 3};
   INT64 dummy_len = 100;
   RECDES rec {};
-  err = build_heap_recdes_with_oos ({dummy_oid}, {dummy_len}, rec);
+  err = build_heap_recdes_with_oos ({dummy_oid}, {dummy_len}, rec, true /* synthetic_oids */);
   ASSERT_EQ (err, NO_ERROR);
   test_oos_utils::auto_freed_recdes_ptr defer_free (&rec, recdes_free_data_area);
 
@@ -164,9 +180,9 @@ TEST_F (OosVacuumCodePathServer, HeapRecdesContainsOos)
 }
 
 // ============================================================================
-// TC-V2: heap_recdes_get_oos_oids extracts single OOS OID
+// TC-V2: heap_recdes_get_oos_refs extracts a single OOS reference
 // ============================================================================
-TEST_F (OosVacuumCodePathServer, HeapRecdesGetOosOidsSingle)
+TEST_F (OosVacuumCodePathServer, HeapRecdesGetOosRefsSingle)
 {
   int err;
 
@@ -188,20 +204,25 @@ TEST_F (OosVacuumCodePathServer, HeapRecdesGetOosOidsSingle)
   ASSERT_EQ (err, NO_ERROR);
   test_oos_utils::auto_freed_recdes_ptr defer_heap (&heap_rec, recdes_free_data_area);
 
-  /* Extract OOS OIDs via the function vacuum relies on */
-  OID_VECTOR extracted;
-  err = heap_recdes_get_oos_oids (&heap_rec, extracted);
+  /* Extract OOS references via the function vacuum relies on */
+  OOS_REF_VECTOR extracted;
+  err = heap_recdes_get_oos_refs (&heap_rec, extracted);
   ASSERT_EQ (err, NO_ERROR);
   ASSERT_EQ ((int) extracted.size (), 1);
-  ASSERT_EQ (extracted[0].pageid, oos_oid.pageid);
-  ASSERT_EQ (extracted[0].slotid, oos_oid.slotid);
-  ASSERT_EQ (extracted[0].volid, oos_oid.volid);
+  ASSERT_EQ (extracted[0].head_oid.pageid, oos_oid.pageid);
+  ASSERT_EQ (extracted[0].head_oid.slotid, oos_oid.slotid);
+  ASSERT_EQ (extracted[0].head_oid.volid, oos_oid.volid);
+
+  /* The extracted generation must equal the one stamped in the chunk (CBRD-26950). */
+  unsigned int stored_generation = 0;
+  ASSERT_EQ (oos_get_generation (thread_p, oos_oid, &stored_generation), NO_ERROR);
+  ASSERT_EQ (extracted[0].generation, stored_generation);
 }
 
 // ============================================================================
-// TC-V3: heap_recdes_get_oos_oids extracts multiple OOS OIDs
+// TC-V3: heap_recdes_get_oos_refs extracts multiple OOS references
 // ============================================================================
-TEST_F (OosVacuumCodePathServer, HeapRecdesGetOosOidsMultiple)
+TEST_F (OosVacuumCodePathServer, HeapRecdesGetOosRefsMultiple)
 {
   int err;
 
@@ -227,16 +248,16 @@ TEST_F (OosVacuumCodePathServer, HeapRecdesGetOosOidsMultiple)
   ASSERT_EQ (err, NO_ERROR);
   test_oos_utils::auto_freed_recdes_ptr defer_heap (&heap_rec, recdes_free_data_area);
 
-  OID_VECTOR extracted;
-  err = heap_recdes_get_oos_oids (&heap_rec, extracted);
+  OOS_REF_VECTOR extracted;
+  err = heap_recdes_get_oos_refs (&heap_rec, extracted);
   ASSERT_EQ (err, NO_ERROR);
   ASSERT_EQ ((int) extracted.size (), 2);
-  ASSERT_EQ (extracted[0].pageid, oid1.pageid);
-  ASSERT_EQ (extracted[0].slotid, oid1.slotid);
-  ASSERT_EQ (extracted[0].volid, oid1.volid);
-  ASSERT_EQ (extracted[1].pageid, oid2.pageid);
-  ASSERT_EQ (extracted[1].slotid, oid2.slotid);
-  ASSERT_EQ (extracted[1].volid, oid2.volid);
+  ASSERT_EQ (extracted[0].head_oid.pageid, oid1.pageid);
+  ASSERT_EQ (extracted[0].head_oid.slotid, oid1.slotid);
+  ASSERT_EQ (extracted[0].head_oid.volid, oid1.volid);
+  ASSERT_EQ (extracted[1].head_oid.pageid, oid2.pageid);
+  ASSERT_EQ (extracted[1].head_oid.slotid, oid2.slotid);
+  ASSERT_EQ (extracted[1].head_oid.volid, oid2.volid);
 }
 
 // ============================================================================
```
