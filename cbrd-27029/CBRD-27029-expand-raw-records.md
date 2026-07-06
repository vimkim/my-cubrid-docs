# CBRD-27029 Expand Raw Records

Commit under review: `85d8f5480` (`[CBRD-27029] Make heap next OOS expansion explicit`)

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
| `HEAP_WITHOUT_OOS_EXPAND` | Keep inline OOS OID slots in the heap record. | The caller immediately decodes through the attribute layer, which resolves OOS columns lazily. |

## Changed Public Scan APIs

| Function | Change |
|---|---|
| `heap_next()` | Keeps the same function name; adds `HEAP_OOS_EXPAND_POLICY oos_expand_policy`. |
| `heap_next_sampling()` | Keeps the same function name; adds `HEAP_OOS_EXPAND_POLICY oos_expand_policy`. |
| `heap_prev()` | Keeps the same function name; adds `HEAP_OOS_EXPAND_POLICY oos_expand_policy`. |
| `heap_next_expand_oos()` | Removed; callers now use `heap_next(..., HEAP_WITH_OOS_EXPAND)`. |
| `heap_next_skip_oos_expand()` | Removed; callers now use `heap_next(..., HEAP_WITHOUT_OOS_EXPAND)`. |
| `heap_next_sampling_skip_oos_expand()` | Removed; callers now use `heap_next_sampling(..., HEAP_WITHOUT_OOS_EXPAND)`. |
| `heap_prev_skip_oos_expand()` | Removed; callers now use `heap_prev(..., HEAP_WITHOUT_OOS_EXPAND)`. |

## Implementation

`src/storage/heap_file.h` 에 `HEAP_OOS_EXPAND_POLICY` 를 추가하고 `heap_next()`, `heap_next_sampling()`,
`heap_prev()` 의 public signature 에 enum 인자를 추가했다. 함수 이름은 유지하되 호출부에서 정책이 보이도록 만들었다.

`src/storage/heap_file.c` 의 `heap_next_internal()` 과 heap-scan visible-version helper 는 이 enum 을 그대로 전달한다.
`HEAP_GET_CONTEXT` 도 boolean `expand_oos` 대신 enum 정책을 보관한다. 실제 record-level Expand 실행 지점인
`heap_record_replace_oos_oids()` 는 `HEAP_WITHOUT_OOS_EXPAND` 일 때 바로 반환한다.

기존 skip/expand wrapper 는 제거했다. 새 호출자는 `heap_next()` 라는 기존 API 이름을 쓰면서도 다음처럼 선택해야 한다.

```c
heap_next (..., HEAP_WITH_OOS_EXPAND);
heap_next (..., HEAP_WITHOUT_OOS_EXPAND);
```

## Caller Review Table

| Caller | Policy | Review reason |
|---|---|---|
| `src/connection/connection_support.cpp:2471` | `HEAP_WITHOUT_OOS_EXPAND` | Immediately calls `heap_attrinfo_read_dbvalues()`. |
| `src/loaddb/load_server_loader.cpp:242` | `HEAP_WITHOUT_OOS_EXPAND` | Uses `heap_next()` to advance OID, then calls visible-version fetch and attribute decoding. |
| `src/query/dblink_global_tran_catalog.c:225` | `HEAP_WITHOUT_OOS_EXPAND` | Global transaction lookup decodes values through `heap_attrinfo_read_dbvalues()`. |
| `src/query/dblink_global_tran_catalog.c:482` | `HEAP_WITHOUT_OOS_EXPAND` | Global transaction iterator decodes values through `heap_attrinfo_read_dbvalues()`. |
| `src/query/scan_manager.c:5930` | `HEAP_WITHOUT_OOS_EXPAND` | Normal heap scan feeds query attribute evaluation. |
| `src/query/scan_manager.c:5936` | `HEAP_WITHOUT_OOS_EXPAND` | Sampling heap scan feeds query attribute evaluation. |
| `src/query/scan_manager.c:5954` | `HEAP_WITHOUT_OOS_EXPAND` | Reverse heap scan feeds query attribute evaluation. |
| `src/storage/btree_load.c:3722` | `HEAP_WITHOUT_OOS_EXPAND` | Index load generates keys through `heap_attrinfo_generate_key()`. |
| `src/storage/btree_load.c:5371` | `HEAP_WITHOUT_OOS_EXPAND` | Online index build evaluates filters and keys through the attribute layer. |
| `src/storage/catalog_class.c:5014` | `HEAP_WITHOUT_OOS_EXPAND` | Server compatibility metadata read decodes attributes. |
| `src/storage/catalog_class.c:5467` | `HEAP_WITHOUT_OOS_EXPAND` | Collation metadata read decodes attributes. |
| `src/storage/catalog_class.c:5679` | `HEAP_WITHOUT_OOS_EXPAND` | Apply-info metadata read decodes attributes. |
| `src/storage/system_catalog.c:4718` | `HEAP_WITH_OOS_EXPAND` | Catalog consistency scan may parse raw class records with `or_*` helpers. |
| `src/storage/system_catalog.c:5030` | `HEAP_WITH_OOS_EXPAND` | Catalog dump may parse raw class records with `or_*` helpers. |
| `src/storage/heap_file.c:8542` | `HEAP_WITH_OOS_EXPAND` | `heap_first()` keeps a raw-record-safe default. |
| `src/storage/heap_file.c:8570` | `HEAP_WITH_OOS_EXPAND` | `heap_last()` keeps a raw-record-safe default. |
| `src/storage/heap_file.c:8740` | `HEAP_WITH_OOS_EXPAND` | Scanrange forward fallback keeps the raw-record-safe behavior. |
| `src/storage/heap_file.c:8763` | `HEAP_WITH_OOS_EXPAND` | Scanrange forward continuation keeps the raw-record-safe behavior. |
| `src/storage/heap_file.c:8852` | `HEAP_WITH_OOS_EXPAND` | Scanrange reverse fallback keeps the raw-record-safe behavior. |
| `src/storage/heap_file.c:8871` | `HEAP_WITH_OOS_EXPAND` | Scanrange reverse continuation keeps the raw-record-safe behavior. |
| `src/storage/heap_file.c:8948` | `HEAP_WITH_OOS_EXPAND` | Scanrange next fallback keeps the raw-record-safe behavior. |
| `src/storage/heap_file.c:8969` | `HEAP_WITH_OOS_EXPAND` | Scanrange next continuation keeps the raw-record-safe behavior. |
| `src/storage/heap_file.c:9019` | `HEAP_WITH_OOS_EXPAND` | Scanrange previous fallback keeps the raw-record-safe behavior. |
| `src/storage/heap_file.c:9040` | `HEAP_WITH_OOS_EXPAND` | Scanrange previous continuation keeps the raw-record-safe behavior. |
| `src/storage/heap_file.c:9085` | `HEAP_WITH_OOS_EXPAND` | Scanrange first fallback keeps the raw-record-safe behavior. |
| `src/storage/heap_file.c:9130` | `HEAP_WITH_OOS_EXPAND` | Scanrange last fallback keeps the raw-record-safe behavior. |
| `src/storage/heap_file.c:15783` | `HEAP_WITHOUT_OOS_EXPAND` | Heap dump calls `heap_attrinfo_read_dbvalues()`. |
| `src/transaction/locator_sr.c:302` | `HEAP_WITH_OOS_EXPAND` | Classname cache parses class records with `or_class_name()`. |
| `src/transaction/locator_sr.c:1975` | `HEAP_WITH_OOS_EXPAND` | Classname consistency check parses class records with `or_class_name()`. |
| `src/transaction/locator_sr.c:2908` | `HEAP_WITH_OOS_EXPAND` | Fetch-all path ships raw records in `LC_COPYAREA`. |
| `src/transaction/locator_sr.c:9152` | `HEAP_WITHOUT_OOS_EXPAND` | Index removal path decodes attributes to find the matching BTID/key. |
| `src/transaction/locator_sr.c:9607` | `HEAP_WITHOUT_OOS_EXPAND` | Index consistency check decodes attributes and generates keys. |
| `src/transaction/locator_sr.c:10062` | `HEAP_WITHOUT_OOS_EXPAND` | Index consistency check decodes attributes and generates keys. |
| `src/transaction/locator_sr.c:10776` | `HEAP_WITH_OOS_EXPAND` | Class heap scan parses class records with `or_class_hfid()`. |
| `src/transaction/locator_sr.c:11962` | `HEAP_WITHOUT_OOS_EXPAND` | Foreign-key validation generates keys through the attribute layer. |
| `src/transaction/locator_sr.c:12117` | `HEAP_WITHOUT_OOS_EXPAND` | Locking branch only advances OID before refetching the locked record with OOS Expand. |
| `src/transaction/locator_sr.c:12157` | `HEAP_WITH_OOS_EXPAND` | Unlocked fetch-all path ships raw records in `LC_COPYAREA`. |

## Reviewer Checklist

- `HEAP_WITH_OOS_EXPAND` row: caller consumes raw `RECDES` bytes, or the function preserves a generic raw-record-safe default.
- `HEAP_WITHOUT_OOS_EXPAND` row: an attribute-layer read follows before OOS values are interpreted.
- Removed wrapper names do not remain in source.
- Visible-version helpers only pass the enum policy through `HEAP_GET_CONTEXT`; they do not change unrelated MVCC behavior.

## Verification

- `git diff --check`
- `just build`

Result: build and install completed successfully.
