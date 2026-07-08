# [CBRD-27006] OOS recdes locality

- JIRA: https://jira.cubrid.org/browse/CBRD-27006
- Parent: https://jira.cubrid.org/browse/CBRD-26583
- PR: https://github.com/CUBRID/cubrid/pull/7391
- Target branch: `feat/oos` (base tip `5b5ff588f`)
- Code branch: `CBRD-27006-oos-recdes-locality`
- Current PR HEAD: `e6fd6e8ba`
- Last checked: 2026-07-08

> Line numbers are for review navigation at HEAD `e6fd6e8ba` and may drift after a
> rebase. Behavior descriptions, not line numbers, are the source of truth.

## Purpose

CBRD-27006은 하나의 heap record(`RECDES`)가 여러 OOS 값을 가질 때, 그 값들을 가능한 한 같은
OOS page에 배치하고(write locality) 같은 head page에 있는 값들을 한 번의 page fix로 읽도록
(read locality) OOS insert/read 경로를 정리한다. 부수적으로, `heap_file.c` 안에 흩어져 있던
OOS 고유 로직을 `heap_oos.cpp` 로 모아 heap-core 파일의 diff와 OOS 결합도를 줄인다.

**AS-IS**

- `heap_attrinfo_insert_to_oos()` 가 OOS 대상 컬럼마다 `oos_insert()` 를 호출했고, 각 호출이
  독립적으로 bestspace 탐색과 `pgbuf_fix` 를 수행했다. 같은 record의 OOS 값이 여러 OOS page로
  흩어질 수 있었다.
- lazy Resolve와 record-level Expand 모두 OOS OID마다 `oos_read()` 를 따로 호출했다. 같은 head
  page에 있는 값이어도 page를 여러 번 fix/unfix했다.
- OOS insert 결과 OID의 replication publication을 caller가 직접 push하는 흐름이 남아 있었다
  (`locator_sr.c` 의 `oos_push_oos_oid`).

**TO-BE**

- heap attribute order대로 OOS 대상 값을 모아 `oos_insert_many()` 로 batch insert 한다.
- single-chunk 값들은 page capacity 안에서 greedy run으로 묶어 한 OOS page에 넣는다. run 하나가
  한 page에 다 들어가지 않으면 값을 흩뿌리지 않고 새 page를 할당한다.
- multi-chunk 값은 기존 chain insert(`oos_insert_across_pages()`)를 그대로 유지하되, single-chunk
  값과 섞여도 publication order를 보존한다.
- read path는 `oos_read_many()` 로 head page가 같은 요청들을 group하여 한 latch로 읽는다.
- lazy Resolve는 요청된 OOS 값이 2개 이상일 때만 grouped path를 탄다. non-OOS/single-OOS
  projection은 scalar path를 유지한다.
- public OOS insert API(`oos_insert` / `oos_insert_many`)가 성공한 head OOS OID publication을 직접
  담당하고, caller-side push는 제거된다.

이 PR은 on-disk OOS format, inline slot layout, OOS OID sharing policy, multi-chunk chain,
replication log format을 바꾸지 않는다. OOS OID는 여전히 값 하나당 하나다.

## Implementation

### Ownership map (누가 무엇을 소유하는가)

이 PR의 구조적 핵심은 아래 3-layer 분담이다.

| Layer | File | 책임 |
|---|---|---|
| OOS page 수준 primitive | `oos_file.cpp` / `oos_file.hpp` | OOS page에 batch로 넣고(`oos_insert_many`), head page 단위로 묶어 읽는다(`oos_read_many`). page fix / bestspace / WAL / publication 을 이 layer가 소유. |
| OOS ↔ heap 접착 로직 | `heap_oos.cpp` / `heap_oos.hpp` | 어떤 attribute가 inline-OOS인지 판별, inline reference 파싱, grouped prefetch, OOS-side insert delegation, record Expand. heap record 포맷을 아는 OOS 로직을 여기에 집약. |
| heap core wiring | `heap_file.c` / `heap_file.h` | DB_VALUE ↔ RECDES 직렬화/역직렬화, scalar attribute read(+ stack scratch fast path), read/insert dispatch. OOS 세부는 위 두 layer로 위임. |

> **이전 문서 대비 이동/개명 (reviewer 주의)**
>
> | 이전 문서 이름 | 현재 이름 / 위치 |
> |---|---|
> | `heap_oos_attr_inline_ptr()` | `heap_oos_find_attr_inline_ref()` (`heap_oos.cpp`) |
> | `heap_oos_read_dbvalues_grouped()` (transform + scalar read 포함) | `heap_oos_read_grouped_payloads()` (`heap_oos.cpp`, **raw buffer만 채움**) + `heap_attrinfo_read_dbvalues_grouped_oos()` (`heap_file.c`, transform + scalar read) |
> | `heap_attrinfo_read_dbvalues_internal()` (dispatch) | `heap_attrinfo_read_dbvalues_from_recdes()` (`heap_file.c`) + gate가 `heap_oos_read_grouped_payloads()` 안으로 이동 |
> | `heap_oos_read_blobs()` | `heap_oos_read_values()` (`heap_oos.cpp`) |
> | insert: `oos_columns`/`oos_oids`/`oos_lengths` 3-vector | `heap_oos_column_plan {selected, oid, length}` + `heap_oos_insert_serialized_values()` |
>
> `heap_record_replace_oos_oids()` 와 그 sub-function(`heap_oos_parse_vot`, `heap_oos_compute_layout`,
> `heap_oos_build_record`) 및 `heap_oos_delete_unreferenced()` 는 **base(`feat/oos`)에 이미
> `heap_oos.cpp` 에 존재**했다. 이 PR은 그 중 `heap_oos_read_blobs`→`heap_oos_read_values` rename과
> body의 `oos_read_many()` 전환만 건드린다.

### Scope Invariants

- OOS inline slot layout은 그대로 `[OID (8B) | full_length (8B bigint)]` = `OR_OOS_INLINE_SIZE` 이다.
- `oos_insert_many()` 는 request order를 logical attribute order로 취급하고 재정렬하지 않는다. 각
  request의 `oid_out` 에 head OOS OID를 채운다.
- single-chunk run은 run 전체가 한 page에 들어갈 때만 그 page를 쓴다. 아니면 fresh page.
- multi-chunk 값은 기존 reverse insert + dummy boundary marker 구조를 유지한다.
- public OOS insert API가 replication용 head OOS OID publication을 수행한다. caller는 push하지 않는다.
- lazy Resolve grouped read는 `요청된 OOS 값 >= 2` 일 때만 수행한다.
- scalar OOS read는 `IO_MAX_PAGE_SIZE` stack scratch fast path를 유지한다.
- `oos_read_many()` 는 한 순간 한 OOS page만 fix한다(scalar와 동일한 latch 규율).

### 1. OOS public API (`oos_file.hpp`)

```cpp
using oos_buffer = cubbase::span<char>;   // caller-owned byte span; size()가 authoritative length

struct oos_insert_request { oos_buffer src;   OID *oid_out; };   // oos_file.hpp:45
struct oos_read_request   { OID oid;          oos_buffer dest; }; // oos_file.hpp:51

extern int oos_insert_many (THREAD_ENTRY *, const VFID &oos_vfid, cubbase::span<oos_insert_request>); // :102
extern int oos_read_many   (THREAD_ENTRY *, cubbase::span<oos_read_request>);                          // :106
```

- `oos_insert_request`: `src` 는 caller-owned OOS payload byte span(호출 동안만 읽힘), `oid_out` 에
  insert 성공 시 head OOS OID를 쓴다. request는 메모리를 소유하지 않는다.
- `oos_read_request`: `oid` 는 heap record inline slot의 head OOS OID, `dest` 는 inline `full_length`
  로 크기를 맞춘 caller-owned 목적지. `oos_read_many()` 는 정확히 `dest.size()` 바이트를 채우거나
  corruption/error를 보고한다.
- Contract: insert는 `src.data()!=null && 0<src.size()<=INT_MAX && oid_out!=NULL`, read는
  `!OID_ISNULL(oid) && dest.data()!=null && 0<dest.size()<=INT_MAX`. 위반 시 진입부에서 즉시 reject.

### Debug counters (`#if CUBRID_UNIT_TEST_ENABLED`, `oos_file.hpp:140`)

batching/grouping이 실제로 일어났는지 테스트가 증명하기 위한 test-only 계수기다:
`insert_many_calls`, `insert_many_requests`, `single_page_batch_count`, `insert_reused_pages`,
`insert_fresh_pages`, `insert_values_per_fixed_page`, `read_many_calls`, `read_many_requests`,
`read_many_grouped_head_pages`, `read_values_per_fixed_page`.

내부 저장소(`oos_Debug_counters`)는 `std::atomic<unsigned long long>` 필드로,
`memory_order_relaxed` fetch_add/store/load를 쓴다(계측 자체의 data race 회피). 위 struct는
`bridge_oos_debug_counters_get()` 가 반환하는 plain snapshot 타입이다.

### 2. Batched insert (`oos_file.cpp`)

### `oos_publish_oos_oid()` / `oos_clear_insert_publication_state()` (`:1101`, `:1107`)

- `oos_publish_oos_oid()`: 성공한 head OOS OID 하나를 `thread_p->oos_oids` 에 push한다. publication
  책임을 public insert API 내부로 국소화한다.
- `oos_clear_insert_publication_state()`: `thread_p->oos_oids` 를 비우고, 현재 transaction
  descriptor가 있으면 `tdes->oos_insert_lsa_queue` 도 비운다. batch insert가 부분 publication 후
  실패했을 때 stale publication 상태가 이후 replication 처리에 섞이지 않도록 한다.

`oos_insert()` 는 이제 scalar 성공 시 `oos_publish_oos_oid()` 를 호출한다(`:1150-1153`).

### `oos_insert_single_page_batch()` (`:1160`)

이미 선택된 single-page batch 하나를 한 OOS page에 넣는다. caller(`oos_insert_many`)가 batch 전체의
`needed_space` 를 계산해 넘긴다.

1. `oos_find_best_page(needed_space)` 로 batch 전체가 들어갈 page를 하나 fix한다. 실패는 propagate.
2. `spage_number_of_records()==0` 로 page가 비어 있었는지(fresh/재사용 분류) 기록한다.
3. request를 original order대로 순회하며 각 값에 head `OOS_RECORD_HEADER{len,0,NULL}` 를 prepend해
   `OOS_RECDES` 를 만들고(`scope_exit` 로 해제 보장), 같은 fixed page에 `spage_insert` 한다. slotted-page
   실패는 `ER_GENERIC_ERROR`.
4. 결과 OID(fixed page VPID + slotid)를 `*request.oid_out` 에 쓰고, WAL(`oos_log_insert_physical`)을
   남기고, `oos_publish_oos_oid()` 로 publish한다.
5. batch 전체가 끝난 뒤 bestspace hint를 **한 번** 갱신한다(`oos_stats_add_bestspace`).
6. 카운터: `single_page_batch_count`, `insert_values_per_fixed_page += batch`, `insert_fresh/reused_pages`.

### `oos_insert_many()` (`:1237`)

여러 OOS payload를 logical order로 삽입한다.

1. 카운터(`insert_many_calls`, `insert_many_requests`)를 기록하고, **모든** request를 먼저 검증한다
   (null/0/INT_MAX/`oid_out`).
2. `max_chunk_size = oos_get_max_chunk_size_within_page()`, `page_capacity = align_below(spage_max_record_size)`,
   `required_space(req) = align(src.size()+OOS_RECORD_HEADER_SIZE)`.
3. `pos` 로 request를 순회(정렬/재정렬 없음):
   - **multi-chunk** (`src.size() > max_chunk_size`): `oos_insert_across_pages()` 로 넣고, 반환 head
     OID를 `oid_out` 에 복사한 뒤 publish하고 한 칸 전진(`:1266-1276`).
   - **single-chunk**: greedy run — 다음 single-chunk request가 같은 page에 계속 들어가는 동안
     (`+ SPAGE_SLOT_SIZE + required_space(next) <= page_capacity`) `batch_end` 를 늘린다(`:1279-1289`).
     선택된 run을 `oos_insert_single_page_batch()` 에 넘기고 `pos = batch_end`.
4. 어떤 단계든 error가 나면 `oos_clear_insert_publication_state()` 후 반환(`:1296-1300`).

> greedy run은 단순 loop 최적화가 아니라 **placement 단위**다. `oos_find_best_page()` 가 그 run
> 전체를 담을 page를 못 찾으면 값을 쪼개 흩뿌리지 않고 fresh page를 할당한다.

### 3. Grouped read (`oos_file.cpp`)

### `oos_read_chunk_in_page()` (`:1491`) / `oos_check_head_header()` (`:1601`)

- `oos_read_chunk_in_page()`: **이미 fix된** page에서 한 chunk를 읽어, chain header를 `header_out` 에
  복사하고 payload를 `byte_span_writer` 에 append한다. slot이 header보다 짧거나 payload가 목적지를
  넘으면 `ER_HEAP_OOS_CORRUPTED_RECORD`. scalar `oos_read()` 와 grouped `oos_read_many()` 가 공유.
- `oos_check_head_header()`: inline OID가 head chunk(`chunk_index==0`)를 가리키는지, header의
  `total_data_length` 가 caller의 기대 길이와 같은지 검사. 불일치는 corruption.

`oos_read_within_page()`(`:1532`)는 이제 page fix/unfix만 하고 실제 slot 읽기는 `oos_read_chunk_in_page()`
에 위임한다. `oos_read()`(`:1627`)는 `oos_read_within_page()` + `oos_check_head_header()` 후 multi-chunk
continuation과 최종 길이 검사를 그대로 수행한다.

### `oos_read_many()` (`:1671`)

head chunk가 같은 page를 공유하는 요청들을 한 page fix로 해석한다.

1. 카운터 기록 후 모든 request를 검증한다.
2. `done[]` 와 continuation vector를 좁은 `std::bad_alloc` 경계 안에서 준비(`:1695`).
3. original order로 순회하며 이미 처리된 request는 skip. 첫 미처리 request의 head VPID로 page를
   read-latch fix하고, `scope_exit` 로 unfix를 보장한다(`read_many_grouped_head_pages++`).
4. 같은 fixed page 안에서 head VPID가 일치하는 나머지 request를 모두 해석한다(`done[j]=true`,
   `read_values_per_fixed_page++`). 각 request는 `oos_read_chunk_in_page()` + `oos_check_head_header()`.
   - multi-chunk면 `(request, next_oid, head_payload_size)` continuation을 기록만 하고(page 잡은 채
     chain을 따라가지 않는다), single-chunk면 writer가 full인지 확인.
5. **page를 unfix한 뒤** 각 continuation을 기존 `oos_read_across_pages()` 로 이어 읽는다(나머지
   destination subspan 위에 writer). 최종 길이 불일치는 corruption.
6. STL allocation 실패는 `ER_OUT_OF_VIRTUAL_MEMORY` 로 변환.

> 한 순간 한 OOS page만 fix한다는 규율을 지키기 위해 multi-chunk tail은 head page scope가 끝난
> 뒤에 읽는다(scalar `oos_read()` 와 동일).

### 4. OOS ↔ heap 접착 로직 (`heap_oos.cpp`)

### `heap_oos_parse_inline_ref()` (`:412`, `heap_oos.hpp` 로 export)

inline OOS reference `[OID | full_length]` 를 검증/파싱하는 **단일 파서**. lazy Resolve(scalar/grouped)
와 record-level Expand가 모두 이 함수를 통과하므로 파싱 규칙과 `DB_MAX_STRING_LENGTH` bound가 경로마다
어긋날 수 없다.

- 출력을 NULL OID / 0 길이로 먼저 초기화(Case 1이 읽기 전에 OID를 보고할 수 있으므로).
- inline 영역이 `OR_OID_SIZE + OR_BIGINT_SIZE` 보다 짧으면 reject(Case 1).
- OID/bigint를 읽고, 읽기 실패·NULL OID·비양수 길이·`> DB_MAX_STRING_LENGTH` 를 reject(Case 2/3).
- corruption은 `ER_HEAP_OOS_BAD_INLINE_HEADER` 로 보고(CBRD-26769 계약: 손상된 inline reference는
  crash가 아니라 반환 가능한 error).

### `heap_oos_find_attr_inline_ref()` (`:454`, static)

요청된 attribute 하나가 현재 record에서 inline-OOS variable 값인지 probe하고, 맞으면 record 안
inline OOS reference 포인터를 반환한다.

- duplicate-key pseudo attr, record/representation 부재, shared/class attr, fixed attr, NULL variable
  attr은 NULL 반환(= "여기서는 OOS 아님").
- `heap_recdes_get_var_offset_entry()` 로 VOT entry를 읽어 `OR_IS_OOS()` 아니거나 offset-size가
  invalid하면 NULL. invalid offset-size를 "not batched"로 취급하여, 이후 scalar path가 그 attribute를
  읽을 때 자신의 error(`ER_GENERIC_ERROR`)를 소유하게 한다(scalar error ownership 보존).

### `heap_oos_read_grouped_payloads()` (`:492`, `heap_oos.hpp` 로 export)

한 record의 요청 OOS 컬럼을 **한 번의 `oos_read_many()`** 로 prefetch한다. **여기에 dispatch gate가
들어 있다.**

1. record가 없거나 `OR_MVCC_FLAG_HAS_OOS` 가 없으면 `raws` 를 비운 채 즉시 반환.
2. 요청 attribute를 훑어 inline-OOS attr 개수를 **최대 2까지** 센다. `< 2` 이면 `raws` 를 비운 채
   반환 → caller가 scalar path를 탄다(`:507-518`).
3. `>= 2` 이면 `raws` 를 `num_values` 크기로 resize(좁은 `bad_alloc` 경계). 각 OOS attr에 대해
   `heap_oos_parse_inline_ref()` 로 파싱하고, 정확한 크기의 목적지 buffer를 `recdes_allocate_data_area`
   로 잡아 `raws[i]` 에 붙인 뒤 `oos_read_request` 를 쌓는다.
4. 준비된 모든 request를 `oos_read_many()` 로 해석한다.

반환 계약: `raws[i].data != NULL` → 그 attr의 raw OOS 바이트가 준비됨. `raws[i].data == NULL` → "여기선
OOS 아님, scalar reader가 처리". `raws` 는 성공/실패 모두 `heap_oos_free_grouped_payloads()` 로 해제해야
한다(부분 buffer가 붙어 있을 수 있음).

### `heap_oos_free_grouped_payloads()` (`:569`)

`heap_oos_read_grouped_payloads()` 가 붙인 raw buffer들을 해제한다. 빈 vector(grouped path 미적용)에도
안전.

### `heap_oos_insert_serialized_values()` (`:590`, `heap_oos.hpp` 로 export)

이미 직렬화된 attribute payload들의 **OOS-side write**를 소유한다. (DB_VALUE→RECDES 직렬화는
`heap_file.c` 가 유지.)

1. `heap_get_class_info()` + `heap_oos_find_vfid(create=true)` 로 class OOS file을 찾거나 만든다.
2. 현재 transaction descriptor를 얻고(없으면 `ER_LOG_UNKNOWN_TRANINDEX` fatal), OOS write 시작 전
   `tdes->oos_insert_lsa_queue` 와 `thread_p->oos_oids` 를 비운다.
3. request가 있으면 `oos_insert_many()` 를 한 번 호출한다.

### `heap_oos_read_values()` (`:132`, `heap_oos_read_blobs` 에서 rename)

record-level Expand가 recdes의 **모든** OOS 값을 필요로 하므로, OOS attr마다 `heap_oos_parse_inline_ref()`
로 파싱하고 목적지 buffer를 준비해 `oos_read_request` 를 모은 뒤 **한 번의 `oos_read_many()`** 로 읽는다.
corruption 시 `ER_HEAP_OOS_BAD_INLINE_HEADER` 를 propagate(assert_release 없음). 이전 `heap_oos_read_blobs`
는 값마다 개별 read였다.

> `heap_record_replace_oos_oids()`(`:341`)와 `heap_oos_parse_vot`/`heap_oos_compute_layout`/
> `heap_oos_build_record`, 그리고 `heap_oos_delete_unreferenced()`(`:653`)는 base에 이미 있던 코드다.
> 이 PR은 Expand 경로에서 `heap_oos_read_values` 로의 rename/전환만 반영한다.

### 5. heap core wiring (`heap_file.c`)

### 읽기 dispatch

두 public 진입점 `heap_attrinfo_read_dbvalues()`(`:11071`)와 `heap_attrinfo_read_dbvalues_without_oid()`
(`:11129`)는 representation recache 후 공통 loop `heap_attrinfo_read_dbvalues_from_recdes()`(`:10853`)를
호출한다.

```text
heap_attrinfo_read_dbvalues_from_recdes()                         [heap_file.c:10853]
  ret = heap_oos_read_grouped_payloads(recdes, attr_info, oos_raws)   [heap_oos.cpp — self-gates >=2]
  if (ret != NO_ERROR)  -> free(oos_raws); return ret
  if (oos_raws.empty())                                                // 0/1 OOS, non-OOS
       -> heap_attrinfo_read_dbvalues_scalar()                         [:10805] scalar loop (+stack scratch)
  else                                                                 // >=2 OOS: grouped
       -> heap_attrinfo_read_dbvalues_grouped_oos()                    [:10823]
            for each value:
              oos_raws[i].data != NULL -> heap_attrvalue_transform_to_dbvalue(..., raw, /*copy*/true)
              else                     -> heap_attrvalue_read()        // scalar
       -> heap_oos_free_grouped_payloads(oos_raws)
```

Dispatch rule:

```text
요청된 OOS 값 = 0 -> scalar path
요청된 OOS 값 = 1 -> scalar path (IO_MAX_PAGE_SIZE stack scratch fast path 유지)
요청된 OOS 값 >= 2 -> grouped: 1× oos_read_many() 후 transform + 나머지 scalar
```

> 이전 문서의 `heap_attrinfo_read_dbvalues_internal()` 은 없다. dispatch loop는
> `heap_attrinfo_read_dbvalues_from_recdes()` 이고, `>=2` gate는 `heap_oos_read_grouped_payloads()`
> 안에 있다. transform + scalar read는 `heap_attrinfo_read_dbvalues_grouped_oos()` 가 한다.

### 관련 read 헬퍼 refactor

- `heap_recdes_get_var_offset_entry()`(`:10501`): 한 variable attribute의 raw VOT entry(flag bits 포함)를
  offset-size(`OR_BYTE/SHORT/INT_SIZE`)에 맞게 읽어 반환. `OR_IS_OOS()` 판정에 쓰인다. corrupt offset-size는
  error 없이 `false` 반환(caller가 보고 방식 결정). `heap_oos_find_attr_inline_ref()` 및
  `heap_attrvalue_point_variable()` 가 공유.
- `heap_attrvalue_read_oos_inline()`(`:10540`): scalar inline OOS 읽기. inline 파싱을
  `heap_oos_parse_inline_ref()` 로 위임하고, 작은 값의 stack scratch(`IO_MAX_PAGE_SIZE`) fast path와 기존
  `oos_read()` 호출/정리를 유지.
- `heap_attrvalue_read()` / `heap_attrvalue_transform_to_dbvalue()`: `heap_file.h` 로 export되어 grouped
  reader가 raw buffer를 DB_VALUE로 변환하는 데 재사용된다.

### 쓰기 (insert)

```text
heap_attrinfo_transform_to_disk()                                 [ ... determine_disk_layout ]
  -> std::vector<heap_oos_column_plan> oos_plan(num_values)          // {selected, oid, length}
  -> heap_attrinfo_insert_to_oos(attr_info, lob_create_flag, &oos_plan)   [heap_file.c:12604]
       -> heap_attrinfo_prepare_oos_insert_requests()               [:12552]
            for each plan.selected:
              heap_attrinfo_serialize_oos_value() -> exact-size RECDES payload   // BLOB/CLOB ELO copy 포함
              plan.length = payload.length
              requests.push_back({ span(payload), &plan.oid })      // oid_out = &plan.oid
       -> heap_oos_insert_serialized_values(class_oid, requests)    [heap_oos.cpp — OOS file + publish reset + oos_insert_many]
       -> cleanup: heap_attrinfo_free_oos_payloads()                [:12586] 모든 payload->data free
```

- `heap_oos_column_plan {selected, oid, length}` (`:701`) 하나가 base의 세 병렬 vector
  (`oos_columns` bool / `oos_oids` / `oos_lengths`)를 대체한다. layout 결정
  (`heap_attrinfo_determine_disk_layout`)이 `selected` 를 채우고, insert가 `oid`/`length` 를 채운다.
- 직렬화는 모든 선택 값에 대해 insert **전에** 완료된다 → `oos_insert_many()` 에 안정적인 request span과
  attribute order를 제공하지만, 넓은 OOS row에서 peak memory가 base의 per-column insert/free보다 커진다.
- 진입부 `payloads.reserve`/`requests.reserve` 의 `std::bad_alloc` 은 `ER_OUT_OF_VIRTUAL_MEMORY` 로 변환.

### 6. Publication ownership (`locator_sr.c`)

`locator_oos_insert_force()`(`:5276`)에서 `oos_insert()` 호출 뒤에 있던 `oos_push_oos_oid(thread_p, &oos_oid)`
한 줄을 제거했다. `oos_insert()` 가 이제 성공 OID를 스스로 publish하므로 caller push는 중복 publication과
replication metadata 순서 꼬임을 유발한다. 기존 exported `oos_push_oos_oid` 는 소스 전체에서 제거되었고,
publication은 `oos_file.cpp` 내부의 static `oos_publish_oos_oid()` 로 일원화되었다.

## Remarks

### Test Plan

### Server OOS unit tests — `unit_tests/oos/test_oos_server.cpp`

test-local 헬퍼: `clear_oos_insert_publication_state_for_test()`(`:43`)는 production static clear 로직의
사본이다(production helper가 static이므로).

| Test | Line | 검증 |
|---|---:|---|
| `OosServerTest.OosInsertManyKeepsSinglePageLocalityAndReadManyGroupsHeadPage` | `162` | single-chunk 3개가 한 page에 들어가고 grouped read가 head page 하나로 묶인다. |
| `OosServerTest.OosInsertManyReusesOnlyPageThatFitsWholeBatch` | `205` | 기존 page는 batch 전체가 들어갈 때만 재사용. |
| `OosServerTest.OosInsertManyAllocatesFreshPageInsteadOfScatteringBatch` | `241` | 후보 page가 batch 전체를 못 담으면 값을 흩뿌리지 않고 fresh(공유) page로. |
| `OosServerTest.OosInsertManySplitsOversizedSingleChunkRun` | `286` | single-chunk 총합이 한 page를 넘으면 run이 분할된다. |
| `OosServerTest.OosInsertManyPreservesMixedSingleAndMultiChunkPublicationOrder` | `320` | single/multi/single 순서에서 OID publication이 logical order를 유지(multi-chunk dummy marker 허용). |

### SQL CRUD tests — `unit_tests/oos/sql/test_oos_sql_crud.cpp`

| Test | Line | 검증 |
|---|---:|---|
| `OosSqlCrud.Cbrd27006MultiOosColumnSelectsAndUpdate` | `131` | 여러 OOS 컬럼을 select/update해도 값이 정확. |
| `OosSqlCrud.Cbrd27006MixedSingleChunkAndMultiChunkRow` | `182` | 한 row에 single-chunk와 multi-chunk OOS 값이 섞여도 동작. |
| `OosSqlCrud.Cbrd27006ReadDispatchBatchesOnlyMultiOosProjections` | `222` | `small_col`만/`c1`만 select → `read_many_calls==0`; `c1+c2` select → `read_many_calls==1`, `read_many_requests==2`, `read_many_grouped_head_pages==1`. |

### Inline-header parser test — `unit_tests/oos/test_oos.cpp`

`OosTest.HeapAttrvalueReadOosInlineCorruptHeader` Case 3의 bad-length 상한을 `INT_MAX` 에서
`DB_MAX_STRING_LENGTH` 로 좁혔다(`(DB_BIGINT) DB_MAX_STRING_LENGTH + 1` 을 bad length에 추가). 공용 파서
`heap_oos_parse_inline_ref()` 의 `> DB_MAX_STRING_LENGTH` 검사와 테스트 상한을 일치시킨 것이다.

### Trade-offs & non-goals

- Insert peak memory 증가: 선택된 모든 OOS 값을 insert 전에 직렬화해 둔다.
- grouped lazy Resolve는 요청된 모든 OOS raw buffer를 DB_VALUE 변환이 끝날 때까지 들고 있다. `>=2`
  gate로 이 비용을 page-fix batching이 이득일 때만 지불한다.
- `std::bad_alloc` catch는 `std::vector` allocation의 좁은 경계에서만 쓰고 CUBRID error로 변환한다
  (일반 control flow 아님).
- `clear_oos_insert_publication_state_for_test()` 는 production static clear 로직을 복제한다. publication
  state 필드가 늘면 테스트와 production을 함께 갱신하거나 bridge helper를 노출해야 한다.
- 이 PR 범위 밖: OOS OID reuse/dedup, OOS read PEEK mode, multi-column combined OOS record, multi-chunk
  continuation-page locality, on-disk/replication format 변경.

### Review-focused flows 요약

```text
Insert locality:
  determine_disk_layout -> heap_oos_column_plan[]
    -> prepare_oos_insert_requests (serialize, attr order)
    -> heap_oos_insert_serialized_values -> oos_insert_many
         multi-chunk -> oos_insert_across_pages
         single-chunk run -> oos_insert_single_page_batch (1 page for whole run)

Lazy Resolve:
  read_dbvalues[_without_oid] -> read_dbvalues_from_recdes
    -> heap_oos_read_grouped_payloads   (>=2 gate; fills raws or leaves empty)
       empty -> scalar loop
       else  -> grouped_oos (transform raws + scalar rest) -> free

Record Expand:
  heap_record_replace_oos_oids -> heap_oos_read_values -> oos_read_many -> rebuild expanded record
```

Review 시 확인 포인트:

- request/attribute order가 logical order와 일치하는가.
- `needed_space` 가 single-page run 전체를 나타내는가(값 하나가 아니라).
- reused page는 run 전체가 들어갈 때만 유효한가. 실패 시 partial publication이 clear되는가.
- `HAS_OOS` 만으로 batch하지 않고 요청 OOS가 2개 이상일 때만 grouped인가.
- Expand/scalar/grouped가 모두 `heap_oos_parse_inline_ref()` 하나를 통과하는가.
