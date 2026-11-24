# CUBRID/cubrid PR #8627 (`CBRD-28032`) 코드 리뷰 보고서

## 1. 검토 개요 및 판정 (Verdict & Recommendation)

- **검토 일자 (`Asia/Seoul`)**: `2026-11-24`
- **검토 대상 저장소 / PR**: [CUBRID/cubrid#8627](https://github.com/CUBRID/cubrid/pull/8627) — *[CBRD-28032] Bitmap heap scan and batch join: heap lookups of an index scan in file order, and the inner heap pages of a nested-loop join told to the OS ahead* (작성자: `xmilex-git`, 30파일 `+4,537 / -253`)
- **고정 스냅샷 (Pinned SHAs)**:
  - `base` / `merge-base` (`develop`): `96f9fb1c9e0da6c9744888cdc717126b782ee511`
  - `head` (`CBRD-28032`): `b52b26697c31e24b7c656ce1cb6a41dfba180617`
  - Patch SHA-256: `279258d18aa2ba2015dce77bb7687cef8dddf2362c39d1ee68b62a359fa6b625`
- **검증 빌드 환경**: 로컬 `debug_gcc` 빌드·설치 (`just configure && just build-and-install`), `cubrid server` (`testdb`) + `csql` + `cubrid lockdb` 실측 재현
- **판정 (`Verdict`)**: **`changes-required` (수정 요청)**
- **후속 검토 필요 (`Follow-up review required`)**: **`yes`** — 필수 수정 항목(`F-1`, `F-2`) 반영 후 델타 재검증 필요.
- **권고안 요약**:
  - **필수 수정 (차단, P1)**: 확인된 결함 2건(`F-1` 상관 부질의 `COUNT(*)` 2배 과대 계산, `F-2` 3단계 이상 NL batch `span`의 `FOR UPDATE` 조상 행 락 조기 해제)은 `debug_gcc` 런타임에서 재현·확정되었으므로 머지 전 수정이 필요합니다.
  - **비차단 보강 권고 (소스 근거 미검증 위험, P2/P3)**: OOM(`std::bad_alloc`·`memoize` NULL 처리), `S_DOESNT_EXIST` assert/`er_clear()` 누락, 병렬 로그 워크 `OLD_PAGE` 폴백, 통계 병합 누락 등은 차단 사유는 아니나 안정성 보강을 권장합니다.
  - 기존 스레드 현황: `hornetmj`, `hgryoo`, `HyunukLee`, `shparkcubrid`, `soheejung-cs`, `youngjinj` 등이 기존 지적을 해소하며 승인했으나(참고: `b52b26697c` 이후 재승인은 `hornetmj` 1명), 기존 스레드와 중복되지 않는 위 `F-1`·`F-2` 결함이 신규 확인되었습니다.

---

## 2. 필수 수정 항목 (Confirmed P1 Defects — Blocking)

### `F-1` [P1 — 결과 오류] 상관 부질의 `sq_batch` + `count_star_with_iscan_opt` 조합에서 `COUNT(*)`를 2배로 계산

- **위치 (`b52b26697c`)**:
  - `src/query/query_executor.c`: [`qexec_sq_batch_arm` (L13959-L14001)](https://github.com/CUBRID/cubrid/blob/b52b26697c31e24b7c656ce1cb6a41dfba180617/src/query/query_executor.c#L13959-L14001), [`qexec_sq_batch_add` (L14155-L14189)](https://github.com/CUBRID/cubrid/blob/b52b26697c31e24b7c656ce1cb6a41dfba180617/src/query/query_executor.c#L14155-L14189), [`qexec_sq_batch_give_slice` (L14345-L14353)](https://github.com/CUBRID/cubrid/blob/b52b26697c31e24b7c656ce1cb6a41dfba180617/src/query/query_executor.c#L14345-L14353), [`qexec_intprt_fnc` (L16494-L16508)](https://github.com/CUBRID/cubrid/blob/b52b26697c31e24b7c656ce1cb6a41dfba180617/src/query/query_executor.c#L16494-L16508) 및 [`L16652-L16659`](https://github.com/CUBRID/cubrid/blob/b52b26697c31e24b7c656ce1cb6a41dfba180617/src/query/query_executor.c#L16652-L16659)
  - `src/query/scan_manager.c`: [`scan_index_take_nl_slice` (L6603-L6620)](https://github.com/CUBRID/cubrid/blob/b52b26697c31e24b7c656ce1cb6a41dfba180617/src/query/scan_manager.c#L6603-L6620), [`scan_index_nl_batch_ok` (L6628-L6641)](https://github.com/CUBRID/cubrid/blob/b52b26697c31e24b7c656ce1cb6a41dfba180617/src/query/scan_manager.c#L6628-L6641), [`scan_next_index_scan` (L6878-L6897)](https://github.com/CUBRID/cubrid/blob/b52b26697c31e24b7c656ce1cb6a41dfba180617/src/query/scan_manager.c#L6878-L6897)
- **발생 조건**:
  - NL batch join(`t1->nl_batch->on == true`)의 단일 상관 부질의(`dptr_list`)가 **비커버링 단일 인덱스 `COUNT(*)`**를 데이터 필터 없이 실행할 때 발생합니다(예: `TIMESTAMPTZ`/`DATETIMETZ` 인덱스 컬럼으로 `TP_TYPE_NOT_SUPPORT_COVERING`에 의해 `xasl_generation.c`에서 `coverage = false`가 되거나, `allow_index_opt == false`인 콜레이션 사용 시).
- **원인 경로**:
  1. `qexec_sq_batch_add` (`query_executor.c:14156-14167`)는 `qexec_intprt_fnc` 진입 전에 `sq_xasl->spec_list->s_id`를 열어 `scan_index_nl_batch_ok`를 호출합니다. 이 시점에 `isidp->need_count_only`는 아직 `false`이므로 `scan_ok = true`가 되어 `sq->b`에 OID를 수집합니다.
  2. 재실행 시 `qexec_execute_mainblock_internal` (`query_executor.c:24888-24892`)이 `qexec_sq_batch_give_slice`로 `isidp->nl_slice_cnt = count`를 전달한 뒤, `qexec_intprt_fnc` (`16503-16506`)가 `need_count_only = true`와 `count_star_with_iscan_opt = true`를 설정합니다.
  3. 1차 루프에서 `scan_next_index_scan` (`scan_manager.c:6878-6896`)은 `scan_index_take_nl_slice`를 통해 `oids_count = count`를 반환하되 `bt_scan`은 시작하지 않은 상태(`curr_keyno == -1`)로 남겨둡니다. `qexec_intprt_fnc` (`16655-16658`)는 `curr_cnt += count` 후 `position = S_BEFORE`로 되돌리고 다음 반복을 수행합니다.
  4. 2차 루프에서 `nl_slice_cnt == -1`이므로 `call_get_next_index_oidset` (`6884`)가 B-tree를 처음부터 끝까지 다시 스캔하여 `count`를 한 번 더 누적합니다.
- **런타임 재현 근거 (`debug_gcc`, `csql`)**:
  - 케이스 A (`f1b_t0`/`f1b_t1`/`f1b_t2`, `k TIMESTAMPTZ`, `idx_k` 인덱스, `f1b_t1.id=1..20` 각 `k`당 `f1b_t2` 2행):
    ```sql
    SELECT /*+ ORDERED USE_NL(f1b_t0, f1b_t1) NO_HASH_JOIN(f1b_t0, f1b_t1) */
      'F1B_SQ_BATCH', f1b_t1.id, (SELECT /*+ USE_IDX */ COUNT(*) FROM f1b_t2 WHERE f1b_t2.k = f1b_t1.k) AS cnt
    FROM f1b_t0 JOIN f1b_t1 ON f1b_t1.j = f1b_t0.j
    ORDER BY f1b_t1.id;
    ```
  - **관측 결과**:
    - `SET TRACE ON` 기준 `f1b_t1.idx_j`에 `nlbatch: 2`, 상관 부질의 `f1b_t2.idx_k`에 `count_only: true, nlbatch: 1`이 동시에 활성화됨.
    - 기준선(`USING INDEX NONE`): `id=1..20` 모두 `cnt = 2` 반환.
    - `F1B_SQ_BATCH`: `id=1`이 **`cnt = 4`**(2배), `id=2..20`은 `cnt = 2` 반환.
    - 소규모 3행 케이스(`f1_t1.idx_j` + `f1_t2.idx_k`, `nlbatch: 1, count_only: true`)에서도 동일하게 `id=1`이 기준선 `1` 대신 **`cnt = 2`**를 반환함.
- **수정 방향**: `qexec_sq_batch_arm`에서 `count_star_with_iscan_opt` 대상(`BUILDVALUE_PROC` 단일 인덱스 `COUNT(*)` 무필터)을 제외하거나, `qexec_sq_batch_add` / `scan_index_nl_batch_ok` 단계에서 `count_star_with_iscan_opt` 조건을 판정해 `sq_batch`를 비활성화하십시오(또는 `need_count_only` 상태에서 `scan_index_take_nl_slice`가 `BTREE_END_OF_SCAN`을 표시하게 해야 하나, `complete == false` 케이스 구분보다 전자 차단 방식이 안전함).

---

### `F-2` [P1 — 동시성/락 안전성] 3단계 이상 NL batch(`span == true`)가 `FOR UPDATE` 조상 테이블 행 락을 조기 해제

- **위치 (`b52b26697c`)**:
  - `src/query/query_executor.c`: [`QEXEC_UNLOCK_UNQUALIFIED_OID` (L188-L214)](https://github.com/CUBRID/cubrid/blob/b52b26697c31e24b7c656ce1cb6a41dfba180617/src/query/query_executor.c#L188-L214), [`qexec_nl_batch_arm` (L12692-L12752)](https://github.com/CUBRID/cubrid/blob/b52b26697c31e24b7c656ce1cb6a41dfba180617/src/query/query_executor.c#L12692-L12752), [`qexec_nl_batch_add` (L12988-L12991)](https://github.com/CUBRID/cubrid/blob/b52b26697c31e24b7c656ce1cb6a41dfba180617/src/query/query_executor.c#L12988-L12991), [`qexec_execute_scan_outer` (L13724)](https://github.com/CUBRID/cubrid/blob/b52b26697c31e24b7c656ce1cb6a41dfba180617/src/query/query_executor.c#L13724), [`qexec_intprt_fnc` (L16979-L16999)](https://github.com/CUBRID/cubrid/blob/b52b26697c31e24b7c656ce1cb6a41dfba180617/src/query/query_executor.c#L16979-L16999)
- **발생 조건**:
  - `t1 -> t2 -> t3` 형태의 3단계(또는 그 이상) NL 조인에서 `t1`이 `mvcc_select_lock_needed == true`(`FOR UPDATE OF t1` 등)이고 `t2`, `t3`가 락을 잡지 않는 인덱스 스캔일 때 발생합니다.
- **원인 경로**:
  1. `qexec_nl_batch_arm(t1, t2, true)`가 `t2->nl_batch->on = true`로 설정하고, `qexec_nl_batch_arm(t2, t3, false)`는 `!outer_is_root && t2->nl_batch->on`을 보고 `t3->nl_batch->span = true`로 설정합니다(`t3->nl_batch->lists`에 `t1->val_list` 포함).
  2. 실행 시 `t1`은 행 `a1`에 `X_LOCK`을 잡고 `t2`로 넘깁니다. `qexec_nl_batch_add(t2)`는 직계 `outer`(`t1`)의 `mvcc_select_lock_needed`를 보고 `S_DOESNT_EXIST`로 passing 모드가 되지만(`t2->nl_batch->on`은 유지), `t3`에서 `qexec_nl_batch_add(t3)`는 **직계 `outer`(`t2`)의 `mvcc_select_lock_needed`만 검사**(`12991`)하므로 `a1`을 `t3->nl_batch`에 저장하고 `S_END`를 반환합니다.
  3. `t2`는 `!t3->nl_batch->span`이 `false`이므로 `13724`에서 `t3`를 비우지 않고 `t1`로 `S_END`를 반환합니다.
  4. `qexec_intprt_fnc(t1)` (`16979-16998`)는 `scan_ptr_qualified == false`로 판단해 **`QEXEC_UNLOCK_UNQUALIFIED_OID(thread_p, t1)`를 호출하여 `t1`의 `X_LOCK`을 즉시 해제**합니다(`t3`가 나중에 `a1`을 재실행·출력할 때까지 `a1`이 무잠금 상태에 노출됨).
- **런타임 재현 근거 (`debug_gcc`, 2세션 `csql` + `cubrid lockdb`)**:
  - **세션 1** (`COMMITTED READ`, `--no-auto-commit`, 100,000행 `f2_big1` -> `f2_big2` -> `f2_big3`, `id=1`만 매칭되고 나머지는 `LENGTH(REPEAT(MD5(id), 1500)) < 0` 술어로 ~2.5초 스캔):
    ```sql
    SELECT /*+ ORDERED USE_NL(f2_big1, f2_big2) USE_NL(f2_big2, f2_big3)
               NO_HASH_JOIN(f2_big1, f2_big2) NO_HASH_JOIN(f2_big2, f2_big3) */
      f2_big1.id, f2_big1.v, f2_big2.v2, f2_big3.v3
    FROM f2_big1
      JOIN f2_big2 ON f2_big2.k1 = f2_big1.k1
      JOIN f2_big3 ON f2_big3.k2 = f2_big2.k2
    WHERE f2_big1.id <= 100000
      AND (f2_big1.id = 1 OR LENGTH(REPEAT(MD5(f2_big1.id), 1500)) < 0)
    USING INDEX f2_big1.pk_f2_big1_id(+) FOR UPDATE OF f2_big1;
    ```
  - **세션 1 실행 중(`t=1.0s`) 관측**:
    - `cubrid lockdb testdb`: `dba.f2_big1` 클래스의 `IX_LOCK`만 남고 인스턴스(`1|8641|1`) **`X_LOCK` 보유 0건** (이미 해제됨).
    - **세션 2** (`SET SYSTEM PARAMETERS 'lock_timeout=1'; UPDATE f2_big1 SET v = 999 WHERE id = 1; COMMIT;`): **대기 없이 `0.002795 sec` 만에 즉시 성공** (`REPEATABLE READ` 대조 실험에서는 동일 행 `1|8641|1`에 `X_LOCK`이 유지되어 세션 2가 `lock_timeout=1` 타임아웃 에러 발생).
    - 이후 **세션 1 완료 결과**: `1 | 999 | 100 | 100` 출력 (`FOR UPDATE OF f2_big1` 스캔이 끝나기 전에 타 트랜잭션 변경이 개입하고 `selupd` 재잠금/재읽기까지 노출됨).
- **수정 방향**: `qexec_nl_batch_arm`에서 `span = true`를 설정할 때(또는 `qexec_nl_batch_add`에서) 직계 `outer`뿐 아니라 `batch->lists`에 포함된 **모든 조상 스캔(`outer`, `above->outer`, ...)** 중 `qexec_spec_is_for_update` / `mvcc_select_lock_needed`가 참인 스캔이 하나라도 있으면 배치를 비활성화(`span` 및 `batch` 중단)해야 합니다.

---

## 3. 비차단 보강 권고 (소스 근거 미검증 위험, Evidence Level 2–3)

아래 항목들은 빌드/실행 제약(OOM 주입, TSAN/ASAN, 로그 워크 강제 언픽스, ARM64 등)으로 런타임 재현은 미실행 상태이나, 핀된 소스에서 결함 메커니즘이 확인되어 보강을 권장하는 항목입니다(머지 차단 사유 아님).

| ID | 심각도 | 위치 (`b52b26697c`) | 내용 및 위험 | 권장 조치 |
|---|---|---|---|---|
| **`SB-1` / `CONC-F2`** | **P2** | `src/query/scan_manager.c:7280, 7289, 7484, 7492, 7545, 7554, 7623, 7658, 7844, 7864, 7875-7877, 7988`; `scan_manager.h:1135-1136` | `scan_bitmap_marks`가 `std::vector`(`m_bm_sectors`, `kept`, `order`, `sub.chain`, `sub.batch`, `sub.where`)와 `new`/`new[]`를 `try/catch` 없이 호출합니다. `SERVER_MODE` 전역 `::operator new` (`memory_wrapper.cpp:81-84`)는 OOM 시 `std::bad_alloc`을 던지며, `SA_MODE`(`cubridsa`)·`CUB_ADDRESS_SANITIZER` 빌드에서는 `new` 매크로가 꺼져(`memory_wrapper.hpp:63`) `new` 자체가 예외를 던집니다. `px_scan` 워커(`thread_worker_pool_impl.hpp:1758`)나 직렬 스캔에 `catch`가 없어 OOM 시 서버가 `std::terminate()`로 즉시 비정상 종료(`SIGABRT`)하며 `collector.partsect_ftab`/`bm`을 누수합니다. | `std::vector` 연산 및 `new`를 `try/catch (const std::bad_alloc &)`로 감싸 `ER_OUT_OF_VIRTUAL_MEMORY`로 변환하거나 C 할당(`malloc`/`calloc`) + 명시적 해제로 통일 |
| **`F-4`** | **P2** | `src/query/memoize.cpp:692-753, 771, 810, 871, 896-916` | 신규 추가된 `storage::has_key()`, `key_hash()`, `begin_key()`가 `db_change_private_heap(..., 0)` 후 `get_key()`(내부에서 예외를 던지는 `std::vector::reserve`/`push_back` 호출)를 부르면서 기존 `get()`/`put()`과 달리 `scope_exit`와 `try/catch`가 없습니다. 또한 `m_key_fixed_allocator`(`throw_on_oom == false`)가 OOM으로 `nullptr`를 반환해 `get_key() == nullptr`가 되면 `begin_key()`가 `m_last_key == nullptr`인 채 `false`를 반환해 호출자(`query_executor.c:13316`)의 `put()`/`put_nullptr()`에서 `assert(m_last_key != nullptr)` 또는 `stop_insert()` 역참조 `SIGSEGV`를 유발합니다. | 3개 메서드에 `scope_exit` + `try/catch` 추가 및 `get_key() == nullptr` 안전 처리 |
| **`CONC-F3` / `SOV-02`** | **P2** | `src/query/scan_manager.c:8355-8385, 8429-8445`; `src/query/parallel/px_scan/index/px_scan_index_leaf_slot_walker.cpp:513-525` | 인덱스 단계와 힙 단계 사이의 시간 간격이 넓어진 비트맵 스캔이 호출하는 `scan_next_index_lookup_heap`은 `sp_scan == S_DOESNT_EXIST` 검사가 `assert(sp_scan == S_SUCCESS \|\| sp_scan == S_SUCCESS_CHN_UPTODATE)`(`8381`)와 `eval_data_filter`(`8385`) **뒤**(`8429`)에 있어 디버그 크래시/릴리스 빈 `recdes` 필터 평가 위험이 있습니다. 병렬 `leaf_slot_walker::lookup_heap_row` (`513-516`)는 `S_DOESNT_EXIST`를 잡지만 `er_clear()`를 호출하지 않아 `ER_HEAP_UNKNOWN_OBJECT`가 스레드 에러 컨텍스트에 잔류합니다. | `8358` 직후 `S_DOESNT_EXIST` 처리 및 두 경로 모두 `er_clear()` 호출 |
| **`SOV-01`** | **P2 (완화됨)** | `src/query/parallel/px_scan/px_scan_slot_iterator_index.cpp:185-221` | 병렬 `next_bitmap_row`에서 `heap_get_visible_version_from_log`가 `heap_prev_version_walk_release_pages`로 `scan_cache->page_watcher.pgptr`를 언픽스한 뒤 해당 슬롯이 `S_END`(`205`) 또는 `keeps_bitmap_page() == true`(`215`)면 `m_bm_unfixed`가 `false`로 남습니다. 같은 페이지의 다음 슬롯이 `fix_bitmap_page` (`OLD_PAGE_MAYBE_DEALLOCATED`)를 건너뛰고 `heap_prepare_object_page`에서 `OLD_PAGE`로 픽스합니다. (`scan_bitmap_marks::init`의 MVCC 홀드백으로 실제 페이지 해제는 차단되나 계약 위반) | `m_bm_unfixed \|\| !m_slot_walker.has_bitmap_page()` 확인 또는 매 슬롯 `fix_bitmap_page` 호출 |
| **`F-5`** | **P3** | `src/xasl/xasl_iteration.cpp:100-125, 161-197` | `xasl_merge_stats`와 `xasl_merge_partition_stats`가 `nl_batch_rows`(`184`)는 병합하면서 새로 추가된 `bitmap_heap*` 통계 5개 필드를 누락했습니다. 현재 비상관 부질의는 메인 스레드에서 실행되고 상관 부질의는 비트맵 대상에서 제외되어 도달 범위가 `px_scan` 워커 클론 내부 서브트리로 좁으나 정합성 누락입니다. | 두 병합 함수에 `bitmap_heap*` 필드 병합 추가 |
| **`CONC-F4`** | **P3** | `src/query/parallel/px_scan/px_scan_task.cpp:1017-1048` | `join_rows()`의 `RESULT_TYPE::MERGEABLE_LIST` 분기(`1021`)가 `result_handler_p->write()`의 `false` 반환을 무시해 워커 에러 후에도 루프를 계속 돕니다. | 반환값 확인 및 `ERROR_INTERRUPTED_FROM_WORKER_THREAD` 시 `stop = true; return S_ERROR;` |
| **기타 경량/방어적 위험** | **P3** | `query_executor.c:12762`, `px_scan_task.cpp:1541`, `scan_manager.h:1064`, `query_manager.c:3454`, `px_scan_input_handler_index.cpp:68`, `scan_manager.c:4707, 5713, 7471, 7905` | `CONC-F1`(병렬 `groupby_skip` 조인의 `outer_is_root=false` 가드 우회는 현재 `g_grbynum_pred` 제한으로 미도달 확인), `SB-U1`(중단된 병렬 스캔이 `!loaders_left()`로 먼저 빠져 `take_over` 정렬 수행), `SB-U2`(ARM64 `memory_order_relaxed` 시 훔치기 조기 종료 가능), `SB-U3`(`qmgr_free_list_temp_file`의 비동기 `temp_vfid` 읽기 — TSAN), `U-1`(병렬 `EXISTS` `ahead_single` 미전달), `U-2`(`BITMAP_HEAP_TABLE_ENTRIES` ~189GiB 오버플로우), `SOV-03`(`scan_fix_bitmap_heap_page`의 `PAGE_HEAP`/bestspace 방어 검사 부재), `SB-U4`(`scan_reset_scan_block` `nl_slice_cnt` 리셋·파티션 트레이스 잔존·`slotid >= 0` assert). | 후속 보강 또는 경량 정리 권고 |

---

## 4. 기존 리뷰 스레드 중복 회피 및 `b52b26697c` 검증 요약

이미 해결/합의된 기존 리뷰 스레드들은 중복 지적을 피하고 현재 헤드(`b52b26697c`)에서 유지 여부를 검증했습니다:
- **유지 확인(해소됨)**: `greptile`(분석 함수 `XASL_ANALYTIC_SKIP_SORT`/`outer_sorted` 제외, 파티션/힙 통계 분리), `shparkcubrid`(SP/메서드 블록 `PT_METHOD_CALL` 제외, 빈 outer `n_rows >= oid_target` 종료, 재계획 시 플래그 일괄 초기화, 직렬 임시파일 `query_id`, 상관 부질의 제외 및 섹터 비례 시작 비용), `soheejung-cs`(`sq_batch`+`memoize` 순서, 병렬 `bitmap_keep_page`, `CONNECT BY` 반복 스캔 플래그 해제, `USE_DESC_IDX` 의도 동작), `hornetmj`(`READ COMMITTED` SP 스냅샷 갱신 제외), `HyunukLee`(3단계 조인 `outer_ended` 복원, `bitmap_keep_page` 순차 스캔 동등성), `youngjinj`(다음 창 선읽기 `6385ae8c62`), `hgryoo`(DML 후속 분리 논의).
- **최신 커밋 `b52b26697c`(대부분의 승인 이후 푸시된 병렬 파티션 청크 공유) 교차 검증 결과**:
  - `load()`가 `w->share_mutex` 하에 `share_next = share_n = 0`을 먼저 초기화한 뒤 `heap_tbl`/`order`를 채우고 다시 `share_mutex` 하에 `share_n`을 공개하며, `take_chunk()`가 `share_mutex` 안에서 스택 배열 `chunk[64]`/`ahead[128]`로 복사하므로 **use-after-reload, 누락/중복 페이지, `m_bm_nsub > 1` 서브파티션 경계 오류는 x86-64 TSO에서 발생하지 않음(소스 검증 완료)**.
  - 단, `PRM_ID_PARALLEL_SCAN_PAGE_THRESHOLD=256` 이상 병렬 비트맵 힙 스캔의 다중 스레드 런타임 실행은 본 로컬 검증에서 미실행 상태입니다(`parallel_scan_page_threshold`가 비동적 파라미터라 256페이지 미만 테이블에서는 직렬 실행과 동일하게 `0` 워커/병합 경로 미진입).

---

## 5. Storage · OOS · Relocation · VACUUM · Edge Cases 및 기각 후보

1. **OOS / `REC_BIGONE` / `REC_RELOCATION` (`cache_last_fix_page = true`) — 안전성 확인 (소스 + 직렬/배치 실측)**:
   - `REC_RELOCATION -> REC_NEWHOME` (`Q` 페이지): `heap_init_get_context`가 `P`를 `home_page_watcher`로 이동하고, `heap_prepare_get_context`가 `Q`를 `fwd_page_watcher`에 `COPY`로 고정한 뒤 `heap_clean_get_context`가 **`home_page_watcher`만** `scan_cache->page_watcher`로 복원하고 `fwd_page_watcher`는 언픽스하므로 `Q`가 캐시 페이지를 덮어쓰거나 래치를 누수하지 않습니다.
   - `REC_BIGONE`은 `PGBUF_ORDERED_HEAP_OVERFLOW`(상위 랭크)로 읽고 즉시 해제하며, OOS 컬럼 읽기는 `oos_fix_page_if_oos`가 `DISK_VOLHEADER_PAGE`·`DISK_STAB_PAGE`·`PAGE_OOS`만 래치하므로 `PAGE_HEAP` 래치와 교착하지 않습니다. 조인(`scan_ptr != NULL`)에서는 항상 `bitmap_keep_page = false`입니다.
   - **런타임 실측 (`debug_gcc`)**: `VARCHAR(60000)` + 삭제 후 확장 업데이트(`Q < P` 및 `Q > P` 재배치, 2,850행) 테이블 `se_oos`에서 직렬 비트맵(`OOS_SERIAL_BM`: `pages: 19, rows: 55`), `PARALLEL(4)`(`OOS_PAR4_BM`), `nl_batch`(`OOS_NL_BATCH`: `78행, sum(char_length)=25971, sum(id)=126241`) 결과가 각각 `USING INDEX NONE` 기준선(`55행, sum(char_length)=18515, sum(id)=87595` 및 `78행, 25971, 126241`)과 완전 일치했습니다.
2. **동시 `UPDATE`/`DELETE`/`VACUUM` 및 MVCC 스냅샷 — 안전성 확인 (소스 + 동시 스트레스 실측)**:
   - `scan_bitmap_marks::init` (`scan_manager.c:7825-7830`)가 `file_get_all_data_sectors` 호출 **직전**에 `logtb_get_mvcc_snapshot`으로 스냅샷을 확보해 `m_transaction_lowest_visible_mvccids[tran_index]`를 고정하므로, 스캔이 보는 행/슬롯을 VACUUM이 회수하거나 슬롯을 재사용할 수 없습니다. 이후 새로 할당된 섹터/페이지는 스냅샷 이후 삽입(`TOO_NEW_FOR_SNAPSHOT`)이므로 `mark()`가 섹터 목록 밖 OID를 버리는 것이 안전합니다.
   - `file_perm_dealloc`으로 빈 힙 페이지가 해제되어 `PAGE_FTAB` 등으로 재사용되더라도 섹터는 `hfid->vfid`에 남고 `pgbuf_ordered_unfix_reused_page`가 `ER_PB_BAD_PAGEID`로 정리하므로 `scan_fix_bitmap_heap_page`가 안전하게 건너뜁니다.
   - **런타임 실측 (`debug_gcc`)**: 20,000행 테이블 `vac_t`에 대해 동시 `DELETE` 트랜잭션 실행 중 직렬 비트맵(`SER_BM`: `pages: 340, rows: 1380`) 및 `PARALLEL(4)` 실행 시 크래시/assert 없이 `USING INDEX NONE` 기준선(`count(*)=1380, sum(v)=13918940`)과 완전 일치했습니다.
3. **빈 결과 / 0 섹터 / 중복 OID / 해시 스필 경계 — 안전성 확인**:
   - **런타임 실측 (`debug_gcc`)**: 0행 테이블(`EMPTY_SERIAL`/`EMPTY_PAR2`: `0`), OR 범위 중복 OID 제거(`OR_SERIAL_BM`: `5584행` 기준선 일치), 30,000행 저밀도/다수 페이지 테이블(`SPILL_SERIAL_BM`/`SPILL_PAR4_BM`: `pages: 509, rows: 150, sum(id)=2259900` 기준선 일치), 35,000행 밀집 테이블(`DENSE_SERIAL_BM`: `6980행` 기준선 일치) 모두 통과했습니다. `BITMAP_HEAP_TABLE_ENTRIES <= nb/2 <= 32768` 및 첫 파티션 유지(`s < ceil(N/U)`) 대수 불변식도 소스에서 확인했습니다.
4. **HA / 복제 / WAL / 디스크 포맷 — 해당 없음 (`Not Applicable`)**:
   - 변경된 30개 파일 전체에 WAL 레코드(`RV*`), 복구 콜백, `log_append*`, HA/복제, 영속 페이지 포맷 변경이 전혀 없습니다(`FILE_TEMP` 및 실행 시 메모리 필드만 사용).
5. **기각된 후보 (`Dropped Candidates`)**:
   - `F-3` (`t2`에 `nl_batch + sq_batch`, `t3`에 `span` 동시 활성화): `query_executor.c:12710`이 `outer->dptr_list != NULL`인 경우 `t3->nl_batch`를 거부하므로 도달 불가능(런타임 확인) → 기각.
   - `CONC-F1` (병렬 `groupby_skip` 조인 경계 훼손): 현재 옵티마이저(`query_planner.c:6515`)의 조인 `groupby_skip`이 `LIMIT`(`g_grbynum_pred != NULL`)을 요구하고 `px_scan_checker.cpp:208`이 `g_grbynum_pred != nullptr`인 병렬 스캔을 차단하므로 현행 코드에서는 미도달(`NO_PARALLEL_SCAN`/`PARALLEL(4)` 양쪽 모두 `15행, sum=0..42000, count=300` 일치 확인) → P1에서 방어적 잠재 위험으로 하향.
   - `cppcheck` `scan_manager.c:6745` `uninitvar`: `n > 0` 가드 및 `vpids[n]` 전량 초기화 확인 → 거짓 양성으로 기각.

---

## 6. 커버리지·한계 및 후속 검증 계획

- **커버리지 요약**: PR `#8627` 변경 30개 파일 전수 및 저장/동시성 교차 모듈(`heap_file.c`, `slotted_page.c`, `file_manager.c`, `overflow_file.c`, `oos_file.cpp`, `mvcc_table.cpp`, `vacuum.c`) 검토 완료.
- **정적 점검**: `cubrid-static-check --no-clang-tidy 96f9fb1c9e0da6c9744888cdc717126b782ee511 b52b26697c31e24b7c656ce1cb6a41dfba180617` 실행(`scan_manager.c:6745`는 거짓 양성, `timercmp` 2건은 기존 cppcheck 매크로 파싱 오류).
- **리뷰 구성 및 한계**: 4개 전문 리뷰 에이전트(모두 `Gemini 4 Neon (High)`) + 코디네이터 `debug_gcc` 로컬 빌드/프로브 검증으로 수행되어 이종 모델 다양성이 축소되었고, 에이전트별 토큰/할당량 텔레메트리는 측정 불가(`unknown`)입니다.
- **미실행 검증 (후속 확인 필요)**:
  1. `F-1`·`F-2` 수정 커밋 반영 후 위 `csql` + `cubrid lockdb` + 2세션 동시 `UPDATE` 회귀 재실행.
  2. `index_pages >= 256` 규모(예: 40,000행 이상 비압축 인덱스, 리프 300페이지 이상)에서의 `PARALLEL(4)` 비트맵 힙 스캔(`b52b26697c` `take_chunk` 워크 스틸링) 및 `slotid >= 640` 오버플로우 리스트(`w->over`) 병합 실측.
  3. `SA_MODE`(`csql -S`)·ASAN/TSAN 빌드 또는 OOM 장애 주입 검증(`SB-1`/`CONC-F2`, `F-4`, `SB-U3`), 및 비 TSO(ARM64) 메모리 순서 검증(`SB-U2`).
