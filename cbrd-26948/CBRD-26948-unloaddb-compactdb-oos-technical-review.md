# CBRD-26948 unloaddb/compactdb OOS 연동 기술 검토

검토 기준은 PR #7416 HEAD `f59e9b8b2d` (2026-07-13)다. OOS 용어와 요구 동작은 같은 날짜의 `OOS-CONTEXT.md`를 따른다.

## 1. Conclusion

CBRD-26948에서 처음 발견한 `unloaddb` 문제의 핵심은 맞다. `unloaddb`는 heap의 raw `RECDES`를 `LC_COPYAREA`로 받아 OOS를 모르는 `desc_disk_to_obj()`로 해석하므로, 서버가 전송 전에 OOS inline stub을 실제 값으로 Expand해야 한다.

다만 현재 이슈 문서에는 수정 주체와 Compactdb 동작이 섞여 있다.

1. `xlocator_fetch_all()`의 OOS Expand 복구는 CBRD-27029가 아니라 CBRD-26818, commit `1561c3b9c`에서 이미 반영됐다. PR #7416의 첫 commit은 이 동작을 `HEAP_WITH_OOS_EXPAND`라는 명시적 정책으로 표현했고, 두 번째 commit은 별도의 단건 client fetch 경로를 수정했다.
2. Compactdb는 하나의 동작이 아니다. standalone phase 1, server phase 1, heap page physical compaction을 분리해서 판단해야 한다.
3. standalone Compactdb의 읽기에는 Expand가 필요하지만, Expand된 값을 `desc_obj_to_disk()`로 다시 직렬화해 `heap_update_logical()`로 직접 기록하는 현재 쓰기 경로는 정상 OOS Demotion 경로를 우회한다. 이 부분이 남은 핵심 연동 gap이다.
4. server Compactdb는 `HEAP_CACHE_ATTRINFO`가 OOS-backed attribute를 Resolve할 수 있으므로 record-level Expand가 필요하지 않다. Expand된 `obj->length`가 `max_space_to_process`보다 크면 실제 stored record는 작아도 big object로 분류되어 건너뛸 수 있다. 최대 예산은 충분하고 현재 호출의 남은 예산만 부족하면 다음 호출로 미룬다.
5. `heap_compact_pages()`의 `spage_compact()`는 물리 record bytes만 이동한다. OOS inline stub을 그대로 보존해야 하며 Expand해서는 안 된다.

따라서 CBRD-26948은 이미 반영된 unloaddb 회귀 복구를 검증하는 범위와, 아직 해결되지 않은 Compactdb/OOS 연동 범위를 구분해야 한다. 구현 티켓까지 명확히 하려면 Compactdb 후속을 별도 이슈로 분리하는 편이 가장 이해하기 쉽다.

## 2. Decision Rules

OOS (Out-of-row Overflow Storage)는 큰 가변 attribute 값을 OOS value chain에 저장하고, heap record에는 16-byte OOS inline stub만 남긴다. 이 stub은 8-byte head OOS OID와 8-byte full length로 구성된다.

동일한 heap record라도 소비 방식에 따라 필요한 정책이 다르다.

| 소비 방식 | 올바른 정책 | 이유 | 대표 경로 |
|-----------|-------------|------|-----------|
| raw `RECDES`를 전송, raw parse, 재삽입, byte 비교 | OOS Expand | 소비자가 OOS inline stub을 해석할 수 없다 | `unloaddb`, standalone Compactdb의 `desc_disk_to_obj()` |
| `HEAP_CACHE_ATTRINFO` 등 OOS-aware attribute 계층 | OOS Resolve | 필요한 attribute만 `oos_read()`로 읽을 수 있다 | server Compactdb, 일반 query attribute read |
| page/record의 물리 바이트 이동 | stub 보존 | 논리 값이 아니라 저장 구조를 다룬다 | `spage_compact()` |

이 기준에서 중요한 점은 "값을 읽는다"만으로 Expand를 선택하지 않는다는 것이다. `SELECT`와 server Compactdb처럼 attribute 계층을 거치는 경로는 record 전체를 Expand할 필요가 없다. 반대로 raw `RECDES`를 OOS-blind decoder에 넘기는 경로는 전송 위치나 실행 모드와 관계없이 Expand가 필요하다.

이 정책 enum의 이름은 `HEAP_RECDES_CONSUMPTION_POLICY`가 적절하다. 정책의 원인이 OOS 자체가 아니라 반환된 `RECDES`의 소비 방식임을 드러내기 때문이다. enum 값은 다음처럼 직접적인 이름이 읽기 쉽다.

| 후보 | 의미 | 평가 |
|------|------|------|
| `HEAP_RECDES_RAW_BYTES_CONSUMED` / `HEAP_RECDES_RAW_BYTES_NOT_CONSUMED` | 반환된 raw record bytes가 실제로 소비되는지를 직접 구분 | 가장 권장한다. record body를 읽지 않는 caller까지 포함하며 CBRD-27029의 binary criterion과 일치한다. |
| `HEAP_RECDES_EXPAND_OOS` / `HEAP_RECDES_PRESERVE_OOS` | 결과 형태를 직접 표현 | 구현 동작은 명확하지만 호출자의 의도가 덜 보인다. |
| `HEAP_RECDES_MATERIALIZED` / `HEAP_RECDES_STORED` | materialized record와 저장형 record를 구분 | 개념은 정확하지만 `MATERIALIZED`의 의미를 별도로 배워야 한다. |

`HEAP_RECDES_RAW_BYTES_NOT_CONSUMED`는 attribute 계층이 OOS Resolve를 수행하는 경로뿐 아니라 record body를 읽지 않는 경로도 포함한다. 실제로 raw bytes를 parse, 전송, 재삽입 또는 비교하는지가 policy 선택 기준이다.

## 3. Fix Ownership

| 시점 | 변경 | 실제 의미 |
|------|------|-----------|
| `a8a192f33`, PR #6766, CBRD-26458 | unloaddb 지원을 위해 OOS 값을 record에 펼침 | raw decoder에 OOS OID가 노출되지 않도록 한 최초 변경 |
| `4a6805e37`, PR #7093, CBRD-26729 | record-level Expand를 opt-in으로 전환 | 필요한 caller 누락 시 raw consumer에 stub이 노출되는 회귀 가능성이 생김 |
| `1561c3b9c`, PR #7337, CBRD-26818 | `xlocator_fetch_all()`을 `heap_next_expand_oos()`로 변경하고 copyarea ownership 및 `S_DOESNT_FIT` 처리 보강 | unloaddb와 standalone Compactdb의 주 fetch 경로를 실제로 복구 |
| `309753de6`, PR #7416, CBRD-27029 | bool 성격의 호출을 `HEAP_WITH_OOS_EXPAND`/`HEAP_WITHOUT_OOS_EXPAND`로 명시 | 위 동작을 enum으로 표현한 policy refactoring |
| `f59e9b8b2`, PR #7416, CBRD-27029 | `locator_lock_and_return_object()`에서 Expand | 별도의 단건 client fetch raw-record 노출을 수정 |

`git blame 5b5ff588f -L 2895,2920 -- src/transaction/locator_sr.c`에서도 `xlocator_fetch_all()`의 Expand 호출은 `1561c3b9c` 소유로 확인된다. 따라서 "PR #7416이 CBRD-26948의 unloaddb 본체를 수정했다"고 적으면 기술적으로 부정확하다.

## 4. unloaddb

### 4.1 호출 흐름

```text
unloaddb
  locator_fetch_all()
    -> server/SA xlocator_fetch_all()
       -> heap_next(..., HEAP_WITH_OOS_EXPAND)
       -> expanded RECDES를 LC_COPYAREA에 적재
    -> desc_disk_to_obj()                 src/loaddb/load_object.c
       -> raw object representation parse
```

`desc_disk_to_obj()`는 raw object representation을 읽지만 OOS inline stub을 Resolve할 수 없다. 그러므로 Expand는 decoder보다 앞선 heap fetch 경계에서 일어나야 한다. 이 요구는 unloaddb를 구체적으로 주석이나 commit/JIRA에 명시할 가치가 있다. 다만 enum 이름 자체를 `UNLOADDB`에 종속시키면 같은 raw consumer인 Compactdb와 단건 client fetch를 설명하지 못한다.

### 4.2 데이터 손실 표현

이 경로는 원본 database를 수정하지 않는다. 관측되는 실패는 OOS-backed attribute가 `X''` 등 잘못된 값으로 dump되는 "export/dump 값 손실"이다. database 내부 데이터 손실이라고 쓰면 영향 범위를 과장한다.

### 4.3 현재 상태

PR #7416 HEAD에서는 `xlocator_fetch_all()`이 `HEAP_WITH_OOS_EXPAND`를 사용한다. 코드상 회귀는 CBRD-26818에서 복구된 상태지만, CS와 SA mode에서 byte equality 및 multi-chunk 값을 검증해야 완료로 판단할 수 있다.

## 5. Compactdb Flows

Compactdb라는 이름 아래 서로 다른 세 작업이 있다.

| 구분 | 구현 | 목적 | OOS 정책 |
|------|------|------|----------|
| standalone phase 1 | `src/executables/compactdb.c` (`sa/CMakeLists.txt`) | instance를 decode해 dangling OID/object reference와 old representation을 정리하고, 변경 시 다시 기록 | read는 Expand 필요, write는 OOS-aware Demotion 필요 |
| server phase 1 | `src/storage/compactdb_sr.c` | lock한 instance를 `HEAP_CACHE_ATTRINFO`로 읽어 같은 논리 정리를 수행하고 정상 locator update 경로로 기록 | record Expand 불필요, attribute Resolve 사용 |
| physical page compaction | `heap_compact_pages()` -> `spage_compact()` | page 내 record bytes를 재배치해 빈 공간을 모음 | OOS inline stub을 그대로 보존 |

### 5.1 Standalone phase 1: read에는 Expand가 필요하다

`src/executables/compactdb.c`는 CS client 파일이 아니라 `sa/CMakeLists.txt`에 포함되는 standalone 구현이다. 다만 object workspace 계열의 raw decoder를 사용한다.

```text
locator_fetch_all()
  -> xlocator_fetch_all()
     -> HEAP_WITH_OOS_EXPAND
  -> desc_disk_to_obj()
  -> process_value()
     -> dangling OID/object reference 정리
  -> 변경된 경우 disk_update_instance()
```

`desc_disk_to_obj()`는 OOS를 모르므로 이 경로에서 Expand를 제거하면 안 된다. 읽기 관점에서는 unloaddb와 같은 raw-consumer 규칙이 적용된다.

### 5.2 Standalone phase 1: direct rewrite가 OOS Demotion을 우회한다

변경된 object는 다음 경로로 기록된다.

```text
disk_update_instance()
  -> desc_obj_to_disk()       logical DB_VALUE를 일반 inline record로 직렬화
  -> heap_update_logical()    만들어진 RECDES를 직접 update
```

정상 INSERT/UPDATE는 `heap_attrinfo_determine_disk_layout()`에서 PG-style four-record heap target을 기준으로 큰 가변 값을 OOS로 Demotion하고 OOS inline stub을 만든다. 현재 standalone Compactdb의 direct rewrite는 `HEAP_CACHE_ATTRINFO`와 이 transformation을 거치지 않는다.

그 결과를 "즉시 데이터 손실"로 단정하면 안 된다. Expand된 logical value는 다시 직렬화되므로 값 자체는 유지될 수 있다. 그러나 새 record에는 OOS stub이 없고, SA mode의 `heap_oos_delete_unreferenced()`는 old record가 소유한 OOS value chain을 정리한다. 따라서 갱신된 row가 완전 inline 또는 `REC_BIGONE` 형태로 바뀌어 OOS 배치 정책과 I/O 이점을 잃을 수 있고, 큰 record의 크기 제한 및 실패 경로도 달라진다.

권장 방향은 standalone phase 1도 server 구현처럼 `HEAP_CACHE_ATTRINFO`와 `locator_attribute_info_force()` 또는 동등한 정상 OOS-aware transformation 경로를 사용하는 것이다. 단순히 Expand된 `RECDES`를 `heap_update_logical()`에 직접 넘기는 방식은 피해야 한다.

### 5.3 Server phase 1: Expand가 중복이며 처리 예산을 왜곡한다

Server 구현은 raw decoder를 쓰지 않는다.

```text
xlocator_lock_and_fetch_all()
  -> 현재 expanded RECDES 반환
  -> obj->length로 space_to_process 차감/큰 object 판정
  -> desc_disk_to_attr_info()
     -> heap_attrinfo_read_dbvalues()      OOS-backed attribute를 lazy Resolve
  -> process_object()
  -> locator_attribute_info_force()       정상 transformation/Demotion 경로
```

`heap_attrinfo_read_dbvalues()`가 OOS inline stub을 이해하므로 record-level Expand는 정확성을 위해 필요하지 않다. 오히려 현재는 Expand 후의 logical record length를 `space_to_process`와 비교한다. heap에는 작은 stub record로 저장된 OOS value라도 expanded `obj->length > max_space_to_process`이면 big object로 분류되어 건너뛴다. `obj->length`가 최대 예산 이하지만 현재 호출의 남은 예산만 초과하면 `last_processed_oid`를 되돌리고 다음 호출로 미룬다.

권장 방향은 이 caller가 stored-form `RECDES`를 받게 하고 attribute 계층에서 필요한 값만 Resolve하도록 하는 것이다. 처리 예산도 page/heap processing 비용을 나타내려면 stored record length를 기준으로 계산해야 한다. `xlocator_lock_and_fetch_all()`의 다른 직접 caller인 domain upgrade 경로도 곧바로 `heap_attrinfo_read_dbvalues()`를 사용하므로, 함수 전체를 no-Expand로 바꾸거나 consumption policy를 인자로 받을 수 있다. 변경 전 모든 caller 계약을 다시 확인해야 한다.

### 5.4 Physical page compaction: OOS를 읽거나 다시 쓰지 않는다

`heap_compact_pages()`는 각 heap page에 `spage_compact()`를 호출한다. 이 함수는 slot이 가리키는 physical record bytes를 page 안에서 옮길 뿐 attribute 값을 decode하지 않고 OOS file도 수정하지 않는다.

따라서 이 경로는 OOS inline stub을 그대로 보존하는 것이 맞다. Expand하면 record 크기가 변해 slot/page 레이아웃의 의미를 깨뜨린다. Compactdb phase 1의 논리 정리와 physical page compaction을 같은 "compact" 동작으로 설명해서는 안 된다.

## 6. Findings

| 우선순위 | finding | 상태 / 조치 |
|----------|---------|-------------|
| 높음 | standalone Compactdb rewrite가 정상 OOS Demotion을 우회한다 | 별도 구현 또는 CBRD-26948 잔여 범위로 수정 필요 |
| 중간 | server Compactdb가 불필요하게 Expand하고, expanded length가 최대 예산을 넘으면 big object로 건너뛴다 | stored-form fetch + attribute Resolve로 변경 검토 |
| 중간 | unloaddb 회귀의 fix ownership이 기존 issue에 잘못 기록됐다 | CBRD-26818로 정정하고 CS/SA E2E 검증 |
| 중간 | standalone Compactdb의 영구 데이터 손실은 재현 없이 확정적으로 서술됐다 | OOS 배치 손실은 코드상 gap, logical value loss는 강제 rewrite TC로 검증 |
| 낮음 | physical compaction과 logical Compactdb가 혼용됐다 | 호출 흐름과 acceptance criteria를 분리 |

## 7. Recommended Issue Split

가장 명확한 구성은 다음과 같다.

1. CBRD-26948: unloaddb raw-fetch 회귀 기록 및 CBRD-26818 수정 검증
   - CS/SA mode dump byte equality
   - multi-chunk OOS value
   - fix ownership 정정
2. Compactdb OOS integration 후속 이슈
   - standalone read는 Expand 유지
   - standalone rewrite를 OOS-aware Demotion 경로로 통합
   - server phase 1의 불필요한 Expand와 processing-budget 기준 수정
   - physical compaction stub 보존 TC
3. CBRD-27029
   - single-object client fetch Expand 및 `S_DOESNT_FIT` grow/retry 검증

한 이슈에 유지한다면 최소한 "이미 수정됨", "남은 구현", "검증만 필요"를 표로 나눠야 한다.

## 8. Acceptance Tests

| 대상 | 시나리오 | 검증값 |
|------|----------|--------|
| unloaddb CS/SA | OOS-backed `BIT VARYING`, OOS inline target 초과, multi-chunk 값 export | dump reload 후 byte equality, 빈 값 없음 |
| standalone Compactdb no-change | OOS-backed row를 정리하되 update 조건 없음 | logical value 동일, OOS 배치 유지 |
| standalone Compactdb forced rewrite | dangling OID 또는 old representation으로 실제 update 유도 | byte equality, update 후 다시 OOS-backed 상태/Demotion 확인 |
| server Compactdb budget | `stored length < max_space_to_process < expanded length`인 row | expansion만으로 `big_objects`가 증가하지 않고 row가 처리됨 |
| physical compaction | OOS-backed row가 있는 heap page compact | 같은 slot의 stored `RECDES`를 compact 전후 byte-compare하고 이후 SELECT byte equality 확인 |
| CBRD-27029 별도 검증 | copyarea보다 큰 single-object CS fetch | CBRD-26948 범위 밖. byte equality와 `S_DOESNT_FIT` grow/retry를 CBRD-27029에서 확인 |

OOS 배치 자체는 release build SQL만으로 직접 확인하기 어렵다. 현재는 debug `oos.log`의 `oos_insert` 기록을 사용하고, CBRD-26871의 관측 기능이 들어오면 그 방식으로 교체한다. 테스트 데이터는 압축으로 크기가 달라지는 `VARCHAR`보다 `BIT VARYING`을 사용한다.

## 9. Source References

- `src/transaction/locator_sr.c`: `xlocator_fetch_all()`, `xlocator_lock_and_fetch_all()`, `locator_lock_and_return_object()`
- `src/loaddb/load_object.c`: `desc_disk_to_obj()`, `desc_obj_to_disk()`
- `src/executables/compactdb.c`: `process_class()`, `process_object()`, `disk_update_instance()`
- `src/storage/compactdb_sr.c`: `process_class()`, `desc_disk_to_attr_info()`
- `src/storage/heap_file.c`: `heap_compact_pages()`, `heap_attrinfo_determine_disk_layout()`
- commit `1561c3b9c`: `[CBRD-26818] Preserve OOS expansion copyarea ownership (#7337)`
- PR #7416 / CBRD-27029: explicit consumption policy와 single-object client fetch
