## Purpose

CBRD-26814 는 `feat/oos` 브랜치에서 OOS column 이 여러 개 있는 row 를 INSERT 할 때 `csql` 이 `or_put_bigint` assertion 으로 종료되는 회귀를 고친다.

OOS 는 큰 variable column 값을 heap record 안에 그대로 넣지 않고 OOS file 로 빼는 기능이다. heap record 안에는 원래 값 대신 작은 inline OOS stub 만 남긴다. 이 stub 은 OOS file 에 있는 값을 다시 찾기 위한 `OOS OID` 와 원래 값의 길이를 담는다.

- AS-IS: inline OOS stub 이 들어갈 공간을 `buf->ptr` 기준으로 검사했다. 그런데 그 시점의 `buf->ptr` 는 variable offset table 쪽을 가리키고, 실제 stub 은 variable value area 의 `*ptr_varvals` 위치에 쓰인다. 즉, 앞쪽 공간을 검사하고 뒤쪽에 쓰는 상태였다.
- TO-BE: inline OOS stub 이 실제로 기록되는 `*ptr_varvals` 기준으로 공간을 검사한다. 공간이 부족하면 assertion 으로 죽지 않고 `S_DOESNT_FIT` 를 반환해서 기존 copyarea retry 흐름이 더 큰 buffer 로 다시 시도한다.

### Terms Used In This Fix

이 버그는 포인터 이름만 보면 헷갈리기 쉽다. 아래 네 가지를 먼저 구분해야 한다.

| Term | Meaning |
|---|---|
| `buf->buffer` | record 를 만들기 위해 받은 buffer 의 시작 주소 |
| `buf->endptr` | 이 buffer 에서 쓸 수 있는 마지막 한계 주소 |
| `buf->ptr` | `OR_BUF` 의 현재 write cursor. offset table 을 쓸 때도 쓰고, value area 를 쓸 때도 재사용한다. |
| `*ptr_varvals` | variable value area 에서 다음 variable value 또는 inline OOS stub 을 써야 하는 실제 위치 |

핵심은 `buf->ptr` 가 항상 "실제 값 쓰기 위치"를 뜻하지 않는다는 점이다. 이 함수에서는 먼저 `buf->ptr` 로 variable offset table entry 를 쓰고, 그 다음 `buf->ptr = *ptr_varvals` 로 value area 에 점프해서 실제 값을 쓴다.

### Heap Record Layout

heap record 는 대략 다음처럼 앞쪽에는 metadata, 뒤쪽에는 variable value bytes 를 둔다.

```text
----------------+------------------------+-------------------+--------------------------+
| record header  | variable offset table  | fixed/bound bits  | variable value area      |
|                | (VOT)                  |                   |                          |
+----------------+------------------------+-------------------+--------------------------+
^                ^                        ^                   ^                          ^
buf->buffer      buf->ptr while writing   ...                 *ptr_varvals while writing  buf->endptr
                 VOT entry                                    actual value/OOS stub
```

variable column 하나를 쓸 때는 두 군데를 건드린다.

1. VOT entry 에 "이 column 의 값은 value area 의 몇 byte offset 에서 시작한다"를 적는다.
2. value area 에 실제 column bytes 를 적는다.

OOS column 도 같은 구조를 쓴다. 다만 value area 에 원래 큰 값 전체를 쓰지 않고, `OR_OOS_INLINE_SIZE` 만큼의 inline OOS stub 만 쓴다.

```text
Normal variable column:
  VOT entry: value offset
  value area: actual value bytes, e.g. 5000 bytes

OOS variable column:
  VOT entry: value offset + OOS flag
  value area: inline OOS stub, currently OOS OID + full length
  OOS file: actual value bytes, e.g. 5000 bytes
```

## Implementation

변경 범위는 `src/storage/heap_file.c` 한 파일이고, 실제 code diff 는 한 줄이다.

### Where The Bug Was

문제 함수는 `heap_attrinfo_transform_variable_to_disk()` 이다. 이 함수는 variable column 하나를 disk record 형식으로 직렬화한다.

현재 흐름을 간단히 줄이면 다음과 같다.

```c
/* 1. VOT entry 위치로 이동 */
buf->ptr = (char *) OR_VAR_ELEMENT_PTR (buf->buffer, value->last_attrepr->location);

/* 2. VOT entry 를 쓴다. OOS column 이면 OOS flag 도 offset 에 섞어 넣는다. */
length = CAST_BUFLEN (*ptr_varvals - buf->buffer - header_size);
if (is_oos)
  {
    length = OR_SET_VAR_OOS (length);
  }
or_put_offset_internal (buf, length, offset_size);

/* 3. OOS column 이면 value area 에 inline OOS stub 을 쓴다. */
if (is_oos)
  {
    if (buf->ptr + OR_OOS_INLINE_SIZE > buf->endptr)
      {
        return S_DOESNT_FIT;
      }

    buf->ptr = *ptr_varvals;
    or_put_oid (buf, oos_oid);
    or_put_bigint (buf, oos_length);
    *ptr_varvals = buf->ptr;
  }
```

문제는 `if (buf->ptr + OR_OOS_INLINE_SIZE > buf->endptr)` 이다. 이 check 는 "현재 `buf->ptr` 에서 inline OOS stub 을 쓸 수 있는가"를 묻는다.

하지만 바로 아래에서 `buf->ptr = *ptr_varvals` 로 cursor 를 옮긴다. 실제 write 는 check 한 위치가 아니라 `*ptr_varvals` 위치에서 일어난다.

```text
check 위치:  buf->ptr       -> VOT 쪽
write 위치:  *ptr_varvals   -> value area 쪽
```

그래서 기존 코드는 다음과 같은 상황을 막지 못했다.

```text
buf->endptr   = buffer + 128
buf->ptr      = buffer +  24   // VOT entry 를 막 쓴 위치
*ptr_varvals  = buffer + 120   // 다음 value 를 실제로 써야 하는 위치

bad check:
  buf->ptr + 16 <= buf->endptr
  24 + 16 <= 128
  true

actual write:
  *ptr_varvals + 16 <= buf->endptr
  120 + 16 <= 128
  false
```

기존 check 는 통과하지만, 실제 inline OOS stub 은 buffer 끝을 8 bytes 넘어서 쓰게 된다. debug build 에서는 `or_put_oid()` 또는 `or_put_bigint()` 내부 assertion 이 잡아낸다. release build 에서는 같은 상황이 memory overwrite 로 이어질 수 있다.

### The One-Line Fix

수정은 check 기준을 실제 write 위치로 바꾸는 것이다.

```diff
-      if (buf->ptr + OR_OOS_INLINE_SIZE > buf->endptr)
+      if (*ptr_varvals + OR_OOS_INLINE_SIZE > buf->endptr)
```

수정 후 흐름은 이렇게 읽을 수 있다.

```c
if (is_oos)
  {
    /* inline OOS stub 을 실제로 쓸 위치가 충분한지 먼저 확인한다. */
    if (*ptr_varvals + OR_OOS_INLINE_SIZE > buf->endptr)
      {
        return S_DOESNT_FIT;
      }

    /* 확인한 바로 그 위치로 이동해서 OOS OID 와 length 를 쓴다. */
    buf->ptr = *ptr_varvals;
    or_put_oid (buf, oos_oid);
    or_put_bigint (buf, oos_length);
    *ptr_varvals = buf->ptr;
  }
```

`buf->ptr = *ptr_varvals` 를 먼저 하고 `buf->ptr + OR_OOS_INLINE_SIZE` 를 검사해도 의미는 같다. 이 PR은 code movement 없이 check 식만 바꾸는 가장 작은 patch 를 택했다.

### Example 1: One OOS Column With Enough Space

다음처럼 큰 `BIT VARYING` 값 하나가 OOS 로 demote 된다고 가정한다.

```sql
CREATE TABLE t (id INT, v1 BIT VARYING);

INSERT INTO t VALUES
  (1, CAST(REPEAT('AA', 5000) AS BIT VARYING));
```

logical value 는 5000 bytes 이지만, heap record 에는 5000 bytes 전체를 넣지 않는다. OOS file 에 실제 5000 bytes 를 쓰고, heap record value area 에는 inline OOS stub 만 남긴다.

```text
heap record:
  id = 1
  v1 = inline OOS stub

OOS file:
  OOS OID 가 가리키는 곳에 5000-byte value 저장
```

buffer 상태가 다음과 같으면 기존 code 와 수정 code 모두 성공한다.

```text
buf->endptr   = buffer + 256
buf->ptr      = buffer +  24
*ptr_varvals  = buffer + 100

old check:
  24 + 16 <= 256   -> true

new check:
  100 + 16 <= 256  -> true
```

이 경우는 버그가 드러나지 않는다. 실제 write 위치에도 충분한 공간이 있기 때문이다.

### Example 2: Multiple OOS Columns Near The Buffer End

이번에는 OOS column 이 여러 개 있다고 가정한다.

```sql
CREATE TABLE t (
  id INT,
  v1 BIT VARYING,
  v2 BIT VARYING,
  v3 BIT VARYING
);

INSERT INTO t VALUES (
  1,
  CAST(REPEAT('AA', 5000) AS BIT VARYING),
  CAST(REPEAT('BB', 5000) AS BIT VARYING),
  CAST(REPEAT('CC', 5000) AS BIT VARYING)
);
```

각 큰 value 는 OOS file 로 가고, heap record value area 에는 column 마다 inline OOS stub 이 하나씩 남는다.

```text
value area before writing OOS stubs:

  *ptr_varvals
      |
      v
  +---------+---------+---------+
  | v1 stub | v2 stub | v3 stub |
  +---------+---------+---------+
      16B       16B       16B
```

`v1`, `v2` stub 을 쓰고 나면 `*ptr_varvals` 는 계속 뒤로 이동한다.

```text
after v1: *ptr_varvals += 16
after v2: *ptr_varvals += 16
before v3: *ptr_varvals is close to buf->endptr
```

문제가 되는 마지막 column 에서 buffer 상태가 다음과 같다고 하자.

```text
buf->endptr   = buffer + 128
buf->ptr      = buffer +  28   // v3 의 VOT entry 를 쓴 직후
*ptr_varvals  = buffer + 120   // v3 stub 을 실제로 써야 할 위치
```

기존 code 는 이렇게 판단한다.

```text
buf->ptr + 16 > buf->endptr ?
28 + 16 > 128 ?
false

=> 충분하다고 판단하고 계속 진행
```

하지만 실제 write 는 여기서 일어난다.

```text
*ptr_varvals + 16 > buf->endptr ?
120 + 16 > 128 ?
true

=> 실제로는 부족하다
```

그래서 debug build 에서는 `or_put_bigint()` 의 assertion 이 터진다.

```text
Assertion `buf->ptr + OR_BIGINT_SIZE <= buf->endptr' failed.
```

수정 후에는 `or_put_oid()` / `or_put_bigint()` 로 들어가기 전에 `S_DOESNT_FIT` 를 반환한다.

```text
new check:
  *ptr_varvals + 16 > buf->endptr
  120 + 16 > 128
  true

return S_DOESNT_FIT;
```

### Why `S_DOESNT_FIT` Is The Right Result

이 함수는 "buffer 가 부족하면 죽는다"가 아니라 "buffer 가 부족하면 알려준다"는 계약을 가진다.

반환값 중 하나가 `S_DOESNT_FIT` 인 이유가 그것이다. 하위 serializer 가 `S_DOESNT_FIT` 를 반환하면, 상위 caller 는 더 큰 copyarea 또는 record buffer 를 준비해서 같은 row 변환을 다시 시도한다.

```text
heap_attrinfo_transform_variable_to_disk()
  -> S_DOESNT_FIT

heap_attrinfo_transform_columns_to_disk()
  -> S_DOESNT_FIT

heap_attrinfo_transform_to_disk_internal()
  -> expected_size 를 늘리고 retry

locator_allocate_copy_area_by_attr_info()
  -> 더 큰 copyarea 로 다시 시도
```

CBRD-26814 의 핵심은 이 retry 경로가 없는 것이 아니었다. retry 경로는 이미 있었다. 문제는 잘못된 포인터로 bounds check 를 해서, retry 로 빠져야 할 상황에서 assertion 으로 먼저 죽었다는 점이다.

### Why `bigPageSize.sh` Hit This Bug

CBRD-26814 의 재현 test 인 `bigPageSize.sh` 는 한 row 안에 여러 큰 variable column 을 넣는다. 대표적으로 큰 `VARCHAR`, `STRING`, `CLOB`, `BLOB`, `JSON` 값이 함께 들어간다.

OOS demotion 이후에도 heap record writer 는 각 OOS column 마다 inline OOS stub 을 value area 에 순서대로 쓴다.

```text
row has many large variable columns
  -> several columns are demoted to OOS
  -> each demoted column leaves one inline OOS stub in the heap record
  -> *ptr_varvals advances by OR_OOS_INLINE_SIZE each time
  -> near the last OOS column, value-area cursor can be close to buf->endptr
```

이 상황에서는 `buf->ptr` 와 `*ptr_varvals` 의 차이가 커진다. `buf->ptr` 는 여전히 앞쪽 VOT 주변에 있으므로 check 는 쉽게 통과한다. 그러나 `*ptr_varvals` 는 value area 끝에 가까워져 있어서 실제 write 는 실패할 수 있다.

### What This PR Does Not Change

이 PR은 pointer 기준만 고친다. 다음 동작은 바꾸지 않는다.

- 어떤 column 을 OOS 로 demote 할지 정하는 정책
- OOS OID 와 length 로 구성되는 inline OOS stub 형식
- OOS file record format
- SELECT 시 OOS 값을 읽는 OOS Resolve / OOS Expand 동작
- LOB locator path 생성 방식
- `bigPageSize.sh` 의 최종 output 비교 방식

그래서 이 PR 이후 `bigPageSize.sh` 가 더 이상 `or_put_bigint` assertion 으로 죽지 않아도, 최종 `NOK` 가 다른 이유로 남을 수 있다. 실제 확인에서도 남은 `NOK` 는 LOB locator path 문자열 차이였고, 이 write-side bounds bug 와는 별개다.

## Remarks

### Reviewer Focus

리뷰어는 `src/storage/heap_file.c` 의 `heap_attrinfo_transform_variable_to_disk()` 안 OOS 분기만 보면 된다.

확인할 질문은 하나다.

```text
inline OOS stub 을 쓸 공간을 검사하는 포인터가
실제로 inline OOS stub 을 쓰는 포인터와 같은가?
```

수정 후 답은 yes 다.

```text
check: *ptr_varvals + OR_OOS_INLINE_SIZE <= buf->endptr
write: buf->ptr = *ptr_varvals; or_put_oid(); or_put_bigint();
```

### Verification

- `src/storage/heap_file.c` 의 diff 는 1 line 이며, `git diff --check -- src/storage/heap_file.c` 를 통과했다.
- debug build 가 성공했다.
- CBRD-26814 의 직접 실패 단계인 `bigPageSize.sh` 의 `init.sql` INSERT 가 assertion 없이 끝났고, `select count(*) from t` 결과가 256 인 것을 확인했다.
- 전체 `bigPageSize.sh` 는 더 이상 `or_put_bigint` assertion 이나 `unloaddb` crash 를 보이지 않았다.
- 전체 `bigPageSize.sh` 의 최종 `NOK` 는 LOB locator path 문자열 차이로 남았다. 이는 이 PR의 write-side bounds fix 와 별개의 shell compare / locator 이슈다.

### Limits

이 PR은 CBRD-26814 의 write-side buffer bounds 문제만 고친다. CBRD-26660 의 LOB/ELO cluster 안에서 남는 locator path 비교, stale database volume, `databases.txt` 의존성 같은 shell-test 문제는 이 PR의 범위가 아니다.
