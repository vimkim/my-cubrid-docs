# CBRD-27029 Expand Raw Records

Review anchor: **PR #7416** (base `feat/oos`), HEAD `846b5c7cf` (`[CBRD-27029] Stop expanding attr-layer fetches inherited as WITH and scanrange boundaries`).

PR 는 6개 커밋으로 진화했다. 최종 상태만이 계약이다:

1. `e1ff2fb9d` — expand 를 기본값으로 뒤집고 `*_skip_oos_expand` opt-out wrapper 를 추가 (폐기된 접근).
2. `c5186d168` — `heap_next` 계열에 `HEAP_OOS_EXPAND_POLICY` enum 인자 도입, wrapper 제거 시작.
3. `3b4b90f40` — `heap_get_visible_version`, `heap_scan_get_visible_version`, `heap_init_get_context` 까지 enum 확장, 모든 wrapper 제거 완료.
4. `400a0e791` — 교정 커밋: locator getter 3종에 정책 인자 스레딩 + attr-layer/미소비 site 의 불필요한 WITH 를 WITHOUT 으로 정리 (아래 Correction 컬럼 *done* 표기). (동일 subject 의 `6f6519c25` 는 rebase 전 hash — 문서/JIRA 에서 참조 금지.)
5. `c33d0ff84` — compactdb old-record fetch 를 WITHOUT 으로 정정.
6. `846b5c7cf` — 상속된 attr-layer/header-only WITH 6곳을 WITHOUT 으로 flip + scanrange NULL-OID boundary 를 `heap_first`/`heap_last` 경유 대신 inline `heap_next`/`heap_prev` WITHOUT 으로 정리 (2026-07-06 correction report 반영).

> 이 문서의 라인 번호는 모두 `846b5c7cf` 기준으로 재생성했다. 검증: 2026-07-06, call site 전수 조사 (~55곳) + base(`origin/feat/oos`) 대비 동작 diff.
> 2026-07-06 correction plan 의 결정 사항 반영 완료. 이후 correction report (codex) 가 correction plan 의 "6곳 census 이연" 결정을 뒤집어 `846b5c7cf` 에서 flip 했다 (아래 "Verified Findings" 참고).

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

## Changed Public APIs (at HEAD `846b5c7cf`)

| Function | Change |
|---|---|
| `heap_next()` | Adds `HEAP_OOS_EXPAND_POLICY oos_expand_policy`. |
| `heap_next_sampling()` | Adds `HEAP_OOS_EXPAND_POLICY oos_expand_policy`. |
| `heap_prev()` | Adds `HEAP_OOS_EXPAND_POLICY oos_expand_policy`. |
| `heap_get_visible_version()` | Adds `HEAP_OOS_EXPAND_POLICY oos_expand_policy`. |
| `heap_scan_get_visible_version()` | Adds `HEAP_OOS_EXPAND_POLICY oos_expand_policy`. |
| `locator_lock_and_get_object()` | Adds `HEAP_OOS_EXPAND_POLICY oos_expand_policy` (`400a0e791`) — 소비자가 혼합이라 getter 내부에 고정하지 않고 caller 가 선언. |
| `locator_lock_and_get_object_with_evaluation()` | Adds `HEAP_OOS_EXPAND_POLICY oos_expand_policy` (`400a0e791`). |
| `locator_get_object()` | Adds `HEAP_OOS_EXPAND_POLICY oos_expand_policy` (`400a0e791`). |
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
| `heap_first()` / `heap_last()` | `HEAP_WITH_OOS_EXPAND` (`heap_file.c:8549/8578`, 주석 부착) | 범용 "레코드 하나 주세요" API. 호출자 중 raw 소비자 존재 → 보수적 WITH 유지 (결정: 2026-07-06): `tde.c:584` raw memcpy, `boot_sr.c:310` caller-owned `BOOT_DB_PARM` buffer 로 raw COPY (둘 다 OOS 불가 record 라 실행은 no-op). **수용된 perf leftover**: attr-layer 호출자 `dblink_global_tran_catalog.c:198/:421` 과 존재-확인 전용 `heap_file.c:18080` 은 불필요하게 expand 됨 — 정책 인자 스레딩은 CBRD-26847 census 로 이연 (결정, 누락 아님). scanrange boundary 는 `846b5c7cf` 부터 이 API 를 경유하지 않는다; `heap_last` 는 현재 호출자 0곳 (대칭 API 로 유지). |
| `heap_next_record_info()` / `heap_prev_record_info()` | `HEAP_WITHOUT_OOS_EXPAND` | record-info 진단 스캔 (`heap_file.c:20364/20414`); 메타데이터만 소비. |
| `heap_next_1page()` | `HEAP_WITHOUT_OOS_EXPAND` (`heap_file.c:8473`) | *done* (`400a0e791`). 호출자 2곳 모두 attr-layer: `px_scan_slot_iterator.cpp:106` (병렬 heap scan), `btree_load.c:3417` (병렬 index build). |
| `heap_scanrange_*` | `HEAP_WITHOUT_OOS_EXPAND` (15 sites, `heap_file.c:8738–9145`, 블록 주석 부착) | *done* (`400a0e791` + `846b5c7cf`). 외부 소비자는 `scan_manager.c:5057/5061/5919` grouped scan 뿐 (attr-layer). NULL-OID boundary 분기도 `846b5c7cf` 에서 `heap_first`/`heap_last`(WITH) 경유 대신 inline `heap_next`/`heap_prev` WITHOUT 으로 정리 — 현재 호출자는 NULL 을 넘겨 이 분기를 타지 않지만 계약을 코드와 일치시켰다. 15 sites 중 4곳은 disabled `ENABLE_UNUSED_FUNCTION` 블록 내부. |
| `locator_lock_and_get_object()` / `locator_get_object()` / `locator_lock_and_get_object_with_evaluation()` | (고정 해제) | *done* (`400a0e791`) — 정책 인자를 signature 로 스레딩 (`locator_sr.c:13328/13463/13564` 에서 caller 정책 사용). 호출부 분류는 아래 "Locator getter 호출부 분류" 표. |

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

전수 조사 결과 (HEAD `846b5c7cf`, ~55 call sites). 컬럼 설명:

- **vs base**: `origin/feat/oos` 대비 실효 동작. *rename* = base 에서 이미 `*_expand_oos` (동작 동일),
  *unchanged* = base plain call 과 동작 동일, **flip** = base 대비 실효 동작이 바뀜 (의도된 수정만 잔존).
- **Correction**: 2026-07-06 correction plan/report 의 결정 사항. *keep* = 그대로 둠, *done* = 해당 커밋에서 반영 완료 (hash 미표기 시 `400a0e791`).

### 판정 기준 재확인

`HEAP_WITHOUT_OOS_EXPAND` 로 확인된 모든 site 는 attr-layer 소비 또는 recdes 미소비로 검증됐다.
**raw-byte 소비인데 WITHOUT 인 data-corruption 사례는 0건.** 문제는 전부 반대 방향(불필요한 WITH)이었고, `400a0e791`/`c33d0ff84`/`846b5c7cf` 에서 정리했다.

### Locator getter 호출부 분류 (12 sites, `400a0e791` 에서 정책 명시)

getter 3종이 정책 인자를 받게 되면서 전 호출부를 분류했다. WITH row 는 raw-byte 소비자를 명기한다.

| Caller | Getter | Policy | Evidence |
|---|---|---|---|
| `scan_manager.c:6050` | with_evaluation | WITHOUT | heap-scan lock-fetch; recdes 는 `:5930` plain `heap_next` 와 동일한 predicate/val-list attr-layer pipeline 으로 소비. |
| `scan_manager.c:6870` | with_evaluation | WITHOUT | index-scan lock-fetch; 동일 attr-layer pipeline. |
| `query_executor.c:14502` | with_evaluation | WITHOUT | increment(click counter); attr-layer. recdes 인자 NULL. |
| `locator_sr.c:5803` | with_evaluation | WITHOUT | `locator_update_force` locking branch; old record → attrinfo index key. base 도 이 branch 는 expand 안 함. (비잠금 `:5811` 과의 비대칭은 `846b5c7cf` 에서 해소 — 두 branch 모두 WITHOUT.) |
| `locator_sr.c:6294` | with_evaluation | **WITH** | `locator_delete_force_internal`: class-delete branch 가 recdes 를 `or_class_name()` 으로 raw 파싱 (`:6349`) — OOS-blind `or_*` parse. instance branch 는 attr-layer 지만 혼합 소비라 ambiguity rule 로 WITH. |
| `query_executor.c:13803` | get_object | WITHOUT | obj-fetch; `oRec` 소비는 `heap_attrinfo_read_dbvalues` 뿐. |
| `locator_sr.c:2336` | get_object | **WITH** | `locator_lock_and_return_object`: recdes 를 `LC_COPYAREA` 로 클라이언트 전송 — raw bytes. base 대비 의도된 개선: client-fetch expansion gap (CBRD-26948) 일부 해소. 호출자 5곳 (`:2521`, `:2594`, `:3156`, `:3250`, `:11645`) 커버. |
| `locator_sr.c:3961` | get_object | WITHOUT | recdes 인자 NULL; lock/존재 확인 전용. |
| `compactdb_sr.c:215` | lock_and_get | WITHOUT | old record 는 `locator_attribute_info_force` → `locator_update_index` 로 흐르며, 소비는 attr-layer/OOS Resolve 기반이다. compactdb 의 heap page cleanup 과 무관하므로 record-level Expand 불필요. |
| `locator_sr.c:4442` | lock_and_get | WITHOUT | `locator_check_primary_key_delete` (FK): CASCADE branch 는 `locator_delete_force` 로 재fetch; SET NULL branch 는 recdes 를 oldrecdes 로 `locator_attribute_info_force` 에 전달 = attr-layer. |
| `locator_sr.c:4798` | lock_and_get | WITHOUT | `locator_check_primary_key_update` (FK SET NULL): `:4442` 와 동일한 attr-layer 소비. |
| `locator_sr.c:7633` | lock_and_get | WITHOUT | `locator_attribute_info_force` last-committed-version retry; oldrecdes → attr-layer (`:7613` 과 동일 근거). |

### src/connection, src/loaddb, src/query

| Caller | API | Policy | vs base | Review reason | Correction |
|---|---|---|---|---|---|
| `connection_support.cpp:2471` | heap_next | WITHOUT | unchanged | `heap_attrinfo_read_dbvalues()` (:2474). | keep |
| `load_server_loader.cpp:243` | heap_next | WITHOUT | unchanged | OID advance 전용; recdes 는 다음 fetch 가 다시 바인딩. | keep |
| `load_server_loader.cpp:246` | heap_get_visible_version | WITHOUT | unchanged | 소비는 `heap_attrinfo_read_dbvalues()` (:260) 뿐. | *done* |
| `dblink_global_tran_catalog.c:225` | heap_next | WITHOUT | unchanged | attr-layer 디코드. | keep |
| `dblink_global_tran_catalog.c:481` | heap_next | WITHOUT | unchanged | attr-layer 디코드. | keep |
| `query_executor.c:10730` | heap_get_visible_version | WITHOUT | unchanged | UPDATE LOB cleanup, attr-layer (:10737). | keep |
| `query_executor.c:11540` | heap_get_visible_version | WITHOUT | unchanged | DELETE LOB cleanup, attr-layer (:11547). | keep |
| `query_executor.c:12375` | heap_get_visible_version | WITHOUT | unchanged | duplicate-key update, attr-layer (:12397). | keep |
| `query_executor.c:13803` | locator_get_object | WITHOUT | unchanged | `oRec` 소비는 `heap_attrinfo_read_dbvalues` (:13934, :13974) 뿐. | *done* (param threaded) |
| `query_executor.c:14502` | locator_lock_and_get_object_with_evaluation | WITHOUT | unchanged | increment(click counter) attr-layer. | *done* (param threaded) |
| `scan_manager.c:5931` | heap_next | WITHOUT | unchanged | heap scan → filter/attr-layer (:5980). | keep |
| `scan_manager.c:5937` | heap_next_sampling | WITHOUT | unchanged | sampling scan, 동일 경로. | keep |
| `scan_manager.c:5954` | heap_prev | WITHOUT | unchanged | reverse scan, 동일 경로. | keep |
| `scan_manager.c:6816` | heap_get_visible_version | WITHOUT | unchanged | non-covering index heap lookup → filter (:6844). | keep |
| `scan_manager.c:6050` / `:6870` | locator getters | WITHOUT | unchanged | lock-fetch 후 동일 tuple pipeline (attr-layer). | *done* (param threaded) |
| `scan_manager.c:5057/5061/5919` | heap_scanrange_* | (WITHOUT inside) | unchanged | grouped scan, attr-layer 전용. | *done* |
| `serial.c:217` / `:534` / `:670` | heap_get_visible_version | WITHOUT | unchanged | attr-layer (:247/:557/:693). serial record 는 OOS 불가(소형)라 runtime no-op 이지만 계약 표기 정정. | *done* |
| `px_scan_index_leaf_slot_walker.cpp:455` | heap_get_visible_version | WITHOUT | unchanged | 병렬 non-covering index heap fetch → filter (:481). | keep |
| `px_scan_slot_iterator.cpp:106` | heap_next_1page | (WITHOUT inside, `heap_file.c:8473`) | unchanged | 병렬 heap scan, attr-layer. | *done* |

### src/sp, src/executables, src/storage (utilities & catalog)

| Caller | API | Policy | vs base | Review reason | Correction |
|---|---|---|---|---|---|
| `sp_code.cpp:90` | heap_get_visible_version | WITHOUT | unchanged | attr-layer (:128). SP code(자바 바이트코드)는 4KB 초과 가능 → 실제 perf 회복. | *done* |
| `compactdb.c:565` | heap_get_visible_version | WITHOUT | unchanged | recdes=NULL, 참조 OID 존재 확인 전용. | *done* |
| `compactdb.c:782` | heap_init_get_context (+ heap_get_last_version) | WITHOUT | unchanged | SA compactdb index update 의 old record 는 `locator_update_index` 에서 attr-layer/OOS Resolve 로 소비된다. caller-owned fixed buffer 에 record-level Expand 를 시도하면 불필요한 `oos_read`/`S_DOESNT_FIT` risk 만 생김. | *done* |
| `compactdb_sr.c:109` | heap_get_visible_version | WITHOUT | unchanged | recdes=NULL, class 존재 확인 전용. | *done* |
| `compactdb_sr.c:215` | locator_lock_and_get_object | WITHOUT | unchanged | old record → `locator_attribute_info_force` → `locator_update_index`; attr-layer/OOS Resolve 소비. compactdb heap cleanup 은 별도 physical page path 라 Expand 불필요. | *done* (param threaded, WITHOUT) |
| `btree_load.c:3724` | heap_next | WITHOUT | unchanged | index build key gen, attr-layer. | keep |
| `btree_load.c:5372` | visible-version fetch | WITHOUT | unchanged | online index build, filter/key attr-layer (:5392). | keep |
| `btree_load.c:3417` | heap_next_1page | (WITHOUT inside) | unchanged | 병렬 index sort, attr-layer. | *done* |
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
| `heap_file.c:8472` | heap_next_1page 내부 fetch | WITHOUT | unchanged | 호출자 2곳 모두 attr-layer (px_scan, btree_load 병렬). | *done* |
| `heap_file.c:8549` | heap_first → heap_next | WITH | flip (no-op급) | 범용 API; `tde.c:584` raw memcpy, `boot_sr.c:310` raw COPY 소비자 존재 → 보수적 WITH 유지, 코드 주석 부착. | keep (문서화 *done*) |
| `heap_file.c:8578` | heap_last → heap_prev | WITH | flip (no-op급) | 호출자 0곳 (`846b5c7cf` 에서 scanrange boundary 가 이탈). heap_first 와 대칭 유지, 코드 주석 부착. | keep (문서화 *done*) |
| `heap_file.c:8738–9145` (15 sites) | heap_scanrange_* 내부 fetch | WITHOUT | unchanged | 소비자는 grouped scan attr-layer 뿐. 블록 주석 부착. NULL-OID boundary 2곳은 `846b5c7cf` 에서 inline heap_next/heap_prev WITHOUT 으로 전환 (base 는 heap_first/heap_last 경유 — 당시 정책 인자 없음). 4곳은 disabled `ENABLE_UNUSED_FUNCTION` 내부. | *done* (`400a0e791` + `846b5c7cf`) |
| `heap_file.c:9355` | heap_is_object_not_null 내부 | WITHOUT | unchanged | recdes=NULL 존재 확인. | *done* |
| `heap_file.c:15798` | heap_next (heap dump) | WITHOUT | unchanged | `heap_attrinfo_read_dbvalues()`. | keep |
| `heap_file.c:20364/20414` | record_info 내부 | WITHOUT | unchanged | record-info 진단, 메타데이터 소비. | keep |
| `heap_file.c:27176` | heap_get_class_record 내부 | WITH | flip (no-op) | class record 소비자는 `or_class_*` raw parse — 정직한 표기, 실행은 no-op. | keep |

### src/transaction

| Caller | API | Policy | vs base | Review reason | Correction |
|---|---|---|---|---|---|
| `locator_sr.c:303` | heap_next | WITH | flip (no-op) | `locator_initialize` — `or_class_name()` raw parse (:307). class record 전용. | keep |
| `locator_sr.c:1976` | heap_next | WITH | flip (no-op) | `locator_check_class_names` — `or_class_name()` (:1978). | keep |
| `locator_sr.c:2909` | heap_next | WITH | rename | **`xlocator_fetch_all`** — raw record 를 `LC_COPYAREA` 로 클라이언트 전송 (:2916–2927). census 필수. | keep |
| `locator_sr.c:3496` | heap_get_visible_version | WITHOUT | **flip** | `locator_all_reference_lockset` — 소비는 `heap_get_referenced_by()` 뿐이고, 그 내부는 `heap_attrinfo_read_dbvalues()` (`heap_file.c:14870`) attr-layer 디코드다 (이전 판의 "raw parse" 표기는 오판정). | *done* (`846b5c7cf`) |
| `locator_sr.c:5811` / `:5954` | heap_get_visible_version | WITHOUT | **flip** | `locator_update_force` old-record fetch. oldrecdes 소비는 `or_mvcc_get_header()` (header) 와 `locator_update_index()` → `heap_attrinfo_read_dbvalues()` (`:8517`) 뿐. locking branch `:5803` 과 대칭 회복. | *done* (`846b5c7cf`) |
| `locator_sr.c:6592` | heap_get_visible_version | WITHOUT | **flip** | `locator_delete_lob_force` — 소비는 `heap_attrinfo_delete_lob()` → `heap_attrvalue_read()` (attr-layer, inline-OOS 는 `heap_attrvalue_read_oos_inline` 로 Resolve). | *done* (`846b5c7cf`) |
| `locator_sr.c:6956` | heap_get_visible_version | WITHOUT | **flip** | `locator_repl_prepare_force` — old record PEEK 소비는 `or_chn()` (`:6971`) header-only; 호출자 `xlocator_repl_force` 는 update 에 oldrecdes=NULL 을 전달해 재사용 없음. | *done* (`846b5c7cf`) |
| `locator_sr.c:7613` | heap_init_get_context (+ heap_get_last_version) | WITHOUT | unchanged | `locator_attribute_info_force` — old record 는 attr-layer 소비 (update/delete force). census: last-version fetch 는 expand 불필요. | *done* |
| `locator_sr.c:9157` | heap_next | WITHOUT | unchanged | `xlocator_remove_class_from_index` — attr-layer. | keep |
| `locator_sr.c:9612` | heap_next | WITHOUT | unchanged | `locator_check_btree_entries` — attr-layer. | keep |
| `locator_sr.c:10067` | heap_next | WITHOUT | unchanged | `locator_check_unique_btree_entries` — attr-layer. | keep |
| `locator_sr.c:10780` | heap_next | WITH | flip (no-op) | `locator_check_all_entries_of_all_btrees` — `or_class_hfid()` raw parse. class record 전용. | keep |
| `locator_sr.c:11965` | heap_next | WITHOUT | unchanged | FK validity — `heap_attrinfo_generate_key`. | keep |
| `locator_sr.c:12119` | heap_next | WITHOUT | unchanged | `xlocator_lock_and_fetch_all` locking branch — OID advance 후 :12144 에서 expand 재fetch. | keep |
| `locator_sr.c:12144` | heap_get_visible_version | WITH | rename | 잠금 후 재fetch → `LC_COPYAREA` 전송. census 필수. | keep |
| `locator_sr.c:12159` | heap_next | WITH | rename | 비잠금 fetch-all → `LC_COPYAREA` 전송. census 필수. | keep |
| `locator_sr.c:13039` | heap_get_visible_version | WITH | rename | **`redistribute_partition_data`** — `locator_insert_force` 재삽입. census 필수. | keep |
| `locator_sr.c:13328` | heap_init_get_context (getter 내부) | caller 정책 | unchanged | `locator_lock_and_get_object_with_evaluation` — 소비자 혼합 → caller 가 선언. | *done* (param threaded) |
| `locator_sr.c:13463` | heap_init_get_context (getter 내부) | caller 정책 | unchanged | `locator_get_object` — 소비자 혼합 (LC_COPYAREA 전송 vs attr-layer) → caller 가 선언. | *done* (param threaded) |
| `locator_sr.c:13564` | heap_init_get_context (getter 내부) | caller 정책 | unchanged | `locator_lock_and_get_object` — copyarea/raw-byte 소비자와 attr-layer 소비자가 혼합되어 caller 가 선언한다. compactdb_sr 는 attr-layer 소비자로 WITHOUT. | *done* (param threaded) |
| `locator_sr.c:13800` | heap_get_visible_version | WITHOUT | **flip** | `locator_mvcc_reeval_scan_filters` — PEEK 후 소비는 `heap_attrinfo_read_dbvalues()` (`:13816`) 와 filter 재평가 (attr-layer). | *done* (`846b5c7cf`) |
| `lock_manager.c:5644` | heap_get_visible_version | WITHOUT | unchanged | 소비는 `or_mvcc_get_header()` (:5647) — header 는 variable area 밖이라 expand 불필요. | *done* |

## Verified Findings (2026-07-06 전수 검증 요약; 교정은 `400a0e791`/`c33d0ff84`/`846b5c7cf` 반영 완료)

1. **Data corruption 0건** — 모든 WITHOUT site 는 attr-layer 또는 recdes 미소비로 검증됨.
2. **PR 이 유발했던 성능 flip — 전부 교정됨 (`400a0e791`)** — base 는 expand 하지 않던 attr-layer 경로가 WITH 로
   바뀌었던 곳: locator getter 3곳(→ 정책 인자 스레딩), `locator_attribute_info_force`, `heap_next_1page`(병렬 스캔!),
   scanrange, serial ×3, sp_code, load_server_loader, lock_manager, 존재-확인 3곳(recdes NULL). 모두 WITHOUT.
   수용된 잔여 leftover 는 `heap_first` 경유 3곳뿐 (위 고정 정책 표 참고; CBRD-26847 이연 결정).
3. **의도된 flip (이 PR 의 목적)** — `locator_sr.c:2336`(`locator_lock_and_return_object` → `LC_COPYAREA`):
   base 에서 OOS stub 이 raw 디코더/클라이언트로 새던 CBRD-26948 계열 누출을 고침. compactdb old-record
   fetches 는 attr-layer/index 소비라 WITHOUT 으로 정정함 (`c33d0ff84`).
4. **base 유래 불필요 WITH 6곳 — flip 완료 (`846b5c7cf`)** — correction plan 은 base 동작 보존을 이유로
   CBRD-26847 census 이연을 결정했으나, correction report (codex, 2026-07-06) 가 소비자 재검증 후 뒤집었다:
   `locator_sr.c:3496`/`:5811`/`:5954`/`:6592`/`:6956`/`:13800` 전부 attr-layer 또는 header-only 소비자로 확인
   (위 transaction 표의 근거 컬럼). scanrange NULL-OID boundary 2곳도 같은 커밋에서 WITHOUT 계약에 편입.
5. **census(CBRD-26847) 필수 Expand 5곳 모두 WITH 유지 확인** — `xlocator_lock_and_fetch_all`,
   `redistribute_partition_data`, `catcls_delete_instance`, `catcls_update_instance`, `catcls_update_class_stats`.
6. base 에 있던 `TODO (CBRD-26847)` audit 주석 — enum 정의부(`heap_file.h:361`)에 재부착 완료 (`400a0e791`).

## Reviewer Checklist

- `HEAP_WITH_OOS_EXPAND` row: caller consumes raw `RECDES` bytes, or the wrapper/helper passes an explicit raw-record-safe policy.
- `HEAP_WITHOUT_OOS_EXPAND` row: an attribute-layer read follows before OOS values are interpreted, or the recdes is not consumed.
- **vs base 가 flip 인 row**: 그 flip 이 의도된 수정(누출 fix)인지, 우발적 성능 회귀인지 판정했는가.
- Removed wrapper names do not remain in source.
- Visible-version helpers only pass the caller-selected enum policy through `HEAP_GET_CONTEXT`; they do not change unrelated MVCC behavior.
- 정책을 내부 고정한 API 목록(위 표)이 최신인가.

## Verification (at `846b5c7cf`)

- `git diff --check`
- `just build-test` (debug_gcc) — build/install + unit tests 23/23 성공
- Call-site 전수 grep: 6개 정책 API + locator getter 3종의 모든 **활성** 호출부가 정책 인자를 전달함;
  `_expand_oos`/`_skip_oos_expand` 잔존 0건; `POLICY_INVALID` 전달 0건.
  **예외 (out of scope 결정)**: disabled `#if defined (ENABLE_UNUSED_FUNCTION)` 블록 안의 legacy `heap_get()`
  호출 6곳 (`heap_file.c:8600/9029/9095/9140`, `system_catalog.c:3770/4066`) 은 정책 인자가 없다 —
  `heap_get()` 자체가 이미 제거된 API 라 이 블록은 활성화해도 컴파일되지 않는 죽은 코드다. 변환하지 않는다.
- CI code-style (indent 2.2.11 / astyle + pre-commit codestyle hook) 통과
- SA-mode 동작 spot check (at `846b5c7cf`): OOS row (`BIT VARYING` 10000B, index 포함) 에 대해 INSERT,
  indexed-column UPDATE (flip 된 `locator_update_force` old-record 경로 통과), SELECT round-trip(md5),
  DELETE, `cubrid compactdb -S` 후 md5 불변, `cubrid checkdb -S` exit 0 확인.
  serial next_value ×2 와 `cubrid unloaddb -S` full `X'..'` emission 은 pre-rebase head (`6f6519c25` 내용 기준)
  에서 통과 — 이후 커밋은 attr-layer fetch 의 expand 억제만 바꿈.
- PR #7416 medium 실패 6건 (`fview1.sql` 등)은 testcase revision 불일치로 분류 (PR body 참고)
