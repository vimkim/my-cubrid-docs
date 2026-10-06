# 파티션 INSERT는 부모와 자식에서 heap insert를 각각 호출하는가?

검토 기준: `feature/oos-merge`, 커밋 `fb567a629cdb390fff920542173fa36f454c74a0` (2026-10-06 확인).

## 결론

**일반적인 한 행의 INSERT가 `locator_insert_force()` 를 통과하는 경로에서는, 저장할 자식을 먼저 선택한 뒤 그 자식을 대상으로 `heap_insert_logical()` 을 호출합니다. 부모 heap에 먼저 삽입하고 자식 heap에 다시 삽입하는 순서가 아닙니다.**

여기서 “부모”는 SQL에서 지정한 파티션 테이블이고, “자식”은 해당 행을 실제로 저장할 파티션입니다. 부모 이름으로 INSERT를 요청했다는 사실과 부모 heap에 행을 저장했다는 사실은 다릅니다.

따라서 “부모 단계에서는 OOS를 쓰지 않고, 자식이 정해진 뒤 쓴다”는 설계 방향은 검토할 수 있습니다. 구현에서는 **두 번의 heap 호출 중 하나를 건너뛰는 방식보다, 목적지 선택 전의 OOS 기록을 선택 이후로 옮기는 방식**으로 이해하는 것이 실제 호출 순서에 맞습니다.

## 한눈에 보는 실제 순서

예를 들어 부모 테이블 `orders` 에 넣을 행이 자식 `orders_p1` 에 속한다고 가정합니다.

```text
INSERT INTO orders ...
        │
        ▼
locator_insert_force()
  ① 요청받은 orders를 후보 목적지로 둠
  ② partition_prune_insert()로 orders_p1 선택
  ③ orders_p1의 테이블 식별자와 heap 식별자로 context 구성
  ④ heap_insert_logical(context) 호출
        │
        ▼
  orders_p1의 heap에 저장
```

②는 **저장 위치를 결정하는 단계**입니다. 부모에 행을 저장하는 단계가 아닙니다.

## 코드 근거: 같은 두 변수를 따라가면 된다

`class_oid` 는 테이블을 식별하고, `hfid` 는 heap 파일을 식별합니다. `real_class_oid` 와 `real_hfid` 는 이 함수에서 실제 저장 목적지를 담는 지역 변수입니다.

### 1. 처음에는 요청받은 테이블을 후보로 복사한다

[`locator_sr.c:4977–4978`](https://github.com/CUBRID/cubrid/blob/fb567a629cdb390fff920542173fa36f454c74a0/src/transaction/locator_sr.c#L4977-L4978):

```c
HFID_COPY (&real_hfid, hfid);
COPY_OID (&real_class_oid, class_oid);
```

부모 테이블로 들어온 요청이면 이 시점의 `real_*` 에는 부모 정보가 있습니다. **식별자를 복사했을 뿐, heap에 행을 삽입하지 않았습니다.**

### 2. 파티션 대상이면 같은 변수에 선택한 자식을 담는다

[`locator_sr.c:4983–4994`](https://github.com/CUBRID/cubrid/blob/fb567a629cdb390fff920542173fa36f454c74a0/src/transaction/locator_sr.c#L4983-L4994)에서 목적지를 결정합니다. 아래는 오류 처리 등을 생략한 발췌입니다.

```c
if (pruning_type != DB_NOT_PARTITIONED_CLASS)
  {
    partition_prune_insert (thread_p, class_oid, recdes, scan_cache,
                            pcontext, pruning_type,
                            &real_class_oid, &real_hfid, &superclass_oid);
  }
```

`&real_class_oid`, `&real_hfid` 는 결과를 받을 주소입니다. 따라서 이 호출 뒤에는 선택한 자식의 정보가 들어갑니다. 실제 코드는 선택에 실패하면 오류 경로로 빠지므로 아래 heap 삽입까지 진행하지 않습니다.

선택 함수 내부에서도 확인할 수 있습니다. `partition_prune_insert()` 는 `partition_find_partition_for_record()` 를 호출하고, 그 함수가 다음과 같이 선택된 자식의 정보를 복사합니다.

[`partition.c:3557–3558`](https://github.com/CUBRID/cubrid/blob/fb567a629cdb390fff920542173fa36f454c74a0/src/query/partition.c#L3557-L3558):

```c
COPY_OID (partition_oid, &pinfo->partitions[pos + 1].class_oid);
HFID_COPY (partition_hfid, &pinfo->partitions[pos + 1].class_hfid);
```

[`partition_prune_insert()` 전체](https://github.com/CUBRID/cubrid/blob/fb567a629cdb390fff920542173fa36f454c74a0/src/query/partition.c#L3605-L3689)는 파티션 정보 준비, 목적지 계산, 직접 지정한 자식과의 일치 검증, 정리를 수행합니다. 여기에는 `heap_insert_logical()` 호출이 없습니다. 필요하면 RECDES의 representation ID를 자식에 맞게 바꾸지만, 이것도 heap에 행을 삽입하는 작업은 아닙니다.

### 3. 선택이 끝난 두 변수로 heap 삽입을 요청한다

[`locator_sr.c:5063`](https://github.com/CUBRID/cubrid/blob/fb567a629cdb390fff920542173fa36f454c74a0/src/transaction/locator_sr.c#L5063)에서 삽입 인자를 구성합니다.

```c
heap_create_insert_context (&context, &real_hfid, &real_class_oid,
                            recdes, local_scan_cache);
```

이후 [`locator_sr.c:5079`](https://github.com/CUBRID/cubrid/blob/fb567a629cdb390fff920542173fa36f454c74a0/src/transaction/locator_sr.c#L5079)에서 호출합니다.

```c
if (heap_insert_logical (thread_p, &context, home_hint_p) != NO_ERROR)
```

즉, 이 호출에 전달되는 것은 **선택된 자식의 heap 정보**입니다. context 생성 과정에서도 [HFID](https://github.com/CUBRID/cubrid/blob/fb567a629cdb390fff920542173fa36f454c74a0/src/storage/heap_file.c#L21627)와 [class OID](https://github.com/CUBRID/cubrid/blob/fb567a629cdb390fff920542173fa36f454c74a0/src/storage/heap_file.c#L24901-L24917)를 그대로 복사합니다.

| 요청 | 파티션 선택 단계 | heap 삽입 대상 |
|---|---|---|
| 일반 테이블에 INSERT | 생략 | 요청한 일반 테이블 |
| 부모 테이블을 통해 INSERT | 행에 맞는 자식 선택 | 선택된 자식 |
| 특정 자식에 직접 INSERT | 해당 자식에 속하는 행인지 검증 | 지정한 자식; 부적합하면 오류 |

직접 자식 INSERT 검증은 [`partition.c:3666–3674`](https://github.com/CUBRID/cubrid/blob/fb567a629cdb390fff920542173fa36f454c74a0/src/query/partition.c#L3666-L3674)에 있습니다.

## 이것이 OOS 설계 검토에 주는 의미

현재 기준 코드에서 SQL의 `HEAP_CACHE_ATTRINFO` 를 RECDES로 변환하는 경로는, 위의 목적지 선택보다 먼저 OOS를 기록합니다.

```text
행을 RECDES로 변환
  └─ OOS 기록                 ← 현재 위치: 목적지 선택 전
locator_insert_force()
  ├─ 자식 목적지 선택
  └─ heap_insert_logical()     ← 이때는 목적지를 이미 알고 있음
```

코드에서 [행 변환 호출은 7699행](https://github.com/CUBRID/cubrid/blob/fb567a629cdb390fff920542173fa36f454c74a0/src/transaction/locator_sr.c#L7699), [locator INSERT 호출은 7711행](https://github.com/CUBRID/cubrid/blob/fb567a629cdb390fff920542173fa36f454c74a0/src/transaction/locator_sr.c#L7711)입니다. 행 변환 내부의 [`heap_attrinfo_insert_to_oos()` 호출](https://github.com/CUBRID/cubrid/blob/fb567a629cdb390fff920542173fa36f454c74a0/src/storage/heap_file.c#L13813-L13821)이 먼저 실행됩니다.

따라서 검토할 질문은 **“heap 삽입 시점에 부모인지 자식인지 다시 알아낼 수 있는가?”보다 “이미 결정된 목적지로 OOS를 기록하도록 순서를 바꿀 수 있는가?”**입니다. 목적지 정보 자체는 `real_class_oid` / `real_hfid` 및 그 값으로 만든 context에 있습니다.

다만 이 사실만으로 구현이 단순해진다고 확정할 수는 없습니다. 목적지가 정해지기 전에도 파티션 키를 읽을 수 있어야 하므로, OOS 기록만 생략하고 빈 stub을 남겨서는 안 됩니다. 현재 합의한 POC는 모든 값을 inline RECDES에 유지하고, 목적지 선택 뒤 공통 함수에서 OOS 기록과 stub 교체를 수행하는 방식입니다. 코드 단순화 여부는 그 구현과 검증으로 판단합니다.

## 설명 범위

이 보고서는 **해당 커밋의 일반적인 한 행 locator INSERT 경로를 읽어 확인한 결과**입니다. 런타임 호출 횟수를 측정한 보고서는 아닙니다.

- “한 SQL 문장당 함수가 무조건 한 번 호출된다”는 뜻은 아닙니다. 여러 행 INSERT나 트리거 등은 별도 호출을 만들 수 있고, 오류가 나면 heap 호출에 도달하지 않을 수도 있습니다.
- `heap_insert_logical()` 에는 [주소 선할당](https://github.com/CUBRID/cubrid/blob/fb567a629cdb390fff920542173fa36f454c74a0/src/storage/heap_file.c#L5693-L5700) 등 다른 호출자도 있습니다. 모든 호출을 일반 행 INSERT로 취급해서는 안 됩니다.
- `OID_IS_ROOTOID` 의 root는 시스템 루트 class입니다. **파티션 부모 판별자가 아니므로**, 이 assert를 본 결론의 근거로 사용하지 않았습니다. [매크로 정의](https://github.com/CUBRID/cubrid/blob/fb567a629cdb390fff920542173fa36f454c74a0/src/storage/oid.h#L85)
- UPDATE, loader, 복제의 전체 경로까지 이 결론을 확대하지 않습니다. 특히 같은 heap UPDATE와 다른 파티션으로 이동하는 UPDATE는 별도 순서 검토가 필요합니다.

## 구두 보고용 설명

> 코드를 확인해 보니, 부모 테이블로 INSERT를 요청해도 부모 heap에 먼저 저장하는 것은 아니었습니다. locator에서 행이 들어갈 자식을 먼저 고르고, 그 자식의 heap 정보를 `heap_insert_logical()` 에 전달합니다. 현재 문제는 OOS 기록이 그 선택보다 먼저 실행된다는 점입니다. 그래서 목적지 선택까지 값을 보존하고, 선택된 heap에 OOS를 기록하는 방식으로 POC를 진행하겠습니다. 새 코드가 기존 prepared-row 방식보다 실제로 단순해지는지를 비교하겠습니다.
