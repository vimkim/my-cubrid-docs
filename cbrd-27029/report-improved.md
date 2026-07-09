# Parallel Heap Scan 과 OOS Expand 정책 검토 보고

## 1. 요약

개발4팀 일한님과 `parallel heap scan` 처리 흐름을 확인한 결과, `parallel heap scan` 은 heap record 전체를 그대로 복사하지 않고 필요한 컬럼만 `DB_VALUE` 로 변환한 뒤 temp file 또는 permanent temp file 의 tuple 로 다시 작성하는 구조입니다.

따라서 OOS 관점에서는 불필요한 record-level expand 를 수행할 필요가 없습니다. 필요한 컬럼이 OOS 컬럼이면 attribute layer 에서 해당 컬럼만 `oos_read()` 로 처리되고, 필요하지 않은 OOS 컬럼은 읽지 않습니다.

결론적으로 `parallel heap scan` 경로는 정합성을 깨지 않으면서도 OOS 도입으로 기대한 성능 개선 효과를 그대로 얻을 수 있습니다.

## 2. 확인한 처리 흐름

`parallel heap scan` 의 기본 흐름은 다음과 같습니다.

```text
heap scan
  -> 필요한 컬럼만 DB_VALUE 로 변환
  -> mr_data_writeval
  -> temp file tuple 작성
```

이 과정에서 중요한 점은 "필요한 컬럼만" 변환한다는 점입니다.

- OOS 컬럼이 필요하지 않은 경우: `oos_read()` 가 발생하지 않습니다. 불필요한 OOS I/O 가 제거되므로 heap scan 성능이 개선됩니다.
- OOS 컬럼이 필요한 경우: 해당 컬럼만 attribute layer 에서 자동으로 `oos_read()` 처리된 뒤 `mr_data_writeval` 로 기록됩니다. 필요한 값은 정상적으로 복원되므로 정합성 문제가 없습니다.

즉, `parallel heap scan` 자체에서 OOS 를 별도로 의식하거나 추가 처리할 필요는 없습니다.

## 3. Heap API 검토 결과

`parallel heap scan` 에서 주로 사용하는 heap 관련 API 를 함께 검토했습니다. `heap_1page` 계열을 포함한 일반적인 heap scan 경로는 필요한 컬럼을 `attrinfo` 기반으로 읽기 때문에 OOS 컬럼도 attribute layer 에서 자연스럽게 처리됩니다.

이 검토 결과를 기준으로 보면, 일반적인 heap API 사용 경로의 대부분은 `HEAP_WITHOUT_OOS_EXPAND` 로 최적화할 수 있습니다. 전체 record 를 미리 expand 하지 않아도 필요한 컬럼 단위로 OOS 값이 resolve 되기 때문입니다.

반대로 `HEAP_WITH_OOS_EXPAND` 가 필요한 경로는 제한적입니다. 대표적으로 네트워크를 통해 raw `recdes` 를 전달하는 locator 계열 경로, `catalog_class`, `system_catalog` 처럼 raw record 자체를 직접 해석하거나 전달하는 경로는 보수적으로 expand 를 유지하는 것이 안전합니다.

- system_catalog, catalog_class 는 현재 OOS를 아예 사용하지 않는 것으로 추정되므로 영향이 없을 수 있습니다.

## 4. 권고 사항

현재 PR 은 이 방향대로 머지해도 된다고 판단합니다.

권고하는 정책은 다음과 같습니다.

1. 기본값은 `HEAP_WITHOUT_OOS_EXPAND` 로 둡니다.
2. attribute layer 를 통해 필요한 컬럼만 읽는 일반 heap scan 경로는 record-level expand 를 수행하지 않습니다.
3. 네트워크를 통해 raw `recdes` 를 전달하는 locator 경로만 별도 API 로 분리합니다.
4. 예를 들어 `locator_fetch_all_network()` 와 같이 목적이 명확한 API 를 만들고, 이 경로에서는 `HEAP_WITH_OOS_EXPAND` 를 명시적으로 사용합니다.
5. `catalog_class`, `system_catalog` 등 자체 raw record 해석 가능성이 있는 경로는 보수적으로 `HEAP_WITH_OOS_EXPAND` 를 유지합니다. (확인 필요)

## 5. 결론

`parallel heap scan` 은 필요한 컬럼만 변환하는 구조이므로, OOS 컬럼이 필요하지 않은 쿼리에서는 `oos_read()` 없이 동작할 수 있습니다. OOS 컬럼이 필요한 쿼리에서도 attribute layer 가 해당 컬럼만 resolve 하므로 정합성은 유지됩니다.

따라서 OOS expand 정책은 전체적으로 `HEAP_WITHOUT_OOS_EXPAND` 를 기본값으로 가져가고, raw `recdes` 를 외부로 전달하거나 직접 해석하는 일부 경로에만 `HEAP_WITH_OOS_EXPAND` 를 명시하는 방식이 가장 합리적입니다.
