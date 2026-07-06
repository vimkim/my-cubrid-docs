# CBRD-27029 Expand Raw Records

Review anchor: **PR #7416** (base `feat/oos`), HEAD `7bd030af6` (`[CBRD-27029] Make heap OOS fetch policy explicit`).

PR 는 3개 커밋으로 진화했다. 최종 상태만이 계약이다:

1. `b35b67eba` — expand 를 기본값으로 뒤집고 `*_skip_oos_expand` opt-out wrapper 를 추가 (폐기된 접근).
2. `85d8f5480` — `heap_next` 계열에 `HEAP_OOS_EXPAND_POLICY` enum 인자 도입, wrapper 제거 시작.
3. `7bd030af6` — `heap_get_visible_version`, `heap_scan_get_visible_version`, `heap_init_get_context` 까지 enum 확장, 모든 wrapper 제거 완료.

> 이 문서의 라인 번호는 모두 `7bd030af6` 기준이다. 검증: 2026-07-06, call site 전수 조사 (~55곳) + base(`origin/feat/oos`) 대비 동작 diff.
> 확인된 수정 항목은 엔진 worktree 의 `CBRD-27029-correction-plan.md` 로 이관했다 (아래 "Verified Findings" 참고).

## Merge Policy: Make OOS Fetch Semantics Explicit

기존 `heap_next()` 같은 public heap fetch API 를 그대로 두고, 별도 `*_expand_oos()` / `*_skip_oos_expand()`
API 를 추가한 접근은 실수였다. OOS 는 heap record 의 물리적 의미를 크게 바꾸는 변경이므로, 기존 caller 가 raw
`RECDES` 바이트를 소비하는지, 아니면 attribute layer 로 값을 읽는지 API 단위로 전부 재검토해야 한다.

문제는 `origin/develop` 이 계속 갱신되는 동안 다른 팀의 변경이 기존 `heap_next()` 나 visible-version 계열 public API
를 사용한다는 점이다. 함수 signature 가 그대로면 merge 시점에 새 caller 가 기존 암묵적 OOS 동작을
가정하게 되고, OOS branch 에서는 그 caller 가 inspection 없이 들어와 raw OOS OID 노출 또는 불필요한 record-level
Expand 같은 심각한 회귀를 반복해서 만들었다.

따라서 CBRD-27029 의 의도는 **merge conflict/build failure 를 통해 caller 검토를 강제**하는 것이다.

- `heap_next()`, `heap_get_visible_version()` 같은 기존 public API 이름은 유지하되, `HEAP_OOS_EXPAND_POLICY` 인자를
  추가해 모든 caller 가 `HEAP_WITH_OOS_EXPAND` 또는 `HEAP_WITHOUT_OOS_EXPAND` 를 명시하게 한다.
- `*_expand_oos()` / `*_skip_expand_oos()` wrapper 는 제거한다. 새 API 이름으로 의미를 숨기지 않고, 기존 API call
  자체에서 OOS 계약이 보이게 한다.
- develop merge 후 새 caller 가 생기면 빌드 실패가 나야 한다. merger/API user 는 실패한 call site 를 raw-record
  소비 경로인지 attribute-layer 소비 경로인지 판정한 뒤 정책 인자를 추가해야 한다.

## Purpose

CBRD-27029 는 OOS 적용 후 raw `RECDES` 바이트를 직접 쓰는 경로에서 inline OOS OID 가 그대로 보일 수 있는 회귀를
막는 작업이다.

- `AS-IS:` `heap_next()` 호출자가 OOS Expand 여부를 함수 이름만으로 명시하기 어려웠고, develop 에서 온 기존
  `heap_next()` 사용자는 OOS 경로에서 raw record 소비인지 attribute-layer 소비인지 다시 판단해야 했다.
- `TO-BE:` `heap_next()` 이름은 유지하되, 호출자가 `HEAP_OOS_EXPAND_POLICY` enum 으로 record-level OOS Expand 여부를
  명시한다.

여기서 OOS Expand 는 record-level eager 동작이다. 즉, `RECDES` 안의 모든 inline OOS OID 를 실제 값으로 바꾸어 record
전체를 다시 만든다. OOS Resolve 는 column-level lazy 동작이다. 즉, `heap_attrinfo_read_dbvalues()` 가 필요한 컬럼을
읽을 때 `oos_read()` 로 실제 값을 가져온다.

## Policy

| Enum | Meaning | Use when |
|---|---|---|
| `HEAP_WITH_OOS_EXPAND` | Return raw-record-safe `RECDES` bytes by replacing inline OOS OID slots with actual values. | The caller consumes raw record bytes: copyarea shipping, `or_*` parsing, raw serialization, reinsertion, or byte-level comparison. |
| `HEAP_WITHOUT_OOS_EXPAND` | Keep inline OOS OID slots in the heap record. | The caller immediately decodes through the attribute layer, which resolves OOS columns lazily — or does not consume the recdes at all (OID advance, existence check). |

`HEAP_OOS_EXPAND_POLICY_INVALID = 0` 이 별도로 있어 zero-init 된 context 가 정책 없이 fetch 로 들어오면
`heap_record_replace_oos_oids()` 가 assert + `S_ERROR` 로 잡는다 (`heap_oos.cpp:351`).

## Changed Public APIs (at HEAD `7bd030af6`)

| Function | Change |
|---|---|
| `heap_next()` | Adds `HEAP_OOS_EXPAND_POLICY oos_expand_policy`. |
| `heap_next_sampling()` | Adds `HEAP_OOS_EXPAND_POLICY oos_expand_policy`. |
| `heap_prev()` | Adds `HEAP_OOS_EXPAND_POLICY oos_expand_policy`. |
| `heap_get_visible_version()` | Adds `HEAP_OOS_EXPAND_POLICY oos_expand_policy`. |
| `heap_scan_get_visible_version()` | Adds `HEAP_OOS_EXPAND_POLICY oos_expand_policy`. |
| `heap_init_get_context()` | Adds `HEAP_OOS_EXPAND_POLICY oos_expand_policy` — context 에 기본 정책이 없으므로 호출자가 반드시 명시. `heap_get_last_version()` 도 이 context 정책을 그대로 따른다 (end-to-end 확인: `heap_get_visible_version_internal` → `heap_record_replace_oos_oids`). |
| `heap_next_expand_oos()` | Removed; callers now use `heap_next(..., HEAP_WITH_OOS_EXPAND)`. |
| `heap_next_skip_oos_expand()` | Removed; callers now use `heap_next(..., HEAP_WITHOUT_OOS_EXPAND)`. |
| `heap_next_sampling_skip_oos_expand()` | Removed. |
| `heap_prev_skip_oos_expand()` | Removed. |
| `heap_get_visible_version_expand_oos()` | Removed. |
| `heap_get_visible_version_skip_oos_expand()` | Removed. |
| `heap_scan_get_visible_version_skip_oos_expand()` | Removed. |

Wrapper 이름 잔존 여부: `src/` 전체 grep 결과 0건 (주석 포함).

### 정책을 내부에 고정한 API (인자 없음)

아래 API 들은 enum 인자를 받지 않고 내부에서 정책을 고정한다. Reviewer 는 이 목록을 알고 있어야 한다:

| API | Hardcoded policy | 비고 |
|---|---|---|
| `heap_first()` / `heap_last()` | `HEAP_WITH_OOS_EXPAND` | 범용 "레코드 하나 주세요" API. 호출자 중 `tde.c:584` 가 raw memcpy 소비 → 보수적 WITH 유지 (결정: 2026-07-06). 나머지 호출자(dblink, boot_sr, 존재 확인)에는 no-op 수준. |
| `heap_next_record_info()` / `heap_prev_record_info()` | `HEAP_WITHOUT_OOS_EXPAND` | record-info 진단 스캔 (`heap_file.c:20351/20401`); 메타데이터만 소비. |
| `heap_next_1page()` | 현재 `HEAP_WITH_OOS_EXPAND` (`heap_file.c:8473`) | **수정 대상 → WITHOUT.** 호출자 2곳 모두 attr-layer: `px_scan_slot_iterator.cpp:106` (병렬 heap scan), `btree_load.c:3417` (병렬 index build). |
| `heap_scanrange_*` | 현재 `HEAP_WITH_OOS_EXPAND` (13 sites) | **수정 대상 → WITHOUT.** 외부 소비자는 `scan_manager.c:5057/5061/5919` grouped scan 뿐 (attr-layer). |
| `locator_lock_and_get_object()` / `locator_get_object()` / `locator_lock_and_get_object_with_evaluation()` | 현재 `HEAP_WITH_OOS_EXPAND` (`locator_sr.c:13324/13457/13558`) | **수정 대상 → 정책 인자를 signature 로 스레딩.** 소비자가 혼합됨 (아래 참고). |

## Implementation

`src/storage/heap_file.h` 에 `HEAP_OOS_EXPAND_POLICY` 를 추가하고 `heap_next()`, `heap_next_sampling()`,
`heap_prev()`, `heap_get_visible_version()`, `heap_scan_get_visible_version()`, `heap_init_get_context()` 의 public
signature 에 enum 인자를 추가했다. 함수 이름은 유지하되 호출부에서 정책이 보이도록 만들었다.

`src/storage/heap_file.c` 의 `heap_next_internal()` 과 heap-scan visible-version helper 는 이 enum 을 그대로 전달한다.
`HEAP_GET_CONTEXT` 도 boolean `expand_oos` 대신 enum 정책을 보관한다. context initializer 에 기본 정책은 없다.
실제 record-level Expand 실행 지점인 `heap_record_replace_oos_oids()` (`heap_oos.cpp:347`) 는
`HEAP_WITHOUT_OOS_EXPAND` 일 때 바로 반환하며, invalid policy 는 assert + `S_ERROR` 로 처리한다.

```c
heap_next (..., HEAP_WITH_OOS_EXPAND);
heap_next (..., HEAP_WITHOUT_OOS_EXPAND);
heap_get_visible_version (..., HEAP_WITH_OOS_EXPAND);
heap_get_visible_version (..., HEAP_WITHOUT_OOS_EXPAND);
```

## Caller Review Table

전수 조사 결과 (HEAD `7bd030af6`, ~55 call sites). 컬럼 설명:

- **vs base**: `origin/feat/oos` 대비 실효 동작. *rename* = base 에서 이미 `*_expand_oos` (동작 동일),
  *unchanged* = base plain call 과 동작 동일, **flip** = 이 PR 이 실효 동작을 no-expand → expand 로 바꿈.
- **Correction**: `CBRD-27029-correction-plan.md` 의 결정 사항. *keep* = 그대로 둠.

### 판정 기준 재확인

`HEAP_WITHOUT_OOS_EXPAND` 로 확인된 모든 site 는 attr-layer 소비 또는 recdes 미소비로 검증됐다.
**raw-byte 소비인데 WITHOUT 인 data-corruption 사례는 0건.** 문제는 전부 반대 방향(불필요한 WITH)이다.

### src/connection, src/loaddb, src/query

| Caller | API | Policy | vs base | Review reason | Correction |
|---|---|---|---|---|---|
| `connection_support.cpp:2471` | heap_next | WITHOUT | unchanged | `heap_attrinfo_read_dbvalues()` (:2474). | keep |
| `load_server_loader.cpp:243` | heap_next | WITHOUT | unchanged | OID advance 전용; recdes 는 다음 fetch 가 다시 바인딩. | keep |
| `load_server_loader.cpp:247` | heap_get_visible_version | WITH | **flip** | 소비는 `heap_attrinfo_read_dbvalues()` (:260) 뿐. | **→ WITHOUT** |
| `dblink_global_tran_catalog.c:225` | heap_next | WITHOUT | unchanged | attr-layer 디코드. | keep |
| `dblink_global_tran_catalog.c:481` | heap_next | WITHOUT | unchanged | attr-layer 디코드. | keep |
| `query_executor.c:10730` | heap_get_visible_version | WITHOUT | unchanged | UPDATE LOB cleanup, attr-layer (:10737). | keep |
| `query_executor.c:11540` | heap_get_visible_version | WITHOUT | unchanged | DELETE LOB cleanup, attr-layer (:11547). | keep |
| `query_executor.c:12375` | heap_get_visible_version | WITHOUT | unchanged | duplicate-key update, attr-layer (:12397). | keep |
| `query_executor.c:13803` | locator_get_object | (WITH in getter) | **flip** | `oRec` 소비는 `heap_attrinfo_read_dbvalues` (:13934, :13974) 뿐. | **thread param → WITHOUT** |
| `query_executor.c:14502` | locator_lock_and_get_object_with_evaluation | (WITH in getter) | **flip** | increment(click counter) attr-layer. | **thread param → WITHOUT** |
| `scan_manager.c:5931` | heap_next | WITHOUT | unchanged | heap scan → filter/attr-layer (:5980). | keep |
| `scan_manager.c:5937` | heap_next_sampling | WITHOUT | unchanged | sampling scan, 동일 경로. | keep |
| `scan_manager.c:5954` | heap_prev | WITHOUT | unchanged | reverse scan, 동일 경로. | keep |
| `scan_manager.c:6816` | heap_get_visible_version | WITHOUT | unchanged | non-covering index heap lookup → filter (:6844). | keep |
| `scan_manager.c:6050` / `:6869` | locator getters | (WITH in getter) | **flip** | lock-fetch 후 동일 tuple pipeline (attr-layer). | **thread param → WITHOUT** |
| `scan_manager.c:5057/5061/5919` | heap_scanrange_* | (WITH inside) | mixed→**flip** | grouped scan, attr-layer 전용. | **scanrange 내부 → WITHOUT** |
| `serial.c:218` / `:535` / `:671` | heap_get_visible_version | WITH | **flip** | attr-layer (:247/:557/:693). serial record 는 OOS 불가(소형)라 runtime no-op 이지만 계약 표기가 틀림. | **→ WITHOUT** |
| `px_scan_index_leaf_slot_walker.cpp:456` | heap_scan_get_visible_version | WITHOUT | unchanged | 병렬 non-covering index heap fetch → filter (:481). | keep |
| `px_scan_slot_iterator.cpp:106` | heap_next_1page | (WITH inside, `heap_file.c:8473`) | **flip** | 병렬 heap scan, attr-layer. | **내부 → WITHOUT** |

### src/sp, src/executables, src/storage (utilities & catalog)

| Caller | API | Policy | vs base | Review reason | Correction |
|---|---|---|---|---|---|
| `sp_code.cpp:91` | heap_get_visible_version | WITH | **flip** | attr-layer (:128). SP code(자바 바이트코드)는 4KB 초과 가능 → 실제 비용 발생. | **→ WITHOUT** |
| `compactdb.c:565` | heap_get_visible_version | WITH | **flip** | recdes=NULL, 참조 OID 존재 확인 전용. | **→ WITHOUT** |
| `compactdb.c:781` | heap_init_get_context (+ heap_get_last_version) | WITH | **flip (의도된 수정)** | SA compactdb 의 old record 가 OOS-blind raw 디코더로 감 — 이 PR 이 고치는 CBRD-26948 계열 stub 누출. | keep |
| `compactdb_sr.c:110` | heap_get_visible_version | WITH | **flip** | recdes=NULL, class 존재 확인 전용. | **→ WITHOUT** |
| `compactdb_sr.c:215` | locator_lock_and_get_object | (WITH in getter) | **flip (의도된 수정)** | old record → `locator_attribute_info_force` 재기록 경로. 보수적으로 raw-safe 필요. | **thread param → WITH** |
| `btree_load.c:3724` | heap_next | WITHOUT | unchanged | index build key gen, attr-layer. | keep |
| `btree_load.c:5372` | visible-version fetch | WITHOUT | unchanged | online index build, filter/key attr-layer (:5392). | keep |
| `btree_load.c:3417` | heap_next_1page | (WITH inside) | **flip** | 병렬 index sort, attr-layer. | **내부 → WITHOUT** |
| `catalog_class.c:4014` | heap_get_visible_version | WITH | rename | `catcls_delete_instance` — `catcls_get_or_value_from_record` raw `or_*` parse (:4021). CBRD-26847 census 의 "정말 필요한 5곳" 중 하나. | keep |
| `catalog_class.c:4180` | heap_get_visible_version | WITH | rename | `catcls_update_instance` — or_chn + raw parse (:4187). census 필수. | keep |
| `catalog_class.c:4504` | heap_get_visible_version | WITH | rename | `catcls_update_class_stats` — raw parse (:4510). census 필수. | keep |
| `catalog_class.c:5015` | heap_next | WITHOUT | unchanged | server compat 메타데이터, attr-layer (:5019). | keep |
| `catalog_class.c:5467` | heap_next | WITHOUT | unchanged | collation 메타데이터, attr-layer (:5472). | keep |
| `catalog_class.c:5678` | heap_next | WITHOUT | unchanged | apply-info 메타데이터, attr-layer (:5682). | keep |
| `system_catalog.c:4719` | heap_next | WITH | flip (no-op) | root-class scan, `or_class_name()` raw parse (:4722). class record 는 현재 OOS 불가 → no-op 이지만 raw 소비 표기로서 정직. | keep |
| `system_catalog.c:5031` | heap_next | WITH | flip (no-op) | catalog dump, `or_class_name()` (:5034). 동일. | keep |

### src/storage/heap_file.c (internal)

| Caller | API | Policy | vs base | Review reason | Correction |
|---|---|---|---|---|---|
| `heap_file.c:8473` | heap_next_1page 내부 fetch | WITH | **flip** | 호출자 2곳 모두 attr-layer (px_scan, btree_load 병렬). | **→ WITHOUT** |
| `heap_file.c:8548` | heap_first → heap_next | WITH | flip (no-op급) | 범용 API; `tde.c:584` raw memcpy 소비자 존재 → 보수적 WITH 유지. | keep (문서화) |
| `heap_file.c:8576` | heap_last → heap_prev | WITH | flip (no-op급) | 외부 소비자 없음(내부 scanrange 만). heap_first 와 대칭 유지. | keep (문서화) |
| `heap_file.c:8739–9133` (13 sites) | heap_scanrange_* 내부 fetch | WITH | visible-version 3곳 rename, next/prev fallback 10곳 **flip** | 소비자는 grouped scan attr-layer 뿐. | **전부 → WITHOUT** |
| `heap_file.c:9342` | heap_is_object_not_null 내부 | WITH | **flip** | recdes=NULL 존재 확인. | **→ WITHOUT** |
| `heap_file.c:15786` | heap_next (heap dump) | WITHOUT | unchanged | `heap_attrinfo_read_dbvalues()` (:15791). | keep |
| `heap_file.c:20351/20401` | record_info 내부 | WITHOUT | unchanged | record-info 진단, 메타데이터 소비. | keep |
| `heap_file.c:27163` | heap_get_class_record 내부 | WITH | flip (no-op) | class record 소비자는 `or_class_*` raw parse — 정직한 표기, 실행은 no-op. | keep |

### src/transaction

| Caller | API | Policy | vs base | Review reason | Correction |
|---|---|---|---|---|---|
| `locator_sr.c:303` | heap_next | WITH | flip (no-op) | `locator_initialize` — `or_class_name()` raw parse (:307). class record 전용. | keep |
| `locator_sr.c:1976` | heap_next | WITH | flip (no-op) | `locator_check_class_names` — `or_class_name()` (:1978). | keep |
| `locator_sr.c:2909` | heap_next | WITH | rename | **`xlocator_fetch_all`** — raw record 를 `LC_COPYAREA` 로 클라이언트 전송 (:2916–2927). census 필수. | keep |
| `locator_sr.c:3496` | heap_get_visible_version | WITH | rename | `locator_all_reference_lockset` — reference 추출 raw parse. census 정리 후보 (CBRD-26847 로 이연). | keep |
| `locator_sr.c:5808` / `:5951` | heap_get_visible_version | WITH | rename | `locator_update_force` old-record fetch. attr-layer 소비로 보이나 base 동작 보존; census 정리 후보 (이연). | keep |
| `locator_sr.c:6589` | heap_get_visible_version | WITH | rename | `locator_delete_lob_force` — `heap_attrinfo_delete_lob` (attr-layer). census 정리 후보 (이연). | keep |
| `locator_sr.c:6953` | heap_get_visible_version | WITH | rename | `locator_repl_prepare_force` — old record PEEK, or_chn 등. base 동작 보존. | keep |
| `locator_sr.c:7611` | heap_init_get_context (+ heap_get_last_version) | WITH | **flip** | `locator_attribute_info_force` — old record 는 attr-layer 소비 (update/delete force). census: last-version fetch 는 expand 불필요. | **→ WITHOUT** |
| `locator_sr.c:9154` | heap_next | WITHOUT | unchanged | `xlocator_remove_class_from_index` — attr-layer (:9174). | keep |
| `locator_sr.c:9609` | heap_next | WITHOUT | unchanged | `locator_check_btree_entries` — attr-layer (:9632). | keep |
| `locator_sr.c:10064` | heap_next | WITHOUT | unchanged | `locator_check_unique_btree_entries` — attr-layer (:10082). | keep |
| `locator_sr.c:10777` | heap_next | WITH | flip (no-op) | `locator_check_all_entries_of_all_btrees` — `or_class_hfid()` raw parse (:10783). class record 전용. | keep |
| `locator_sr.c:11962` | heap_next | WITHOUT | unchanged | FK validity — `heap_attrinfo_generate_key` (:11965). | keep |
| `locator_sr.c:12116` | heap_next | WITHOUT | unchanged | `xlocator_lock_and_fetch_all` locking branch — OID advance 후 :12141 에서 expand 재fetch. | keep |
| `locator_sr.c:12141` | heap_get_visible_version | WITH | rename | 잠금 후 재fetch → `LC_COPYAREA` 전송 (:12168–). census 필수. | keep |
| `locator_sr.c:12156` | heap_next | WITH | rename | 비잠금 fetch-all → `LC_COPYAREA` 전송. census 필수. | keep |
| `locator_sr.c:13036` | heap_get_visible_version | WITH | rename | **`redistribute_partition_data`** — `locator_insert_force` 재삽입 (:13048). census 필수. | keep |
| `locator_sr.c:13324` | heap_init_get_context (getter 내부) | WITH | **flip** | `locator_lock_and_get_object_with_evaluation` — 소비자 혼합 (scan/qexec attr-layer). | **thread param** |
| `locator_sr.c:13457` | heap_init_get_context (getter 내부) | WITH | **flip** | `locator_get_object` — qexec obj-fetch attr-layer. | **thread param** |
| `locator_sr.c:13558` | heap_init_get_context (getter 내부) | WITH | **flip** | `locator_lock_and_get_object` — compactdb_sr 재기록(raw-safe 필요) + attr-layer 소비자 혼합. | **thread param** |
| `locator_sr.c:13794` | heap_get_visible_version | WITH | rename | `locator_mvcc_reeval_scan_filters` — PEEK + attr-layer (:13810). census 정리 후보 (이연). | keep |
| `lock_manager.c:5644` | heap_get_visible_version | WITH | **flip** | 소비는 `or_mvcc_get_header()` (:5647) — header 는 variable area 밖이라 expand 불필요. | **→ WITHOUT** |

## Verified Findings (2026-07-06 전수 검증 요약)

1. **Data corruption 0건** — 모든 WITHOUT site 는 attr-layer 또는 recdes 미소비로 검증됨.
2. **PR 이 유발한 성능 flip** — base 는 expand 하지 않던 attr-layer 경로가 WITH 로 바뀐 곳:
   locator getter 3곳(내부 고정), `locator_attribute_info_force`, `heap_next_1page`(병렬 스캔!), scanrange
   next/prev fallback, serial ×3, sp_code, load_server_loader:247, lock_manager, 존재-확인 3곳(recdes NULL).
   → 수정안은 `CBRD-27029-correction-plan.md`.
3. **의도된 flip (이 PR 의 목적)** — `compactdb.c:781`, `compactdb_sr.c:215`(getter 경유): base 에서 OOS stub 이
   raw 디코더로 새던 CBRD-26948 계열 누출을 고침.
4. **census(CBRD-26847) 필수 Expand 5곳 모두 WITH 유지 확인** — `xlocator_lock_and_fetch_all`,
   `redistribute_partition_data`, `catcls_delete_instance`, `catcls_update_instance`, `catcls_update_class_stats`.
5. base 에 있던 `TODO (CBRD-26847)` audit 주석이 wrapper 삭제와 함께 사라짐 — enum 정의부에 재부착 권고.

## Reviewer Checklist

- `HEAP_WITH_OOS_EXPAND` row: caller consumes raw `RECDES` bytes, or the wrapper/helper passes an explicit raw-record-safe policy.
- `HEAP_WITHOUT_OOS_EXPAND` row: an attribute-layer read follows before OOS values are interpreted, or the recdes is not consumed.
- **vs base 가 flip 인 row**: 그 flip 이 의도된 수정(누출 fix)인지, 우발적 성능 회귀인지 판정했는가.
- Removed wrapper names do not remain in source.
- Visible-version helpers only pass the caller-selected enum policy through `HEAP_GET_CONTEXT`; they do not change unrelated MVCC behavior.
- 정책을 내부 고정한 API 목록(위 표)이 최신인가.

## Verification

- `git diff --check`
- `just build` (debug_gcc) — build/install 성공
- Call-site 전수 grep: 6개 정책 API 의 모든 호출부가 정책 인자를 전달함 (dead/#ifdef 코드 포함 누락 0건)
- PR #7416 medium 실패 6건 (`fview1.sql` 등)은 testcase revision 불일치로 분류 (PR body 참고)
