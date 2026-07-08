# [CBRD-27006] OOS recdes locality 쉽게 이해하기

- 원문: `CBRD-27006-oos-recdes-locality.md`
- JIRA: https://jira.cubrid.org/browse/CBRD-27006
- PR: https://github.com/CUBRID/cubrid/pull/7391
- 대상 branch: `feat/oos`
- 작업 branch: `CBRD-27006-oos-recdes-locality`
- 현재 확인일: 2026-07-07

이 문서는 원문을 더 쉽게 풀어쓴 버전이다. 목표는 CUBRID 내부 코드를 잘 모르는 사람도
이 PR이 왜 필요한지, 어떤 코드를 바꾸는지, 무엇은 바꾸지 않는지 이해하는 것이다.

## 한 문장 요약

CBRD-27006은 한 heap record에서 나온 여러 OOS 값을 가능한 한 같은 OOS page에 모아 쓰고,
읽을 때도 같은 page에 있는 OOS 값들을 한 번에 읽도록 바꾸는 PR이다.

쉽게 말하면, 같은 row에 속한 큰 컬럼 값들을 여기저기 흩어 놓지 말고 가까운 곳에 두자는
변경이다. 데이터가 가까이 있으면 나중에 읽을 때 page를 여러 번 잡았다 놓는 일을 줄일 수 있다.

## 먼저 알아야 할 배경

### heap record와 RECDES

CUBRID에서 table row는 heap file 안의 heap record로 저장된다. 코드에서는 이 record를
`RECDES` 라는 구조로 많이 다룬다.

예를 들어 row가 이렇게 생겼다고 하자.

```text
id = 1
name = 'kim'
big_col1 = 아주 큰 값
big_col2 = 아주 큰 값
```

작은 값은 heap record 안에 그대로 넣어도 된다. 하지만 큰 variable column 값을 모두 heap
record 안에 넣으면 record가 너무 커진다. 그러면 작은 컬럼만 읽고 싶어도 큰 값까지 같이
읽게 되어 비효율적이다.

### OOS란?

OOS는 Out-of-row Overflow Storage의 약자다. 큰 variable column 값을 heap record 밖의
OOS file에 따로 저장하는 방식이다.

AS-IS, OOS가 없거나 OOS를 쓰지 않는 경우:

```text
heap record
[ id | name | big_col1의 실제 값 | big_col2의 실제 값 ]
```

OOS를 쓰는 경우:

```text
heap record
[ id | name | big_col1의 OOS OID | big_col2의 OOS OID ]
                       |                    |
                       v                    v
                  OOS file              OOS file
              [ big_col1 값 ]       [ big_col2 값 ]
```

여기서 `OOS OID` 는 "실제 큰 값이 OOS file의 어느 page, 어느 slot에 있는지" 알려주는
주소 같은 값이다. heap record 안에는 큰 값 전체가 아니라 16바이트짜리 OOS inline slot이
들어간다. 그 안에는 OID와 원래 값 길이가 들어 있다.

## 이 PR이 해결하려는 문제

이 PR 전에는 한 row 안에 OOS 대상 컬럼이 여러 개 있어도 컬럼마다 따로 처리했다.

예를 들어 한 row에 OOS 값 3개가 있다고 하자.

```text
row 1:
  c1 = OOS 대상
  c2 = OOS 대상
  c3 = OOS 대상
```

기존 insert 흐름은 대략 이랬다.

```text
c1 저장 -> OOS page 찾기 -> page fix -> insert -> page unfix
c2 저장 -> OOS page 찾기 -> page fix -> insert -> page unfix
c3 저장 -> OOS page 찾기 -> page fix -> insert -> page unfix
```

이 방식에는 두 가지 문제가 있다.

1. 같은 row에서 나온 값인데 서로 다른 OOS page로 흩어질 수 있다.
2. 같은 page에 들어갈 수 있는 값이어도 page 탐색과 page fix를 여러 번 반복할 수 있다.

읽을 때도 비슷했다. OOS OID가 여러 개 있으면 각각 `oos_read()` 를 호출했다.

```text
c1 읽기 -> page fix -> read -> page unfix
c2 읽기 -> page fix -> read -> page unfix
c3 읽기 -> page fix -> read -> page unfix
```

만약 c1, c2, c3가 같은 OOS page에 있다면 page를 한 번만 fix하고 세 값을 읽는 편이 낫다.

## 이 PR의 핵심 아이디어

핵심은 두 가지다.

1. 쓸 때: 같은 heap record에서 나온 OOS 값들을 모아서 `oos_insert_many()` 로 넣는다.
2. 읽을 때: 여러 OOS 값을 `oos_read_many()` 로 묶어서 읽는다.

단, 아무렇게나 묶는 것이 아니다. 이 PR은 기존 OOS 저장 형식과 의미를 유지하면서,
효율만 개선한다.

## 바뀌지 않는 것

이 PR은 다음을 바꾸지 않는다.

- OOS on-disk format
- heap record 안의 OOS inline slot layout
- OOS OID가 가리키는 방식
- OOS OID 공유 정책
- multi-chunk chain 구조
- replication log format
- OOS demotion 정책 자체

특히 "OOS OID 하나를 여러 record가 공유한다" 같은 변화는 없다. OOS OID는 여전히 값
하나에 대한 주소다.

## 주요 용어

### locality

locality는 "같이 쓰이는 데이터를 가까운 곳에 둔다"는 뜻이다. 이 PR의 locality는 한 heap
record에서 나온 여러 OOS 값을 가능한 한 같은 OOS page에 두는 것을 말한다.

### single-chunk 값

OOS 값 하나가 OOS page 하나 안에 들어갈 수 있으면 single-chunk 값이다.

```text
OOS value A -> OOS page 하나에 저장 가능
```

### multi-chunk 값

OOS 값 하나가 너무 커서 page 하나에 안 들어가면 여러 chunk로 나누어 저장한다.

```text
OOS value B
  -> chunk 1 -> chunk 2 -> chunk 3
```

heap record 안의 OOS OID는 첫 번째 chunk, 즉 head chunk를 가리킨다.

### head page

OOS OID가 직접 가리키는 첫 번째 chunk가 들어 있는 page다. `oos_read_many()` 는 같은
head page를 가리키는 요청들을 묶어서 처리한다.

### page fix

CUBRID buffer manager에서 page를 읽거나 쓰려면 그 page를 fix해야 한다. 쉽게 말하면
"지금 이 page를 쓰거나 읽을 것이니 메모리에 붙잡아 두겠다"는 동작이다.

page fix는 공짜가 아니다. 그래서 같은 page를 여러 번 fix/unfix하는 것보다, 가능하면 한
번 fix한 동안 필요한 일을 모아서 하는 편이 좋다.

### OOS insert publication

OOS insert publication은 insert된 OOS OID를 나중에 replication 처리에서 사용할 수 있도록
기록해 두는 일이다.

이 PR 전에는 OOS API가 OID를 돌려주고, caller가 그 OID를 별도로 push하는 흐름이 섞일 수
있었다. 이 PR 후에는 public OOS insert API가 성공한 OOS OID publication을 직접 담당한다.

## 쓰기 경로가 어떻게 바뀌나

쓰기 경로의 중심은 `heap_attrinfo_insert_to_oos()` 와 `oos_insert_many()` 다.

### 1단계: OOS로 보낼 값을 고른다

OOS 대상 컬럼을 고르는 큰 정책은 이 PR의 주제가 아니다. 이미 OOS 쪽에는 record가 일정
크기보다 커지면 큰 variable column을 OOS로 보내는 정책이 있다.

CBRD-27006은 "어떤 컬럼을 OOS로 보낼까"가 아니라, "이미 OOS로 보내기로 한 여러 값을
어떻게 더 가까이 배치할까"를 다룬다.

### 2단계: OOS 대상 값을 임시 buffer로 직렬화한다

`heap_attrinfo_insert_to_oos()` 는 OOS 대상 값을 attribute order대로 걷는다. 그리고 각
값을 OOS에 넣을 byte buffer로 만든다.

여기서 중요한 점은, 기존처럼 값 하나를 만들고 바로 `oos_insert()` 하는 방식이 아니라는
것이다. 이 PR에서는 여러 값을 먼저 준비한 뒤 한 번에 `oos_insert_many()` 로 넘긴다.

간단히 보면 이렇다.

```text
attr order:
  c1 -> OOS 대상 -> buffer 준비
  c2 -> OOS 대상 아님 -> skip
  c3 -> OOS 대상 -> buffer 준비
  c4 -> OOS 대상 -> buffer 준비

requests:
  [c1 buffer, c3 buffer, c4 buffer]
```

각 request는 대략 이렇게 생겼다.

```cpp
struct oos_insert_request
{
  oos_buffer src;
  OID *oid_out;
};
```

- `src`: OOS에 저장할 byte 범위
- `oid_out`: insert 결과로 나온 OOS OID를 써 줄 자리

### 3단계: `oos_insert_many()` 가 request를 순서대로 처리한다

`oos_insert_many()` 는 request 순서를 바꾸지 않는다. 정렬하지 않는다. logical attribute
order를 유지한다.

그 이유는 OOS OID publication과 replication 쪽에서 순서가 중요하기 때문이다.

### 4단계: multi-chunk 값은 기존 방식대로 처리한다

request 하나가 너무 커서 OOS page 하나에 들어가지 않으면 multi-chunk 값이다. 이 경우에는
기존 `oos_insert_across_pages()` 흐름을 사용한다.

즉, 이 PR은 multi-chunk chain 형식을 새로 만들지 않는다.

```text
큰 값:
  chunk 1 -> chunk 2 -> chunk 3

heap record에는 chunk 1의 OOS OID가 들어감
```

multi-chunk 값도 insert가 성공하면 public OOS insert API가 OOS OID publication을 처리한다.

### 5단계: single-chunk 값들은 한 page에 들어갈 만큼 greedy하게 묶는다

single-chunk 값들은 가능한 한 한 OOS page에 같이 넣는다.

예를 들어 request가 이렇게 있다고 하자.

```text
requests:
  c1 = 1000 bytes
  c2 = 1200 bytes
  c3 = 900 bytes
```

세 값이 OOS page 하나에 모두 들어갈 수 있으면 하나의 single-page OOS batch가 된다.

```text
OOS page P
  slot 1: c1
  slot 2: c2
  slot 3: c3
```

이 PR에서 "batch"는 단순히 for-loop를 줄이는 정도가 아니다. batch 전체를 한 page에
배치하는 단위로 본다.

만약 c1, c2는 같이 들어가지만 c3까지는 안 들어간다면 이렇게 나뉠 수 있다.

```text
batch 1: c1, c2
batch 2: c3
```

이때도 request 순서는 유지된다.

### 6단계: 기존 page는 batch 전체가 들어갈 때만 재사용한다

이 PR의 중요한 정책은 "batch를 흩뿌리지 않는다"는 것이다.

예를 들어 기존 OOS page A에는 c1만 들어갈 공간이 있고, 기존 OOS page B에는 c2만 들어갈
공간이 있다고 하자. batch가 c1, c2라면 두 값을 A와 B에 나누어 넣지 않는다.

```text
나쁜 방향:
  page A: c1
  page B: c2
```

대신 batch 전체가 들어가는 page를 찾는다. 그런 page가 없으면 새 page를 할당해서 둘을
같이 넣는다.

```text
PR 방향:
  fresh page C: c1, c2
```

이렇게 하면 같은 row에서 나온 OOS 값들이 가까이 있을 가능성이 높아진다.

### 7단계: 한 page에 여러 값을 넣고 bestspace는 한 번 갱신한다

`oos_insert_single_page_batch()` 는 batch 전체가 들어갈 OOS page를 하나 fix한다. 그리고
그 page에 request를 순서대로 insert한다.

각 값마다 해야 하는 일은 그대로 한다.

- OOS record 만들기
- slotted page에 insert하기
- OOS OID 만들기
- WAL log 남기기
- OOS insert publication 하기

하지만 page fix와 bestspace 갱신은 batch 단위로 줄어든다.

## 읽기 경로가 어떻게 바뀌나

읽기 경로의 중심은 `oos_read_many()` 다.

### 기존 scalar read

기존에는 OOS 값 하나를 읽을 때 `oos_read()` 를 사용했다.

```text
oos_read(OID 1)
oos_read(OID 2)
oos_read(OID 3)
```

각 OID가 같은 page에 있어도 호출은 따로였다.

### 새 grouped read

`oos_read_many()` 는 여러 read request를 받는다.

```cpp
struct oos_read_request
{
  OID oid;
  oos_buffer dest;
};
```

- `oid`: heap record에 저장되어 있던 OOS OID
- `dest`: 실제 OOS 값을 복사해 넣을 caller-owned buffer

`oos_read_many()` 는 request들을 보면서 같은 `(volid, pageid)` 를 가진 head page 요청들을
묶는다.

예를 들어 OID가 이렇게 있다고 하자.

```text
OID 1 -> page 10, slot 1
OID 2 -> page 10, slot 2
OID 3 -> page 10, slot 3
```

그러면 page 10을 한 번 fix하고 세 값을 읽을 수 있다.

```text
fix page 10
  read slot 1
  read slot 2
  read slot 3
unfix page 10
```

### multi-chunk tail은 head page를 놓은 뒤 읽는다

multi-chunk 값은 head chunk 뒤에 tail chunk들이 이어진다.

`oos_read_many()` 는 head page를 fix한 상태에서 head chunk만 읽고, tail chunk가 필요하면
head page를 unfix한 뒤 기존 multi-chunk read 흐름으로 이어서 읽는다.

이 정책은 동시에 여러 page를 오래 붙잡는 일을 피한다. 기존 scalar `oos_read()` 의 latch
동작과 비슷하게 유지하려는 선택이다.

## Lazy Resolve는 언제 batch를 쓰나

OOS 읽기에는 크게 두 종류가 있다.

### Lazy Resolve

query가 실제로 요청한 column만 OOS에서 읽는 방식이다.

예를 들어 table에 OOS column이 c1, c2가 있어도 query가 `small_col` 만 읽으면 OOS 값을
읽을 필요가 없다.

```sql
SELECT small_col FROM t;
```

이 PR의 최신 형태에서는 lazy Resolve가 무조건 batch를 쓰지 않는다.

dispatch rule은 이렇다.

```text
요청된 OOS 값 개수 = 0 -> scalar path
요청된 OOS 값 개수 = 1 -> scalar path
요청된 OOS 값 개수 >= 2 -> oos_read_many()
```

이유는 간단하다. OOS 값이 0개나 1개면 묶어서 읽을 이득이 없다. 오히려 vector allocation
같은 준비 비용이 생길 수 있다.

그래서 single-OOS projection은 기존 scalar path를 유지한다. 이 path는 작은 값에 대해
`IO_MAX_PAGE_SIZE` stack scratch fast path를 쓸 수 있다.

### Record-level Expand

Record-level Expand는 heap record 안의 모든 OOS OID를 실제 값으로 바꿔서 record 전체를
확장하는 방식이다.

이 방식은 raw recdes bytes를 소비하는 코드에서 필요하다. 예를 들어 client로 record bytes를
보내거나, record를 통째로 다시 넣거나, byte 단위로 비교하는 경로가 여기에 해당한다.

이 경우에는 어차피 모든 OOS 값을 읽어야 하므로 `heap_oos_read_values()` 가 OOS read request를
모아서 `oos_read_many()` 를 호출한다.

## OOS insert publication 책임이 왜 바뀌었나

이 PR은 public OOS insert API가 OOS insert publication을 직접 맡도록 정리한다.

### 기존 위험

기존에는 이런 흐름이 가능했다.

```text
caller:
  oid = oos_insert(...)
  oos_push_oos_oid(oid)
```

그런데 이제 `oos_insert_many()` 가 생기면 scalar insert와 batch insert가 같은 publication
규칙을 가져야 한다. caller가 직접 push하는 흐름이 남아 있으면 중복 push나 순서 꼬임이
생길 수 있다.

### 새 규칙

새 규칙은 단순하다.

```text
public OOS insert API가 성공한 OOS OID를 publish한다.
caller는 다시 push하지 않는다.
```

그래서 `oos_insert()` 도 성공 시 publish하고, `oos_insert_many()` 도 성공한 각 request의
OID를 publish한다.

오류가 중간에 발생하면 `oos_clear_insert_publication_state()` 로 임시 publication 상태를
비운다. 실패한 batch의 일부 결과가 나중에 replication 처리에 섞이면 안 되기 때문이다.

## 안전을 위해 지키는 규칙

이 PR에서 중요한 안전 규칙은 다음과 같다.

- request 순서를 바꾸지 않는다.
- OOS OID는 여전히 값 하나를 가리킨다.
- single-chunk batch는 한 page에 들어갈 때만 그 page에 넣는다.
- 기존 page가 batch 전체를 담지 못하면 값을 흩뿌리지 않고 fresh page를 쓴다.
- multi-chunk chain 구조는 기존 방식을 유지한다.
- caller-owned buffer의 lifetime은 call 동안만 필요하다.
- insert/read request는 null pointer, 0 length, `INT_MAX` 초과 길이를 거부한다.
- partial publication이 생긴 뒤 오류가 나면 transient publication state를 clear한다.
- `std::bad_alloc` 은 좁은 STL allocation 경계에서 CUBRID error로 바꾼다.

## 이 PR이 일부러 하지 않는 일

이 PR은 locality와 grouped read에 초점을 둔다. 다음은 이 PR의 범위가 아니다.

- OOS OID reuse
- OOS value deduplication
- OOS read PEEK mode
- multi-column combined OOS record
- multi-chunk continuation page locality
- OOS on-disk format 변경
- replication log format 변경

즉, "저장 형식 자체를 바꾸는 PR"이 아니라 "기존 형식을 유지하면서 같은 row의 OOS 값들을
더 잘 모아 쓰고 읽는 PR"로 이해하면 된다.

## trade-off

좋아지는 점은 명확하다.

- 같은 row의 single-chunk OOS 값들이 같은 page에 있을 가능성이 높아진다.
- 여러 OOS 값을 읽을 때 같은 head page를 한 번만 fix할 수 있다.
- record-level Expand와 multi-OOS lazy Resolve에서 page fix 반복을 줄일 수 있다.
- public OOS insert API의 publication 책임이 명확해진다.

대신 비용도 있다.

- insert 때 OOS 대상 값들을 모두 직렬화해 두므로 peak memory가 예전보다 늘 수 있다.
- batched lazy Resolve는 여러 OOS raw buffer를 DB_VALUE 변환이 끝날 때까지 들고 있는다.
- 기존 page를 부분적으로 재사용하지 않고 fresh page를 쓰는 경우가 있어, locality를 위해
  공간 재사용을 조금 덜 공격적으로 할 수 있다.
- locality는 주로 single-chunk 값과 multi-chunk의 head page에 적용된다. multi-chunk tail
  page까지 새롭게 가까이 배치하는 PR은 아니다.

## 코드에서 어디를 보면 되나

### OOS public API

파일: `src/storage/oos_file.hpp`

- `oos_insert_request`
- `oos_read_request`
- `oos_insert_many()`
- `oos_read_many()`
- unit-test debug counters

### OOS insert 구현

파일: `src/storage/oos_file.cpp`

- `oos_publish_oos_oid()`
- `oos_clear_insert_publication_state()`
- `oos_insert_single_page_batch()`
- `oos_insert_many()`

여기서 single-page OOS batch를 만들고, 한 page에 batch 전체를 넣는 정책을 볼 수 있다.

### OOS read 구현

파일: `src/storage/oos_file.cpp`

- `oos_read_chunk_in_page()`
- `oos_check_head_header()`
- `oos_read()`
- `oos_read_many()`

여기서 scalar read와 grouped read가 공통 helper를 공유한다.

### heap write path

파일: `src/storage/heap_file.c`

- `heap_attrinfo_insert_to_oos()`

여기서 OOS 대상 DB_VALUE를 attribute order대로 직렬화하고 `oos_insert_many()` 로 넘긴다.

### lazy Resolve path

OOS read helper는 `heap_file.c` diff를 줄이기 위해 `heap_oos.cpp` 로 옮겼다.

파일: `src/storage/heap_file.c` (heap-core wiring)

- `heap_recdes_get_var_offset_entry()` — generic VOT entry reader (`heap_file.h` 로 export)
- `heap_attrvalue_read()` / `heap_attrvalue_transform_to_dbvalue()` — scalar reader (`heap_file.h` 로 export)
- `heap_attrinfo_read_dbvalues_internal()` — dispatch (2개 이상이면 grouped path)

파일: `src/storage/heap_oos.cpp` (OOS-specific, `heap_oos.hpp` 로 export)

- `heap_oos_parse_inline_ref()`
- `heap_oos_attr_inline_ptr()`
- `heap_oos_read_dbvalues_grouped()`

여기서 requested OOS 값이 2개 이상일 때만 batch read로 가는 dispatch rule을 볼 수 있다.

### record-level Expand path

파일: `src/storage/heap_oos.cpp`

- `heap_oos_read_values()`

여기서 record 안의 모든 OOS 값을 모아 `oos_read_many()` 로 읽는다.

### replication apply 쪽 caller 정리

파일: `src/transaction/locator_sr.c`

- `locator_oos_insert_force()`

여기서 caller-side OOS OID push가 제거된다. 이제 `oos_insert()` 가 publish를 직접 하기
때문이다.

## 테스트가 확인하는 것

### server OOS unit test

파일: `unit_tests/oos/test_oos_server.cpp`

주요 테스트:

- `OosInsertManyKeepsSinglePageLocalityAndReadManyGroupsHeadPage`
- `OosInsertManyReusesOnlyPageThatFitsWholeBatch`
- `OosInsertManyAllocatesFreshPageInsteadOfScatteringBatch`
- `OosInsertManySplitsOversizedSingleChunkRun`
- `OosInsertManyPreservesMixedSingleAndMultiChunkPublicationOrder`

이 테스트들은 대략 다음을 확인한다.

- 여러 single-chunk 값이 한 page에 같이 들어간다.
- read many가 같은 head page를 하나의 group으로 읽는다.
- 기존 page는 batch 전체가 들어갈 때만 재사용한다.
- batch가 page 하나보다 크면 적절히 나뉜다.
- single-chunk와 multi-chunk가 섞여도 publication order가 깨지지 않는다.

### SQL CRUD test

파일: `unit_tests/oos/sql/test_oos_sql_crud.cpp`

주요 테스트:

- `Cbrd27006MultiOosColumnSelectsAndUpdate`
- `Cbrd27006MixedSingleChunkAndMultiChunkRow`
- `Cbrd27006ReadDispatchBatchesOnlyMultiOosProjections`

이 테스트들은 SQL 수준에서 다음을 확인한다.

- 여러 OOS column을 select/update해도 값이 맞다.
- 한 row 안에 single-chunk와 multi-chunk OOS 값이 섞여도 동작한다.
- non-OOS projection과 single-OOS projection은 `oos_read_many()` 를 부르지 않는다.
- OOS 값 2개를 요청할 때만 `oos_read_many()` 를 부른다.

## 전체 흐름 다시 보기

쓰기 흐름:

```text
heap_attrinfo_insert_to_oos()
  -> OOS 대상 값을 attr order대로 직렬화
  -> oos_insert_request[] 생성
  -> oos_insert_many()
       -> multi-chunk 값은 기존 across-pages insert
       -> single-chunk 값은 한 page에 들어갈 만큼 batch 구성
       -> oos_insert_single_page_batch()
            -> batch 전체가 들어갈 page 찾기
            -> 한 fixed page에 여러 OOS record insert
            -> WAL log
            -> OOS insert publication
            -> bestspace 갱신
```

lazy read 흐름:

```text
heap_attrinfo_read_dbvalues()                     [heap_file.c]
  -> heap_attrinfo_read_dbvalues_internal()        [heap_file.c]
       -> 요청된 OOS 값 개수 확인 (heap_oos_attr_inline_ptr)
       -> 0개 또는 1개면 scalar path
       -> 2개 이상이면 heap_oos_read_dbvalues_grouped()   [heap_oos.cpp]
            -> oos_read_request[] 생성 (heap_oos_parse_inline_ref)
            -> oos_read_many()
            -> raw OOS bytes를 DB_VALUE로 변환
            -> non-OOS 값은 scalar read
```

record-level Expand 흐름:

```text
heap_record_replace_oos_oids()
  -> heap_oos_read_values()
       -> record 안의 모든 OOS inline slot을 찾음
       -> oos_read_many()
       -> 실제 값들로 expanded record 재구성
```

## 마지막으로 기억할 점

이 PR을 가장 짧게 기억하면 다음과 같다.

```text
기존:
  같은 row의 OOS 값도 하나씩 따로 쓰고, 하나씩 따로 읽었다.

변경:
  같은 row의 OOS 값 중 같이 둘 수 있는 것은 같은 page에 넣고,
  같은 page에서 읽을 수 있는 것은 한 번에 읽는다.

범위:
  저장 형식과 replication format은 그대로 둔다.
```

따라서 CBRD-27006은 OOS의 의미를 바꾸는 PR이 아니라, OOS를 더 locality-friendly하게
사용하도록 insert/read 경로를 정리하는 PR이다.
