# CBRD-26948 Server Compactdb OOS Expand 제거 및 처리 예산 수정 계획

> 상태: 구현 전 review plan
>
> 기준 revision: PR #7416 HEAD `81f7dbbf3` 기반 분석. PR #7416의 enum rename
> (`HEAP_RECDES_CONSUMPTION_POLICY`, `HEAP_RECDES_CONSUME_RAW_BYTES`,
> `HEAP_RECDES_DONT_CONSUME_RAW_BYTES`) 반영을 전제로 한다.
>
> 대상: server Compactdb phase 1과 공용 fetch 함수 `xlocator_lock_and_fetch_all()`

## 1. Objective

Server Compactdb가 heap에 저장된 작은 OOS inline stub record를 record-level Expand한 뒤 처리하지 않도록 한다. 가져온 stored-form `RECDES`는 OOS-aware attribute 계층에서 필요한 값만 Resolve하고, `space_to_process`는 expanded logical length가 아니라 stored record length로 차감한다.

결과적으로 다음 두 문제를 함께 없앤다.

1. Compactdb가 record 전체를 미리 Expand하면서 발생하는 OOS read, 메모리 할당, copyarea 확장 비용을 제거한다.
2. stored record는 처리 예산 안에 들어오지만 expanded record가 예산보다 크다는 이유만으로 `big_objects`에 포함되어 영구적으로 건너뛰는 문제를 막는다.

이 계획은 standalone Compactdb의 direct rewrite 문제를 다루지 않는다. `src/executables/compactdb.c`가 `desc_obj_to_disk()` 결과를 `heap_update_logical()`에 직접 전달해 OOS Demotion을 우회하는 문제는 별도 수정 범위다.

## 2. Background

OOS (Out-of-row Overflow Storage)는 큰 가변 attribute 값을 OOS value chain에 저장하고, heap record에는 16-byte OOS inline stub만 남긴다. OOS inline stub은 head OOS OID 8B와 full length 8B로 구성된다.

OOS 값을 읽는 방법은 두 가지다.

| 방식 | 동작 | 적합한 소비자 |
|------|------|---------------|
| OOS Expand | 모든 OOS inline stub을 실제 값으로 바꾸고 record 전체를 다시 만든다 | raw `RECDES`를 전송, parse, 재삽입 또는 byte-compare하는 소비자 |
| OOS Resolve | attribute를 읽을 때 해당 OOS value만 `oos_read()`로 가져온다 | `HEAP_CACHE_ATTRINFO` 등 OOS-aware attribute 소비자 |

Server Compactdb는 후자다. `desc_disk_to_attr_info()`가 `heap_attrinfo_read_dbvalues()`를 호출하므로 stored-form record 안의 OOS inline stub을 이해할 수 있다. record-level Expand를 먼저 수행할 정확성 요구가 없다.

## 3. Current Call Flow

### 3.1 Compactdb 진입

```text
client compactdb
  -> boot_compact_classes(..., space_to_process, ...)
     -> server boot_compact_db()
        -> process_class()
```

`space_to_process`는 한 번의 Compactdb server 요청에서 처리할 record bytes의 최대 예산이다. `boot_compact_db()`는 입력값을 `max_space_to_process`에 보존하고, 처리하면서 `space_to_process`를 차감한다.

### 3.2 현재 fetch 및 decode

```text
process_class()                                      compactdb_sr.c
  -> xlocator_lock_and_fetch_all()                   locator_sr.c
     -> heap_next(... RAW_BYTES_NOT_CONSUMED)        OID 탐색용 첫 read
     -> instance X_LOCK
     -> heap_get_visible_version(... RAW_BYTES_CONSUMED)
        -> heap_record_replace_oos_oids()
           -> 모든 OOS-backed attribute oos_read()
           -> expanded RECDES rebuild
     -> LC_COPYAREA에 expanded RECDES 저장
  -> obj->length와 space_to_process 비교
  -> desc_disk_to_attr_info()
     -> heap_attrinfo_read_dbvalues()
        -> attribute DB_VALUE 구성
  -> process_object()
  -> 변경 시 locator_attribute_info_force()
```

instance lock이 없는 분기에서도 `heap_next(... RAW_BYTES_CONSUMED)`를 사용하므로 반환되는 `obj->length`는 expanded length다.

## 4. Problem Analysis

### 4.1 불필요한 record-level Expand

`heap_attrinfo_read_dbvalues()`는 variable offset table의 OOS flag를 보고 OOS-backed attribute를 lazy Resolve할 수 있다. 따라서 현재 흐름은 다음과 같이 같은 값을 두 계층에서 중복 취급한다.

```text
heap fetch 계층: record 전체 Expand
  -> attribute 계층: 이미 펼쳐진 일반 value를 parse
```

원하는 흐름은 다음과 같다.

```text
heap fetch 계층: stored RECDES 보존
  -> attribute 계층: 실제로 읽는 OOS-backed attribute만 Resolve
```

Expand를 제거하면 다음 비용이 줄어든다.

- record의 모든 OOS-backed attribute에 대한 선행 `oos_read()`
- expanded record를 만들기 위한 임시 메모리 할당 및 copy
- expanded record가 기본 `DB_PAGESIZE` copyarea를 넘을 때 발생하는 `S_DOESNT_FIT` grow/retry
- logical value 전체를 `LC_COPYAREA`에 담는 메모리 사용량

### 4.2 Expanded length가 처리 예산을 왜곡함

현재 `process_class()`는 `LC_COPYAREA_ONEOBJ.length`를 그대로 사용한다.

```c
if (obj->length > *space_to_process)
  {
    if (*space_to_process == max_space_to_process)
      {
        (*big_objects)++;
        /* 이 object는 건너뜀 */
      }
    else
      {
        *space_to_process = 0;
        /* 다음 요청에서 현재 object부터 재시도 */
      }
  }
else
  {
    *space_to_process -= obj->length;
    /* object 처리 */
  }
```

두 분기는 구분해야 한다.

| 조건 | 현재 의미 |
|------|-----------|
| `obj->length > max_space_to_process` | 새 요청의 전체 예산으로도 처리할 수 없는 big object로 판단해 건너뜀 |
| `obj->length <= max_space_to_process`, 현재 남은 예산만 부족 | `last_processed_oid`를 되돌리고 다음 요청에서 재시도 |

OOS Expand가 켜져 있으면 `obj->length`는 heap의 stored length가 아니라 logical expanded length다. 예를 들어 heap에는 약 수십 byte의 OOS inline stub을 가진 record로 저장됐지만 OOS value가 50KB라면, 16KB 예산에서 다음처럼 오판할 수 있다.

```text
stored record length       200B
max_space_to_process      16KB
expanded obj->length      50KB

stored length < max budget < expanded length
  -> 현재: big_objects 증가, 해당 row 건너뜀
  -> 목표: stored length 200B 차감 후 정상 처리
```

Compactdb가 실제로 heap에서 scan하고 lock하여 처리하는 단위는 stored record다. OOS value read 비용은 attribute Resolve 시점에 별도로 발생하지만, 기존 `space_to_process`가 나타내는 record byte budget을 expanded logical payload로 바꾸겠다는 명시적 설계는 없다. 따라서 stored length를 유지하는 것이 기존 Compactdb budget 의미와 OOS 도입 전 동작에 가장 가깝다.

## 5. Scope

### 5.1 포함

- `xlocator_lock_and_fetch_all()`이 caller의 `RECDES` 소비 정책을 명시적으로 받도록 하는 API 변경
- server Compactdb와 domain upgrade caller가 `HEAP_RECDES_DONT_CONSUME_RAW_BYTES`를 선택하도록 변경
- `xlocator_lock_and_fetch_all()`의 lock/no-lock 분기 모두 stored-form record를 반환하도록 변경
- server Compactdb가 stored `obj->length`로 `space_to_process`를 판정하고 차감하는 계약 명시
- OOS-backed row의 Compactdb budget 회귀 테스트
- domain upgrade 경로의 OOS 회귀 테스트 또는 기존 테스트 확인

### 5.2 제외

- standalone Compactdb의 `desc_obj_to_disk()` -> `heap_update_logical()` direct rewrite 수정
- `space_to_process`를 실제 OOS I/O 비용이나 logical value 크기까지 포함하는 새로운 cost model로 재설계
- OOS attribute Resolve 자체의 최적화 또는 OOS value-chain reuse
- physical `heap_compact_pages()` / `spage_compact()` 변경
- unloaddb 및 일반 client raw fetch 정책 변경

## 6. Proposed Design

### 6.1 권장안: 공용 함수에 consumption policy 전달

`xlocator_lock_and_fetch_all()`에 `HEAP_RECDES_CONSUMPTION_POLICY` 인자를 추가한다.

```c
int xlocator_lock_and_fetch_all (...,
                                 LC_COPYAREA **fetch_area,
                                 MVCC_SNAPSHOT *mvcc_snapshot,
                                 HEAP_RECDES_CONSUMPTION_POLICY recdes_consumption_policy);
```

현재 caller는 두 곳이며 모두 OOS-aware attribute 계층을 사용한다.

| caller | 후속 소비 | 전달 정책 |
|--------|-----------|-----------|
| `compactdb_sr.c:process_class()` | `desc_disk_to_attr_info()` -> `heap_attrinfo_read_dbvalues()` | `HEAP_RECDES_DONT_CONSUME_RAW_BYTES` |
| `locator_sr.c:heap_upgrade_domain()` 계열 | `heap_attrinfo_read_dbvalues()` | `HEAP_RECDES_DONT_CONSUME_RAW_BYTES` |

함수 내부의 모든 최종 fetch에 전달받은 정책을 사용한다.

```text
[instance lock 있음]
heap_next(... RAW_BYTES_NOT_CONSUMED)     OID 탐색
lock_object(...)
heap_get_visible_version(... recdes_consumption_policy)

[instance lock 없음]
heap_next(... recdes_consumption_policy)
```

OID 탐색용 첫 `heap_next()`는 raw record body를 소비하지 않으므로 계속 `HEAP_RECDES_DONT_CONSUME_RAW_BYTES`로 고정한다.

이 안을 권장하는 이유는 다음과 같다.

1. 함수 이름만 보고 future caller가 raw bytes 소비 여부를 알 수 없으므로 caller가 정책을 선택하게 해야 한다.
2. PR #7416의 목표인 compile-time consumption-policy 선택을 locator helper 경계에서도 유지한다.
3. 나중에 raw `LC_COPYAREA` consumer가 추가되더라도 함수 내부 hardcode를 조용히 공유하지 않는다.

### 6.2 대안: 함수 내부에서 NOT_CONSUMED 고정

현재 두 caller가 모두 attribute 소비자이므로 `xlocator_lock_and_fetch_all()` 내부를 바로 `HEAP_RECDES_DONT_CONSUME_RAW_BYTES`로 고정할 수도 있다. 변경량은 작지만 다음 단점이 있다.

- 함수의 public declaration만으로 stored-form 반환 계약이 드러나지 않는다.
- future raw consumer가 추가될 때 compile-time 검토가 강제되지 않는다.
- PR #7416에서 locator helper까지 policy를 전달한 방향과 맞지 않는다.

따라서 함수 주석과 이름으로 stored-only 계약을 강하게 제한할 계획이 아니라면 권장하지 않는다.

### 6.3 Budget 계산

별도의 `stored_length` 필드를 추가하지 않는다. Expand를 끄면 `LC_COPYAREA_ONEOBJ.length`에 stored `recdes.length`가 들어가므로 기존 `process_class()`의 조건과 차감식이 그대로 올바른 기준을 사용한다.

다만 future regression을 막기 위해 해당 위치에 다음 의미를 주석으로 남긴다.

```c
/* fetch_area keeps the stored RECDES form. Use its physical length for the
 * per-request Compactdb processing budget; OOS values are resolved later by
 * heap_attrinfo_read_dbvalues(). */
```

변수명을 바꿀 필요는 없지만, review에서 의미가 불명확하면 다음 local alias를 사용할 수 있다.

```c
const int stored_recdes_length = obj->length;
```

그 뒤 big-object 판정과 차감에 alias를 사용하면 expanded length가 다시 들어오는 실수를 더 쉽게 발견할 수 있다.

## 7. File-Level Change Plan

### 7.1 `src/base/xserver_interface.h`

- `xlocator_lock_and_fetch_all()` declaration에 `HEAP_RECDES_CONSUMPTION_POLICY` 인자를 추가한다.
- 필요한 type visibility가 이미 `heap_file.h` include를 통해 제공되는지 확인한다. 직접 include 추가가 필요하면 include cycle을 점검한다.

### 7.2 `src/transaction/locator_sr.c`

- function definition과 header comment에 `recdes_consumption_policy`를 추가한다.
- entry에서 `HEAP_IS_VALID_RECDES_CONSUMPTION_POLICY()`로 assert한다.
- lock 분기의 `heap_get_visible_version()`에 전달받은 정책을 사용한다.
- no-lock 분기의 `heap_next()`에도 전달받은 정책을 사용한다.
- OID 탐색용 첫 `heap_next()`는 `HEAP_RECDES_DONT_CONSUME_RAW_BYTES`를 유지한다.
- `S_DOESNT_FIT` retry는 raw bytes가 consumed될 때만 OOS Expand 때문에 추가로 발생할 수 있지만, 기존 generic oversized-record 계약은 유지한다. 코드를 삭제하지 않는다.

### 7.3 `src/storage/compactdb_sr.c`

- `xlocator_lock_and_fetch_all()` 호출에 `HEAP_RECDES_DONT_CONSUME_RAW_BYTES`를 전달한다.
- `obj->length`가 stored length라는 주석 또는 `stored_recdes_length` alias를 추가한다.
- `desc_disk_to_attr_info()`와 `heap_attrinfo_read_dbvalues()`는 그대로 유지한다.
- `locator_attribute_info_force()` write path도 그대로 유지한다. 이 경로가 update 시 정상 OOS Demotion을 수행한다.

### 7.4 Domain upgrade caller (`src/transaction/locator_sr.c`)

- `xlocator_lock_and_fetch_all()` 호출에 `HEAP_RECDES_DONT_CONSUME_RAW_BYTES`를 전달한다.
- 후속 `heap_attrinfo_read_dbvalues()`가 OOS inline stub을 Resolve하는지 OOS-backed fixture로 확인한다.

### 7.5 변경하지 않는 파일

- `src/executables/compactdb.c`: standalone 후속 이슈 소관
- `src/storage/heap_oos.cpp`: consumption policy의 기존 Expand/보존 동작 사용
- `src/storage/heap_file.c`: fetch API가 전달받은 policy를 이미 처리함
- `src/storage/heap_file.c:heap_compact_pages()`: physical compaction은 OOS inline stub 보존

## 8. Correctness Invariants

수정 후 다음 조건이 유지되어야 한다.

1. `LC_COPYAREA`의 record는 stored-form `RECDES`이며 OOS inline stub과 `OR_MVCC_FLAG_HAS_OOS`를 보존한다.
2. `heap_attrinfo_read_dbvalues()` 이후 `HEAP_CACHE_ATTRINFO.values[]`에는 logical DB_VALUE가 들어간다.
3. Compactdb가 dangling OID 또는 old representation을 수정하면 `locator_attribute_info_force()`가 새 record에 정상 OOS Demotion을 적용한다.
4. `obj->length`는 `space_to_process` 계산 동안 stored length다.
5. `stored length < max budget < expanded length`인 row는 `big_objects`로 분류되지 않는다.
6. stored length 자체가 `max_space_to_process`보다 큰 일반 record는 기존과 같이 `big_objects`로 분류된다.
7. 현재 요청의 남은 예산만 부족한 row는 `last_processed_oid` rollback 후 다음 요청에서 처리된다.
8. lock 실패, snapshot visibility, `S_DOESNT_FIT`, copyarea ownership 계약은 바뀌지 않는다.

## 9. Test Plan

### 9.1 단위 수준: policy와 반환 형태

가능하면 `xlocator_lock_and_fetch_all()` 또는 그 하위 fetch를 직접 호출하는 test fixture를 추가한다.

1. OOS inline target을 넘는 `BIT VARYING` 값을 가진 row를 만든다.
2. `HEAP_RECDES_DONT_CONSUME_RAW_BYTES`로 fetch한다.
3. 반환 `RECDES`에 `OR_MVCC_FLAG_HAS_OOS`가 남아 있는지 확인한다.
4. 반환 길이가 expanded logical length보다 작고 stored record length와 같은지 확인한다.
5. 같은 `RECDES`를 `heap_attrinfo_read_dbvalues()`로 읽어 원본과 byte-identical한 DB_VALUE를 얻는지 확인한다.

### 9.2 Server Compactdb budget 판별 TC

핵심 TC는 다음 부등식을 만족해야 한다.

```text
stored record length < max_space_to_process < expanded logical length
```

권장 fixture:

- `BIT VARYING` 50KB 이상을 사용해 multi-chunk OOS value를 만든다.
- heap record는 OOS inline stub으로 작게 유지한다.
- `space_to_process`는 stored record보다 크고 50KB보다 작은 값으로 설정한다. 예: 16KB. 정확한 stored length는 test helper로 읽어 조건을 assert한다.
- server Compactdb phase 1을 한 cycle 실행한다.

검증:

- `big_objects`가 expansion만을 이유로 증가하지 않는다.
- `total_objects`에 해당 row가 포함된다.
- `last_processed_oid`가 해당 row 앞에서 멈추지 않는다.
- Compactdb 후 logical `BIT VARYING` 값이 byte-identical하다.
- debug 환경에서는 불필요한 record-level Expand가 발생하지 않았음을 OOS read trace 또는 breakpoint/counter로 확인한다. 안정적인 counter가 없다면 `RECDES`의 HAS_OOS flag 보존을 직접 assert한다.

### 9.3 기존 big object 동작 보존 TC

OOS를 사용하지 않고 stored record 자체가 `max_space_to_process`보다 큰 fixture를 만든다.

검증:

- `big_objects`가 1 증가한다.
- 해당 object는 기존과 같이 건너뛴다.
- 다음 object scan과 lock 해제가 정상이다.

이 TC는 "모든 big object skip을 제거했다"는 잘못된 구현을 막는다.

### 9.4 Remaining-budget defer 동작 보존 TC

각 record의 stored length는 최대 예산보다 작지만 두 record의 합이 한 요청 예산을 넘도록 만든다.

검증:

- 첫 요청에서 두 번째 row를 big object로 세지 않는다.
- `space_to_process`가 0이 되고 `last_processed_oid`가 이전 row로 돌아간다.
- 다음 요청에서 두 번째 row가 처리된다.

### 9.5 Domain upgrade 회귀 TC

OOS-backed attribute가 있는 class에서 domain upgrade 경로가 실행되는 fixture가 가능하면 추가한다.

검증:

- stored-form fetch 후 `heap_attrinfo_read_dbvalues()`가 값을 정상 Resolve한다.
- upgrade 전후 OOS-backed attribute가 byte-identical하다.
- update가 필요하면 새 record가 정상 OOS Demotion을 거친다.

재현 가능한 domain-upgrade fixture를 기존 regression suite에서 찾지 못하면 기존 test 위치와 수동 검증 절차를 PR에 기록하고, 자동 TC 추가 여부를 review에서 결정한다.

### 9.6 Build 및 regression

- debug GCC build와 configured unit tests
- SQL regression tests
- Compactdb utility regression tests
- OOS multi-chunk read/update regression
- `git diff --check`와 C/C++ formatting check

## 10. Risk Analysis

| 위험 | 설명 | 대응 |
|------|------|------|
| 숨은 raw consumer | `xlocator_lock_and_fetch_all()`의 외부 caller가 source grep에 잡히지 않거나 향후 추가될 수 있음 | policy 인자를 API에 추가해 compile-time 선택 강제, 전체 link/build 수행 |
| attribute Resolve 누락 | 특정 old representation/type이 `heap_attrinfo_read_dbvalues()`에서 OOS를 처리하지 못할 수 있음 | VARBIT multi-chunk와 old representation fixture로 검증 |
| budget 의미 변경 논쟁 | logical payload 크기를 예산에 포함해야 한다는 해석 가능 | 기존 OOS 이전 semantics와 stored-record 처리 단위를 문서화하고 review에서 확정 |
| OOS I/O 폭증 | record Expand는 제거되지만 Compactdb가 모든 attribute를 읽으면 결국 OOS Resolve가 발생할 수 있음 | 정확성에는 영향 없음. attribute selective read 최적화는 별도 범위 |
| `S_DOESNT_FIT` 처리 회귀 | Expand 제거 후 해당 분기 실행 빈도가 줄어 미사용처럼 보일 수 있음 | generic oversized stored record를 위해 retry 코드 유지 |
| update OOS 배치 회귀 | stored stub을 attr layer로 읽은 뒤 update 시 Demotion이 누락될 가능성 | `locator_attribute_info_force()` 유지 및 forced-update TC에서 새 `oos_insert` 확인 |

## 11. Review Decisions Needed

구현 전에 다음 세 가지를 review에서 확정한다.

1. `space_to_process`를 stored record bytes 예산으로 유지하는가?
   - 권장: 유지한다. OOS 도입 전 Compactdb가 처리하던 physical record length 의미와 같다.
2. `xlocator_lock_and_fetch_all()`에 policy 인자를 추가하는가, stored-form 반환으로 hardcode하는가?
   - 권장: policy 인자를 추가한다. future caller의 raw-byte 계약을 compile time에 드러낸다.
3. Domain upgrade 자동 TC를 이번 수정의 merge gate로 둘 수 있는가?
   - 권장: 기존 fixture가 있으면 포함한다. fixture 신규 구축 비용이 크면 OOS-backed 수동 검증을 남기고 별도 TC task로 분리한다.

## 12. Implementation Order

1. `xlocator_lock_and_fetch_all()` declaration/definition에 consumption policy를 추가한다.
2. 현재 두 caller를 `HEAP_RECDES_DONT_CONSUME_RAW_BYTES`로 명시한다.
3. 함수 내부 lock/no-lock 최종 fetch에 policy를 전달한다.
4. `compactdb_sr.c` budget 위치에 stored-length 계약을 주석 또는 alias로 남긴다.
5. build로 누락 caller와 signature mismatch를 검출한다.
6. budget 판별 TC, 기존 big-object TC, remaining-budget defer TC를 추가한다.
7. domain upgrade와 Compactdb forced-update 회귀를 검증한다.
8. SQL/utility regression을 수행하고 PR description에 AS-IS/TO-BE 및 test evidence를 기록한다.

## 13. Acceptance Criteria

- [ ] `xlocator_lock_and_fetch_all()`의 모든 caller가 `HEAP_RECDES_CONSUMPTION_POLICY`를 명시한다.
- [ ] Server Compactdb와 domain upgrade는 `HEAP_RECDES_DONT_CONSUME_RAW_BYTES`를 사용한다.
- [ ] OOS-backed row의 fetch area에는 stored-form `RECDES`와 OOS inline stub이 유지된다.
- [ ] `heap_attrinfo_read_dbvalues()` 이후 logical value가 원본과 byte-identical하다.
- [ ] `stored length < max_space_to_process < expanded length`인 row가 `big_objects`에 포함되지 않고 처리된다.
- [ ] stored length 자체가 최대 예산보다 큰 row의 기존 big-object skip은 유지된다.
- [ ] 현재 요청의 남은 예산만 부족한 row는 다음 요청에서 처리된다.
- [ ] Compactdb가 실제 update한 OOS-backed row는 정상 OOS Demotion을 거친다.
- [ ] Domain upgrade 경로에서 OOS-backed attribute 값이 보존된다.
- [ ] build, configured tests, SQL/Compactdb regression이 통과한다.

## 14. Source References

- `src/storage/compactdb_sr.c`: `process_class()`, `desc_disk_to_attr_info()`, `boot_compact_db()`
- `src/transaction/locator_sr.c`: `xlocator_lock_and_fetch_all()`, domain upgrade caller
- `src/base/xserver_interface.h`: `xlocator_lock_and_fetch_all()` declaration
- `src/storage/heap_file.c`: `heap_next()`, `heap_get_visible_version()`, `heap_init_get_context()`
- `src/storage/heap_oos.cpp`: `heap_record_replace_oos_oids()`
- `src/storage/heap_file.h`: `HEAP_RECDES_CONSUMPTION_POLICY`
- CBRD-26948 technical review: `CBRD-26948-unloaddb-compactdb-oos-technical-review.md`
